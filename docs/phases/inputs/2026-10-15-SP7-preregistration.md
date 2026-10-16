# SP7 pre-registration, part 1: the structural experiments (step S6a)

Written 2026-10-15 to 2026-10-16 for SP7 checkpoint 1 and step S6a
(docs/phases/SP7-structural-mass-push-load.md, section 7; design
docs/phases/inputs/2026-10-08-SP7-design.md, sections 3.2, 4.10, 4.11, 5 and 6) and committed
with the two experiment files before any run of them. Step S7a runs them from a clean
committed tree and drafts docs/findings/RQ1-structural-2d.md against this note. Part 2 (file
B, experiments/silo_drive_2d.yaml, the linear-motor cases) is an addendum written at S6b. A
change to either file after the pre-registration commit is an amendment: its own commit,
logged as a decision, this note kept and extended, never rewritten. The sections follow
SP1's pre-registration (docs/phases/inputs/2026-10-03-sp1-preregistration.md).

Every expected value below is an estimate, and none is a target: a different result is
reported as it is. Every structural number is a first-order station sizing (D-SP7-01), not
a detailed structural design.

## 1. What is registered

| File | Vehicle | Structure file | What it declares |
|---|---|---|---|
| experiments/silo_structure_2d.yaml (file A) | generic_f9_class_2d.yaml (gate, mass set C; calibrates +14.3% high, accepted 2026-09-30) | configs/structures/generic_f9_class_2d.yaml | pad baseline; variants silo_cold, silo_cold_200m, silo_hot_full, silo_hot_ramp_on_track; a structure block with 4 payload cases (design 4.10's two and one for each other row expected to end no_offload, section 6); an offload block with 24 stage-1 cases (4 uncharged, SP1's 3 penalty rows, 17 structural), the stage-1 pad control, 8 sensitivity arms on the structural headline and SP1's energy block; 2 sweeps (5 and 4 points), each point solving an uncharged and the central structural case |
| experiments/silo_structure_2d_readme.yaml (file C) | generic_f9_class_2d_readme_loads.yaml (mass set A, README loads; calibrates +8.33%, inside the band) | configs/structures/generic_f9_class_2d_readme_loads.yaml | pad baseline; variant silo_cold; a structure block (no payload case); an offload block with the uncharged and the central structural stage-1 case and the stage-1 pad control |

The six shared blocks (dynamics, site, target_orbit, guidance, search, checks), the vehicle
line and the baseline pad with its integrator are copied verbatim from
experiments/silo_offload_2d.yaml (file A) and experiments/silo_offload_2d_readme.yaml (file
C); a test pins the shared blocks and the budget id across every planar experiment. File A's
variants silo_cold, silo_cold_200m and silo_hot_ramp_on_track are SP1's, copied with their
comments; silo_hot_full is silo_screening_2d's, written out in full. No label.

Commands for step S7a, from the repository root, all three started together (in parallel)
from one clean commit, this note's commit or a later clean commit that changes no code:

    uv run python -m launchsim run experiments/silo_structure_2d.yaml
    uv run python -m launchsim sweep experiments/silo_structure_2d.yaml
    uv run python -m launchsim run experiments/silo_structure_2d_readme.yaml

With plots (the findings need them). No test suite and no app-driving agent runs while they
run. Each command's start time (UTC) and each results directory's last file time go into
the findings note's Reproduction section (the run command writes all its directories at the
end and records no per-solve wall time).

**The convergence check** (exit criterion 6, registered here so that it is not an extra,
unregistered solve of the headline): at S7a, after the three commands above have finished
(never beside them), from the same commit, a committed script (docs/findings/scripts/)
solves silo_cold_s1_st of file A (its pad, silo_cold and that one case, read from the
committed file) at the shipped budget and under its tightening by the file's
`checks.convergence` (`SearchContext.tightened`: every search and final tolerance divided
by 10, the max-step caps times 0.5, as SP1's
tests/test_offload.py::test_gate_offload_converges_under_a_tightened_budget did for the
uncharged headline), each chain with its own pad P* as P_ref and as the envelope's flight,
the structure's fixed-point tolerance (1e-6 kg) unchanged; it writes only under the
session's scratch directory, never in results/. Passes if the tightened x* is within
0.1% of the shipped x* (which equals run A's within 0.002 kg). Beside it, sizing only, dm
of the central case at its solved x* with `stations_per_barrel` doubled (200 to 400, on a
scratch copy of the structure file outside configs/) moves by less than 0.1 kg
(criterion 6's second part). Its numbers are a check quoted in the
findings note's convergence line, never a finding; a failure blocks the headline until
explained.

No `launchsim` command ran these files, no offload of any case of either was solved and no
x* of any pre-registered case was computed by a solve (D-SP7-31). Only their pad baselines
were flown (file A's pad, also in the six perturbed forms of its arms, and file C's pad),
for the sizing envelopes of section 7, as D-SP7-31 allows; section 2 lists what was
computed. The files were resolved the way `launchsim run` resolves them
(`cli.load_experiment`: the vehicle, the structure file through `load_structure`,
`sim.check_result_names` and the preflight `sim.check_resolved`, which also refuses a
structure block whose pad does not hold down under thrust), and `sim.check_resolved` was run
again on both and `run_ignition_specs` on every one of their resolved runs (70 for file A,
4 for file C; the payload cases fly the variant's run): all passed (re-run after the
second review added the 4.0 g0 envelope-cap row).
tests/test_config_planar.py checks the properties of section 4.

## 2. What is already known before any run

Stated plainly: SP7's structural answer is not unknown. Five kinds of numbers exist before
these runs, and the readings of section 8 were fixed with all of them known.

**(a) The planning probe** (survey 08, docs/phases/inputs/2026-10-08-SP7-survey/
08-closed-forms-and-probe.md, sections 6, 7 and 8; placeholder coefficients, no non-optimum
factor, not a finding): the increment at silo_cold_s1's push (x = 41.26 t), monocoque,
3.5 bar, quasi-static, 2,550 kg (RP-1 wall 1,710, aft skirt 327, intertank 323, LOX bottom
dome 114, RP-1 bottom dome 50, LOX wall 27); corner sets 2,159 / 2,550 / 3,487 kg
(monocoque), 1,390 / 2,248 / 2,550 (stiffened 2x), 1,492 / 1,972 / 2,345 (stiffened 3x), so
1.4 to 3.5 t quasi-statically; the dynamic factor on the push's dynamic part 1.0 / 1.1 /
1.3 / 2.0 gave 2,550 / 2,857 / 3,473 / 6,328 kg (monocoque), 2,248 / 2,513 / 3,029 / 4,951
(stiffened 2x), 1,972 / 2,238 / 2,836 / 5,250 (stiffened 3x), 2,234 / 2,555 / 3,209 / 5,545
(pressure-stabilized bracket); interface hardware 20, 50 and 100 kg/MN gave 0.42, 1.04 and
2.08 t at DLF 1 (0.73, 1.82, 3.64 t at DLF 2); entry through the thrust structure +1.5,
3.1 or 4.6 t for an assumed 1, 2 or 3 t thrust structure. Its placement on SP1's penalty
curve (naive: dm at x = 41.26 t; coupled: the fixed point):

| Probe case | Naive | Coupled |
|---|---|---|
| Monocoque central, DLF 1, k = 20 kg/MN | 27.74 t | 27.16 t |
| Monocoque central, DLF 1, k = 50 | 24.80 t | 23.99 t |
| Monocoque central, DLF 1, k = 100 | 19.66 t | 18.25 t |
| Stiffened 2x central, DLF 1, k = 50 | 26.22 t | 25.23 t |
| Stiffened 3x central, DLF 1, k = 50 | 27.52 t | 26.47 t |
| Monocoque central, DLF 1.3, k = 50 | 19.07 t | 17.44 t |
| Monocoque central, DLF 2.0, k = 20 | 7.30 t | 4.26 t |
| Monocoque central, DLF 2.0, k = 50 | 1.73 t (extrapolated) | 0 |

Over the nine corner sets and k = 20-100 kg/MN the coupled x was 12.2-32.9 t (30-80% of
41.263 t) at DLF 1.0, 8.7-31.8 t at 1.1, 1.6-29.5 t at 1.3 and 0-20.2 t at 2.0; the probe
put the naive placement's bias at +0.4 to +1.7 t at DLF 1 and up to +4 t at DLF 2 (for the
assist), and the full-load sizing bound (dm fixed at the x = 0 push) 0.6 to 2.6 t below the
coupled value at DLF 1 (survey 08, section 8).

The probe's other tables (survey 08, section 7; b_out.txt), which S0's disclosure (item (b)
below) means by "the probe's one-at-a-time table" and which were known when the centrals
and the range ends were set:

| One-at-a-time, kg around each form's 3.5 bar central | Monocoque (2,550) | Stiffened 2x (2,248) | Stiffened 3x (1,972) |
|---|---|---|---|
| sigma_ult 400 / 520 MPa | +130 / -59 | +205 / -278 | +214 / -188 |
| FS 1.25 / 1.5 | -165 / +114 | -229 / +141 | -190 / +123 |
| p_u 2.5 / 4.5 bar | -177 / +429 | -397 / +125 | -40 / -168 |
| aft skirt +1 m / -0.5 m | +142 / -71 | +71 / -36 | +78 / -39 |
| intertank +1 m | +103 | +53 | +43 |
| E 70 / 80 GPa | +71 / -40 | +17 / -12 | +16 / -10 |
| minimum gauge 3 mm | -50 | -49 | -346 |
| densities, ullage fraction, top mass, hemispherical domes, drag in the envelope | 0 to 60 each | 0 to 60 each | 0 to 60 each |

The buckling form against the ullage pressure (2.5 / 3.5 / 4.5 bar; sigma_ult 450 MPa, FS
1.4): monocoque 2,373 / 2,550 / 2,979 kg, stiffened 2x 1,852 / 2,248 / 2,373, stiffened 3x
1,932 / 1,972 / 1,804, pressure-stabilized 2,409 / 2,234 / 2,080 (the pressure's effect
changes sign with the form; the bottom domes a fixed 148-164 kg). The increment against
the offload x (central, quasi-static; x = 0, 10, 20, 30, 41.26 t): monocoque 2,892 / 2,806 /
2,722 / 2,640 / 2,550 kg, stiffened 2x 2,722 / 2,603 / 2,487 / 2,373 / 2,248, stiffened 3x
2,534 / 2,393 / 2,255 / 2,119 / 1,972 (-9 to -14 kg per t of offload). The probe's release
check: an undamped instantaneous release swings the LOX bottom to -0.53 MPa absolute (survey
08, section 3), the first sight of the release flag of item (c).

The probe's envelope check (survey 08, section 6; labelled there as calibration, not
validation): the probe's envelope masses of the sized elements against stage 1's dry mass
less its engines (17,970 kg), monocoque 9,244 kg (51.4%; the LOX wall 4,638, the intertank
845, the RP-1 wall 2,705, the aft skirt 642, the domes 413), stiffened 2x 4,878 (27.1%),
stiffened 3x 4,018 (22.4%), pressure-stabilized 4,993 (27.8%), the walls governed by axial
buckling at MECO (5.195 g0, the stage-1 tanks empty). That heavy MECO-buckling LOX wall was
the first sign of the envelope that later fires the plausibility rule and D-SP7-41's
scaling (item (c): the model's LOX barrel 7,541.9 kg, 71% of its envelope tank mass).

Survey 08 recommended reporting constant_accel at its as-flown dynamic factor 2 ("Under
`constant_accel` as modelled (infinite jerk), the honest DLF is 2", its section 3; its
section 10, item 2), and the design records that (its section 1). The design chose instead
(D-SP7-09) an assumed real-drive rise time, central 0.5 s (DLF 1.1273), for the headline,
its plateau cost charged, with the step row (DLF 2, the push the constant_accel trajectory
actually flies) beside it; under the estimates of section 7 that row ends at no offload.
The design (section 1) adopted ranges less favourable than the probe's and said then that
a planning reading at the central values is an offload below half of 41.26 t, with the
adverse ends possibly at no offload.

**(b) S0's central values and range ends were set after the probe.** The source note's
disclosure (docs/phases/inputs/2026-10-08-SP7-sources.md, section 1, "Disclosure", and the
paragraph after it; the note is unchanged since its commit 81e045d), repeated verbatim as
it asks:

> **Disclosure.** The central values below were chosen after the planning probe (survey 08) had shown
> which coefficients matter (the dynamic factor, the load-entry hardware, the buckling form, the tank
> pressures), and the probe's one-at-a-time table also showed the direction and rough size of several
> coefficients' effects on the added mass dm (sigma_ult, FS, p_u, the skirt length, E, t_min). The
> review rounds' changes (sections 1.2 and 1.3 and the third round's revision section) were also
> made with that table known. To keep that knowledge from steering the choice, each central value
> follows a rule written beside it. The rules
> used, the complete list: the opened value; the current edition's recommendation; the method as
> written; the midpoint of the range or of the opened values; the median of the opened readings; a
> flown tank's regulation-band bottom over its relief valve's top setting, where both are legible; the
> one opened flight-hardware analogue, or the opened analogue nearest the case; the vehicle guide's
> statement read plainly, with the one opened value of that kind; the value at a quoted temperature; a
> quoted value; the Gerard row nearest the opened calibration, and that row's exponent for a member
> no Gerard row describes; Wu's factor for the model's fidelity, with the opened calibration where
> the model's base differs from the factor's; the population
> average; no weld knockdown under a factor that already carries the weld lands; an inferred load path
> or symmetry; SP1's shipped value; a fixed value (no range) where the vehicle's own source or the
> analogue regulation names it and no opened source supports another; a user decision. No rule refers
> to the value's effect on dm. Where a rule lands on a range end, the row says so and, where known,
> which way dm moves at that end.
>
> The range ends were also set with the probe's table known, and for a coefficient that moves dm
> one way the band's ends are set by them, not by the centrals. Most ends are opened values, the
> sources' spread (rule 3) or a bound derived from opened values (with the model's own geometry,
> where the row says so). Section 1.4 lists every dm-lowering end or discrete alternative that
> rests instead on an assumption, an analogue, a quoted value, a rule or a user decision (and every
> such end whose direction is only expected or not monotone), and the fixed choices of that kind,
> with its reason and the probe's one-at-a-time effect where the probe tested it. The
> pre-registration (S6a) repeats this disclosure and section 1.4's table as they stand after the
> last revision of this note (the rows added after the round-3 verification included).

The rules behind the centrals of the 35 coefficients (27 physics, 8 design axes; the
structure file's values, gate and fork alike). Where a central lands on a range end, or is
one of two alternatives, the row says which way dm moves there: from S2's tornado and
search D at the headline push (the phase file's section 11, step S2), and for nu and s_dg,
whose tornado rows give only the size, from this step's converged sizing at the same push
(x = 41,262.9 kg, the rest central, the envelope rebuilt with the same value; section 7's
method):

| Coefficient | Central | Range | Rule behind the central |
|---|---|---|---|
| materials.E_GPa | 75.84 | 72.0-79.6 | the opened value (LOV10, 11.0 Msi) |
| materials.nu | 0.33 | 0.30-0.33 | the opened value (LOV10, HL19); also the high end, the dm-raising one by 0.3 kg (nu 0.30: dm -0.34 kg, this step) |
| materials.rho_wall_kg_per_m3 | 2712.6 | 2698.8-2726.5 | the opened value (LOV10) |
| materials.F_tu_MPa | 558.5 | 520.0-558.5 | the opened value (LOV10, 81 ksi); also the high end, the dm-lowering one (520 MPa: +136.0 kg) |
| materials.eta_weld | 1.00 | 0.70-1.00 | no weld knockdown under a factor that already carries the weld lands (Wu's practice); also the high end, the dm-lowering one (0.70: +1,828.2 kg, no offload) |
| materials.dome_alloy | 2219-T851 | or 2195 | the vehicle guide's statement read plainly ("aluminum domes" as a conventional alloy, inferred); the dm-raising alternative (2195 lowers dm, appendix A; the tornado's move under 133 kg) |
| pressures.<tank>.p_meop_bar (4 tanks) | 2.62 | 1.24-4.00 | the midpoint of the range |
| pressures.<tank>.p_min_fraction (4 tanks) | 0.84 | 0.40-0.93 | a flown tank's regulation-band bottom over its relief valve's top setting (S-IVB LOX) |
| buckling.s_dg | 1 | or 0 | the method as written (SP-8007 prescribes the pressure increment); the dm-raising alternative by 0.7 kg (s_dg 0: dm -0.69 kg, this step) |
| buckling.k_stiff | 0.65 | 0.65-0.75 | the current edition's recommendation (SP-8007-2020); also the low end, the dm-raising one (0.75: -305.8 kg) |
| buckling.gerard_row | ring_common_z | or plate_limited | the Gerard row nearest the opened calibration (LOV10's PANDA2 designs); the dm-lowering alternative (plate_limited: +4,851.6 kg, no offload) |
| buckling.t_min_mm | 1.65 | 1.22-1.676 | the opened value (LOV10's minimum manufacturing gauge) |
| geometry.aft_skirt_length_m | 6.045 | 2.0-10.09 | the midpoint of the range |
| geometry.dome_axis_ratio | 1.3333 | 1.0-1.4142 | the one opened flight-hardware analogue (the SLWT LO2 aft bulkhead) |
| geometry.ullage_fraction | 0.0345 | 0.020-0.050 | the midpoint of the opened values (S-IVB) |
| geometry.rho_lox_kg_per_m3 | 1253.3 | 1141.2-1306.1 | the value at a quoted temperature (66.5 K) |
| geometry.rho_rp1_kg_per_m3 | 819.9 | 785.0-829.2 | the value at a quoted temperature (-6.6 C, extrapolated) |
| geometry.tube_diameter_m | 0.65 | 0.40-0.90 | the midpoint (no source public) |
| geometry.interstage_length_m | 4.5 | 3.66-10.83 | a quoted value |
| load_entry.skirt_envelope_path | hold_down | or flight_thrust | an inferred load path (the thrust through the engine mount into the tank); the dm-raising alternative (flight_thrust: -325.1 kg) |
| load_entry.ring_h_over_b | 6.5 | 1.0-12.0 | the midpoint of the range |
| nof.nof_barrel | 1.80 | 1.54-1.90 | Wu's factor for the model's fidelity (WU24, the SLWT barrel's average NOF) |
| nof.nof_stiffened | 1.61 | 1.45-1.90 | Wu's factor with the opened calibration where the model's base differs (1.24 x 1.2955) |
| nof.nof_dome | 1.90 | 1.50-2.36 | Wu's factor (WU13's coarse gore average) |
| nof.nof_entry_ratio | 1.47 | 1.05-1.47 | the opened analogue nearest the case (the SSME load-introduction gores); also the high end, the dm-raising one (search D: dm 5,134.1 kg at 1.05 against 6,143.0 at 1.47, at the 50% target's offload) |
| dynamics.rise_time_s | 0.5 | 0.1-1.0 | a user decision (D-SP7-09) |
| dynamics.axial_frequency_Hz | 5.0 | 2.0-10.0 | a user decision (D-SP7-09) |
| thrust_structure.k_ts_kg_per_kN | 0.2805 | 0.197-0.628 | the median of the opened readings counted once per relation (D-SP7-37); changed at S0's gate (D-SP7-37), after the note was written and with the probe known, from the note's nine-reading median 0.306 to the per-relation 0.2805 (the design's 0.28), a move whose direction was plain: at the same push the thrust-structure row's increment, linear in k_ts, is 8.3% lower; at the coupled estimates (this step, sizing only) 4,621.4 kg against 5,080.1 kg at 0.306, so the _ts row's expected x* is 5,769.7 kg against 3,325.2 kg at the note's value (2.4 t higher) |
| ring.ring_pads | 8 | 4-8 | an inferred layout (the engine mount's eight-fold symmetry); also the high end, the dm-lowering one (fewer pads raise dm; at 4 pads no offload, search D) |

Fixed (no range): FS_ult 1.40 (the vehicle guide's factor), the fitting factor 1.15 (14 CFR
25.625), the interstage exponent 0.6, the alloy of the skirt, ring and tube (2195), the
pressure basis (one gauge value in every case), the pads on the skirt's circle and the
breakdown's placement. The source note's section 1.4 lists every dm-lowering end or
alternative that rests on an assumption, an analogue, a quoted value, a rule or a user
decision, with its reason; appendix A repeats that table verbatim as it stands after the
note's last revision (the note is unchanged since its commit 81e045d). In short: E 79.6 GPa (assumed allowance); either end of p_meop_bar and p_min_fraction
(non-monotone; analogue or assumed ends); the pressure basis (assumed); eta_weld 1.00 (a
rule); the skirt 2.0 m (assumed); ullage 0.020 (assumed); RP-1 density 829.2 (extrapolated);
ring_h_over_b 12.0 (analogue); tube 0.40 m (assumed); interstage 3.66 m (derived bound);
t_min 1.676 mm (analogue); nof_stiffened 1.45 (analogue calibration); nof_entry_ratio 1.05
(analogue, kept by rule 3); k_ts 0.197 kg/kN (analogue, derived); rise time 1.0 s and frequency 10 Hz (user decision D-SP7-09);
ring_pads 8 (inferred); margin 0.25 (user decision D-SP7-03); no envelope cap (the design's
envelope, model output); skirt path flight_thrust (assumed); dome_alloy 2195 (analogue);
the 2195 alloy of skirt, ring and tube, the interstage exponent 0.6, the fitting factor
1.15, the pad line and the breakdown placement (fixed choices that could move dm either
way or whose alternative would raise it).

**(c) S2's sizing-only numbers** (the phase file's section 11, step S2; docs/physics.md,
"The screened search and the frozen sets"): at SP1's headline push (constant_accel 3 g0,
100 m, cold, the pad as flown, stage-1 offload x = 41,262.908 kg), the first pass of the
sizing gave the central 5,868.2 kg (stage 2 not sized), the physics band's frozen sets
3,677.1 kg (low mass; 2,717.5 kg after the plausibility rule's factor 0.7390) and 18,603.8
kg (high mass), the outer envelope 2,186.2 kg and 50,497.9 + 1,362.1 kg, the step row
12,251.9 kg (stage 2 sized), with coupled-placement estimates central 11,298 kg (27.4%),
physics low 23,717 (57.5%; 28,546, 69.2%, scaled), physics high and outer high no offload,
outer low 31,113 (75.4%), quasi-static 14,888 (36.1%), thrust structure 6,276 (15.2%),
margin 0.10 13,133 (31.8%), 0.25 15,585 (37.8%), cap 4.5 g0 10,374 (25.1%), cap 4.0 g0
5,039 (12.2%). The tornado (dm at each range end, the rest central): the Gerard row's
plate-limited alternative 10,719.8 kg (no offload), the skirt length 2.0 / 10.09 m
4,558.7 / 7,177.8 kg, eta_weld 0.7 7,696.5 kg (no offload), ring_h_over_b 1.0 / 12.0
7,130.4 / 5,861.4 kg, the flight-thrust skirt path 5,543.1 kg, k_stiff 0.75 5,562.4 kg,
the stage-1 LOX MEOP 1.24 / 4.0 bar 5,835.0 / 6,081.3 kg, E 72.0 / 79.6 GPa 5,995.0 /
5,757.6 kg, the stage-1 RP-1 MEOP 1.24 / 4.0 bar 5,758.6 / 5,984.1 kg, F_tu 520 MPa
6,004.2 kg, the other twelve under 133 kg each. Search D's break-even values (the other
coefficients central; the 50% target dm 4,440.4 kg, interpolated, biased against the
assist; the 0% target 8,488.6 kg, extrapolated, biased for it): no non-optimum factor
reaches 50% inside its range; k_ts reaches 0% at 0.3476 kg/kN (in range); the rise time
reaches 0% at 0.1438 s (in range); the frequency stays below 50% and above 0% throughout;
the pad count's 0% crossing lies between 4 pads (no offload) and 5; the four non-optimum
factors reach 0% only outside their ranges (nof_barrel 4.128, nof_stiffened 2.364, nof_dome
10.69, nof_entry_ratio 2.299), and k_ts reaches 50% only at 0.1178 kg/kN, below its range.
S2's sizing-only lines (outside every band; S2's first-pass estimates): FS_u 1.25 dm
5,447.1 kg (x* 13,891 kg, 33.7%), k_stiff 0.85 5,399.7 (13,782, 33.4%), k_stiff 0.52
6,444.9 (7,898, 19.1%), the Gerard rows ring_common_y 5,554.8 (12,985, 31.5%),
ring_improved_z 5,409.3 (13,508, 32.7%) and ring_improved_y 5,299.4 (14,136, 34.3%).
S2's band sets at the step row (search B: the frozen physics sets at the step row's push,
stage 2 sized; first pass at the headline offload; the fork in brackets): low mass 8,306.7 +
185.8 kg [7,308.3 + 104.0], high mass 36,128.7 + 668.2 kg [34,020.0 + 409.5]. Unscaled, even
the low-mass set places at no offload: its equivalent dm1 + 5.478 dm2 is 9,324 kg at 41.26 t
(9,372.8 kg converged, this step) against the 8,488.6 kg zero crossing, so at the push the
constant_accel trajectory flies the whole physics band ends at no offload; after the
plausibility rule's factor 0.7390 the low-mass set places at about 5.5 t (5,528.1 kg coupled,
naive 8,007.2 kg; this step, sizing only). No band case is flown at the step row; these are
context for the step row's reading (section 8: "cancels all"), not a registered row.
The search's polish and checks (D-SP7-38; the fork in brackets; "excess" is how far a
one-coordinate trial goes beyond the end): the polish moved only the physics high-mass end,
+413.0 kg [+421.0] (the RP-1 MEOP 3.31 to 2.62 bar +132.0, the LOX density 1,306.1 to
1,141.2 kg/m^3 +281.0), and the fork's outer high-mass end +2.2 kg; the one-coordinate
excesses A low 11.8 [4.9], A high 0 [0], B low 2.0 [0], B high 0 [0], C low 1.4 [0], C high
8.0 [7.7] kg, so each frozen end may sit up to that far inside the true one-coordinate
extreme (A, B and C low: the low-mass ends overstated, against the assist; C high: the
outer high-mass end understated, for it); on the charged dm1 + 5.478 dm2, C high 43.6
[42.0] kg; search B's held check over the 22 stage-1 coefficients at the step row: the
physics low-mass set 223.2 kg [149.1] above the step row's one-coordinate low (the band's
low end overstated, against the assist; 280.1 [181.0] charged) and the high-mass set 67.3
kg [43.2] below its one-coordinate high (the high end understated, for the assist); the
seeded samples stayed inside the ends (A 4,465 against 3,677 and 14,866 against 18,604 kg;
C 2,723 against 2,186 and 41,610 against 51,860 kg). Plausibility (D-SP7-33): the model's
envelope tank mass 10,621.8 kg against Heineman's 6,038.3 kg, M/R 1.759 (the fork's
1.700), so the rule cuts the physics band's low-mass end by the factor 0.7390 (the fork's
0.7649). Beside Heineman's relation S2 recorded the other references of the plausibility
table: Akin's relation 4,903.0 kg (so the model's envelope tank mass is 2.17 times Akin's),
the interstage relation 934.4 kg, k_ts T_max 2,307.6 kg and stage 1 less its engines
17,970.0 kg; the rule reads Heineman's alone (D-SP7-33). Its trigger, stated as D-SP7-41
asks: mostly the stage-1 LOX barrel's envelope
(7,541.9 of the 10,621.8 kg, 71%; monocoque-governed by MECO's compression at all 200
stations) carrying nof_barrel, which the source note's section 4 calls a double count of
buckling material at those stations, not the base-skin bias the note's section 7
anticipated. The push barely loads that element: the LOX barrel's own push increment is 0.7
kg in the central's sizing at the headline push, 25.6 kg at the central's expected x*
(section 7) and 0 in the physics low-mass set's sizing at either offload. The factor
multiplies the scaled case's whole dm (`sim.StructureTransform.iterate`: both stages'
increments, every element), not only the tank elements the relation covers: at the
headline push the scaled low-mass end's 2,723.8 kg is the aft skirt 356.2 and the load ring
1,017.8 kg (the load entry, 50%), the RP-1 barrel 1,257.4 and the common dome 92.4 kg. That
26% cut of the whole dm (965 kg at the headline push) is what puts the scaled end's estimate
4.9 t above the unscaled one (section 7: 28,514 against 23,658 kg). The user kept the rule
as approved, both ends printed (D-SP7-40, D-SP7-41). The release flag fires at the central
headline (D-SP7-39): the swing -4.389 g0 against MECO's -5.195 g0; the stage-1 LOX bottom
at -911.6 kPa gauge (-810.3 absolute) at the release, where the same tank, empty at the
pad's MECO, stays at +132.4 kPa gauge; and the same single-mode treatment separates stage
2's full LOX column at the pad's own MECO (-231.7 kPa gauge, MECO's ambient taken as 0,
against the push's -161.6 on the same tank), so a column separation under the instant-step
treatment is not specific to the push, while the stage-1 release is about 3.5 times deeper
(-810 kPa absolute against -232). At the central's expected x* (11.1 t, sizing only) the
stage-1 LOX bottom is at -896.6 kPa absolute (the larger column), the other values
unchanged. Sizing only at each case's expected x (section 7; this step, third review), the
release flag fires on every structural case of both files and at every sweep point, the hot
starts included (their stage-1 LOX bottom at about -103 and -119 kPa absolute).

The payload-limit flag (`structure_payload_limit`: n_peak above the payload's published
+6.0 g0 or the release swing below its -2.0 g0) fires at the central headline too, on the
swing: -4.389 g0 against -2.0 g0 (S2's log: "The payload-limit flag fires on the swing").
Its MECO comparison, the one D-SP7-39 asks for the LOX column: under the same single-mode
instant step the pad's own MECO swings the stack to -5.195 g0 (`meco_swing_g`; the fork's
-5.638), also beyond -2.0 g0, so the flag is a property of the instant-step treatment, not
specific to the push; the flag itself tests the push only. Sizing only at each case's
expected x (this step, third review) it fires on every cold-start structural case of file A
(the swing -2.689 g0 on silo_cold_200m_s1_st to -6.998 on _outer_hi), at every sweep point
(sweep 2's 300 m point nearest the limit, -2.124 g0), on file C's central (-4.389) and on
all four payload cases at P_ref, and also on n_peak above +6.0 g0 for _step (6.996 g0),
_outer_hi (6.998) and sweep 2's 50 m point (7.845); it does not fire on the two hot starts,
whose stage 1 keeps thrusting through the release (swing -1.581 and -1.617 g0).

The upper-stack flag (`structure_upper_stack_exceeded`: the push's peak n U above the
envelope's; it is the condition that sizes stage 2 and the interstage) is expected on
_step (push 9.58 MN against the envelope's 7.10 MN), _outer_hi (9.65 against its capped
envelope's 5.46 MN), _cap40 (6.00 against the capped envelope's 5.46 MN, below the pad's own
7.10 MN: the cap, not the push, puts the upper stack outside) and sweep 2's 50 m point (10.75
against 7.10 MN), with their payload cases (_step and _outer_hi), and on no other case;
_cap45 comes nearest without firing (5.99 against 6.15 MN).

**(d) Solves that exist, none of a pre-registered case.** S3's slow pins
(tests/test_structure_pipeline.py) solved SP1's headline through the coupled pipeline with
the structure off and with a constant 2,000 kg on stage 1: both reproduce SP1's x* and
verification P* to 0.0 kg (the same bits; D-SP7-42). Every structural solve made before this
note used only the synthetic structure file tests/data/structure_synthetic.yaml (sha256
78148004...; the gate file's sections with 100 stations per barrel, F_tu, the four
non-optimum factors, the rise time 0.8 s, the frequency 3 Hz, the ullage fraction and the
four MEOPs moved inside their ranges, and synthetic sets): the tests of S3, S3b and S3a that solve, S3's slow pin (c) among them; the
scratch solves of S3's smoke run (2026-10-09), of S3's gate (its G5 solve and two
charged-stage-2 solves beside it, 2026-10-11) and of S3's reviewers (2026-10-11); and S3b's
probe (2026-10-11), which solved silo_cold's central stage-1 case and a synthetic payload
case of silo_cold (P* 26,515.1 kg at dm_0 5,784.6 kg; docs/physics.md quotes it as measured
by hand, not a finding). None of them is a pre-registered case and none solved on a file
under configs/structures/. This checkpoint's timing case (section 11) solved one central
structural stage-1 case on that synthetic file: x* 15,195.4 kg at dm 5,561.1 kg. That is a
synthetic-file number, never quoted as a result. It is not the first such solve: S3's slow
pin (c) (tests/test_structure_pipeline.py::
test_structural_solve_charges_dm_through_the_pipeline, fixture `sp1_pins`, case
silo_cold_s1_syn) solves the same case (silo_cold, stage 1, the
synthetic file at its central settings: flown, rise_time, aft_ring, margin 0, no cap), on
the same gate vehicle and shared blocks at the shipped budget, with P_ref the pad's own P*,
beside the uncharged headline in one pass (the solver's memo keeps the two apart), and its
x* equals the timing case's to all digits (15,195.380332367815 kg in both, compared at this
step's last review; D-SP7-31 allows this step the one timing solve). That value was visible
in this session before this step's estimates and readings were fixed. The pin computes it
at every slow-tier run since S3 and records it as a junit user property
(`synthetic_x_star_kg_not_a_finding`), and the session's scratch folder keeps eight junit
XMLs of S3's slow-tier runs (2026-10-09 to 2026-10-11) that carry it; S3's smoke log printed
it on 2026-10-09 and S3's gate log on 2026-10-11 (G5: "x* = 15195.380332367815 (synthetic,
not a finding)", dm 5,561.1 kg); S3's reviewers' logs and a scratch summary (its offload
split 15,195.4 kg) printed it, and so did S3b's probe, beside its payload case. No note, log
or tracker committed before this note quotes it, and this step's scripts read none of those
records (the timing case's value is the timing run's own). The timing case's x* is used
once below, to measure the coupled placement's error on a solved case (section
7, its bias bullet, and twice in section 8). That use goes beyond step S6a's item 4 ("Its x*
is a synthetic-file number, never quoted as a result"), so it is a deviation of this step,
put to S6a's gate: accepted, it is logged in the phase file's section 12 at S6a's tracker
commit (section 12 below); struck, the comparison, the bias bullet's sentences on it and
their two echoes in section 8 are removed before this note's commit, and the timing case
stays in section 11 alone. The bias it measures is a property of the placement on the
synthetic file, not a measurement of the gate file's headline.

**(e) This step's sizing-only estimates** (section 7) place every case of both files on
SP1's penalty curve before the run. The central estimate is 11.1 t (26.9% of 41.26 t).

So the structural experiments re-measure, with a full solve and an independent
verification, numbers that sizing-only estimates have already placed. What this
pre-registration fixes in advance is the design around them, the method of the estimates
and how each result will be read, not ignorance of their size.

## 3. Comparison basis and resolution

- Reference payload P_ref: the full-load pad's payload capacity P* on the same vehicle,
  orbit (200 km circular, 28.5 deg, due east) and shared blocks (one budget id; guidance
  sweep-optimized per run; results called "sweep-optimized"). File A: 26,054.396243494975 kg
  (SP1's, tests/data/silo_offload_2d_record.json); file C: 24,700.013061881455 kg (SP1's
  bridge). The run's pad P* must equal it within 0.002 kg (section 9): the structure's
  envelope is that pad's own flight. This step flew both pads afresh for the estimates and
  got the same bits (0.0 kg).
- Offload x*: the largest evaluated stage-1 propellant removal with residual propellant
  m_res >= 0 when the assisted run flies P_ref; tanks partly filled, the mixture ratio kept.
  A structural case's assisted run carries its modelled mass dm(x) = dm1 + dm2, re-sized at
  every x the solve evaluates (sizing flown) or once at x = 0 (full_load), dm1 on stage 1
  (the stage-1 elements and the interstage, D-SP7-36) and dm2 on stage 2; the pad keeps its
  vehicle (D-SP7-35). A penalty row adds an assumed stage-1 dry mass instead (D-SP1-04).
- Stage 1 is the only headline. The stage-1 pad control is the solver's consistency test.
- Sensitivity arms: the assisted run and the pad perturbed alike (drive efficiency on the
  assisted run only); each arm's P_ref is the perturbed pad's P*; the arm's envelope is that
  perturbed pad's flight; no verification search (`OFFLOAD_SENSITIVITY_BASIS`). The
  stage-1 dry-mass arm's caveat (the phase file's deviation 17) goes beside the arms: its
  geometry is built from the perturbed variant, but the stations are loaded from the
  structure file's breakdown, so the perturbed dry mass reaches the sizing only through the
  push's interface force and the perturbed pad's envelope.
- Sweep points: the experiment pad's P_ref and envelope, verified; no paired pad, pad
  control or arms; their offload runs are not written (sweep_index.csv columns, including
  the structure columns, and checks only). A structural case at a push other than the
  headline's is a central solve; its band ends are sizing-only estimates labelled "the
  headline's sets" (design 4.2.6).
- Calibration: every gate number carries the gate fork's +14.3% miss; file C is the one
  robustness row on a fork inside the band.
- Resolution. SP1's rule (its pre-registration, section 3, and Amendment 1) carries over: a
  difference between two solves' x* reads as equal within R_P + 0.25 kg, as unresolved up
  to R = R_P + 0.25 kg + G, and as real beyond it, with G = 0.5 k w^2 / s (k 36.6
  kg/deg^2, w 0.07 deg) and R_P = final_payload_xtol_kg / s against a re-solved P_ref (0 at
  the same P_ref), s being |dm_res/dx|. For the uncharged cases SP1's values hold: R at
  most 2.55 kg at the same P_ref (s = 0.039 near silo_cold's x*) and about 3.8 kg against a
  re-solved P_ref. A structural solve differs in two ways. Its x* is expected at 4.8-39.1 t
  (section 7), most of it well below silo_cold's 41.26 t, so SP1's rule gives it s =
  0.031, the larger allowance. And the coupling flattens m_res(x), because dm falls as x
  rises: dm_res/dx = -s (1 - X' dm'), with X' the offload lost per kg of dry mass (-5.096
  kg/kg on SP1's last segment) and dm' = d(dm)/dx (-0.0140 kg/kg at the central's expected
  x*, sizing only), a factor 0.929 at the central, so every s-dependent term grows by
  1/0.929 = 1.077: G 3.1 kg, R about 3.4 kg at the same P_ref and about 5.1 kg against a
  re-solved P_ref (2.7 and 4.1 kg if s = 0.039 held). The fixed point's own tolerance (1e-6
  kg of dm, about 5e-6 kg of x*) is negligible beside these. Every structural difference
  expected below is tonnes, far beyond R; the reproductions are judged at 0.002 kg (section
  9), not against R.

## 4. The cases and what each is for

File A. All on silo_cold unless stated (3 g0 net, 100 m vented vertical stroke, exit 76.707
m/s at the mouth, massless carriage, stage 1 lit 0.5 s after release with the 2 s ramp; the
same resolved run as silo_screening_2d's and silo_offload_2d's silo_cold). The headline
settings: set central, sizing flown, dynamic rise_time (t_r 0.5 s, f 5 Hz: DLF
min(2, 1 + T/(pi t_r)) = 1.1273, the plateau a drive ramping over t_r needs charged by closed
form), entry aft_ring (8 pads), margin 0, no envelope cap, no override, not
plausibility-scaled. Every structural case writes every structure key out.

| Case | What it changes from the headline | Purpose and decision |
|---|---|---|
| silo_cold_s1 | uncharged (SP1's headline without its paired pad, which does not enter x*) | reproduces SP1's 41,262.908 kg within 0.002 kg (criterion 3); the row every structural case is read against |
| silo_cold_s1_dry+2t, +4t, +8.1t | SP1's assumed penalty rows, verbatim | reproduce 32,285.203 / 22,875.961 / 1,980.477 kg within 0.002 kg; the bracket beside the model and the curve the estimates are placed on (D-SP1-04) |
| silo_cold_s1_st | none | THE HEADLINE (design 4.10, 4.11; Q2 D-SP7-02, Q3 D-SP7-03, Q5 D-SP7-05, Q7 D-SP7-07 and D-SP7-09) |
| silo_cold_s1_st_phys_lo | set physics_low_mass | layer 1, the physics band's low-mass end, unscaled (D-SP7-18) |
| silo_cold_s1_st_phys_lo_scaled | physics_low_mass, plausibility_scaled | the same end with its whole dm (the load entry included) multiplied by the plausibility rule's factor (about 0.739, computed at run time; the trigger in section 2(c)), the band's low-mass end under D-SP7-33 as applied (D-SP7-41: both printed side by side); beyond design 4.10's table (section 6) |
| silo_cold_s1_st_phys_hi | set physics_high_mass | layer 1, the band's high-mass (adverse) end; the rule's factor there is 1 |
| silo_cold_s1_st_outer_lo | set outer_low_mass (its margin 0.25, no cap) | layer 3, the outer envelope's low-mass end |
| silo_cold_s1_st_outer_hi | set outer_high_mass (margin 0, cap 4.0 g0) | layer 3, the outer envelope's high-mass end |
| silo_cold_s1_st_qs | dynamic quasi_static (DLF 1, the plain plateau) | Q7's row (D-SP7-07) |
| silo_cold_s1_st_step | dynamic step (DLF 2) | Q7's row: the dynamic factor of the push the constant_accel trajectory actually flies (an instant step; survey 08's recommended reporting factor, section 2(a)), and the single-mode bound |
| silo_cold_s1_st_full | sizing full_load (dm sized once at x = 0) | Q2's row (D-SP7-02) |
| silo_cold_s1_st_ts | entry thrust_structure (k_ts 0.2805 kg/kN) | Q5's row, at the headline's prominence (D-SP7-05, D-SP7-17) |
| silo_cold_s1_st_m10, _m25 | margin 0.10, 0.25 on the envelope's loads and pressures | Q3's rows (D-SP7-03) |
| silo_cold_s1_st_cap45 | the pad's stage-1 felt n capped at 4.5 g0 in the envelope | the unthrottled-envelope direction (design 4.2.6, a design-assumption axis of D-SP7-18 on the envelope of D-SP7-15; review H6, E20) |
| silo_cold_s1_st_cap40 | the pad's stage-1 felt n capped at 4.0 g0 in the envelope | the same axis's second row (design 4.2.6, "capped at 4.5 and 4.0 g0"; appendix A's disposition of reviews H6 and E20, "the envelope-cap rows (4.5 and 4.0 g0)", so that the envelope's sensitivity runs both ways); beyond design 4.10's table (section 6, item 11) |
| silo_hot_full_s1, _st | silo_hot_full (stage 1 at full thrust from push start), uncharged and central | the lower interface force against the propellant burned on the track (no decision of its own; design 4.10, review E8); SP1 never solved silo_hot_full; with SP1's exhaust caveat, which favours both hot starts (section 10) |
| silo_hot_ramp_s1, _st | silo_hot_ramp_on_track (full thrust at release), uncharged and central | the same; the uncharged case reproduces SP1's 46,013.437 kg within 0.002 kg |
| silo_cold_200m_s1, _st | silo_cold_200m (200 m at 1.5 g0 net, the same exit speed), uncharged and central | sweep 2's base, the lower felt load at the same exit speed (review N8, D12, E17); the uncharged case reproduces SP1's 41,262.971 kg within 0.002 kg; from step S6a's case list, beyond design 4.10's table (section 6); read under S2 only (sweep 2's 200 m point flies the same run), with its 260 m facility and its 2.5 g0 felt load beside, and no R sentence of its own (section 8) |
| pad__offload_stage1 | the stage-1 pad control | the solver's consistency test (D-SP1-10); expected as SP1's (section 7) |
| arms on silo_cold_s1_st | +/-10% stage-1 dry mass, stage-1 Isp_vac, cd_scale, drive efficiency | CLAUDE.md's headline sensitivity (never cut); the two drive-efficiency arms change only the electricity, so they reuse the nominal solve |
| silo_cold_pstar_st | payload case: silo_cold at its own P* with the central structure sized for its full-load push, two passes | the payload form (design 4.4), read beside silo_cold_s1_st_full; never under the offload heading |
| silo_cold_pstar_st_phys_hi | the same with physics_high_mass | the payload form at the adverse band end (review E14); it also gives the phys_hi row's payload deficit if that row ends no_offload |
| silo_cold_pstar_st_outer_hi | the same with outer_high_mass (its recorded margin 0 and cap 4.0 g0) | the payload deficit of silo_cold_s1_st_outer_hi, expected to end no_offload (D-SP7-32; exit criterion 4); beyond design 4.10's list (section 6) |
| silo_cold_pstar_st_step | the same with the central set at dynamic step | the payload deficit of silo_cold_s1_st_step, expected to end no_offload (D-SP7-32; exit criterion 4); beyond design 4.10's list (section 6) |

File C (the README-loads fork): silo_cold_s1 (uncharged, reproduces SP1's bridge 36,006.444
kg within 0.002 kg; results/silo_offload_2d_readme/20261003T112956Z) and silo_cold_s1_st
(file A's headline settings against this fork's structure file), with the stage-1 pad
control. No sweep, arm, payload case or energy block.

## 5. The sweeps and what each is for

Each sweep solves two stage-1 cases at every point, both rebuilt on the point's run, at the
experiment pad's P_ref, each verified: the uncharged case (which reproduces SP1's point) and
the central structural case.

| Sweep | Axis | Points | Question |
|---|---|---|---|
| 1 | assist.stroke_m on silo_cold (3 g0) | 25, 50, 100, 200, 300 m (exit 38.35, 54.24, 76.71, 108.48, 132.86 m/s) | the exit-speed axis with the structure charged: the lowest exit speed that still offloads, the direct test of "every m/s of assist helps" |
| 2 | assist.stroke_m on silo_cold_200m (exit 76.70717046013364 m/s) | 50, 100, 200, 300 m (net 6, 3, 1.5, 1 g0; felt about 7.0, 4.0, 2.5, 2.0 g0) | the depth axis: how the structural offload grows as a deeper silo lowers the felt load at the same exit speed |

SP1's notes hold (its pre-registration, sections 5 and 7): at 25 and 50 m (sweep 1) the
coast slows below v_k = 50 m/s by the ignition, so those points rise vertically before the
kick, a regime change inside the sweep; the 300 m point's kick comes above 120 m/s, an
upper bound. At sweep 2's 50 m point the felt load exceeds the pad's MECO (5.195 g0), so the
push sizes stage 2 and the interstage too (D-SP7-11, D-SP7-36). Sweep 2's 100 m point
agrees with silo_cold to integrator noise (an acceleration one ulp lower), not bit for bit.

Beside the sweeps the findings note gives sizing-only tables (no flight; S7a, by a
committed script under docs/findings/scripts/): the central structure's dm by element
against the felt load n from 1.2 to 7.0 g0 in steps of 0.1 g0 at the fixed exit speed
76.70717046013364 m/s (stroke L = v_e^2 / (2 a), a = n g0 - g_eff, at SP1's headline
offload), each element's break-even n (the smallest n with a positive increment, by
bisection to 0.001 g0) and the stroke it implies; and the physics band's estimated ends at
each sweep point (section 7 gives them). SP1's headline offload (41.26 t) leaves a lighter
stack than any structural x* does, so at it dm is understated and each break-even n
overstated, both for the assist (the central's dm is 5,901.8 kg there against 6,309.6 kg at
its expected x* of 11.1 t); the same table and break-even values are therefore also given
at x = 0 (the full-load stack, the adverse bound), the two side by side.

## 6. Choices fixed by this pre-registration

1. **No paired pad on the uncharged cases**: SP1's attribution (the head start against the
   lighter stack) is SP1's finding and does not enter x*; a structural case may not have one
   (D-SP7-35). silo_cold_s1's case dict is SP1's with paired_pad false (a test).
2. **The plausibility-scaled twin of the low-mass end** (silo_cold_s1_st_phys_lo_scaled; a
   case beyond design 4.10's table, which lists the two physics ends only): D-SP7-33 widens
   the band end on the side the rule fires, applied as approved (D-SP7-41), and the
   Structure subsection prints the scaled end only when such a case is flown (S3b's band
   line), so the physics band's low-mass end read by section 8 is the scaled case, with the
   unscaled one printed beside it. Read it with its trigger (section 2(c)): a double count
   of buckling material at the stage-1 LOX barrel, an element whose own push increment is
   0.7 kg at the headline push (25.6 kg at the central's expected x*, 0 in the low-mass
   set's sizing), while the factor multiplies the case's whole dm, the aft skirt and the
   load ring included (half of it), which the Heineman relation does not cover. The
   high-mass end's factor is 1 (M/R above the band's upper edge fires only the
   favourable-end factor), so it has no twin. Every case or payload case beyond design
   4.10's lists is logged as a deviation of the registered case list in the phase file's
   section 12 at S6a's tracker commit: this twin, silo_cold_200m's pair (item 4), the two
   added payload cases (item 5), the 4.0 g0 cap row (item 11) and the uncharged case solved
   at every sweep point beside the central one (section 5; design 4.10's sweeps name the
   central structure only). silo_hot_full_s1 is not
   among them: design 4.10's table lists it (item 4).
3. **The outer sets' margin and cap written out** as the file records them (outer_low_mass
   margin 0.25, no cap; outer_high_mass margin 0, cap 4.0 g0); a different value is refused.
4. **silo_hot_full_s1, new against SP1, not against the design** (uncharged; design 4.10's
   table lists it with _st): SP1 never solved silo_hot_full's offload, so its structural row
   has its own uncharged reference in the same run and no SP1 value to reproduce (its x0 in
   section 7 is an estimate). **silo_cold_200m's pair added** (silo_cold_200m_s1 and _st):
   sweep 2's base, from step S6a's case list, beyond design 4.10's table. Its structural
   case is read under S2 only (sweep 2's 200 m point flies the same run), with no R
   sentence of its own (second review, finding H2-06: an R sentence would quote sweep 2's
   favourable depth point twice in the headline and its adverse 50 m point once).
5. **A payload case for every row expected to end no_offload** (silo_cold_pstar_st_outer_hi
   and silo_cold_pstar_st_step, beyond design 4.10's list of two; S6a review finding H1-01):
   D-SP7-32 reports a no_offload end "with its delta-v shortfall and its payload deficit"
   and exit criterion 4 asks the same of every case of the headline's table, while the
   summary quotes a payload deficit only from a payload case of the same variant and
   settings (the sizing basis aside; `summary._no_offload_line`), and the estimates of
   section 7 put outer_hi and the step row at no offload as well as phys_hi. They cost
   four searched runs (section 11). A case that ends no_offload although section 7 expects
   an offload has no payload case: it is reported with its shortfall and "payload deficit
   not flown (no payload case at these settings)" and named as departing from its
   estimate; no payload case is added after the run except by an amendment. A sweep point
   that ends no_offload is reported the same way (a payload case flies a variant, not a
   sweep point; exit criterion 4 does not cover the sweeps).
6. **The push-time RP-1 pressure at its range's high end is not flown** (design 4.10: flown
   only if it moves dm by more than 0.5 t). Measured sizing only at the headline push (x =
   41,262.908 kg, the central structure, the pad's envelope at the central 2.62 bar), with
   the stage-1 RP-1 tank's MEOP raised to 4.00 bar (and its minimum pressure with it, at the
   0.84 fraction) for the push only: dm 5,808.6 kg against 5,901.8 kg, a move of -93.3 kg
   (the RP-1 barrel -111.3 kg from the extra relief, the aft dome +49.5 kg from the extra
   hoop, the common dome -29.7 kg, the tube -1.2 kg, the skirt and ring -0.5 kg), below
   0.5 t. At the range's full high end, the minimum pressure's fraction also raised to its
   high end (0.93, the largest push-time minimum pressure the ranges allow; pressure
   stabilisation relieves buckling through p_min), the move is -148.7 kg (the RP-1 barrel
   -157.2, the common dome -38.9, the aft dome +49.5, the tube -1.2, the skirt and ring
   -0.9 kg); the fraction alone at 0.93 moves dm by -38.4 kg, and both stage-1 tanks at 4.00
   bar and 0.93 by -58.6 kg. At the central's expected x* (11,105.2 kg) the same moves are
   -71.1, -127.0, -38.5 and +17.7 kg. Raised for the envelope too (the tornado's row) the
   MEOP moves dm by +116.5 kg. Every move is below 0.5 t, so no row is added.
7. **Names.** Every derived run name (cases, arms with their variants and pads, sweep-point
   cases, payload cases) is a valid results name within 64 characters (a test; the longest,
   an Isp arm of silo_cold_s1_st, has 61).
8. **The reference for the reading rules** is SP1's uncharged headline, 41,262.9 kg (50%:
   20,631.45 kg), for every row of file A at any push, as D-SP7-32 states it; each row's
   fraction of its own uncharged x* is reported beside. File C's central is read against
   its own uncharged offload (section 8).
9. **The structure files stay as frozen; nothing is added to them** (the decisions the
   phase file's deviations 23 and 25 left to this step under D-SP7-31). S2's tornado and
   search D's break-even values, and a structured record of the push the sets were found
   at, are not written into configs/structures: the files stay byte-identical to S2's
   commit (section 12). So `structure_inputs` keeps `tornado` and `break_even` null with its
   `tornado_note` (`STRUCTURE_SETS_NOT_IN_FILE`); the findings note quotes the tornado and
   break-even values from S2's session log (the phase file, section 11) as sizing-only
   estimates; and the band ends at a push other than the headline's stay sizing-only
   estimates labelled "the headline's sets", beside the summary's unconditional
   applicability line (`STRUCTURE_SETS_APPLICABILITY`).
10. **The fork comparison has two registered tests, both quoted** (section 8, C): C1 on the
   structure's offload cost U - X (the offload the structure takes away) and C2 on the
   share X/U it leaves, each with its own fixed sentence. Disclosed in full: the draft
   registered C2 alone (SP1's 10% bridge threshold applied to X/U), which under the
   estimates of section 7 fires "depends on the vehicle masses" (20.8% against 26.9%, 23%
   apart). At this note's first review (S6a review finding N1), with those estimates known,
   the rule was restated as C1 alone, whose expected sentence is "nearly the same" (5.4%
   apart). Changing a rule after seeing which way it fires is post-hoc (D-SP7-41's reason),
   so at the second review (findings H2-02 and N2-03) both tests are registered and both
   sentences go beside the headline, whichever way each fires. The case for each: X/U = 1 -
   (U - X)/U amplifies a relative change of U by about (1 - F)/F, 3 to 4 times here, and
   the fork's U is 12.7% below the gate's (SP1's bridge measured that), so C2 fires
   "depends" for almost any small leftover; the cost scales with the masses, as a threshold
   of twice the forks' 5.5% P* difference assumes, but under section 7's shift method C1's
   expected value is set by the two dm values alone (the fork placed on the gate's slope)
   and says nothing about how the run's C1 will read, which the fork's own slope decides.
   Neither test is decided by the estimates: a fork slope 4.9% shallower than the gate's
   flips C1, and one 4.4-11.2% shallower flips C2 (section 7). SP1's bridge read x*/m_p1, a
   fraction of the stage-1 load; its structural analogue X/m_p1 is printed beside (2.70% on
   the gate against 1.89% on the fork under the estimates, 30% apart) and is not read. The
   restatement and this registration of both tests were put to the user at S6a's gate
   (2026-10-16): both tests are registered and both sentences quoted, whichever way each
   fires (D-SP7-45, the user's choice). At the same gate the user accepted the headline
   sentence's amended form below (D-SP7-46).
11. **The 4.0 g0 envelope-cap row added** (silo_cold_s1_st_cap40, at the second review,
   finding H2-01; beyond design 4.10's table, which lists the 4.5 g0 row only). Design 4.2.6
   names the axis with both rows ("the pad's stage-1 felt n capped at 4.5 and 4.0 g0 when
   building the envelope"), and appendix A's disposition of reviews H6 and E20 took "the
   envelope-cap rows (4.5 and 4.0 g0)" so that the envelope's sensitivities run both ways.
   Without it the only adverse envelope row flown would be the milder cap, beside two margin
   rows that lower dm, and the outer high-mass end carries the 4.0 g0 cap only mixed with
   every other adverse axis. Its estimate was known when it was added (S2's 5,039 kg in
   section 2(c); section 7: 4,800 kg, stage 2 sized), and the reading it is expected to
   fire, "cancels most", is the 4.5 g0 row's too. It costs one structural verified solve
   (section 11).

## 7. Expected values (estimates; none is a target)

**Method.** Sizing only, no offload solved (D-SP7-31). For every structural case the case's
own transform (`sim.offload_structure_transform`: the geometry of the variant at its full
loads, the envelope of the pad flown afresh at P_ref, the push of the case's start, the
fixed point dm = S(push(m(x) + dm)) iterated to 1e-6 kg, the plausibility factor when the
case is scaled) gives dm1(x) and dm2(x) at any offload x: exactly what the solve will add at
x. The coupled placement (`structure.coupled_placement`) then solves the fixed point x =
max(0, X(dm1(x) + w dm2(x))) from the uncharged offload, until two iterates agree to 1 g,
with w = 24 / 4.381 = 5.478 (a kg of stage-2 increment in kg of stage-1 dry mass of equal
offload cost; an estimate, used only where stage 2 is sized). X is SP1's penalty curve
through its four solved rows (0, 2, 4 and 8.1 t of added stage-1 dry mass to 41,262.908,
32,285.203, 22,875.961 and 1,980.477 kg), linear between them; beyond 8.1 t it is
extrapolated along the last segment (-5.096 kg/kg), and X <= 0 means no offload: on the
headline's curve that is any equivalent dm at or above 8,488.6 kg. For a push other than
SP1's headline push the uncharged x0 comes from SP1's recorded run or sweep at that point
and the curve is shifted to it, X_case(dm) = x0 + (X(dm) - 41,262.908): the slope (offload
lost per kg of dry mass) is SP1's. x0 sources: silo_cold_200m_s1 41,262.971 kg and
silo_hot_ramp_s1 46,013.437 kg (results/silo_offload_2d/20261003T112934Z); sweep points
from results/silo_offload_2d/20261003T112949Z/sweep_1 and sweep_2/sweep_index.csv (12
significant digits); the arms from the same run's offload.sensitivity records; file C from
results/silo_offload_2d_readme/20261003T112956Z (36,006.444 kg). silo_hot_full has no SP1
offload: its x0 is estimated as its payload gain (+1,488.6 kg, RQ3-2d) times silo_hot_ramp's
offload per kg of payload gain (46,013.4 / 1,733.8 = 26.54), 39,506 kg (40,982 kg at
silo_cold's 27.53); the run solves silo_hot_full_s1 itself, and the structural estimate
moves one for one with x0. The "naive" placement reads the dm sized at x0 straight off the
curve, with no re-sizing.

**Biases, with their direction and size where known.**
- The curve is concave (its segments steepen, -4.489, -4.705, -5.096 kg/kg), so a chord
  between its rows places x low (against the assist) and the extended last chord beyond
  8.1 t places it high (for the assist). Measured once on a solved case, the checkpoint's
  synthetic timing case (a use put to S6a's gate, section 2(d)): placed at 14,898.0 kg
  against its solve's 15,195.4 kg, 297 kg low (2.0%), at dm about 5.6 t, between the 4 t and
  8.1 t rows. A solved x* somewhat above the coupled estimates of that region is therefore
  expected; not an adjustment.
- The naive placement favours the assist (the push at x0 is lighter than at x*): by 2.1 t at
  the headline (13,183 against 11,105 kg), up to 3.7 t elsewhere (0 for the full-load row,
  whose dm does not depend on x; the tables' naive column).
- The shift for pushes whose x0 is below 41.26 t (silo_hot_full, sweep 1's 25 and 50 m,
  file C) borrows slopes measured at higher offload levels, which are shallower than at the
  case's own level, so it favours the assist; the level-matched reading (X_case(dm) =
  X(dm0 + dm) with X(dm0) = x0) gives 15,001 kg instead of 15,259 kg for silo_hot_full_s1_st,
  6,710 kg instead of 7,475 kg for file C, and no offload either way at 25 and 50 m. For x0
  above 41.26 t (silo_hot_ramp, sweep 1's 200 and 300 m, the Isp -10% arm) the true slope at
  those levels is not measured; if it keeps flattening as SP1's three segments do (linearly
  in the offload level, an extrapolation), the shift places those x* about 3 t (200 m) and
  4 t (300 m) low, against the assist.
- The arms are placed on the headline's slope; the perturbed vehicles' own offload lost per
  kg of dry mass is not measured (sign not known).
- The payload cases and the no_offload rows' payload deficits use RQ3-2d's linear rate,
  184.3 kg of P* per t of stage-1 dry mass, and w x 184.3 for stage 2. It was measured over
  +/-2.22 t only (silo_cold's stage-1 dry-mass arms, results/silo_screening_2d/
  20260930T175743Z: 182.3 kg/t on the +2.22 t side, 186.2 on the -2.22 t side), so the
  curve is convex and the rate falls as mass is added: extrapolated 10 to 30 times beyond
  that range, the linear rate likely overstates the large deficits (against the assist). A
  quadratic through the two arms (184.27 kg/t, +0.879 kg/t^2) is given beside as the other
  end of a range, itself an extrapolation. Stage 2's dm is charged here at w x 184.3 =
  1.0096 kg of P* per kg, while in the pipeline a kg of stage-2 dry mass costs exactly 1 kg
  of P* (moving mass between the payload and stage 2's dry mass leaves the vehicle's mass the
  same at every instant, so the trajectory and m_res do not change; w belongs to the offload
  placement only): the estimates overstate stage 2's charge by 1%, at most about 13 kg
  (outer_hi's 1,362.1 kg) and 3 kg (step), inside their rounding. The delta-v shortfall
  converts the deficit with SP1's 0.993 kg of m_res per kg of payload, m_res = 0.993 (P_ref
  - P*), and then by the
  pipeline's own rule (what the run prints as dv_shortfall_mps: c2 ln(m_e / (m_e - |m_res|)),
  c2 = 348 s x g0, m_e the stage-2 dry mass with any dm2 plus P_ref), not by the slope at
  m_res = 0 (8.81 kg of m_res per m/s), which understates large shortfalls (outer_hi: 1,202
  against 1,403 m/s for the same m_res). All are first-order, labelled estimates.
- This step's sizing iterates the fixed point the solve iterates; S2's table used its first
  pass, so the estimates here sit 0.0-0.5 t below S2's (central 11,105 against 11,298 kg).

**File A at the headline push** (dm at SP1's x = 41,262.9 kg is S2's push, converged; dm at
x* is at the estimate, or at x = 0 for no offload; % of 41,262.9 kg; the stage-1 load is
410.9 t; push numbers at x*: n_q / DLF / n_peak [g0] / F_peak [MN]):

| Case | dm1 + dm2 at 41.26 t [kg] | dm1 + dm2 at x* [kg] | Expected x* [kg] (% of 41,262.9; % of stage 1) | Naive [kg] | n_q / DLF / n_peak / F_peak | Reading that would fire |
|---|---|---|---|---|---|---|
| silo_cold_s1 (uncharged) | 0 | 0 | 41,262.9 (100%; 10.04%), SP1's record, reproduced | | | the reference |
| silo_cold_s1_dry+2t | 2,000 + 0, assumed | 2,000 + 0, assumed | 32,285.2 (78.2%; 7.86%), SP1's record, reproduced | | | none: an assumed penalty, not sized structure |
| silo_cold_s1_dry+4t | 4,000 + 0, assumed | 4,000 + 0, assumed | 22,876.0 (55.4%; 5.57%), SP1's record, reproduced | | | none: an assumed penalty, not sized structure |
| silo_cold_s1_dry+8.1t | 8,100 + 0, assumed | 8,100 + 0, assumed | 1,980.5 (4.8%; 0.48%), SP1's record, reproduced | | | none: an assumed penalty, not sized structure |
| silo_cold_s1_st | 5,901.8 + 0 | 6,309.6 + 0 | 11,105.2 (26.9%; 2.70%) | 13,183.3 | 4.006 / 1.1273 / 4.389 / 24.43 | cancels most |
| silo_cold_s1_st_phys_lo | 3,688.7 + 0 | 3,833.7 + 0 | 23,658.2 (57.3%; 5.76%) | 24,340.6 | 4.006 / 1.1273 / 4.389 / 23.78 | (band end, unscaled) above half |
| silo_cold_s1_st_phys_lo_scaled | 2,723.8 + 0 | 2,801.5 + 0 | 28,514.4 (69.1%; 6.94%) | 28,879.9 | 4.006 / 1.1273 / 4.389 / 23.53 | (band end) above half |
| silo_cold_s1_st_phys_hi | 19,046.0 + 0 | 21,551.8 + 0 | no offload | no offload | 4.006 / 1.1273 / 4.389 / 25.56 | (band end) no offload: undecided |
| silo_cold_s1_st_outer_lo | 2,190.3 + 0 | 2,253.5 + 0 | 31,092.5 (75.4%; 7.57%) | 31,389.9 | 4.034 / 1.0318 / 4.131 / 22.02 | (outer end) above half |
| silo_cold_s1_st_outer_hi | 53,362.0 + 1,362.1 | 58,536.8 + 1,362.1 | no offload | no offload | 3.997 / 2.0000 / 6.998 / 43.39 | (outer end) no offload: outer undecided |
| silo_cold_s1_st_qs | 5,289.8 + 0 | 5,598.7 + 0 | 14,728.3 (35.7%; 3.58%) | 16,302.5 | 3.996 / 1.0000 / 3.996 / 22.07 | row cancels most |
| silo_cold_s1_st_step | 12,042.0 + 319.8 | 13,178.1 + 319.8 | no offload | no offload | 3.996 / 2.0000 / 6.996 / 40.20 | row cancels all |
| silo_cold_s1_st_full | 6,467.0 + 0 | 6,467.0 + 0 | 10,302.9 (25.0%; 2.51%) | 10,302.9 | 4.006 / 1.1273 / 4.389 / 24.91 | row cancels most |
| silo_cold_s1_st_ts | 6,638.3 + 0 | 7,356.5 + 0 | 5,769.7 (14.0%; 1.40%) | 9,429.8 | 4.006 / 1.1273 / 4.389 / 24.70 | row cancels most |
| silo_cold_s1_st_m10 | 5,587.6 + 0 | 5,947.2 + 0 | 12,951.9 (31.4%; 3.15%) | 14,785.1 | 4.006 / 1.1273 / 4.389 / 24.33 | row cancels most |
| silo_cold_s1_st_m25 | 5,134.7 + 0 | 5,463.2 + 0 | 15,418.8 (37.4%; 3.75%) | 17,093.0 | 4.006 / 1.1273 / 4.389 / 24.21 | row cancels most |
| silo_cold_s1_st_cap45 | 6,014.8 + 0 | 6,492.4 + 0 | 10,173.4 (24.7%; 2.48%) | 12,607.6 | 4.006 / 1.1273 / 4.389 / 24.48 | row cancels most |
| silo_cold_s1_st_cap40 | 6,600.4 + 67.9 | 7,174.9 + 67.9 | 4,800.4 (11.6%; 1.17%) | 7,728.3 | 4.006 / 1.1273 / 4.389 / 24.74 | row cancels most |

SP1's four rows head the table as the bracket the modelled rows sit in: the central's
modelled 6.3 t at x* lies between SP1's assumed +4 t and +8.1 t, and the step row, the
physics high-mass end and the outer high-mass end lie beyond the +8.1 t row (equivalent dm
14.9, 21.6 and 66.0 t at x = 0).

The no_offload rows, with estimates of what the run prints instead of "0 t": the delta-v
shortfall of the full-load push at x = 0 (from P* - P_ref of the vehicle carrying dm(0),
converted by the pipeline's rule; the linear payload rate first, the quadratic second), and
the payload deficit the summary quotes, P_2* - P_ref of the payload case at the same
settings (two passes, section 7's payload paragraph). phys_hi (dm at x = 0 21,551.8 kg):
about 291 m/s short (241 on the quadratic), deficit about -2,449 kg (-2,048);
outer_hi (equivalent dm 65,998.7 kg, far beyond every measured rate): of order 800 to 1,400
m/s short (1,403 linear, 831 quadratic), deficit of order 7 to 10 t (-9,984 linear, -6,668
quadratic), a range rather than a value; step (equivalent dm 14,930.2 kg): about 143 m/s
short (120), deficit about -1,231 kg (-1,041).

The central's elements at x* (kg): the aft skirt 2,096.6 and the ring frame 1,523.0 (the
load entry, 57% of dm), the RP-1 barrel 2,224.3, the common dome 298.6, the RP-1 aft dome
130.0, the LOX barrel 25.6, the transfer tube 11.6; stage 2 and the interstage not sized
(n_peak U below MECO's). The thrust-structure row moves the entry's 3.6 t into a 4.6 t
thrust-structure increment. The step row and the outer high-mass end size stage 2 (dm2
319.8 and 1,362.1 kg) and the interstage (184.2 and 915.3 kg, charged to stage 1). The 4.0
g0 cap row sizes them too, at every offload (dm2 67.9 kg: stage 2's RP-1 barrel 36.9, LOX
barrel 17.8, common dome 12.1, aft dome 1.1; the interstage 53.8 kg on stage 1): the cap
lowers the upper stack's envelope below the push's 4.389 g0, and MECO's compression
envelope on the stage-1 LOX barrel with it (that barrel 650.0 kg at x*, against the
central's 25.6). Its other elements at x*: the aft skirt 2,123.8, the ring frame 1,536.0,
the RP-1 barrel 2,359.8, the common dome 305.1, the RP-1 aft dome 132.7, the tube 13.8 kg.

**File A at the other pushes** (central, and the headline's sets as sizing-only band
estimates; x0 as in the method):

| Case | x0 [kg] | dm1 + dm2 at x* [kg] | Expected x* [kg] (% of 41,262.9; % of own x0) | Naive [kg] | F_peak [MN] | Band estimate: phys_hi / phys_lo / phys_lo scaled [kg] | Reading |
|---|---|---|---|---|---|---|---|
| silo_hot_full_s1_st | 39,506 (estimate) | 5,150.0 + 0 | 15,258.5 (37.0%; 38.6%) | 17,027.9 | 16.48 | none / 24,786 / 28,872 | row cancels most |
| silo_hot_ramp_s1_st | 46,013.4 | 6,238.4 + 0 | 16,218.5 (39.3%; 35.2%) | 18,245.8 | 24.20 | none / 28,600 / 33,405 | row cancels most |
| silo_cold_200m_s1_st | 41,263.0 | 3,202.3 + 0 | 26,628.9 (64.5%; 64.5%) | 27,256.0 | 14.47 | none / 32,960 / 35,174 | read under S2 (sweep 2's 200 m point) |

silo_hot_ramp's structure equals silo_cold's at the same x (5,901.8 kg at 41.26 t): its peak
interface force comes at push start, before its ramp's thrust builds; its larger x* comes
from its larger uncharged offload (+4.75 t of its +5.11 t lead: the structure's offload cost
U - X is 29.79 t against the cold start's 30.16 t, 0.36 t less). silo_hot_full's interface
force is a third lower (16.5 against 24.4 MN), but the tanks still see the same felt load,
so dm falls by only 18%; its lead (+4.15 t) is structural, on an uncharged offload estimated
1.76 t below the cold start's (its cost U - X about 24.25 t against 30.16 t, the estimate
moving one for one with its x0).

**Sweeps** (central; band estimates are the headline's sets at the point's push; x0 from
SP1's sweep index; n_q / DLF / n_peak in g0):

| Sweep | L [m] | Exit [m/s] | x0 [kg] | n_q / DLF / n_peak | dm1 + dm2 at x* [kg] | Expected x* [kg] (% of 41,262.9; % of own) | Naive [kg] | Band estimate [kg] | Reading |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 25 | 38.35 | 18,765.1 | 4.034 / 1.1273 / 4.421 | 6,526.5 + 0 | no offload (about 66 m/s short, P* about 580 kg below P_ref; 62 m/s and 545 kg on the quadratic) | no offload | none / 69 / 5,236 | no offload |
| 1 | 50 | 54.24 | 28,653.6 | 4.015 / 1.1273 / 4.399 | 6,486.6 + 0 | no offload (about 24 m/s short, P* about 210 kg below; 19 m/s and 171 kg) | no offload | none / 10,489 / 15,496 | no offload |
| 1 | 100 | 76.71 | 41,262.9 | 4.006 / 1.1273 / 4.389 | 6,309.6 + 0 | 11,105.2 (26.9%; 26.9%) | 13,183.3 | none / 23,658 / 28,514 | offloads |
| 1 | 200 | 108.48 | 56,827.2 | 4.001 / 1.1273 / 4.384 | 6,070.3 + 0 | 27,888.9 (67.6%; 49.1%) | 29,791.2 | none / 39,876 / 44,558 | offloads |
| 1 | 300 | 132.86 | 67,285.8 | 4.000 / 1.1273 / 4.382 | 5,918.6 + 0 | 39,120.9 (94.8%; 58.1%) | 40,936.1 | none / 50,768 / 55,334 | offloads (upper bound: unconstrained kick) |
| 2 | 50 | 76.71 | 41,263.0 | 7.072 / 1.1273 / 7.845 | 15,543.0 + 506.1 | no offload (about 215 m/s short, P* about 1,880 kg below; 180 m/s and 1,581 kg) | no offload | none / none / none | no offload (stage 2 sized) |
| 2 | 100 | 76.71 | 41,263.0 | 4.006 / 1.1273 / 4.389 | 6,309.6 + 0 | 11,105.3 (26.9%) | 13,183.4 | none / 23,658 / 28,515 | offloads |
| 2 | 200 | 76.71 | 41,263.0 | 2.498 / 1.1273 / 2.689 | 3,202.3 + 0 | 26,628.9 (64.5%) | 27,256.0 | none / 32,960 / 35,174 | offloads |
| 2 | 300 | 76.71 | 41,262.9 | 1.997 / 1.1273 / 2.124 | 2,055.3 + 0 | 32,024.8 (77.6%) | 32,364.4 | 13,556 / 36,129 / 37,491 | offloads |

The structural mass is set by the felt load, nearly the same at every point of sweep 1
(about 4.0 g0 felt; dm 5.9-6.5 t), while the uncharged offload grows with the exit speed; so
the short strokes, whose uncharged offload is smaller than the mass's cost, are expected to
end no_offload. Sweep 2's 50 m point (felt 7.0 g0) sizes stage 2 (dm2 506.1 kg; stage 2's
RP-1 barrel 197.6, LOX barrel 186.7, common dome 82.6, aft dome 39.1 kg; the interstage
264.8 kg on stage 1). The uncharged points are expected to reproduce SP1's sweep index
(section 9). A sweep point that ends no_offload prints its shortfall and "payload deficit
not flown" (section 6, item 5): the deficits in the table are estimates, never quoted as
results.

**Arms of silo_cold_s1_st** (each on its perturbed pad, flown afresh here: every pad's P*
equals SP1's recorded arm P_ref to 0.0 kg; x0 SP1's arm):

| Arm | P_ref [kg] | x0 [kg] | dm1 at x* [kg] | Expected x* [kg] (% of 41,262.9) |
|---|---|---|---|---|
| stage-1 dry mass +10% | 25,661.0 | 41,639.5 | 6,345.4 | 11,299.3 (27.4%) |
| stage-1 dry mass -10% | 26,456.3 | 40,892.4 | 6,274.0 | 10,916.2 (26.5%) |
| stage-1 Isp_vac +10% | 29,927.4 | 38,668.0 | 6,393.2 | 8,084.0 (19.6%) |
| stage-1 Isp_vac -10% | 22,478.3 | 44,464.5 | 6,221.0 | 14,758.5 (35.8%) |
| cd_scale +10% | 26,015.5 | 41,222.0 | 6,309.8 | 11,063.4 (26.8%) |
| cd_scale -10% | 26,093.5 | 41,304.2 | 6,309.4 | 11,147.5 (27.0%) |
| drive efficiency +/-10% | 26,054.4 | 41,262.9 | 6,309.6 | 11,105.2 (26.9%; the nominal solve reused) |

So the headline is expected with the arms' range 8.1 to 14.8 t beside it, every arm below
half.

**Payload cases** (two passes on the linear rate, the quadratic of the bias bullet in
brackets; silo_cold's uncharged P* 27,553.227 kg, results/silo_screening_2d/
20260930T175743Z): silo_cold_pstar_st dm_0 6,467.0 kg at P_ref, P_1* about 26,361 kg, dm_1
6,471.2 kg, P_2* about 26,361 kg, about +306 kg against P_ref [+343] (the full-load
structure leaves silo_cold above the pad by about a fifth of its uncharged +1,498.8 kg);
silo_cold_pstar_st_phys_hi dm_0 21,551.8 kg, P_1* about 23,581 kg, dm_1 21,419.3 kg, P_2*
about 23,606 kg, about -2,449 kg against P_ref [-2,048] (below the pad); stage 2 is not sized
in either. silo_cold_pstar_st_outer_hi dm_0 58,536.8 + 1,362.1 kg, P_1* about 15,390 kg,
dm_1 56,941.8 + 978.7 kg, P_2* about 16,071 kg, about -9,984 kg [-6,668; P_2* 19,386 kg]:
stage 2 sized, and P* far outside every measured rate, so of order 7 to 10 t below the pad;
silo_cold_pstar_st_step dm_0 13,178.1 + 319.8 kg, P_1* about 24,802 kg, dm_1 13,108.6 + 311.3
kg, P_2* about 24,823 kg, about -1,231 kg [-1,041]. A payload case whose search finds no
P* ends with that search's status and writes nothing (the phase file's deviation 27); its
row's deficit is then reported with that status, not as a number.

The payload form's flag `structure_payload_unconverged` (`results_io._structure_payload_case`:
the contraction c = |P_2* - P_1*| / |P_1* - P_ref| above 0.1, or the residual estimate c
|P_2* - P_1*| above 0.5 x final_payload_xtol_kg = 0.025 kg; promoted to the run's flags) is
expected to fire on three of the four payload cases, the three whose P_2* - P_ref supplies
a no-offload row's payload deficit: phys_hi c 0.0099, residual estimate 0.24 kg [0.13];
outer_hi c 0.064, 43.5 kg [4.1]; step c 0.017, 0.37 kg [0.23]; not on the central (c
0.0025, 0.0020 kg [0.0019]). |P_2* - P_1*| comes from the sizing's own dependence on the
payload (dm_1 - dm_0 = -132.5, -1,978.4 and -78.0 kg), which is itself driven by P_1* -
P_ref, so the residual estimate scales about as the payload rate squared; the expectation is
robust to the rate all the same: on the quadratic the three residual estimates are 0.13, 4.1
and 0.23 kg, still at least 5 times the 0.025 kg tolerance, and the central's 0.0019 kg stays
about 13 times below it (0.0020 kg, 12 times, on the linear rate). Section 8 fixes how a
flagged deficit is quoted.

**The stage-1 pad control** (pad__offload_stage1, both files): expected no_offload at x = 0
with consistency pass, as SP1 recorded it at the same P_ref (results/silo_offload_2d/
20261003T112934Z: m_res(0) -0.0016 kg, dv_shortfall 0.00019 m/s, inside its resolution
bound; file C's results/silo_offload_2d_readme/20261003T112956Z: m_res(0) -0.0016 kg,
pass). The pad, P_ref and the solver are unchanged, so the same m_res is expected; a
difference of grams from a warm start is reported beside, and only a failed consistency
test blocks (section 9).

**File C** (the fork's pad flown afresh: P* equals SP1's bridge P_ref to 0.0 kg; M/R 1.700):
silo_cold_s1_st dm 5,990.5 + 0 kg at x* (5,616.1 kg at the bridge's 36,006.4 kg), expected
x* 7,475 kg (20.8% of the fork's 36.0 t; 18.1% of 41.26 t; naive 9,383 kg; level-matched
6,710 kg), reading "cancels most" on the fork. The fork has no penalty curve of its own:
its estimate uses the gate's slope (shifted to 36,006.4 kg), whose error on the fork's
masses is not measured. Sizing-only band estimates at the fork's headline (not flown):
no offload / 19,510 / 23,621 kg. The structure's offload cost (section 8, C1): about 28,531
kg on the fork (36,006.4 - 7,475.1) against 30,157.7 kg on the gate (41,262.9 - 11,105.2),
5.4% apart (dm at x* 5,990.5 against 6,309.6 kg, 5.1%); on the level-matched reading
29,297 kg (2.9% apart). The share left (C2): 20.8% against 26.9%, 22.9% apart. X/m_p1
(printed, not read): 1.89% on the fork's 395.7 t against 2.70% on the gate's 410.9 t.

Under the shift method the fork's case sits on the gate's curve, so the expected cost
difference is set by the two dm values alone and carries no information about the C
readings; the run decides them through the fork's own slope, which nothing here measures.
If the fork loses k times the gate's offload per kg of dry mass, its cost is about k x
28,531 kg: C1 fires "depends" for k below 0.951 (a fork slope 4.9% shallower than the
gate's), and C2 reads "nearly the same" for k between 0.888 and 0.956 (a slope 4.4-11.2%
shallower). Scaling the slope with the forks' P* ratio (k = 24,700.0 / 26,054.4 = 0.948, as
the threshold's premise that the cost scales with the masses would have it) puts the cost
10.3% apart and the share 7.6% apart: each test then fires the other way. Neither C
sentence is decided by the estimates.

## 8. How each result will be read

**The freeze fixed by the design** (D-SP7-31, design 3.2, verbatim): "Freeze: S3-S5 tests
use a synthetic structure file and short or 1-D vehicles, never a pre-registered case; the
structure files are frozen at S2's commit, a later change is a logged decision (before
S6a) or an amendment (after)". Applied: no change to either structure file was made or
decided before this note (section 6, item 9); from this note's commit a change to either is
an amendment (its own commit, logged as a decision, this note extended, never rewritten),
as is a change to either experiment file. Section 12 records both files' sha256; a mismatch
at S7a's commit blocks every structural number (section 9).

**The rules fixed by the design** (D-SP7-32, design 4.10, verbatim):

- "survives" if the physics band's adverse end keeps more than 50% of 41,262.9 kg;
- "cancels most" if the central x* is below 50% of it;
- "undecided" if the physics band straddles 50% or either physics end is no_offload;
- "cancels all" if the central case is no_offload;
- the same tests on the bound rows, each with its own fixed sentence; every sentence that
  fires goes into the note's headline; a no_offload end is reported with its delta-v
  shortfall and its payload deficit.

**How they are applied (fixed now).** 50% of 41,262.9 kg is 20,631.45 kg. The physics
band's ends are silo_cold_s1_st_phys_hi (the adverse end) and silo_cold_s1_st_phys_lo_scaled
(the low-mass end as D-SP7-33 widens it); the rules are evaluated again with the unscaled
silo_cold_s1_st_phys_lo, and the two evaluations are compared sentence by sentence as filled
text: whenever a sentence differs between them (a different rule fires, or the same rule
with a different <a> or <b>), both go into the headline, each naming the end it used ("the
plausibility-scaled low-mass end" or "the unscaled low-mass end"). Only H1 and H3 read a
physics end: H1 reads the adverse end alone (its factor is 1), so it cannot differ; H3 reads
both, so under the estimates (H3 in both, <b> about 28.5 t scaled and 23.7 t unscaled) both
H3 sentences are quoted. O1 reads the outer envelope's two cases, which no plausibility factor
touches, so it has one evaluation. "cancels most" needs a central case that
ends ok below 20,631.45 kg; a central no_offload fires "cancels all" instead. A no_offload
end counts as below 50% for the straddle test. A case that ends search_failed or
reference_failed fires nothing and is reported as such. The fixed sentences ("X t" is the
case's x* in tonnes to two decimals, "Y%" its share of SP1's uncharged 41,262.9 kg to 0.1%,
never a share of the stage-1 load; every no-offload phrase followed by "(s m/s of delta-v
short of P_ref at x = 0; payload deficit d kg)", d being P_2* - P_ref of the payload case at
the same settings, or, only for a sweep point or a case section 7 expects to offload
(section 6, item 5), by "(s m/s of delta-v short of P_ref at x = 0; payload deficit not
flown: no payload case at these settings)"). When that payload case's
`structure_payload_unconverged` flag fired (expected for phys_hi, outer_hi and step,
section 7), d is still its two-pass P_2* - P_ref, quoted with the residual estimate r
beside it: "payload deficit d kg (two passes; residual estimate r kg)", here and in the
headline sentence; the flag does not block (its residual, 0.2-44 kg expected, against
deficits of 1.0-10 t changes no reading):

- H1 survives: "At the physics band's adverse end the modelled structure still leaves X t
  (Y% of SP1's uncharged 41.26 t): the offload survives a first-order structure over the
  band's physics coefficients."
- H2 cancels most: "At the central coefficients the modelled structure cancels most of
  SP1's uncharged offload: X t is left (Y%)."
- H3 undecided: "The physics band runs from <a> to <b>, so the physics coefficients alone do
  not decide whether more than half of the offload survives." (<a>, <b>: "X t" or "no
  offload ...".)
- H4 cancels all: "At the central coefficients the modelled structure cancels the whole
  offload: no offload at P_ref ..."
- O1 (the outer envelope, the same tests on outer_hi and outer_lo): "survives (outer)": "At
  the outer envelope's adverse end X t is left (Y%)."; "undecided (outer)": "The outer
  envelope runs from <c> to <d>, so the design assumptions together with the physics do
  not decide it."
- R (each single row: _qs, _step, _full, _ts, _m10, _m25, _cap45, _cap40, the two hot
  starts): "keeps more than half" if x* > 20,631.45 kg: "<row> (<what it changes>) keeps
  more than half of SP1's uncharged offload: X t (Y%)."; "cancels most" if ok and below:
  "<row> (<what it changes>) cancels most of it: X t is left (Y%)."; "cancels all" if
  no_offload: "<row> (<what it changes>) cancels all of it: no offload at P_ref ...". Each
  row's share of its own uncharged x* is printed beside. silo_cold_200m_s1_st has no R
  sentence: it is read under S2 (sweep 2's 200 m point flies the same run; section 6,
  item 4), and the note prints its x* with its 260 m facility and its 2.5 g0 felt load.
- HS (the hot starts against the cold headline, at the same P_ref): "<hot start> keeps
  <more | less> offload than the cold start with the same structure: X_hot - X_st t
  (uncharged U_hot - U_cold t; the structure's offload cost U - X D_hot t against the cold
  start's D_cold t)." Each difference is read with SP1's rule as section 3 restates it for
  structural solves (different flights at the same P_ref: R about 3.4 kg for X, 2.55 kg for
  U, and their sum, about 6 kg, for D); within R, "the same within the resolution". Quoted with SP1's caveat in the
  same sentence: "(nothing models the exhaust in the shaft: back-pressure, heating, the
  carriage in the plume, which favours the hot starts)".
- S1 (sweep 1): "With the central structure, the lowest exit speed of sweep 1 that still
  offloads is v m/s (L m); below it, at <the lower speeds>, the structure cancels the
  offload." If every point offloads: "every exit speed swept offloads, the lowest (38.35 m/s)
  X t." If x* does not rise with the exit speed across the points that offload, "x* does not
  rise monotonically with the exit speed" is added. Each point's x* is quoted with its own
  uncharged x* beside.
- S2 (sweep 2): "At the fixed exit speed 76.71 m/s the structural offload is <x50>, <x100>,
  <x200> and <x300> at 50, 100, 200 and 300 m (felt about 7.0, 4.0, 2.5 and 2.0 g0)."; plus
  "it rises with the stroke" or "it does not rise monotonically with the stroke"; a
  no_offload point names stage 2 if the push sized it.
- A (arms): "Under CLAUDE.md's +/-10% arms the structural headline ranges from a to b t." An
  arm that ends no_offload, reference_failed or with a failing decomposition is named.
- P (payload cases): "Sized for its own full-load push, silo_cold carries P t to orbit, D kg
  <above | below> the pad's P_ref (central; physics high-mass end P' t, D' kg)." The outer
  high-mass and step payload cases are quoted in their rows' no-offload phrases (as d), not
  in P.
- C (file C, read against the fork's own uncharged x* U, never SP1's 41.26 t; U the run's
  file C silo_cold_s1, expected 36,006.4 kg, 50% of it the threshold): R's three tests on
  file C's silo_cold_s1_st, each with its own fixed sentence, "X t" its x* and "Y_C%" its
  share of U to 0.1%: "keeps more than half" if X > 0.5 U: "On the README-loads fork the
  central structure keeps more than half of the fork's uncharged offload: X t (Y_C% of its
  U t)."; "cancels most" if ok and X <= 0.5 U: "On the README-loads fork the central
  structure cancels most of the fork's uncharged offload: X t is left (Y_C% of its U t).";
  "cancels all" if no_offload: "On the README-loads fork the central structure cancels all
  of the fork's uncharged offload: no offload at P_ref ...", followed by the no-offload
  phrase above ("payload deficit not flown": file C has no payload case). Its share of
  SP1's 41.26 t is printed beside and not read. Then
  "On the README-loads fork the central structure leaves X t of its uncharged U t (F%;
  the gate's F_gate%): the structure costs U - X t of offload against the gate's U_gate -
  X_gate t.", followed by two registered tests, each with its own fixed sentence, both
  quoted beside the headline whichever way each fires (section 6, item 10; the 10% is
  SP1's bridge threshold, about twice the forks' 5.5% P* difference):
  - C1, the cost: if |(U - X) - (U_gate - X_gate)| <= 0.10 (U_gate - X_gate): "the
    structure's offload cost is nearly the same on both forks"; otherwise: "the
    structure's offload cost depends on the vehicle masses more than the calibration
    difference suggests";
  - C2, the share left: if |F - F_gate| <= 0.10 F_gate: "the share of the uncharged offload
    the structure leaves is nearly the same on both forks"; otherwise: "the share of the
    uncharged offload the structure leaves depends on the vehicle masses more than the
    calibration difference suggests".
  dm at x* on both forks and X/m_p1 (SP1's bridge quantity) are printed beside; neither is
  read. If either fork's central case ends no_offload, its X is 0 and its cost its whole
  U, and both tests are still evaluated.

**The headline sentence, fixed form** (design 4.11, with three changes and one renaming, no others:
D-SP7-39's comparison, with its numbers, in the release clause; D-SP7-32's no-offload
wording; and D-SP7-41's two ends side by side "with the trigger stated": the scaled end b
with the rule's factor and trigger, the unscaled end b' beside it; the renaming: design
4.11's "Y% of stage 1" is written S%, since section 8's Y% is the share of SP1's 41.26 t,
a different quantity): "With a first-order
structure sized for the offloaded stack only (central coefficients; an assumed real-drive
rise time of 0.5 s that the constant_accel trajectory does not fly, its plateau cost charged;
an instant release that the model's single-mode treatment says would separate the stage-1
LOX column (its bottom at p1 kPa absolute at the release, where the same tank, empty at
the pad's MECO, stays at p1m kPa gauge), as the same treatment also separates stage 2's full
LOX column at the pad's own MECO (p2m kPa gauge, against p2 kPa gauge at the push); the
model's unthrottled envelope; zero margin), the 3 g0, 100 m cold-start silo leaves out X t
of stage-1 propellant (S% of stage 1) against SP1's 41.26 t uncharged; the physics band gives a to b
t (b after the plausibility rule's factor phi, which fires at M_model / R = r and
multiplies the case's whole dm, the load entry included; s% of M_model is the envelope of
the <element>, an element the push barely loads, sized by <mode> at <case> and carrying
nof_barrel, a double count of buckling material the source note flags; b' t unscaled), the
outer envelope c to d t; sized for a full load e t; through the thrust structure f t; with
a step push g t." followed by every reading sentence that fired. phi is the scaled case's
`structure_plausibility_factor` to three decimals and r its `structure_plausibility_ratio`
to three significant digits (expected 0.739 and 1.76); <element>, s (to whole %), <mode> and
<case> come from `structure_inputs.plausibility.dominant` (`element`, `share`, `mode` and
`case_label`; expected "stage1.lox_barrel", 71%, "monocoque" and "pad GRAVITY_TURN
t=151.3284 s"), written in words, not as the record's raw values:
- <element>: the stage as "stage-1" or "stage-2" and the element as this note names it
  (lox_barrel "LOX barrel", rp1_barrel "RP-1 barrel", forward_dome "forward dome",
  common_dome "common dome", rp1_aft_dome "RP-1 aft dome"); expected "stage-1 LOX barrel";
- <mode>: monocoque "axial buckling"; a stiffened row (a Gerard row or plate_limited,
  `structure.STIFFENED_MODES`) "stiffened-panel axial buckling"; hoop "hoop stress";
  combined "combined stress"; membrane "membrane stress"; min_gauge "the minimum gauge",
  with " at <case>" left out (the record's case_label is then null); expected "axial
  buckling";
- <case>: "the pad's MECO" when the label's time is the envelope pad's stage-1 burnout (its
  `propellant` event, 151.3284 s on SP1's pad, results/silo_offload_2d/20261003T112934Z/pad/
  events.csv) to the label's four decimals; otherwise "load case <label>", the label as the
  record has it; expected "the pad's MECO";
- "and carrying nof_barrel, a double count of buckling material the source note flags"
  stands only while <mode> is monocoque (the double count the source note states in its
  section 4: every LOX station takes nof_barrel, and a monocoque increment sized by
  SP-8007's buckling already holds its buckling material; only LOX stations are
  monocoque-sized); otherwise it reads "and carrying f", f the factor the plausibility check
  gives that mode (nof_barrel, nof_stiffened or nof_dome, `structure.plausibility`);
- "an element the push barely loads" stands only while that element's own push increment
  in the central case at x* is below 1% of the central's dm (expected 25.6 of 6,309.6 kg,
  0.4%), and otherwise reads "an element the push loads with q kg" (q that increment, to
  whole kg).

Expected, so: "...; 71% of M_model is the envelope of the stage-1 LOX barrel, an element the
push barely loads, sized by axial buckling at the pad's MECO and carrying nof_barrel, a
double count of buckling material the source note flags; ...".
S% is x* over the stage-1 propellant load (410.9 t; 2.70% expected), to 0.01 percentage
points, the summary's "% of stage 1", not section 8's Y%. p1, p1m, p2m and p2 are the
central case's release-flag record at x* (`lox_bottom_pressure_min_abs_pa`,
`meco_lox_bottom_pressure_min_gauge_pa`, `meco_stage2_lox_bottom_pressure_min_gauge_pa`
and `stage2_lox_bottom_pressure_min_gauge_pa`; MECO's ambient taken as 0, so its gauge
value is also absolute), to whole kPa: expected about -897, +132, -232 and -162 (section
2(c)). If the central case's flag does not fire, the clause reads "an instant release the
model's single-mode treatment does not flag"; if the pad's MECO does not separate stage
2's column (p2m >= 0), "as the same treatment also separates" becomes "while the same
treatment keeps stage 2's full LOX column at the pad's own MECO". Each of a to g that is a
no_offload is written "no offload (s m/s short, payload deficit d kg)", never "0 t" ("not
flown" only under the rule above; "(two passes; residual estimate r kg)" after d when its
payload case's flag fired); b is the plausibility-scaled low-mass end and b' the unscaled
one.

**The sentences expected to fire under the estimates of section 7**: H2 (cancels most:
about 11.1 t, 26.9%) and H3 twice (undecided: no offload to about 28.5 t with the
plausibility-scaled low-mass end, and no offload to about 23.7 t with the unscaled one,
both quoted, each naming its end); not H1 and not H4. O1 undecided (no offload to about
31.1 t). R: _qs, _full, _ts, _m10, _m25, _cap45, _cap40 (about 4.8 t) and both hot starts
cancel most; _step cancels all. silo_cold_200m_s1_st (about 26.6 t) is read under S2. HS: both hot
starts keep more than the cold start (silo_hot_full by about 4.2 t on an uncharged offload
about 1.8 t lower, its structural cost about 24.2 against 30.2 t; silo_hot_ramp by about 5.1
t, 4.75 t of it from its larger uncharged offload, its cost about 29.8 against 30.2 t), with
the exhaust caveat, which favours them. S1: the lowest exit speed that offloads is 76.71
m/s (100 m); no offload at 38.35 and 54.24 m/s; x* rises with the exit speed above it. S2:
no offload at 50 m (stage 2 sized), then about 11.1, 26.6 and 32.0 t, rising with the
stroke. A: about 8.1 to 14.8 t. P: about +306 kg (central) and -2,449 kg (high-mass end);
the no-offload rows' deficits about -2,449 kg (phys_hi), of order -7 to -10 t (outer_hi)
and about -1,231 kg (step), each with its residual estimate beside (the payload flag
expected on all three). C: "On the README-loads fork the central structure cancels most of
the fork's uncharged offload" (about 7.5 t, 20.8% of the fork's 36.0 t, against the gate's
26.9%); the structure's offload cost about 28.5 t on the fork against
30.2 t on the gate. The two C tests are not decided by the estimates (section 7): under
them C1 fires "the structure's offload cost is nearly the same on both forks" (5.4% apart)
and C2 "the share of the uncharged offload the structure leaves depends on the vehicle
masses more than the calibration difference suggests" (22.9% apart), but the C1 value is
set by the two dm values alone (5,990 against 6,310 kg, 5.1% apart), and a fork slope
scaled by the forks' P* ratio would swap both (10.3% and 7.6% apart).

**The flags expected beside the numbers** (section 2(c); reported beside, never a gate,
section 9; sizing only at each case's expected x): the release flag on every structural case
of both files and every sweep point; the payload-limit flag on every cold-start structural
case, every sweep point, file C's central and all four payload cases (on the swing, -2.1 to
-7.8 g0 against -2.0 g0; on n_peak above +6.0 g0 too for _step, _outer_hi and sweep 2's 50 m
point), not on the two hot starts (swing about -1.6 g0), quoted with its MECO comparison
(the same instant step swings the pad's MECO to -5.195 g0); the upper-stack flag on _step,
_outer_hi, _cap40 and sweep 2's 50 m point (and the _step and _outer_hi payload cases), on
no other case. A flag state that differs from these is reported as departing from its
estimate.

**How far each expected reading sits from its threshold** (under the estimates; the
placement's error was measured once, on the synthetic timing case, at 0.3 t, a use put to
S6a's gate, section 2(d)). Within reach:
- sweep 1's 50 m point: no offload, so S1's "lowest exit speed that offloads is 76.71 m/s"
  rests on it. On the penalty curve it misses by about 2.4 t of offload (x0 + X(dm(0)) -
  41,262.9 = -2,406 kg); on the payload rate the same row's deficit (P* about 210 kg below
  P_ref, 24 m/s) corresponds to about 5-7 t of offload (m_res about -206 kg at SP1's 0.031
  (near x = 0) to 0.039 (near silo_cold's x*) kg of m_res per kg of offload). The two
  models' margins differ 2 to 3
  times because each is a small difference of two large numbers (the point's uncharged
  payload gain, 987.5 kg, against the structure's cost on the payload rate, about 1,160 to
  1,200 kg); the sign (no offload) holds on the curve, the level-matched reading and the
  payload rate alike, while the margin's size depends on the model (2.4 t on the curve, 5-7
  t on the payload rate); the shift
  for its x0 below 41.26 t favours the assist;
- C1 and C2: the margins of section 7 (a fork slope 4.9% or 4.4% shallower flips them);
- P's central sign: +306 kg above P_ref on the linear rate, extrapolated about 3 times
  beyond its measured range; a rate 26% steeper would put it below, while the curve's
  convexity biases the estimate the other way.

The rest sit at least about 4 t of offload (or about 0.9 t of equivalent dm) from their
thresholds: H2 at 11.1 against 20.6 t; H3 and O1 through ends at no offload by 13.1 and 57.5
t of equivalent dm beyond the 8.5 t zero crossing (H1 would need phys_hi above 20.6 t);
R's nearest to half, silo_hot_ramp (16.2 t), m25 (15.4 t) and silo_hot_full (15.3 t, its x0
an estimate), 4.4-5.4 t below; R's nearest to no offload, _cap40 (4.8 t; 0.94 t of
equivalent dm from the crossing) and _ts (5.8 t; 1.13 t); _step no offload by 6.4 t of
equivalent dm; HS by 4.2 and 5.1 t; S1 above 50 m rising by 16.8 and 11.2 t; S2's 50 m no
offload by 9.8 t of equivalent dm, then rising by 15.5 and 5.4 t; A's lowest arm 8.1 t.

**Registered for the findings note's caveats**: beside the central, the note names the four
coefficients whose central sits at the dm-lowering end of its range or is the dm-lowering
alternative (section 2(b)): eta_weld 1.00, F_tu 558.5 MPa, the Gerard row ring_common_z and
ring_pads 8; and every in-range single move that alone gives no offload at the headline
push (S2's tornado and search D; break-even values from S2's first-pass sizing): eta_weld
0.70 (dm +1,828.2 kg), the plate-limited Gerard row (+4,851.6 kg), 4 carriage pads, and the
rise time at or below 0.1438 s (the range's 0.1 s end: dm 10,235.6 kg in S2's search D; the
rise time is a user decision, D-SP7-09, and with the axial period the axis survey 08 put
first by leverage, its section 10, item 3). Beside the
thrust-structure row (Q5, at the headline's prominence) the note names its own break-even:
k_ts at or above 0.3476 kg/kN, 24% above its central 0.2805 and inside its range
0.197-0.628, gives no offload on that row. Under this step's converged sizing both
break-evens already give no offload at their values (equivalent dm1 + 5.478 dm2 at x = 0:
8,543.1 kg (8,416.7 + 23.1, stage 2 sized there) at 0.1438 s and 8,617.1 kg (stage 1
alone) at 0.3476 kg/kN, against the 8,488.6 kg crossing in equivalent dm), so the converged
break-evens lie slightly inside S2's. F_tu's other end (520 MPa) moves dm by +136.0 kg.

**Registered for the findings note's headline table** (design 4.11, "the headline table
with SP1's penalty rows"): SP1's uncharged row and its three assumed penalty rows (+2.0,
+4.0 and +8.1 t: 32,285.2, 22,876.0 and 1,980.5 kg, 78.2%, 55.4% and 4.8% of 41.26 t, as
reproduced by run A) stand beside every modelled row of the headline push, labelled
"assumed penalty, not sized structure", with each modelled row's dm1 + dm2 at its x* beside
its x*, so that a reader sees in one place where the modelled masses fall against SP1's
assumed ones (expected: the central's 6.3 t between the +4 t and +8.1 t rows; the step row,
the physics high-mass end and the outer high-mass end beyond the +8.1 t row).

**What would undercut the hypothesis that every m/s of assist helps**, stated now: the
structural headline below half of 41.26 t (expected); any no-offload row (expected for the
step, the adverse ends and the short strokes); the lowest exit speed that still offloads
lying above the screening speeds of 38-54 m/s (expected); the payload-limit flag at the
central headline (expected: the release swing -4.389 g0 against the payload's published
-2.0 g0), with its MECO caveat beside it: the same single-mode instant step swings the pad's
own MECO to -5.195 g0, also beyond the limit, so the flag measures the model's step
treatment as much as the push, and a real drive's release and a real MECO are not instant
steps. What would favour it: the
physics band's adverse end keeping more than half (not expected), or a solved headline far
above the estimate (the placement's bias, measured once, on the synthetic timing case: 0.3
t low; a use put to S6a's gate, section 2(d)).

## 9. Checks that block a citation

A number is not cited in the findings until each check below that touches it passes or is
explained in the note:

- any run or comparison that is bug_suspect (the per-run closure, loss identity and
  insertion checks, the blocking screening checks, a cross-vehicle decomposition whose
  residual exceeds `checks.closure_tol_mps`, 1e-5 m/s);
- a reference_failed pad, or a pad whose P* differs from P_ref (section 3) by more than
  0.002 kg (the envelope is that pad's flight);
- a stage-1 pad control that fails its consistency test;
- a reproduction outside 0.002 kg: silo_cold_s1 (41,262.90803733282 kg), the three penalty
  rows (32,285.203295407457, 22,875.96053288855 and 1,980.4767886165673 kg),
  silo_hot_ramp_s1 (46,013.43730748323 kg), silo_cold_200m_s1 (41,262.97057414868 kg),
  file C's silo_cold_s1 (36,006.44430169878 kg), and each uncharged sweep point against
  SP1's sweep index (sweep 1: 18,765.1262419, 28,653.558053, 41,262.9080373, 56,827.1590629,
  67,285.8026498 kg; sweep 2: 41,262.9734368, 41,262.971734, 41,262.9705741, 41,262.9072618
  kg; 12 significant digits): it blocks every number of that command until explained;
- a structural case's verification off P_ref by more than 1e-4 P_ref (2.605 kg;
  `offload_verify_mismatch`): the case is flagged and reported as a bound; for
  silo_cold_s1_st it blocks the headline until explained;
- a structural case whose `xv_dry_mass_delta_kg` differs from dm1 + dm2 at x* by more than
  1e-6 kg (a bug);
- a frozen set that does not recompute: tests/test_structure_search.py::
  test_frozen_sets_reproduce, both files, at the run's commit (it blocks every band and
  outer-envelope number);
- a structure file whose sha256 at the run's commit, or as recorded in a run's
  `structure_file` record, differs from section 12's (D-SP7-31): it blocks every
  structural number of that file;
- the convergence check of section 1 failing (the tightened x* off the shipped one by 0.1%
  or more, or dm moved by 0.1 kg or more with the stations doubled): it blocks the
  headline until explained;
- an unexplained `offload_nonmonotone`, a capped gamma* refine on the headline, or a fired
  `structure_fixed_point_cap` (explained before the number is quoted);
- a no_offload structural case reported without its delta-v shortfall, or without the
  payload deficit of its payload case where one is registered (section 6, item 5): a
  reporting defect to fix first.

Not blocking: a payload case's `structure_payload_unconverged` flag (expected on phys_hi,
outer_hi and step, section 7). The passes are not iterated further (design 4.4), so its
deficit d is quoted as the two-pass P_2* - P_ref with its residual estimate beside it
(section 8).

Every case must end ok, or no_offload with its shortfall and deficit, or be flagged; a
no_offload case without a registered payload case (a sweep point, or a case section 7
expected to offload, which the note then names as departing from its estimate) is reported
with its shortfall and "payload deficit not flown".
Reported beside every number, never a gate: max-Q against the pad's, peak felt g and
interface force, the release, upper-stack and payload-limit flags with their numbers (the
states expected in section 8; the payload-limit flag with its MECO comparison), the
post-hoc flight check's exceedance, facility length with braking, the push's electricity and
peak power.

## 10. What nothing here measures

With the direction each would move the structural offload, where known:

- propellant settling for the ignition 0.5 s after the release, after the release step the
  model flags as separating the LOX column (not modelled; a risk against the assist);
- the LOX transfer tube beyond its hoop, COPVs, engine mounts loaded in reverse by the push,
  feedlines (not charged; against the assist);
- joints and weld lands beyond what the non-optimum factors carry (against);
- lateral and bending loads in the shaft (against);
- q-alpha bending in flight: in the pad's envelope it would raise the envelope and lower dm
  (for the assist; leaving it out is conservative); on the offloaded flight, whose max-Q is
  higher than the pad's, it would add load the envelope may not cover (against the
  assist);
- drag in the pad's envelope (D-SP7-15 leaves it out): modelled, it would raise the
  envelope's compression and lower dm (for the assist; the probe put drag in the envelope
  at under 60 kg, section 2(a));
- the pad release's own dynamic step (the envelope is quasi-static, D-SP7-15): a dynamic
  factor on the pad's hold-down release would raise the envelope and lower dm (for the
  assist; size not measured);
- the pad's envelope flown unthrottled (MECO at 5.195 g0; Falcon 9's MECO acceleration is
  not public, and its guide says the engines may be throttled to hold acceleration limits):
  a throttled MECO would lower the envelope and raise dm, so the unthrottled envelope
  favours the assist; the 4.5 and 4.0 g0 cap rows measure part of it (about 0.9 and 6.3 t
  of offload under the estimates);
- fatigue on a reused stage (against);
- the payload adapter and the payload (flagged against the published +6.0/-2.0 g limits,
  not sized; against; the flag is expected on every cold start and sweep point, and not on
  the hot starts, section 2(c));
- a strengthened vehicle's own pad flights carrying dm (outside this comparison; against a
  mixed fleet);
- a clean-sheet vehicle designed for the push (RQ7; for the assist, size not known);
- a damped structural response (damping lowers the single-mode peak the factor charges;
  for the assist);
- a multi-mode response (the single-mode factor is not conservative at the upper stations
  for short rise times; against the assist);
- the release step, reported as a flag and not sized (D-SP7-10, D-SP7-19): sizing it as one
  more push load case could only add mass or leave dm unchanged (each station's increment
  is the positive part of the push's requirement over the envelope's, D-SP7-14), so leaving
  it out favours the assist; the flag fires at the central case (section 2(c));
- from SP1: no throttle (no max-Q-constrained offload), tanks partly filled with the mixture
  ratio kept and no ullage, residuals or centre-of-gravity effects, a massless carriage and
  a vented shaft, nothing modelling the exhaust in the shaft (back-pressure, heating, the
  carriage in the plume; it favours the hot starts, and the HS sentence is quoted with it),
  the planar model and the calibration miss.

## 11. Runtime estimate

**Measured at this checkpoint** (2026-10-16 UTC, the development machine, 32 logical
processors, other agents possibly running). The timing case is a scratch copy of file A
outside experiments/ (scratchpad s6a/timing_synthetic.yaml) holding the pad and silo_cold,
one central structural stage-1 case and its verification, no pad control, with
`structure.file` tests/data/structure_synthetic.yaml, run with `launchsim run ...
--results-root <scratch>/s6a/timing --no-plots`: 185.2 s wall (06:50:18Z to 06:53:23Z;
directory s6a_timing_synthetic/20261016T065020Z; the solve took 39 evaluations, the fixed
point 6 sizings, x* 15,195.4 kg, a synthetic-file number). The same file with
`--no-offload` (pad and silo_cold only; directory 20261016T064838Z) took 92.6 s, so the
structural case with its verification, the structure inputs, the flight check and the
writes took about 92.6 s, twice one searched run (46.3 s). The pad flights of this step's
estimates took 39-52 s each, so the machine ran about 1.8-2.3 times slower than in SP1's
production runs (set M of survey 09: a searched run S 20-26 s, a verified solve V 34-46 s, a
solve without verification O 25-30 s, a pad control C1 about 15 s).

**Costs used**: a structural verified solve V_s = 2.0 S (the timing ratio), so 40-52 s at set
M (about 1.15 V); a structural arm solve O_s = 1.15 O; at this checkpoint's rate S 46 s, V_s
93 s, V 81 s, O_s 65 s, C1 30 s; at SP1's pessimistic set P (S 25-55, V 90-110, O 65-100, C1
30 s) V_s 104-127 s and O_s 75-115 s. Run directories with plots 1.3-2.5 s each.

| Command | Contents | Set M | This checkpoint's rate | Set P |
|---|---|---|---|---|
| run A | 5 S (pad, 4 variants), C1, 7 V (4 uncharged, 3 penalty), 17 V_s (3 expected no_offload), 4 payload cases (8 S), 6 arm pads (S) and 6 O_s (2 arms reused), about 34 directories | 26-34 min | about 59 min | 56-80 min |
| sweep A | own pad (S), 9 points of S + V + V_s (3 structural points expected no_offload) | 15-20 min | about 34 min | 34-45 min |
| run C | 2 S, C1, V, V_s, about 4 directories | 2-3 min | about 5 min | 5-6 min |

The three run in parallel, so the wall time is run A's: about 26-34 min at SP1's production
rates, about an hour under the load measured here, at most about 80 min at the pessimistic
rates: below D-SP1-17's 90-minute threshold, so nothing is trimmed. The two payload cases
added at the first review (section 6, item 5) cost 4 S, about 2-4 min of it, and the 4.0 g0
cap row added at the second (section 6, item 11) one V_s, about 1-2 min. The design's 10
min for sweep A counted one solve per point; each point solves two. A quiet machine (no
suite, no app-driving agent) is part of the registered procedure. The convergence check of
section 1 runs afterwards, not in parallel: two pad searches and two structural solves with
their verification, about 6 min at SP1's rates and 5-10 min allowing for a slower machine
(SP1's tightened chain took 75 s for the pad and 172 s for the uncharged solve with its
verification; a tightened structural solve about 1.15 times that, V_s = 2.0 S = 1.15 V from
this checkpoint's timing case: 75 + 198 s, plus the shipped pad S and V_s, 333-351 s).

## 12. Provenance

- The structure files are frozen at SP7 step S2's commit 45e39d4 (D-SP7-31; `git diff
  --quiet 45e39d4 -- configs/structures` holds at this commit):
  - configs/structures/generic_f9_class_2d.yaml sha256
    a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232
  - configs/structures/generic_f9_class_2d_readme_loads.yaml sha256
    a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997
  tests/test_config_planar.py pins both digests. Under D-SP7-31 (section 8) a change to
  either file after this commit is an amendment, and a digest that differs at S7a's commit
  blocks every structural number (section 9). Nothing was added to them at this step
  (section 6, item 9: the decisions the phase file's deviations 23 and 25 left to S6a; to
  be logged with the phase file's deviations). Their frozen sets were written from the
  tree at 4494fe1 and are reproduced by tests/test_structure_search.py::
  test_frozen_sets_reproduce; this step re-ran it on its own tree (the code of f10cf58):
  both files pass (301.7 s and 359.5 s, 2026-10-16), the recomputation exit criterion 5
  asks for at S6a's commit. The test compares the polish records and the extremality
  checks too (floats to 1e-9), so the recorded excesses recompute; criterion 5's largest
  excess, as recorded and recomputed: the one-coordinate check's 11.8 kg at the gate's
  physics low-mass end (the fork's largest 7.7 kg, at its outer high-mass end), 43.6 kg
  [42.0] on the charged dm1 + 5.478 dm2 (outer high-mass), and the held check at the step
  row's 223.2 kg [149.1] (280.1 [181.0] charged), all listed with their directions in
  section 2(c). S7a's gate re-runs it at the run's commit (section 9).
- configs/vehicles/ and the seven shipped experiment files are unchanged since SP7's start
  commit 22c62e9.
- This note's own commit, with the two experiment files, the test changes and
  docs/physics.md's shipped-experiments table and test-map rows for them, is the
  pre-registration commit. The physics.md rows lie beside the step's listed files (design
  5's S6a row names experiments/, docs/phases/inputs/ and tests/test_config_planar.py),
  kept because the standing gate asks that physics.md hold the step's test-map rows. S6a's
  gate (2026-10-16) accepted that out-of-list file and kept the timing case's use beyond
  step S6a's item 4 (section 2(d)); both are logged as deviations in the phase file's
  section 12 at S6a's tracker commit, with the case additions beyond design 4.10's lists
  (section 6: the plausibility-scaled twin, silo_cold_200m's pair, the two added payload
  cases, the 4.0 g0 cap row and the uncharged case at every sweep point; not
  silo_hot_full_s1, which the design's table lists). S7a runs from this commit or
  from a later clean commit that changes no code (src/, configs/, experiments/,
  pyproject.toml, uv.lock).
- The estimates of section 7 were computed sizing only by scratch scripts at HEAD f10cf58's
  code (the working tree of this step changes no code), on pads flown afresh (file A's pad
  four times, twice more at the first review's fixes for the added payload cases, the
  quadratic payload estimates, the release-flag pressures at x*, the element splits and
  the nu and s_dg directions, and once more at the second review's for the 4.0 g0 cap row,
  the RP-1 pressure's minimum-pressure end and dm'(x) at the central, and three times more at
  the third review's for the three flags of every case at its expected x, the step row's band
  sets, the thrust-structure row at k_ts 0.306 and 0.3476, the rise time at 0.1438 and 0.1 s,
  and the plausibility record's dominant element; its six perturbed arm pads; file C's pad,
  once more at the third review's), every P* equal to SP1's recorded value to 0.0 kg; no
  offload of any case of files A or C was solved.

## Appendix A. The source note's section 1.4 table (verbatim)

From docs/phases/inputs/2026-10-08-SP7-sources.md, section 1.4 (commit 81e045d), verbatim:
the paragraph before the table, the table and the one paragraph after it. Section numbers
inside the quoted text are the source note's ("rule 6" is its section 1's rule list); the
question its last sentence sends to the user was answered by D-SP7-36 (the interstage
increment is charged to stage 1).

"End" means the end that lowers dm (or that lowers the row it belongs to); for a discrete
coefficient or a design row it is the alternative that lowers dm. The probe's figures are survey
08's one-at-a-time changes around its own placeholders (monocoque / stiffened 2x / stiffened
3x), context only (rule 6). The table lists every dm-lowering end or alternative that rests on an
assumption, an inference, a rule, a user decision or model output, or on an analogue, and every
end that rests on one of these whose direction is only expected or not monotone. An analogue,
here and in section 12 alike, is an opened value read beyond what it measures: another member's
value, another load case's or another law's, including an extrapolation, a law applied across
vehicles and a reading that needs an assumed parameter. Every dm-lowering end not listed is an
opened value used for what it measures (a material property, a design standard's or Wu's factor,
a Falcon 9 statement), an opened spread, a physical or validity limit, or a bound derived from
opened values, named in its row. Fixed choices (no range) are listed where they rest on an
assumption, an inference or an analogue and either a named alternative would raise dm in some case
or the choice moves dm both ways.

| Field | dm-lowering end | Basis | Reason | Probe's effect |
|---|---|---|---|---|
| `E_GPa` | 79.6 | assumed | 1.3% above the opened compression modulus (78.6 GPa), an allowance | E 80 GPa: -40 / -12 / -10 kg |
| `p_meop_bar` | either end (non-monotone; enumerated) | high end 4.00 assumed; low end 1.24 an analogue (the S-IC LOX tank's pad value, applied to all four tanks) | the high end lies above the highest opened analogue (3.45 bar), an allowance for a pressure-stabilized LOX tank; the low end is a LOX tank's value used for the RP-1 tanks too (the only RP-1 analogue, the S-IC fuel tank's 1.67 bar at altitude, 0.66 bar at sea level, is covered by the pair's lowest p_min, 0.50 bar; section 3.2) | survey 08: the sign changes with the buckling form |
| `p_min_fraction` | either end (non-monotone; enumerated) | high end 0.93 an opened band ratio kept as a value of p_min/MEOP although it bounds that ratio from above (assumed: a tank may regulate close to its MEOP); low end 0.40 an analogue (LOV10's design-study relief choice) | no flown tank's p_min/MEOP is legible except as these upper bounds (S-IVB LOX 0.84, LH2 0.76); section 3.2 | survey 08: non-monotone (the pressures' effect changes sign with the buckling form) |
| Pressure basis (fixed): one differential value for the pad, the push at sea level and flight | the same value in every case | assumed (whether Falcon 9 regulates in absolute or gauge terms is not public; most analogues are psia read at altitude) | if Falcon 9 regulates in absolute terms, the push's relief is overstated (lowers dm) and the hoop pressures too (either way by station); the pressure enumeration spans part of it (section 3.2) | not tested |
| `eta_weld` | 1.00 (also the central) | a rule from Wu's factor practice (WU13, WU24), an analogue | no weld knockdown under a factor that already carries the weld lands; no opened efficiency value is 1.0 | not tested |
| `aft_skirt_length_m` | 2.0 m | assumed | the shortest skirt that encloses the deepest aft dome (1.83 m) with room above it | skirt -0.5 m: -71 / -36 / -39 kg |
| `ullage_fraction` | 0.020 | assumed (widened beyond the opened 0.029-0.040) | expected dm-lowering (shorter barrels), not tested; both ends assumed | under 60 kg (survey 08) |
| `rho_rp1_kg_per_m3` | 829.2 | assumed extrapolation (to -20 C) | expected dm-lowering (a shorter RP-1 barrel and tube), not tested | under 60 kg (survey 08) |
| `ring_h_over_b` | 12.0 | analogue | LOV10's manufacturing limit on orthogrid rings, not a load ring; at 4 to 8 pads bending-only sizing under-sizes the ring there (section 11) | not tested |
| `tube_diameter_m` | 0.40 m | assumed | a fast feed; no feed-velocity source opened | not tested |
| `interstage_length_m` | 3.66 m | derived bound, with the MVac's length below its dome taken as zero (assumed) | the shortest interstage that encloses two hemispherical domes, so that it encloses the domes at every dome ratio the search takes (at the central a/b 4/3 they need 2.745 m; section 2.4); acts only when the upper stack is sized | not tested |
| `t_min_mm` | 1.676 mm | analogue (opened) | WU13's minimum gauge on the SLWT's 2195 bulkheads (flight hardware of another vehicle); Falcon 9's gauge is not public | 3 mm: -50 / -49 / -346 kg |
| `nof_stiffened` | 1.45 | opened factor x opened calibration, analogue (LOV10's 2219 PANDA2 designs) | the non-plate-limited calibration, lower than the 2195 one; whether Falcon 9's barrel is plate-limited is not public (section 4). LOV10 credits PANDA2 with "additional conservatism" as well as the extra constraint, so a PANDA2-only calibration may itself sit high (that raises dm; size not known, section 3.3) | not tested |
| `nof_entry_ratio` | 1.05 | analogue, kept by rule 3 | dome gores, not a skirt or a ring; the row's own comparison puts the push nearest the 1.34-1.47 cases, and 1.05 is kept only because the range equals the sources' spread | not tested |
| `rise_time_s` | 1.0 s | user decision D-SP7-09 | 40% of the push | not tested |
| `axial_frequency_Hz` | 10 Hz | user decision D-SP7-09 | no full-tank anchor near it | not tested |
| `ring_pads` | 8 (the central) | inferred layout choice | the axis stops at the central: above it the model's saving would rest partly on uncharged per-pad hardware (section 4) | not tested |
| `margin` | 0.25 | user decision D-SP7-03 | a row, not a range | not tested |
| `envelope_cap_g` | none (also the central) | the design's envelope (D-SP7-15: the pad's own recorded flight) and model output | the envelope rests on the model's unthrottled MECO (5.195 g0); FUG25 printed p.32 says both stages' engines "may be throttled" to hold acceleration limits, and Falcon 9's MECO acceleration is not public | not tested |
| `skirt_envelope_path` | `flight_thrust` | assumed (the design's alternative, appendix A SP-11, N17) | a thrust path through the skirt, contrary to the inferred octaweb-into-tank path (section 3.5); no source | not tested |
| `dome_alloy` | 2195 | opened analogue (WU13 PDF p.3: the SLWT LO2 aft bulkhead's gores are 2195, with a 2219 cap) and an assumed reading of the guides | the vehicle's skin alloy, if "aluminum domes" includes Al-Li | not tested |
| Alloy of the aft skirt, ring frame and transfer tube (fixed) | 2195 (the materials block) | assumed (their alloys are not public; section 2.3) | the named alternative, a conventional alloy (2219-T851), would raise dm: the tube's increments by about 29%, the ring's mass by about 20%, the Gerard-sized skirt's by about 7% (section 11) | not tested |
| `k_ts_kg_per_kN` | 0.197 | analogue (derived) | Wu's S-II cone law applied across vehicles as well as across the push | not tested |
| `interstage_exponent` (fixed) | 0.6 | assumed | the central Gerard row's exponent; the alternative, the plate-limited row's 1, would raise the interstage increment 1.77 times at the step row (section 5.5) | not tested |
| `fitting_factor` (fixed) | 1.15 | analogue regulation (14 CFR 25.625), with the ring assumed wrought | a cast ring would take 1.25 to 2.0 (14 CFR 25.621); a test-qualified ring could drop the factor (section 3.5) | not tested |
| Ring pad line (fixed) | the pads on the skirt's circle (radial offset e = 0) | assumed (S1's ring model; the facility layout is not public) | an offset adds a uniform bending moment q e r about the pad moment's axis: a small offset of one sign lowers the ring's peak moment (by up to 25%), a larger one of either sign raises it (section 11) | not tested |
| Breakdown placement (fixed): the stage-1 remainder (7,480 kg gate) at the base, the 1,000 kg top share, stage 2's rest at its forward end | as section 5 places them | assumed (no breakdown is public) | non-monotone across cases (section 5.4): where n_peak is above the governing envelope n (the step row, the 50 m stroke) the base placement can lower dm against mass placed at the top; at the headline it raises dm slightly | survey 08: the top mass moves dm by at most about 60 kg |

`drive_efficiency` 0.87 is a favourable end too, but it moves energy and power only, never dm
(section 10). The stage-2 tank order (assumed) has no known direction; it is in section 11. The
stage the interstage increment is charged to (stage 1 proposed, section 5.5) moves the offload
cost of that increment, not dm; it goes to the user (section 13, item 14).
