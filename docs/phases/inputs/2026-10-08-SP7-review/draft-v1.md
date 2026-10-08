<!-- Record: SP7 design draft v1 as reviewed on 2026-10-08 (superseded by ../2026-10-08-SP7-design.md, version 2, which the user approved). Not edited. -->

# SP7 design: the structural mass of the push load, and a force-limited drive (draft v1, for review)

Draft v1, 2026-10-08, written in SP7 step 0 at HEAD 22c62e9 ("Close SP2: trackers, handoff,
next phase file"; clean tree). Line numbers are for that commit. Sources: the brief
(docs/phases/SP7-structural-mass-push-load.md) and nine read-only surveys made at 22c62e9
(to be saved as docs/phases/inputs/2026-10-08-SP7-survey/01..09; cited below as S01..S09).
Every number marked "probe" comes from S08's labelled planning probe with placeholder
coefficients: it sizes the problem for the plan, it is not a finding and not a target, and it
is disclosed in the pre-registration (step S6).

## 1. Context

SP1's headline: at the pad's payload P_ref = 26,054.396 kg and the 200 km orbit, the 3 g0,
100 m cold-start silo lets the gate vehicle leave out 41,262.908 kg of stage-1 propellant
(10.04% of stage 1), before any structural mass; assumed +2, +4, +8.1 t of stage-1 dry mass
leave 32.285, 22.876, 1.980 t (RQ1). SP7 charges a modelled structural mass for the push with
an uncertainty band, beside those rows, and builds the linear motor, carriage mass, release
at a target speed, braking functions and a sealed-shaft air column. The answer may undercut
the hypothesis; it is reported as plainly as any other.

What the surveys established that the design rests on:

- **Construction is public** (S06, SpaceX Falcon 9 User's Guide Rev 2 2015 Table 2-1 and
  section 2.2; Falcon User's Guide 2025): Al-Li skin, friction-stir welded; **LOX tank on top,
  monocoque; RP-1 tank below, skin and stringer; an insulated common dome between them**; a
  LOX transfer tube through the RP-1 tank; a composite interstage; 3.66 m; structural factor
  of safety 1.4. Tank pressures, dome shape, tank lengths and a dry-mass breakdown are not
  public (only the Merlin 1D at 470 kg, quoted).
- **Where the push exceeds the pad's own envelope** (S05, from the recorded pad and
  silo_cold_s1 time series): the upper (LOX) barrel in compression is inside it (push n U =
  0.77 of MECO's 7.095 MN); the RP-1 barrel in compression carries n (U + LOX) at 2.20 (offloaded
  headline) to 2.37 (full load) times the envelope (MECO); the aft structure 2.6-2.9 times; the
  tank-bottom hydrostatic heads 2.6-3.0 times (liftoff). The push's 3.996 g0 is below MECO's
  5.195 g0, so stage 2 and the interstage are not sized by a quasi-static push.
- **Magnitude** (probe, S08): a quasi-static first-order increment of 1.4-3.5 t in the tanks,
  plus 0.4-2.1 t of load-entry hardware at 20-100 kg/MN of interface force; placed on SP1's
  penalty curve, 12-33 t of offload (30-80% of the headline). The two largest drivers are the
  dynamic load factor (DLF) and the load-entry coefficient, then the buckling form; allowables,
  factor of safety and ullage pressure move dm by 0.2-0.4 t each. No probed case keeps the full
  41 t.
- **A power limit cannot lower the load** (S01, S07): at a fixed stroke and exit speed,
  constant force is the minimum-peak profile; r = P_max/(F_max v_exit) < 1 raises the felt g
  (5.8 g0 at r = 0.5). The linear motor's structural relief comes only from a longer stroke or
  a lower exit speed. A force rise time of 0.5-1 s costs +0.2-0.9% of F_max at the same exit
  speed and brings the DLF from 2 to about 1.0-1.2.
- **Code seams** (S01-S04): the drive seam (`AssistModel.state_rate`) takes a new drive
  without touching the planners; a vehicle transform inside `OffloadProblem.vehicle_at`
  reproduces SP1's +2 t row bit for bit and keeps SP1's path unchanged when off (S03);
  resolved dicts are raw merged YAML, so new fields on new models move no digest (S02); the
  1-D golden tier can never be recaptured, so every new key, column, assumption line or
  summary row must appear only on runs that use the new features (S01).

## 2. Start checklist (done, 2026-10-08)

- Tree clean; HEAD 22c62e9 "Close SP2: trackers, handoff, next phase file"; the closing commit
  3a1b243 is an ancestor; `git diff --stat 3a1b243 HEAD` touches CLAUDE.md, README.md, TODO.md,
  docs/ (18 files) and site/ (5 files) only.
- Fast suite: 1678 passed, 41 deselected in 188.72 s. Ruff: all checks passed; 109 files
  already formatted.
- Pins: the exact golden tier (LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1), the planar digest pin and the
  planar output capture: 123 passed. Slow entry tests: tests/test_silo_screening_record.py (pad
  and silo_cold P* within 0.002 kg of 26,054.3962 and 27,553.2271 kg) and
  tests/test_offload.py::test_gate_silo_offload_recorded_run_and_verification: 3 passed in
  103.7 s.
- SP1's run data on disk: results/silo_offload_2d/20261003T112934Z (19 run folders with CSVs)
  and 20261003T112949Z (5 sweeps).
- Inventory drift: `git diff --stat 705025f HEAD -- src tests configs experiments
  pyproject.toml uv.lock site/build.py` is empty; section 6 of the brief holds at HEAD, with the
  corrections listed in section 9 of this design.
- `gh` authenticated; Pages run 37732568686 green.
- App basis: experiments/silo_offload_2d.yaml and the gate vehicle unchanged since b3150c1
  (S04: `sp1_files_same` true).
- Open items owned by SP7: B-004, B-005, KI-030, KI-039. Falling to SP7 by their owner rules:
  KI-036 (S3a edits replay.py), KI-038 (S4a edits scene.py), KI-035 (S1 edits
  tests/test_scene.py), KI-021/KI-022/KI-023 (S4 edits tests/test_config.py and
  tests/test_silo.py). Re-targeted by this design: B-007's braking, air column and
  target-speed release (friction stays later). KI-032 stays "later" (no SP7 step touches that
  metric).

## 3. Decisions

### 3.1 The user's answers (2026-10-08, step 0)

| Id | Question | Answer |
|---|---|---|
| D-SP7-01 | Q1 model fidelity | B: first-order station sizing (closed forms per tank, the domes, the aft skirt, the load-entry ring and interface hardware by coefficient); FEM not taken |
| D-SP7-02 | Q2 sizing basis | the offloaded stack actually flown (re-sized at each x), with a full-load-sizing bound row |
| D-SP7-03 | Q3 existing margin | zero (the existing structure exactly meets the pad envelope), with 10% and 25% margin rows |
| D-SP7-04 | Q4 drive scope | linear motor, carriage mass, release at a target speed in; braking and the sealed-shaft air column in but first to cut; curved track and cable winch out |
| D-SP7-05 | Q5 load entry | an aft ring at the stage base (central), with a row through the thrust structure |
| D-SP7-06 | Q6 findings | a new note docs/findings/RQ1-structural-2d.md and a dated pointer section at the top of RQ1; RQ1's record kept |
| D-SP7-07 | Q7 dynamic load factor | charged from a stated force rise time and an assumed axial period (for constant_accel, an assumed real-drive rise time from the structure file); the quasi-static value beside; the step (factor 2) as a bound row |
| D-SP7-08 | App form | no change in SP7; a modelled-structure switch and a linear-motor launch in the form go to the backlog (B-016) |

### 3.2 Design decisions (approved with the plan)

| Id | Decision | Reason |
|---|---|---|
| D-SP7-09 | Stage-1 layout from SpaceX's guides: load ring at the base, aft skirt, RP-1 tank (skin and stringer), common dome, LOX tank (monocoque), forward dome, interstage (not sized). Barrel lengths from the propellant volumes at densified densities plus an ullage fraction; everything not public `assumed: true` | The only public construction facts; S06 |
| D-SP7-10 | Station sizing by max of modes, increment = sum of the positive parts over the pad envelope (section 4.2) | Zero inside the envelope by construction; every term a closed form |
| D-SP7-11 | The envelope is the pad baseline's own recorded flight (HOLD and stage-1 flight, drag included), quasi-static | Built from the model's own records (Q3); a DLF on the pad's release step would raise the envelope and favour the assist, so it is left out and said to be conservative |
| D-SP7-12 | DLF on the increment over the resting load, envelope bound min(2, 1 + T/(pi t_r)); T from an assumed first axial frequency; t_r the drive's own or, for constant_accel, the structure file's rule value t_r = 10 T_low / pi (DLF <= 1.10 at the lowest assumed frequency) | Q7; the exact sinc drops to 1 at integer t_r/T, so using it on an uncertain T would be tuning (S08); the rule keeps the ramp's own cost under 1% of F_max (S07) |
| D-SP7-13 | Release unloading and an upper-stack exceedance are reported as flags with numbers, not sized | Both are dynamic or out-of-model; sizing them needs a structural-dynamics model (out of scope) |
| D-SP7-14 | Load entry, central: aft skirt in closed form plus ring and vehicle-side hardware at k_entry x F_peak; row B: a thrust structure sized by its mass-estimating relation, scaled by F_peak / T_max | Q5; no source sizes a push ring (S06), so k_entry is assumed with anchors stated |
| D-SP7-15 | Coefficient band: every coefficient has a range (sourced or assumed); the low-mass and high-mass sets are the corners of those ranges that minimise and maximise dm at SP1's headline push, found by the sizing model alone in S2 and frozen in the structure file before any flight; a one-at-a-time tornado beside | The direction of a coefficient's effect flips with the buckling form (S08), so sets cannot be picked per coefficient; a corner band is a stated bound, not a confidence interval |
| D-SP7-16 | Coupling: an optional vehicle transform on `OffloadProblem`, applied inside `vehicle_at`; it flies the push of the vehicle at x and P_ref with fixed settings and iterates dm to a fixed tolerance | S03: one place, `offloaded_vehicle`, `record` and `verify_offload` all see dm, no double application; SP1's path unchanged when off |
| D-SP7-17 | Switch and file: an optional `structure:` field on offload cases and an experiment-level `structure:` block (the file, payload cases); configs/structures/<vehicle>.yaml read by cli and passed to `resolve_experiment` as a loader; recorded in resolved_config.yaml; refused with `stage1_dry_mass_added_t` and with `paired_pad` | S02: moves no shipped resolved dict; config.py stays free of I/O; the refusals follow config.py 1659-1664's reasoning |
| D-SP7-18 | The modelled mass has its own record keys and a three-way wording branch (uncharged, assumed penalty, modelled) at every source; never written into `stage1_dry_mass_added_kg`; program-level claims ("no structural model exists") reworded at the close, when the note exists | S04: one reader (`replay.penalty_added_kg`) decides "penalty row" for every page |
| D-SP7-19 | KI-039: imposed cases get their own sub-section and one-line basis; solved cases keep "Propellant saved at fixed payload"; the basis constant covers solved cases only; the app banner's imposed disclaimer is dropped | S04: about 30 places point at the heading; a split keeps them valid |
| D-SP7-20 | Linear motor: P_max is the mechanical limit at the carriage (efficiency energy-only, electrical peak = P_max/eta reported); force ramps from the holding force over t_r; release at s = L or at `release_speed_mps`; a stall at push start and a release-referenced ignition with t_ign_s < 0 are refused; F_max and P_max by a rule stated before any run (section 4.10) | S01, S07 |
| D-SP7-21 | Braking: closed-form functions of the drive at a constant total deceleration; facility = max(L, s_release + d_brake); no trace phase, no force-speed brake law | No source gives a brake law for a heavy carriage (S07); the RunTrace is sequential (S01) |
| D-SP7-22 | Air column: `shaft: sealed` on linear_motor only; adiabatic trapped column below the carriage; the force acts on the carriage; a `W_other_J` state and a `work_other` budget term | S01, S07; constant_accel's vented shaft and its assumption text stay byte-identical |
| D-SP7-23 | KI-030: strict and finite per field on the existing models plus range bounds (t_ign_s within +/-3600 s; exit_altitude_m within +/-500 m); no resolved dict changes; tests/test_config.py 389 updated | S02 measured: 12 of 16 cases closed by strictness, 4 need bounds; whole-model strictness refuses every planar file |
| D-SP7-24 | Experiments in three new files (structure, drive, bridge); experiments/silo_offload_2d.yaml unchanged, so the app's basis and its reproduction mark stay; four commands in parallel from a clean commit | S04, S09 |
| D-SP7-25 | SP1's headline and penalty rows pinned from its metrics.json into tests/data/silo_offload_2d_record.json; slow pins at <= 0.002 kg for the structure-off headline and the constant-2 t cross-check | S03: no test pins x* today; same code and P_ref give the same bits |
| D-SP7-26 | Test hygiene with the steps that touch the files: the docstring check fails on a missing module path and lists the phases files; KI-035's import check split fast/slow; KI-021-023 docstrings | S09 |

Not taken: FEM (Q1 C); a parametric fraction (Q1 A); a modelled braking phase in the trace; a
force-speed brake law; any app form change; editing a shipped experiment or vehicle file;
KI-032.

## 4. Design

### 4.1 Files

| File | Change |
|---|---|
| `src/launchsim/structure.py` (new, pure) | closed-form sizing primitives; the station model; load cases from a flown push or a Result; the envelope; the increment; DLF; flags; the corner search and tornado (sizing only) |
| `src/launchsim/assist/linear_motor.py` (new, pure) | `LinearMotorAssist` behind `AssistModel`; the ramp, limits, braking functions, sealed-shaft force |
| `src/launchsim/assist/base.py`, `assist/__init__.py`, `assist/constant_accel.py`, `assist/none.py` | backward-compatible protocol members (mass-aware push time, model kink times, release speed, extra work quadrature name); registry entry; existing models return today's values |
| `src/launchsim/config.py` | `LinearMotorConfig`; `StructureConfig` and its range quantity; the offload case's `structure` field; the experiment-level `structure` block; a keyword-only `load_structure` on `resolve_experiment`; KI-030 validators; `PLANNED_MODELS = ("cable_winch",)`; one tuple of union tags |
| `src/launchsim/units.py`, `compare.py` | `mw_to_w`; the `MW` suffix row; `ENERGY_ONLY_ASSIST_KEYS` gains linear_motor's `drive_efficiency` |
| `src/launchsim/dynamics.py`, `phases/prelude.py`, `phases/engine.py`, `losses.py` | the target-speed release event and the release position in `TrackExit`; model kink times merged into the sub-phase boundaries; the extra work quadrature; `AssistEnergyBudget.work_other` (default 0) |
| `src/launchsim/offload.py` | the optional vehicle transform (about five lines) |
| `src/launchsim/sim.py`, `results_io.py` | building the transform; the structural payload case; restating dm(x*) in the verified dict; memo keys; record keys; `structure_inputs`; assumption lines |
| `src/launchsim/summary.py`, `metrics.py`, `metrics_planar.py`, `plots.py` | the Structure subsection; conditional linear-motor metrics and rows; the thickness-profile figure |
| `src/launchsim/replay.py`, `scene.py`, `app.py` | three-way structure wording; the linear-motor drive clause; no derived constant acceleration for another drive; KI-036; KI-038 |
| `src/launchsim/cli.py` | reading the structure file next to the vehicle loader |
| `configs/structures/generic_f9_class_2d.yaml`, `generic_f9_class_2d_readme_loads.yaml` (new) | coefficients with ranges, layout, breakdown, the frozen sets; every number sourced or `assumed: true` |
| `experiments/silo_structure_2d.yaml`, `silo_drive_2d.yaml`, `silo_structure_2d_readme.yaml` (new) | section 4.10 |
| `tests/` | `test_structure.py`, `test_linear_motor.py`, `test_structure_pipeline.py` (new); the pinned wording tests; `tests/data/silo_offload_2d_record.json` (new) |
| `docs/physics.md` | sections for each new piece, assumptions, test-map rows, SP7 research notes |
| docs/findings, README, manual, site | at S7 and the close |

Unchanged, byte for byte: every shipped experiment and vehicle file; `templates/replay.html`;
`ConstantAccelConfig`'s fields, `ConstantAccelAssist`'s integration, assumptions, metric keys
and time-series columns; the RunTrace phase sequence of every existing run; the six gallery
pages (regenerated byte-identical, section 4.5).

### 4.2 The structural model (structure.py)

**Stations.** z runs up from the load ring at the stage base. Elements, bottom to top: aft
skirt (length L_s, assumed), RP-1 aft dome, RP-1 barrel, common dome, LOX barrel, LOX forward
dome, interstage (mass only). Barrel lengths: propellant volume m/rho, plus an ullage fraction,
over A = pi r^2 (cylinder-equivalent; dome volumes neglected, stated). A barrel is cut into N
stations (N fixed in the file; a test shows doubling N moves dm by < 0.1 kg).

**Load case.** One sample c of a flight: felt axial load factor n (g0), drag D, the stage-1
propellant on board split into LOX and RP-1 at the structure file's mixture ratio, the upper
stack U (stage 2 wet + fairing + payload flown), the interface force F_int (push only), the
thrust T, the phase (HOLD, ASSIST or flight). The liquid surface of a tank is at m/(rho A) above
its bottom; the head at station z is h = max(0, surface - z).

**Station loads** (free body above a cut; the liquid of the tank whose wall is cut loads its
bottom dome, not the wall above it; S05, S06):
- LOX barrel: N(z) = (U + m_struct,above(z)) n g0 + D;
- RP-1 barrel: N(z) = (U + m_struct,above(z) + m_LOX) n g0 + D;
- aft skirt: N = the load through the base (push: F_int; pad: the hold-down support, section 4.2.3);
- pressure at a barrel station: p(z) = p_u + rho n g0 h(z).
m_struct,above comes from the structure file's breakdown (interstage, LOX tank, common dome),
not from the sized thicknesses; the increment's own inertia is not added to the loads (stated;
about 0.3% of dm).

**Modes and required thickness** (FS_u the ultimate factor, F_tu the ultimate strength,
eta_w the weld efficiency, relief at the minimum expected ullage pressure and unfactored,
NASA-STD-5001B FSR 19 and 53-54):
- hoop (barrels): t_h = FS_u p(z) r / (F_tu eta_w);
- compression, net design load N_d = FS_u N(z) - p_u,min pi r^2 (no requirement if N_d <= 0):
  - monocoque (LOX barrel): smallest t with 2 pi E t^2 (gamma(t)/sqrt(3(1 - nu^2)) +
    Delta_gamma(p, t)) >= N_d, gamma = 1 - 0.901 (1 - exp(-sqrt(r/t)/16)) (SP-8007 1968 Eq. 5;
    2020 Eq. 9-10), Delta_gamma from the digitized SP-8007 Fig. 6 / Fig. 4-5 curve against
    (p/E)(r/t)^2 (2020 Eq. 48-49), times a coefficient s_dg in [0, 1];
  - stiffened (RP-1 barrel, aft skirt): smeared t_bar = (d/4) C (N_x/(k_s E d))^n with
    N_x = N_d/(2 pi r), k_s the stiffened knockdown (0.65, SP-8007-2020) and (C, n) from Gerard
    & Lakshmikantham 1966 Table 2 (ring + common Z: 6.48, 3/5);
- minimum gauge t_min.

t(z, c) = max of the modes and t_min. Domes are membranes sized at their crown: t =
FS_u p_net r k_d / (F_tu eta_w), with k_d = (a/b)/2 for a spheroid of axis ratio a/b, area from
the spheroid formula; RP-1 aft dome: p_net = p_u,RP1 + rho_RP1 n g0 H_RP1; common dome (LOX side
concave, in tension, assumed): p_net = FS_u (p_u,LOX + rho_LOX n g0 H_LOX) - p_u,RP1,min, the
relieving side unfactored; forward dome: ullage only, unchanged by the push.

**Envelope and increment.** t_env(z) = (1 + margin) max over the pad's load cases of t(z, c);
t_push(z) = max over the push samples of t(z, c) at n_peak. Increment of an element:
Delta_m = NOF sum over stations of 2 pi r rho_w Delta_z max(0, t_push - t_env) (domes: area x
rho_w x the positive part). Zero inside the envelope, exactly, by construction (a test: the
pad's own cases give 0.000 kg).

**4.2.1 Dynamic load factor.** n_peak = n_0 + DLF (n - n_0) and F_peak = F_0 + DLF (F_int - F_0),
with n_0 and F_0 the resting values before the push (g_eff/g0 and m_v g_eff for a cold push;
the hold's for a hot one). DLF by the case's `dynamic` setting: `rise_time` (central)
min(2, 1 + T/(pi t_r)), T = 1/f; `quasi_static` 1; `step` 2. The hydrostatic heads use n_peak.
Damping is not credited (conservative by at most 4.5% against 1-3% damping, S07).

**4.2.2 Flags (reported, not sized).**
- `structure_upper_stack_exceeded`: n_peak above the pad's maximum n at the full upper stack
  (MECO, 5.195 g0): stage 2, the interstage and the payload adapter would also need
  strengthening, which the model does not size; dm is then a lower bound. Happens for DLF >
  1.40 at 3 g0 net and for the 50 m stroke (7.0 g0) quasi-statically (S08).
- `structure_release_unload`: the release drops the load from n_rel to n_after in one step (no
  ramp-down is modelled for any drive); with DLF 2 the tank-bottom pressure swings to
  p_u + rho g0 H (n_after - (n_rel - n_after)); a negative absolute value means the liquid
  column would separate from the dome (probe: -0.53 MPa at the LOX bottom). Reported with the
  numbers.

**4.2.3 Load entry (Q5).** Central `aft_ring`: the aft skirt as a stiffened element whose
envelope is the pad's hold-down support (5.593 MN at full load, compression, from the HOLD rows;
S05) and whose push load is F_peak; plus the ring and vehicle-side hardware at k_entry x F_peak
(new hardware, all charged; no envelope credit). Row `thrust_structure`: the push enters
through the thrust structure; Delta_m = m_ts max(0, F_peak/T_max - 1), m_ts = k_ts T_max with
k_ts from the thrust-structure mass-estimating relations (S06: 0.20-0.36 kg/kN; central 0.255)
and T_max = 8,227 kN; the aft skirt is then not loaded by the push. k_entry: assumed, anchored
low by a continuous annular seat (a light bearing ring), high by the thrust-structure relation
(a structure that gathers discrete loads the way the octaweb gathers engine loads), central by
the order of hold-down hardpoint structure per unit load; values fixed in S0.

**4.2.4 Plausibility (labelled calibration, not validation).** The model's envelope masses
(barrels, domes, skirt, x NOF) beside Heineman's tank relation (S06, +/-30%), the interstage and
thrust-structure relations and the 22.2 t stage-1 dry mass less the engines. Reported in the
structure inputs; it changes no coefficient.

**4.2.5 The band.** Each coefficient carries (low, central, high), sourced or assumed: E, nu,
rho_w, F_tu, eta_w, FS_u, p_u,LOX, p_u,RP1 (with p_u,min), s_dg, k_s, (C, n), NOF, t_min, L_s,
a/b, k_entry, k_ts, the axial frequency f, the densities, the ullage fraction. The **central
set** takes every central value. The **low-mass** and **high-mass** sets are the corners of the
ranges that minimise and maximise dm at SP1's headline push (constant_accel 3 g0, 100 m, cold,
x = 41,262.908 kg, P_ref), found by an exhaustive corner search of the sizing model (2^k
evaluations, closed form, seconds) in S2 and written into the structure file with the commit
that computed them, before any flight. A one-at-a-time tornado (each coefficient at its low and
high, the rest central) is written beside. The band is labelled "the bounds of the stated
coefficient ranges, all at once; not a confidence interval".

### 4.3 The structure file and its configuration

`configs/structures/<vehicle>.yaml`, one per vehicle an SP7 experiment flies (the gate vehicle;
the README-loads fork for the bridge), never a calibrated vehicle file (S04 section 9: a vehicle
fork would lose its calibration record). Model `StructureConfig` in config.py (CLAUDE.md puts
YAML models there; no I/O): `name`, `applies_to` (vehicle names, non-empty, no repeats, as
configs/display/ does), `layout` (tank order, the common dome, per-element construction,
radius, aft skirt length, dome axis ratio, ullage fraction, stations), `mixture` (stage-1 LOX
mass fraction), `materials`, `factors`, `buckling` (the Delta_gamma table, stiffened
knockdown, Gerard C and n), `pressures`, `densities`, `nof`, `load_entry` (k_entry, k_ts),
`dynamics` (axial frequency, the constant_accel rise-time rule), `breakdown` (stage-1 dry mass
by element, for the station loads and the plausibility check), and `sets` (the frozen low-mass
and high-mass corner choices with the commit that computed them). Every number is a range
quantity `{central, low, high, source | assumed: true, note}` (low <= central <= high, finite,
signs bounded by the field), or a `Quantity` where no range applies; field names avoid the
assist and ignition family names (tests/test_config.py 662-690). Loading: `cli.load_experiment`
reads the file named by the experiment's `structure.file` and passes it to `resolve_experiment`
as a keyword-only `load_structure` (the `VehicleLoader` pattern, so the app's seven call sites do
not change); the file's content and sha256 go into resolved_config.yaml under a top-level
`structure` key, written only when a structure is used. `results_io.PREREGISTERED_PATHS`
already covers configs/.

Experiment-level block (new, optional, not a shared block):

    structure:
      file: configs/structures/generic_f9_class_2d.yaml
      payload_cases:                       # the payload form (RQ3): P* with the structure
        - {name: silo_cold_pstar_st, of: silo_cold, set: central}

Offload case field (new, optional; default absent, so no case dict or dump changes):

    - name: silo_cold_s1_st
      of: silo_cold
      solve: stage1
      structure: {set: central, sizing: flown, dynamic: rise_time, entry: aft_ring, margin: 0.0}

`set` in {central, low_mass, high_mass}; `sizing` in {flown, full_load}; `dynamic` in
{rise_time, quasi_static, step}; `entry` in {aft_ring, thrust_structure}; `margin` >= 0. Refused:
with `stage1_dry_mass_added_t`, with `paired_pad`, on a case of a variant with no push, on the
pad, without an experiment `structure` block. Sweep points and sensitivity arms inherit the
field (S02).

### 4.4 Coupling to the offload solve, the payload search and the records

**Offload solve.** `OffloadProblem` (offload.py 151) gains `transform: Callable[[Vehicle,
float], Vehicle] | None = None`, applied in `vehicle_at` after `with_offload`; with None every
line of SP1's path is unchanged. `sim` builds the transform for a structural case from the
case's start context: given the vehicle at x and P_ref it flies the push alone
(`ctx.planner(P_ref, final).start(assist, track)`, about 8 ms; S03) with dense output, takes
every push sample and event (ramp end, power-limit corner, release), builds the load cases,
evaluates dm against the precomputed envelope, adds dm to stage 1's dry mass, and repeats with
the heavier vehicle until |dm_k+1 - dm_k| < 1e-6 kg or six iterations (deterministic;
contraction about 0.05, S03). The envelope is computed once from the pad baseline's Result
(for an arm: the pad flown under the same perturbation). `sizing: full_load` computes dm once at
x = 0 and adds that constant at every x.

- Monotonicity: m_res(x, dm(x)) stays decreasing while dm'(x) > -1/E, E = 4.38-4.58 kg of
  offload per kg of dry mass (S03 measured), so the bound is about -0.22 kg/kg; the probe gives
  -0.009 to -0.014 kg/kg for constant_accel, and dm' > 0 under a fixed-limit linear motor (a
  lighter stack is pushed harder). A fast test asserts dm'(x) > -1/(2 E) from the sizing model
  alone; `offload_nonmonotone` stays the in-run check; the fixed point (brief 5.5 option ii)
  is the fallback, with no solver change.
- Verification: `offload_solved_run` gains a dry-mass argument and a note argument; the
  pipeline passes dm(x*) and "modelled by first-order station sizing, set <set>, <file>"
  (never "assumed"), so the verification search and the recorded run fly the structure;
  `xv_dry_mass_delta_kg` of the decomposition then equals dm(x*) (a test, within 1e-6 kg).
- Memo: the structure setting enters the solve and run memo keys (results_io 1174), so a
  structural case can never reuse an unstructured solve (S03 measured the collision).

**Payload form.** `structure.payload_cases` fly the named variant at its own P* with the
modelled dm: dm_0 sized at P = the pad's P* (P_ref), P_1* searched on vehicle + dm_0, dm_1
re-sized at P_1*, P_2* searched; reported P_2* with |P_2* - P_1*| as a check (flag above
0.05 kg). Recorded as a new record kind in the structure section, never under the offload
heading.

**Records** (metrics.json, per structural case, beside the penalty keys of results_io
1462-1467): `structure_charged` true, `structure_dm_kg` (at x*), `structure_dm_x0_kg`,
`structure_set`, `structure_sizing`, `structure_dynamic`, `structure_entry`,
`structure_margin`, `structure_dlf`, `structure_n_peak_g`, `structure_F_peak_N`,
`structure_elements` (kg per element), `structure_governing` (element, mode, station, case),
`structure_flags`, `structure_file` and its sha256. Block level `structure_inputs` beside
`energy_inputs`: the envelope per element with its governing instant, the plausibility table,
the frozen sets and the tornado. Uncharged cases carry none of these keys (so every existing
record and pin stays as it is).

**Summary** (summary.md, only when a structure block exists): a "Structure" subsection after
the offload cases: one row per structural case (set, sizing, dynamic, entry, margin, dm, x*, % of
stage 1, verification gap, flags) with the penalty rows of the same experiment beside it, the
band line ("x* from <high-mass> to <low-mass> t at dm from <> to <> t; the bounds of the stated
coefficient ranges, not a confidence interval"), the element table of the central case, and
the payload cases.

**Figure** (plots.py, written for every structural case): required wall thickness along the
stage-1 stations, pad envelope against the push, the governing mode marked, and dm by element.

### 4.5 Wording at source, KI-039, KI-036 and the gallery

Every sentence that says or implies that no structural mass is charged (S04 sections 2.1 and
2.2: C1-C11 and the three "dry masses unchanged" sentences) branches three ways from the run's
own record: uncharged (today's text, word for word), assumed penalty (today's text), modelled
(new text naming the mass, the model, the set and the file, and saying it is a first-order
estimate with a band, not a detailed structural design). The run-specific branches change in
S3a; the program-level claims ("no structural model exists" in `replay.penalty_structure_sentence`
and app.py's "Structure." caveat; site/build.py 227; README, site and deck prose) change at
the close, pointing at the findings note. `OFFLOAD_CAVEATS`' drive item branches by drive (it
is false for a linear-motor case). The honesty auditor reviews every new sentence.

KI-039 as D-SP7-19. KI-036: replay.py 1819-1820 put "state unknown" into the git string when
dirty is not a bool or the hash is a no-git value, and keep `dirty` a bool (the frozen template
renders it); tests for both. Recorded summaries and results are never rewritten.

Gallery: the six pages regenerate from their recorded commands (S04 section 7); since every
source run is uncharged and constant_accel, they are expected byte-identical, and the gate is
`git status --porcelain site/examples` empty after regeneration, recorded in the session log. A
deliberate change would be regenerated and its diff recorded, as SP2 A1a did.

### 4.6 The linear motor (assist/linear_motor.py)

**Config** `LinearMotorConfig` (replaces `PlannedAssistConfig` for that tag; every number strict
and finite): `stroke_m` (> 0), `force_max_kN` (> 0), `power_max_MW` (> 0; `units.mw_to_w`, a
`MW` suffix row in compare), `force_rise_time_s` (>= 0; 0 is a step), `carriage_mass_t` (>= 0),
`brake_decel_g` (> 0), `drive_efficiency` (0, 1], `exhaust_impingement_fraction` [0, 1],
`release_speed_mps` (optional, > 0, left out of the dump when unset), `shaft` (`vented` |
`sealed`) with `shaft_bore_m`, `shaft_gap_m`, `shaft_gamma` required only when sealed, `track`.
No assist-family key names. The depth-bound check (config.py 1433-1438) is generalised to any
track drive.

**Model.** Drive force F = min(F_lim(t), F_max, P_max / sdot) with F_lim(t) = F_0 + (F_max -
F_0) min(1, t / t_r): the ramp starts from the holding force F_0 = max(0, M_0 g_eff sin phi -
(1 - f_imp) T(0)), fixed at push start through a new hook `at_push_start(m_vehicle, thrust)`
that returns a bound copy (existing models return themselves). Track equation as today (base.py
11-20): M sddot = F + (1 - f_imp) T - M g_eff sin phi - F_p(s); F_int = m_v (sddot + g_eff sin
phi) - T; dissipated 0. P_max is the mechanical limit at the carriage; electricity = drive work /
eta and the electrical peak = mechanical peak / eta are reported. Events: the ramp end t_r as a
model kink time merged into the sub-phase boundaries (empty for the existing models, so their
call sequence is unchanged); the power-limit corner sdot = P_max/F_max as a non-terminal,
logged event. Refusals: a stall at push start (F_max + (1 - f_imp) T(0) <= M_0 g_eff sin phi),
reported as a failed run with its reason; a `release`-referenced ignition with t_ign_s < 0 (its
time would depend on the push it changes); ramp starts by depth, speed or height (as today for
any drive but constant_accel). A `release`-referenced ignition with t_ign_s >= 0 is resolved at
the real release time (pending through the unlit push), not from an estimate, so no closed-form
push time is needed in the run path; `push_time_estimate` stays an estimate used only for the
step cap. The 1-D planner takes the drive with no change (S01).

**Metrics** (conditional on linear_motor; `net_accel_*` stay None as today): `push_force_max_N`,
`push_power_max_W`, `push_rise_time_s`, `push_corner_speed_mps`, `push_power_limited` (the
corner was reached), `push_accel_mean_mps2` (v_exit / t_push, named a mean),
`release_position_m`, `release_trigger`, `electrical_power_peak_W`, and the braking items of
4.8. Readers: `replay.drive_caveat` gains a linear-motor clause that is always present (F_max,
P_max, t_r, carriage, shaft); scene.py stops deriving `net_accel` from v^2/(2L) for any drive but
constant_accel; KI-038 (the renderer's version and git state on the scene page). The replay and
scene pages of a linear-motor run are looked at in S4a's gate.

### 4.7 Release at a target speed

linear_motor only: a terminal event sdot - v_release crossing upward (ATOL_MPS) in fly_track's
event list; `TrackExit` gains `s_release_m` and `trigger`; z, phi and x are evaluated at the
release position for the new trigger only, so `track_end` keeps z(L) bit for bit. If v_release
is not reached by L, `track_end` fires and the run carries the flag `release_speed_not_reached`.
After a release below the mouth the vehicle flies the rest of the vented shaft in the free
atmosphere (no shaft flow model, as for the push; stated); the carriage brakes in the stroke
left: facility length = max(L, s_release + d_brake).

### 4.8 Braking and the sealed-shaft air column

**Braking** (linear_motor only; constant_accel's functions unchanged): constant total
deceleration a_b = brake_decel_g g0: distance v^2 / (2 a_b), time v / a_b, brake force on the
carriage m_c (a_b - g_eff sin phi), brake energy (1/2) m_c v^2 (1 - g_eff sin phi / a_b); facility
as 4.7. Closed form only (D-SP7-21).

**Sealed shaft** (linear_motor only): the carriage seals the bore above a gap h_0 of trapped air
at the push-start pressure p_0 = p_atm(z_start); F_p(s) = max(0, p_0 - p_0 (h_0/(h_0 + s))^gamma)
A_bore, acting on the carriage against the motion, bounded by p_0 A_bore (1.09 MN for a 3.7 m
bore). The work against it enters a model state `W_other_J` and the budget's new `work_other`
(default 0.0, so constant_accel's residual is bit-identical). Refused: bore at or below the body
diameter. Stated, not modelled: the air pushed out of the mouth above the vehicle (S08: about 77
kN of momentum flux at exit, 0.4% of F_int) and the gas cooling that makes the adiabat only
first order near the end of a small-gap stroke (S08).

### 4.9 KI-030 and test hygiene

KI-030 (S4): per-field `strict=True, allow_inf_nan=False` on `ConstantAccelConfig`,
`TrackConfig`, `StartupOverride`, `IgnitionConfig`, `OffloadFixedConfig`, `OffloadCaseConfig`,
`OffloadConfig` (S02's measured patch), strict bools, and range bounds t_ign_s in [-3600, 3600] s
and exit_altitude_m in [-500, 500] m (the -30 m failed-ignition test geometry still passes).
Measured: every shipped file resolves to identical digests; one test case changes (test_config
389). Shared blocks are left lax (their YAML strings and tuples would be refused).

Hygiene (D-SP7-26): `structure` and `assist/linear_motor` into `PHYSICS_MODULES` and
`RUN_PATH_MODULES`; the docstring check fails on a missing path and lists the six phases files
(and `offload`); KI-035: the import guard split into a fast AST part and a slow subprocess part;
KI-021, KI-022, KI-023: the stale test docstrings and comments.

### 4.10 Experiments (pre-registered in S6)

Three new files, the six shared blocks copied verbatim from experiments/silo_offload_2d.yaml,
no label, listed in `PLANAR_EXPERIMENTS`.

**A. experiments/silo_structure_2d.yaml** (gate vehicle; baseline pad, variant silo_cold as SP1;
structure file configs/structures/generic_f9_class_2d.yaml). Offload (stage 1, at P_ref, pad
control on, SP1's energy block):

| Case | What | Purpose |
|---|---|---|
| silo_cold_s1 | uncharged | reproduces SP1's 41,262.908 kg (<= 0.002 kg) |
| silo_cold_s1_dry+2t, +4t, +8.1t | SP1's penalty rows | reproduce 32,285.203 / 22,875.961 / 1,980.477 kg (<= 0.002 kg); the bracket beside the model |
| silo_cold_s1_st | central set, flown, rise_time, aft_ring, margin 0 | **the headline** |
| _st_low, _st_high | low-mass and high-mass corner sets | the band |
| _st_full | full_load sizing | Q2's bound |
| _st_qs, _st_step | DLF 1 and 2 | Q7's quasi-static value and step bound |
| _st_ts | entry through the thrust structure | Q5's row |
| _st_m10, _st_m25 | 10% and 25% margin | Q3's sensitivity |
| arms on _st | +/-10% stage-1 dry mass, Isp, C_D, drive efficiency | CLAUDE.md's sensitivity of a headline |

Payload cases: silo_cold's P* with the central, low-mass and high-mass structure (RQ3's payload
form, against the pad's 26,054.4 kg and RQ3's +1,498.8 kg).

Sweeps (the depth question): stroke 50, 100, 200, 300 m at the fixed exit speed
76.70717046013364 m/s (felt 7.0, 4.0, 2.5, 2.0 g0), each point solved with the central, the
low-mass and the high-mass structure (three sweeps, twelve verified solves).

**B. experiments/silo_drive_2d.yaml** (gate vehicle; baseline pad). Variants, each with an
uncharged and a central structural stage-1 solve:

| Variant | Drive |
|---|---|
| silo_cold | constant_accel 3 g0, 100 m (the reference) |
| lm_cold_target | linear motor by the rule, release at 76.70717 m/s |
| lm_cold_atL | the same limits, release at L (the offloaded stack exits faster) |
| lm_cold_r07 | r = 0.7, F_max re-solved for the same exit at full load |
| lm_hot | lm_cold_atL's limits, stage 1 lit at push start (2 s ramp) |
| lm_sled22 | lm_cold_atL's limits with a 22 t carriage |
| lm_sealed | lm_cold_atL with the sealed shaft (3.7 m bore, 5 m gap) |

The linear-motor rule, fixed before any run and shown in the pre-registration: r =
P_max/(F_max v_e) = 1 (Jacobs 2000's constant-force sizing, S07); m_c = 0; t_r = the structure
file's 10 T_low/pi; F_max such that the pad's own full-load vehicle at P_ref (572,354.4 kg)
reaches v_e = 76.70717046013364 m/s at L = 100 m, cold, vertical, at g_eff (closed forms of
section 4.6's test oracles); P_max = r F_max v_e. The numbers go into the file with a comment
naming the rule; nothing is changed after any run.

**C. experiments/silo_structure_2d_readme.yaml** (the README-loads fork with its own structure
file): pad, silo_cold, an uncharged and a central structural stage-1 solve, the pad control.

**Commands**, from one clean commit, four in parallel: `run` A, `sweep` A, `run` B, `run` C.
Budget at SP1's measured production rates (S09 set M): about 18, 12, 12 and 3 min, wall about
20 min; about 60 min at the pessimistic rates (below D-SP1-17's 90 min trim threshold).

**Pre-registration** (S6, docs/phases/inputs/<date>-SP7-preregistration.md, SP1's sections,
S09 1.4): what is registered and the commands; what is already known (this probe, S2's
sizing-only dm per case at the headline push, SP1's numbers); the basis and the resolution;
each case's purpose; the rules fixed; for every case an expected x* from its sizing-only dm by
the coupled placement on SP1's penalty curve (an estimate, "none is a target"; the naive
placement's bias stated); the reading of every outcome, including the sentence fixed in advance
for a band wider than the offload ("the first-order model cannot decide whether the stage-1
offload survives; the coefficients that decide it are ..."); the blocking checks; what nothing
measures; the runtime estimate.

### 4.11 The findings note

docs/findings/RQ1-structural-2d.md: the question; caveats first (first order, not a detailed
design; the band is the bounds of stated ranges, not a confidence interval; the assumed
load-entry coefficient; zero margin; the assumed axial frequency and rise time, and that
constant_accel's trajectory keeps its infinite jerk while its structure assumes a ramp; the
calibration miss; sweep-optimized; unthrottled; free kick; partly filled tanks); definition;
provenance; headline (central x* with the band, dm at each end, the bounds, SP1's penalty rows
beside); which elements and modes carry the mass; depth; the drive cases; the payload form; the
flags; what goes against the hypothesis; limits; each pre-registered reading; reproduction;
figures. RQ1 gets a dated pointer section at its top; its headline paragraph and caveat titles
stay (tests/test_app_server.py 3045-3075 pins them).

## 5. Steps

Each step runs the protocol's loop: implementer; adversarial reviewers (a physics or numerics
skeptic on every code step, a CLAUDE.md compliance auditor on every step, an honesty auditor
on S0, S3a, S6, S7 and every caveat or label reworded, a visual reviewer on anything drawn); up
to two fix rounds; an independent gate; one commit; the tracker commit at once; push and the
Pages check. Standing gates on every code step: fast suite green, ruff clean, the exact 1-D
golden tier, the planar digest pin and the planar output capture unchanged, the pad and
silo_cold capacities' slow record test where the step touches the run path, no shipped
experiment or vehicle file changed (`git diff --quiet <start> HEAD -- configs/vehicles` and the
seven shipped experiment files), templates/replay.html's sha256 unchanged. The full suite after
S3, S4, S4a and S5 and before the close. Tests run on synthetic directories or short flights in
a temporary folder, never on results/. App runs made by reviewers and gates use a scratch
results root (D-SP2-37).

| # | Step | Main files | Tests | Gate |
|---|---|---|---|---|
| 0 | Plan mode: checklist, surveys, questions, this design, its review | docs/phases/inputs/ | fast suite | the user approves |
| S0 | Sources: every coefficient's range with its source or the reason it is assumed; the stage-1 breakdown; the rise-time and linear-motor rules; k_entry's anchors | docs/phases/inputs/<date>-SP7-sources.md | none | every number sourced or assumed with a reason; honesty review |
| S1 | Sizing primitives (pure): hydrostatic head, hoop, monocoque buckling with gamma and Delta_gamma, stiffened Gerard thickness, domes, the DLF bound, the increment rule; test hygiene of D-SP7-26 | structure.py; tests/test_scaffold.py, test_scene.py | test_structure.py: each closed form against a hand-computed value (not the code's formula); Delta_gamma table read-back; t(N) inverse checks; zero inside the envelope; monotone in n and in the propellant | all listed tests; KI-035 split; docstring check strict |
| S2 | The station model, load cases from a flown push and from a Result, the envelope from a pad Result, flags, plausibility; `StructureConfig`, the loader, the two structure files; the corner search and the tornado at SP1's headline push, written into the files (the frozen sets) | structure.py, config.py, cli.py, configs/structures/ | the pad's own cases give 0.000 kg; stations converge (doubling N < 0.1 kg); the file validates with every number sourced or assumed; S05's station products recomputed from a short synthetic flight; the sets are corners of the ranges | all listed tests; vehicle files untouched; digests unchanged; the sizing-only table recorded in the session log |
| S3 | Coupling: the `OffloadProblem` transform, the transform builder, dm(x*) in the verified dict, memo keys, the payload cases, record keys, `structure_inputs`, the Structure subsection, the thickness figure; tests/data/silo_offload_2d_record.json | offload.py, sim.py, results_io.py, summary.py, plots.py, config.py | without a structure block every output byte-identical; constant-2 t cross-check through the pipeline = SP1's +2 t row (<= 0.002 kg; slow); SP1's headline with the structure off (<= 0.002 kg; slow); dm'(x) > -1/(2E); xv_dry_mass_delta_kg = dm(x*); memo separation; payload two-pass check | all listed tests; full suite |
| S3a | Wording at every source (three-way branch), KI-039, KI-036; the pinned wording tests; the gallery regenerated | summary.py, compare.py, sim.py, config.py, replay.py, scene.py, plots.py, app.py; docs/manual | the eight pinned files updated; three-way branch tests per source | honesty review; `git status --porcelain site/examples` empty after regeneration (or the deliberate diff recorded); KI-039 and KI-036 closed |
| (checkpoint 1) | the structural headline can be produced from an experiment file | | | |
| S4 | linear_motor: config, model, ramp, limits, corner event, the pending release-referenced ignition, refusals, metrics, braking functions; KI-030; KI-021-023; physics.md | assist/linear_motor.py, assist/base.py, config.py, units.py, compare.py, phases/prelude.py, metrics*.py | closed forms (ramp from the holding force, force phase, power phase; vertical in the model, horizontal on an injected track): <= 1e-9 relative; F <= F_max and F sdot <= P_max at every sample; energy identity < 1e-9 (required 1e-6) cold, hot and with a ramp; hot interface force for f_imp 0, 0.5, 1; stall and ignition refusals; KI-030 refusals and the shipped digests | all listed tests; full suite |
| S4a | Release at a target speed; the readers (replay drive clause, scene push labels, KI-038); the conditional summary rows | phases/prelude.py, phases/engine.py, replay.py, scene.py, summary.py | event at sdot = v_release with s = s(v) of the closed form; z at s_release; track_end runs bit-identical; `release_speed_not_reached` | all listed tests; the replay and scene pages of a linear-motor run looked at; full suite |
| S5 | The sealed-shaft air column; the energy budget's `work_other` | assist/linear_motor.py, dynamics.py, losses.py, physics.md | p = p_0 (h_0/(h_0+s))^gamma and the work closed form against the quadrature; F_p <= p_0 A; F_int lower by (m_v/M) F_p; the identity < 1e-9 with the piston | all listed tests; full suite |
| (checkpoint 2) | the drive realism complete | | | |
| S6 | The three experiment files and the pre-registration note, committed before any run | experiments/, docs/phases/inputs/ | test_config_planar lists the files; resolve and preflight only | resolves; honesty review of the expected readings; committed; clean tree |
| S7 | The four commands from the clean commit; the findings note, RQ1's pointer, README results, the findings index, physics.md research notes; derived figures | results/ (summaries), docs/findings/ | full suite | no `bug_suspect`; every verification within 1e-4 P_ref or flagged; the reproductions within 0.002 kg; honesty review |
| C | Close: exit-criteria gate, full suite, demo, trackers, CLAUDE.md, README, public face, SP3's file fact-checked, handoff, memory, cold read | docs/, site/, TODO.md, CLAUDE.md, README.md, memory | full suite; site build | independent gate; final commit; Pages green |

**If room runs out**, in this order, each put to the user when it happens: the sealed shaft (S5)
and its case; lm_cold_r07 and lm_sled22; the low-mass and high-mass stroke sweeps; the bridge;
the margin rows; the arms beyond stage-1 dry mass and C_D.

## 6. Exit criteria (tolerances fixed)

1. **Validation first.** Every test of S1-S5 passes; each piece's test commit precedes S6's
   experiment commit (git log).
2. **Provenance.** Both structure files validate with every number sourced or `assumed: true`
   (a test scans them); `git diff --quiet <start commit> HEAD` on configs/vehicles/ and the
   seven shipped experiment files.
3. **Nothing validated moved.** The exact 1-D golden tier; the planar digest pin; the planar
   output capture; the pad and silo_cold capacities within 0.002 kg; SP1's headline with the
   structure off within 0.002 kg of 41,262.908 kg (slow pin and S7's uncharged case); SP1's
   three penalty rows within 0.002 kg (S7); the constant-2 t cross-check within 0.002 kg of
   32,285.203 kg; replay.html's sha256; the six gallery pages byte-identical on regeneration
   (or a deliberate, recorded diff).
4. **The structural headline**, from the pre-registered file run from a clean commit: the
   central x* and dm, the low-mass and high-mass x* and dm (the band), the full-load bound, the
   quasi-static and step rows, the thrust-structure row, the margin rows, the penalty rows
   beside; every case ends `ok` or carries its flags; every verification within 1e-4 x P_ref
   (2.605 kg) or flagged and reported as a bound; every decomposition explained; every
   structural case's `xv_dry_mass_delta_kg` equals its recorded dm(x*) within 1e-6 kg; no
   `bug_suspect`; no unexplained `offload_nonmonotone`.
5. **Convergence.** Tightening the search tolerances 10x moves the central structural x* by
   < 0.1%, and doubling the station count moves dm by < 0.1 kg (slow test).
6. **Depth and drive.** The three stroke sweeps and the six linear-motor variants solved and
   reported with felt g, DLF, dm, x*, electricity, peak mechanical and electrical power, the
   facility length and, for the linear motor, the release position and speed.
7. **The findings note** (RQ1-structural-2d.md) with the pointer in RQ1, passing the honesty
   review: the band, the dominant coefficients, and plainly whether the structure cancels most
   of the offload; README results and the findings index updated; every structural sentence
   branched at its source; KI-039 and KI-036 closed.
8. **physics.md** holds the structural model, the DLF and the flags, the linear motor, the
   target-speed release, braking, the air column, their assumptions and test-map rows.
9. **Full suite** green with the count recorded; ruff clean; no new dependency.
10. **Demo** recorded under docs/demos/SP7/.
11. **Close-out**: public face refreshed (landing page, deck and PDF, gallery, manual), site built
    with no broken link, main pushed and Pages green; SP3's file fact-checked; handoff, prompt
    and memory written; cold read done.

## 7. Verification commands

    uv run pytest -q -m "not slow"
    LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1 uv run pytest -q
    uv run ruff check . ; uv run ruff format --check .
    uv run python -m launchsim run experiments/silo_structure_2d.yaml
    uv run python -m launchsim sweep experiments/silo_structure_2d.yaml
    uv run python -m launchsim run experiments/silo_drive_2d.yaml
    uv run python -m launchsim run experiments/silo_structure_2d_readme.yaml
    uv run python -m launchsim replay results/silo_structure_2d/<ts> --runs pad silo_cold_s1_st --out docs/demos/SP7/pad-vs-structural-offload.html
    uv run python -m launchsim scene results/silo_structure_2d/<ts> --runs pad silo_cold_s1_st --out docs/demos/SP7/pad-vs-structural-offload-scene-page.html
    uvx --with markdown==3.11 python site/build.py

## 8. Risks

| Risk | Resolution |
|---|---|
| The band is wider than the offload | The result: the pre-registered sentence, the dominant coefficients named |
| k_entry dominates and is assumed | Its anchors stated in S0; the tornado shows its share; the note says it is the least sourced term |
| A first-order model reads as more certain than it is | Caveats first; the penalty rows beside; "not a detailed structural design" in every modelled sentence |
| The coupling breaks monotonicity | dm' bound test; the solver's flag; the fixed-point fallback |
| A new key breaks the 1-D golden tier | Every new key, column, assumption and row conditional on the new features; the exact tier on every step |
| Linear-motor parameters chosen to flatter | The rule fixed in S6 before any run; r < 1 only as a labelled case |
| The rise-time rule hides the dynamic charge | The step row and the quasi-static row beside the central; the rule's own cost reported in the linear-motor runs |
| Release unloading | Reported with numbers and flagged; a ramp-down is not modelled and is said so |
| Run time | About 20 min wall at measured rates, about 60 min pessimistic; background commands |
| A usage limit kills agents mid-step | Journals and resume (protocol section 11) |

New tracker items to log at the start commit: B-016 (P2, later: the app's modelled-structure
switch and a linear-motor launch, D-SP7-08); B-007 re-targeted in part (braking functions, the
air column and the target-speed release to SP7; friction stays later); KI-035, KI-036, KI-038,
KI-021-023 owned by SP7 under their own rules.

## 9. Corrections to the brief found by the surveys

- Section 5.5 and 5.8 run times: about 35-45 s per verified solve under three-way concurrency
  and about 15 s per pad control, not 90-110 s and 30 s (S09).
- Section 5.10 and R4: a defaulted field on `ConstantAccelConfig` moves no resolved dict and no
  digest (resolved dicts are raw YAML); it breaks the dump-key pin at tests/test_config.py
  432-443 (S02).
- Section 2 item 5 and 5.11: removing `linear_motor` from `PLANNED_MODELS` drops it from
  `ASSIST_UNION_TAGS` (appform.py 187); it does not follow (S01, S02, S04).
- Section 5.1's list of structural sentences misses `scene.structure_note`, `app.SP1_HEADLINE`'s
  "Structure." caveat, summary.py 1821's row label, and the three "dry masses unchanged"
  sentences plus `OFFLOAD_CAVEATS`' drive item (S04).
- Section 5.2: the step factor applies to the increment over the resting 1 g0, so a step peaks
  near 7 g0, not 8 (S01, S07); release is a second step (S07).
- Section 5.7: eta does not enter the mechanical identity; the piston work is not "dissipated"
  (S01); the power limit cannot lower the felt g at a fixed (L, v_e) (S01, S07).
- Section 5.5: a factory wrapper alone leaves `offloaded_vehicle` and the verification without
  dm (S03, measured `bug_suspect`); the transform belongs in `vehicle_at`.
- tests/test_offload.py 795 does not pin x* (S03); entry criterion 4 relies on it only for the
  re-solve; SP7 adds the pin.
- TODO.md lines: KI-030 is at 347, KI-036 at 353 (S09).
- tests/test_scaffold.py's "phases" entry is silently skipped (S09).

## 10. First actions after approval

1. Save this design (as approved) as docs/phases/inputs/2026-10-08-SP7-design.md and the nine
   surveys as docs/phases/inputs/2026-10-08-SP7-survey/ with a README index; the review of this
   draft as docs/phases/inputs/2026-10-08-SP7-review/.
2. Log D-SP7-01 to D-SP7-26 in TODO.md; B-016; B-007's re-target; the KI ownership notes.
3. Bring the phase file's sections 3, 7, 8 and 10 to the approved design; section 11's first
   entry (the checklist, step 0); section 12's deviations from the brief.
4. Mark SP7 in progress in the phase file, the board and TODO.md; the handoff's header line.
5. Commit "Start SP7: status in progress"; push; check Pages.
