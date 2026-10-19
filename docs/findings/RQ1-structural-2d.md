# RQ1 (structural, 2-D): the stage-1 offload once the push load's structure is charged

Status: draft of 2026-10-19 (SP7 step S7a). This is the structural part, on files A
(experiments/silo_structure_2d.yaml, the gate vehicle) and C
(experiments/silo_structure_2d_readme.yaml, the README-loads fork), constant_accel pushes
only. The drive cases of file B (the linear motor) are pending S7b. Planar 2-D model,
sweep-optimized guidance (not an optimal-control solution; Phase 5), unthrottled.
Pre-registered in commit cbbd7bc (docs/phases/inputs/2026-10-15-SP7-preregistration.md, "the
pre-registration" below, its sections cited as "section n"), with its Amendment 1 (74eb3c8,
D-SP7-48: the sweep's no-offload record and the sweep's re-run). Every new number comes from
run A and run C, made from the clean commit 1b5f9d4 (1b5f9d46d31c), from the sweep's re-run
under Amendment 1 (from 2b343d7; it reproduces the first sweep of 1b5f9d4 cell for cell and
adds the no-offload points' shortfalls; its git record reads dirty, by the session's
account from 13 untracked draft documents of this note, a departure from the clean commit
Amendment 1 names, deviation 45), from the convergence check of section 1 and from two
sizing-only scripts, all named under "Provenance" and "Reproduction". Every structural
number is a first-order station sizing of the push load (D-SP7-01): a first-order estimate
with its stated ranges, not a detailed structural design.

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
structure is paid for.

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
- **Drive.** A prescribed constant acceleration with no force or power limit, a massless
  carriage, a vented shaft and no model of the exhaust in the shaft (which favours the hot
  starts). File B's linear motor is pending S7b.
- **The flags, with their numbers** (reported beside, never a gate; section 9). The release
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
  numbers and how each result is read.
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
  File C is read against its own uncharged x*.

## Provenance

| command | results directory | git | contents |
|---|---|---|---|
| `run experiments/silo_structure_2d.yaml` (run A) | results/silo_structure_2d/20261016T171513Z | 1b5f9d46d31c, clean | pad; silo_cold, silo_cold_200m, silo_hot_full, silo_hot_ramp_on_track; 24 stage-1 cases (4 uncharged, SP1's 3 penalty rows, 17 structural); the stage-1 pad control; 4 structure payload cases; 8 sensitivity arms on the structural headline; the energy block |
| `sweep experiments/silo_structure_2d.yaml` (sweep A, first) | results/silo_structure_2d/20261016T171522Z | 1b5f9d46d31c, clean | the sweep's own pad; sweep 1 (stroke 25-300 m at 3 g0) and sweep 2 (stroke 50-300 m at 76.71 m/s), 9 points, an uncharged and a central structural stage-1 solve at each, each ok solve verified (6 of the 9 structural ones; the three no-offload points carry no verification); no shortfall column (the reporting defect); on record, superseded by the re-run for every sweep number |
| `sweep experiments/silo_structure_2d.yaml` (sweep A, re-run under Amendment 1) | results/silo_structure_2d/20261019T172327Z | 2b343d7f25eb, dirty true (below) | the same 9 points and solves, every pre-existing index column equal to the first sweep's cell for cell; adds `<case>.dv_shortfall_mps` and the summary's no-offload lines; the source of every sweep number here |
| `run experiments/silo_structure_2d_readme.yaml` (run C) | results/silo_structure_2d_readme/20261016T171529Z | 1b5f9d46d31c, clean | the README-loads fork: pad, silo_cold, the uncharged and the central structural stage-1 case, the stage-1 pad control |

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

Pending S7b. File B (experiments/silo_drive_2d.yaml: the linear motor under a force law and
an acceleration law, a stop taper, hot starts, a 22 t carriage and the sealed shaft, each
with an uncharged and a central structural stage-1 solve; design 4.10) is pre-registered at
S6b and run at S7b, which completes this section.

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
  absolute against -231.7). A real drive's release and a real MECO are not instant steps;
  the stop taper that would soften the release is file B's lm_cmd_taper (pending S7b).
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
