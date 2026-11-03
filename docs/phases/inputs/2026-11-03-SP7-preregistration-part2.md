# SP7 pre-registration, part 2: the drive experiment (step S6b)

Written 2026-11-03 for SP7 step S6b (docs/phases/SP7-structural-mass-push-load.md, section
7; design docs/phases/inputs/2026-10-08-SP7-design.md, sections 4.6 to 4.11, 5 and 6;
sources docs/phases/inputs/2026-10-08-SP7-sources.md, section 10) and committed with
experiments/silo_drive_2d.yaml (file B) before any run of it. It is part 2 of
docs/phases/inputs/2026-10-15-SP7-preregistration.md ("part 1" below, its sections cited
as "part 1, section n"), written as a separate file: part 1's header gains one paragraph
pointing here, and none of part 1's existing text changes. Step S7b runs file B from a
clean committed tree and completes docs/findings/RQ1-structural-2d.md against this note. A
change to file B after this note's commit is an amendment: its own commit, logged as a
decision, this note kept and extended, never rewritten. The sections follow part 1's (and
so SP1's, docs/phases/inputs/2026-10-03-sp1-preregistration.md).

Every expected value below is an estimate, and none is a target: a different result is
reported as it is. Every structural number is a first-order station sizing (D-SP7-01), not
a detailed structural design.

File B's variants and its rules were fixed by the approved design (section 4.10, approved
2026-10-08) and the sources note's section 10 (commit 81e045d) before run A, so registering
file B after run A's results reopens none of them. The choices this step made inside them,
and the one decision taken after run A that changes a registered value (D-SP7-54, the
sealed bore, for a fairing that could not pass the design's bore), are listed with their
reasons in section 6.

## 1. What is registered

| File | Vehicle | Structure file | What it declares |
|---|---|---|---|
| experiments/silo_drive_2d.yaml (file B) | generic_f9_class_2d.yaml (gate, mass set C; calibrates +14.3% high, accepted 2026-09-30) | configs/structures/generic_f9_class_2d.yaml (frozen at 45e39d4) | pad baseline; variants silo_cold (file A's, verbatim) and the nine linear-motor variants of design 4.10; a structure block with no payload case; an offload block with 20 stage-1 cases (for silo_cold and each linear-motor variant one uncharged and one central structural case), the stage-1 pad control and SP1's energy block; no sweep, no sensitivity block, no arm |

The six shared blocks (dynamics, site, target_orbit, guidance, search, checks), the vehicle
line and the baseline pad with its integrator are copied verbatim from
experiments/silo_offload_2d.yaml; a test pins the shared blocks and the budget id across
every planar experiment (tests/test_config_planar.py). silo_cold is file A's, copied with
its comment, and resolves to the same run and vehicle dicts as in file A and
silo_offload_2d (a test). No label.

The command for step S7b, from the repository root, alone:

    uv run python -m launchsim run experiments/silo_drive_2d.yaml

With plots (the findings need them), from one clean commit: this note's commit or a later
clean commit that changes no code (src/, configs/, experiments/, pyproject.toml, uv.lock).
Before it starts, `git status --porcelain` is empty apart from results/ (protocol section
11: an untracked file outside results/ marks the run dirty). No test suite, no app-driving
agent and no other command of this session runs beside it; other projects' sessions seen
on the machine are recorded, as S7a recorded them. The command's start time (UTC) and the
results directory's last file time go into the findings note's Reproduction section.

**The linear-motor convergence check** (exit criterion 6, "one linear-motor structural
x*", registered here as part 1 registered the central case's, so that it is not an extra,
unregistered solve): at S7b, after run B has finished (never beside it), from the same code
as run B (`git diff --quiet <run B's commit> HEAD -- src configs experiments pyproject.toml
uv.lock tests` exits 0), a committed script under docs/findings/scripts/ solves
lm_fixed_s1_st of file B (its pad, lm_fixed and that case, read from the committed file)
at the shipped budget and under its tightening by the file's `checks.convergence`
(`SearchContext.tightened`: every search and final tolerance divided by 10, the max-step
caps multiplied by 0.5). Each chain flies its own pad, whose P* is its P_ref and whose
flight is its envelope; each chain's flown push is flown with that chain's context (the
transform's `push_context` replaced by the tightened context, as S4b's linear-motor
convergence test passes it: nothing tightens the push automatically, docs/physics.md, "The
flown push of a linear motor"); the structure's fixed-point tolerance (1e-6 kg) is
unchanged; each chain's x* is checked by an independent payload search at its own budget.
It writes only under the session's scratch directory, never in results/. Passes if the
tightened x* is within 0.1% of the shipped x*, which must equal run B's within 0.002 kg.
The case is lm_fixed's central structural solve, the brief's proposal, kept because on the
solve's offloaded stacks its push runs into its power limit before L (the corner speed v_e
is reached at s < L once the stack is lighter than the full load, so a `power_limit`
sub-phase boundary moves with x; KI-071), its exit speed rises with the offload, and its
structural load is the flown history's (D-SP7-52): the three parts of a linear-motor
solve that file A's check did not exercise. The stations part of criterion 6 is file A's
(passed at S7a, +6.2e-6 kg) and is not repeated: the station model does not depend on the
drive. The check's numbers are quoted in the findings note's convergence line, never as a
finding; a failure blocks every linear-motor number of file B until explained.

Nothing ran file B: no `launchsim` command, no offload of any case and no coupled
structural solve of any case (D-SP7-31). What this step computed, all under section 2(c):
the file resolved as `launchsim run` resolves it (`cli.load_experiment`: the vehicle, the
structure file through `load_structure`, `sim.check_result_names` and the preflight
`sim.check_resolved`), `sim.check_resolved` again and `run_ignition_specs` on every one of
its 31 resolved runs (the pad, the ten variants and the twenty case starts): all passed;
the pad flown once (its payload search and recorded run), for the sizing envelope, as
D-SP7-31 allows; each variant's push flown alone (`sim.flown_push_trace`: the track phase
only, no ascent) at chosen stack masses; and sizing-only estimates through each structural
case's transform (`StructureTransform.sizing_at`), placed on SP1's penalty curve (section
7). tests/test_config_planar.py checks the declared cases of section 4 and the rule values
and validity conditions of section 5, and flies five of the pushes alone at the full load
(lm_cmd, lm_cmd_taper, lm_cmd_hot, lm_fixed and lm_fixed_r07: each reaches v_e at L, check
3's full-load exits for lm_fixed and lm_fixed_r07, and the lm_cmd family logs no cap or
power event, check 2 at the full load); the rest of checks (2) to (4) are the scratch
scripts' (section 12).

## 2. What is already known before any run

Stated plainly: much of file B's answer is not unknown. Four kinds of numbers exist before
run B, and the readings of section 8 were fixed with all of them known.

**(a) Part 1's results** (run A, results/silo_structure_2d/20261016T171513Z, from 1b5f9d4;
run C and sweep A beside it; S7a's draft, docs/findings/RQ1-structural-2d.md). silo_cold_s1
41,262.908 kg (SP1's to the bit); the structural headline silo_cold_s1_st
11,420.246638573297 kg (27.7% of 41.26 t; dm 6,305.2 kg; "cancels most"); the hot starts
silo_hot_ramp_s1 46,013.437 kg and silo_hot_ramp_s1_st 18,273.917 kg (dm 6,210.0 kg),
silo_hot_full_s1 38,980.362 kg and _st 16,336.257 kg; the physics band no offload to
28.57 t, the outer envelope no offload to 31.12 t; the lowest exit speed of sweep 1 that
still offloads once the central structure is charged, 76.71 m/s (100 m); the central and
design-axis structural x* at the headline push 204 to 315 kg above part 1's estimates (the
penalty curve's chord bias; 5.6 kg on the 4.0 g0 cap row, 18 to 56 kg on the band's
low-mass ends and the outer low end), the two hot starts 1.6 and 2.1 t above theirs; the
central convergence check passed (+0.0378 kg, 3.3e-6 relative). S7a's finding, plainly:
at the central coefficients a first-order structure sized for the push cancels most of
SP1's uncharged offload.

**(b) Two linear-motor pushes are file A's pushes by construction** (sizing only, section
7). lm_cmd flies the ramped plateau a_p that file A's constant_accel `rise_time` row
charges (design 4.2.1's a', `structure.ramped_plateau_accel_mps2`; section 5), so at any
offload its dm equals silo_cold_s1_st's (6,309.590919961468 against 6,309.590919961466 kg at
the same x, sizing only) and its release state (cold, at the mouth, v_e, the full stack) is
silo_cold's. lm_cmd_hot lights its 2 s ramp so that it ends at the release, as
silo_hot_ramp_on_track does, so its release state (v_e at the mouth at full thrust, 2,697.46
kg burned on the track) is silo_hot_ramp_on_track's, and its dm at 16.2 t (6,238.4 kg, its
peak interface force coming before its ignition) equals part 1's sizing of
silo_hot_ramp_s1_st at the same x to 0.1 kg (part 1, section 7). Both pairs are therefore
expected to reproduce run A's numbers (section 7); only lm_cmd's uncharged equality is a
blocking check (design 4.10; section 9).

**(c) This step's checks and estimates**: the rule values and the checks of the flown pushes
(section 5) and the sizing-only estimates of every case (section 7).

**(d) Solves on linear-motor pushes exist, none of a registered case**: S4b's slow coupled
solve on the synthetic structure file (tests/test_structure_linear_motor.py::
test_a_linear_motor_structural_case_solves: a cold force-law push over 100 m, x* 13,160.9 kg
with dm 5,906.2 kg, 3.4e-7 relative under the tightened budget) and S5's sizing of a sealed
and a vented flown push on the same file (5,812 against 5,903 kg). Both are synthetic-file
numbers, never quoted as results, and nothing below uses them.

So run B re-measures, with full solves and independent verifications, numbers that file A's
solves and this step's estimates have largely placed. What this note fixes in advance is
the design around them, the method of the estimates and how each result will be read.

## 3. Comparison basis and resolution

- Reference payload P_ref: file B's pad P*, on the same vehicle, orbit (200 km circular,
  28.5 deg, due east) and shared blocks as files A and C (one budget id; guidance
  sweep-optimized per run; results called "sweep-optimized"); expected 26,054.396243494975
  kg, SP1's (tests/data/silo_offload_2d_record.json). This step flew the pad afresh and got
  the same bits (0.0 kg). The run's pad P* must equal it within 0.002 kg (section 9): the
  structure's envelope is that pad's own flight. The pad keeps its vehicle (D-SP7-35).
- Offload x* and the structural charge as part 1, section 3: the largest evaluated stage-1
  propellant removal with m_res >= 0 when the assisted run flies P_ref, tanks partly filled
  with the mixture ratio kept; a structural case carries dm(x) = dm1 + dm2 re-sized at every
  x the solve evaluates, its push flown in every sizing (S4b), dm1 on stage 1 (the stage-1
  elements and the interstage, D-SP7-36) and dm2 on stage 2. Stage 1 is the only mode solved;
  the stage-1 pad control is the solver's consistency test.
- The cross-commit check (design 4.10; exit criterion 7): file B's silo_cold_s1 equals SP1's
  41,262.90803733282 kg and its silo_cold_s1_st equals run A's 11,420.246638573297 kg, each
  within 0.002 kg. The code changed between run A (1b5f9d4) and run B (S4 to S5a: the linear
  motor, the target-speed release, the flown structural push, the sealed shaft), each step
  pinning constant_accel's resolved and flown paths, so this check measures that nothing on
  silo_cold's path moved.
- Calibration: every number carries the gate fork's +14.3% miss (docs/findings/
  CAL-f9-leo-2d.md). File B has no README-loads fork.
- Resolution. Part 1's rule (section 3) carries over: at the same P_ref two structural x*
  read as equal within R about 3.4 kg, two uncharged x* within about 2.55 kg, and two
  structural costs U - X within about 6 kg (their sum). On the force-law variants the
  release state moves with the offload, so the residual m_res(x) flattens or steepens by
  the factor 1 - dU/dx, where U is the uncharged offload of the flown release state
  (section 7's method): dU/dx about +0.03 to +0.05 where the exit speed rises with the
  offload (pushes flown alone: dv/dx about 7e-5 to 9e-5 m/s per kg against SP1's 490 to 561
  kg of offload per m/s of exit speed; lm_fixed_hot adds its falling burn on the track) and
  about -0.001 on lm_fixed_target, whose release falls deeper in the shaft as the offload
  grows but at v_e, so that only the altitude's worth moves with x (about 5 to 6 kg per m
  and 2.2e-4 m per kg; section 7). Each R moves by at most about 5% (about 3.6 kg for X).
  Every difference expected below that a sentence reads is at least about 140 kg, beyond
  R, apart from lm_cmd's against silo_cold_s1_st (expected 0, read against R); the
  reproductions are judged at 0.002 kg and 0.25 kg (section 9), not against R.

## 4. The cases and what each is for

All on silo_cold's silo: a vertical 100 m vented stroke exiting at the mouth (z = 0), the
linear-motor drive's rise time t_r 0.5 s (silo_cold flies an instant 3 g0 step; its
structure charges the structure file's assumed 0.5 s rise time, D-SP7-09, which its push
does not fly), drive efficiency 0.5 (SP1's, assumed; it moves the electricity
only), exhaust impingement 0 (SP1's: the exhaust is assumed to miss the carriage), a 5 g0
carriage brake (SP1's) and a massless carriage, unless stated; stage 1 lit 0.5 s after the
release with its 2 s ramp (silo_cold's cold start) unless stated. Each variant has two
stage-1 cases, `<variant>_s1` (uncharged) and `<variant>_s1_st` (the central structure at
file A's headline settings: set central, sizing flown, dynamic rise_time, entry aft_ring,
margin 0, no envelope cap, no override, not plausibility-scaled; on a linear-motor push the
dynamic factor takes the drive's own t_r and the charged load is the larger of the rise
formula and the flown history's single-mode bound, D-SP7-52).

| Variant | Drive | Isolates (design 4.10) |
|---|---|---|
| silo_cold | constant_accel 3 g0, 100 m (file A's) | the comparison basis and the cross-commit check (design 4.10) |
| lm_cmd | acceleration law: a_cmd so the ramped profile reaches v_e at L, t_r 0.5 s; release at L | constant_accel with a flown ramp (its uncharged x* equals SP1's within 0.25 kg for a cold start: pre-registered by the design) |
| lm_cmd_taper | lm_cmd with a stop taper over v_e t_r metres, a_cmd re-solved | the cost of a gentle stop against the release flag |
| lm_cmd_hot | lm_cmd, stage 1 lit so its 2 s ramp ends at release (push_start reference) | the hot start under a structure-protecting drive (thrust replaces motor force) |
| lm_fixed | force law: F_max for the full-load vehicle to reach v_e at L with t_r 0.5 s; r = P_max/(F_max v_e) = 1; release at L | a facility sized for the full load, run at full force on a lighter stack |
| lm_fixed_target | lm_fixed, release at v_e | the same exit speed from a fixed facility |
| lm_fixed_r07 | r = 0.7, F_max re-solved for the same full-load exit; release at L | a power-limited drive |
| lm_fixed_hot | lm_fixed, lit at push start | the force-limited hot start (pre-registered to raise the upper-stack flag) |
| lm_fixed_sled22 | lm_fixed with a 22 t carriage | carriage mass at a fixed force |
| lm_fixed_sealed | lm_fixed with the sealed shaft (bore 5.24 m by D-SP7-54, gap 5 m, gamma 1.4) | the air column |

The stage-1 pad control (pad__offload_stage1) is expected no_offload at x = 0 with its
consistency test passing, as in SP1 and run A (m_res(0) -0.0016 kg).

## 5. The rule values and the checks before registration

**The rules** (sources section 10, applied as written; docs/physics.md, "The linear-motor
rules of file B (SP7 step S6b)"). Computed by docs/findings/scripts/sp7_drive_rules.py
(`uv run python docs/findings/scripts/sp7_drive_rules.py`; it flies nothing, prints every
input and value at full precision and checks every validity condition: 21 of 21 pass) and
written into file B at full precision, each with a comment naming its rule and the sources
section; tests/test_config_planar.py::test_drive_rule_values_follow_their_closed_forms
recomputes every value from the raw files and the constants, not through the script, and
holds the file to 1e-12 relative (the largest difference measured is 3.7e-14, on
lm_cmd_hot's t_ign_s; the plateau's two algebraic forms differ by 1.2e-14). Nothing
changes after any run (D-SP7-24). Inputs: M = 572,354.3962434949 kg (the vehicle file's
22.2 + 410.9 + 4.0 + 107.5 + 1.7 t plus SP1's P_ref 26,054.396243494975 kg; the sources'
572,354.4 kg is its rounding; section 6, item 2), v_e = 76.70717046013364 m/s, L = 100 m,
t_r = 0.5 s, g_eff = 9.772091717511234 m/s^2 (`dynamics.g_eff_track` at 28.5 deg, azimuth
90 deg), the vehicle's stage-1 ramp t_ramp = 2.0 s, vacuum thrust 8,226.9 kN and full mass
flow 2,697.46 kg/s, and for the bore the display file's 5.2 m fairing and 3.66 m body (read
for D-SP7-54's provenance only: the model reads file B's literal 5.24 m, never the display
file).

| Variant | Field as written | Value | Rule |
|---|---|---|---|
| (all) | the plateau a_p [m/s^2] | 29.51066660871779 (3.0092505 g0) | smaller root of v_e^2 = 2 a_p L - a_p^2 t_r^2/12; equals `structure.ramped_plateau_accel_mps2(L, v_e, t_r)`, the plateau file A's constant_accel `rise_time` row charges |
| lm_cmd, lm_cmd_hot | accel_command_g | 3.0092505196695907 | a_p / g0 |
| | force_max_kN | 24732.025367046735 | 1.10 M (a_cmd + g_eff) / 1e3 |
| | power_max_MW | 1897.1236856544033 | force_max_kN v_e / 1e3 |
| lm_cmd_taper | stop_taper_m | 38.35358523006682 | v_e t_r |
| | accel_command_g | 3.7293839141545706 | a_t / g0, a_t the same root with L - s_taper/2 (36.57276276174392 m/s^2) |
| | force_max_kN | 29178.249324913388 | 1.10 M (a_t + g_eff) / 1e3 |
| | power_max_MW | 2238.1809446944103 | force_max_kN v_e / 1e3 |
| lm_cmd_hot | ignition stage1 t_ign_s | 0.8493032105033325 (push_start) | t_push - t_ramp, t_push = t_r/2 + v_e/a_cmd = 2.8493032105033325 s |
| lm_fixed, lm_fixed_target, lm_fixed_hot, lm_fixed_sled22, lm_fixed_sealed | force_max_kN | 22483.65942458794 | M (a_p + g_eff) / 1e3 |
| | power_max_MW | 1724.6578960494573 | r force_max_kN v_e / 1e3, r = 1 (corner speed P_max/F_max 76.70717046013364 m/s, v_e to the last bit) |
| lm_fixed_target | release_speed_mps | 76.70717046013364 | v_e |
| lm_fixed_r07 | force_max_kN | 25236.147321379234 | F_max / 1e3, F_max the bracketed root of s(v_e) = L (ramp, force plateau to v_c = 0.7 v_e, power phase) |
| | power_max_MW | 1355.0554180366573 | 0.7 force_max_kN v_e / 1e3 |
| lm_fixed_hot | ignition stage1 t_ign_s | 0.0 (push_start) | lit at push start |
| lm_fixed_sled22 | carriage_mass_t | 22.0 | the sources' 22 t (silo_screening_2d's silo_sled_22t; assumed) |
| lm_fixed_sealed | shaft_bore_m, shaft_gap_m, shaft_gamma | 5.24, 5.0, 1.4 | D-SP7-54: 5.2 m fairing + (3.7 - 3.66) m; the sources' central gap; ICAO's adiabatic index |

The validity conditions, each checked by the script and by the test: the plateau's rise
ends inside the stroke (a_p t_r^2/6 = 1.23 m < L; a_p t_r/2 = 7.38 m/s < v_e); the taper's
rise ends before the taper (1.52 m against L - s_taper = 61.65 m) and the taper's closed
form returns v_e at L; lm_cmd_hot is lit after push start and after the command's rise
(0.849 s >= 0.5 s), and its drive force stays positive at full vacuum thrust, the second
condition of t_push's closed form (the drive never pulls back): (m_release)(a_p + g) -
T_vac = 14.15 MN on the full load and 11.79 MN on a stack offloaded by 60 t with no dm
(check 2's largest offload; no dm, the lightest stack there), reaching zero only on a stack
below 209.4 t at the release (an offload beyond 360.2 t), so it cannot reach `drive_limit`
on those stacks; lm_fixed_r07's bracket holds (s(v_e) - L = +17.03 m at lm_fixed's F_max,
-50.62 m at twice it), its rise ends below its corner (a' t_r/2 = 8.58 m/s < v_c = 53.70
m/s), v_e < v_inf (242.3 m/s) and its plateau reaches v_c inside the stroke (s_c = 42.36
m); the sealed bore lies above the run's body diameter sqrt(4 A_ref/pi) = 3.660 m, its
gamma is the ICAO adiabatic index (`atmosphere.KAPPA_AIR`, 1.4), and F_max exceeds M g_eff
+ F_p(L) (22.48 against 7.77 MN; F_p is largest at L, 2.18 MN of the bound p_0 A = 2.21 MN,
p_0 = p_atm(-100 m) = 102.53 kPa); the 22 t carriage leaves F_max above the stack's and
carriage's weight (22.48 against 5.81 MN). None failed, so no rule needed a choice.

**The checks before registration** (each a check, never a choice; pushes flown alone on the
vehicle at P_ref, offloaded along stage 1, the track phase only, no ascent; the final
tolerance, dense output; the scratch scripts are outside the repository and their numbers
are checks, never findings):

1. **The file resolves and passes the preflight**: `cli.load_experiment` (the result names
   and `sim.check_resolved`, including the structure block's held-down pad), then
   `sim.check_resolved` again and `run_ignition_specs` on all 31 resolved runs: every one
   built. The resolved file: 11 runs (pad, silo_cold, the nine variants), 20 cases, the
   stage-1 pad control, no arm, no sweep, no payload case; the structure file's recorded
   sha256 a0516875... (section 12). The pad flown afresh: P* 26,054.396243494975 kg, SP1's
   P_ref to 0.0 kg.
2. **No `drive_cap` or `power_limit` on the lm_cmd family**, at the full load and at x = 0,
   20, 40 and 60 t of stage-1 propellant less, each stack carrying that x's central dm
   estimate (`sizing_at(x)` of the variant's _s1_st case): lm_cmd and lm_cmd_hot dm 6,467.0,
   6,186.3, 5,918.3 and 5,664.9 kg (stacks 578.8 to 518.0 t), lm_cmd_taper 8,052.8,
   7,661.0, 7,298.6 and 6,951.2 kg (580.4 to 519.3 t), all below 1.10 M = 629.6 t. Every
   push logged only push_start, drive_ramp_end (and taper_start, or ignition and ramp_end)
   and the release: no cap event, no power event. Passes for all fifteen pushes. The three
   pushes flown at the variant runs' order of payload, P_ref + 1,498.8 kg (check 3), log
   none either.
3. **The force law's full-load exits**: lm_fixed at the full load reaches 76.70717046013361
   m/s at L (3.7e-16 relative to v_e, against 1e-6), with no power_limit event (its corner
   speed P_max/F_max equals v_e to the last bit, so the limit is met at the exit);
   lm_fixed_r07 reaches 76.70717046013357 m/s at L (9.3e-16), its power_limit at 1.8146 s
   and v_c; lm_fixed_target releases at v_e before L on every lighter stack: at 99.977,
   99.769, 98.848, 97.702, 95.431, 90.688 and 86.603 m along the stroke for 0.1, 1, 5, 10,
   20, 41.26 and 60 t of offload (the `target_speed` event; 99.164, 96.876, 92.380 and
   87.985 m for 10, 20, 40 and 60 t carrying their dm). At the full load itself v_e and L
   coincide: the final-tolerance flight reaches L at 76.70717046013361 m/s, inside the
   flag's 1e-9 m/s tolerance, and releases at the track end with no flag (a search-mode
   flight logs the `target_speed` event at L instead; the release state is the same). On
   any stack heavier than M by more than about 0.01 g (the flag's tolerance) the push
   reaches L below v_e and releases there with the flag `release_speed_not_reached`: at
   P_ref + 1 g (76.70717037 m/s), and at x = 0 and 5 t carrying their dm (6,375.3 and
   6,376.0 kg; 76.144 and 76.585 m/s). The corner speed and the release speed are both v_e,
   equal to the last bit, so on a lighter stack the power limit and the release meet at one
   instant: whether a `power_limit` event is logged there is a rounding matter (none on the
   eleven lighter stacks; with power_max_MW one ulp lower one is logged on five of them),
   and no stack flies power-limited.

   **The variant runs.** Each variant's own run is a payload-capacity search
   (`search.figure_of_merit: payload`) whose recorded run flies its own P*, above P_ref for
   any assisted run (SP1's silo_cold: P_ref + 1,498.8 kg): the full load plus its payload
   gain, a stack heavier than M. Its search flies lighter stacks too: the gamma* grid runs
   at the vehicle file's 22.8 t payload (P0,
   `search.SearchProblem.payload_kg`) and the first payload bracket at 20.8 and 24.8 t,
   stacks 1.25 to 5.25 t lighter than M. At P_ref + 1,498.8 kg (the order of that gain;
   each variant's own differs) the acceleration law's pushes are unchanged
   (mass-independent while no cap binds: v_e at L), and the force law's pushes exit at L at
   76.574 m/s (lm_fixed, 2.8538 s), 76.611 (lm_fixed_r07), 89.250 (lm_fixed_hot), 74.673
   (lm_fixed_sled22) and 71.840 m/s (lm_fixed_sealed). lm_fixed_target reaches L below v_e
   and releases there with `release_speed_not_reached`: the same flight as lm_fixed's
   (76.574 m/s in 2.8538 s), so its recorded run at P* is lm_fixed's flight, and its P* is
   expected to equal lm_fixed's within the payload search's tolerance (final_payload_xtol_kg
   0.05 kg), not to the bit. On its search's lighter stacks the target-speed release acts
   (at 22.8 t it releases at 99.249 m at v_e, where lm_fixed exits at L at 76.997 m/s with a
   `power_limit` event), so its grid table and its P0 figures (m_res and the delta-v margin
   at 22.8 t) differ from lm_fixed's, and the grid's best point, the warm starts and P1 may
   too; a larger difference in P* is reported as it is. The cold force-law variant runs'
   recorded runs therefore exit below v_e. Their uncharged cases, and the structural cases
   whose x* exceeds their dm, fly stacks lighter than M and release faster than the variant
   runs (lm_fixed_target's at v_e, below the mouth); lm_fixed_r07_s1_st (x* 5.49 t, below
   its dm of 7.40 t, at the estimate) flies a stack about 1.9 t heavier than M and exits at
   about 76.59 m/s (section 7).
4. **The flown pushes at the full load and at x = 41.26 t** (SP1's offload, no dm; the
   felt peak is the largest flown n = (F_int + T)/(m_v g0): on the cold pushes and on
   lm_cmd_hot the plateau, from the rise end on; on lm_fixed_hot its power-limit corner
   (2.29 s at the full load), the thrust and the burn included; F_int peak the largest
   interface force):

| Variant | full: exit [m/s] | release [m] | felt peak [g0] | F_int peak [MN] | push [s] | 41.26 t: exit [m/s] | release [m] | felt peak [g0] | F_int peak [MN] | push [s] |
|---|---|---|---|---|---|---|---|---|---|---|
| silo_cold | 76.7072 | 100.000 | 3.9965 | 22.432 | 2.6073 | 76.7072 | 100.000 | 3.9965 | 20.815 | 2.6073 |
| lm_cmd | 76.7072 | 100.000 | 4.0057 | 22.484 | 2.8493 | 76.7072 | 100.000 | 4.0057 | 20.863 | 2.8493 |
| lm_cmd_taper | 76.7072 | 100.000 | 4.7259 | 26.526 | 2.6028 | 76.7072 | 100.000 | 4.7259 | 24.613 | 2.6028 |
| lm_cmd_hot | 76.7072 | 100.000 | 4.0057 | 22.484 | 2.8493 | 76.7072 | 100.000 | 4.0057 | 20.863 | 2.8493 |
| lm_fixed | 76.7072 | 100.000 | 4.0057 | 22.484 | 2.8493 | 80.4457 | 100.000 | 4.3169 | 22.484 | 2.7242 |
| lm_fixed_target | 76.7072 | 100.000 | 4.0057 | 22.484 | 2.8493 | 76.7072 | 90.688 | 4.3169 | 22.484 | 2.6057 |
| lm_fixed_r07 | 76.7072 | 100.000 | 4.4961 | 25.236 | 2.6862 | 79.4542 | 100.000 | 4.8454 | 25.236 | 2.5799 |
| lm_fixed_hot | 89.3716 | 100.000 | 5.3938 | 22.484 | 2.6083 | 92.8433 | 100.000 | 5.8109 | 22.484 | 2.5068 |
| lm_fixed_sled22 | 74.7992 | 100.000 | 3.8575 | 21.651 | 2.9160 | 78.4340 | 100.000 | 4.1452 | 21.589 | 2.7909 |
| lm_fixed_sealed | 71.9688 | 100.000 | 3.9023 | 21.903 | 2.9686 | 75.7052 | 100.000 | 4.1969 | 21.859 | 2.8352 |

   silo_cold's row is its instant-step push as flown (3 g0 net from rest); file A's
   structure charges it the ramped plateau lm_cmd flies (4.0057 g0 quasi-static, then the
   dynamic factor). The hot pushes hold nothing on the clamp (no hold phase; the delivered
   thrust is 0 at push start, so F_rest = m_v g_eff exactly) and burn on the track 2,697.46
   kg (lm_cmd_hot, at both stacks: silo_hot_ramp_on_track's ramp) and 4,338.4 and 4,064.5
   kg (lm_fixed_hot, full load and 41.26 t); both reach full thrust (7,606.8 kN delivered at
   the mouth) by the release. With no carriage the force law's F_int equals its drive force,
   F_max on the plateau at every stack; the 22 t carriage takes the share m_c/(m_v + m_c) of
   it, and the sealed column lowers it by F_p (by (m_v/(m_v + m_c)) F_p with a carriage).
   The lighter stack exits faster under the force law (+3.74 m/s for lm_fixed at 41.26 t),
   and the 22 t carriage and the sealed column take 1.91 and 4.74 m/s from the full-load
   exit.

## 6. Choices fixed by this pre-registration

1. **Part 2 is a separate file** (this one), with a pointer paragraph added to part 1's
   header; the brief offered appending it to part 1 instead. Kept apart so that part 1's
   existing text and its Amendment 1 stay as committed (the pointer paragraph is the only
   addition) and part 1's section numbers keep their meaning in run A's note.
2. **M at full precision** (D-SP7-55): the rules take M = 572,354.3962434949 kg, the sum the sources
   name (22.2 + 410.9 + 4.0 + 107.5 + 1.7 t + P_ref), with SP1's P_ref at full precision,
   not the sources' rounded 572,354.4 kg (3.8e-3 kg higher; it would move every force rule
   by 6.6e-9 relative). With it lm_fixed's full-load stack, the stack the pad's P_ref
   defines, reaches v_e at L to 3.7e-16 (check 3). The values written are this M's: a
   recomputation from the rounded 572,354.4 kg differs from every force and power value by
   6.6e-9 relative, beyond the registered 1e-12, so a recomputation takes this M.
3. **v_e computed, not typed**: sqrt(2 x 3 g0 x 100 m) from silo_cold's own settings, equal
   to silo_cold_200m's written 76.70717046013364 m/s (asserted). lm_cmd_hot's t_push uses
   the rule's a_cmd in m/s^2, not its round trip through accel_command_g (at most one ulp).
4. **No sensitivity arm**: design 4.10 names none for file B, and its 18-minute budget has
   none; CLAUDE.md's headline arms are file A's, on silo_cold_s1_st (run A: 8.55 to 15.07 t,
   every arm below half). No file-B number is the headline. The cost of adding them is in
   section 11.
5. **No payload case**: design 4.10 names none. A file-B case that ends no_offload (none is
   expected, section 7) is reported with its delta-v shortfall and "payload deficit not
   flown: no payload case at these settings" (D-SP7-32; part 1, section 6, item 5), and no
   payload case is added after the run except by an amendment.
6. **The convergence case** is lm_fixed_s1_st (section 1), with its push flown under each
   chain's own context.
7. **The sealed bore** is 5.24 m (D-SP7-54, 2026-10-25, made at S5's review after run A,
   before this registration): the 5.2 m fairing stands 30 to 43 m below the mouth of a 100
   m silo at push start and must pass the bore, so the design's 3.7 m (the sources' row,
   README.md line 246) is not a facility this vehicle could use. The rule: the fairing's
   diameter plus the design's own diametral clearance over the body (3.7 - 3.66 = 0.04 m;
   nominal, since 3.7 m is also SpaceX's rounding of the 3.66 m body: 2 cm radial around
   the fairing). Both diameters are read from configs/display/f9_class.yaml (spacex.com;
   Falcon User's Guide 2021) for the decision's provenance only: file B writes 5.24 m as a
   literal, and the model never reads the display file.
   It roughly doubles the column's force bound (2.21 MN against about 1.1 MN at 3.7 m) and
   so lowers lm_fixed_sealed's exit speed (against the assist in the sealed row; D-SP7-54
   was made for the geometry, not for a result). Not taken: 3.7 m with a caveat (a facility
   that cannot exist), the display file's assumed 7.0 m drawn shaft, dropping the variant.
   D-SP7-54 records that it was session-made and open to the user's change before this
   registration commit.
8. **silo_cold written verbatim** from file A, with its comment ("The headline variant.",
   file A's wording; in file B it is the comparison basis); the energy block is file A's
   (SP1's) verbatim.
9. **Every linear-motor push writes its silo settings out** (stroke 100, carriage 0 or 22,
   brake 5, efficiency 0.5, impingement 0.0, shaft, track angle 90 and exit 0), no YAML
   anchor, so a test can read each variant's block alone.
10. **The expected values' x0 method** (section 7) goes beyond part 1's shift method, which
   took each push's uncharged offload from SP1's records: no linear-motor offload was ever
   solved, so each case's uncharged offload is estimated from its flown release state by
   rules stated in section 7, the 1-for-1 burn rule among them checked on run A's solved
   silo_hot_full from its solved silo_hot_ramp (0.06 kg), and the early release's
   altitude worth priced from SP1's solved ignition-delay offloads. Estimates only; no
   reading depends on them.
11. **KI-067 read against file B** (section 10): the brief names it an unconservative bias
   of lm_cmd_hot and lm_fixed_hot. KI-067 concerns a hot push lit before its push start,
   whose startup ramp lowers F_int on the clamp before the push; neither file-B hot start
   holds on the clamp (lm_fixed_hot is lit at push start, where its delivered thrust is 0;
   lm_cmd_hot 0.849 s into its push), so the rest at push start is exact for both and the
   bias does not reach them. Stated with its direction for any hot push that does hold.
12. **Names**: every derived run name (the 20 cases and the pad control) is a valid results
   name within 64 characters (a test; the longest, lm_fixed_target_s1_st, has 21).
13. **The structure files stay as frozen** at 45e39d4; nothing is added to them.

## 7. Expected values (estimates; none is a target)

**Method.** Sizing only, no offload solved (D-SP7-31). For every structural case the case's
own transform (`sim.build_structure_transform` with the pad flown afresh at P_ref as its
envelope, as `sim.offload_structure_transform` builds it) gives dm1(x) and dm2(x) at any
offload x, its push flown in every sizing exactly as the solve will fly it. Each case is
then placed by part 1's coupled placement on SP1's penalty curve X(dm) (its four solved
rows, linear between them, the last segment extended; w = 5.478 for stage 2), shifted to
the case's own uncharged offload: x = max(0, U(state(x, dm(x))) + X(dm1 + w dm2) -
41,262.908), iterated until two iterates agree to 1 g. New against part 1: U depends on the
push's release state, which a linear motor's offload changes, so U is estimated from the
release state of the push flown alone at x carrying dm(x), by these rules:

- a cold release at the mouth at speed v: U = SP1's sweep-1 uncharged offload at v (its five
  points at 38.35, 54.24, 76.71, 108.48 and 132.86 m/s, part 1 section 9's values, linear
  between them): the push changes nothing else about the release state (the mass, the
  position, the ignition 0.5 s after the release), so the flight is SP1's sweep point's;
- an early release (lm_fixed_target) at v_e from d metres below the mouth, its stage 1 lit
  0.5 s after the release: the flight from the release is silo_cold's lowered by d (the
  same speed, mass and 0.5 s coast, so the same speed at ignition, 71.82 m/s, d metres
  lower), so U = U(v_e) less the altitude's worth, w_h d. SP1's solved silo_cold_s1
  offloads against the ignition delay after a mouth release at v_e price it
  (silo_offload_2d sweeps 3 and 4 and silo_cold: 43,631.2, 43,014.8, 41,262.9 and
  41,070.2 kg at delays 0, 0.13, 0.5 and 0.54 s, ignition heights 0, 10, 37.1 and 40 m).
  Priced against the quadratic through sweep 1's three neighbouring points at each delay
  point's own ignition speed (sweep 1's own 0.5 m of ignition height per m/s of exit speed
  removed), the four delay points (sweep 3 at depth 0, sweep 4 at 10, 40 and 100 m, the
  last 36,655.6 kg) give 5.2 to 5.5 kg per m (5.2 to 5.3 on the three at 0 to 40 m, which
  contain the case's ignition heights, 27.8 m uncharged and 36.1 m at x*). The estimate
  takes 6.0 kg per m, the 10 to 37.1 m step priced with its change of ignition speed at
  the quadratic's slope at v_e (531.7 kg per m/s) and sweep 1's own ignition height left
  in: 0.5 to 0.8 kg per m high (the bias, below). Pricing the depth as lost mouth speed
  instead (U at sqrt(v_e^2 - 2 g_eff d)) would charge the 1.19 m/s that the about 0.12 s
  less coast after the mouth crossing gives back (at d = 9.30 m), and place U about 0.6 t
  low;
- a hot start at full thrust at the release: U = silo_hot_ramp's 46,013.437 kg (the 2 s
  ramp ending at release at v_e), plus the sweep-1 difference U(v) - U(v_e), less one for one
  the propellant burned on the track beyond that ramp's 2,697.46 kg. The 1-for-1 rule is
  checked, not only assumed: the release state depends on the propellant left, so a
  kilogram burned on the track is a kilogram offloaded; applied to run A's silo_hot_full
  (9,730.60 kg burned) from its silo_hot_ramp, it gives 38,980.30 kg against the solved
  38,980.36 kg (one solved case).
- the uncharged case: the same map with dm = 0, iterated to its fixed point.

The "naive" placement reads dm sized at the case's uncharged estimate straight off the
curve, with no re-sizing. Beside each estimate: its difference from silo_cold_s1_st's
estimate by the same method, and that difference added to run A's solved 11,420.2 kg
("anchored"), which removes the part of the placement's bias the cases share.

**Biases, with their direction and size where known.**
- The penalty curve's chord bias (part 1, section 7; concave curve, chords place x low,
  against the assist): measured on run A at the headline push, +204 to +315 kg (solve
  minus estimate) on the central and the design-axis rows. Expected on every case here.
- The shift for a hot start (U above 41.26 t): measured on run A, silo_hot_ramp_s1_st solved
  2,055 kg above part 1's estimate and silo_hot_full_s1_st 1,646 kg above its estimate
  re-placed on its solved U (S7a's note: "both hot starts depart upward, by 1.6 to 2.1 t";
  why is not measured). Expected on lm_cmd_hot and lm_fixed_hot (against the assist).
- U's own interpolation on sweep 1 (concave in v: its segment slopes 622, 561, 490 and 429
  kg per m/s, so a chord places U low, against the assist): a quadratic through three
  neighbouring points puts U higher by 4 to 330 kg at the speeds flown here off v_e (the
  most at lm_fixed_hot's 89-94 m/s; none at v_e itself, a sweep point: silo_cold, the
  lm_cmd family and lm_fixed_target).
- The early release's altitude worth (lm_fixed_target only; d = 9.3 m uncharged, 1.0 m at
  x*): priced consistently (each delay point at its own ignition speed, above), the delay
  points agree at 5.2 to 5.5 kg per m, so the estimate's 6.0 places U about 5 to 8 kg low
  uncharged (41,207.1 against 41,211.6 to 41,214.8 kg; about 2 to 3 times the uncharged R
  of about 2.55 kg) and x* under 1 kg low: sign known, against the assist; no reading
  moves. Pricing every delay step at the slope at v_e with sweep 1's ignition height left
  in gives 5.3 to 6.7 kg per m, and at sweep 1's linear segment slopes (561 and 490 kg per
  m/s) -0.4 to 10.5 kg per m (chords over 22 to 32 m/s of a curve whose curvature is
  known; not used). The lowered flight differs from silo_cold's only by the depth's effect
  on the air and on gravity (about 0.1% denser air and 3e-6 stronger gravity at 9.3 m:
  about 0.03 mm/s less at ignition, which the estimate leaves out; for the assist: the
  estimate is high by about a hundredth of a kilogram of offload).
- A hot start's speed dependence is the cold sweep's (no hot sweep exists): sign not known.
- The structural cost per kg of dm is SP1's penalty slope at every release state; at run A
  the hot starts' cost per kg (4.41 and 4.47) lay below the cold start's 4.73 kg/kg.
- Sizing: the fixed point the solve iterates, from dm = 0 (6 to 7 sizings, contraction
  0.006 to 0.021 at the estimates).

**File B's cases** (dm1 + dm2 at x*; n_q / DLF / n_peak in g0 and F_peak in MN at x*; the
exit speed and release position of the push at x* carrying dm; % of 41,262.9 kg):

| Case | U: uncharged estimate [kg] | x*: structural estimate [kg] (% of 41.26 t) | naive [kg] | dm1 + dm2 at x* [kg] | n_q / DLF / n_peak / F_peak | exit at x* [m/s], release [m] | estimate - silo_cold_s1_st's [kg]; anchored [kg] |
|---|---|---|---|---|---|---|---|
| silo_cold | 41,262.9 (SP1's, reproduced by run A) | 11,105.2 (26.9%) (run A solved 11,420.2) | 13,183.3 | 6,309.6 + 0 | 4.006 / 1.1273 / 4.389 / 24.43 | 76.707, 100.0 | 0; 11,420.2 |
| lm_cmd | 41,262.9 (silo_cold's release state) | 11,105.2 (26.9%) | 13,183.3 | 6,309.6 + 0 | 4.006 / 1.1273 / 4.389 / 24.43 | 76.707, 100.0 | 0.0; 11,420.2 |
| lm_cmd_taper | 41,262.9 (the same release state) | 2,450.7 (5.9%) | 6,157.8 | 8,002.7 + 0.9 | 4.726 / 1.1273 / 5.201 / 29.47 | 76.707, 100.0 | -8,654.5; 2,765.7 |
| lm_cmd_hot | 46,013.4 (silo_hot_ramp's release state) | 16,218.5 (39.3%) (run A's silo_hot_ramp_s1_st solved 18,273.9) | 18,245.8 | 6,238.4 + 0 | 4.006 / 1.1273 / 4.389 / 24.20 | 76.707, 100.0 | +5,113.2; 16,533.5 |
| lm_fixed | 43,181.3 (exit 80.62 m/s) | 10,960.9 (26.6%) | 12,643.2 | 6,377.2 + 0 | 4.038 / 1.1274 / 4.426 / 24.64 | 77.116, 100.0 | -144.3; 11,276.0 |
| lm_fixed_target | 41,207.1 (release at 90.70 m at v_e) | 10,756.7 (26.1%) | 10,681.1 | 6,376.8 + 0 | 4.037 / 1.1273 / 4.424 / 24.64 | 76.707, 99.0 | -348.5; 11,071.7 |
| lm_fixed_r07 | 42,655.9 (exit 79.55 m/s) | 5,491.9 (13.3%) | 6,245.5 | 7,397.6 + 0 | 4.481 / 1.1281 / 4.927 / 27.75 | 76.585, 100.0 | -5,613.4; 5,806.9 |
| lm_fixed_hot | 53,143.7 (exit 93.89 m/s, 3,985 kg burned) | 3,750.1 (9.1%) | 1,811.8 | 8,850.9 + 124.5 | 5.345 / 1.1273 / 5.899 / 24.64 | 88.949, 100.0 | -7,355.1; 4,065.1 |
| lm_fixed_sled22 | 42,148.0 (exit 78.51 m/s) | 11,463.0 (27.8%) | 13,182.7 | 6,079.7 + 0 | 3.893 / 1.1273 / 4.261 / 23.69 | 75.257, 100.0 | +357.8; 11,778.0 |
| lm_fixed_sealed | 40,668.8 (exit 75.65 m/s) | 9,188.6 (22.3%) | 11,118.8 | 6,192.4 + 0 | 3.922 / 1.1319 / 4.308 / 24.05 | 72.228, 100.0 | -1,916.6; 9,503.7 |

The expected uncharged values are the U column. lm_cmd's and lm_cmd_taper's release state
is silo_cold's, so both are expected at SP1's 41,262.908 kg (lm_cmd's within 0.25 kg is a
blocking check, section 9; the taper's is an expectation); lm_cmd_hot's is
silo_hot_ramp_on_track's, expected at 46,013.437 kg. For lm_cmd and lm_cmd_hot the
estimates equal part 1's for silo_cold_s1_st and silo_hot_ramp_s1_st to 0.1 kg (11,105.2
and 16,218.5 kg), whose solves run A made, so their best estimates are run A's solved
11,420.2 and 18,273.9 kg. The structural cost U - x* at the estimates: silo_cold and lm_cmd
30.16 t, lm_cmd_taper 38.81, lm_cmd_hot 29.79, lm_fixed 32.22, lm_fixed_target 30.45,
lm_fixed_r07 37.16, lm_fixed_hot 49.39, lm_fixed_sled22 30.69 and lm_fixed_sealed 31.48 t.
dm'(x) at the estimates lies between -0.020 and +0.0084 kg/kg (the acceleration law about
-0.014 to -0.020; the cold force law mixed in sign: lm_fixed +2.9e-4 and lm_fixed_target
+1.5e-4, lm_fixed_r07, lm_fixed_sled22 and lm_fixed_sealed -0.7e-4 to -4.9e-4, where
D-SP7-53 found -4e-4 on S4b's synthetic case; lm_fixed_hot +8.4e-3), every one above the
-0.114 floor, so no `offload_nonmonotone` is expected.

What the estimates say, in words. The acceleration law that reaches v_e at L is
constant_accel with its ramp flown: no change. Its stop taper buys a release at zero net
acceleration with a command 24% higher (3.73 against 3.01 g0 net; felt 4.73 against 4.01
g0), and the higher plateau costs structure (dm about 8.0 t against lm_cmd's 6.3 t, stage
2 sized by a hair) with no offload gained back, since the model sizes no release step
(part 1, section 10): the gentler stop shows only in the flags (the stage-1 LOX bottom at
the release -230 against -897 kPa absolute; the release swing -1.95 against -4.39 g0).
The force law sized for the full load exits faster on the lighter offloaded stack (80.6
m/s uncharged), which raises the uncharged offload about 1.9 t, but its plateau rises with
the lighter stack too (felt 4.04 g0 at x*), and the structural estimate lands about 0.1 t
below silo_cold's. Releasing that facility at v_e gives back the exit-speed gain (the
release falls below the mouth). The power-limited drive needs a 12% higher F_max to make
the same full-load exit, and its plateau costs about 1 t more structure. The force-limited
hot start adds the thrust to F_max (5.35 g0 quasi-static, upper stack sized): its
uncharged offload rises about 10 t against lm_fixed's (53.1 against 43.2 t), its dm about
2.6 t (8.98 against 6.38 t), and its structure costs about 49 t of offload against
lm_fixed's 32 t. The 22 t carriage lowers the vehicle's share of the force (and the felt
load) and the exit speed together: about +0.4 t net against silo_cold's estimate (+0.50 t
against lm_fixed's, the CM sentence's comparator). The sealed column lowers the exit speed
at x* by about 4.5 m/s against silo_cold's (4.89 m/s against lm_fixed's): about -1.9 t
against silo_cold's estimate (-1.77 t against lm_fixed's, the SS sentence's comparator).

**Flags expected beside the numbers** (sizing only at each case's expected x; reported
beside, never a gate): the release flag on every structural case (the stage-1 LOX bottom
at the release, absolute: silo_cold and lm_cmd -897 kPa, lm_fixed -929, lm_fixed_target
-907, lm_fixed_sled22 -860, lm_fixed_sealed -809, lm_fixed_r07 -738, lm_fixed_hot -423,
lm_cmd_taper -230, lm_cmd_hot -119 kPa); the payload-limit flag on every structural case
but lm_cmd_taper (its release swing -1.946 g0 against -2.0 g0, n_peak 5.201 g0 against
+6.0 g0) and lm_cmd_hot (swing -1.617 g0), with its MECO comparison (the same instant step
swings the pad's MECO to -5.195 g0); the upper-stack flag on lm_cmd_taper (the push's
7.102 MN on the upper stack against the envelope's 7.095 MN, 0.10% over: stage 2 sized by
0.9 kg) and lm_fixed_hot (8.06 against 7.10 MN: stage 2 sized by 124.5 kg and the
interstage by 74.5 kg), as design 4.10 pre-registers for lm_fixed_hot, and on no other
case; `release_speed_not_reached` on lm_fixed_target's variant run, and on none of its two
cases' recorded runs at x* or their verifications. The flag fires on any stack heavier
than M (beyond its 1e-9 m/s tolerance: x < dm in a structural case, or a payload above
P_ref). The variant run's recorded run flies its own P*, above P_ref (SP1's silo_cold:
+1,498.8 kg), so it releases at L at about 76.57 m/s with the flag, the same flight as
lm_fixed's recorded variant run, whose P* it is expected to equal within the payload
search's tolerance (final_payload_xtol_kg 0.05 kg), not to the bit (its gamma* grid and
first payload bracket fly lighter stacks, released early at v_e, so its grid table and P0
figures differ from lm_fixed's: section 5, check 3); the cases' stacks at their estimates
are lighter than M (released at 90.7 m uncharged and at 99.0 m structural), and the
structural solve meets x < dm only on its way to x*. A flag state
that differs from these is reported as departing from its estimate.

## 8. How each result will be read

**The freeze** (D-SP7-31; part 1, section 8): from this note's commit a change to file B or
to either structure file is an amendment (its own commit, logged as a decision, this note
extended, never rewritten).

**The registered expectations** (reported as met or not met, never as a check that blocks;
a case that departs is read as flown):

- E1 (design 4.10): lm_fixed_hot_s1_st raises the upper-stack flag
  (`structure_upper_stack_exceeded`) at its x*.
- E2 (sources section 10; D-SP7-24): no `drive_cap` on the lm_cmd family: neither the
  `drive_cap` event in the recorded runs of lm_cmd, lm_cmd_taper and lm_cmd_hot (the
  variant runs and the six cases' runs at their x*) nor a cap flag in their records. A cap
  that binds is reported with that flag and the exit speed the push reached, and the case
  is read as flown; no cap changes after the run.

Read beside them, not registered as expectations of their own: lm_cmd_s1_st against
silo_cold_s1_st and lm_cmd_hot's pair against run A's silo_hot_ramp_on_track pair
(46,013.437 and 18,273.917 kg), each difference with R beside it (section 3).

**The fixed sentences** (the D-SP7-32 forms of part 1, section 8, applied to file B). "X t"
is a case's x* in tonnes to two decimals, "Y%" its share of SP1's uncharged 41,262.9 kg to
0.1% (never a share of the stage-1 load), "D t" a signed difference in tonnes to two
decimals; a difference within its R (section 3: about 3.4 kg for x*, 2.55 kg for an
uncharged x*, 6 kg for a cost) reads "the same within the resolution". A no_offload case is
written "no offload (s m/s of delta-v short of P_ref at x = 0; payload deficit not flown: no
payload case at these settings)" and counts as 0 t in a difference, never as "0 t" in a
sentence; a case that ends search_failed or reference_failed fires nothing and is reported
as such. The bracketed parts are filled from the run.

- RB, each linear-motor central case against SP1's uncharged 41.26 t (part 1's R tests,
  20,631.45 kg the threshold): "keeps more than half" if x* > 20,631.45 kg: "<case>
  (<what it isolates>) keeps more than half of SP1's uncharged offload: X t (Y%)."; "cancels
  most" if ok and below: "<case> (<what it isolates>) cancels most of it: X t is left
  (Y%)."; "cancels all" if no_offload: "<case> (<what it isolates>) cancels all of it: no
  offload at P_ref (...)". Each case's share of its own uncharged x* is printed beside.
- LM, each linear-motor central x* against silo_cold_s1_st of file B: "<case> (<what it
  isolates>) leaves X t of stage-1 propellant against silo_cold_s1_st's X_c t: <D t more |
  D t less | the same within the resolution> (uncharged U t against U_c t; the structure's
  offload cost U - X C t against C_c t)."
- HS, the hot starts against the cold start of the same drive (lm_cmd_hot against lm_cmd,
  lm_fixed_hot against lm_fixed, at the same P_ref): "<hot> keeps <more | less> offload
  than <cold> with the same drive and the same structure settings: X_hot - X_cold t
  (uncharged U_hot - U_cold t; the structure's offload cost D_hot t against D_cold t) (nothing models the
  exhaust in the shaft: back-pressure, heating, the carriage in the plume, which favours the
  hot starts)."; within R, "the same within the resolution" in place of "<more | less>".
- TS, the target-speed release against release at L: "Released where its speed reaches v_e
  (s_rel m up the 100 m stroke at x*), lm_fixed_target leaves X t against lm_fixed's X_L t
  released at the track end at v_L m/s: <D t more | D t less | the same within the
  resolution> (uncharged U_T t against U_L t)."
- CM, the carriage at a fixed force: "With a 22 t carriage at the same F_max and P_max,
  lm_fixed_sled22 leaves X t against lm_fixed's X_F t: <D t more | D t less | the same
  within the resolution> (uncharged U t against U_F t; at x* an exit speed of v m/s against
  v_F m/s and a peak interface force of F MN against F_F MN)."
- SS, the sealed shaft against vented: "In the sealed shaft (bore 5.24 m, gap 5 m) the same
  drive leaves X t against the vented lm_fixed's X_F t: <D t more | D t less | the same
  within the resolution> (uncharged U t against U_F t; at x* the column's peak force F_p MN
  and its work W_p MJ, and an exit speed of v m/s against v_F m/s)."
- TP, the stop taper (design 4.10: "the cost of a gentle stop against the release flag"):
  "The stop taper leaves X t against lm_cmd's X_c t: <D t more | D t less | the same within
  the resolution>; at x* its release flag <fires | does not fire> (the stage-1 LOX bottom
  at p kPa absolute against lm_cmd's p_c kPa; the release swing s g0 against s_c g0) and its
  payload-limit flag <fires | does not fire>."
- PL, the power-limited drive: "The power-limited drive (r = 0.7, F_max F MN) leaves X t
  against lm_fixed's X_F t (F_max F_F MN): <D t more | D t less | the same within the
  resolution>."

TP and PL are beyond the brief's list of comparisons; they read the two variants whose
design 4.10 purpose is a pairwise comparison the LM sentence alone does not state.

**The sentences expected to fire under section 7's estimates** (structural x*, placement;
anchored values in brackets): RB "cancels most" on all nine (from 2.45 t for lm_cmd_taper to
16.22 t [18.27, run A's hot ramp] for lm_cmd_hot; 5.9% to 39.3%). LM: lm_cmd the same within
the resolution (0.00 t); lm_cmd_taper 8.65 t less; lm_cmd_hot 5.11 t more [6.85 t on run A's
pairs]; lm_fixed 0.14 t less; lm_fixed_target 0.35 t less; lm_fixed_r07 5.61 t less;
lm_fixed_hot 7.36 t less; lm_fixed_sled22 0.36 t more; lm_fixed_sealed 1.92 t less. HS:
lm_cmd_hot keeps more than lm_cmd (+5.11 t; uncharged +4.75 t; cost 29.79 against 30.16
t); lm_fixed_hot keeps less than lm_fixed (-7.21 t; uncharged +9.96 t; cost 49.39 against
32.22 t). TS: 0.20 t less (uncharged 1.97 t less). CM: 0.50 t more. SS: 1.77 t less. TP:
8.65 t less; the release flag fires on both (-230 against -897 kPa absolute; swing -1.95
against -4.39 g0), the payload-limit flag does not fire on the taper (it does on lm_cmd).
PL: 5.47 t less. E1 met; E2 met.

**How far each expected reading sits from its threshold** (under the estimates). Within
reach, so not decided by them: LM on lm_fixed (-0.14 t), lm_fixed_target (-0.35 t) and
lm_fixed_sled22 (+0.36 t), TS (-0.20 t) and CM (+0.50 t), all differences between cases at
nearly the same push whose
size is of the order of the spread of run A's measured chord bias across the headline
push's rows (204 to 315 kg, a spread of 111 kg) and of U's interpolation (4 to 330 kg);
the taper's payload-limit flag (its swing 0.054 g0 inside the -2.0 g0 limit) and its
upper-stack flag (0.10% over); lm_cmd_taper's and lm_fixed_hot's distance from no offload
(at x = 0 their equivalent dm lies 432 and 764 kg below the zero crossing of their shifted
curves; their estimates 2.45 and 3.75 t). The rest sit at least about 1.8 t of offload
from their thresholds: RB's nearest to half, lm_cmd_hot (4.41 t below on the placement,
2.36 t on run A's hot ramp); LM and HS differences of 1.9 to 8.7 t; the sealed row's 1.77 t
against lm_fixed.

**What would undercut the hypothesis that every m/s of assist helps**, stated now: a drive
that gains exit speed over silo_cold and still leaves less offload once its structure is
charged, the exit speed read at x* (the central structural case's push at its x*, carrying
its dm, as the CM and SS sentences read it; at x*: expected for lm_fixed_hot, 88.95 m/s,
about 12 m/s more than silo_cold's 76.71 m/s, and about 7.4 t less; lm_fixed within reach,
77.12 m/s and 0.14 t less; lm_fixed_r07 exits faster only uncharged, 79.55 m/s, and at x*
below v_e, 76.59 m/s, so it does not count); a gentler release whose offload cost the model
measures and whose benefit it reports only as flags (expected for lm_cmd_taper: 8.65 t less
than lm_cmd under the estimates, at the same exit speed); a drive that exits slower and
still leaves more offload once charged (expected within reach for lm_fixed_sled22: about
1.9 m/s slower than lm_fixed at x* and +0.50 t; +0.36 t against silo_cold at 1.45 m/s
slower); the payload-limit flag on the linear-motor central cases (expected on seven of the
nine: all but lm_cmd_taper, its release swing 0.054 g0 inside the -2.0 g0 limit, and
lm_cmd_hot, -1.617 g0), with part 1's MECO caveat beside it (the same single-mode instant
step swings the pad's own MECO to -5.195 g0, also beyond the limit, so the flag measures
the model's step treatment as much as the push); every linear-motor row below half of
SP1's 41.26 t (expected).
What would favour it: lm_fixed's faster exit paying for its structure beyond R against
silo_cold_s1_st (within reach), or any linear-motor row above half (not expected).

## 9. Checks that block a citation

A number is not cited in the findings until each check below that touches it passes or is
explained in the note:

- any run or comparison that is bug_suspect (part 1, section 9's list);
- a reference_failed pad, or a pad P* off P_ref (26,054.396243494975 kg) by more than
  0.002 kg;
- a stage-1 pad control that fails its consistency test;
- **the cross-commit check** (design 4.10): file B's silo_cold_s1 off SP1's
  41,262.90803733282 kg, or its silo_cold_s1_st off run A's 11,420.246638573297 kg, by more
  than 0.002 kg: it blocks every number of run B until explained;
- **lm_cmd's uncharged x*** off SP1's 41,262.908 kg by more than 0.25 kg (design 4.10's
  pre-registered equality for a cold start): it blocks every linear-motor number until
  explained;
- a structural case's verification off P_ref by more than 1e-4 P_ref (2.605 kg;
  `offload_verify_mismatch`): the case is flagged and reported as a bound;
- a structural case whose `xv_dry_mass_delta_kg` differs from dm1 + dm2 at x* by more than
  1e-6 kg (a bug);
- a structure file whose sha256 at the run's commit, or as recorded in run B's
  `structure_file` record, differs from part 1, section 12's: it blocks every structural
  number;
- the linear-motor convergence check of section 1 failing (0.1%): it blocks every
  linear-motor number until explained;
- an unexplained `offload_nonmonotone`, a capped gamma* refine, or a fired
  `structure_fixed_point_cap` (explained before the number is quoted);
- a no_offload case reported without its delta-v shortfall and "payload deficit not flown".

File B quotes no band or outer-envelope number, so part 1's frozen-set recomputation does
not block it. Not blocking: the release, upper-stack and payload-limit flags,
`release_speed_not_reached` on an unrecorded evaluation or on lm_fixed_target's variant
run (a stack heavier than M, expected: section 7), and the registered expectations of
section 8 (met or not met).

Reported beside every number, never a gate (exit criterion 7 and part 1, section 9): felt g,
DLF, n_peak, F_peak, dm by stage, x*, the push's electricity, peak mechanical and electrical
power, the facility length with braking, the release position and speed, the control law
and the release trigger, max-Q and peak q-alpha against the pad's, the three structure
flags with their numbers (the payload-limit flag with its MECO comparison), the post-hoc
flight check's exceedance, and on lm_fixed_sealed the column's peak force and work.

## 10. What nothing here measures

Part 1, section 10's list holds for every case of file B, each item with its direction
there (propellant settling after the release step, the transfer tube beyond its hoop,
COPVs, engine mounts loaded in reverse, feedlines, joints and weld lands beyond the NOF,
lateral and bending loads in the shaft, q-alpha bending, drag and the pad release's
dynamic step in the envelope, the unthrottled envelope, fatigue, the payload adapter, a
strengthened vehicle's pad flights, a clean-sheet vehicle, damping, a multi-mode response,
the release step reported and not sized, and SP1's list). Added for the drive, each with
the direction modelling it would move the structural offload, part 1's convention
("against the assist": modelled, it would lower x*; "leaving it out" says which way the
model errs), where known; "no direction" where it touches no x*:

- the motor's thermal and electrical limits beyond P_max (duty cycle, heating, current and
  voltage limits; P_max is a mechanical cap at the carriage and F_max a force cap, nothing
  else): not modelled; direction not known: a further force cap (current, heating) lowers
  the exit speed (U, against the assist) and the plateau force (dm, for it); a further power
  or voltage cap lowers the exit speed only (against the assist); section 7's rows show
  both net signs where the force on the vehicle and the exit speed fall together
  (lm_fixed_sled22 +0.50 t and lm_fixed_sealed -1.77 t against lm_fixed), while more force
  at the same full-load exit costs offload (lm_fixed_r07, 12% more F_max: 5.47 t less);
- the converter and the energy storage: the electricity is the drive work over the
  efficiency 0.5 (assumed), and the storage's losses and the supply of the peak electrical
  power are not modelled; they move energy and power only, never dm or x*;
- the carriage's own structure and its interface hardware: a massless carriage, or the 22 t
  carriage as a lumped mass, never sized; direction not known: under the force law a
  heavier carriage lowers the vehicle's force and its exit speed together (CM's 22 t
  estimate: +0.50 t against lm_fixed, within reach, section 8); under the acceleration law
  it reaches the vehicle only once a cap binds; interface hardware carried by the vehicle
  would add to dm (against the assist);
- the shaft flow above the vehicle and the gas in the sealed shaft: the air the vehicle
  pushes out of the mouth (design 4.8: about 77 kN at the exit for a 3.7 m bore, the bore
  D-SP7-54 found the fairing cannot pass; a momentum flux of the order of rho v^2 A_bore,
  docs/physics.md, "The sealed shaft", so at the 5.24 m a real shaft for this vehicle needs
  it is larger, of the order of the area ratio, about 2: inferred, not computed; acting on
  the vehicle against its motion, as shaft drag would: against the assist); the cooling of
  the trapped gas near the end of a small-gap stroke on lm_fixed_sealed (the uniform
  adiabat is first order there and biases F_p low, docs/physics.md, "The sealed shaft":
  against the assist, inferred; heat from the walls would act the other way; the p_0 A
  bound holds regardless); the open shaft's hydrostatic drop above the carriage on
  lm_fixed_sealed (F_p biased high by up to rho g s A, about 1.2% of F_p(L), about 26 kN
  at the 5.24 m bore, docs/physics.md, "The sealed shaft": for the assist, inferred from
  the sealed row's sign; leaving it out is conservative); and the vents a vented shaft
  needs (about the bore's area; the vented variants assume them, and smaller vents would
  leave a column force on the vehicle: against the assist);
- the release mechanism: every release is an instant separation (the release flag states
  what the single-mode treatment does with it); lm_cmd_taper flies one way to soften it (its
  effect on the release shows only in the flags; no release step is sized), and no release
  hardware is sized (direction not known);
- the carriage's braking: closed-form functions at a constant 5 g0 (D-SP7-12), setting only
  the facility length; no braking phase in the trace (no direction: it touches no x*);
- the exhaust in the shaft for the two hot starts (SP1's caveat: back-pressure, heating,
  the carriage in the plume; it favours the hot starts); under the force law the whole
  thrust adds to F_max (impingement 0), which raises lm_fixed_hot's felt load and dm;
- **KI-067, with its direction**: a hot linear-motor push lit before its push start (a hot
  hold) has its F_int taken at rest at push start although the startup ramp on the clamp
  was still lowering it by about T; a single mode started at ignition exceeds the charged
  F_peak by up to 0.456 MN (2.3%) in the 2-10 Hz band (S4b's probe: 20 t carriage,
  impingement 0.5): charged, it would raise such hot cases' dm (against the assist;
  leaving it out is unconservative). Read against file B (section 6, item 11): neither hot
  start holds on the clamp (no hold phase; the delivered thrust is 0 at push start, so
  F_rest = m_v g_eff exactly; lm_cmd_hot is lit 0.849 s into its push, lm_fixed_hot at
  push start), so the at-rest premise is exact for both and this bias does not reach them;
  their thrust ramps are flown on the track and charged as forcings of F_int's mode (the
  convention's other side, docs/physics.md, "The flown push of a linear motor").

The known issues of steps S4 to S5a (TODO.md KI-045 to KI-087), each read against file B's
settings. Those that reach file B, with their direction in the same sense:

- KI-048 (the scan for a watch value passed over inside one step assumes one extremum per
  step and watch; a binding inside its zero band is not flown as a sub-phase; drive_limit is
  not scanned): every linear-motor push; on lm_fixed_target the power limit and the release
  coincide at v_e (section 5, check 3). Direction not known; size at the scan's resolution.
- KI-049 (the delivered-thrust clamp unsplit in ascent burns lit after release and in
  constant_accel's push): every cold variant's ascent (silo_cold and the seven cold
  linear-motor variants: stage 1 lit 0.5 s after release, its 2 s ramp crossing p_amb A_e
  in the ascent), at about the 1e-10 level, as in SP1 and run A; no push of file B, since
  silo_cold's is cold (no engine runs on it) and S4 splits the clamp on the linear motor's
  (the two hot starts' ramps lie on their pushes: lm_cmd_hot's ends at the release,
  lm_fixed_hot's on the track, 2 s into a push of about 2.5 to 2.6 s at the estimates, so
  their ascents start at full thrust; stage 2 starts by a step). Direction not known.
- KI-070 (the flown history's single-mode bound is phase-free and counts a curving load to
  first order): the bound is conservative, 0.002-0.006 g0 on n_peak on an
  lm_fixed_r07-like push (S4b's measure), so it may raise the charged load slightly where
  the bound governs (at the estimates lm_fixed, lm_fixed_r07 and lm_fixed_sealed, whose
  bound exceeds the rise formula by 0.0002, 0.0026 and 0.013 g0 on n_peak, the most KI-070
  can add there; on lm_fixed_hot the rise formula governs, 5.899 against the bound's 5.774
  g0, and on lm_fixed_target, lm_fixed_sled22 and the lm_cmd family the two agree); a
  second-order count would lower it (for the assist; leaving it out is conservative). Its
  release bound, the most conservative part (0.11-1.81 g0 beyond the oracle's swing,
  TODO.md), sets the charged release swing on lm_cmd_taper, lm_fixed, lm_fixed_r07,
  lm_fixed_hot and lm_fixed_sealed at the estimates, 0.01 to 0.18 g0 beyond the rise
  formula's (-1.946 against -1.926, -4.504 against -4.404, -3.766 against -3.586, -2.662
  against -2.650 and -4.054 against -4.009 g0); on the other four the two agree. It moves
  no x* (the swing enters only the flags), and no expected flag state depends on it: each
  flagged case's formula swing also lies beyond -2.0 g0, and the taper's lies inside
  either way. It overstates the swings that TP and the payload-limit flag read, and the
  release flag's LOX-bottom pressures with them (conservative for the flags; in TP it
  deepens the taper's swing by 0.02 g0 and not lm_cmd's, so it understates the gentle
  stop's gain).
- KI-071 (the bound depends on the scan resolution at a corner; dm(x) can step by about 1%
  of the load where a corner crosses a sub-phase start): the force-law variants whose power
  corner moves with the offload (lm_fixed, lm_fixed_r07, lm_fixed_hot, lm_fixed_sled22;
  lm_fixed_target's corner is its release). A step in dm(x) would show as a kink in m_res(x)
  or an `offload_nonmonotone` (section 9); the convergence check exercises it on lm_fixed.
  Direction not known.
- KI-074 (on linear-motor runs the minima, `drive_force_peak_N` and the track-normal peaks
  stay sampled): every linear-motor run's reported drive-force peak is read at the sample
  spacing, so the sampled peaks read low (the felt-g and interface-force maxima are exact).
  No direction: no x* depends on them.
- KI-076 (a sealed bore is checked only against the body diameter): lm_fixed_sealed's bore
  is set to clear the 5.2 m fairing by D-SP7-54 (section 6, item 7), not by the code's
  check. No direction on file B's numbers.
- KI-047 (near-duplicate `drive_cap` and `power_limit` rows when the caps meet) and KI-057
  (the cap record carries no timing): the lm_cmd family only if a cap binds (E2 expects
  none). No direction: records only.
- KI-053, KI-058, KI-081, KI-082, KI-083 and KI-084 (the scene template brakes the drawn
  carriage from the stroke's end, two video-frame fits, the display file's vented-shaft
  note, two manual gaps): the readers' pages and documents of run B (lm_fixed_target's
  early release, lm_fixed_sealed's pages), never its numbers. No direction.

Those that do not reach file B, each with the setting that keeps it out: KI-050, KI-059 and
KI-063 (a stalled, stopped or unmoved push: no push stalls, each F_max being 2.9 to 5.2
times the full-load stack's weight, the column and the carriage included); KI-054 (a kick
begun inside the shaft: lm_fixed_target releases at most about 14 m below the mouth on the
stacks the solves fly (85.74 m at x = 64 t, the high end of the uncharged solve's bracket
[32, 64] t, reached by doubling from hint 0; 86.60 m at 60 t) and lights stage 1 0.5 s
later, about 37 m higher, above the mouth); KI-055 (every track angle is written); KI-056
(file B is sweep-optimized); KI-060 (every brake is 5 g0); KI-061 (v_k 50 m/s); KI-062,
KI-064 and KI-065 (no fall back is expected, and the file is planar); KI-066, KI-085 and
KI-087 (no buried exit: every exit is at the mouth); KI-067 (no hold, above); KI-068 (no
release in tension: without a carriage F_int equals the drive force, less F_p on
lm_fixed_sealed, about 20.3 MN at L and still compressive, and the 22 t carriage is a cold
start); KI-069 (silo_cold is cold); KI-072 (no payload case); KI-073 (no acceleration-law
push comes near drive_limit: lm_cmd_hot's drive force at full vacuum thrust stays positive
on every stack up to 60 t of offload carrying no dm, the lighter first iterate KI-073
concerns: 14.15 MN at the full load, 11.79 MN at 60 t, zero only beyond an offload of 360
t; lm_cmd and lm_cmd_taper carry no thrust on the track); KI-078 (the sealed variant is
cold and released at L); KI-080 (the sealed variant has no release speed); KI-086
(impingement 0 everywhere). Closed: KI-045, KI-046, KI-052, KI-077 and KI-079. Not about a
run: KI-051 (a test flake) and KI-075 (a test-map name).

## 11. Runtime estimate

The design's budget: about 18 min at SP1's measured rates (survey 09's set M). Re-estimated
from S7a's measured rates: run A took 64.8 min against part 1's 59 min at the checkpoint's
rate and run C 5.6 against 5.1 min, both about 1.10 times, so S7a's machine ran a searched
run S in about 51 s, a verified solve V in 89 s, a structural verified solve V_s in 102 s,
a pad control C1 in 33 s and a directory with plots in about 2 s. Run B holds 11 S (the pad
and the ten variants), one C1, 10 V (the uncharged cases), 10 V_s (the structural cases)
and about 32 directories, plus the push flown in every sizing of the nine linear-motor
structural solves (S4b: a transform call about 0.15 s, 0.38 s under sustained load; about
40 evaluations per solve: 1 to 2.5 min in all) and the linear-motor flights' sub-phases (a
linear-motor variant's payload search has not been timed on the gate vehicle).

| Rates | Run B |
|---|---|
| SP1's set M (S 23, V 40, V_s 46, C1 15 s) | about 20 min (the design's 18) |
| S7a's measured (S 51, V 89, V_s 102, C1 33 s) | about 44-45 min |
| SP1's pessimistic set P (S 55, V 110, V_s 127, C1 30 s) | about 54 min |

All below D-SP1-17's 90-minute threshold, so nothing is trimmed. Arms on one structural case
(section 6, item 4) would add six arm pads and six arm solves, about 12 min at S7a's rates.
The convergence check of section 1 runs afterwards, not beside: two pad searches and two
structural solves with their verification, about 5-10 min (part 1's took 277.5 s on file
A).

## 12. Provenance

- The structure files are frozen at SP7 step S2's commit 45e39d4 (D-SP7-31): `git diff
  --quiet 45e39d4 HEAD -- configs/structures/` holds at this note's tree. File B names
  configs/structures/generic_f9_class_2d.yaml, sha256
  a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232 (part 1, section 12; the
  README-loads fork's file, a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997,
  is not used here; tests/test_config_planar.py pins both digests and checks file B's
  structure block against the first).
- The vehicle file configs/vehicles/generic_f9_class_2d.yaml, sha256
  a8ea5203da658b6d86d690ea26b784fa6004f2b990fe2f4b7f829c9a799e59a9, is unchanged since
  SP7's start commit 22c62e9, with the rest of configs/vehicles/ and the seven shipped
  experiment files; files A and C are unchanged since their registration commit cbbd7bc.
- The rule values come from docs/findings/scripts/sp7_drive_rules.py, committed with this
  note; the checks of section 5 and the estimates of section 7 from scratch scripts kept
  outside the repository, run on 2026-11-03 at HEAD c99c683 with this step's uncommitted
  files (no change under src/ or configs/), on the pad flown afresh once (40.6 s; P*
  26,054.396243494975 kg, SP1's bits); no offload of any case of file B was solved. The
  review's regeneration of the rule values through units.py moved seven power_max_MW values
  by one ulp (lm_cmd_taper's, lm_fixed_r07's and the five lm_fixed values); checks (2) to
  (4) and the estimates were flown again on the values as written here, and the numbers
  above are those flights': only check 3's lm_fixed full-load exit (in its last two digits)
  and its event logs at the corner tie moved; every other number is unchanged at its
  printed precision. The review then corrected section 7's early-release rule (the flight
  lowered by d, priced by SP1's ignition-delay offloads, in place of U at the
  mouth-equivalent speed, which had placed lm_fixed_target's U 0.60 t and its x* 65 kg low)
  and re-estimated lm_fixed_target's row on the same pad and values, with its readings in
  sections 3 and 8; no other row moved, since no other case releases below the mouth. A
  later review priced that altitude worth consistently (each delay point at its own
  ignition speed: 5.2 to 5.5 kg per m); the row keeps its 6.0 kg per m estimate, with the
  bias (U about 5 to 8 kg low, x* under 1 kg low) stated in section 7.
- This note's commit, with file B, the rules script, the test changes and docs/physics.md's
  table row, section and test-map rows, is the pre-registration commit. S7b runs from it or
  from a later clean commit that changes no code (src/, configs/, experiments/,
  pyproject.toml, uv.lock).

