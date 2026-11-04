# RQ1 (structural, 2-D): the stage-1 offload once the push load's structure is charged

Status: preliminary, 2026-11-03 (SP7 step S7b). The structural part was drafted at step S7a
(2026-10-19) on files A (experiments/silo_structure_2d.yaml, the gate vehicle) and C
(experiments/silo_structure_2d_readme.yaml, the README-loads fork), constant_accel pushes
only. Step S7b added the drive cases of file B (experiments/silo_drive_2d.yaml): silo_cold
and the nine linear-motor variants, each uncharged and with the central structure ("The
drive cases"). Planar 2-D model, sweep-optimized guidance (not an optimal-control solution;
Phase 5), unthrottled. Files A and C were pre-registered in commit cbbd7bc
(docs/phases/inputs/2026-10-15-SP7-preregistration.md, "the pre-registration" or "part 1"
below; its sections are cited as "section n"), with its Amendment 1 (74eb3c8, D-SP7-48: the
sweep's no-offload record and the sweep's re-run). File B was pre-registered in commit
331891d (docs/phases/inputs/2026-11-03-SP7-preregistration-part2.md, "part 2"; its sections
are cited as "part 2, section n"). Every new number comes from run A and run C, made from
the clean commit 1b5f9d4 (1b5f9d46d31c), from the sweep's re-run under Amendment 1 (from
2b343d7; it reproduces the first sweep of 1b5f9d4 cell for cell and adds the no-offload
points' shortfalls; its git record reads dirty, by the session's account from 13 untracked
draft documents of this note, a departure from the clean commit Amendment 1 names,
deviation 45), from run B, made from the clean commit 642e11e (642e11e3851d, dirty false),
from the convergence checks of section 1 and part 2, section 1, and from two sizing-only
scripts, all named under "Provenance" and "Reproduction". Every structural number is a
first-order station sizing of the push load (D-SP7-01): a first-order estimate with its
stated ranges, not a detailed structural design.

## The question

README research question 1 asks how payload or propellant changes with exit speed after
interface mass, extra structure and ignition losses, and where the break-even lies. SP1
(docs/findings/RQ1-fuel-offload-2d.md) measured the propellant form for concept A with no
structural mass charged for the push: at the pad's payload and orbit, the 3 g0, 100 m
cold-start silo lets the gate vehicle leave out 41.26 t of stage-1 propellant. Assumed
stage-1 dry-mass penalties of +2, +4 and +8.1 t left 32.29, 22.88 and 1.98 t, and about
8.5 t (extrapolated) left nothing. This note replaces the assumption with a modelled
structure: a first-order sizing of what the fully fuelled stack needs to survive the push,
charged to the assisted run at every offload the solve evaluates. It asks how much of SP1's
41.26 t survives, and whether "every m/s of assist helps" still holds once the push's
structure is paid for. File B then asks how the drive changes the answer: a linear motor
under an acceleration law or a force law, a stop taper, hot starts, a 22 t carriage and a
sealed shaft, each on the same silo and the same central structure.

## Headline

**With a first-order structure sized for the offloaded stack only (central coefficients; an
assumed real-drive rise time of 0.5 s that the constant_accel trajectory does not fly, its
plateau cost charged; an instant release that the model's single-mode treatment says would
separate the stage-1 LOX column (its bottom at -896 kPa absolute at the release, where the
same tank, empty at the pad's MECO, stays at +132 kPa gauge), as the same treatment also
separates stage 2's full LOX column at the pad's own MECO (-232 kPa gauge, against -162 kPa
gauge at the push); the model's unthrottled envelope; zero margin), the 3 g0, 100 m
cold-start silo leaves out 11.42 t of stage-1 propellant (2.78% of stage 1) against SP1's
41.26 t uncharged; the physics band gives no offload (243.7 m/s short, payload deficit
-2,080 kg (two passes; residual estimate 0.137 kg)) to 28.57 t (28.57 t after the
plausibility rule's factor 0.739, which fires at M_model / R = 1.76 and multiplies the
case's whole dm, the load entry included; 71% of M_model is the envelope of the stage-1 LOX
barrel, an element the push barely loads, sized by axial buckling at the pad's MECO and
carrying nof_barrel, a double count of buckling material the source note flags; 23.68 t
unscaled), the outer envelope no offload (1,021.5 m/s short, payload deficit -7,804 kg (two
passes; residual estimate 23.0 kg)) to 31.12 t; sized for a full load 10.59 t; through the
thrust structure 5.97 t; with a step push no offload (125.2 m/s short, payload deficit
-1,087 kg (two passes; residual estimate 0.277 kg)).**

Beside the number: the gate vehicle carries 26,054.4 kg to the reference orbit against the
published 22,800 kg (+14.3%, outside the +/-10% band; the user accepted the miss on
2026-09-30, docs/findings/CAL-f9-leo-2d.md), so every offload here is a difference between
runs of this vehicle model, not a Falcon 9 figure; file C (the README-loads fork, +8.33%) is
the one robustness row. The thrust-structure row's 5.97 t sits close to its own estimated
break-even (sizing only, S2's first pass: k_ts 0.3476 kg/kN, 24% above the central), and S0
moved k_ts's central after the planning probe in a direction that raised that row (both
beside its reading sentence below).

The sentence is design 4.11's fixed form as amended by D-SP7-46 (section 8), filled from
results/silo_structure_2d/20261016T171513Z/metrics.json: x* and the stage-1 share from
`offload.cases` (`offload_kg`, `stage1_fraction`); the four pressures from silo_cold_s1_st's
`structure_flags` record `structure_release_unload` (`lox_bottom_pressure_min_abs_pa`
-895,688 Pa, `meco_lox_bottom_pressure_min_gauge_pa` +132,436 Pa,
`meco_stage2_lox_bottom_pressure_min_gauge_pa` -231,741 Pa,
`stage2_lox_bottom_pressure_min_gauge_pa` -161,596 Pa); the factor and ratio from
silo_cold_s1_st_phys_lo_scaled (`structure_plausibility_factor` 0.739034,
`structure_plausibility_ratio` 1.75905); the trigger from
`offload.structure_inputs.plausibility.dominant` (stage1.lox_barrel, share 0.7100, mode
monocoque, case "pad GRAVITY_TURN t=151.3284 s", the pad's stage-1 `propellant` event at
151.328437545 s in pad/events.csv, so "the pad's MECO"); "barely loads" because that
barrel's own increment in the central case at x* is 25.1 kg, 0.40% of its dm (below
section 8's 1%); each no-offload end's shortfall from its case's `dv_shortfall_mps` and its
deficit, P_2* - P_ref, from the payload case at the same settings
(`offload.structure_payload_cases`), with that case's residual estimate because its
`structure_payload_unconverged` flag fired.

Every reading sentence that fired (section 8, word for word; a label in brackets names the
physics end a sentence used, and text after "beside:" is printed beside, not read):

- At the central coefficients the modelled structure cancels most of SP1's uncharged
  offload: 11.42 t is left (27.7%).
- [the plausibility-scaled low-mass end] The physics band runs from no offload (243.7 m/s of
  delta-v short of P_ref at x = 0; payload deficit -2,080 kg (two passes; residual estimate
  0.137 kg)) to 28.57 t, so the physics coefficients alone do not decide whether more than
  half of the offload survives.
- [the unscaled low-mass end] The physics band runs from no offload (243.7 m/s of delta-v
  short of P_ref at x = 0; payload deficit -2,080 kg (two passes; residual estimate
  0.137 kg)) to 23.68 t, so the physics coefficients alone do not decide whether more than
  half of the offload survives.
- The outer envelope runs from no offload (1,021.5 m/s of delta-v short of P_ref at x = 0;
  payload deficit -7,804 kg (two passes; residual estimate 23.0 kg)) to 31.12 t, so the
  design assumptions together with the physics do not decide it.
- silo_cold_s1_st_qs (dynamic quasi_static, DLF 1, the plain plateau) cancels most of it:
  15.02 t is left (36.4%). [beside: 36.4% of its own uncharged 41.26 t]
- silo_cold_s1_st_step (dynamic step, DLF 2) cancels all of it: no offload at P_ref
  (125.2 m/s of delta-v short of P_ref at x = 0; payload deficit -1,087 kg (two passes;
  residual estimate 0.277 kg)). [beside: no offload]
- silo_cold_s1_st_full (sizing full_load, dm sized once at x = 0) cancels most of it:
  10.59 t is left (25.7%). [beside: 25.7% of its own 41.26 t]
- silo_cold_s1_st_ts (entry through the thrust structure, k_ts 0.2805 kg/kN) cancels most of
  it: 5.97 t is left (14.5%). [beside: 14.5% of its own 41.26 t; this row's break-even
  (section 8): k_ts at or above 0.3476 kg/kN, 24% above its central 0.2805 and inside its
  range 0.197-0.628, gives no offload on this row (a sizing-only estimate, S2's first pass;
  under the converged sizing, equivalent dm 8,617.1 kg against the 8,488.6 kg crossing); and
  S0 changed k_ts's central at its gate, after the source note was written and with the
  planning probe known, from the note's 0.306 to 0.2805, a move whose direction was plain:
  it raised this row's expected x* by about 2.4 t (5,769.7 against 3,325.2 kg at 0.306,
  sizing only; section 2(b)). The break-even sits 13.6% above the note's 0.306 (derived:
  0.3476 / 0.306).]
- silo_cold_s1_st_m10 (margin 0.10 on the envelope's loads and pressures) cancels most of
  it: 13.27 t is left (32.1%). [beside: 32.1% of its own 41.26 t; an existing margin on the
  pad's envelope, spare capacity the push can use, so this row keeps more than the
  headline's zero (Caveats, "What the headline assumes")]
- silo_cold_s1_st_m25 (margin 0.25 on the envelope's loads and pressures) cancels most of
  it: 15.70 t is left (38.1%). [beside: 38.1% of its own 41.26 t; an existing margin, as the
  row above]
- silo_cold_s1_st_cap45 (the pad's stage-1 felt n capped at 4.5 g0 in the envelope) cancels
  most of it: 10.48 t is left (25.4%). [beside: 25.4% of its own 41.26 t]
- silo_cold_s1_st_cap40 (the pad's stage-1 felt n capped at 4.0 g0 in the envelope) cancels
  most of it: 4.81 t is left (11.6%). [beside: 11.6% of its own 41.26 t]
- silo_hot_full_s1_st (silo_hot_full, stage 1 at full thrust from push start) cancels most
  of it: 16.34 t is left (39.6%). [beside: 41.9% of its own uncharged 38.98 t]
- silo_hot_ramp_s1_st (silo_hot_ramp_on_track, full thrust at release) cancels most of it:
  18.27 t is left (44.3%). [beside: 39.7% of its own uncharged 46.01 t]
- silo_hot_full_s1_st keeps more offload than the cold start with the same structure:
  +4.92 t (uncharged -2.28 t; the structure's offload cost U - X 22.64 t against the cold
  start's 29.84 t) (nothing models the exhaust in the shaft: back-pressure, heating, the
  carriage in the plume, which favours the hot starts).
- silo_hot_ramp_s1_st keeps more offload than the cold start with the same structure:
  +6.85 t (uncharged +4.75 t; the structure's offload cost U - X 27.74 t against the cold
  start's 29.84 t) (nothing models the exhaust in the shaft: back-pressure, heating, the
  carriage in the plume, which favours the hot starts).
- With the central structure, the lowest exit speed of sweep 1 that still offloads is
  76.71 m/s (100 m); below it, at 38.35 m/s (60.2 m/s of delta-v short of P_ref at x = 0;
  payload deficit not flown: no payload case at these settings) and 54.24 m/s (18.3 m/s of
  delta-v short of P_ref at x = 0; payload deficit not flown: no payload case at these
  settings), the structure cancels the offload. [beside: 25 m no offload (uncharged
  18.77 t); 50 m no offload (28.65 t); 100 m 11.42 t (41.26 t); 200 m 31.62 t (56.83 t);
  300 m 44.73 t, an upper bound (67.29 t, also an upper bound); the shortfalls from the
  sweep's re-run, sweep_1/sweep_index.csv `silo_cold_s1_st.dv_shortfall_mps`, Amendment 1]
- At the fixed exit speed 76.71 m/s the structural offload is no offload (stage 2 sized)
  (190.0 m/s of delta-v short of P_ref at x = 0; payload deficit not flown: no payload case
  at these settings), 11.42 t, 26.69 t and 32.03 t at 50, 100, 200 and 300 m (felt about
  7.0, 4.0, 2.5 and 2.0 g0); it rises with the stroke. [beside: the shortfall from the
  re-run's sweep_2/sweep_index.csv `silo_cold_200m_s1_st.dv_shortfall_mps`]
- Under CLAUDE.md's +/-10% arms the structural headline ranges from 8.55 to 15.07 t.
- Sized for its own full-load push, silo_cold carries 26.40 t to orbit, 342 kg above the
  pad's P_ref (central; physics high-mass end 23.97 t, -2,080 kg (two passes; residual
  estimate 0.137 kg)). [beside: both flown with the free kick; the central's run peaks at
  119.0 Pa rad, 1.59 times the pad's (`offload.runs` `peak_q_alpha`; derived ratio), so by
  the rule run A applies to its comparisons (its variants table labels silo_cold's uncharged
  +1,498.8 kg "an unthrottled/unconstrained upper bound: q-alpha above the baseline") the
  +342 kg is an upper bound, and so is the -2,080 kg (1.29 times); a payload case records no
  comparison flag, and a q-alpha-constrained kick would lower both by an amount not measured
  ("The payload form")]
- On the README-loads fork the central structure cancels most of the fork's uncharged
  offload: 9.16 t is left (25.5% of its 36.01 t). [beside, not read: 22.2% of SP1's 41.26 t]
- On the README-loads fork the central structure leaves 9.16 t of its uncharged 36.01 t
  (25.5%; the gate's 27.7%): the structure costs 26.84 t of offload against the gate's
  29.84 t.
  - C1, the cost: the structure's offload cost depends on the vehicle masses more than the
    calibration difference suggests. [10.05% apart against the 10% threshold: 3,000.2 kg
    against 2,984.3 kg, 16.0 kg past it; the two costs' summed resolution is about 11.9 kg
    (derived from section 3: about 3.4 + 2.55 kg per fork's cost, twice that for their
    difference); 16.0 kg is about 1.3 times that (derived: 16.0 / 11.9), so under section
    3's rule the margin is resolved, but narrowly]
  - C2, the share left: the share of the uncharged offload the structure leaves is nearly
    the same on both forks. [8.0% apart against 10%]
  - [beside, not read: dm at x* 5,967.3 kg on the fork against 6,305.2 kg on the gate, 5.4%
    apart (derived: (6,305.2 - 5,967.3) / 6,305.2); X/m_p1 2.32% on the fork's 395.7 t
    against 2.78% on the gate's 410.9 t]

Not fired: H1 (survives); H4 (cancels all at the central coefficients); O1's "survives
(outer)"; R's "keeps more than half" on every row, R's "cancels all" on every row but
silo_cold_s1_st_step, and R's "cancels most" on silo_cold_s1_st_step; C's "keeps more than
half" and "cancels all" (file C's central offloads, below half of its own U); HS's "less"
(and "the same within the resolution") for both hot starts; S1's "every exit speed swept
offloads" and "x* does not rise monotonically with the exit speed"; S2's "it does not rise
monotonically with the stroke"; C1's "the structure's offload cost is nearly the same on
both forks"; C2's "the share of the uncharged offload the structure leaves depends on the
vehicle masses more than the calibration difference suggests"; and no arm of A is named
(none ended no_offload or reference_failed, and every arm's decomposition closes). Both
fork tests fired the opposite way to their pre-registered estimates (section 7 said the
estimates do not decide them; "How each pre-registered reading came out").

File B's drive cases (run B, same caveats, at the central structure only: no physics band
and no +/-10% arm on file B): all nine linear-motor central cases cancel most of SP1's
uncharged offload, from 2.48 t (6.0%, lm_cmd_taper_s1_st) to 18.27 t (44.3%,
lm_cmd_hot_s1_st, a hot start favoured by the unmodelled exhaust), and neither of the two
drives that exit faster than silo_cold at x* on the same 100 m silo (lm_fixed,
lm_fixed_hot) keeps more once charged; every fixed sentence of part 2 that fired is under
"The drive cases", word for word.

## Caveats (read first)

- **What the headline assumes.** The structure file's central coefficients; an assumed
  real-drive rise time of 0.5 s at an axial frequency of 5 Hz (DLF = min(2, 1 + T/(pi
  t_r)) = 1.1273 on the increment over the resting load: n_peak 4.389 g0 against the
  plateau's 4.006 g0), which the constant_accel trajectory does not fly: it flies an instant
  step, whose row (DLF 2, n_peak 6.996 g0) ends at no offload. The rise time is a user
  decision (D-SP7-09), and with the axial period it is the axis survey 08 put first by
  leverage (its section 10, item 3); survey 08 recommended reporting constant_accel at its
  as-flown dynamic factor 2, and the design chose the assumed real-drive rise time for the
  headline instead, with the step row beside it (section 2(a)). The ramp a real drive needs
  over t_r is charged by closed form as a 0.31% higher net-acceleration plateau
  (`structure_ramp_cost_rel` 0.0030835: 29.511 against 29.420 m/s^2; the felt plateau
  4.006 g0 against the flown 3.996 g0, 0.23% higher, derived); zero existing margin
  (D-SP7-03: the stage-1 structure exactly meets the pad's own envelope, so the push gets no
  spare capacity; the margin multiplies the envelope's loads and pressures only, never the
  push's, docs/physics.md, so a margin is capacity the push can use, and the 10% and 25%
  margin rows keep more, 13.27 and 15.70 t against 11.42 t: zero is the adverse choice for
  the assist, not a missing safety factor); the push and the envelope are both sized at
  ultimate loads with FS_ult 1.40 (configs/structures/generic_f9_class_2d.yaml
  `factors.FS_ult`; 1.25 is listed there as a sizing-only alternative); the pad's own
  unthrottled flight at P_ref, quasi-static and without drag, as the envelope (D-SP7-15);
  the instant release flagged, not sized (D-SP7-10, D-SP7-19).
- **A first-order sizing, not a structural design.** Closed forms per station (200 per
  barrel): hoop, net compression against buckling (SP-8007 with the pressure increment on
  monocoque walls; Gerard rows and a plate-limited row on stiffened walls), a von Mises
  membrane check, the minimum gauge, domes, the LOX transfer tube's hoop, the interstage by
  a relation, the aft skirt and a ring frame between the carriage pads (D-SP7-14, D-SP7-17).
  Each station's increment is the positive part of the push's required wall over the pad
  envelope's, times a non-optimum factor; the ring frame is new hardware with no envelope
  credit. No FEM, no joints beyond what the non-optimum factors carry, no lateral loads, no
  fatigue (Limits).
- **The band's method and what lies outside it.** The physics band's ends are the extremes
  in dm that S2's screened search found over the 27 physics coefficients' ranges, sizing
  only, at SP1's headline push and at the design axes' central values (6,789 sizings; frozen
  at 4494fe1; the record's `sets.method`). They are the extremes the search found, not
  bounds: a one-coordinate move beyond an end adds at most 11.8 kg at the gate's physics
  low-mass end (the fork's largest 7.7 kg, at its outer high-mass end), and 43.6 kg on the
  charged dm1 + 5.478 dm2 at the outer high-mass end; at the step row the held check puts
  the physics low-mass set 223.2 kg above that row's one-coordinate low (the band's low end
  overstated, against the assist) and the high-mass set 67.3 kg below its one-coordinate
  high (understated, for the assist) (section 2(c); the phase file, section 11, step S2).
  Outside the band: the design axes (the dynamic factor's rise time and frequency, the four
  non-optimum factors, k_ts, the pad count, the margin, the envelope cap, the entry path,
  the sizing basis), which the layer-2 rows move one at a time and the outer envelope moves
  together; the plausibility rule's scaling of the low-mass end (below); and everything
  under "Limits". At any push other than the headline's (the hot starts, the 200 m silo, the
  sweep points) the band ends are the headline's sets placed at that push: sizing-only
  estimates, never flown (section 3; design 4.2.6).
- **The dominant terms.** At x* the central's 6,305.2 kg is 57.4% load entry (the aft skirt
  2,095.4 kg and the load ring 1,522.5 kg) and 35.3% stage-1 RP-1 barrel (2,222.7 kg); the
  stage-1 LOX barrel takes 25.1 kg ("Which elements and modes carry the mass"). Four
  coefficients sit at the dm-lowering end of their range or are the dm-lowering alternative
  at the central (section 8, registered for these caveats): eta_weld 1.00, F_tu 558.5 MPa
  (520 MPa, its other end: +136.0 kg), the Gerard row ring_common_z and 8 carriage pads.
  Each of the following single in-range moves alone gives no offload at the headline push
  (S2's sizing-only tornado and search D, first pass, the phase file's section 11;
  estimates, not solves): eta_weld 0.70 (dm +1,828.2 kg), the plate-limited Gerard row
  (+4,851.6 kg), 4 carriage pads, and a rise time at or below 0.1438 s (the range's 0.1 s
  end: dm 10,235.6 kg). On the thrust-structure row, k_ts at or above 0.3476 kg/kN (24%
  above its central 0.2805, inside its range 0.197-0.628) gives no offload (the same
  sizing-only estimate). Under the pre-registration's converged sizing both break-evens are
  already placed at no offload (sizing-only placements: equivalent dm 8,543.1 kg at
  0.1438 s and 8,617.1 kg at 0.3476 kg/kN against SP1's 8,488.6 kg zero crossing, itself
  extrapolated along the curve's last segment; section 8), so the converged break-evens lie
  slightly inside S2's. The tornado's other large swings: the aft skirt's length 2.0 /
  10.09 m (dm 4,558.7 / 7,177.8 kg) and the ring's height-to-width ratio 1.0 / 12.0
  (7,130.4 / 5,861.4 kg); every other physics coefficient moves dm by 330 kg or less.
- **The push-time RP-1 pressure** (design 4.10's third sizing-only check, beside the
  sweeps; flown only if it moves dm by more than 0.5 t). Measured at the headline push
  (section 6, item 6; sizing only, x = 41,262.908 kg, the pad's envelope at the central
  2.62 bar): the stage-1 RP-1 tank's MEOP raised to 4.00 bar for the push only moves dm by
  -93.3 kg, and to the range's full high end (its minimum-pressure fraction 0.93 too) by
  -148.7 kg; raised for the envelope too, by +116.5 kg. Every move is below 0.5 t, so no row
  was flown. A higher push-time pressure alone lowers dm, so leaving it out is conservative
  for the assist; raised for the envelope too, the MEOP runs the other way (+116.5 kg,
  against the assist): that is the MEOP's own row in S2's tornado, a physics coefficient
  whose range the band's search spans.
- **The plausibility rule fires.** At the central coefficients the model's envelope mass of
  the stage-1 tank elements is 1.76 times Heineman's relation, so the physics band's
  low-mass end is multiplied by 0.739 (D-SP7-33, applied as approved, D-SP7-41). The factor
  multiplies the case's whole dm, the load entry included, which the relation does not
  cover; its trigger is mostly the LOX barrel's MECO-buckling envelope, an element the push
  barely loads. Both ends are printed side by side: 28.57 t scaled, 23.68 t unscaled ("The
  plausibility check").
- **Calibration.** The gate vehicle (configs/vehicles/generic_f9_class_2d.yaml) carries
  26,054.4 kg to the reference orbit, +14.3% against the published 22,800 kg, outside the
  +/-10% band; the user accepted the miss on 2026-09-30 (docs/findings/CAL-f9-leo-2d.md).
  Every offload is a difference between runs of this vehicle model, not a Falcon 9 figure.
  File C (the README-loads fork, +8.33%, inside the band) is the one robustness row.
- **Sweep-optimized and unthrottled.** Both sides of every comparison fly the same
  restricted guidance family with gamma*, the kick angle and the LTG pair solved per run. No
  throttle: max-Q and q-alpha are upper bounds, and no max-Q limit constrains the offloaded
  runs. Every structural case of file A flies a max-Q below the pad's (the central 32,130.7
  against 37,191.4 Pa, -13.6%, derived: -5,060.7 / 37,191.4), where SP1's uncharged headline
  flew 3.35% above it. Max-Q falls at the tropopause (11,019 m) in every run; the structural
  central reaches it 8.8 s sooner after its release than the pad after liftoff (56.9 against
  65.8 s, derived) and slower, at Mach 1.42, against the pad's 1.53 and SP1's uncharged
  1.56 (metrics.json `offload.runs`, `max_q_time_s`, `max_q_mach`). Lower max-Q is not a
  load benefit the model can claim: neither max-Q nor q-alpha is constrained, and q-alpha is
  higher (next bullet).
- **Free kick.** No angle-of-attack aerodynamics. The central offloaded run kicks at the
  first lit instant, 0.5 s after release at 71.8 m/s, with a peak q-alpha of 140.9 Pa rad,
  1.89 times the pad's 74.7 (derived: 140.9 / 74.7; metrics.json `offload.runs`). Every
  offloaded structural run of file A peaks in q-alpha at its kick, 1.7 to 3.9 times the
  pad's (derived: 126.6 Pa rad on the 4.0 g0 cap row to 288.8 on silo_hot_full_s1_st); the
  hot starts' structural runs reach 288.8 and 268.5 Pa rad at release. Sweep points'
  offloaded runs are not written, but their full-load point runs are: at sweep 1's 200 and
  300 m they kick at the first lit instant at 103.6 and 127.9 m/s into a q-alpha of 574.1
  and 1,293.3 Pa rad, 7.7 and 17.3 times the pad's (the re-run's sweep_1/sweep_index.csv
  `speed_at_kick_mps`, `peak_q_alpha`; derived ratios; the values SP1's note quotes). The
  structural runs' values there are not written, and they likely peak above those full-load
  values (not measured): at a given exit speed the kick's q-alpha rises as the stack lifts
  off lighter (run A's `runs` and `offload.runs`: the 26 run records kicking at 71.8 m/s
  fall in liftoff-mass order within 1.5 Pa rad, from 45.3 Pa rad at 632.3 t to 226.9 at
  531.1 t). At 100 m the structural headline run, 6.6 t lighter than the full-load point
  run, peaks 1.08 times its 129.9 Pa rad (derived: 140.9 / 129.9), and the uncharged run,
  42.8 t lighter, 1.75 times (derived: 226.9 / 129.9); the 200 and 300 m structural runs
  lift off 27.8 and 41.6 t lighter than their point runs (derived: the point's
  `payload_delta_kg` + x* - dm). The four payload cases' runs also kick at the first lit
  instant at 71.8 m/s, into 55.2 to 119.0 Pa rad, 0.74 to 1.59 times the pad's (the central
  119.0, 1.59 times; `offload.runs`; derived ratios), so by the rule run A applies to its
  comparisons the central's +342 kg and the physics high-mass and step deficits are upper
  bounds ("The payload form").
- **Partly filled tanks.** The offloaded vehicle keeps every dry mass of the full-load
  vehicle and adds dm: an under-filled vehicle carrying a strengthening increment, not one
  redesigned around the smaller load (RQ7). The mixture ratio is kept; no ullage, residual
  or centre-of-gravity effect.
- **Drive.** Files A and C: a prescribed constant acceleration with no force or power
  limit, a massless carriage, a vented shaft and no model of the exhaust in the shaft
  (which favours the hot starts). File B: silo_cold's constant_accel push and a linear
  motor capped by F_max and P_max only (P_max a mechanical cap at the carriage; no
  thermal, current or voltage limit), flying its own 0.5 s rise, with a massless carriage
  except one 22 t lumped carriage, a vented shaft except one sealed shaft (a uniform
  adiabat), an instant release, and the same unmodelled exhaust ("The drive cases";
  "Limits").
- **The flags, with their numbers** (reported beside, never a gate; section 9; files A and
  C here, file B's under "The drive cases"). The release
  flag (`structure_release_unload`) fires on every structural case of both files, every
  sweep point, every payload case and all eight arms of the headline: at the central, a
  release swing of -4.389 g0 against the pad's MECO -5.195 g0 under the same single-mode
  instant step, and the stage-1 LOX bottom at -896 kPa absolute ("The release"); on the arms
  (run A's `offload.sensitivity[]` records) the same swing against their own pads' MECO
  -5.07 to -5.31 g0, and the stage-1 LOX bottom at -885 to -904 kPa absolute; on the payload
  cases -766 to -1,671 kPa absolute (the payload form's table). The payload-limit flag fires
  on every cold-start structural case, every sweep point, file C's central, all four payload
  cases and all eight arms, on the swing (-2.12 to -7.85 g0 against the payload's published
  -2.0 g0) and also on n_peak above +6.0 g0 for the step row, the outer high-mass end,
  sweep 2's 50 m point and the step and outer high-mass payload cases; the pad's own MECO
  swings the stack to -5.195 g0 under the same treatment, also beyond -2.0 g0, so the flag
  measures the step treatment as much as the push. It does not fire on the hot starts (swing
  -1.58 and -1.61 g0). The upper-stack flag fires on the step row (push 9.58 MN against the
  envelope's 7.10 MN), the outer high-mass end (9.65 against its capped envelope's 5.46 MN),
  the 4.0 g0 cap row (6.00 against 5.46 MN) and sweep 2's 50 m point (10.75 against
  7.10 MN), and on the step and outer high-mass payload cases; the 4.5 g0 cap row comes
  nearest without firing (5.99 against 6.15 MN). The 4.0 g0 cap row's flight check also
  fires: its own flight needs 2.34 kg more wall than the envelope it was sized to (threshold
  1 kg; sized, not charged). No arm carries the upper-stack flag or a flight-check
  exceedance (0.0 kg on each). Three payload cases carry `structure_payload_unconverged`
  (residual estimates 0.137, 23.0 and 0.277 kg against 0.025 kg; not blocking, section 9).
  The outer high-mass end's solve carries an informational search flag ("solved only after a
  warm retry from a converged neighbour at gamma* = 0.383972435 rad"); it is not a capped
  refine, a nonmonotone search or a mismatch.
- **What was known before the run.** The answer was not unknown: the pre-registration's
  sizing-only estimates placed the headline at 11.1 t, the band from no offload to 28.5 t,
  and the short strokes at no offload (section 2(e), section 7), and S0's central values and
  range ends were set after the planning probe had shown which coefficients matter (the
  disclosure quoted in section 2(b)). What was fixed in advance is the design around these
  numbers and how each result is read. File B's answer was largely placed before run B too
  (part 2, section 2): lm_cmd and lm_cmd_hot fly the ramped plateau that file A's
  rise_time rows charge (by construction), so they were expected to reproduce run A's
  silo_cold_s1_st and silo_hot_ramp_s1_st, and part 2's
  sizing-only estimates placed every case (part 2, section 7). Run B re-measured them
  with full solves and independent verifications.
- **The sweep's no-offload record: failed on the first sweep, fixed, re-run.** The first
  sweep (results/silo_structure_2d/20261016T171522Z, from 1b5f9d4) ended sweep 1's 25 and
  50 m points and sweep 2's 50 m point at no_offload, as estimated, but wrote no delta-v
  shortfall for them (no index column, no line in its summary), which section 9 calls a
  reporting defect to fix first. The user decided the fix (D-SP7-48); Amendment 1 of the
  pre-registration (74eb3c8) registered it and the sweep's re-run; step S3c (1e4c732,
  77e1691; reporting only, results_io.py and summary.py) appended `<case>.dv_shortfall_mps`
  to the index and the no-offload lines to the summary. The sweep was re-run from 2b343d7
  (results/silo_structure_2d/20261019T172327Z). Its git record reads 2b343d7f25eb, dirty
  true (by the session's account from the 13 untracked draft documents of this note, with no
  tracked file modified; the record holds only the flag, and the session's check before the
  start covered the code paths only, "Provenance"): a departure from the "clean commit" that
  Amendment 1 and D-SP7-48 name, accepted by the session, not by a user decision, and logged
  as deviation 45. It reproduces every pre-existing column of the first sweep's index cell
  for cell (657 cells, 0 differ), so the dirty flag reached no number, and records the three
  shortfalls: 60.2, 18.3 and 190.0 m/s, against section 7's estimates of about 66, 24 and
  215 m/s (62, 19 and 180 on the quadratic). Every sweep number here is the re-run's; the
  first sweep stays on record.

## Definition

- **Offload x** [kg]: stage-1 propellant removed from a full load, the mixture ratio kept;
  the tanks are partly filled and the liftoff mass falls by x (docs/physics.md, "Propellant
  offload at fixed payload").
- **Reference payload P_ref**: the full-load pad's payload capacity P* on the same vehicle,
  orbit (200 km circular, 28.5 deg, due east) and search budget (id a17a0160...a7df):
  26,054.396243494975 kg for file A, 24,700.013061881455 kg for file C. Each run's pad P*
  equals it to 0.0 kg (section 9).
- **x\***: the largest evaluated offload whose residual propellant m_res at insertion is >=
  0 when the assisted run flies P_ref, with gamma* re-optimised. Different vehicles carrying
  the same payload to the same orbit.
- **Modelled structural mass dm(x) = dm1 + dm2** (design 4.2; docs/physics.md, "Structural
  sizing of the push load (first order)"): the increment the push adds over the pad's own
  envelope, station by station, at the offloaded stack the solve flies. dm1 is the stage-1
  elements and the interstage (D-SP7-36), dm2 the stage-2 tanks, sized only where the push's
  load on the upper stack exceeds the pad envelope's (D-SP7-11). Sizing "flown": dm is
  re-sized at every x the solve evaluates, by a fixed point dm = S(push(m(x) + dm)) iterated
  to 1e-6 kg; sizing "full_load": once at x = 0. dm rides on the assisted run only; the pad
  keeps its vehicle (D-SP7-35).
- **An assumed penalty row** (SP1's +2, +4 and +8.1 t) adds an assumed stage-1 dry mass
  instead: an assumption, not a sized structure (D-SP1-04).
- **The structure's offload cost** U - X: the uncharged offload U of the same push less the
  structural x* X, both at the same P_ref.
- **Verification**: an independent payload search on the vehicle offloaded by x* and
  carrying dm(x*) must return P_ref within 1e-4 P_ref (2.605 kg for file A, 2.470 kg for
  file C), or the case is flagged and x* is a bound.
- **no_offload**: no offload x >= 0 keeps m_res >= 0 at P_ref. Such a case prints the
  solver's delta-v shortfall at x = 0 (`dv_shortfall_mps`) and, where a payload case at the
  same settings is registered, its payload deficit d = P_2* - P_ref, a full-load sizing
  (section 8).
- **Payload case** (design 4.4): silo_cold at its own P* with the structure sized for its
  full-load push, two passes (P_1* on dm sized at P_ref, P_2* on dm re-sized at P_1*), not
  iterated further; never read as propellant saved.
- **Pad control**: the same stage-1 solve on the pad, a consistency test of the solver.
- **The reading rules** (D-SP7-32, section 8): 50% of SP1's uncharged 41,262.9 kg is
  20,631.45 kg; "survives" if the physics band's adverse end keeps more than that, "cancels
  most" if the central x* is below it, "undecided" if the band straddles it or either end is
  no_offload, "cancels all" if the central is no_offload; the same tests on the bound rows.
  File C is read against its own uncharged x*. File B's fixed sentences (part 2, section 8)
  read each linear-motor central case against the same 20,631.45 kg (RB) and against file
  B's silo_cold_s1_st (LM), and the pairs within file B (HS, TS, CM, SS, TP, PL).
- **A linear-motor push** (file B; docs/physics.md, "Linear motor (SP7 step S4)"): the
  drive force rises over t_r 0.5 s to its plateau. Under the acceleration law the plateau is
  the command a_cmd (the net acceleration), capped by F_max and P_max / sdot. Under the
  force law it is F_max until the power limit P_max / sdot binds above the corner speed
  P_max / F_max. The push releases at the track end (`track_end`) or where its speed first
  reaches a set release speed (`target_speed`); "release position" is the distance along
  the 100 m stroke there. "Exit speed at x*" is the speed at release of the case's recorded
  run at x*, carrying its dm.

## Provenance

| command | results directory | git | contents |
|---|---|---|---|
| `run experiments/silo_structure_2d.yaml` (run A) | results/silo_structure_2d/20261016T171513Z | 1b5f9d46d31c, clean | pad; silo_cold, silo_cold_200m, silo_hot_full, silo_hot_ramp_on_track; 24 stage-1 cases (4 uncharged, SP1's 3 penalty rows, 17 structural); the stage-1 pad control; 4 structure payload cases; 8 sensitivity arms on the structural headline; the energy block |
| `sweep experiments/silo_structure_2d.yaml` (sweep A, first) | results/silo_structure_2d/20261016T171522Z | 1b5f9d46d31c, clean | the sweep's own pad; sweep 1 (stroke 25-300 m at 3 g0) and sweep 2 (stroke 50-300 m at 76.71 m/s), 9 points, an uncharged and a central structural stage-1 solve at each, each ok solve verified (6 of the 9 structural ones; the three no-offload points carry no verification); no shortfall column (the reporting defect); on record, superseded by the re-run for every sweep number |
| `sweep experiments/silo_structure_2d.yaml` (sweep A, re-run under Amendment 1) | results/silo_structure_2d/20261019T172327Z | 2b343d7f25eb, dirty true (below) | the same 9 points and solves, every pre-existing index column equal to the first sweep's cell for cell; adds `<case>.dv_shortfall_mps` and the summary's no-offload lines; the source of every sweep number here |
| `run experiments/silo_structure_2d_readme.yaml` (run C) | results/silo_structure_2d_readme/20261016T171529Z | 1b5f9d46d31c, clean | the README-loads fork: pad, silo_cold, the uncharged and the central structural stage-1 case, the stage-1 pad control |
| `run experiments/silo_drive_2d.yaml` (run B) | results/silo_drive_2d/20261103T231946Z | 642e11e3851d, clean | file B: pad; silo_cold and the nine linear-motor variants; 20 stage-1 cases (for each variant one uncharged and one central structural); the stage-1 pad control; SP1's energy block; no sweep, no sensitivity block, no arm, no payload case |

- Commits: the pre-registration and both experiment files at cbbd7bc; run A, the first sweep
  and run C from 1b5f9d4, its tracker commit, whose src/, configs/, experiments/, tests/,
  pyproject.toml and uv.lock equal cbbd7bc's (`git diff --quiet cbbd7bc 1b5f9d4 -- ...`
  exits 0). Every metrics.json of those three directories records git 1b5f9d46d31c, dirty
  false. Amendment 1 at 74eb3c8 (D-SP7-48); step S3c's code at 1e4c732 and 77e1691; the
  re-run from 2b343d7, the S3c tracker commit after them, whose src/ differs from 1b5f9d4's
  in src/launchsim/results_io.py and summary.py only (reporting: Amendment 1; `git diff
  --stat 1b5f9d4 2b343d7 -- src configs experiments pyproject.toml uv.lock` lists those two
  files; tests/ gained S3c's tests), a departure Amendment 1 registers (deviation 43 of the
  phase file). The re-run's git record reads 2b343d7f25eb, dirty true, and holds only that
  flag: `results_io.git_info` stores a boolean, counting tracked changes and untracked files
  outside results/ as dirty, so the record does not say which files made it so. By the
  session's own account (its draft of deviation 45), the only untracked files outside
  results/ at the start were the 13 draft files of this note under docs/findings/ (the
  note, its tables .md and .json and the ten PNGs) and no tracked file was modified; the one
  check it records, `git status --porcelain -- src configs experiments tests pyproject.toml
  uv.lock`, empty seconds before the start, covers the code paths only, so it shows that the
  code the re-run imported was 2b343d7's, not the state of the rest of the tree. That
  departs from the "clean commit" Amendment 1 and D-SP7-48 name for the re-run; the session
  accepted it rather than re-run a third time (not a user decision), and it is deviation 45
  of the phase file. The 657 reproduced cells (below) show it reached no number.
- Structure files, frozen at S2's commit 45e39d4 (D-SP7-31; `git diff --quiet 45e39d4 HEAD
  -- configs/structures` exits 0): configs/structures/generic_f9_class_2d.yaml sha256
  a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232 and
  configs/structures/generic_f9_class_2d_readme_loads.yaml sha256
  a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997. Both equal section 12's
  at HEAD, at 1b5f9d4 and at 45e39d4, and in all 65 digest records the three runs of
  2026-10-16 hold (run A's 51 and run C's 3 in metrics.json: the structure inputs, every
  structural case, payload case, arm and run record; their two top-level
  resolved_config.yaml files; and the first sweep's nine sweep-point resolved_config.yaml
  files; the checks script's check 7); the re-run's nine resolved_config.yaml files record
  the same file A digest.
- Numbers are copied from each directory's summary.md, metrics.json and the sweeps'
  sweep_index.csv (named where they appear); derived numbers say "derived" and show the
  arithmetic. Pre-registered estimates are always labelled so; none is a target.
- Nine of section 9's eleven blocking checks (all but the frozen sets and the convergence
  check, both in the next bullet) and Amendment 1's reproduction check are evaluated on
  run A, both sweep directories and run C by docs/findings/scripts/sp7_s7a_checks.py
  (read-only; committed at 9b91473 and first run there at 2026-10-19T18:43Z; re-run
  unchanged at a5b21b8 at 20:24:46Z, after the figures were redrawn; its output, all ten
  checks PASS, is docs/findings/RQ1-structural-2d-checks.txt, written by that re-run, whose
  header names HEAD a5b21b8). Its output
  reports: no run or comparison is bug_suspect ("No run and no comparison is bug_suspect."
  appears in each summary, the re-run's included, with no blocked-findings line; every
  decomposition status read is "explained"). Every pad's P* equals its P_ref to 0.0 kg (the
  run A, sweep and run C pads, and the six perturbed arm pads against SP1's arm P_ref; the
  two drive-efficiency arms use the nominal pad; all eight arms' P_ref equal SP1's to
  0.0 kg). Both stage-1 pad controls pass their consistency test (file A m_res(0)
  -0.00164 kg against a 1.618 kg bound; file C -0.00159 kg against 1.28 kg). Every
  reproduction is 0.0 kg off (the same bits): silo_cold_s1 41,262.90803733282 kg, the
  penalty rows 32,285.203295407457, 22,875.96053288855 and 1,980.4767886165673 kg,
  silo_hot_ramp_s1 46,013.43730748323 kg, silo_cold_200m_s1 41,262.97057414868 kg, file C's
  silo_cold_s1 36,006.44430169878 kg, and all nine uncharged sweep points equal SP1's sweep
  index to 12 significant digits. Every structural verification lies within 1e-4 P_ref
  (file A's offload cases +0.0009 to +0.0035 kg, file C's +0.0012 kg, the sweep points' up
  to +0.488 kg at sweep 1's 300 m point). `xv_dry_mass_delta_kg` equals dm1 + dm2 to
  7.3e-12 kg on all 18 structural cases. No `offload_nonmonotone`, capped gamma* refine or
  fired `structure_fixed_point_cap` is recorded (the flags as written; at most 10 sizings in
  any recorded case: the 52 `structure_fixed_point_cap` records (50 in run A's and 2 in run
  C's metrics.json, counted beside the output, which prints only the total); a sweep point
  records no count, only its fired flags, and none fired the cap). The
  three no-offload structural cases of file A carry their shortfall and deficit. The
  no-offload sweep points' shortfall check failed on the first sweep and passes on the
  re-run: sweep 1's 25 and 50 m points 60.2 and 18.3 m/s, sweep 2's 50 m point 190.0 m/s
  (`<case>.dv_shortfall_mps`), each with "payload deficit not flown" (no payload case at
  these settings; Caveats, "The sweep's no-offload record").
- Beside the script, read from the named records (not in its output): every recorded
  `run_checks` is ok (run A 34 and run C 5, in metrics.json `runs.<name>.run_checks` and
  `offload.runs.<name>.run_checks`; each sweep directory 10, the `metrics.run_checks` of its
  ten metrics.json files, the baseline's and the nine points'). In both sweeps' summary.md
  the bug_suspect line is followed by the M2 diagnostic lines (the re-run's lines 197 and
  198, after the bug_suspect line at 196: the M2 fails at sweep 1's 25 and 50 m points, and
  the gamma*-sensitivity line at the 50 m point only; KI-006 below). The largest
  cross-vehicle decomposition residual is 2.2e-9 m/s, against 1e-5 m/s: run A's stage-1
  dry mass -10% arm (`offload.sensitivity[].decomposition_residual_mps`, -2.16e-9 m/s); the
  cases' `offload.cases[].decomposition.xv_residual_mps` reach at most 8.4e-10 m/s in run
  A and 2.0e-11 m/s in run C. Both pad controls' m_res(0) equal SP1's to the bit
  (`offload.pad_controls[].m_res_kg`; file A's against SP1's run,
  results/silo_offload_2d/20261003T112934Z, file C's against SP1's README-loads bridge,
  results/silo_offload_2d_readme/20261003T112956Z). The 10 sizings are the outer high-mass
  end's, in its offload case and its payload case (the `structure_fixed_point_cap` record's
  `values.iterations`, against `max_iterations` 25). Outside the script, the other two
  checks of section 9: tests/test_structure_search.py::test_frozen_sets_reproduce passed for
  both files at the run's code (317.5 s and 290.0 s, each its own foreground command after
  the three runs ended), and the convergence check passes ("Convergence").
- Amendment 1's reproduction check: every pre-existing column of both sweeps'
  sweep_index.csv in the re-run, compared with the first sweep's by column name, cell by
  cell as written (%.12g): 365 cells (sweep 1, 5 rows) and 292 cells (sweep 2, 4 rows), 657
  in all, 0 differing. The new columns are each case's `dv_shortfall_mps` (empty for an ok
  solve). So every number the first sweep wrote is the re-run's too, including the
  reproduction of SP1's uncharged sweep points and the verifications above.
- **Run B** (file B). Part 2, file B, the rules script and their tests were committed at
  331891d (the registration commit). Run B ran from 642e11e, S6b's tracker commit, whose
  src/, configs/, experiments/, tests/, pyproject.toml and uv.lock equal 331891d's (`git
  diff --quiet 331891d 642e11e -- ...` exits 0). Its metrics.json records git 642e11e3851d,
  dirty false: 388 files, no FAILED.txt. Fingerprints at the run's end: metrics.json
  sha256 08278d414db0063e9c4dcf641ae9f5ddca91ce87229cc908a8bce29cbaf7b488; the sorted
  per-file sha256 list of the directory hashes to
  c67572aaca8832a5f703be8da498c952a656e67325f25813c2de2da30dc54f7d (`find DIR -type f |
  sort | xargs sha256sum | sha256sum` in Git Bash). Both equal at the checks' run (its
  provenance line) and at this note's writing. Files at 642e11e and at this note's HEAD:
  experiments/silo_drive_2d.yaml sha256
  7513d74bfa488125f9a14da091b0bfedb5e59516cb8ce27e21531cb0f5a68ee5;
  configs/structures/generic_f9_class_2d.yaml
  a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232 (part 1 and part 2,
  section 12; unchanged since 45e39d4, and named by all 22 of run B's digest records);
  configs/vehicles/generic_f9_class_2d.yaml
  a8ea5203da658b6d86d690ea26b784fa6004f2b990fe2f4b7f829c9a799e59a9 (part 2, section 12).
  The README-loads structure file (a850de94...) is not used by file B.
- **Run B's blocking checks.** The eleven checks of part 2, section 9, the registered
  expectations E1 and E2 and the fixed sentences of part 2, section 8 are evaluated by
  docs/findings/scripts/sp7_s7b_checks.py. It reads run B, run A's and SP1's directories
  for the cross-commit check and the convergence report, and it is read-only. It was
  committed at b291518 with the convergence script; that commit holds documents only
  (`git diff --quiet 642e11e b291518 -- src configs experiments pyproject.toml uv.lock
  tests` exits 0). It ran at b291518 on 2026-11-04 at 03:03:48Z, after the convergence
  check, and exited 0: "SUMMARY: PASS: all 11 checks pass". Its text and JSON output are
  committed unchanged, byte for byte, as docs/findings/RQ1-structural-2d-drive-checks.txt
  (sha256 d026442b19614eacb4ba5c4f9b6e14bc26091c14ae20cafac5be7fcaf9d8d673) and
  docs/findings/RQ1-structural-2d-drive-checks.json
  (7e11ce57018e8efc9233ca08f9b610c5f5dc8daa5925010ca11eb14a9462faa5). File B's numbers
  are copied from run B's summary.md and metrics.json (named where they appear); derived
  numbers say "derived".

## The headline table: SP1's assumed rows beside the modelled rows

File A at the headline push (3 g0 net, 100 m vented vertical stroke, exit 76.707 m/s, cold
start lit 0.5 s after release with SP1's 2 s ramp; P_ref 26,054.4 kg). % of 41.26 t: x* over
SP1's uncharged 41,262.9 kg; % of stage 1: x* over the 410.9 t stage-1 load. dm1 + dm2 at x*
(a no-offload row: at x = 0, where the solve ended). The pre-registered estimate is
section 7's coupled placement on SP1's penalty curve (sizing only, not a target), with its
dm at the estimated x in brackets; result - estimate is x* less the estimate, unrounded
where docs/findings/RQ1-structural-2d-tables.json holds it (the central and the band's
low-mass ends, `sweep_bands`), else as printed. Source: run A's summary.md (offload table,
Structure subsection) and metrics.json `offload.cases`, `offload.structure_payload_cases`.

| row | what it changes | status | x* [kg] | % of 41.26 t | % of stage 1 | dm1 + dm2 [kg] | pre-registered estimate x* [kg] (dm1 + dm2) | result - estimate [kg] | reading |
|---|---|---|---|---|---|---|---|---|---|
| silo_cold_s1 | uncharged (SP1's headline) | ok | 41,262.9 | 100.0% | 10.04% | 0 | SP1's 41,262.908, to reproduce | 0.0 (same bits) | the reference |
| silo_cold_s1_dry+2t | +2.0 t assumed stage-1 dry mass | ok | 32,285.2 | 78.2% | 7.86% | 2,000 + 0, assumed penalty, not sized structure | SP1's 32,285.203 | 0.0 | none: an assumed penalty |
| silo_cold_s1_dry+4t | +4.0 t assumed | ok | 22,876.0 | 55.4% | 5.57% | 4,000 + 0, assumed penalty, not sized structure | SP1's 22,875.961 | 0.0 | none: an assumed penalty |
| silo_cold_s1_dry+8.1t | +8.1 t assumed | ok | 1,980.5 | 4.8% | 0.48% | 8,100 + 0, assumed penalty, not sized structure | SP1's 1,980.477 | 0.0 | none: an assumed penalty |
| **silo_cold_s1_st** | none: **the headline** (central set, flown, rise_time 0.5 s / 5 Hz, aft_ring 8 pads, margin 0, no cap) | ok | **11,420.2** | **27.7%** | **2.78%** | 6,305.2 + 0 | 11,105.2 (6,309.6 + 0) | +315.0 | H2: cancels most |
| silo_cold_s1_st_phys_lo_scaled | physics_low_mass x 0.739 (the band's low-mass end under D-SP7-33) | ok | 28,570.8 | 69.2% | 6.95% | 2,801.2 + 0 | 28,514.4 (2,801.5 + 0) | +56.4 | H3 (band end) |
| silo_cold_s1_st_phys_lo | physics_low_mass, unscaled | ok | 23,676.6 | 57.4% | 5.76% | 3,833.6 + 0 | 23,658.2 (3,833.7 + 0) | +18.5 | H3 (unscaled end) |
| silo_cold_s1_st_phys_hi | physics_high_mass (the adverse end) | no_offload | no offload: 243.7 m/s short at x = 0; payload deficit -2,080.4 kg (two passes; residual estimate 0.137 kg) | n/a (no offload) | n/a (no offload) | 21,551.8 + 0 | no offload: about 291 m/s, -2,449 kg (241 m/s, -2,048 kg on the quadratic) | 47 m/s and 369 kg less short than the linear estimate | H3 (adverse end) |
| silo_cold_s1_st_outer_lo | outer_low_mass (margin 0.25, no cap; t_r 1.0 s, 10 Hz: DLF 1.03, n_peak 4.13 g0, the design axes' corners) | ok | 31,118.2 | 75.4% | 7.57% | 2,253.3 + 0 | 31,092.5 (2,253.5 + 0) | +25.7 | O1 |
| silo_cold_s1_st_outer_hi | outer_high_mass (margin 0, cap 4.0 g0; t_r 0.159 s, 2 Hz: DLF 2, n_peak 7.0 g0, the design axes' corners) | no_offload | no offload: 1,021.5 m/s short; payload deficit -7,804.3 kg (two passes; residual estimate 23.0 kg) | n/a (no offload) | n/a (no offload) | 58,536.8 + 1,362.1 | no offload: of order 800-1,400 m/s, -7 to -10 t | inside the estimated range | O1 |
| silo_cold_s1_st_qs | dynamic quasi_static (DLF 1) | ok | 15,023.5 | 36.4% | 3.66% | 5,595.3 + 0 | 14,728.3 (5,598.7 + 0) | +295.2 | R: cancels most |
| silo_cold_s1_st_step | dynamic step (DLF 2) | no_offload | no offload: 125.2 m/s short; payload deficit -1,086.9 kg (two passes; residual estimate 0.277 kg) | n/a (no offload) | n/a (no offload) | 13,178.1 + 319.8 | no offload: about 143 m/s, -1,231 kg (120 m/s, -1,041 kg) | 18 m/s and 144 kg less short than the linear estimate | R: cancels all |
| silo_cold_s1_st_full | sizing full_load (dm once at x = 0) | ok | 10,588.9 | 25.7% | 2.58% | 6,467.0 + 0 | 10,302.9 (6,467.0 + 0) | +286.0 | R: cancels most |
| silo_cold_s1_st_ts | entry through the thrust structure (k_ts 0.2805 kg/kN; break-even 0.3476 kg/kN, 24% above, sizing only; central moved after the probe from 0.306, which raised this row's estimate by about 2.4 t, section 2(b)) | ok | 5,973.2 | 14.5% | 1.45% | 7,352.2 + 0 | 5,769.7 (7,356.5 + 0) | +203.5 | R: cancels most |
| silo_cold_s1_st_m10 | existing margin 0.10 on the envelope (spare capacity the push can use) | ok | 13,266.0 | 32.1% | 3.23% | 5,943.3 + 0 | 12,951.9 (5,947.2 + 0) | +314.1 | R: cancels most |
| silo_cold_s1_st_m25 | existing margin 0.25 on the envelope | ok | 15,704.3 | 38.1% | 3.82% | 5,459.6 + 0 | 15,418.8 (5,463.2 + 0) | +285.5 | R: cancels most |
| silo_cold_s1_st_cap45 | envelope's stage-1 felt n capped at 4.5 g0 | ok | 10,483.3 | 25.4% | 2.55% | 6,487.5 + 0 | 10,173.4 (6,492.4 + 0) | +309.9 | R: cancels most |
| silo_cold_s1_st_cap40 | envelope's stage-1 felt n capped at 4.0 g0 | ok | 4,806.0 | 11.6% | 1.17% | 7,174.8 + 67.9 | 4,800.4 (7,174.9 + 67.9) | +5.6 | R: cancels most |

- SP1's four rows reproduce to the bit, and the modelled rows fall where section 8 expected
  against them: the central's 6.31 t between SP1's assumed +4 t and +8.1 t rows; the step
  row, the physics high-mass end and the outer high-mass end beyond the +8.1 t row (their
  equivalent dm1 + 5.478 dm2 at x = 0: 14.93, 21.55 and 66.00 t, derived, with w = 5.478
  section 7's estimate of a stage-2 kg's offload cost, against SP1's zero crossing near
  8.5 t, itself extrapolated along the curve's last segment).
- Every ok row verifies within +0.0006 to +0.0085 kg of P_ref, the structural rows within
  +0.0009 to +0.0035 kg (tolerance 2.605 kg), and every decomposition closes (residuals at
  most 8.4e-10 m/s, on the +4 t row; run A's Decomposition table).
- Every solved structural x* at the headline push lies above its estimate, as section 7's
  bias bullet expected (a chord between the curve's rows places x low): by 204-315 kg on the
  central and the design-axis rows (5.6 kg on the 4.0 g0 cap row) and by 18-56 kg on the
  band's low-mass ends and the outer low end. At the other pushes whose x0 differs from
  41.26 t the departures are larger (+1.1 to +5.6 t), and two of them run opposite to the
  bias section 7 named ("How each pre-registered reading came out", below its table); at
  sweep 2's 200 and 300 m points (x0 41.26 t, dm 3.20 and 2.06 t) they are smaller, +57.5
  and +6.2 kg (derived: the re-run's sweep_2/sweep_index.csv
  `silo_cold_200m_s1_st.offload_kg` less the tables .json estimates 26,628.9 and
  32,024.8 kg), in the chord's direction.
- At the central's 6.31 t the structure costs 29.84 t of offload, 4.73 kg of offload per kg
  of modelled mass (derived: 29,842.7 / 6,305.2), the order of SP1's penalty-curve slopes
  (4.49 to 5.10 kg/kg).

Figure: RQ1-structural-2d-derived_headline_rows.png (its footer's caveats, and the free-kick
q-alpha of the rows its footer's kick clause does not cover: "Figures").

Reported beside every number (section 9's list; never a gate): each structural row's
recorded run (at x*; a no-offload row's at x = 0) against the pad, from run A's metrics.json
`offload.cases[].vs_pad` (max-Q, felt g, interface force, electricity),
`structure_flight_exceedance_kg` and `offload.runs` (q-alpha, peak drive power); file C's
from run C's. Every row of file A flies 3.996 g0 on the track and needs a 160 m facility
(100 m + 60 m braking at 5 g0), except silo_cold_200m_s1_st (2.496 g0; 260 m). The release,
upper-stack and payload-limit flags with their numbers: Caveats, "The flags".

| row | max-Q [Pa] (pad 37,191.4) | peak q-alpha [Pa rad] (pad 74.7) | peak felt axial g in flight (pad 5.195) | interface force, flown peak [MN] | flight-check exceedance [kg] (threshold 1) | electricity of the push [kWh] | peak drive power [GW] |
|---|---|---|---|---|---|---|---|
| silo_cold_s1_st | 32,130.7 | 140.9 | 5.000 | 22.23 | 0 | 1,235.1 | 1.705 |
| silo_cold_s1_st_phys_lo_scaled | 35,570.6 | 186.5 | 5.107 | 21.42 | 0 | 1,190.1 | 1.643 |
| silo_cold_s1_st_phys_lo | 34,541.3 | 172.5 | 5.075 | 21.65 | 0 | 1,203.0 | 1.661 |
| silo_cold_s1_st_phys_hi (x = 0) | 28,045.1 | 92.4 | 4.584 | 23.28 | 0 | 1,293.1 | 1.785 |
| silo_cold_s1_st_outer_lo | 36,122.4 | 194.1 | 5.124 | 21.30 | 0 | 1,183.4 | 1.634 |
| silo_cold_s1_st_outer_hi (x = 0) | 23,113.9 | 45.3 | 3.790 | 24.78 | 0 | 1,376.6 | 1.901 |
| silo_cold_s1_st_qs | 32,815.5 | 149.7 | 5.022 | 22.06 | 0 | 1,225.7 | 1.692 |
| silo_cold_s1_st_step (x = 0) | 29,267.7 | 106.2 | 4.795 | 22.96 | 0 | 1,275.6 | 1.761 |
| silo_cold_s1_st_full | 31,975.4 | 139.0 | 4.996 | 22.27 | 0 | 1,237.2 | 1.708 |
| silo_cold_s1_st_ts | 31,131.1 | 128.5 | 4.969 | 22.49 | 0 | 1,249.2 | 1.725 |
| silo_cold_s1_st_m10 | 32,479.1 | 145.4 | 5.011 | 22.14 | 0 | 1,230.3 | 1.699 |
| silo_cold_s1_st_m25 | 32,947.1 | 151.4 | 5.026 | 22.03 | 0 | 1,223.9 | 1.690 |
| silo_cold_s1_st_cap45 | 31,955.7 | 138.7 | 4.995 | 22.28 | 0 | 1,237.5 | 1.709 |
| silo_cold_s1_st_cap40 | 30,977.4 | 126.6 | 4.973 | 22.53 | 2.34 (fires; sized, not charged) | 1,251.5 | 1.728 |
| silo_hot_full_s1_st | 34,494.7 | 288.8 | 5.036 | 14.28 | 0 | 783.1 | 1.074 |
| silo_hot_ramp_s1_st | 33,445.8 | 268.5 | 5.003 | 21.96 | 0 | 988.6 | 1.093 |
| silo_cold_200m_s1_st | 35,169.6 | 181.0 | 5.095 | 13.44 | 0 | 1,493.1 | 1.031 |
| file C's silo_cold_s1_st (its pad: 42,732.6 Pa; 105.2 Pa rad; 5.638 g0) | 37,082.8 | 207.8 | 5.421 | 21.21 | 0 | 1,178.5 | 1.627 |

The flown interface force is the trajectory's; the sizing's F_peak (with the dynamic factor;
24.41 MN on the central) is in the tables below. The sweep points' values are beside their
tables (their structural runs' felt g, interface force and q-alpha are not in the sweep's
records: a sweep point's offloaded runs are not written; its full-load run's q-alpha is).

The same at file A's other pushes (central structure; % of own: x* over the same push's
uncharged x* in this run; source as above):

| row | uncharged x0 [kg] | x* [kg] | % of 41.26 t | % of own | % of stage 1 | dm1 + dm2 [kg] | F_peak [MN] | pre-registered estimate [kg] | result - estimate [kg] | reading |
|---|---|---|---|---|---|---|---|---|---|---|
| silo_hot_full_s1_st | 38,980.4 (silo_hot_full_s1; estimated 39,506) | 16,336.3 | 39.6% | 41.9% | 3.98% | 5,134.2 + 0 | 16.43 | 15,258.5 on the estimated x0 | +1,077.8 | R: cancels most; HS |
| silo_hot_ramp_s1_st | 46,013.4 (silo_hot_ramp_s1, SP1's reproduced) | 18,273.9 | 44.3% | 39.7% | 4.45% | 6,210.0 + 0 | 24.12 | 16,218.5 | +2,055.5 | R: cancels most; HS |
| silo_cold_200m_s1_st | 41,263.0 (silo_cold_200m_s1, SP1's reproduced) | 26,686.4 | 64.7% | 64.7% | 6.49% | 3,201.8 + 0 | 14.47 | 26,628.9 | +57.5 | read under S2 (260 m facility, 2.50 g0 felt) |

Re-placed on the solved x0 (38,980.4 kg) by the same method, silo_hot_full_s1_st's estimate
is 14,690.1 kg, 1,646.2 kg below the solve (docs/findings/RQ1-structural-2d-tables.md,
section 7).

File C, the README-loads fork (its own pad, P_ref 24,700.0 kg; read against its own
uncharged x*, never SP1's 41.26 t; run C's summary.md and metrics.json `offload.cases`):

| quantity | silo_cold_s1 (uncharged) | silo_cold_s1_st (central) |
|---|---|---|
| status; x* | ok; 36,006.4 kg (SP1's bridge reproduced, 0.0 kg) | ok; 9,164.0 kg |
| % of its own uncharged x*; % of SP1's 41.26 t (not read); % of stage 1 (395.7 t) | 100%; 87.3%; 9.10% | 25.5%; 22.2%; 2.32% |
| the structure's offload cost U - X | | 26,842.4 kg (the gate's 29,842.7 kg) |
| dm1 + dm2 at x* (at x = 0) | 0 | 5,967.3 + 0 kg (6,094.3 kg) |
| of which the load entry (skirt + ring) / the RP-1 barrel | | 3,515.6 / 2,026.1 kg |
| sizing: n_peak; F_peak | | 4.389 g0; 23.30 MN |
| verification P* - P_ref (tolerance 2.470 kg) | +0.0040 kg | +0.0012 kg |
| decomposition; offload / screening (14,247 kg) | explained; 2.527 | explained (residual 3.9e-12 m/s); 0.643 |
| max-Q (the fork's pad: 42,732.6 Pa) | 43,923.3 Pa | 37,082.8 Pa |
| flags | none | release (swing -4.389 g0 against the fork's MECO -5.638 g0; stage-1 LOX bottom -859 kPa absolute; stage 2's LOX column at the fork's MECO -216 kPa gauge), payload limit |
| pre-registered estimate | SP1's 36,006.444 kg | 7,475 kg (20.8% of 36.0 t; level-matched 6,710 kg), the gate's slope shifted to the fork's x0; result +1,689 kg (derived: 9,164.0 - 7,475), +2,454 kg on the level-matched estimate (derived: 9,164.0 - 6,710): opposite to the shift bias section 7 named for x0 below 41.26 t (below the readings table) |

The fork's pad control passes (m_res(0) -0.00159 kg, SP1's to the bit). The fork carries the
plausibility rule's trigger too (M_model / R 1.700, factor 0.765, its stage-1 LOX barrel
70.8% of M_model; "The plausibility check"), but no band case was flown on it.

The headline case beside SP1's uncharged headline and the pad (all three in run A, at P_ref;
run A's summary.md offload table and Structure subsection, metrics.json `offload.runs`):

| quantity | silo_cold_s1_st (structural) | silo_cold_s1 (uncharged) | pad |
|---|---|---|---|
| stage-1 offload x* | 11,420.2 kg (2.78% of stage 1) | 41,262.9 kg (10.04%) | |
| modelled structural mass at x* (dm1 + dm2; at x = 0) | 6,305.2 kg (6,467.0 kg) | 0 | |
| independent verification: P* - P_ref | +0.0014 kg (tolerance 2.605 kg): passed | +0.0085 kg | |
| ideal-screening offload at 76.7 m/s (14,976.6 kg): offload / screening | 0.763 | 2.755 | |
| cross-vehicle decomposition: D_id(pad) - D_id(case) | 144.217 m/s, residual -2.8e-11 m/s | 228.204 m/s, residual 4.5e-12 m/s | |
| of which release speed / gravity + steering | 76.707 / 35.965 m/s | 76.707 / 124.710 m/s | |
| liftoff mass | 567,239 kg | 531,091 kg | 572,354 kg |
| MECO after release | 149.595 s | 138.531 s | 151.328 s |
| max-Q (unthrottled) | 32,130.7 Pa | 38,438.5 Pa | 37,191.4 Pa |
| peak q-alpha (unconstrained) | 140.9 Pa rad at the kick | 226.9 Pa rad | 74.7 Pa rad |
| gravity / drag / steering / back-pressure loss | 1,450.8 / 22.9 / 94.2 / 49.5 m/s | 1,367.2 / 26.9 / 89.1 / 49.9 m/s | 1,492.0 / 26.0 / 89.0 / 63.1 m/s |
| peak felt axial g in flight | 5.000 g0 | 5.195 g0 | 5.195 g0 |
| peak felt g on the track (flown); the sizing's n_q / DLF / n_peak | 3.996 g0; 4.006 g0 / 1.1273 / 4.389 g0 | 3.996 g0 | |
| interface force, peak (flown); the sizing's F_peak | 22.23 MN; 24.41 MN | 20.81 MN | |
| peak track-normal g | 0 (a vertical shaft) | 0 | |
| facility length incl. braking | 160 m (100 m + 60 m at 5 g0) | 160 m | |
| electricity of the push; peak drive power | 1,235.07 kWh; 1.705 GW | 1,156.36 kWh; 1.597 GW | |
| RP-1 removed; its combustion heat / electricity (not an efficiency claim) | 3,432.5 kg; 33.2 | 12,402.0 kg; 128.2 | |
| flags | structure_release_unload, structure_payload_limit | none | |

With the structure charged, the decomposition's gravity + steering term falls from 124.7 to
36.0 m/s while the release speed's 76.7 m/s stays: the structural stack lifts off only 5.1 t
lighter than the pad (derived: 572,354 - 567,239 kg), against 41.3 t for SP1's uncharged
one. That is a reading of two decompositions, not a split: no paired pad was flown here. The
structural headline no longer beats the ideal-screening estimate at its release speed (0.763
of it; file C's central 0.643 of 14.25 t). CLAUDE.md's rule asks that a beat be explained;
here there is none to explain, and the decomposition closes.

## Which elements and modes carry the mass

Elements of the modelled mass at each row's x* (a no-offload row at x = 0), kg (run A's
metrics.json `offload.cases[...].structure_elements`; the central's modes from its
summary.md "Pad envelope per element" table and docs/findings/RQ1-structural-2d-tables.md,
section 5, a re-sizing at the solved x* that equals the recorded elements to 0.0 kg):

| element | central (x* 11.42 t) | phys_lo scaled (28.57 t) | phys_lo (23.68 t) | phys_hi (x = 0) | step (x = 0) | ts (5.97 t) | cap40 (4.81 t) | outer_hi (x = 0) |
|---|---|---|---|---|---|---|---|---|
| stage-1 aft skirt | 2,095.4 | 366.9 | 503.1 | 9,112.1 | 3,340.3 | 0 | 2,123.8 | 20,355.0 |
| stage-1 load ring | 1,522.5 | 1,036.7 | 1,414.7 | 3,088.3 | 2,122.8 | 0 | 1,536.0 | 11,944.4 |
| stage-1 thrust structure | 0 | 0 | 0 | 0 | 0 | 4,618.9 | 0 | 0 |
| stage-1 RP-1 aft dome | 129.8 | 0 | 0 | 199.8 | 252.8 | 132.2 | 132.7 | 461.4 |
| stage-1 RP-1 barrel | 2,222.7 | 1,298.5 | 1,778.3 | 5,369.4 | 4,195.0 | 2,250.6 | 2,359.7 | 13,474.9 |
| stage-1 common dome | 298.3 | 99.1 | 137.5 | 451.0 | 576.2 | 303.8 | 305.0 | 1,041.7 |
| stage-1 LOX barrel | 25.1 | 0 | 0 | 2,945.8 | 2,344.8 | 33.3 | 650.0 | 9,420.8 |
| stage-1 transfer tube | 11.5 | 0 | 0 | 385.5 | 161.9 | 13.4 | 13.8 | 923.2 |
| interstage (charged to stage 1) | 0 | 0 | 0 | 0 | 184.2 | 0 | 53.8 | 915.3 |
| stage-2 tanks (dm2) | 0 | 0 | 0 | 0 | 319.8 | 0 | 67.9 | 1,362.1 |
| dm1 + dm2 | 6,305.2 | 2,801.2 | 3,833.6 | 21,551.8 | 13,498.0 | 7,352.2 | 7,242.7 | 59,898.9 |
| governing element and modes (push / envelope), envelope load case | RP-1 barrel, ring_common_z / ring_common_z, the pad's MECO | RP-1 barrel, ring_common_z / ring_common_z, the pad's MECO | RP-1 barrel, the same | aft skirt, plate_limited / plate_limited, the pad's hold-down (t = -2 s) | RP-1 barrel, combined / ring_common_z, the pad's MECO | thrust structure, its relation | RP-1 barrel, ring_common_z / ring_common_z, the capped envelope (t = 133.45 s) | aft skirt, plate_limited / plate_limited, the pad's hold-down |

- **At the central, the load entry and the RP-1 barrel carry 93% of the mass.** The aft
  skirt (2,095.4 kg, 33.2%) and the RP-1 barrel (2,222.7 kg, 35.3%) are sized by
  stiffened-panel axial buckling (the Gerard ring + common Z row) in the push and in the
  envelope; the skirt's envelope is the pad's hold-down at t = -2 s and the barrel's the
  pad's MECO. The load ring (1,522.5 kg, 24.1%) is new hardware sized in ring bending with
  no envelope credit. The common dome (298.3 kg) and the RP-1 aft dome (129.8 kg) are
  membrane-sized. The LOX barrel adds only 25.1 kg (combined stress in the push against a
  monocoque-buckling envelope), the tube 11.5 kg (hoop). Stage 2, the interstage, the thrust
  structure and both forward domes take nothing: the push's upper-stack load (5.99 MN) stays
  inside the envelope's (7.10 MN). Figure: RQ1-structural-2d-derived_elements.png.
- **The rows move different elements.** The step push (DLF 2, n_peak 6.996 g0) raises every
  station and adds the LOX barrel (2,344.8 kg), the interstage and stage 2. The
  thrust-structure row replaces the skirt and ring (3,617.8 kg at the central's x*) by a
  4,618.9 kg thrust-structure increment. The 4.0 g0 envelope cap lowers the envelope below
  the push's 4.389 g0, so the LOX barrel (650.0 kg) and the upper stack (stage 2 67.9 kg,
  the interstage 53.8 kg) are sized. The physics high-mass end is governed by the
  plate-limited row at the skirt (eta_weld 0.70, a 10.09 m skirt and a ring h/b of 1.0 are
  among its coefficients; the record's `sets.physics_high_mass.values`); its LOX barrel
  takes 2,945.8 kg. The structure figures of the central, step, phys_hi and ts rows and of
  file C's central are listed under "Figures".
- **Sizing only against the felt load** (docs/findings/RQ1-structural-2d-tables.md,
  sections 2 to 4, by docs/findings/scripts/sp7_structure_tables.py; no trajectory flown
  except file A's pad; the central structure re-pushed at each felt load n from 1.2 to
  7.0 g0 at the fixed exit speed 76.707 m/s, at SP1's headline offload, which understates
  dm, and at x = 0, the adverse bound). Some mass is charged at every push tried, at any
  felt load: the load ring takes 543.1 kg already at 0.9975 g0 (571 kg at x = 0), and the
  aft skirt is charged from 1.065 g0 at 41.26 t and at every push at x = 0. The other
  elements' break-even felt loads (at 41.26 t; at x = 0 in brackets; the stroke at 76.7 m/s
  in metres): the common dome 1.438 g0, 679 m (1.313, 947 m); the RP-1 aft dome 1.488, 611 m
  (1.362, 821 m); the RP-1 barrel 1.768, 389 m (1.658, 454 m); the LOX barrel 3.953, 101.5 m
  (3.620, 114.3 m); the transfer tube 3.977, 100.7 m (3.755, 108.7 m); the upper stack (the
  interstage and stage 2) 4.704, 80.9 m at both. Never charged anywhere in the 1.2 to 7.0 g0
  range: the thrust structure (not in the load path on entry aft_ring), both forward domes
  and stage 2's transfer tube. Total dm at 4.0 g0 is 5,908.3 kg at 41.26 t and 6,474.5 kg at
  x = 0; at 7.0 g0, 14,236.0 + 507.0 kg and 15,554.5 + 507.0 kg. Figure:
  RQ1-structural-2d-derived_dm_vs_felt_load.png.

## The plausibility check

D-SP7-33's rule compares the model's envelope mass of the stage-1 tank elements (M_model,
the non-optimum factors included) with Heineman's tank relation R within +/-30%; above 1.3 R
the physics band's low-mass end is multiplied by 1.3 R / M_model, mechanically. It is a
calibration check, not a validation. The user kept it as approved, with both ends printed
side by side and the trigger stated (D-SP7-40, D-SP7-41). Run A's and run C's summary.md,
"Plausibility" tables and their trigger lines:

| quantity | file A (gate) | file C (fork) |
|---|---|---|
| M_model, the stage-1 tank elements' envelope mass | 10,621.8 kg (LOX barrel 7,541.9; RP-1 barrel 2,588.8; forward, common and RP-1 aft domes 157.6, 175.8 and 157.6) | 9,977.1 kg (LOX barrel 7,059.7; RP-1 barrel 2,424.3; domes 157.6, 177.8 and 157.6) |
| R, Heineman's relation on the combined tank volume; its band 0.7-1.3 R | 6,038.35 kg; 4,226.8-7,849.9 kg | 5,870.03 kg; 4,109.0-7,631.0 kg |
| M_model / R | 1.759 | 1.700 |
| the low-mass end's factor 1.3 R / M_model (the high-mass end's: 1) | 0.739034 | 0.764855 (no band case flown on file C) |
| trigger: the element with the largest share of M_model | stage-1 LOX barrel, 71.0%, monocoque-governed at the pad's MECO (t = 151.3284 s, z 20.91 m) | stage-1 LOX barrel, 70.8%, monocoque at the fork's pad MECO (t = 145.6935 s) |
| that element's own push increment in the central case at x* | 25.1 kg (0.40% of dm) | 15.2 kg |
| printed beside (not read): Akin's tank fractions; the interstage relation; k_ts T_max; stage 1 less its engines | 4,903.0; 934.4; 2,307.6; 17,970 kg | 4,721.6; 934.4; 2,307.6; 21,370 kg |

The physics band's low-mass end, scaled and unscaled side by side (run A; solved cases):

| quantity | silo_cold_s1_st_phys_lo_scaled (x 0.739) | silo_cold_s1_st_phys_lo (unscaled) |
|---|---|---|
| x* (% of 41.26 t) | 28,570.8 kg (69.2%) | 23,676.6 kg (57.4%) |
| dm1 + dm2 at x* | 2,801.2 kg | 3,833.6 kg |
| of which the load entry (aft skirt + ring) | 1,403.6 kg (50.1%, derived: 1,403.6 / 2,801.2) | 1,917.8 kg (50.0%, derived: 1,917.8 / 3,833.6) |
| of which the RP-1 barrel / common dome | 1,298.5 / 99.1 kg | 1,778.3 / 137.5 kg |
| of which the stage-1 LOX barrel | 0 | 0 |
| verification P* - P_ref | +0.0034 kg | +0.0031 kg |

Read with its trigger: the rule fires because the model's MECO-buckling envelope of the LOX
barrel is heavy (71% of M_model), carrying nof_barrel on a monocoque increment that already
holds its buckling material (a double count the source note flags, its section 4), not
because the push's mass is out of line: neither low-mass case charges the LOX barrel
anything. The factor still multiplies the whole dm, the load entry included (half of it),
which the Heineman relation does not cover. That cut puts the scaled end 4.89 t of offload
above the unscaled one (derived: 28,570.8 - 23,676.6 kg). The scaled end is the band's
low-mass end for the readings (section 8); the unscaled one is printed beside, and both H3
sentences are quoted.

## The exit-speed axis: sweep 1, "the lowest exit speed that still offloads"

Sweep 1 runs silo_cold's 3 g0 push over strokes of 25 to 300 m and solves at every point the
uncharged case and the central structural case, each against the experiment pad's P_ref,
each ok solve verified (section 5; the two no-offload points carry no verification). It is
the direct test of "every m/s of assist helps" with the structure charged. Source: the
sweep's re-run, results/silo_structure_2d/20261019T172327Z/sweep_1/sweep_index.csv
(`silo_cold_s1.offload_kg`, `silo_cold_s1_st.status`, `.offload_kg`, `.dv_shortfall_mps`,
`.structure_dm_kg`, `.structure_dm_stage2_kg`, `.structure_n_peak_g`, `.structure_F_peak_N`,
`.verification_delta_kg`, `.max_q_pa`, `.electrical_energy_J`, `facility_length_m`, and the
full-load point run's `drive_power_peak_W`, `peak_q_alpha` and `speed_at_kick_mps`), whose
every pre-existing column equals the first sweep's
(results/silo_structure_2d/20261016T171522Z) cell for cell (Amendment 1); the pre-registered
estimates from section 7.

| stroke | exit speed | uncharged x0 (SP1's, reproduced) | structural status | structural x* (% of 41.26 t; % of own x0) | dm1 + dm2 at x* (no offload: at x = 0) | n_peak; F_peak | verification P* - P_ref | max-Q of the structural run (pad 37,191.4 Pa) | facility | electricity of the structural run | peak drive power (full-load point run) | peak q-alpha of the full-load point run (its kick speed; pad 74.7 Pa rad) | pre-registered estimate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 m | 38.35 m/s | 18,765.1 kg | no_offload | no offload: 60.2 m/s of delta-v short of P_ref at x = 0; payload deficit not flown (no payload case at these settings) | 6,526.5 + 0 kg | 4.421 g0; 25.10 MN | n/a | 33,133.7 Pa (at x = 0) | 40 m | 315.1 kWh (at x = 0) | 0.86 GW | 58.9 Pa rad (50.0 m/s, after the vertical rise) | no offload (about 66 m/s short, P* about 580 kg below P_ref; 62 m/s and 545 kg on the quadratic) |
| 50 m | 54.24 m/s | 28,653.6 kg | no_offload | no offload: 18.3 m/s short at x = 0; payload deficit not flown | 6,486.6 + 0 kg | 4.399 g0; 24.97 MN | n/a | 31,822.0 Pa (at x = 0) | 80 m | 630.2 kWh (at x = 0) | 1.22 GW | 49.4 Pa rad (50.0 m/s, after the vertical rise) | no offload (about 24 m/s, 210 kg; 19 m/s, 171 kg) |
| 100 m | 76.71 m/s | 41,262.9 kg | ok | 11,420.2 kg (27.7%; 27.7%) | 6,305.2 + 0 kg | 4.389 g0; 24.41 MN | +0.0014 kg | 32,130.7 Pa | 160 m | 1,235.1 kWh | 1.73 GW | 129.9 Pa rad, 1.74 times the pad's (71.8 m/s) | 11,105.2 kg |
| 200 m | 108.48 m/s | 56,827.2 kg | ok | 31,618.3 kg (76.6%; 55.6%) | 6,020.4 + 0 kg | 4.384 g0; 23.50 MN | +0.0019 kg | 34,195.3 Pa | 320 m | 2,380.9 kWh | 2.44 GW | 574.1 Pa rad, 7.7 times the pad's (103.6 m/s) | 27,888.9 kg |
| 300 m | 132.86 m/s | 67,285.8 kg | ok | 44,727.9 kg (108.4%; 66.5%): unconstrained kick, an upper bound | 5,846.1 + 0 kg | 4.382 g0; 22.92 MN | +0.488 kg | 36,117.3 Pa | 480 m | 3,484.6 kWh | 2.99 GW | 1,293.3 Pa rad, 17.3 times the pad's (127.9 m/s, unconstrained) | 39,120.9 kg |

(Electricity: the structural run's `electrical_energy_J` over 3.6e6, derived; at a
no-offload point it is the recorded run at x = 0. The flown felt load on the track is
3.996 g0 at every point; the sizing's DLF is 1.1273 throughout. Peak drive power and peak
q-alpha are the point's full-load run's (`drive_power_peak_W`, `peak_q_alpha`; the ratios to
the pad's 74.7 Pa rad derived); the sweep records no peak power, flight felt g, flown
interface force or q-alpha for a structural run. At 100 m the structural run's q-alpha
(run A, 140.9 Pa rad) is 1.08 times the point run's (derived: 140.9 / 129.9); it lifts off
6.6 t lighter than the point run, while the 200 and 300 m structural runs lift off 27.8 and
41.6 t lighter than theirs, and q-alpha rises as the stack lifts off lighter (at 100 m the
uncharged run, 42.8 t lighter, peaks 1.75 times), so theirs likely peak above the values in
the table (not measured; Caveats, "Free kick"). Every structural run's max-Q lies below the
pad's; every uncharged offload run's lies above it (37,264.5 to 41,845.8 Pa,
`silo_cold_s1.max_q_pa`).)

- **Below 76.71 m/s the structure cancels the offload; the sweep does not resolve the
  crossing between 54.24 and 76.71 m/s.** At 25 and 50 m (38.35 and 54.24 m/s) the
  full-load push carrying its dm falls 60.2 and 18.3 m/s of delta-v short of P_ref at
  x = 0 (payload deficit not flown: no payload case at these settings). The push still feels
  about 4.0 g0 (sizing n_peak 4.42 and 4.40 g0), so it needs nearly the same structure as at
  100 m (6.53 and 6.49 t at x = 0, against 6.47 t at x = 0 for the 100 m push), while the
  uncharged offload it would buy is smaller (18.77 and 28.65 t): the structure's cost
  exceeds the whole uncharged offload there. The shortfall falls from 60.2 m/s at 38.35 m/s
  to 18.3 m/s at 54.24 m/s, so the extra speed helped but did not pay for the structure.
  Both shortfalls lie below section 7's linear estimates (about 66 and 24 m/s) and within
  2 m/s of its quadratic ones (62 and 19 m/s). These two points rise vertically before the
  kick (SP1's regime change: the coast slows below the 50 m/s kick speed before ignition).
- **Above it x* rises with the exit speed**: 11.42, 31.62 and 44.73 t, by 636 kg per m/s
  from 100 to 200 m and 538 kg per m/s from 200 to 300 m (derived from the table), more than
  the uncharged sweep's 490 and 429 kg per m/s over the same steps (derived): the structural
  cost falls with the exit speed (U - X 29.84, 25.21 and 22.56 t, derived), mostly because
  each kg of structure costs less offload at the higher offload levels (4.73, 4.19 and
  3.86 kg per kg, derived: U - X over dm), and partly because the lighter stack needs less
  structure for the same felt load (dm 6.31, 6.02 and 5.85 t): at the 100 m point's
  4.73 kg/kg the 200 m point's 6.02 t would cost 28.5 t, so the lighter dm accounts for
  about 1.3 t of the 4.6 t fall from 100 to 200 m (derived). The 300 m point kicks above
  120 m/s, an upper bound (SP1), and verifies to +0.488 kg (inside 2.605 kg). The faster
  exits come with a much harder kick: the 200 and 300 m points' full-load runs kick at the
  first lit instant at 103.6 and 127.9 m/s into a q-alpha of 574.1 and 1,293.3 Pa rad, 7.7
  and 17.3 times the pad's (`peak_q_alpha`, `speed_at_kick_mps`; derived ratios), against
  129.9 Pa rad (1.74 times) at 100 m. Their structural runs' q-alpha is not written and
  likely peaks higher still (not measured): they lift off 27.8 and 41.6 t lighter than
  these point runs (derived), and at 100 m q-alpha rises from 1.08 times the point run's
  for the structural headline (6.6 t lighter; derived: 140.9 / 129.9) to 1.75 times for the
  uncharged run (42.8 t lighter). Nothing in the model constrains q-alpha or charges a
  structure for it.
- **Every point flags the release and the payload limit** (swing -4.38 to -4.42 g0 against
  the payload's -2.0 g0 and the pad's MECO -5.195 g0; stage-1 LOX bottom -799 to -937 kPa
  absolute; the re-run's summary.md, "Offload flags at each point"); no point sizes stage 2.
- **Sizing-only band estimates at each point** (the headline's frozen sets placed at the
  point's push; docs/findings/RQ1-structural-2d-tables.md, section 6b; never flown; the
  coupled placement's biases apply, and at 200 and 300 m the central estimate sat 3.7 and
  5.6 t below the solve): the adverse end at no offload at every point; the low-mass end
  unscaled / scaled 69.0 / 5,236.0 kg (25 m), 10,489.5 / 15,495.5 kg (50 m), 23,658.2 /
  28,514.4 kg (100 m), 39,876.2 / 44,557.7 kg (200 m) and 50,768.1 / 55,333.7 kg (300 m).

Figure: RQ1-structural-2d-derived_sweep1_exit_speed.png.

## The depth axis: sweep 2 at a fixed exit speed, and the 200 m silo

Sweep 2 runs silo_cold_200m's push to the fixed exit speed 76.70717 m/s over strokes of 50
to 300 m (net 6, 3, 1.5 and 1 g0). In SP1 the uncharged offload was the same at every stroke
by construction (a cold start's flight after release does not see the stroke); with the
structure charged, depth matters through the felt load. Source: the sweep's re-run,
results/silo_structure_2d/20261019T172327Z/sweep_2/sweep_index.csv
(`silo_cold_200m_s1.offload_kg`, `silo_cold_200m_s1_st.status`, `.offload_kg`,
`.dv_shortfall_mps`, `.structure_dm_kg`, `.structure_dm_stage2_kg`, `.structure_n_peak_g`,
`.structure_F_peak_N`, `.verification_delta_kg`, `.max_q_pa`, `.electrical_energy_J`,
`facility_length_m`, and the full-load point run's `drive_power_peak_W`, `peak_q_alpha` and
`speed_at_kick_mps`; every pre-existing column equal to the first sweep's cell for cell) and
each point's metrics.json (`felt_g_track_peak`).

| stroke (net) | felt on the track (flown) | facility | uncharged x0 | structural status | structural x* (% of 41.26 t) | dm1 + dm2 (no offload: at x = 0) | n_peak; F_peak | upper stack: push against envelope | verification | max-Q of the structural run (pad 37,191.4 Pa) | electricity of the structural run | peak drive power (full-load point run) | pre-registered estimate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50 m (6 g0) | 6.996 g0 | 110 m | 41,262.97 kg | no_offload | no offload, stage 2 sized: 190.0 m/s of delta-v short of P_ref at x = 0; payload deficit not flown (no payload case at these settings) | 15,543.0 + 506.1 kg | 7.845 g0; 45.27 MN | 10.75 MN against 7.10 MN: stage 2 and the interstage sized | n/a | 28,868.1 Pa (at x = 0) | 1,121.4 kWh (at x = 0) | 3.02 GW | no offload, stage 2 sized (about 215 m/s, 1,880 kg; 180 m/s, 1,581 kg) |
| 100 m (3 g0) | 3.996 g0 | 160 m | 41,262.97 kg | ok | 11,420.2 kg (27.7%) | 6,305.2 + 0 kg | 4.389 g0; 24.41 MN | inside | +0.0014 kg | 32,130.7 Pa | 1,235.1 kWh | 1.73 GW | 11,105.3 kg |
| 200 m (1.5 g0) | 2.496 g0 | 260 m | 41,262.97 kg | ok | 26,686.4 kg (64.7%) | 3,201.8 + 0 kg | 2.689 g0; 14.47 MN | inside | +0.0035 kg | 35,169.6 Pa | 1,493.1 kWh | 1.08 GW | 26,628.9 kg |
| 300 m (1 g0) | 1.996 g0 | 360 m | 41,262.91 kg | ok | 32,031.0 kg (77.6%) | 2,055.3 + 0 kg | 2.124 g0; 11.30 MN | inside | +0.0053 kg | 36,323.8 Pa | 1,769.8 kWh | 0.86 GW | 32,024.8 kg |

(Every point's full-load run kicks at the first lit instant at 71.8 m/s into a q-alpha of
129.9 Pa rad, 1.74 times the pad's (`peak_q_alpha`, `speed_at_kick_mps`; derived); the
structural runs' q-alpha is not written in the sweep. The 200 m point's structural run is
run A's silo_cold_200m_s1_st (181.0 Pa rad, 2.42 times the pad's, derived); the 300 m
point's lifts off at 542.4 t (derived: 572,354.4 - 32,031.0 + 2,055.3 kg), near run A's
outer_lo (543.5 t, 194.1 Pa rad, 2.60 times; not measured at the point). Every structural
run's max-Q lies below the pad's; every uncharged offload run's lies above it (38,437.4 to
38,438.5 Pa, `silo_cold_200m_s1.max_q_pa`).)

- **The structural offload rises with the stroke**: from no offload at 50 m (190.0 m/s of
  delta-v short of P_ref at x = 0; payload deficit not flown: no payload case at these
  settings; section 7 estimated about 215 m/s, 180 on the quadratic, so the shortfall lies
  between its two estimates) to 11.42, 26.69 and 32.03 t. The gentler push needs less
  structure (dm 16.05 t at 50 m with stage 2 sized; 6.31, 3.20 and 2.06 t). The returns
  diminish: the last 100 m of stroke add 5.34 t (derived: 32,031.0 - 26,686.4 kg), against
  15.27 t for the step from 100 to 200 m, and cost 100 m more facility and 276.8 kWh more
  electricity (derived).
- **The 7 g0 push sizes the upper stack.** At 50 m the push's peak load on the upper stack
  (10.75 MN) exceeds the pad envelope's (7.10 MN), so stage 2's tanks (506.1 kg) and the
  interstage (charged to stage 1; the sweep records only the two stages' totals) are sized,
  and the push's n_peak (7.845 g0) is above the payload's published +6.0 g0 as well as its
  release swing below -2.0 g0.
- **Consistency with run A**: the 100 m point's x* is 0.00056 kg below run A's headline (an
  acceleration one ulp lower, integrator noise; section 5), and the 200 m point equals
  run A's silo_cold_200m_s1_st to 12 significant digits. **silo_cold_200m_s1_st** (read
  under S2 only; section 6 item 4) leaves 26,686.4 kg (64.7% of 41.26 t; 6.49% of stage 1)
  with dm 3,201.8 kg, for a 260 m facility (200 m stroke + 60 m braking) and a push felt at
  2.50 g0 (2.496 g0 flown; sizing n_peak 2.689 g0); it flags the release (swing -2.69 g0,
  stage-1 LOX bottom -397 kPa absolute) and the payload limit.
- **Sizing-only band estimates** (tables, section 6b): at 50 m every end at no offload (the
  scaled low-mass end's equivalent dm 9,397.6 kg against the 8,488.6 kg crossing); at 200 m
  the adverse end at no offload and the low-mass end 32,959.8 / 35,173.6 kg (unscaled /
  scaled); at 300 m the adverse end's estimate offloads, about 13.6 t (sizing only, never
  flown; the only point where the adverse end's estimate does), and the low-mass end
  36,129.2 / 37,491.4 kg.
- **Sizing only against the felt load** (the tables, sections 2 to 4; "Which elements and
  modes carry the mass"): at the fixed exit speed the central's dm grows from 0.75 t at
  1.2 g0 (a 1,474 m stroke) to 5.91 t at 4.0 g0 and 14.74 t at 7.0 g0 (at 41.26 t), with
  stage 2 sized from 4.704 g0 (an 80.9 m stroke) up.

Figures: RQ1-structural-2d-derived_sweep2_depth.png (against the stroke and against the felt
load) and RQ1-structural-2d-derived_dm_vs_felt_load.png.

## The hot starts

Two constant_accel hot starts on the same 3 g0, 100 m silo: silo_hot_full (stage 1 at full
thrust from the push start, lit 4.607 s before release; its full-load run burns 9,730.6 kg
on the track) and silo_hot_ramp_on_track (lit 2 s before release, so its 2 s ramp ends at
release; 2,697.5 kg). Under the prescribed drive the on-track thrust buys no exit speed
(SP1); it lowers the interface force and burns propellant before release. Source: run A's
summary.md (variants table, offload table, Structure subsection, Flags) and metrics.json.

| quantity | silo_cold (reference) | silo_hot_full | silo_hot_ramp_on_track |
|---|---|---|---|
| uncharged x* (% of stage 1) | 41,262.9 kg (10.04%) | 38,980.4 kg (9.49%), new against SP1 (the pre-registered x0 estimate: 39,506 kg) | 46,013.4 kg (11.20%), SP1's reproduced |
| structural x* (% of 41.26 t; % of own) | 11,420.2 kg (27.7%; 27.7%) | 16,336.3 kg (39.6%; 41.9%) | 18,273.9 kg (44.3%; 39.7%) |
| the structure's offload cost U - X | 29,842.7 kg | 22,644.1 kg | 27,739.5 kg |
| dm1 + dm2 at x* (at x = 0) | 6,305.2 kg (6,467.0) | 5,134.2 kg (5,377.2) | 6,210.0 kg (6,467.0) |
| of which the load entry (skirt + ring) / the RP-1 barrel | 3,617.8 / 2,222.7 kg | 2,509.4 / 2,183.5 kg | 3,579.1 / 2,187.4 kg |
| sizing: n_peak; F_peak | 4.389 g0; 24.41 MN | 4.389 g0; 16.43 MN | 4.389 g0; 24.12 MN |
| release swing; stage-1 LOX bottom at the release | -4.389 g0; -896 kPa absolute | -1.58 g0; -100 kPa absolute | -1.61 g0; -114 kPa absolute |
| flags | release, payload limit | release only | release only |
| verification P* - P_ref | +0.0014 kg | +0.0022 kg | +0.0017 kg |
| pre-registered estimate of the structural x* | 11,105.2 kg | 15,258.5 kg (on the estimated x0; 14,690.1 kg re-placed on the solved x0, tables section 7) | 16,218.5 kg |

- **Both hot starts keep more than the cold start with the same structure** (HS):
  silo_hot_full by +4.92 t on an uncharged offload 2.28 t lower, silo_hot_ramp by +6.85 t,
  +4.75 t of it from its larger uncharged offload. Every difference lies far beyond
  section 3's resolution (about 3.4 kg for X, 2.55 kg for U, about 6 kg for the cost).
- **silo_hot_full's structure is lighter but not by as much as its push force.** Its peak
  interface force is a third lower (16.43 against 24.41 MN, -32.7%, derived), so its load
  entry falls by 1.11 t at their own x* (derived: 3,617.8 - 2,509.4 kg); but the tanks feel
  the same 4.389 g0, so the RP-1 barrel barely changes. dm falls by 18.6% at their own x*
  (derived: 5,134.2 against 6,305.2 kg, at x* 16.34 and 11.42 t, so part of it is the
  lighter stack) and by 16.9% at the same offload, x = 0 (derived: 5,377.2 against
  6,467.0 kg). Its structural cost is 7.20 t below the cold start's (derived: 29,842.7 -
  22,644.1 kg).
- **silo_hot_ramp's structure is the cold start's at the same offload** (6,467.0 kg at x = 0
  for both): its peak interface force comes at push start, before its ramp's thrust builds.
  Its lead is mostly its larger uncharged offload; its cost is 2.10 t below the cold start's
  (derived).
- **Exhaust caveat** (SP1): nothing models the exhaust in the shaft (back-pressure, heating,
  the carriage in the plume), which favours both hot starts. Under the prescribed drive the
  on-track thrust reduces the drive force one for one (impingement fraction 0). The release
  flag still fires on both (their stage-1 LOX bottom below zero absolute at a swing of
  -1.6 g0), and the payload-limit flag does not. Under the instant-step treatment the
  stage-1 LOX bottom falls to -100 and -114 kPa absolute while stage 1 is firing (it keeps
  thrusting through the release, section 2(c)); nothing models what that would do to engines
  already running: a risk against the hot starts that no number here measures (far shallower
  than the cold start's -896 kPa absolute, and a real release is not an instant step).

## The drive cases

File B (experiments/silo_drive_2d.yaml, registered with part 2 of the pre-registration at
331891d; run B, results/silo_drive_2d/20261103T231946Z, from 642e11e, which changes no code
against 331891d) keeps file A's pad, P_ref (26,054.396243494975 kg, run B's own pad P* to
0.0 kg) and central structure (set central, sizing flown, dynamic rise_time, entry
aft_ring, margin 0, no cap, no override), and changes only the drive. silo_cold is file
A's constant_accel push, copied verbatim as the comparison basis; the nine linear-motor
variants are design 4.10's (part 2, section 4). Each has an uncharged (`<variant>_s1`) and
a central structural (`<variant>_s1_st`) stage-1 solve. All share silo_cold's silo: a
vertical 100 m stroke exiting at the mouth, a vented shaft, a massless carriage, a 5 g0
carriage brake, drive efficiency 0.5 (assumed; it moves only the electricity) and exhaust
impingement 0, unless the variant says otherwise; stage 1 is lit 0.5 s after the release
with its 2 s ramp unless the variant is a hot start. The linear motor flies its own 0.5 s
rise. Its structure is charged the larger of the rise formula and the flown history's
single-mode bound (D-SP7-52), where file A's constant_accel rows charge an assumed rise
their step push does not fly. Two drive laws:

- **The acceleration law** (lm_cmd, lm_cmd_taper, lm_cmd_hot) commands the net
  acceleration whose ramped profile reaches v_e = 76.71 m/s at L = 100 m (a_cmd 3.009 g0;
  3.729 g0 with the taper). Its caps, F_max = 1.10 M (a_cmd + g_eff) and P_max = F_max v_e,
  never bound (E2 below), so its push does not depend on the stack's mass.
- **The force law** (lm_fixed and its relatives) pushes at F_max = M (a_p + g_eff) =
  22.48 MN, the force that brings the full-load stack (M = 572,354.4 kg, the pad's) to v_e
  at L, with P_max = F_max v_e (r = 1; lm_fixed_r07: r = 0.7 and F_max 25.24 MN for the
  same full-load exit). A lighter stack, such as one offloaded by more than its dm, exits
  faster unless it is released at v_e (lm_fixed_target).

The rule values (a_cmd, F_max, P_max, the hot starts' ignition times) were computed in
closed form before the run and written into file B (part 2, section 5); nothing changed
after it. All eleven blocking checks of part 2, section 9 pass (the table below), so
every number of run B here may be cited. The note's caveats apply to all of them
(Caveats: the calibration miss, sweep-optimized, unthrottled, the free kick, partly
filled tanks, a first-order sizing), with the drive's own limits ("Limits").

File B is solved at the central structure only. No physics band, no outer envelope and no
+/-10% sensitivity arm was run on it (part 2, section 6, item 4: design 4.10 names none,
and no file-B number is the headline); CLAUDE.md's headline arms are file A's (8.55 to
15.07 t, "Headline"). Every difference between drives below is therefore a difference at
the central coefficients. How it would move across the headline's own band (from no
offload to 28.57 t) is not measured, so a difference of 0.22 t or 82 kg is read at the
central structure and nowhere else.

**The cases** (exit criterion 7). Source: run B's metrics.json. Structural values come
from `offload.cases`: x*, `structure_dm_kg`, `structure_dm_stage2_kg`, `structure_dlf`,
`structure_n_peak_g` and `structure_F_peak_N`. Push values come from `offload.runs` for the
recorded run at x* of each case: `felt_g_track_peak`, `peak_interface_force_N`,
`release_position_m`, `speed_at_release_mps`, `electrical_energy_kWh`,
`peak_drive_power_W`, `electrical_power_peak_W` and `facility_length_m`. % of 41.26 t: x*
over SP1's uncharged 41,262.9 kg (part 2, section 8). On a linear-motor structural row the
felt g equals the largest flown quasi-static load n_q (`structure_n_q_g`). silo_cold_s1_st's
n_q is instead the ramped plateau its structure is charged, 4.006 g0, 0.23% above the
3.996 g0 its instant step flies (Caveats, "What the headline assumes"). DLF and n_peak are
the charged values (n_peak = n_rest + DLF (n_q - n_rest)), F_peak is the charged peak
interface force, and "F_int" is the flown peak interface force. silo_cold's constant_accel
runs record no release position and no electrical peak: their release is at L by
construction, and the electrical peak in brackets is the recorded mechanical peak over the
efficiency 0.5 (derived). The electricity is the push's positive drive work over the
efficiency 0.5.

| case | drive; release | x* [kg] | % of 41.26 t | dm1 + dm2 at x* [kg] | felt g, flown peak [g0] | DLF; n_peak [g0] | F_peak [MN] | F_int, flown peak [MN] | release: position [m]; speed [m/s] | electricity [kWh] | peak power, mechanical; electrical [GW] | facility with braking [m] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold_s1 | constant_accel 3 g0 (no force or power limit); at L | 41,262.9 | 100.0% | uncharged | 3.996 | n/a | n/a | 20.81 | 100 (L); 76.71 | 1,156.4 | 1.597; n/a (3.193 derived) | 160.0 |
| **silo_cold_s1_st** | constant_accel 3 g0 (no force or power limit); at L | 11,420.2 | 27.7% | 6,305.2 + 0 | 3.996 | 1.1273; 4.389 | 24.41 | 22.23 | 100 (L); 76.71 | 1,235.1 | 1.705; n/a (3.411 derived) | 160.0 |
| lm_cmd_s1 | acceleration law; track_end | 41,262.9 | 100.0% | uncharged | 4.006 | n/a | n/a | 20.86 | 100; 76.71 | 1,156.4 | 1.600; 3.201 | 160.0 |
| lm_cmd_s1_st | acceleration law; track_end | 11,420.3 | 27.7% | 6,305.2 + 0 | 4.006 | 1.1273; 4.389 | 24.41 | 22.28 | 100; 76.71 | 1,235.1 | 1.709; 3.418 | 160.0 |
| lm_cmd_taper_s1 | acceleration law, 38.35 m stop taper; track_end | 41,263.0 | 100.0% | uncharged | 4.726 | n/a | n/a | 24.61 | 100; 76.71 | 1,156.4 | 1.648; 3.295 | 160.0 |
| lm_cmd_taper_s1_st | acceleration law, 38.35 m stop taper; track_end | 2,479.0 | 6.0% | 8,002.1 + 0.9 | 4.726 | 1.1273; 5.201 | 29.47 | 26.78 | 100; 76.71 | 1,258.2 | 1.793; 3.586 | 160.0 |
| lm_cmd_hot_s1 | acceleration law, lit 0.849 s into the push; track_end | 46,013.4 | 111.5% | uncharged | 4.006 | n/a | n/a | 20.68 | 100; 76.71 | 914.9 | 0.994; 1.989 | 160.0 |
| lm_cmd_hot_s1_st | acceleration law, lit 0.849 s into the push; track_end | 18,273.9 | 44.3% | 6,210.0 + 0 | 4.006 | 1.1273; 4.389 | 24.12 | 22.01 | 100; 76.71 | 988.9 | 1.097; 2.193 | 160.0 |
| lm_fixed_s1 | force law (r = 1); track_end | 43,322.0 | 105.0% | uncharged | 4.334 | n/a | n/a | 22.48 | 100; 80.64 | 1,242.7 | 1.725; 3.449 | 166.3 |
| lm_fixed_s1_st | force law (r = 1); track_end | 11,338.2 | 27.5% | 6,377.3 + 0 | 4.041 | 1.1274; 4.429 | 24.64 | 22.48 | 100; 77.15 | 1,246.1 | 1.725; 3.449 | 160.7 |
| lm_fixed_target_s1 | force law (r = 1); target_speed | 41,216.1 | 99.9% | uncharged | 4.317 | n/a | n/a | 22.48 | 90.70; 76.71 | 1,129.6 | 1.725; 3.449 | 150.7 |
| lm_fixed_target_s1_st | force law (r = 1); target_speed | 11,046.4 | 26.8% | 6,376.8 + 0 | 4.039 | 1.1273; 4.426 | 24.64 | 22.48 | 98.92; 76.71 | 1,232.7 | 1.725; 3.449 | 158.9 |
| lm_fixed_r07_s1 | force law (r = 0.7); track_end | 42,760.9 | 103.6% | uncharged | 4.859 | n/a | n/a | 25.24 | 100; 79.56 | 1,218.6 | 1.355; 2.710 | 164.5 |
| lm_fixed_r07_s1_st | force law (r = 0.7); track_end | 5,658.7 | 13.7% | 7,397.5 + 0 | 4.482 | 1.1281; 4.929 | 27.75 | 25.24 | 100; 76.60 | 1,247.3 | 1.355; 2.710 | 159.8 |
| lm_fixed_hot_s1 | force law (r = 1), lit at push start; track_end | 52,727.5 | 127.8% | uncharged | 5.939 | n/a | n/a | 22.48 | 100; 93.85 | 1,202.8 | 1.725; 3.449 | 189.8 |
| lm_fixed_hot_s1_st | force law (r = 1), lit at push start; track_end | 7,347.5 | 17.8% | 8,874.8 + 131.2 | 5.378 | 1.1273; 5.936 | 24.64 | 22.48 | 100; 89.24 | 1,221.1 | 1.725; 3.449 | 181.2 |
| lm_fixed_sled22_s1 | force law (r = 1), 22 t carriage; track_end | 42,218.1 | 102.3% | uncharged | 4.152 | n/a | n/a | 21.59 | 100; 78.52 | 1,245.4 | 1.725; 3.449 | 162.9 |
| lm_fixed_sled22_s1_st | force law (r = 1), 22 t carriage; track_end | 11,643.3 | 28.2% | 6,079.7 + 0 | 3.894 | 1.1273; 4.263 | 23.69 | 21.64 | 100; 75.27 | 1,246.3 | 1.692; 3.385 | 157.8 |
| lm_fixed_sealed_s1 | force law (r = 1), sealed shaft; track_end | 40,703.2 | 98.6% | uncharged | 4.193 | n/a | n/a | 21.86 | 100; 75.65 | 1,245.9 | 1.701; 3.402 | 158.4 |
| lm_fixed_sealed_s1_st | force law (r = 1), sealed shaft; track_end | 9,049.8 | 21.9% | 6,192.4 + 0 | 3.921 | 1.1319; 4.307 | 24.05 | 21.90 | 100; 72.22 | 1,246.2 | 1.624; 3.247 | 153.2 |

- Every case is ok and verified (the structural cases by part 2, section 9's check 6; the
  uncharged ones reported beside it). On the structural cases the independent payload search
  returns P_ref +0.0004 to +0.0017 kg; on the uncharged cases +0.0060 to +0.0094 kg, except
  lm_fixed_hot_s1's +0.6820 kg (tolerance 2.605 kg; `verification.delta_kg`). That gap is 73
  to 115 times the other uncharged cases' and corresponds to about 18 kg of U (derived:
  0.682 kg times the case's own chord of 27.0 kg of offload per kg of payload, its U of
  52,727.5 kg over its full-load run's payload gain of 1,949.6 kg over the pad,
  `runs.lm_fixed_hot.payload_kg`), about 7 times the uncharged R of 2.55 kg. So
  lm_fixed_hot's U, and its cost U - X, are uncertain by about that much, beyond a cost's R
  of 6 kg, and are not read to 0.1 kg; no reading moves (HS's +9.41 t uncharged, the cost's
  45.38 t). No case ended no_offload, so no delta-v shortfall or payload deficit is reported
  for file B (check 11).
- silo_cold_s1_st reproduces run A's 11,420.246638573297 kg to the bit (0.0 kg), and
  silo_cold_s1 SP1's 41,262.90803733282 kg (check 4, the cross-commit check). Between run
  A (1b5f9d4) and run B the code gained the linear motor, the target-speed release, the
  flown structural push and the sealed shaft, and silo_cold's numbers did not move (bit for
  bit; the check compares results, not the code on their path).
- Against the README's ideal-screening estimate at each case's own release speed
  (`offload.cases` `screening_offload_kg`, `screening_ratio` and `beats_screening`;
  summary.md's "stage-1 offload / screening offload"), 11 of the 20 cases beat it: all ten
  uncharged ones, at 2.752 (lm_fixed_target_s1) to 3.072 times it (lm_cmd_hot_s1), and one
  structural case, lm_cmd_hot_s1_st, at 1.220 times the 14,976.6 kg at 76.71 m/s (its
  18.27 t is the top of the drive range). CLAUDE.md asks that a beat be explained: each of
  the 11 has a closing decomposition ("explained"), and each beats it through the
  gravity + steering term of the cross-vehicle decomposition
  (`decomposition.xv_gravity_steering_mps`), as file A's rows and SP1's uncharged headline
  (124.7 m/s) do: 84.5 m/s on lm_cmd_hot_s1_st against silo_cold_s1_st's 36.0, and 122.7
  to 194.3 m/s on the uncharged cases. The other nine structural cases do not beat it,
  silo_cold_s1_st among them (0.763): 0.166 (lm_cmd_taper_s1_st) to 0.792
  (lm_fixed_sled22_s1_st), with lm_fixed_hot_s1_st at 0.423 of its own 17.39 t at
  89.24 m/s.
- The electricity of the cold pushes at x* is 1,232.7 to 1,258.2 kWh. The two hot starts
  need less, for different reasons. lm_cmd_hot (988.9 kWh) needs less because under the
  acceleration law its thrust replaces motor force: its drive force falls from 22.01 MN on
  the plateau to 14.30 MN at the release (`drive_force_peak_N`; the last ASSIST row's
  `drive_force_N`). lm_fixed_hot (1,221.1 kWh, against lm_fixed's 1,246.1 kWh) needs less
  because its faster stack meets the power cap 26.0 m below the mouth and flies its last
  0.313 s at P_max, its force falling from 22.48 to 19.33 MN (its `power_limit` event and
  last ASSIST row; lm_fixed meets the cap 1.14 m below the mouth). Under the force law its
  drive holds F_max whatever the thrust, which adds on top rather than replacing motor
  force; its drive work is 2.198 against lm_fixed's 2.243 GJ (`drive_work_in_J`). The
  electricity is a lower bound for the hot starts (impingement 0, no plume). The peak
  electrical power at x* is 2.19 to 3.59 GW. The facility, the release position plus the
  carriage's braking distance at 5 g0, is 153.2 to 181.2 m long, the longest for
  lm_fixed_hot's 89.24 m/s exit.
- The 22 t carriage's brake takes 0.864 MN and 49.9 MJ at x* (`brake_force_N`,
  `brake_energy_J` of lm_fixed_sled22_s1_st's run). The sealed column on
  lm_fixed_sealed_s1_st peaks at 2.180 MN and takes 201.7 MJ of the drive's work
  (`piston_force_peak_N`, `piston_work_J`); the column's absolute pressure below the
  vehicle at the release is 1,444.6 Pa, 1.4% of its initial p_0 (`bore_pressure_release_pa`,
  p_0 (h_0/(h_0 + s))^gamma; the share derived).

**The structural cost of each drive.** Source: run B's metrics.json `offload.cases`
(`offload_kg`, `structure_n_q_g`, `structure_dm_x0_kg`, `structure_iterations`, the
`structure_fixed_point_cap` flag's `contraction`, `verification.delta_kg` and
`solve.n_evaluations`). U - X is the structure's offload cost and X / U the share of the
push's own uncharged offload that the structure leaves (both derived).

| variant | uncharged U [kg] | structural X [kg] | X - silo_cold_s1_st's [kg] | U - X [kg] | X / U | n_q at x* [g0] | dm at x = 0 [kg] | sizings at x*; contraction | verification P* - P_ref [kg] | solve evaluations (uncharged) |
|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold | 41,262.9 | 11,420.2 | 0 (the basis) | 29,842.7 | 27.7% | 4.006 | 6,467.0 | 6; 0.0056 | +0.0014 (uncharged +0.0085) | 40 (42) |
| lm_cmd | 41,262.9 | 11,420.3 | +0.0046 | 29,842.7 | 27.7% | 4.006 | 6,467.0 | 6; 0.0056 | +0.0013 (uncharged +0.0084) | 40 (42) |
| lm_cmd_taper | 41,263.0 | 2,479.0 | -8,941.2 | 38,784.0 | 6.0% | 4.726 | 8,052.8 | 6; 0.0061 | +0.0008 (uncharged +0.0060) | 38 (44) |
| lm_cmd_hot | 46,013.4 | 18,273.9 | +6,853.7 | 27,739.5 | 39.7% | 4.006 | 6,467.0 | 6; 0.0056 | +0.0017 (uncharged +0.0087) | 41 (42) |
| lm_fixed | 43,322.0 | 11,338.2 | -82.0 | 31,983.7 | 26.2% | 4.041 | 6,375.3 | 6; 0.0089 | +0.0013 (uncharged +0.0060) | 40 (44) |
| lm_fixed_target | 41,216.1 | 11,046.4 | -373.9 | 30,169.8 | 26.8% | 4.039 | 6,375.3 | 6; 0.0087 | +0.0013 (uncharged +0.0094) | 40 (42) |
| lm_fixed_r07 | 42,760.9 | 5,658.7 | -5,761.5 | 37,102.2 | 13.2% | 4.482 | 7,400.3 | 7; 0.0115 | +0.0008 (uncharged +0.0062) | 39 (42) |
| lm_fixed_hot | 52,727.5 | 7,347.5 | -4,072.8 | 45,380.0 | 13.9% | 5.378 | 8,944.3 | 7; 0.0211 | +0.0004 (uncharged +0.6820) | 44 (45) |
| lm_fixed_sled22 | 42,218.1 | 11,643.3 | +223.1 | 30,574.8 | 27.6% | 3.894 | 6,081.9 | 6; 0.0075 | +0.0014 (uncharged +0.0060) | 40 (42) |
| lm_fixed_sealed | 40,703.2 | 9,049.8 | -2,370.4 | 31,653.3 | 22.2% | 3.921 | 6,193.2 | 6; 0.0079 | +0.0014 (uncharged +0.0060) | 40 (42) |

**Beside every number** (part 2, section 9's list). Source: run B's metrics.json:
`offload.runs` (`max_q_pa`, `peak_q_alpha`), `runs.pad` for the pad's, and each structural
case's `structure_flags` (`structure_release_unload`: `release_swing_g`,
`lox_bottom_pressure_min_abs_pa`; `structure_payload_limit`: `n_peak_g`,
`release_swing_g`; `structure_upper_stack_exceeded`: `push_n_upper_N` against
`envelope_n_upper_N`; `structure_flight_exceedance`: `total_kg`). The flags are reported,
never a gate. The release flag's comparison is the pad's own MECO under the same
single-mode instant step (D-SP7-39).

| variant | max-Q, uncharged; structural [Pa] (pad 37,191.4) | peak q-alpha, uncharged; structural [Pa rad] (pad 74.7) | release flag: swing [g0] (the pad's MECO -5.195); stage-1 LOX bottom [kPa absolute] | payload-limit flag (+6.0 / -2.0 g0): n_peak; swing | upper-stack flag: push against the envelope's 7.095 MN | flight check [kg] |
|---|---|---|---|---|---|---|
| silo_cold | 38,438.5; 32,130.7 | 226.9; 140.9 | fires: -4.389; -896 | fires: 4.389; -4.389 | does not fire: 5.994 MN | 0.0 |
| lm_cmd | 38,438.4; 32,130.6 | 226.9; 140.9 | fires: -4.389; -896 | fires: 4.389; -4.389 | does not fire: 5.994 MN | 0.0 |
| lm_cmd_taper | 38,437.4; 30,512.4 | 226.9; 120.9 | fires: -1.946; -230 | does not fire: 5.201; -1.946 | fires: 7.102 MN | 0.0 |
| lm_cmd_hot | 39,712.6; 33,445.8 | 393.0; 268.5 | fires: -1.607; -114 | does not fire: 4.389; -1.607 | does not fire: 5.994 MN | 0.0 |
| lm_fixed | 38,616.3; 32,082.3 | 284.8; 144.2 | fires: -4.505; -928 | fires: 4.429; -4.505 | does not fire: 6.048 MN | 0.0 |
| lm_fixed_target | 38,473.6; 32,065.2 | 226.9; 140.1 | fires: -4.426; -907 | fires: 4.426; -4.426 | does not fire: 6.044 MN | 0.0 |
| lm_fixed_r07 | 38,566.2; 31,082.8 | 268.0; 127.0 | fires: -3.767; -737 | fires: 4.929; -3.767 | does not fire: 6.731 MN | 0.0 |
| lm_fixed_hot | 40,882.9; 31,123.0 | 846.1; 409.2 | fires: -2.670; -418 | fires: 5.936; -2.670 | fires: 8.114 MN | 0.0 |
| lm_fixed_sled22 | 38,518.7; 32,281.1 | 252.5; 130.4 | fires: -4.263; -860 | fires: 4.263; -4.263 | does not fire: 5.821 MN | 0.0 |
| lm_fixed_sealed | 38,391.0; 32,035.1 | 212.9; 104.1 | fires: -4.053; -809 | fires: 4.307; -4.053 | does not fire: 5.882 MN | 0.0 |

- Every uncharged run flies a max-Q above the pad's, and every structural run one below
  it (unthrottled, unconstrained: not a load benefit the model can claim, Caveats). Every
  offloaded run kicks free into a q-alpha above the pad's 74.7 Pa rad: the structural
  runs 1.39 to 5.48 times it (104.1 Pa rad on lm_fixed_sealed to 409.2 on lm_fixed_hot),
  the uncharged runs 2.85 to 11.32 times (212.9 to 846.1 Pa rad, derived ratios).
  lm_fixed_hot_s1 kicks at its release, at 93.85 m/s, into 846.1 Pa rad.
- The payload-limit flag fires on seven of the nine linear-motor central cases, as on
  silo_cold. It fires on the swing everywhere (beyond -2.0 g0), and never on n_peak:
  lm_fixed_hot's 5.936 g0 comes nearest to +6.0 g0, 0.064 g0 inside it (0.190 g0 against
  the flown history's own bound of 5.810 g0, which the charged rise formula exceeds there:
  "Limits"). The pad's own MECO swings the stack to -5.195 g0 under the same treatment, so
  the flag measures the model's step treatment as much as the push. It does not fire on
  lm_cmd_taper (swing -1.946 g0, 0.054 g0 inside the limit) or on lm_cmd_hot (-1.607 g0).
- The upper-stack flag fires on lm_cmd_taper_s1_st (7.102 against 7.095 MN, 0.10% over;
  stage 2 sized by 0.9 kg) and on lm_fixed_hot_s1_st (8.114 against 7.095 MN; stage 2
  sized by 131.2 kg), and on no other case. The release flag fires on all ten
  structural cases. Even the taper's gentle stop leaves the stage-1 LOX bottom at
  -230 kPa absolute, below zero absolute. Half of the taper's -1.946 g0 swing is not the
  release step itself: -0.996 g0 is the step (the felt load falling from about 1 g0 to 0,
  `release_swing_plateau_g`) and 0.950 g0 the flown history's single-mode bound on the
  undamped residual of the rise and of the taper's start, carried to the release
  phase-free (`release_bound_residual_g`; D-SP7-52, KI-070). Any structural damping would
  shrink that residual, and with it the swing and the LOX-bottom depth, widening the
  0.054 g0 margin to the payload limit; none is modelled.
- `release_speed_not_reached` fires once, on lm_fixed_target's variant run (a stack
  heavier than M flying its own P*: it released at the track end at 76.574 m/s, below
  v_e). Part 2 expected it there and calls it not blocking; it fires on neither of
  lm_fixed_target's two cases. That variant run's P* equals lm_fixed's to 3.1e-6 kg
  (derived from `runs.<variant>.payload_kg`; expected within 0.05 kg, part 2, section 5).

**Every fixed sentence that fired** (part 2, section 8, word for word as
docs/findings/scripts/sp7_s7b_checks.py fills them from the run: its output, section C, in
docs/findings/RQ1-structural-2d-drive-checks.txt). The bracket names the sentence and the
branch that fired; text in brackets after "beside:" is printed beside, not read. A
difference is read against part 2, section 3's resolution R: about 3.4 kg for x*, 2.55 kg
for an uncharged x*, 6 kg for a cost.

- [RB, cancels most] lm_cmd_s1_st (constant_accel with a flown ramp (its uncharged x* equals SP1's within 0.25 kg for a cold start: pre-registered by the design)) cancels most of it: 11.42 t is left (27.7%). [beside: 27.7% of its own uncharged 41.26 t (lm_cmd_s1)]
- [RB, cancels most] lm_cmd_taper_s1_st (the cost of a gentle stop against the release flag) cancels most of it: 2.48 t is left (6.0%). [beside: 6.0% of its own uncharged 41.26 t (lm_cmd_taper_s1)]
- [RB, cancels most] lm_cmd_hot_s1_st (the hot start under a structure-protecting drive (thrust replaces motor force)) cancels most of it: 18.27 t is left (44.3%). [beside: 39.7% of its own uncharged 46.01 t (lm_cmd_hot_s1)]
- [RB, cancels most] lm_fixed_s1_st (a facility sized for the full load, run at full force on a lighter stack) cancels most of it: 11.34 t is left (27.5%). [beside: 26.2% of its own uncharged 43.32 t (lm_fixed_s1)]
- [RB, cancels most] lm_fixed_target_s1_st (the same exit speed from a fixed facility) cancels most of it: 11.05 t is left (26.8%). [beside: 26.8% of its own uncharged 41.22 t (lm_fixed_target_s1)]
- [RB, cancels most] lm_fixed_r07_s1_st (a power-limited drive) cancels most of it: 5.66 t is left (13.7%). [beside: 13.2% of its own uncharged 42.76 t (lm_fixed_r07_s1)]
- [RB, cancels most] lm_fixed_hot_s1_st (the force-limited hot start (pre-registered to raise the upper-stack flag)) cancels most of it: 7.35 t is left (17.8%). [beside: 13.9% of its own uncharged 52.73 t (lm_fixed_hot_s1)]
- [RB, cancels most] lm_fixed_sled22_s1_st (carriage mass at a fixed force) cancels most of it: 11.64 t is left (28.2%). [beside: 27.6% of its own uncharged 42.22 t (lm_fixed_sled22_s1)]
- [RB, cancels most] lm_fixed_sealed_s1_st (the air column) cancels most of it: 9.05 t is left (21.9%). [beside: 22.2% of its own uncharged 40.70 t (lm_fixed_sealed_s1)]
- [LM, the same within the resolution] lm_cmd_s1_st (constant_accel with a flown ramp (its uncharged x* equals SP1's within 0.25 kg for a cold start: pre-registered by the design)) leaves 11.42 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: the same within the resolution (uncharged 41.26 t against 41.26 t; the structure's offload cost U - X 29.84 t against 29.84 t). [beside: X - X_c +0.0046 kg, U - U_c +0.0014 kg, cost - cost_c -0.0032 kg, each within its R]
- [LM, less] lm_cmd_taper_s1_st (the cost of a gentle stop against the release flag) leaves 2.48 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 8.94 t less (uncharged 41.26 t against 41.26 t; the structure's offload cost U - X 38.78 t against 29.84 t).
- [LM, more] lm_cmd_hot_s1_st (the hot start under a structure-protecting drive (thrust replaces motor force)) leaves 18.27 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 6.85 t more (uncharged 46.01 t against 41.26 t; the structure's offload cost U - X 27.74 t against 29.84 t).
- [LM, less] lm_fixed_s1_st (a facility sized for the full load, run at full force on a lighter stack) leaves 11.34 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 0.08 t less (uncharged 43.32 t against 41.26 t; the structure's offload cost U - X 31.98 t against 29.84 t). [beside: X - X_c -82.0 kg against R 3.4 kg]
- [LM, less] lm_fixed_target_s1_st (the same exit speed from a fixed facility) leaves 11.05 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 0.37 t less (uncharged 41.22 t against 41.26 t; the structure's offload cost U - X 30.17 t against 29.84 t).
- [LM, less] lm_fixed_r07_s1_st (a power-limited drive) leaves 5.66 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 5.76 t less (uncharged 42.76 t against 41.26 t; the structure's offload cost U - X 37.10 t against 29.84 t).
- [LM, less] lm_fixed_hot_s1_st (the force-limited hot start (pre-registered to raise the upper-stack flag)) leaves 7.35 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 4.07 t less (uncharged 52.73 t against 41.26 t; the structure's offload cost U - X 45.38 t against 29.84 t).
- [LM, more] lm_fixed_sled22_s1_st (carriage mass at a fixed force) leaves 11.64 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 0.22 t more (uncharged 42.22 t against 41.26 t; the structure's offload cost U - X 30.57 t against 29.84 t).
- [LM, less] lm_fixed_sealed_s1_st (the air column) leaves 9.05 t of stage-1 propellant against silo_cold_s1_st's 11.42 t: 2.37 t less (uncharged 40.70 t against 41.26 t; the structure's offload cost U - X 31.65 t against 29.84 t).
- [HS, more] lm_cmd_hot_s1_st keeps more offload than lm_cmd_s1_st with the same drive and the same structure settings: +6.85 t (uncharged +4.75 t; the structure's offload cost 27.74 t against 29.84 t) (nothing models the exhaust in the shaft: back-pressure, heating, the carriage in the plume, which favours the hot starts).
- [HS, less] lm_fixed_hot_s1_st keeps less offload than lm_fixed_s1_st with the same drive and the same structure settings: -3.99 t (uncharged +9.41 t; the structure's offload cost 45.38 t against 31.98 t) (nothing models the exhaust in the shaft: back-pressure, heating, the carriage in the plume, which favours the hot starts).
- [TS, less] Released where its speed reaches v_e (98.92 m up the 100 m stroke at x*), lm_fixed_target leaves 11.05 t against lm_fixed's 11.34 t released at the track end at 77.15 m/s: 0.29 t less (uncharged 41.22 t against 43.32 t).
- [CM, more] With a 22 t carriage at the same F_max and P_max, lm_fixed_sled22 leaves 11.64 t against lm_fixed's 11.34 t: 0.31 t more (uncharged 42.22 t against 43.32 t; at x* an exit speed of 75.27 m/s against 77.15 m/s and a peak interface force of 21.644 MN against 22.484 MN).
- [SS, less] In the sealed shaft (bore 5.24 m, gap 5 m) the same drive leaves 9.05 t against the vented lm_fixed's 11.34 t: 2.29 t less (uncharged 40.70 t against 43.32 t; at x* the column's peak force 2.180 MN and its work 201.7 MJ, and an exit speed of 72.22 m/s against 77.15 m/s).
- [TP, less; the release flag fires; the payload-limit flag does not fire] The stop taper leaves 2.48 t against lm_cmd's 11.42 t: 8.94 t less; at x* its release flag fires (the stage-1 LOX bottom at -230 kPa absolute against lm_cmd's -896 kPa; the release swing -1.95 g0 against -4.39 g0) and its payload-limit flag does not fire.
- [PL, less] The power-limited drive (r = 0.7, F_max 25.236 MN) leaves 5.66 t against lm_fixed's 11.34 t (F_max 22.484 MN): 5.68 t less.

Not fired: RB's "keeps more than half" and "cancels all" on all nine; LM's "the same
within the resolution" on all but lm_cmd (every other difference is beyond R, the smallest
lm_fixed's 82.0 kg against about 3.4 kg); HS's "the same within the resolution" on both
pairs; TS's, CM's, SS's and PL's other two branches; TP's "more", "the same within the
resolution", "its release flag does not fire" and "its payload-limit flag fires". No case
ended no_offload, search_failed or reference_failed, so no sentence was withheld.

**The registered expectations** (part 2, section 8; met or not met, never a check):

- E1 (design 4.10): lm_fixed_hot_s1_st raises the upper-stack flag at its x*: **met** (its
  push loads the upper stack with 8.114 MN against the envelope's 7.095 MN; dm2 131.2 kg).
- E2 (sources section 10; D-SP7-24): no `drive_cap` on the lm_cmd family: **met**. No
  `drive_cap` or `drive_cap_end` event, no `push_cap_bound` and no cap flag appears on the
  variant runs of lm_cmd, lm_cmd_taper and lm_cmd_hot or on their six cases' runs at x*.
  Each released at v_e (76.71 m/s).

Read beside them (part 2, section 8, not expectations of their own): lm_cmd_s1_st -
silo_cold_s1_st = +0.0046 kg (R 3.4 kg); lm_cmd_hot_s1 - run A's silo_hot_ramp_s1 =
+0.0014 kg (R 2.55 kg); lm_cmd_hot_s1_st - run A's silo_hot_ramp_s1_st (18,273.917 kg) =
+0.00004 kg (R 3.4 kg). Both pairs reproduce file A's pushes, as part 2, section 2(b) said
they would by construction: the acceleration law that reaches v_e at L flies the ramped
plateau that file A's constant_accel `rise_time` row already charges, so lm_cmd's flown
ramp gives the same x* as file A's closed-form charge of silo_cold's (within R), and
lm_cmd_hot's the same as silo_hot_ramp_on_track's.

**The blocking checks** (part 2, section 9, in its order; evaluated on run B by
docs/findings/scripts/sp7_s7b_checks.py at b291518 on 2026-11-04T03:03:48Z, after the
convergence check; its text and JSON output are committed unchanged as
docs/findings/RQ1-structural-2d-drive-checks.txt and .json; its summary line: "SUMMARY:
PASS: all 11 checks pass"):

| check (part 2, section 9) | what it blocks | value on run B | verdict |
|---|---|---|---|
| 1. no run or comparison bug_suspect | the number it touches | none (summary.md's "No run and no comparison is bug_suspect."; 20 decompositions explained, the worst residual 8.578e-11 m/s against 1e-5 m/s; run checks ok on all 32 runs) | pass |
| 2. the pad not reference_failed, its P* within 0.002 kg of P_ref | every number | P* 26,054.396243494975 kg, 0.0 kg off | pass |
| 3. the stage-1 pad control's consistency test | every offload number | no_offload at x_pad = 0, m_res(0) -0.00164 kg against a 1.618 kg bound (a resolution effect, as in SP1 and run A) | pass |
| 4. the cross-commit check (0.002 kg) | every number of run B | silo_cold_s1 41,262.90803733282 kg against SP1's, 0.0 kg; silo_cold_s1_st 11,420.246638573297 kg against run A's, 0.0 kg | pass |
| 5. lm_cmd's uncharged x* within 0.25 kg of SP1's 41,262.908 kg | every linear-motor number | 41,262.909435 kg, +0.0014 kg | pass |
| 6. structural verification within 1e-4 P_ref (2.605 kg) or flagged | the case (reported as a bound) | +0.0004 to +0.0017 kg on the ten structural cases | pass |
| 7. `xv_dry_mass_delta_kg` = dm1 + dm2 at x* within 1e-6 kg | the case (a bug) | at most 4.5e-12 kg off on the ten structural cases | pass |
| 8. the structure files' sha256 at run B's commit and as recorded | every structural number | both equal part 1, section 12's (a0516875... and a850de94...); run B's 22 records name the first | pass |
| 9. the linear-motor convergence check (0.1%) | every linear-motor number | on lm_fixed_s1_st, the one registered case: tightened x* +0.0274 kg (2.4e-6 relative); the shipped x* equals run B's to 0.0 kg (the other eight linear-motor cases' tolerance sensitivity is not measured: "Convergence") | pass |
| 10. no unexplained `offload_nonmonotone`, capped gamma* refine or fired fixed-point cap | the number | none fired (20 fixed-point records, the ten cases' and their recorded runs'; 6 or 7 sizings each against the cap of 25) | pass |
| 11. every no_offload case reported with its shortfall and "payload deficit not flown" | the case's report | no case ended no_offload | pass |

**What the drive cases show**, case by case (each against silo_cold_s1_st unless named;
every difference beyond R unless stated):

- **The acceleration law is constant_accel with its ramp charged.** lm_cmd reproduces
  silo_cold_s1_st to +0.0046 kg, within R, and its uncharged x* reproduces SP1's to
  +0.0014 kg (check 5). The push it flies (felt 4.006 g0 after a 0.5 s rise) is the
  plateau file A already charges for silo_cold's instant step, so this equality is by
  construction. It is not evidence that a real drive behaves so.
- **A gentle stop costs most of what is left.** lm_cmd_taper's taper scales the net
  acceleration command down linearly in position to zero at the release over its last
  38.35 m (w(s) = min(1, (L - s)/s_taper)), with the command raised 24% to make the same
  exit (felt 4.726 g0 against 4.006). Its dm is 8,003.0 kg against 6,305.2 kg, with
  stage 2 sized by 0.9 kg, and it keeps 2.48 t, 8.94 t less than lm_cmd at the same
  76.71 m/s exit. The model sizes no release step, so the gentler stop shows only in
  the flags: release swing -1.946 g0 inside the payload's -2.0 g0 (0.950 g0 of it the
  undamped residual of the rise and the taper's start, above), and the stage-1 LOX
  bottom at -230 kPa absolute against -896 kPa. The release flag still fires.
- **The hot start under the acceleration law keeps the most.** lm_cmd_hot (thrust
  replaces motor force over the last 2 s of the push; 2,697.5 kg burned on the track)
  leaves 18.27 t (44.3%), 6.85 t more than lm_cmd. 4.75 t of that is its larger uncharged
  offload; its structure costs 2.10 t less (derived). Its peak interface force comes on
  the plateau before its ignition at 0.849 s, so its dm at x = 0 equals the cold start's
  6,467.0 kg. It is run A's silo_hot_ramp_s1_st to +0.00004 kg. Nothing models
  the exhaust in the shaft, which favours it.
- **A force sized for the full load gains nothing once charged.** lm_fixed's lighter
  stack exits faster: 80.64 m/s uncharged, +2.06 t of uncharged offload. But its felt
  plateau rises with the lighter stack (n_q 4.041 against 4.006 g0; F_peak 24.64 against
  24.41 MN), its dm is 72.1 kg larger (6,377.3 against 6,305.2 kg, derived), and at x* it
  exits only 0.44 m/s faster (77.15 m/s). It leaves 82.0 kg less than silo_cold_s1_st,
  0.08 t, about 24 times R. The power limit binds at x* (`push_power_limited`; its corner
  speed is v_e, and the stack offloaded by more than its dm passes it before L).
- **Releasing that facility at v_e gives up its extra exit speed and keeps less.**
  lm_fixed_target releases its stack at v_e (76.71 m/s), 98.92 m up the stroke, 1.08 m
  below the mouth (90.70 m uncharged), and keeps 11.05 t: 0.29 t less than lm_fixed and
  0.37 t less than silo_cold_s1_st. Its uncharged offload is 2.11 t below lm_fixed's, and
  its structure costs 1.81 t less (U - X 30.17 against 31.98 t, derived): it keeps less
  because its uncharged offload is lower, not because its structure costs more.
- **More force for the same exit costs offload.** lm_fixed_r07 needs a 12% higher F_max
  (25.24 against 22.48 MN) for the same full-load exit with r = 0.7. Its plateau (n_q
  4.482 g0) sizes 7,397.5 kg, and it keeps 5.66 t, 5.68 t less than lm_fixed. At x* it
  exits at 76.60 m/s, below v_e: the stack is heavier than M (x* = 5.66 t, below its dm
  of 7.40 t).
- **The force-limited hot start offloads the most uncharged and loses the most to
  structure.** lm_fixed_hot adds the full thrust to F_max on the track (4,349.3 kg burned
  at x*). Uncharged it leaves out 52.73 t, the most of any case, exiting at 93.85 m/s.
  But its felt load reaches 5.378 g0 (n_peak 5.936 g0, the rise formula's, 0.126 g0 above
  the flown history's own bound: an overcharge against the assist, of order 1 t of x* on a
  rough estimate, not measured; "Limits"), dm is 9,006.0 kg with stage 2 and the
  interstage sized (E1), and the structure costs 45.38 t of offload. It keeps 7.35 t,
  3.99 t less than lm_fixed, while exiting at 89.24 m/s, 12.53 m/s faster than silo_cold.
- **A carriage at a fixed force trades speed for structure, and wins by a little.**
  lm_fixed_sled22's 22 t carriage takes its share of the same F_max, lowering both the
  vehicle's felt load (n_q 3.894 g0) and its exit speed (75.27 m/s at x*). Its dm falls
  to 6,079.7 kg and it keeps 11.64 t: 0.31 t more than lm_fixed and 0.22 t more than
  silo_cold_s1_st while exiting 1.43 m/s slower. Part 2 placed this reading within
  reach (+0.36 t estimated). The carriage itself, its structure and its interface
  hardware are not sized.
- **The air column costs exit speed and offload.** In the sealed shaft (bore 5.24 m, gap
  5 m) the column pushes back with up to 2.180 MN and takes 201.7 MJ of the drive's
  work. The exit at x* falls to 72.22 m/s and the case keeps 9.05 t, 2.29 t less than
  the vented lm_fixed. Its lower interface force (21.90 against 22.48 MN flown) lowers dm
  to 6,192.4 kg (lm_fixed's 6,377.3 kg), by less than the lost speed costs.
- **The exit speed alone does not order the charged offloads.** At x* the fastest exit
  (lm_fixed_hot, 89.24 m/s) keeps less than seven slower ones, and the 22 t carriage's
  slower exit keeps more than silo_cold's. Among pushes at the same 76.71 m/s the
  structural x* spans 2.48 t (the taper) to 18.27 t (lm_cmd_hot)
  (RQ1-structural-2d-derived_drive_exit_speed.png).

Figures: RQ1-structural-2d-derived_drive_cases.png (the table as a chart),
RQ1-structural-2d-derived_drive_force_power.png (the flown pushes' force and power against
speed) and RQ1-structural-2d-derived_drive_exit_speed.png ("Figures").

## The payload form

Each payload case flies silo_cold at its own P* with the structure sized for its full-load
push, in two passes (design 4.4): dm_0 sized at P_ref on the full-load vehicle, P_1*
searched carrying dm_0, dm_1 re-sized at P_1*, P_2* searched carrying dm_1; not iterated
further. These runs offload nothing: P_2* - P_ref is the payload change at the full load,
not a propellant saving. Source: run A's summary.md, "Structure payload cases", and
metrics.json `offload.structure_payload_cases`; the pre-registered estimates from section 7
(two passes on RQ3-2d's linear payload rate, the quadratic in brackets). Reported beside
(section 9's list), each case's recorded run (it flies P_2*) against the pad: its
`structure_payload_cases[].vs_pad` (liftoff mass, max-Q, felt g, interface force,
electricity over 3.6e6, derived), `offload.runs` (`peak_q_alpha`, `drive_power_peak_W`; the
ratios derived) and its `structure_flags`. Every payload run flies 3.996 g0 on the track and
needs a 160 m facility; no flight check (below).

| quantity | silo_cold_pstar_st (central) | silo_cold_pstar_st_phys_hi | silo_cold_pstar_st_outer_hi | silo_cold_pstar_st_step |
|---|---|---|---|---|
| dm_0 at P_ref (stage 2 within it) | 6,467.0 kg | 21,551.8 kg | 59,898.9 kg (1,362.1) | 13,498.0 kg (319.8) |
| P_1* | 26,397.4 kg | 23,957.0 kg | 17,814.6 kg | 24,950.0 kg |
| dm_1 at P_1* (stage 2 within it) | 6,471.7 kg | 21,439.4 kg | 58,368.4 kg (1,063.5) | 13,429.2 kg (312.3) |
| P_2* | 26,396.6 kg | 23,974.0 kg | 18,250.0 kg | 24,967.5 kg |
| **P_2* - P_ref** | **+342.2 kg** | **-2,080.4 kg** | **-7,804.3 kg** | **-1,086.9 kg** |
| P_2* - P_1* | -0.81 kg | +16.97 kg | +435.48 kg | +17.47 kg |
| contraction c | 0.00237 | 0.00809 | 0.0529 | 0.0158 |
| residual estimate c x abs(P_2* - P_1*) against 0.025 kg | 0.0019 kg | 0.137 kg | 23.0 kg | 0.277 kg |
| `structure_payload_unconverged` | not fired | fired (not blocking) | fired (not blocking) | fired (not blocking) |
| read beside | silo_cold_s1_st_full (10.59 t) | the phys_hi row's deficit | the outer_hi row's deficit | the step row's deficit |
| liftoff mass (pad 572.4 t) | 579.2 t | 591.7 t | 622.9 t | 584.7 t |
| max-Q (pad 37,191.4 Pa) | 30,349.3 Pa | 28,398.5 Pa | 24,279.5 Pa | 29,466.1 Pa |
| peak q-alpha, at the kick 0.5 s after release at 71.8 m/s (pad 74.7 Pa rad) | 119.0 Pa rad (1.59 times the pad's) | 96.3 Pa rad (1.29 times) | 55.2 Pa rad (0.74 times) | 108.5 Pa rad (1.45 times) |
| P_2* - P_ref an upper bound by run A's rule (q-alpha or max-Q above the pad's, or a kick above 120 m/s; derived: a payload case writes no comparison record) | yes (q-alpha) | yes (q-alpha) | no (none of the three) | yes (q-alpha) |
| peak felt axial g in flight (pad 5.195 g0) | 4.985 g0 | 4.639 g0 | 4.291 g0 | 4.827 g0 |
| interface force, flown peak | 22.70 MN | 23.19 MN | 24.41 MN | 22.92 MN |
| electricity of the push; peak drive power | 1,261.0 kWh; 1.741 GW | 1,288.4 kWh; 1.779 GW | 1,356.3 kWh; 1.873 GW | 1,273.1 kWh; 1.758 GW |
| flags fired, with their numbers (the pad's MECO -5.195 g0 under the same step) | release (swing -4.389 g0; stage-1 LOX bottom -928 kPa absolute); payload limit on the swing | release (-4.389 g0; -766 kPa absolute); payload limit on the swing | release (-6.998 g0; -1,503 kPa absolute); payload limit on the swing and on n_peak 6.998 g0; upper stack (9.06 against its capped envelope's 5.46 MN) | release (-6.996 g0; -1,671 kPa absolute); payload limit on the swing and on n_peak 6.996 g0; upper stack (9.50 against 7.10 MN) |
| pre-registered estimate: P_1*, P_2*, P_2* - P_ref | about 26,361; 26,361; +306 [+343] kg | about 23,581; 23,606; -2,449 [-2,048] kg | about 15,390; 16,071; -9,984 [-6,668] kg | about 24,802; 24,823; -1,231 [-1,041] kg |
| pre-registered estimate: c; residual | 0.0025; 0.0020 [0.0019] kg | 0.0099; 0.24 [0.13] kg | 0.064; 43.5 [4.1] kg | 0.017; 0.37 [0.23] kg |

- **Sized for its own full-load push, silo_cold keeps 342 kg above the pad**, 22.8% of its
  uncharged payload gain of 1,498.8 kg (derived: 342.2 / 1,498.8; the uncharged gain from
  run A's variants table). The full_load offload row beside it, sized the same way at P_ref,
  leaves 10.59 t. Both payload gains are flown with the free kick: run A's variants table
  labels the uncharged +1,498.8 kg "an unthrottled/unconstrained upper bound: q-alpha above
  the baseline" (its run peaks at 129.9 Pa rad), and the payload case's run peaks at
  119.0 Pa rad, 1.59 times the pad's (the table above), so by the same rule the +342 kg is
  an upper bound (a payload case records no comparison flag); a q-alpha-constrained kick
  would lower it by an amount not measured. For scale: 342.2 kg is about 38 m/s of delta-v
  at the uncharged comparison's own rate (derived: 342.2 x 165.248 / 1,498.83; run A's
  summary.md, silo_cold's matched-payload attribution, d dv_margin +165.248 m/s), whose
  gravity + steering term is +56.4 m/s; the payload case carries no decomposition of its
  own, so how much of the 342 kg the free kick supplies is not measured.
- **At the physics high-mass end it falls 2,080 kg below the pad**: the adverse end of the
  band gives the vehicle less payload than having no silo at all. Its run also kicks above
  the pad's q-alpha (96.3 Pa rad, 1.29 times), so the deficit is an upper bound by the same
  rule (at least this deep), as is the step case's (108.5 Pa rad, 1.45 times); the outer
  high-mass case's run peaks below the pad's (55.2 Pa rad, 0.74 times) and meets none of the
  rule's three tests.
- The three flagged cases' deficits are quoted as their two-pass P_2* - P_ref with the
  residual estimate beside, as section 8 fixes; the flag does not block (its residual, at
  most 23.0 kg, against deficits of 1.1 to 7.8 t, changes no reading). The deficits lie
  close to the quadratic estimates for the physics high-mass end and the step row and
  between the linear and the quadratic for the outer high-mass end: section 7's bias
  statement (the linear rate overstates large deficits) held.
- No flight check on a payload case (deviation 28: its run flies its own P*, so the pad's
  envelope at P_ref is not its comparison).

## The release

The release load step is reported as a flag, not sized (D-SP7-10, D-SP7-19). D-SP7-39 fixes
its comparison: the same single-mode instant-step treatment applied to the pad's own MECO
shutdown. At the central headline (run A's metrics.json, silo_cold_s1_st `structure_flags`,
`structure_release_unload` and `structure_payload_limit`):

| quantity | the push's release (central, at x*) | the pad's own MECO under the same treatment |
|---|---|---|
| swing (peak of the release; the plateau's) | -4.389 g0 (-4.006 g0) | -5.195 g0 |
| stage-1 LOX bottom | -997.0 kPa gauge, -895.7 kPa absolute | +132.4 kPa gauge (the tank empty at MECO) |
| stage-1 RP-1 bottom | -319.5 kPa gauge, -218.2 kPa absolute | +162.7 kPa gauge |
| stage-2 LOX bottom | -161.6 kPa gauge, -60.3 kPa absolute | -231.7 kPa gauge (the tank full at MECO; MECO's ambient taken as 0) |
| stage-2 RP-1 bottom | +39.5 kPa gauge | +6.3 kPa gauge |
| common-dome reverse pressure | 363.3 kPa (the LOX side floored at zero absolute) | 129.6 kPa |
| upper-stack swing | -5.99 MN | -7.10 MN |
| payload limit (-2.0 / +6.0 g0) | swing -4.389 g0 beyond -2.0 g0: fires; n_peak 4.389 g0 inside +6.0 g0 | -5.195 g0, also beyond -2.0 g0 (the flag tests the push only) |

- The model says an instant release would separate the stage-1 LOX column (its bottom far
  below zero absolute), and the same treatment also separates stage 2's full LOX column at
  the pad's own MECO (-231.7 kPa gauge, deeper than the push's -161.6 kPa on that tank). So
  a column separation under the instant-step treatment is not specific to the push, while
  the stage-1 release is about 3.9 times deeper than stage 2's at MECO (derived: -895.7 kPa
  absolute against -231.7). A real drive's release and a real MECO are not instant steps.
  File B's lm_cmd_taper flies a stop taper to soften the release. Its softer release shows
  in the model only in the flags (swing -1.946 g0, stage-1 LOX bottom -230 kPa absolute, the
  release flag still firing), while its higher plateau costs 8.94 t of offload against
  lm_cmd ("The drive cases").
- The flag fires on every structural case of both files, every sweep point, every payload
  case and all eight arms (Caveats, "The flags"), the hot starts included (stage-1 LOX
  bottom about -100 and -114 kPa absolute at a swing of -1.6 g0). The payload-limit flag
  fires on every cold start and not on the hot starts, as section 8 expected.
- Nothing models propellant settling for the ignition 0.5 s after a release that the model
  flags as separating the LOX column (Limits): a risk against the assist that no number here
  measures. The hot starts' stage 1 is already firing when the model flags their release (it
  keeps thrusting through it, section 2(c)); nothing models what a LOX bottom at -100 and
  -114 kPa absolute would do to engines already running: a risk against the hot starts that
  no number here measures either (far shallower than the cold start's -896 kPa absolute, and
  a real release is not an instant step).

## What goes against the hypothesis

The hypothesis is that every m/s of ground-supplied velocity cuts the propellant the rocket
needs. Charging the push's structure undercuts it, stated as plainly as the headline:

- **The structure cancels most of the offload at the central coefficients.** 11.42 t of
  SP1's 41.26 t is left (27.7%). The modelled 6.31 t of structure costs 29.84 t of offload,
  about 4.7 kg of propellant per kg of structure (derived), the order of the slopes SP1's
  penalty rows measured (4.49 to 5.10 kg/kg).
- **With the structure charged the silo no longer beats the ideal-screening estimate.** The
  central's offload is 0.763 of the 14.98 t the README's ideal screening gives at 76.7 m/s
  (file C's 0.643 of 14.25 t); SP1's uncharged headline was 2.76 times it. Other rows still
  beat it, each with a closing decomposition (run A's summary.md, "stage-1 offload /
  screening offload" and Offload checks): narrowly the quasi-static row (1.003) and the 25%
  margin row (1.049), and the band's low-mass ends (1.58 unscaled, 1.91 scaled), the outer
  low end (2.08), the hot starts (1.09 and 1.22) and the 200 m silo (1.78). They beat it
  through the lighter stack's gravity + steering term in the cross-vehicle decomposition
  (`xv_gravity_steering_mps`: 46.8, 48.9, 72.7, 87.3, 94.8, 99.6, 84.5 and 81.7 m/s in that
  order, against the central's 36.0), as SP1's uncharged headline did (124.7 m/s). The
  stage-1 Isp -10% arm (1.012) also beats it, its decomposition explained (the arm record
  carries no split), and so do sweep 1's 200 and 300 m points (1.50, 1.74) and sweep 2's
  300 m point (2.14), each "explained" in the re-run's index (their split is not written).
- **The physics band reaches no offload.** At the band's adverse end the full-load push
  falls 243.7 m/s short of P_ref and the payload form loses 2,080 kg against the pad (two
  passes; residual estimate 0.137 kg; flown with the free kick above the pad's q-alpha, so
  at least that much by the run's own rule, "The payload form"); the outer envelope's
  adverse end falls 1,021.5 m/s short and loses 7,804 kg (two passes; residual estimate
  23.0 kg).
- **The push the constant_accel trajectory actually flies cancels all of it.** The instant
  step (DLF 2) leaves no offload (125.2 m/s short; payload deficit -1,087 kg (two passes;
  residual estimate 0.277 kg)). The headline's 0.5 s rise time is an assumed real drive, and
  a rise time at or below about 0.14 s (inside its 0.1-1.0 s range) is estimated (sizing
  only, S2's first pass) to give no offload too.
- **Short strokes give none at all.** At 25 and 50 m (38.35 and 54.24 m/s) the push feels
  the same 4 g0 and needs the same structure as at 100 m, while its uncharged offload is
  smaller: no offload at either, 60.2 and 18.3 m/s of delta-v short of P_ref at x = 0
  (payload deficit not flown: no payload case at these settings). The lowest exit speed that
  still offloads lies between 54.24 and 76.71 m/s (the sweep does not resolve the crossing),
  above the screening speeds of 38-54 m/s. Below it the shortfall falls from 60.2 m/s at
  38.35 m/s to 18.3 m/s at 54.24 m/s: the extra speed helped, but did not pay for the
  structure it needs.
- **A fast, short push sizes the upper stack and ends at no offload.** At 7 g0 (sweep 2's
  50 m, the same exit speed as the headline) dm is 16.05 t with stage 2 and the interstage
  sized, and the push falls 190.0 m/s of delta-v short of P_ref at x = 0 (payload deficit
  not flown: no payload case at these settings).
- **Every offloaded structural run kicks into a q-alpha well above the pad's.** The cold
  starts kick at the first lit instant, 0.5 s after release, and the hot starts at release;
  each offloaded structural run of file A peaks in q-alpha there, at 126.6 to 288.8 Pa rad,
  1.7 to 3.9 times the pad's 74.7 Pa rad (derived; the central 140.9, 1.89 times;
  metrics.json `offload.runs`). No angle-of-attack aerodynamics and no limit constrain it: a
  lateral load that the pad envelope the structure is sized against does not cover
  (Limits). The faster sweep points kick harder still: at sweep 1's 200 and 300 m the
  full-load runs reach 574.1 and 1,293.3 Pa rad, 7.7 and 17.3 times the pad's (the re-run's
  index, `peak_q_alpha`; derived ratios; the structural runs' values are not written and
  likely higher: Caveats, "Free kick").
- **Other plausible design choices leave little.** Through the thrust structure (Q5, at the
  headline's prominence) 5.97 t is left (14.5%); with the envelope capped at 4.0 g0, as a
  throttled MECO might cap it, 4.81 t (11.6%). Single in-range moves are estimated (sizing
  only, S2's first pass) to give no offload: eta_weld 0.70, the plate-limited Gerard row,
  4 carriage pads, k_ts at or above 0.3476 kg/kN on the thrust-structure row.
- **In payload terms the silo becomes marginal, and its one gain is an upper bound.** Sized
  for its own full-load push, silo_cold keeps +342 kg over the pad, 22.8% of its uncharged
  +1,499 kg; at the physics high-mass end it carries 2,080 kg less than the pad (two passes;
  residual estimate 0.137 kg). Both payload gains are flown with the free kick: run A's
  variants table labels the uncharged +1,498.8 kg "an unthrottled/unconstrained upper bound:
  q-alpha above the baseline", and the payload case's run peaks at 119.0 Pa rad, 1.59 times
  the pad's (`offload.runs` `peak_q_alpha`; derived ratio), so by the same rule the +342 kg
  is an upper bound (a payload case records no comparison flag); a q-alpha-constrained kick
  would lower it by an amount not measured, and 342 kg is about 38 m/s of delta-v at the
  uncharged comparison's own rate (derived; "The payload form"), so its sign is shown only
  under the unconstrained kick. The physics high-mass deficit is an upper bound by the same
  rule (1.29 times the pad's q-alpha).
- **The payload-limit flag fires on every cold start** (release swing -4.389 g0 against the
  payload's published -2.0 g0), with its MECO caveat beside it: the same treatment swings
  the pad's own MECO to -5.195 g0, so the flag measures the step treatment as much as the
  push. The release would also separate the stage-1 LOX column (-896 kPa absolute), with
  nothing modelling the settling before the ignition 0.5 s later.
- **Most unmodelled terms favour the assist** ("Limits"): the unthrottled envelope (the cap
  rows measure part of it: 0.94 t and 6.61 t of offload lost at 4.5 and 4.0 g0, derived from
  the central's x*), the release not sized, the transfer tube beyond its hoop, COPVs and
  engine mounts not charged, the four coefficients at their dm-lowering ends at the central,
  and the plausibility scaling of the band's low-mass end.

What the results show in the assist's favour, stated as plainly: the band's low-mass end
keeps more than half (28.57 t scaled, 23.68 t unscaled) and so does the outer envelope's
(31.12 t); a deeper silo at the same exit speed keeps 32.03 t at 300 m (2.0 g0 felt) for
360 m of facility and 1,769.8 kWh; a faster exit keeps more (31.62 t at 108.5 m/s; 44.73 t
at 132.9 m/s, an upper bound), for 320 and 480 m of facility, 2,380.9 and 3,484.6 kWh (the
structural runs) and 2.44 and 2.99 GW of peak drive power (the full-load point runs), but
those points' full-load runs kick at 103.6 and 127.9 m/s into a q-alpha of 574.1 and
1,293.3 Pa rad, 7.7 and 17.3 times the pad's (the re-run's sweep 1 index, `peak_q_alpha`;
derived ratios; the structural runs' values are not written and likely higher, since they
lift off 27.8 and 41.6 t lighter and at 100 m a run 42.8 t lighter peaks 1.75 times the
full-load run's; not measured, Caveats, "Free kick"); both hot starts keep 4.9 to 6.9 t more
than the cold start (with the exhaust caveat, which favours them, and their release flag:
under the instant-step treatment the stage-1 LOX bottom falls to -100 and -114 kPa absolute
while stage 1 is firing, and nothing models what that would do to engines already running, a
risk against the hot starts that no number here measures; a real release is not an instant
step); and every structural case of file A and every sweep point's structural run flies a
max-Q below the pad's (23,113.9 to 36,323.8 Pa against 37,191.4 Pa, unthrottled and
unconstrained; not a load benefit the model can claim, Caveats; every sweep point's
uncharged offload run flies above it), while every offloaded structural run of file A peaks
in q-alpha at its kick at 1.7 to 3.9 times the pad's (also unconstrained). Some omissions
and choices are conservative, working against the assist ("Limits"; Caveats): drag and
q-alpha bending in the pad's envelope (drag under 60 kg in the planning probe), the pad
release's own dynamic step, structural damping, a clean-sheet vehicle designed for the push
(RQ7; size not known), the push-time RP-1 pressure (-93.3 to -148.7 kg of dm, sizing only)
and the zero existing margin on the envelope (the 10% and 25% margin rows keep 13.27 and
15.70 t). Of the two results section 8 registered as favouring the hypothesis, neither
occurred: the physics band's adverse end ends at no offload, and the solved headline lies
0.3 t above its estimate (+315.0 kg), not far above it.

Neither for nor against the hypothesis (a robustness comparison between the forks): the two
fork tests split. On the README-loads fork the structure costs 26.84 t against the gate's
29.84 t, 10.05% apart: C1 fires "depends on the vehicle masses", 16.0 kg past its threshold
(about 1.3 times the two costs' summed resolution of about 11.9 kg, derived: resolved under
section 3's rule, but narrowly), while C2 on the share left (25.5% against 27.7%) reads
"nearly the same on both forks".

**On file B's drives** (run B, "The drive cases"; part 2, section 8's "what would undercut"
list, each item checked against the run):

- **No drive keeps more than half.** All nine linear-motor central cases cancel most of
  SP1's uncharged 41.26 t, from 2.48 t (6.0%, lm_cmd_taper) to 18.27 t (44.3%,
  lm_cmd_hot). Six of the nine keep less than silo_cold_s1_st's 11.42 t and lm_cmd ties
  it. Only two keep more: lm_cmd_hot by 6.85 t, a hot start that the unmodelled exhaust
  favours, and lm_fixed_sled22 by 0.22 t.
- **On the same 100 m silo, both drives that exit faster leave less once charged.** Only two
  of the nine exit faster than silo_cold at x*, and both keep less, by different mechanisms.
  lm_fixed exits 0.44 m/s faster (77.15 m/s) and keeps 82.0 kg less, about 24 times R. Its
  stack is lighter than M (x* of 11.34 t, above its dm of 6.38 t), so it feels more (n_q
  4.041 against 4.006 g0), but that adds only 72.1 kg of dm. Its structure costs 2.14 t more
  than silo_cold's against 2.06 t more uncharged offload (derived from U and U - X), and
  most of that 2.14 t is exit speed, not felt load: under the fixed force the charged stack
  at x*, 38.4 t heavier than the uncharged one, exits at 77.15 m/s against 80.64 m/s. At
  silo_cold's 4.73 kg of offload per kg of dm the 72.1 kg costs about 0.34 t, leaving about
  1.80 t to the lost speed; lm_fixed_target, the same force released at v_e, costs
  4.73 kg per kg too, against lm_fixed's 5.02 (all derived: U - X over dm). So at x* its
  0.44 m/s gain earns less than its extra dm costs. lm_fixed_hot exits 12.53 m/s faster
  (89.24 m/s) and keeps 4.07 t less: its thrust adds to F_max on the track (felt 5.378 g0;
  its stack 1.66 t heavier than M at x*, `vs_pad.delta_liftoff_mass_kg`), and its structure
  costs 45.38 t against silo_cold's 29.84 t (an overcharge of its n_peak included:
  "Limits"), more than its 11.46 t larger uncharged offload. That larger offload is the hot
  start's (9.41 t of it over lm_fixed's): lit at push start, it exits at 93.85 m/s
  uncharged and is at full thrust at its release (its ramp ends at 2.00 s, its release
  comes at 2.48 s), while lm_fixed lights 0.5 s after its release and ramps for 2 s
  (events.csv of the two uncharged runs). The run does not split the two. At an unchanged
  exit speed the acceleration law's hot start, lit 0.849 s into its push, gains 4.75 t of
  uncharged offload over lm_cmd (both at 76.71 m/s), so part of the 9.41 t may be the
  timing (an inference across different ignition times, not measured). Uncharged it burns
  3.99 t of its loaded propellant on the track (`propellant_burned_on_track_kg`), which is
  not part of the offload. This is narrower than "a faster exit keeps less": on file A's
  sweep 1, longer strokes exit faster and keep more (31.62 t at 108.5 m/s, 200 m; 44.73 t
  at 132.9 m/s, an upper bound), with their own caveats (above).
- **A gentler release costs offload that the model measures and buys only flags.**
  lm_cmd_taper keeps 8.94 t less than lm_cmd at the same 76.71 m/s exit. Its benefit
  shows only in the flags, because the model sizes no release step: a release swing of
  -1.946 g0 inside the payload's -2.0 g0 (-0.996 g0 of it the release step, 0.950 g0 the
  undamped residual of the rise and the taper's start), and the stage-1 LOX bottom at
  -230 kPa absolute against -896 kPa. Its release flag still fires.
- **A slower exit can leave more.** lm_fixed_sled22 exits 1.43 m/s slower than silo_cold
  at x* (1.88 m/s slower than lm_fixed) and keeps 0.22 t more (0.31 t more than
  lm_fixed). Its 22 t carriage takes part of the fixed force, which lowers the felt load
  and the structure by more than the lost speed costs. So the exit speed alone does not
  rank the charged offloads (RQ1-structural-2d-derived_drive_exit_speed.png). The
  carriage itself is not sized ("Limits"), and part 2 placed this reading within reach
  (+0.36 t estimated).
- **More force for the same full-load exit costs offload**: lm_fixed_r07 (12% more F_max)
  keeps 5.68 t less than lm_fixed. **So does the air column**: the sealed shaft keeps
  2.29 t less than the vented lm_fixed, at the 5.24 m bore the fairing needs (D-SP7-54),
  under a uniform adiabat.
- **The force-limited hot start loses to its own cold start** (HS "less": -3.99 t), though
  its uncharged offload is 9.41 t larger. The rise formula overcharges its n_peak (against
  it; of order 1 t of x* on a rough estimate, not measured: "Limits"), and on that estimate
  the reading does not move. The acceleration-law hot start gains (+6.85 t), with the
  exhaust caveat favouring it.
- **The flags fire on the linear motor too.** The payload-limit flag fires on seven of the
  nine linear-motor central cases, on the swing (-2.67 to -4.51 g0 against -2.0 g0). The
  MECO caveat applies: the same treatment swings the pad's own MECO to -5.195 g0. The
  release flag fires on all nine. On the taper and on both hot starts the stage-1 LOX
  bottom still falls below zero absolute (-230, -114 and -418 kPa).

What file B shows in the assist's favour, stated as plainly: lm_cmd_hot keeps 18.27 t
(44.3%), the most of any structural case of file B. That is still below half, and it comes
with the exhaust caveat favouring it and with its release flag (the stage-1 LOX bottom at
-114 kPa absolute while stage 1 is firing). lm_fixed_sled22 keeps 0.22 t more than
silo_cold_s1_st. Uncharged, four of the six force-law pushes offload more than silo_cold
(lm_fixed, lm_fixed_r07, lm_fixed_hot and lm_fixed_sled22; up to 52.73 t on lm_fixed_hot),
but no structure is charged there. Of part 2's two "would favour" readings, neither
occurred: lm_fixed's faster exit did not pay for its structure (82.0 kg less, beyond R the
other way), and no linear-motor row keeps more than half.

## Limits

Section 10's list, with the direction each would move the structural offload where known:

- Propellant settling for the ignition 0.5 s after a release the model flags as separating
  the LOX column: not modelled (a risk against the assist). Added here, beyond section 10's
  list: the hot starts' feed through a release the model flags while stage 1 is firing
  (stage-1 LOX bottom -100 and -114 kPa absolute under the instant step): not modelled (a
  risk against the hot starts).
- The LOX transfer tube beyond its hoop, COPVs, engine mounts loaded in reverse by the push,
  feedlines: not charged (against the assist); joints and weld lands beyond what the
  non-optimum factors carry (against); lateral and bending loads in the shaft (against);
  fatigue on a reused stage (against); a multi-mode response (the single-mode factor is not
  conservative at the upper stations for short rise times; against).
- q-alpha bending in flight: in the pad's envelope it would raise the envelope and lower dm
  (for the assist; leaving it out is conservative); on an offloaded flight whose q-alpha is
  above the pad's (the central's 1.89 times; 1.7 to 3.9 times on every offloaded structural
  run of file A; at sweep 1's 200 and 300 m even the full-load runs reach 7.7 and 17.3
  times) it would add load the envelope may not cover (against). Section 10 wrote this
  bullet for an offloaded flight "whose max-Q is higher than the pad's", as SP1's uncharged
  headline's was (3.35% above). That premise did not hold: with the structure charged,
  every structural case of both files and every sweep point's structural run flies a max-Q
  below its pad's (23,113.9 to 36,323.8 Pa against 37,191.4 Pa; file C's central 37,082.8
  against its pad's 42,732.6 Pa), and the load the envelope may not cover is the q-alpha
  above, not max-Q.
- Drag in the pad's envelope (left out, D-SP7-15): it would raise the envelope's compression
  and lower dm (for the assist; under 60 kg in the planning probe). The pad release's own
  dynamic step (the envelope is quasi-static): a factor there would raise the envelope and
  lower dm (for the assist; not measured). A damped structural response would lower the
  single-mode peak the factor charges (for the assist).
- The pad's envelope flown unthrottled (MECO at 5.195 g0; Falcon 9's MECO acceleration is
  not public): a throttled MECO would lower the envelope and raise dm, so the unthrottled
  envelope favours the assist; the 4.5 and 4.0 g0 cap rows measure part of it (0.94 and
  6.61 t of offload, derived).
- The release step reported as a flag, not sized: sizing it as one more push load case could
  only add mass or leave dm unchanged, so leaving it out favours the assist.
- The payload adapter and the payload: flagged against the published +6.0/-2.0 g limits, not
  sized (against).
- A strengthened vehicle's own pad flights carrying dm: outside this comparison (against a
  mixed fleet). A clean-sheet vehicle designed for the push (RQ7): for the assist, size not
  known.
- From SP1: no throttle and no max-Q-constrained offload; partly filled tanks of a fixed
  vehicle, the mixture ratio kept, no ullage, residual or centre-of-gravity effect; a
  massless carriage and a vented shaft; nothing models the exhaust in the shaft (it favours
  the hot starts); the planar point-mass model, the generic C_D table and the ICAO
  atmosphere with its isothermal extension; sweep-optimized guidance; the gate vehicle's
  +14.3% calibration miss.
- The sizing's own scope: a first-order station sizing with coefficients whose centrals and
  ends were set after the planning probe (section 2(b)); the band's ends are the extremes a
  screened search found, not bounds; the band's sets are found at SP1's headline push and
  only placed at the others; the sensitivity arms carry no verification; the stage-1
  dry-mass arm reaches the sizing only through the push's interface force and its perturbed
  pad's envelope (deviation 17); sweep points get no paired pad, pad control or arms, and
  their offloaded runs are not written.
- One vehicle class (a medium launcher; RQ8 untouched).

For file B's drives, part 2, section 10 adds these items. Each direction follows part 1's
convention ("against the assist": modelled, it would lower x*), "no direction" where an
item touches no x*, and run B's numbers replace the estimates where the run gives them:

- The motor's thermal and electrical limits beyond P_max (duty cycle, heating, current and
  voltage limits; P_max is a mechanical cap at the carriage and F_max a force cap, nothing
  else): not modelled, direction not known. A further force cap would lower the exit speed
  (U, against the assist) and the plateau force (dm, for it); a further power or voltage cap
  would lower the exit speed only (against). Run B shows both net signs where the force on
  the vehicle and the exit speed fall together (lm_fixed_sled22 +0.31 t and lm_fixed_sealed
  -2.29 t against lm_fixed), while more force at the same full-load exit costs offload
  (lm_fixed_r07, 12% more F_max: 5.68 t less).
- The converter and the energy storage: the electricity is the drive work over an assumed
  efficiency of 0.5. Storage losses and the supply of the peak electrical power (2.19 to
  3.59 GW at x*) are not modelled. They move energy and power only, never dm or x*.
- The carriage's own structure and its interface hardware: the carriage is massless, or a
  22 t lumped mass, and never sized; direction not known. Under the force law a heavier
  carriage lowers the vehicle's force and its exit speed together (CM: +0.31 t against
  lm_fixed). Under the acceleration law it reaches the vehicle only once a cap binds (none
  bound, E2). Interface hardware carried by the vehicle would add to dm (against).
- The shaft flow above the vehicle and the gas in the sealed shaft (all inferred, not
  computed):
  - the air the vehicle pushes out of the mouth (design 4.8: about 77 kN at the exit for a
    3.7 m bore, which D-SP7-54 found the fairing cannot pass; at the 5.24 m bore a real
    shaft for this vehicle needs, larger by about the area ratio, about 2), acting on the
    vehicle against its motion (against the assist);
  - the cooling of the trapped gas near the end of lm_fixed_sealed's small-gap stroke (the
    uniform adiabat biases F_p low: against; heat from the walls would act the other way;
    the p_0 A bound holds regardless);
  - the open shaft's hydrostatic drop above the carriage on lm_fixed_sealed (F_p biased
    high by up to about 1.2% of F_p(L), about 26 kN: for the assist, so leaving it out is
    conservative);
  - the vents a vented shaft needs (about the bore's area): the vented variants assume
    them, and smaller vents would leave a column force on the vehicle (against).
- The release mechanism: every release is an instant separation. lm_cmd_taper flies one way
  to soften it, whose effect shows only in the flags, and no release hardware is sized
  (direction not known).
- The carriage's braking: closed-form at a constant 5 g0 (D-SP7-12). It sets only the
  facility length, with no braking phase in the trace (no direction: it touches no x*).
- The exhaust in the shaft for the two hot starts (SP1's caveat: back-pressure, heating,
  the carriage in the plume): on back-pressure and heating it favours the hot starts. On
  lm_fixed_hot its direction is mixed: under the force law impingement 0 adds the whole
  thrust to F_max, which raises its felt load (5.378 against 4.041 g0 for lm_fixed at x*)
  and its dm (against the assist), so the omission's net direction there is not known.
- **KI-067, with its direction.** Take a hot linear-motor push lit before its push start
  (a hot hold). Its F_int is taken at rest at push start, although the startup ramp on the
  clamp was still lowering it by about T. A single mode started at ignition exceeds the
  charged F_peak by up to 0.456 MN (2.3%) in the 2-10 Hz band (S4b's probe: a 20 t
  carriage, impingement 0.5). Charged, it would raise such hot cases' dm (against the
  assist), so leaving it out is unconservative. Neither of file B's hot starts holds on
  the clamp, and run B's records confirm it: no hold phase; lm_fixed_hot's `ignition`
  event at push start, where its delivered thrust is 0; lm_cmd_hot's 0.849 s into its push.
  So the at-rest premise is exact for both and this bias does not reach them. Their thrust
  ramps are flown on the track and charged as forcings of F_int's mode.
- Added here, beyond section 10's list: **the rise formula's excess on lm_fixed_hot.** Its
  charged n_peak is the rise formula's 5.936 g0, 0.126 g0 above the flown history's own
  phase-free bound (5.810 g0, `n_bound_g`), which already bounds the single-mode response of
  the flown push. D-SP7-52's larger-of rule gives the motor's 0.5 s rise DLF (1.1273) to the
  whole rise from 0.996 g0 at rest to 5.378 g0, including the 1.12 g0 that the rest of the
  thrust's ramp adds over the next 1.5 s (felt 4.251 g0 at 0.5 s and 5.371 g0 at 2.0 s, the
  ASSIST rows; about 7.5 periods of the 5 Hz mode, which follows it nearly
  quasi-statically). Against the model's own single-mode response, this overcharges the
  elements n_peak governs: its tanks, transfer tube, interstage and stage 2 (against the
  assist; a multi-mode response, not modelled, is a separate item above). The force-governed
  aft skirt and load ring equal lm_fixed's to 0.02 kg. Its effect on x* is not measured: of
  order 0.2 t of dm and 1 t of x* on a rough slope derived across two cases that also differ
  in stack mass (lm_fixed_hot's n-governed elements carry 2,628.7 kg more than lm_fixed's
  over n_peak 4.429 to 5.936 g0, about 1,744 kg per g0; its structure costs 5.04 kg of
  offload per kg of dm, U - X over dm). On that estimate no reading moves: HS stays "less"
  (-3.99 t) and LM "less" (-4.07 t), and lm_fixed_hot still loses the most to structure
  (45.38 t against lm_cmd_taper's 38.78 t).

The known issues of steps S4 to S5a (TODO.md) that reach file B (part 2, section 10), with
their direction in the same sense:

- KI-048 (the scan for a watch value passed over inside one step; drive_limit not scanned):
  every linear-motor push. On lm_fixed_target the power limit and the release coincide at
  v_e. Direction not known; size at the scan's resolution.
- KI-049 (the delivered-thrust clamp unsplit in ascent burns lit after release): every
  cold variant's ascent, at about the 1e-10 level, as in SP1 and run A. Direction not
  known.
- KI-070 (the flown history's single-mode bound is phase-free and counts a curving load to
  first order; conservative, 0.002 to 0.006 g0 on n_peak on an lm_fixed_r07-like push): it
  may raise the charged load where the bound governs. Run B's DLF lies above the rise
  formula's 1.1273 on lm_fixed (1.1274), lm_fixed_r07 (1.1281) and lm_fixed_sealed (1.1319),
  so the bound governed n_peak there. On lm_fixed_hot the rise formula governs n_peak (5.936
  against the bound's 5.810 g0, `n_bound_g`; that excess, larger and also against the
  assist, is the item above on D-SP7-52's rule, not this bias) and the bound governs F_peak,
  the charged peak interface force: `structure_F_peak_N` equals the bound's `f_bound_N` to
  the bit (24.64 MN), so the bias reaches lm_fixed_hot too, by about 9.7 kN (0.04% of
  F_peak; its effect on x* is not measured). That excess is derived, not recorded: the rise
  formula F_0 + DLF (F_q - F_0) on the records' F_0 (the first ASSIST row's
  `interface_force_N`) and F_q (`peak_interface_force_N`) with `dlf_rise` gives
  24,632,168.7 N against `f_bound_N`'s 24,641,869.1 N, and the same formula reproduces
  F_peak to 0.01 N on every linear-motor case where it governs (lm_cmd, lm_cmd_taper,
  lm_cmd_hot, lm_fixed_target, lm_fixed_sled22; silo_cold's row charges its ramped plateau
  from rest, not its flown step, so the recipe does not apply to it). On the lm_cmd family,
  lm_fixed_target and lm_fixed_sled22 the two agree (DLF 1.1273; F_peak within 2e-5 N of
  `f_bound_N`). silo_cold's constant_accel row has no flown bound. A second-order count
  would lower it (for the assist), so leaving it out is conservative. Its release bound
  overstates the release swings that TP and the payload-limit flag read. That is
  conservative for the flags, and in TP it understates the gentle stop's gain.
- KI-071 (the bound depends on the scan resolution at a corner; dm(x) can step by about 1%
  of the load where a corner crosses a sub-phase start): the force-law variants whose power
  corner moves with the offload. No `offload_nonmonotone` fired, so no step was large enough
  to reverse m_res(x)'s slope; a smaller kink in m_res(x) was not looked for. The
  convergence check exercised the corner on lm_fixed (a `power_limit` event at x* in both
  chains) but does not bound x*'s dependence on the scan resolution ("Convergence").
  Direction not known.
- KI-074 (on linear-motor runs the minima, `drive_force_peak_N` and the track-normal peaks
  stay sampled): the reported drive-force peaks read low between samples (the felt-g and
  interface-force maxima are exact). No direction: no x* depends on them.
- KI-076 (a sealed bore is checked only against the body diameter): lm_fixed_sealed's
  5.24 m bore was set to clear the 5.2 m fairing by D-SP7-54, not by the code's check. No
  direction on the numbers.
- KI-047 and KI-057 (cap records): the lm_cmd family only if a cap binds; none bound (E2).
  No direction: records only.
- KI-053, KI-058, KI-081, KI-082, KI-083 and KI-084 (the scene template, two video-frame
  fits, the display file's vented-shaft note, two manual gaps): the readers' pages and
  documents of run B, never its numbers. No direction.

Part 2, section 10 lists the known issues that do not reach file B, each with the setting
that keeps it out.

## How each pre-registered reading came out

Every reading and expectation of sections 7 to 9, taken as written, with its pre-registered
estimate (sizing only, none a target) and its result. "As expected" means the same verdict;
a departure is named with its size.

| pre-registered reading or expectation (section) | pre-registered estimate | result | how it came out |
|---|---|---|---|
| Reproductions within 0.002 kg (9): silo_cold_s1, the three penalty rows, silo_hot_ramp_s1, silo_cold_200m_s1, file C's silo_cold_s1, the nine uncharged sweep points | SP1's recorded values | every one 0.0 kg (the same bits; sweep points equal at 12 significant digits) | reproduced |
| Pads' P* equal P_ref within 0.002 kg; arm pads equal SP1's arm P_ref (9) | the same bits | 0.0 kg for the three pads (the re-run's pad the same, reproduced) and the six perturbed arm pads (the two drive-efficiency arms use the nominal pad; all eight arms' P_ref equal SP1's) | as expected |
| Stage-1 pad controls (7, 9) | no_offload, m_res(0) -0.0016 kg, consistency pass (both files) | file A m_res(0) -0.00164 kg (bound 1.618 kg), file C -0.00159 kg (1.28 kg); both pass, bit-identical to SP1 | as expected |
| H1 survives: the adverse end keeps more than 20.63 t (8) | not expected (phys_hi no offload) | phys_hi no offload | not fired, as expected |
| H2 cancels most (8) | about 11.1 t (26.9%), 9.5 t below half | 11.42 t (27.7%), 9.21 t below half | fired, as expected; +315.0 kg above the estimate (+2.8%), in the direction section 7 expected (a chord places x low; the synthetic timing case had been 297 kg low) |
| H3 undecided, the plausibility-scaled low-mass end (8) | no offload to about 28.5 t | no offload (243.7 m/s; -2,080 kg) to 28.57 t | fired, as expected |
| H3 undecided, the unscaled low-mass end (8) | no offload to about 23.7 t | no offload to 23.68 t | fired, as expected; both quoted, each naming its end |
| H4 cancels all (8) | not expected | central ok | not fired |
| O1 survives (outer) / undecided (outer) (8) | undecided: no offload to about 31.1 t | no offload (1,021.5 m/s; -7,804 kg) to 31.12 t | "undecided (outer)" fired, as expected |
| R silo_cold_s1_st_qs (8) | cancels most, 14.73 t | 15.02 t (36.4%) | as expected; +295 kg |
| R silo_cold_s1_st_step (8) | cancels all: about 143 m/s short, deficit about -1,231 kg (120 m/s, -1,041 kg quadratic) | cancels all: 125.2 m/s short, deficit -1,086.9 kg (residual estimate 0.277 kg) | as expected; the shortfall and deficit near the quadratic estimate |
| R silo_cold_s1_st_full (8) | cancels most, 10.30 t | 10.59 t (25.7%) | as expected; +286 kg |
| R silo_cold_s1_st_ts (8) | cancels most, 5.77 t (1.13 t of equivalent dm from no offload) | 5.97 t (14.5%) | as expected; +204 kg |
| R silo_cold_s1_st_m10 / _m25 (8) | cancels most, 12.95 / 15.42 t | 13.27 t (32.1%) / 15.70 t (38.1%) | as expected; +314 / +285 kg |
| R silo_cold_s1_st_cap45 / _cap40 (8) | cancels most, 10.17 / 4.80 t (cap40 0.94 t of equivalent dm from no offload) | 10.48 t (25.4%) / 4.81 t (11.6%) | as expected; +310 / +5.6 kg |
| R silo_hot_full_s1_st (8) | cancels most, 15.26 t on an estimated x0 of 39,506 kg | 16.34 t (39.6%) on a solved x0 of 38,980.4 kg | as expected in verdict; +1,078 kg on the estimated x0 (that estimate 526 kg high, for the assist); re-placed on the solved x0 the estimate is 14.69 t, 1,646 kg below the solve: opposite to the shift bias section 7 named for x0 below 41.26 t (below the table) |
| R silo_hot_ramp_s1_st (8) | cancels most, 16.22 t, 4.4 t below half | 18.27 t (44.3%), 2.36 t below half | as expected in verdict; +2,055 kg (+12.7%), nearer half than estimated; about twice the stated biases' +1.1 t at its x0 (section 7's extrapolation carried there, derived; below the table) |
| silo_cold_200m_s1_st, read under S2 (6, 8) | about 26.6 t | 26.69 t, 260 m facility, 2.50 g0 felt | as expected; +57.5 kg |
| HS silo_hot_full (8) | keeps more by about 4.2 t; uncharged about 1.8 t lower; cost about 24.2 against 30.2 t | +4.92 t; uncharged -2.28 t; cost 22.64 against 29.84 t | fired as expected ("more"); +0.76 t above the estimated lead (derived: 4,916.0 - 4,153.3 kg = +762.7 kg; the estimate on the estimated x0) |
| HS silo_hot_ramp (8) | keeps more by about 5.1 t, 4.75 t of it from the larger uncharged; cost about 29.8 against 30.2 t | +6.85 t; uncharged +4.75 t; cost 27.74 against 29.84 t | fired as expected; +1.74 t above the estimated lead (derived: 6,853.7 - 5,113.3 kg = +1,740.4 kg) |
| S1 (8) | lowest exit speed that offloads 76.71 m/s (100 m); no offload at 38.35 and 54.24 m/s (about 66 and 24 m/s short; 62 and 19 on the quadratic); x* rising above it | the same: no offload at 25 and 50 m, 60.2 and 18.3 m/s short at x = 0 (payload deficit not flown; the re-run, Amendment 1); 11.42, 31.62, 44.73 t at 100, 200, 300 m, rising | fired as expected; both shortfalls below the linear estimates and within 2 m/s of the quadratic ones (60.2 against 66 (62); 18.3 against 24 (19)); the 50 m point, within reach in section 8 (its margin about 2.4 t of offload on the curve, 5-7 t on the payload rate): no offload held, 18.3 m/s short at x = 0 (24 m/s linear, 19 quadratic), so S1's 76.71 m/s stands; the 200 and 300 m points 3.73 and 5.61 t above their estimates (+13.4% and +14.3%), the direction section 7 expected for x0 above 41.26 t but more than its "about 3 t and 4 t" |
| S2 (8) | no offload at 50 m (stage 2 sized; about 215 m/s short, 180 on the quadratic), then about 11.1, 26.6 and 32.0 t, rising | no offload at 50 m (stage 2 sized; 190.0 m/s short at x = 0, payload deficit not flown; the re-run), 11.42, 26.69, 32.03 t, rising | fired as expected; the shortfall between its linear and quadratic estimates (190.0 against 215 (180)); x* +315.0, +57.5 and +6.2 kg above the estimates at 100, 200 and 300 m (11,105.3, 26,628.9 and 32,024.8 kg; derived from the unrounded estimates in the tables .json), the chord's direction |
| A, the +/-10% arms (8) | about 8.1 to 14.8 t, every arm below half | 8.55 to 15.07 t; all 8 ok, decompositions explained (residuals at most 2.2e-9 m/s) | fired, as expected; each arm +108 to +520 kg above its estimate, with no pattern in x0 (the arms bullet below the table) |
| P, the payload cases (8) | about +306 kg (+343 quadratic) central; about -2,449 kg (-2,048) phys_hi | +342.2 kg; -2,080.4 kg | fired, as expected; both near the quadratic estimate; the central's sign, "within reach" in section 8, held under the free kick (an upper bound by the run's own rule: its q-alpha 1.59 times the pad's, the phys_hi case's 1.29 times; "The payload form") |
| The no-offload rows' payload deficits (7) | phys_hi about -2,449 kg; outer_hi of order -7 to -10 t; step about -1,231 kg | -2,080.4; -7,804.3; -1,086.9 kg | as expected; each inside or near its quadratic estimate (phys_hi's and step's flown with the free kick above the pad's q-alpha, upper bounds by the run's own rule, at least this deep; outer_hi's below it; "The payload form") |
| The no-offload rows' shortfalls (7) | phys_hi about 291 m/s (241 quadratic); outer_hi 800-1,400 m/s; step about 143 m/s (120) | 243.7; 1,021.5; 125.2 m/s | as expected; phys_hi and step near the quadratic estimates; outer_hi between the linear (1,403) and the quadratic (831), inside the 800-1,400 range |
| C, file C's central against its own U (8) | cancels most, about 7.5 t (20.8% of 36.0 t) | 9.16 t (25.5% of 36.01 t) | fired "cancels most", as expected; +1,689 kg (+22.6%), the largest relative departure of any solved x*; opposite to the shift bias section 7 named for x0 below 41.26 t (below the table) |
| C1, the cost (6 item 10, 8; D-SP7-45) | "nearly the same" (5.4% apart), not decided by the estimates (a fork slope 4.9% shallower than the gate's flips it) | "depends on the vehicle masses more than the calibration difference suggests" (10.05% apart) | **fired the other way**; the fork's cost is 0.941 of its own estimate (derived: 26,842.4 / 28,531.3 kg) and the gate's 0.990 of its own (derived: 29,842.7 / 30,157.7 kg), the chord bias both placements share, so the fork's slope is about 0.951 times the gate's (derived: 0.9408 / 0.9896), at section 7's flip point (0.951; 0.9513 derived: 0.9 x 30,157.7 / 28,531.3) and 0.0006 below it, which is the 16.0 kg margin: about 1.3 times the two costs' summed resolution (about 11.9 kg; derived), resolved under section 3's rule, narrowly |
| C2, the share left (6 item 10, 8; D-SP7-45) | "depends" (22.9% apart), not decided by the estimates (a slope 4.4-11.2% shallower flips it) | "nearly the same on both forks" (8.0% apart) | **fired the other way**, by the same fork slope |
| The headline sentence's fills (8) | p1, p1m, p2m, p2 about -897, +132, -232, -162 kPa; phi 0.739, r 1.76; stage-1 LOX barrel, 71%, axial buckling, the pad's MECO; the barrel's increment 25.6 kg (0.4%) | -896, +132, -232, -162 kPa; 0.739, 1.76; the same element, share, mode and case; 25.1 kg (0.40%) | as expected |
| Flags (7, 8) | release on every structural case and sweep point, hot starts included; payload limit on every cold start, every sweep point, file C's central and all four payload cases (on the swing; on n_peak above +6.0 g0 too for _step, _outer_hi and sweep 2's 50 m point), not on the hot starts; upper stack on _step, _outer_hi, _cap40, sweep 2's 50 m and the _step and _outer_hi payload cases only; payload_unconverged on three payload cases | every flag's state so (hot starts' stage-1 LOX bottom -100 and -114 kPa absolute against about -103 and -119 estimated); beyond section 8's n_peak list, the payload-limit flag's n_peak clause also holds on the _step and _outer_hi payload cases (6.996 and 6.998 g0; the same pushes at x = 0) | as expected in every flag's state; the n_peak clause on those two payload cases departs from the list (not from any flag's state); beyond the list also: _cap40's flight check (2.34 kg, threshold 1 kg) and an informational grid-retry flag on outer_hi's solve, neither blocking; beyond section 8's list also: the release flag on the four payload cases (the list names them for the payload-limit and upper-stack flags only) and the release and payload-limit flags on the eight arms (none on the upper stack, no flight-check exceedance; Caveats, "The flags") |
| The cap rows' share of the unthrottled-envelope bias (10) | about 0.9 and 6.3 t of offload | 0.94 and 6.61 t (derived from the central's x*) | as expected |
| The convergence check (1, 9) | tightened x* within 0.1%; dm moved below 0.1 kg with doubled stations | +0.0378 kg (3.3e-6); +6.2e-6 kg (the committed script's run of 2026-10-19, the same bits as its first, uncommitted run: deviation 42) | passed |
| The frozen sets recompute (9) | both files pass | both pass at the run's code (317.5 s, 290.0 s) | passed |
| Every no-offload case with its shortfall (9) | the file A rows and the sweep points | the file A rows: yes; sweep 1's 25 and 50 m and sweep 2's 50 m: no shortfall on the first sweep's disk; on the re-run 60.2, 18.3 and 190.0 m/s, each with "payload deficit not flown" | **failed on the first sweep** (a reporting defect), **passes on the re-run** (D-SP7-48, Amendment 1, step S3c; Caveats) |
| Amendment 1's reproduction check: the re-run against the first sweep, every pre-existing column of both indexes by name, cell by cell at %.12g (Amendment 1) | every cell the same (the physics code unchanged) | 365 cells (sweep 1, 5 rows) and 292 (sweep 2, 4 rows), 657 in all, 0 differing; new columns: each case's `dv_shortfall_mps` | passed |
| The no-offload sweep points' shortfalls (7; Amendment 1) | about 66, 24 and 215 m/s (62, 19 and 180 on the quadratic) | 60.2, 18.3 and 190.0 m/s | the sweep 1 points below the linear estimates and within 2 m/s of the quadratic; sweep 2's 50 m point between the two |
| What would undercut the hypothesis (8) | the headline below half; no-offload rows (step, adverse ends, short strokes); the lowest exit speed that offloads above 38-54 m/s; the payload-limit flag at the central | all four occurred (the short strokes 60.2 and 18.3 m/s short) | undercut, as expected |
| What would favour it (8) | the band's adverse end above half (not expected); a solved headline far above the estimate | adverse end no offload; the headline 0.3 t above the estimate | neither occurred |
| Runtime (11) | run A about 59 min at the checkpoint's rate (26-34 at SP1's, 56-80 pessimistic); sweep A about 34 min; run C about 5 min; the convergence check 333-351 s | 64.8, 32.9 and 5.6 min; the sweep's re-run 32.3 min (beside it, of this session, only read-only review scripts and a worktree checkout outside the repository; sessions of two other projects were active on the machine: Reproduction); the convergence check 277.5 s from the committed script with nothing else of this session running (another project's session was active: Convergence; its first, uncommitted run about 374.5 s beside other agents' processes) | run A 5.8 min over the checkpoint-rate estimate, inside the pessimistic range; the rest inside or below their estimates |

The departures from the estimates, set against the direction section 7 gave each bias:

- In the direction section 7 said (against the assist): sweep 1's 200 and 300 m points,
  +3.73 and +5.61 t, and silo_hot_ramp_s1_st, +2,055 kg (all three on section 7's list of x0
  above 41.26 t, where the shift places x low if the slope keeps flattening; at 200 and
  300 m by more than its "about 3 t and 4 t"); and the chord bias on the headline's own push
  (estimate minus solve: -204 to -315 kg on the central and the design-axis rows, -5.6 kg on
  the 4.0 g0 cap row), which matches the one measured before the run on a synthetic file
  (-297 kg). Section 7 sized the shift at 200 and 300 m only. Its extrapolation (the slope
  linear in the offload level through SP1's three segments, integrated from x0 over the
  estimate's dm; derived) gives, chord included, about +2.8 and +4.4 t at 200 and 300 m,
  +0.28 t at the central and about +1.1 t at silo_hot_ramp's x0 (4.75 t above 41.26 t), so
  about 1.0 t of silo_hot_ramp's +2,055 kg is beyond the stated biases, as with
  silo_hot_full (+1.33 t beyond the chord, last bullet): both hot starts depart upward, by
  1.6 to 2.1 t (+1,646 and +2,055 kg), whichever side of 41.26 t their x0 lies, and their
  structural cost per kg of dm, 4.41 and 4.47 kg/kg (derived: 22,644.1 / 5,134.2 and
  27,739.5 / 6,210.0), lies below the cold start's 4.73; why is not measured.
- The arms do not measure the shift bias. All six perturbed arms lie above their estimates,
  by +108.0 to +520.3 kg (stage-1 dry mass +10% +520.3, -10% +108.0; Isp +10% +461.1,
  -10% +307.1; C_D +10% +469.5, -10% +158.7; derived from the arms table below): the chord
  bias's direction and about its size (the central's +315.0 kg), whatever their x0
  (38,668.0 to 44,464.5 kg, section 7's arm table). Section 7 left the arms' own slopes'
  sign unknown, so neither the Isp -10% arm (+307.1 kg, x0 3.2 t above 41.26 t, on section
  7's list of x0 above it) nor the Isp +10% arm (+461.1 kg, x0 2.6 t below 41.26 t, where
  the shift would place x high) measures it.
- In the direction section 7's payload-rate bullet said (the linear rate likely overstates
  the large deficits, against the assist): every no-offload shortfall lies below its linear
  estimate, by about 6 m/s at the two short strokes (60.2 against 66, 18.3 against 24 m/s)
  to about 382 m/s on the outer high-mass end (1,021.5 against 1,403 m/s), with the step row
  125.2 against 143, the physics high-mass end 243.7 against 291 and sweep 2's 50 m point
  190.0 against 215 m/s (derived differences); every payload deficit is smaller than its
  linear estimate (-1,086.9 against -1,231, -2,080.4 against -2,449 and -7,804.3 against
  -9,984 kg); and each of these nine numbers lies nearer its quadratic estimate than its
  linear one (the rows above).
- Opposite to the shift bias section 7 named for x0 below 41.26 t, which it said favours the
  assist and places x high: file C, +1,689 kg (+22.6%) on the shift estimate and +2,454 kg
  on the level-matched 6,710 kg (derived), which also flips both fork tests; and
  silo_hot_full_s1_st, +1,646 kg on its estimate re-placed on the solved x0 (tables
  section 7) and +1,335 kg on the level-matched 15,001 kg (derived; that one on the
  estimated x0, itself 526 kg high, for the assist). Beyond the chord bias's share (about
  0.3 t of each, if it is the headline's +315.0 kg, which leaves about +1.37 t for file C
  and +1.33 t for silo_hot_full re-placed, derived), the placement's stated biases do not
  explain these two, and neither case's own slope (offload lost per kg of structure at its
  level) is measured: the fork's cost implies a slope about 0.951 times the gate's once both
  placements' chord bias is taken out (the C1 row), and silo_hot_full's cost per kg of dm is
  4.41 against the central's 4.73 kg/kg (derived: 22,644.1 / 5,134.2 and
  29,842.7 / 6,305.2). Both departures favour the assist.

The arms one by one (run A's summary.md, offload "Sensitivity"; pre-registered estimates
from section 7):

| arm | P_ref [kg] | x* [kg] (estimate) | change against the nominal 11,420.2 kg | dm at x* [kg] |
|---|---|---|---|---|
| stage-1 dry mass +10% | 25,661.0 | 11,819.6 (11,299.3) | +399.3 | 6,338.1 |
| stage-1 dry mass -10% | 26,456.3 | 11,024.2 (10,916.2) | -396.1 | 6,272.5 |
| stage-1 Isp_vac +10% | 29,927.4 | 8,545.1 (8,084.0) | -2,875.1 | 6,386.7 |
| stage-1 Isp_vac -10% | 22,478.3 | 15,065.6 (14,758.5) | +3,645.3 | 6,216.7 |
| C_D scale +10% | 26,015.5 | 11,532.9 (11,063.4) | +112.6 | 6,303.2 |
| C_D scale -10% | 26,093.5 | 11,306.2 (11,147.5) | -114.1 | 6,307.2 |
| drive efficiency +/-10% | 26,054.4 | 11,420.2 (the nominal solve reused) | 0 | 6,305.2 |

As in SP1, the stage-1 Isp sets the range; every arm stays below half. The arms carry no
verification search (`OFFLOAD_SENSITIVITY_BASIS`), and the dry-mass arm reaches the sizing
only through the push's interface force and its perturbed pad's envelope, never through the
stage-1 station loads (deviation 17).

**Part 2 (file B)**: every reading and expectation of part 2, sections 7 to 9, taken as
written, with its estimate (sizing only, placed on SP1's penalty curve; none a target) and
its result from run B. "As expected" means the same verdict; a departure is named with its
size.

| pre-registered reading or expectation (part 2, section) | pre-registered estimate | result | how it came out |
|---|---|---|---|
| The eleven blocking checks (9) | each to pass | all eleven pass ("The drive cases") | as expected |
| The cross-commit check (3, 9): silo_cold_s1 against SP1's, silo_cold_s1_st against run A's, 0.002 kg | the same bits | 0.0 kg and 0.0 kg | reproduced |
| lm_cmd's uncharged x* against SP1's 41,262.908 kg, 0.25 kg (9) | 41,262.9 kg | 41,262.909 kg, +0.0014 kg | reproduced |
| lm_cmd_taper's uncharged x* against SP1's 41,262.908 kg (7, an expectation: the same release state) | 41,262.9 kg | 41,262.972 kg, +0.064 kg (R 2.55 kg) | met |
| The pad's P* against P_ref (3, 9) | 26,054.396243494975 kg, the same bits | 0.0 kg | as expected |
| The stage-1 pad control (4, 9) | no_offload, m_res(0) -0.0016 kg, consistency pass | m_res(0) -0.00164 kg (bound 1.618 kg), pass | as expected |
| E1 (8): lm_fixed_hot_s1_st raises the upper-stack flag | met; push 8.06 against 7.10 MN; stage 2 sized by 124.5 kg and the interstage by 74.5 kg | met; 8.114 against 7.095 MN; stage 2 131.2 kg, the interstage 78.4 kg | as expected |
| E2 (8): no `drive_cap` on the lm_cmd family | met | met (no cap event, flag or bound on the three variant runs and the six cases' runs) | as expected |
| Read beside (8): lm_cmd_s1_st against silo_cold_s1_st; lm_cmd_hot's pair against run A's silo_hot_ramp pair | 0 (R 3.4 kg); 46,013.437 and 18,273.917 kg | +0.0046 kg; +0.0014 and +0.00004 kg | within R; reproduced |
| RB on all nine (8) | cancels most, 2.45 t (lm_cmd_taper) to 16.22 t (lm_cmd_hot; 18.27 t on run A's hot ramp), 5.9% to 39.3% | cancels most on all nine, 2.48 to 18.27 t, 6.0% to 44.3% | as expected; lm_cmd_hot at run A's value, 2.36 t below half |
| LM, lm_cmd (8) | the same within the resolution (0.00 t) | the same within the resolution (+0.0046 kg) | as expected |
| LM, lm_cmd_taper | 8.65 t less | 8.94 t less | as expected |
| LM, lm_cmd_hot | 5.11 t more (6.85 t on run A's pairs) | 6.85 t more | as expected, at run A's pairs |
| LM, lm_fixed (within reach) | 0.14 t less | 0.08 t less (82.0 kg; 24 times R) | as expected; nearer the threshold |
| LM, lm_fixed_target (within reach) | 0.35 t less | 0.37 t less | as expected |
| LM, lm_fixed_r07 | 5.61 t less | 5.76 t less | as expected |
| LM, lm_fixed_hot | 7.36 t less | 4.07 t less | as expected in verdict; 3.29 t nearer silo_cold than estimated (the hot start's upward departure, below the table) |
| LM, lm_fixed_sled22 (within reach) | 0.36 t more | 0.22 t more | as expected; nearer the threshold |
| LM, lm_fixed_sealed | 1.92 t less | 2.37 t less | as expected |
| HS, lm_cmd_hot against lm_cmd (8) | more: +5.11 t; uncharged +4.75 t; cost 29.79 against 30.16 t | more: +6.85 t; uncharged +4.75 t; cost 27.74 against 29.84 t | as expected |
| HS, lm_fixed_hot against lm_fixed | less: -7.21 t; uncharged +9.96 t; cost 49.39 against 32.22 t | less: -3.99 t; uncharged +9.41 t; cost 45.38 against 31.98 t | as expected in verdict; 3.22 t nearer |
| TS (within reach) | 0.20 t less; uncharged 1.97 t less | 0.29 t less; uncharged 2.11 t less | as expected |
| CM (within reach) | 0.50 t more | 0.31 t more | as expected; nearer the threshold |
| SS | 1.77 t less | 2.29 t less | as expected |
| TP | 8.65 t less; the release flag fires on both (-230 against -897 kPa absolute; swing -1.95 against -4.39 g0); the payload-limit flag does not fire on the taper (its swing 0.054 g0 inside -2.0 g0, within reach) | 8.94 t less; fires (-230 against -896 kPa; -1.95 against -4.39 g0); does not fire (swing -1.946 g0) | as expected |
| PL | 5.47 t less | 5.68 t less | as expected |
| The flags (7) | release on every structural case; payload limit on all but lm_cmd_taper and lm_cmd_hot; upper stack on lm_cmd_taper (0.10% over; stage 2 0.9 kg) and lm_fixed_hot only; `release_speed_not_reached` on lm_fixed_target's variant run only; stage-1 LOX bottoms -897 (silo_cold, lm_cmd), -929, -907, -860, -809, -738, -423, -230 and -119 kPa absolute | every flag's state so; upper stack 7.102 against 7.095 MN on the taper (stage 2 0.9 kg); LOX bottoms -896, -928, -907, -860, -809, -737, -418, -230 and -114 kPa | as expected; each LOX bottom within 5 kPa of its estimate |
| The distance from no offload of lm_cmd_taper and lm_fixed_hot (8, within reach) | 2.45 and 3.75 t | 2.48 and 7.35 t | both offload |
| dm'(x) (7): -0.020 to +0.0084 kg/kg; the acceleration law about -0.014 to -0.020; lm_fixed +2.9e-4, lm_fixed_target +1.5e-4; lm_fixed_r07, lm_fixed_sled22 and lm_fixed_sealed -0.7e-4 to -4.9e-4; lm_fixed_hot +8.4e-3; no `offload_nonmonotone` | as stated | the chord slopes (dm(x*) - dm(0)) / x* (derived from `structure_dm_kg` and `structure_dm_x0_kg`): -0.0141 to -0.0201 on the acceleration law; +1.74e-4 and +1.40e-4; -4.98e-4, -1.91e-4 and -8.3e-5; +8.39e-3; no `offload_nonmonotone` | as expected, each sign the estimate's (a chord over [0, x*], not the local slope) |
| The fixed point (7) | 6 to 7 sizings, contraction 0.006 to 0.021 | 6 to 7 sizings; contraction 0.0056 to 0.0211 | as expected |
| What would undercut (8) | lm_fixed_hot faster and less (88.95 m/s, about 7.4 t less); lm_fixed within reach (77.12 m/s, 0.14 t less); lm_cmd_taper 8.65 t less at the same exit; lm_fixed_sled22 slower and more (within reach); the payload-limit flag on seven of nine; every row below half | lm_fixed_hot 89.24 m/s, 4.07 t less; lm_fixed 77.15 m/s, 82.0 kg less; lm_cmd_taper 8.94 t less; lm_fixed_sled22 75.27 m/s, 0.22 t more; seven of nine; every row below half | all occurred |
| What would favour (8) | lm_fixed's faster exit paying beyond R (within reach); any row above half (not expected) | 82.0 kg less; none | neither occurred |
| The linear-motor convergence check (1, 9) | tightened x* within 0.1%; the shipped x* equal to run B's within 0.002 kg | +0.0274 kg (2.4e-6); 0.0 kg | passed |
| Runtime (11) | run B about 44-45 min at S7a's rates (20 at SP1's set M, 54 pessimistic); the convergence check about 5-10 min | 41.8 min; 389.7 s of parts (6.5 min) | inside the estimates |

The structural x* against the estimates (part 2, section 7: the placement and, in
brackets, the placement anchored on run A's solved silo_cold_s1_st; result - estimate
derived):

| case | uncharged U: estimate; result [kg] | structural x*: estimate (anchored); result [kg] | result - estimate (anchored) [kg] |
|---|---|---|---|
| silo_cold | 41,262.9; 41,262.9 | 11,105.2 (11,420.2); 11,420.2 | +315.0 (0.0) |
| lm_cmd | 41,262.9; 41,262.9 | 11,105.2 (11,420.2); 11,420.3 | +315.1 (+0.0) |
| lm_cmd_taper | 41,262.9; 41,263.0 | 2,450.7 (2,765.7); 2,479.0 | +28.3 (-286.7) |
| lm_cmd_hot | 46,013.4; 46,013.4 | 16,218.5 (16,533.5); 18,273.9 | +2,055.4 (+1,740.4) |
| lm_fixed | 43,181.3; 43,322.0 | 10,960.9 (11,276.0); 11,338.2 | +377.3 (+62.2) |
| lm_fixed_target | 41,207.1; 41,216.1 | 10,756.7 (11,071.7); 11,046.4 | +289.7 (-25.3) |
| lm_fixed_r07 | 42,655.9; 42,760.9 | 5,491.9 (5,806.9); 5,658.7 | +166.8 (-148.2) |
| lm_fixed_hot | 53,143.7; 52,727.5 | 3,750.1 (4,065.1); 7,347.5 | +3,597.4 (+3,282.4) |
| lm_fixed_sled22 | 42,148.0; 42,218.1 | 11,463.0 (11,778.0); 11,643.3 | +180.3 (-134.7) |
| lm_fixed_sealed | 40,668.8; 40,703.2 | 9,188.6 (9,503.7); 9,049.8 | -138.8 (-453.9) |

- **The chord bias** (concave penalty curve: a chord places x low, against the assist;
  part 1 measured +204 to +315 kg at the headline push) shows on the cold cases at
  silo_cold's push (lm_cmd +315.1 kg, the same as silo_cold's +315.0) and at about its
  size on lm_fixed (+377.3) and lm_fixed_target (+289.7). It is smaller on lm_fixed_sled22
  (+180.3), lm_fixed_r07 (+166.8) and lm_cmd_taper (+28.3), and reversed on
  lm_fixed_sealed (-138.8 kg, the only solve below its estimate). Anchoring on run A's
  solve removes the shared part: +0.005 kg for lm_cmd, -25.3 to +62.2 kg for
  lm_fixed_target and lm_fixed, and -134.7 to -453.9 kg for the sled, the power-limited
  drive, the taper and the sealed shaft. Why these four lie below their anchored estimates
  is not measured. Each case's own slope (offload lost per kg of structure at its level)
  is not measured either; the run gives only the cost per kg of dm (derived: U - X over
  dm at x*): 4.73 kg/kg for silo_cold, 4.85 for the taper, 4.73 for lm_fixed_target and
  5.02 to 5.11 for the other cold force-law cases.
- **The hot starts depart upward, as part 2, section 7 expected, lm_fixed_hot by more
  than run A's hot starts did.** lm_cmd_hot lands on run A's silo_hot_ramp_s1_st
  (+2,055.4 kg against the estimate, the same departure run A measured). lm_fixed_hot
  lands 3,597.4 kg above its estimate (+96%; run A's two hot starts departed by 1.6 to
  2.1 t), on an uncharged offload 416.2 kg below its estimate. That U estimate came from
  the 1-for-1 burn rule and the cold sweep's speed dependence, whose sign part 2, section
  7 called not known. So the structural departure is not U's: the structure costs
  45.38 t against an estimated 49.39 t, 4.0 t less. Why is not measured. Both departures
  favour the assist.
- **U's interpolation** (a chord on sweep 1's concave curve places U low, against the
  assist, by 4 to 330 kg off v_e): every cold force-law U lies above its estimate (lm_fixed
  +140.7, lm_fixed_r07 +105.0, lm_fixed_sled22 +70.1, lm_fixed_sealed +34.4 kg), in that
  direction. lm_fixed_target's U lies 9.0 kg above its estimate; part 2, section 7 said its
  altitude worth placed U about 5 to 8 kg low (against the assist).

## KI-006: M2 and M4 over gamma* +/- 0.5 deg

- **The structural offload cases, the uncharged offload cases, the payload cases and the
  arms carry no M2 to M5**, by design: their cross-vehicle decomposition is checked for
  closure only. KI-006 cannot be answered for them from these outputs.
- **Run A's four variant comparisons** (silo_cold, silo_cold_200m, silo_hot_full,
  silo_hot_ramp_on_track: the full-load payload comparisons against the pad): closure and
  attribution pass; M2 (diagnostic), M3 and M4 (blocking) pass at gamma*_ref and at both
  neighbours (robust); M5 n/a. M2 ratios 0.449, 0.449, 0.913 and 0.782; M4 shares 0.144
  (range 0.063-0.216), 0.144 (0.063-0.216), 0.138 (0.054-0.211) and 0.124 (0.060-0.179)
  (metrics.json `comparison`).
- **Run C's silo_cold comparison**: all pass and robust; M2 0.422 (0.347-0.498), M3 0.687,
  M4 0.112 (0.023-0.188).
- **Run B's ten variant comparisons** (silo_cold and the nine linear-motor variants, each a
  full-load payload comparison against the pad, uncharged): screening status ok on all
  ten; M2 (diagnostic), M3 and M4 (blocking) pass at gamma*_ref and at both neighbours
  (robust); M5 n/a. M2 ratios 0.449 on silo_cold, lm_cmd, lm_cmd_taper, lm_fixed,
  lm_fixed_target and lm_fixed_r07, 0.439 on lm_fixed_sled22, 0.424 on lm_fixed_sealed,
  0.781 on lm_cmd_hot and 0.825 on lm_fixed_hot; M4 shares 0.124 to 0.147 (ranges 0.058
  to 0.225) (run B's metrics.json `comparison`).
- **At the sweep points** the checks belong to each point's full-load payload comparison,
  not to its offload solves. M2 (diagnostic) fails at sweep 1's 25 m point (0.098, range
  -0.031 to 0.227, both neighbours fail) and 50 m point (0.294, 0.199-0.390, one neighbour
  fails, so not robust), the same values SP1 recorded for these points; M4 (blocking) passes
  at gamma*_ref and at both neighbours at all nine points (shares 0.127 to 0.186). As in
  RQ3-2d and SP1, M2 fails where the cold start's in-air startup is large against the head
  start (the slow releases). Source: each point's metrics.json `comparison.checks_m2`,
  `checks_m4` in the sweep's re-run (results/silo_structure_2d/20261019T172327Z), and its
  summary.md, Checks; the first sweep's values are the same (the index columns reproduce,
  Amendment 1).

## Convergence

Exit criterion 6 and section 1, read from the check's report (scratch, outside the
repository), written by docs/findings/scripts/sp7_convergence.py as committed at 0a12c36
(documents only; its src/, configs/, experiments/, tests/, pyproject.toml and uv.lock equal
1b5f9d4's, `git diff --quiet 1b5f9d4 0a12c36 -- ...` exits 0), run on 2026-10-19 from
06:34:53Z to 06:39:58Z with nothing else of this session running (part walls 38.0, 46.1,
44.3, 0.7, 47.3, 33.8 and 67.3 s, 277.5 s in all, against section 11's 333-351 s). The
session's records do not cover other Claude Code sessions on the machine, and a session of
another project wrote its transcript files inside the window (their file times only, not
their contents), so the machine is not shown idle; no number depends on it (the same bits as
the first run, below), the 277.5 s may. It solves silo_cold_s1_st of file A (its pad,
silo_cold and that case, read from the committed file) at the shipped budget and under
`SearchContext.tightened(checks.convergence)` (every search and final tolerance divided by
10, the max-step caps times 0.5), each chain with its own pad P* as P_ref and as the
envelope's flight, the fixed point's 1e-6 kg tolerance unchanged.

- The shipped chain reproduces run A to 0.0 kg (P_ref 26,054.396243494975 kg; x*
  11,420.246638573297 kg; dm 6,305.185585283194 kg; verification P* 26,054.397684198262 kg).
- Tightened: P_ref 26,054.395519976406 kg (0.0007 kg lower, derived: 26,054.396243 -
  26,054.395520); x* 11,420.284416087732 kg (44 evaluations, no flags; verification
  +0.0003 kg). **x* moves by +0.0378 kg, 3.3e-6 relative, against 0.1%: passes.**
- Stations doubled (200 to 400 per barrel, on a scratch copy of the structure file differing
  from the committed one in that line only), sizing only at the shipped x*: **dm moves by
  +6.2e-6 kg (6,305.185585 to 6,305.185591 kg), against 0.1 kg: passes**; nearly all of it
  in the stage-1 LOX barrel.
- The numbers are a check, not a finding. The check first ran on 2026-10-16 (18:32:41Z to
  18:40:13Z, at HEAD ac5c6bd, after the three runs had ended) from the uncommitted working
  tree, before the script was committed: a departure from section 1's "a committed script",
  logged as deviation 42 of the phase file (the code it imports was the run's code; its
  parts took 374.5 s beside other agents' processes). The committed run of 2026-10-19 gives
  the same bits on every number above.

**The linear-motor x*** (exit criterion 6's "one linear-motor structural x*", registered in
part 2, section 1). This is read from the check's report (scratch, outside the repository;
report.json, sha256 91a2b6ab76a13739186c077e6f1c9beea24e947710c3a919436f8ba9cf9705fa),
written by docs/findings/scripts/sp7_lm_convergence.py as committed at b291518. That commit
holds documents only: its code paths equal run B's commit 642e11e's, and the report
records `git diff --quiet 642e11e b291518 -- src configs experiments pyproject.toml uv.lock
tests` quiet in each of its parts. The check ran on 2026-11-04 from 02:57:04Z to 03:03:48Z,
after run B, one part at a time and with nothing else of this session running. Part walls:
33.2, 55.6, 39.0, 74.3, 103.6 and 84.1 s, 389.7 s in all, plus 0.3 s for the report, against
part 2, section 11's "about 5-10 min". It solves lm_fixed_s1_st of file B (its pad, lm_fixed
and that case, read from the committed file) twice: at the shipped budget and under
`SearchContext.tightened(checks.convergence)` (every search and final tolerance divided by
10, the max-step caps times 0.5). Each chain flies its own pad, whose P* is its P_ref and
whose flight is its envelope. Each chain's push is flown with that chain's own context
(the transform's `push_context` replaced by the tightened one, as S4b's test does: nothing
tightens the push automatically). The fixed point's 1e-6 kg tolerance is unchanged, and
each chain's x* is verified by an independent payload search at its own budget.

- The shipped chain reproduces run B to 0.0 kg (P_ref 26,054.396243494975 kg; x*
  11,338.21677533504 kg; dm 6,377.263265780975 kg; 40 evaluations; verification +0.0013 kg).
- Tightened: P_ref 26,054.395519976406 kg (0.0007 kg lower); x* 11,338.244185975396 kg (41
  evaluations, no flags; dm 6,377.26328685691 kg; verification +0.0005 kg). **x* moves by
  +0.0274 kg, 2.4e-6 relative, against 0.1%: passes** (the registered rule: both solves ok,
  the tightened x* within 0.1% of the shipped one, the shipped one within 0.002 kg of run
  B's). In both chains the push at x* logs a `power_limit` event before its release (the
  sub-phase boundary of KI-071 that moves with x), so the check exercised it.
- **What it does not bound.** The report's `not_tightened` lists what neither chain
  tightens (not exhaustive): the LTG finite-difference steps, brackets, penalties and
  false-root guard; the gamma* grid (15 points), the refine's iteration cap (30) and the
  payload search's backoff cap (4); brentq_rtol (8.9e-16, at its floor); the track-peak
  scan resolution (`metrics.TRACK_PEAK_SCAN_POINTS`, 256 points per sub-phase), on which
  KI-071's dm step depends; the time-series sampling interval (`integrator.sample_dt_s`,
  0.05 s), whose rows give the envelope's load cases; and the structure's fixed-point
  tolerance (1e-6 kg) and iteration cap (25). So the check does not bound x*'s dependence
  on KI-071's track-peak scan resolution or on the sampling step, nor on the rest of that
  list.
- **Which case it measures.** The check flies lm_fixed_s1_st only, a push whose power
  corner comes 0.0149 s before its release. The tolerance sensitivity of the other eight
  linear-motor cases is not measured. Among what it leaves unexercised: lm_fixed_r07's
  long power-limited sub-phase (its corner at 1.82 s of a 2.69 s push, KI-071's
  long-sub-phase case), lm_fixed_hot's thrust on the track, the sealed column's state and
  the 22 t carriage.
- The numbers are a check, not a finding. Run B's checks script read the report (its check
  9). It recomputed the registered rule, the verifications, the same-code record (`git
  diff` run again for the recorded HEAD) and the scripts' sha256 at each recorded HEAD, and
  agreed with the report's own verdicts. The machine's other processes during the check are
  not recorded beyond this session; no number depends on them, the wall times may.

## Reproduction

The three registered commands (section 1), from a clean checkout of 1b5f9d4, in the
repository root:

    uv run python -m launchsim run experiments/silo_structure_2d.yaml
    uv run python -m launchsim sweep experiments/silo_structure_2d.yaml
    uv run python -m launchsim run experiments/silo_structure_2d_readme.yaml

and the sweep's re-run under Amendment 1, alone, from 2b343d7:

    uv run python -m launchsim sweep experiments/silo_structure_2d.yaml

- Experiment files: experiments/silo_structure_2d.yaml and
  experiments/silo_structure_2d_readme.yaml, byte for byte as committed in cbbd7bc (the
  pre-registration), unchanged at 2b343d7; the structure files as committed in 45e39d4
  (sha256 under "Provenance"). Results: the four directories of "Provenance"; only their
  top-level summary.md files are tracked.
- The three commands of 2026-10-16 were started together, with plots, from 1b5f9d4, as
  section 1 registers: run A at 2026-10-16T17:15:10Z, sweep A at 17:15:19Z, run C at
  17:15:26Z (the launcher's own stamps). They ended at 18:19:59Z, 17:48:15Z and 17:21:03Z,
  each console log ending "exit 0". The directories' last file times: 18:19:58Z (run A, 394
  files), 17:48:15Z (sweep A, 141 files) and 17:21:03Z (run C, 55 files). No suite, app or
  agent ran the code beside them (the phase file's section 11 records this at the runs'
  start; the frozen-sets test, the convergence check's first run and the tables script's
  first run all started after run A ended at 18:19:59Z). Wall times: run A 64.8 min, sweep A
  32.9 min, run C 5.6 min, against section 11's estimates of about 59, 34 and 5 min at the
  checkpoint's rate.
- The re-run was started at 2026-10-19T17:23:21Z (the launcher's stamp), with plots, from
  2b343d7, the S3c tracker commit after Amendment 1 (74eb3c8; step S3c's code 1e4c732 and
  77e1691), and ended at 17:55:41Z, exit 0 (32.3 min, against section 11's about 34 min for
  sweep A): results/silo_structure_2d/20261019T172327Z, 141 files, last file time 17:55:41Z,
  no FAILED.txt. Its git record reads dirty for the reason given under "Provenance": a
  departure from the "clean commit" of Amendment 1 and D-SP7-48, accepted by the session
  (deviation 45). Amendment 1 also registers a quiet machine (section 11: no suite, no
  app-driving agent). By the session's scratch file times, two things of this session ran
  beside the re-run: review pass 1's agents read the results files with standard-library
  Python scripts (written 17:24 to 17:33Z; their reports by 17:39Z), and step S4's workflow
  wrote its brief and checked out a git worktree of 2b343d7 outside the repository at
  17:27Z, whose virtual environment dates from 18:00:46Z, after the re-run ended; the brief
  for the scripts' fix was written at 17:40Z and that agent's first scratch file dates from
  18:02Z, so whether it worked before 17:55:41Z is not shown. No suite, app or launchsim
  command of this session appears beside the re-run in those records. They do not cover
  other Claude Code sessions on the machine, and sessions of two other projects wrote their
  transcript files inside the window (their file times only, not their contents), so whether
  the machine was quiet in section 11's sense is not established beyond this session. No
  number depends on it (the 657 cells reproduce to the same bits); the 32.3 min wall time
  may.
- After the three runs of 2026-10-16, at their code: tests/test_structure_search.py::
  test_frozen_sets_reproduce for both files (18:27:27Z to 18:37:52Z, each its own foreground
  command). The convergence check, from the committed script at 0a12c36 (2026-10-19,
  "Convergence"), with OUT a directory outside the repository (the script refuses one inside
  it), PART each of shipped-pad, shipped-solve, shipped-verify, stations, tightened-pad,
  tightened-solve and tightened-verify in that order, and then the report:

      uv run python docs/findings/scripts/sp7_convergence.py --out OUT --part PART
      uv run python docs/findings/scripts/sp7_convergence.py --out OUT --part report \
          --run-a results/silo_structure_2d/20261016T171513Z

- The sizing-only tables (from b82417b) and the derived figures (from a5b21b8, the figures
  script after review passes 2 to 4) (no offload solved; the tables script flies file A's
  pad afresh, whose P* equalled run A's P_ref to 0.000000 kg; the figures script only
  reads):

      uv run python docs/findings/scripts/sp7_structure_tables.py
      uv run python docs/findings/scripts/sp7_structure_figures.py

  The first writes docs/findings/RQ1-structural-2d-tables.md and
  RQ1-structural-2d-tables.json (`--markdown-only` rebuilds the markdown from the saved data
  without flying anything); its header records the commit it ran at and how that commit's
  code differs from the run's. The second reads run A, the sweep's re-run, run C and the
  tables' JSON and writes the derived figures below, and copies the five structure figures
  from the runs' plots/ folders.
- The three scripts under docs/findings/scripts/ were written at S7a and committed at
  0a12c36 (documents only); after review pass 1 the tables and figures scripts were fixed
  (the figures: the re-run directory, the no-offload points' shortfall labels, caveat lines;
  the tables: the re-run directory, the list of code differences, a caveat line) and
  committed at b82417b (documents only). The tables (.md and .json) cited here were
  generated from b82417b on 2026-10-19T18:11:12Z (72.9 s; the header records that the code
  differs from the run's commit 1b5f9d4 in src/launchsim/results_io.py and summary.py only,
  reporting, Amendment 1). The figures were drawn from b82417b with the tables (about
  18:11Z) and again from 9b91473 (b82417b with the felt-load figure's subtitle shortened to
  fit) at 2026-10-19T18:43Z; both draws are replaced. After review passes 2 to 4 the
  figures script was fixed again (the footers' free-kick q-alpha clauses for the headline's
  structural cases and both sweeps, the thrust-structure row's sizing-only break-even and
  S0's move of k_ts's central, the exhaust remark's direction, "zero existing margin
  (adverse for the assist)", the felt-load figure's full break-even list and highest
  structural x*, the sweep footers' full column lists, sweep 2's right-panel labels beside
  their own points, and the headline legend's orange solved-x* marker) and committed at
  a5b21b8 (documents only). The ten figures cited here were drawn from a5b21b8 by a command
  started at 2026-10-19T20:24:42Z (file times 20:24:44Z to 20:24:46Z; the five derived ones
  redrawn; the five copied ones byte-identical to run A's and run C's plots). The section 9
  checks script was committed at 9b91473, run there at 18:43Z, and re-run unchanged at
  a5b21b8 at 20:24:46Z (its output above; all ten PASS).
- The checks: `uv run python docs/findings/scripts/sp7_s7a_checks.py` (read-only; exits 0
  only when all ten pass). The first drafts of the tables and the derived figures
  (2026-10-16, drawn and redrawn from 18:35Z to about 18:56Z) came from the uncommitted
  working tree and are replaced.

**Run B** (file B; part 2, section 1's command), alone, with plots, from a clean checkout of
642e11e in the repository root:

    uv run python -m launchsim run experiments/silo_drive_2d.yaml

- Started at 2026-11-03T23:19:44Z (the launcher's stamp) and ended at 2026-11-04T00:01:31Z,
  exit 0: 41.8 min, against part 2, section 11's about 44-45 min at S7a's measured rates
  (about 20 min at SP1's set M, 54 min at its pessimistic set). The directory's last file
  time is 2026-11-04T00:01:31Z (summary.md); 388 files, no FAILED.txt. Its git record reads
  dirty false, which `results_io.git_info` writes only when no tracked file outside results/
  is modified and no untracked file outside results/ is one that git does not ignore (its
  `git status --porcelain` excludes the results tree and lists no ignored file). No suite,
  app-driving agent or other command of this session ran beside it. Other projects'
  processes were running on the machine (a Blender MCP server, and a VideoSearchDB uvicorn
  server with two celery processes, all since 2026-10-29), so the machine was not idle. No
  number depends on that; the wall time may.
- Experiment file experiments/silo_drive_2d.yaml as committed in 331891d (part 2), unchanged
  at 642e11e and b291518; the structure file as committed in 45e39d4 and the vehicle file
  unchanged since SP7's start commit 22c62e9 (sha256 under "Provenance"). Results: only the
  directory's top-level summary.md is tracked.
- The linear-motor convergence check, after run B, from b291518, with OUT a directory
  outside the repository (the script refuses one inside it), PART each of shipped-pad,
  shipped-solve, shipped-verify, tightened-pad, tightened-solve and tightened-verify in
  that order, each in its own process, and then the report:

      uv run python docs/findings/scripts/sp7_lm_convergence.py --out OUT --part PART
      uv run python docs/findings/scripts/sp7_lm_convergence.py --out OUT --part report \
          --run-b results/silo_drive_2d/20261103T231946Z

- The blocking checks, after the convergence check, from b291518 (read-only; exit 0 only
  when all eleven pass; TEXT and JSON are the output paths, whose committed copies are
  docs/findings/RQ1-structural-2d-drive-checks.txt and .json):

      uv run python docs/findings/scripts/sp7_s7b_checks.py \
          --run-b results/silo_drive_2d/20261103T231946Z \
          --convergence OUT/report.json --out-text TEXT --out-json JSON

- The drive figures, read-only (they fly nothing), by the script committed with this
  note at step S7b. `--check` compares the plotted x*, U, dm1 + dm2 and dm2, the release
  speeds and positions and the drive-force and drive-power peaks with their records,
  re-read independently from metrics.json and the ASSIST rows, and exits 1 on a mismatch
  (it passed). The footers' facts listed under "Figures" are checked before any figure is
  drawn; the footers' other numbers (the q-alpha values, the caps, the corner speed, the
  column force, the power-cap spans, sweep 1's points) are read from the records and
  printed, not re-checked:

      uv run python docs/findings/scripts/sp7_drive_figures.py --check

## Figures

Copied unchanged (byte for byte) from the runs' plots/ folders: the structure figure of a
case shows the required wall thickness along stage 1's stations (and stage 2's where the
push sized it), the pad envelope against the push with the governing mode per station, and
dm by element. In the headline's, the thrust-structure row's and file C's figures the label
"stage1.lox_barrel" sits left of its line, over the RP-1 barrel's: the LOX barrel's line
starts at z 20.9 m (20.4 m in file C's figure; the copies are byte for byte, so the
placement is plots.py's). These are the runs' own plots and carry none of the note's caveat
lines. Each is a first-order station sizing on the gate vehicle (+14.3% high,
CAL-f9-leo-2d; file C's on the README-loads fork, +8.33%) against the pad's own unthrottled
envelope at zero existing margin (D-SP7-03), with the instant release flagged, not sized
(D-SP7-10, D-SP7-19). All but the step figure print "rise_time (DLF 1.127)": an assumed
0.5 s real-drive rise time that the constant_accel trajectory does not fly (it flies the
step, DLF 2: the step row). Their cases' runs were flown with the free kick, each peaking
in q-alpha at its kick above its pad's: the headline 140.9 Pa rad and the ts row 128.5
(1.89 and 1.72 times the pad's 74.7); at x = 0 the step row 106.2 and the phys_hi row 92.4
(1.42 and 1.24 times; run A `offload.runs`, the table under "The headline table"; derived
ratios); file C's central 207.8 (1.98 times its own pad's 105.2; run C); with no
angle-of-attack aerodynamics and no structure charged for it (Caveats, "Free kick"). The ts
figure's x* = 5.973 t also carries the row's sizing-only break-even (no offload at k_ts
0.3476 kg/kN or above) and S0's move of k_ts's central (about +2.4 t on the row's expected
x*; "Beside the number").

- RQ1-structural-2d-silo_cold_s1_st_structure.png: the headline case at x* = 11.42 t (run A,
  plots/silo_cold_s1_st_structure.png); the governing station is the RP-1 barrel's top (push
  6.35 mm against the envelope's 3.35 mm, ring + common Z).
- RQ1-structural-2d-silo_cold_s1_st_step_structure.png: the step row (DLF 2) at x = 0,
  stage 2 sized. As drawn (plots.py's placement; the copy is byte for byte):
  "stage1.common_dome" sits under its push point (z 19.4 m, 7.85 mm) with its own drop line
  through it; in the stage-2 inset "stage2.transfer_tube" sits over stage2.common_dome's
  envelope square (z 50.4 m, 2.08 mm), with that dome's drop line through it, away from its
  own min-gauge point at about z 46.7 m, 1.65 mm (beside the RP-1 aft dome's, at the same
  height), and the "stage2.rp1_aft_dome" label lies between the two; the stage-2 LOX
  barrel's push line and a triangle marker cross the start of "stage2.forward_dome"; and
  the governing annotation's first line overlaps the inset's "z [m]" label, its leader
  crossing the inset's 46 and 48 tick labels.
- RQ1-structural-2d-silo_cold_s1_st_phys_hi_structure.png: the physics band's adverse end at
  x = 0 (plate-limited skirt).
- RQ1-structural-2d-silo_cold_s1_st_ts_structure.png: the thrust-structure row at x* =
  5.97 t.
- RQ1-structural-2d-readme_silo_cold_s1_st_structure.png: file C's central case at x* =
  9.16 t (run C, plots/silo_cold_s1_st_structure.png). Its own title does not name the fork
  (it reads "silo_cold_s1_st"). Unlike the gate's, it is governed by the aft skirt's base
  (push 7.78 mm against the envelope's 3.21 mm, ring + common Z; 2,039.9 kg), with the
  RP-1 barrel second by 13.8 kg (2,026.1 kg).

Derived, by docs/findings/scripts/sp7_structure_figures.py at a5b21b8 (drawn 2026-10-19,
file times 20:24:44Z to 20:24:46Z) from the files named in each figure's footer (the
gate-vehicle and modelled-rows caveat lines in every footer). Where a figure as drawn
leaves out a caveat that the text puts beside its numbers, its entry says so and gives it.
Every footer's modelled-rows line reads "zero existing margin (adverse for the assist)":
zero existing margin on the pad's envelope (D-SP7-03), not a missing safety factor; the
headline chart's "10% margin" and "25% margin" rows are that existing margin, spare
capacity the push can use, which is why they keep more (Caveats, "What the headline
assumes").

- RQ1-structural-2d-derived_headline_rows.png: x* at P_ref of SP1's uncharged and assumed
  penalty rows, every modelled row of the headline push, the physics band and the outer
  envelope as ranges between their solved ends (a bar marks the band's unscaled low-mass
  end), 50% of 41.26 t marked, the other pushes beside their own uncharged x* (hollow grey;
  each label gives the share of 41.26 t first and of its own uncharged x* second), and
  file C beside its own uncharged x* (a tick at its 50%). Solved ends are filled dots, blue
  and, for the outer envelope, orange (the legend's "modelled structure: solved x*" shows
  both; the orange dot at the outer envelope's right end is its solved low-mass end,
  31.12 t). No-offload rows are drawn at 0 (hollow, blue for the band and the step row,
  orange for the outer envelope; the legend: "no offload (drawn at 0; short of P_ref even
  at x = 0)") and carry their shortfall and payload deficit with the residual estimate. The
  footer names file C's own P_ref (24,700.0 kg) and fork calibration (+8.33%), the range
  ends as the extremes S2's search found, not bounds, and the plausibility factor's
  trigger, and it carries three caveats the text puts beside these rows. (1) The free kick:
  every ok structural case of run A peaks in q-alpha at its kick, 1.7 to 3.9 times the
  pad's 74.7 Pa rad (126.6 to 288.8 Pa rad; run A `offload.runs` `peak_q_alpha`),
  unconstrained, with no angle-of-attack aerodynamics and no structure charged for it
  (Caveats, "Free kick"). (2) The thrust-structure row's sizing-only break-even: no offload
  at k_ts 0.3476 kg/kN or above, 24% above the central 0.2805 (S2's first pass); and S0's
  move of k_ts's central from 0.306 with the planning probe known, about +2.4 t on the
  row's expected x* (5,769.7 against 3,325.2 kg, sizing only; "Beside the number"). (3) The
  exhaust remark's direction: its gate-vehicle line reads "no exhaust in the shaft
  modelled, which favours the hot starts" (SP1), whose lead over the cold start the chart
  shows. As drawn, the kick clause covers run A's structural cases only; the chart's other
  offloaded rows kick free too: SP1's four, 119.9 to 226.9 Pa rad (1.60 to 3.04 times);
  the other pushes' uncharged x* (hollow grey), 226.9 to 393.0 Pa rad (3.04 to 5.26
  times); file C's uncharged and central, 308.3 and 207.8 Pa rad, 2.93 and 1.98 times its
  own pad's 105.2 (run A and run C `offload.runs`; derived ratios). As drawn, it also
  leaves out two caveats. First, the no-offload rows' payload deficits were flown with the
  free kick: the physics high-mass end's -2,080 kg (96.3 Pa rad, 1.29 times the pad's) and
  the step row's -1,087 kg (108.5 Pa rad, 1.45 times) are upper bounds by run A's rule, so
  the deficits are at least this deep; the outer high-mass end's -7,804 kg (55.2 Pa rad,
  0.74 times) meets none of the rule's three tests (run A `offload.runs`
  silo_cold_pstar_st_phys_hi, _step and _outer_hi; derived ratios; "The payload form").
  Second, the plausibility trigger's LOX-barrel envelope carries nof_barrel, a double count
  of buckling material the source note flags (Headline).
- RQ1-structural-2d-derived_sweep1_exit_speed.png: sweep 1 from the re-run's index (the
  first sweep reproduced column by column), uncharged and with the central structure,
  against the exit speed; the two no-offload points drawn at 0 and labelled with their
  shortfall at x = 0 (60.2 and 18.3 m/s; dm 6.53 and 6.49 t at x = 0; payload deficit not
  flown), dotted between a no-offload point and the next (nothing is measured there); both
  300 m points tagged as upper bounds. Its footer names every column it reads
  (`unconstrained_kick` and `.structure_dm_stage2_kg` among them) and the kick: a vertical
  rise first at 25 and 50 m; the 300 m point's kick above 120 m/s, an upper bound; the 200
  and 300 m points' full-load runs kicking at the first lit instant at 103.6 and
  127.9 m/s into a peak q-alpha of 574.1 and 1,293.3 Pa rad, 7.7 and 17.3 times the pad's
  74.7 (the re-run's sweep_1/sweep_index.csv `peak_q_alpha`, `speed_at_kick_mps`, and its
  baseline's; derived ratios), with q-alpha unconstrained, no angle-of-attack aerodynamics
  and no structure charged for it; and that the structural runs' own q-alpha is not written
  at a sweep point (likely higher: Caveats, "Free kick"; the sweep 1 table). The footer's
  "unconstrained" there means q-alpha unconstrained, not the `unconstrained_kick` column,
  which is True only at the 300 m point (its kick above checks.unconstrained_kick_mps,
  120 m/s; compare.py); the "(upper bound)" tags follow that column, as in SP1. The index's
  `payload_delta_upper_bound`, which also counts q-alpha above the pad's, is True at the
  100 and 200 m points as well. As drawn, it leaves out the 100 m point's kick, the
  headline push's: at the first lit instant at 71.8 m/s into 129.9 Pa rad, 1.74 times the
  pad's (the same index; derived).
- RQ1-structural-2d-derived_sweep2_depth.png: sweep 2 from the re-run's index, against the
  stroke (left) and against the felt load (right; the felt-load axis falls to the right),
  each structural value labelled beside its own point on both panels (11.42 t at 100 m and
  4.0 g0, 26.69 t at 200 m and 2.5 g0, 32.03 t at 300 m and 2.0 g0); the 50 m point drawn
  at 0 and labelled 190.0 m/s short at x = 0 (dm 15.54 + 0.51 t at x = 0, stage 2 sized;
  payload deficit not flown); dotted where nothing is measured. Its footer names every
  column it reads (`unconstrained_kick` among them) and the kick: every point's full-load
  run kicks at the first lit instant at 71.8 m/s into a peak q-alpha of 129.9 Pa rad,
  1.7 times the pad's 74.7 (1.74, derived), with q-alpha unconstrained, no angle-of-attack
  aerodynamics and no structure charged for it; the structural runs' own q-alpha is not
  written at a sweep point. The footer's "unconstrained" there means q-alpha unconstrained,
  not the `unconstrained_kick` column, which is False at every sweep 2 point (71.8 m/s,
  below checks.unconstrained_kick_mps, 120 m/s), so no point is tagged "(upper bound)";
  the index's `payload_delta_upper_bound`, which also counts q-alpha above the pad's, is
  True at every point. As drawn, it leaves out the structural runs written elsewhere: the
  100 m one matches run A's headline to 0.00056 kg (its own q-alpha not written; run A's
  140.9 Pa rad, 1.89 times), and the 200 m one equals run A's silo_cold_200m_s1_st to 12
  significant digits (181.0 Pa rad, 2.42 times); the 300 m one's is not written (lifting
  off at 542.4 t, near outer_lo's 543.5 t, which peaks at 194.1 Pa rad, 2.60 times; not
  measured at the point), all with q-alpha unconstrained (the sweep 2 table note; Caveats,
  "Free kick").
- RQ1-structural-2d-derived_elements.png: the headline case's dm by element at x*, with the
  governing push and envelope modes; the load entry is 57% of it.
- RQ1-structural-2d-derived_dm_vs_felt_load.png: sizing only, the central structure's dm by
  element group against the push's felt load at the fixed exit speed, at SP1's headline
  offload (stacked) and at x = 0 (line); sweep 2's strokes marked. Its footer lists every
  break-even felt load at 41.26 t, as under "Which elements and modes carry the mass" (the
  aft skirt 1.065 g0, below the plotted range; the common dome 1.438; the RP-1 aft dome
  1.488; the RP-1 barrel 1.768; the LOX barrel 3.953; the transfer tube 3.977; the upper
  stack 4.704; the load ring charged at every push); says that at 41.26 t the stack is
  lighter than at any structural x* solved at this exit speed (the highest, 32.03 t at
  sweep 2's 300 m), so dm is understated there, and that x = 0 is the adverse bound; and
  gives the rise-time basis (sized at n_peak from the plateau with DLF 1.127, an assumed
  0.5 s rise time) and that the step push the constant_accel trajectory flies (DLF 2) sizes
  13.5 t at 4 g0 and x = 0 (the step row), about 2.1 times this curve's 6.47 t there
  (derived). Not a flown result: the subtitle says "no assisted flight (file A's pad
  re-flown)", and the footer's modelled-rows line names the pad's own unthrottled flight as
  the envelope.

The sizing-only tables (the felt-load table, the break-even felt loads, the central at its
solved x*, the estimates at the sweep points against the re-run's solves, and the other
pushes against their solves) are in docs/findings/RQ1-structural-2d-tables.md, generated by
the tables script and not edited by hand.

Derived from run B by docs/findings/scripts/sp7_drive_figures.py (step S7b; it reads run B's
metrics.json and resolved_config.yaml, the recorded runs' timeseries.csv and events.csv,
and, for one footer clause, file A's sweep re-run's sweep_1/sweep_index.csv and
baseline/metrics.json; it flies nothing and writes only these three files). It reuses the
look and helpers of sp7_structure_figures.py, unchanged. Every footer carries the
gate-vehicle line (the +14.3% calibration miss, sweep-optimized, unthrottled, planar, x* at
P_ref with partly filled tanks, and the central structure only, with no physics band and no
+/-10% arm on file B) and the drive line (the caps, the assumed efficiency, the carriage,
the shaft, and the unmodelled exhaust, which favours the hot starts on back-pressure and
heating, while on lm_fixed_hot impingement 0 also adds the whole thrust to F_max and raises
its felt load and dm, so the omission's net direction there is not known). The two x*
figures also carry the modelled-rows line (a first-order sizing, not a structural design;
central coefficients; the linear motor's flown rise against silo_cold's assumed one; the
pad's unthrottled envelope; zero existing margin, adverse for the assist; the instant
release flagged, not sized, the release flag firing on all ten structural cases). The script
prints, each with its source key, every plotted point of the x* figures, each flown push's
row count, maxima and release row (not its every sample), the power-cap spans and every
footer cap. Its `--check` compares x*, U, dm1 + dm2 (against the decomposition's
`xv_dry_mass_delta_kg`), dm2 (against the stage-2 elements), the release speed (against the
decomposition, `exit_speed_mps` and the last ASSIST row), the release position (against the
last ASSIST row) and the drive-force and drive-power peaks (against `drive_force_peak_N` and
`peak_drive_power_W`) with their records, and passed. These footer facts are read from
metrics.json and resolved_config.yaml and checked before drawing: the verifications, the
release flag, the kick phase, the sampling interval, the efficiency, the impingement, the
carriage, the bore, the drive laws, silo_cold_s1_st's assumed rise time (`structure_t_r_s`,
0.5 s) and each linear-motor case's against its flown rise, and each force-law variant's
power ratio r = P_max / (F_max v_e) against its label. The exit-speed figure also checks,
before writing its words, that lm_cmd lies within R of silo_cold_s1_st, that lm_cmd_taper
releases at silo_cold's speed and keeps less beyond R, that each faster exit keeps less, and
that sweep 1's 200 and 300 m points exit faster and keep more. It measures a dot on its
drawn axes and refuses to save if that measure names other near-line points than its footer
does. The force and power figure measures which force-law release dots lie beside
lm_fixed_target's, and that each ringed release dot lies within a quarter of a dot's width
of the dot drawn over it on both of its panels; it refuses to save if either differs from
its footer. The footers' other numbers (the q-alpha values, the caps, the corner speed, the
column force, the power-cap spans, sweep 1's points) are read from the records and printed,
not re-checked. Words that describe the model rather than the run (the uniform adiabat, the
kind of cap) are written, not read.

- RQ1-structural-2d-derived_drive_cases.png: "The cases" as a chart. Each variant's
  central structural x* (filled) and its uncharged x* (hollow) are joined by the
  structure's offload cost U - X, against silo_cold_s1_st's 11.42 t, 50% of 41.26 t and
  SP1's 41.26 t. Each row's text gives x* with its share of 41.26 t, the difference from
  silo_cold_s1_st ("within R" for lm_cmd's +0.0046 kg), U, U - X and dm1 + dm2 at x*.
  lm_cmd_taper's stage-2 0.9 kg is printed in kilograms. Its footer's free-kick clause gives
  the central cases' peak q-alpha, 104.1 to 409.2 Pa rad (1.39 to 5.48 times the pad's
  74.7). As drawn it leaves out the uncharged runs' kick (212.9 to 846.1 Pa rad, 2.85 to
  11.32 times; "Beside every number"), the payload-limit flag (on seven of the nine
  linear-motor central cases and on silo_cold's) and the upper-stack flag (lm_cmd_taper,
  lm_fixed_hot).
- RQ1-structural-2d-derived_drive_force_power.png: drive force and mechanical drive power
  against the speed along the track for the ten flown pushes of the central structural cases
  at x*, each carrying its dm. The acceleration law and silo_cold's constant_accel are on
  the left, the force law on the right, and a dot marks each release. The footer names the
  sampled rows (every 0.05 s plus the event rows; KI-074: a sampled drive-force peak can
  read low), the caps, the electricity's efficiency of 0.5, and where the force on the
  vehicle differs from the drive force (the sealed column's 2.18 MN, the 22 t carriage's
  share, the hot starts' thrust). Five force-law pushes coincide on lm_fixed's F_max plateau
  and power line after the rise (lm_fixed drawn above the other solid lines, lm_fixed_target
  dashed over it) and release at 72.22 to 89.24 m/s (listed in the footer). lm_fixed (over
  its last 1.14 m) and lm_fixed_hot (over its last 26.0 m) then fly the power cap from the
  corner speed 76.71 m/s, the force falling as P_max / sdot, and lm_fixed_r07 flies its own
  from 53.70 m/s over its last 57.48 m (the `power_limit` events). Rings mark the two
  releases that another dot hides: lm_fixed's (77.15 m/s, 0.44 m/s past lm_fixed_target's;
  its power-capped end is too short to see at this scale) and silo_cold's, under lm_cmd's
  (22.23 against 22.28 MN). Their centres lie 0.15 and 0.02 of a dot's width from the dot
  drawn over them (measured on the drawn axes, derived). lm_fixed_target's release dot is
  drawn above the other force-law dots, so lm_fixed_sled22's (75.27 m/s) shows as a crescent
  beside it. silo_cold's prescribed force (dashed) nearly coincides with lm_cmd's after the
  rise. The caps and the corner speed come from `offload.runs` (`push_force_max_N`,
  `push_power_max_W`, `push_corner_speed_mps`; r = P_max / (F_max v_e) derived, 1 and 0.7).
  The acceleration law's caps (lm_cmd and lm_cmd_hot 24.73 MN and 1,897 MW; lm_cmd_taper
  29.18 MN and 2,238 MW) never bind (E2) and are not drawn; the power axis is in MW. As
  drawn it shows neither the hot starts' thrust nor the interface force, nor the uncharged
  pushes (lighter stacks, which exit faster under the force law: "The cases").
- RQ1-structural-2d-derived_drive_exit_speed.png: each central structural x* against the
  speed at release of its recorded run at x*, all at the same 100 m stroke.
  silo_cold_s1_st's point is the origin of four quadrants named after part 2, section 8's
  readings: faster and less, or slower and more, undercuts "every m/s helps"; faster and
  more beyond R would favour it. Its subtitle says that both faster exits (lm_fixed,
  lm_fixed_hot) keep less. Its footer adds that on file A's sweep 1 longer strokes exit
  faster and keep more (31.62 t at 108.5 m/s over 200 m, 44.73 t at 132.9 m/s over 300 m, an
  upper bound), with an unconstrained kick: their full-load runs kick at 7.7 and 17.3 times
  the pad's q-alpha, and the structural runs' own values are not written. silo_cold and
  lm_cmd share one point and one label; silo_cold_s1_st's point, the quadrants' origin, is
  drawn above the others and ringed in ink, so that lm_fixed_target's blue point below it
  shows as a blue sliver inside the ring's lower edge. lm_cmd, lm_cmd_taper, lm_cmd_hot and
  lm_fixed_target release at silo_cold's 76.71 m/s and lie on the vertical boundary, in no
  quadrant (lm_cmd_hot, at 18.27 t, sits on the boundary in the upper half, between the two
  "more" quadrants, without being slower or faster), which the footer says.
  lm_fixed_target's speed is its release speed 1.08 m below the mouth, which the footer says
  too. As drawn, R (about 3.4 kg) is far below the axis resolution, and a dot is about
  0.65 t tall (the script measures it on the drawn axes): lm_fixed (82.0 kg, about 24 R,
  below), lm_fixed_target (373.9 kg, about 110 R, below, partly under silo_cold's ringed
  point) and lm_fixed_sled22 (223.1 kg, about 66 R, above) lie within about a dot's width of
  silo_cold's line. Their side is shown by their labels (11.34, 11.05 and 11.64 against
  11.42 t) and the footer, not by their positions.
