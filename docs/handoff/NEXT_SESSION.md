# Handoff: SP7 `<C2:closed>`; start SP3 (3-D dynamics S1, a 3-DOF point mass over a rotating sphere)

`<C2:delete-this-line>` Until C2 fills the marks in this file, SP7 is in progress and step C2 is next (its brief: C:/Users/rahul/.claude/projects/D--DEV-ClaudeProjects-SpaceRocketOptimization/sp7work/c2/BRIEF.md): do not start SP3 from this file.

## 1. Header

- Written 2026-11-05, at the close of phase SP7 (session started 2026-10-08, resumed
  2026-10-19), following docs/process/SESSION_PROTOCOL.md sections 7 and 8.
- Phase `<C2:closed>`: **SP7**, the structural mass of the push load and a force-limited drive
  (planar model), docs/phases/SP7-structural-mass-push-load.md. Exit gate:
  `<C2:exit-gate-verdict>`.
- Closing commit (the last commit that changed code or results): `<C2:closing-commit>`.
- This file is part of the bookkeeping commit that follows, subject
  `Close SP7: trackers, handoff, next phase file` (protocol section 7, item 12). A file cannot
  hold the hash of its own commit, so HEAD is identified by that subject. main is pushed to
  origin after it and the Pages deployment checked (`gh run list --workflow pages.yml --limit
  1`).
- Next phase: **SP3**, docs/phases/SP3-3d-dynamics-s1-sphere.md. After it: SP4, SP5, SP6
  (D-SP1-18, D-SP2-40), then the rest of README Phase 3, Phase 5 and Phase 6 (the user's
  request, section 2).

Read in this order (protocol section 3, item 1):

1. This file.
2. docs/process/SESSION_PROTOCOL.md.
3. docs/phases/README.md (the program board).
4. docs/phases/SP3-3d-dynamics-s1-sphere.md (the phase file).
5. CLAUDE.md.
6. TODO.md. While reading it, list the open known issues and backlog items owned by SP3
   (section 5 below lists them as of this handoff).
7. README.md.
8. The memory index and the notes it links:
   C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md
9. The inputs the phase file links: docs/phases/inputs/2026-09-30-design-3d-dynamics.md first,
   then docs/phases/inputs/2026-09-30-SP1-approved-plan.md. Then sections 11 and 12 of
   docs/phases/SP7-structural-mass-push-load.md for what SP7 changed in the shared modules.

## 2. The request

The user's request to the session that resumed SP7 (2026-10-19), verbatim:

> resume SP7 here, starting with S7a's open check. Then continue with the rest of the SP7, then SP3-SP6, then rest of the readme phase 3, phase 5, phase 6, keep working till it is complete.

It stands. Each later phase still opens with its own Plan mode and the user's approval of its
design (protocol section 3, item 6): the request does not replace that approval.

No new research request otherwise. SP7's own goal is the user's ordering (D-SP1-18, confirmed
by D-SP2-40), quoted with the rules of the phase in the SP7 phase file, section 13. The
user's answers during SP7: D-SP7-01 to D-SP7-12 (the questions and follow-ups), the design
approved with the plan (D-SP7-13 to D-SP7-35), D-SP7-36, D-SP7-41, D-SP7-45 to D-SP7-47, and
on 2026-10-19 D-SP7-48 ("Fix and re-run sweep A"). Every one was the recommended option.
D-SP7-49 to D-SP7-56 were made by the session under the instruction to keep working, and go
to the user in section 6. The other seven: D-SP7-37 is the source note's corrections to the
design, adopted at S0; D-SP7-40 records the question D-SP7-41 answered; D-SP7-38 and
D-SP7-39 were session-made and reported to the user at S2's gate; D-SP7-42 to D-SP7-44 were
session-made and logged as reported in S3's entry of the phase file.

## 3. What was finished in SP7

**Steps** (SP7 phase file, section 7; every row with its commit):

| Step | What | Commit |
|---|---|---|
| 0 | Plan mode: nine surveys, the questions, draft v1 and six reviews, version 2 approved | `a7c9f0a` (the start commit) |
| S0 | Sources of every coefficient | `81e045d` |
| S1 | Sizing primitives (structure.py) | `a3bd183` |
| S2 | Station model, structure files, the frozen sets | `45e39d4` |
| S3 | The coupling into the offload solve | `889f6ea` |
| S3b | Reporting the structure | `216a79c` |
| S3a | The structural wording at every source | `0a16a89` |
| S6a | Files A and C and the pre-registration, part 1 (with checkpoint 1) | `cbbd7bc` |
| S7a | `run` A, `sweep` A, `run` C; the note's structural part | `6fa2ff0` |
| S3c | The sweep's no-offload record (D-SP7-48) | `1e4c732`, `77e1691` |
| S4 | The linear motor core, KI-030, KI-021 to KI-023 | `25967be`, merged `8c4b41a` |
| S4a | Target-speed release, the flown power cap, the readers, the shaft floor | `7cdc24a` |
| S4b | The structural transform on linear-motor pushes | `b0fcc31` |
| S5 | The sealed shaft and the piston-work record | `460c4d6` |
| S5a | The sealed shaft's wording (with checkpoint 2) | `2bd40bd` |
| S6b | File B and the pre-registration's part 2 | `331891d` |
| S7b | `run` B; the note completed | `e5f64b3` (scripts `b291518`) |
| S7c | The program-level wording in code | `9fe125c` |
| S7d | A fast tier that holds under other projects' load (added, deviation 57) | `cd14968` |
| S8 | The public face: demo record, gallery entry, deck and PDF, manual, landing page | `3a07f07` |
| C1 | The documents of the close: SP3's file fact-checked, the trackers, this handoff, memory | `ead6e38` |
| C2 | Independent exit gate, full suite, cold read, closing commit, push, Pages | the bookkeeping commit |

**Exit criteria** (SP7 phase file, section 8; 12 criteria, tolerances fixed by the approved
design). C2's independent gate records its verdicts there:

| # | Criterion | Result |
|---|---|---|
| 1 | Validation first | `<C2:criterion-1>` |
| 2 | Provenance and freeze | `<C2:criterion-2>` |
| 3 | Nothing validated moved | `<C2:criterion-3>` |
| 4 | The structural headline | `<C2:criterion-4>` |
| 5 | The frozen sets | `<C2:criterion-5>` |
| 6 | Convergence | `<C2:criterion-6>` |
| 7 | Axes and drive | `<C2:criterion-7>` |
| 8 | The findings note and the KI closures | `<C2:criterion-8>` |
| 9 | docs/physics.md | `<C2:criterion-9>` |
| 10 | Full suite, ruff, no new dependency | `<C2:criterion-10>` |
| 11 | Demo | `<C2:criterion-11>` |
| 12 | Close-out | `<C2:criterion-12>` |

**The headline, with its caveats beside it.** Quoted from docs/findings/RQ1-structural-2d.md,
which this file does not recompute; read that note's "Caveats (read first)" before quoting
any number:

> **With a first-order structure sized for the offloaded stack only (central coefficients; an
> assumed real-drive rise time of 0.5 s that the constant_accel trajectory does not fly, its
> plateau cost charged; an instant release that the model's single-mode treatment says would
> separate the stage-1 LOX column (its bottom at -896 kPa absolute at the release, where the
> same tank, empty at the pad's MECO, stays at +132 kPa gauge), as the same treatment also
> separates stage 2's full LOX column at the pad's own MECO (-232 kPa gauge, against -162 kPa
> gauge at the push); the model's unthrottled envelope; zero margin), the 3 g0, 100 m
> cold-start silo leaves out 11.42 t of stage-1 propellant (2.78% of stage 1) against SP1's
> 41.26 t uncharged; the physics band gives no offload (243.7 m/s short, payload deficit
> -2,080 kg (two passes; residual estimate 0.137 kg)) to 28.57 t (28.57 t after the
> plausibility rule's factor 0.739, which fires at M_model / R = 1.76 and multiplies the
> case's whole dm, the load entry included; 71% of M_model is the envelope of the stage-1 LOX
> barrel, an element the push barely loads, sized by axial buckling at the pad's MECO and
> carrying nof_barrel, a double count of buckling material the source note flags; 23.68 t
> unscaled), the outer envelope no offload (1,021.5 m/s short, payload deficit -7,804 kg (two
> passes; residual estimate 23.0 kg)) to 31.12 t; sized for a full load 10.59 t; through the
> thrust structure 5.97 t; with a step push no offload (125.2 m/s short, payload deficit
> -1,087 kg (two passes; residual estimate 0.277 kg)).**
>
> Beside the number: the gate vehicle carries 26,054.4 kg to the reference orbit against the
> published 22,800 kg (+14.3%, outside the +/-10% band; the user accepted the miss on
> 2026-09-30, docs/findings/CAL-f9-leo-2d.md), so every offload here is a difference between
> runs of this vehicle model, not a Falcon 9 figure; file C (the README-loads fork, +8.33%) is
> the one robustness row. The thrust-structure row's 5.97 t sits close to its own estimated
> break-even (sizing only, S2's first pass: k_ts 0.3476 kg/kN, 24% above the central), and S0
> moved k_ts's central after the planning probe in a direction that raised that row (both
> beside its reading sentence below).

and, on the drive:

> File B's drive cases (run B, same caveats, at the central structure only: no physics band
> and no +/-10% arm on file B): all nine linear-motor central cases cancel most of SP1's
> uncharged offload, from 2.48 t (6.0%, lm_cmd_taper_s1_st) to 18.27 t (44.3%,
> lm_cmd_hot_s1_st, a hot start favoured by the unmodelled exhaust), and neither of the two
> drives that exit faster than silo_cold at x* on the same 100 m silo (lm_fixed,
> lm_fixed_hot) keeps more once charged; every fixed sentence of part 2 that fired is under
> "The drive cases", word for word.

This undercuts the hypothesis that every m/s of assist helps, at these coefficients: the
note's "What goes against the hypothesis" says so as plainly. The run is planar,
sweep-optimized (not optimal control) and unthrottled.

**Links.** The findings note: docs/findings/RQ1-structural-2d.md, with the pointer at the top
of docs/findings/RQ1-fuel-offload-2d.md. The demo: docs/demos/SP7/README.md, with the three
fast-suite results in order. The public face: site/index.html, site/deck/, site/examples/,
docs/manual/.

## 4. Requirements and status

| # | Requirement | Status on 2026-11-05 |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done before SP1; structural, linear-motor and sealed-shaft caveats branched in S3a, S4a, S5a and S7c; the template unchanged |
| R2 | An animated scene of the launch, 2-D first | Done in SP2; linear-motor and sealed-shaft labels in S4a and S5a |
| R3 | The same in a 3-D world | Not started: SP3, SP5, SP6 (dynamics), SP4 (the scene) |
| R4 | Configure the launch depth in the silo | Done in SP1; the depth sweep with the structure charged ran in S7a |
| R5 | Configure where the thrust ramp starts | Done in SP1 |
| R6 | Reduce the propellant at fixed payload and report the fraction replaced | SP1's answer re-judged by SP7 (section 3): a first-order station sizing at central coefficients (an assumed rise time, zero margin, the pad's unthrottled flight as the envelope, the instant release flagged, not sized) leaves 11.42 t of 41.26 t; planar, sweep-optimized and unthrottled, on the gate vehicle (+14.3% calibration miss); the app's form still offers only the assumed penalty row (D-SP7-08, B-016) |
| R7 | Stay on the Falcon 9-class model | Standing; configs/vehicles/ unchanged since 22c62e9 |
| R8 | Lose nothing between sessions | This handoff, the phase file and the archive (docs/handoff/archive/2026-11-03-SP7-in-progress.md) |
| R9 | One fresh session per phase; the previous session prepares the next | Exercised at this close: SP3's file fact-checked, its prompt final (section 10) |
| R10 | Public repository, pushed after every step, with a current logo, banner, deck, gallery, manual and Pages site | Refreshed in S8 (d03367b pushed, Pages green); the close's push and Pages run follow the bookkeeping commit |

## 5. The next phase: SP3

Open docs/phases/SP3-3d-dynamics-s1-sphere.md. Its design input is
docs/phases/inputs/2026-09-30-design-3d-dynamics.md, whose line numbers are for 2eebcae; the
phase file's section 6 holds the corrected ones.

**Goal** (SP3 section 1). Build stage S1 of true 3-D dynamics: a 3-DOF point mass in
Earth-centred inertial Cartesian coordinates over a rotating spherical Earth, with the same
atmosphere, drag, thrust, staging, guidance family and payload search as the planar model, at
any latitude and azimuth. Validate it by closed forms and by reduction to the planar model,
then record how far its payload capacity sits from the planar gate (26,054.4 kg at 28.5 deg,
azimuth 90 deg), with the pre-registered expectation |dP*| < 5 kg written into TODO.md and
committed with the planar pin (S1.0), before any file under src/ is edited. The phase produces
no new claim about the assist. It builds beside the planar model and moves no planar or 1-D
number.

**What SP7 changed that SP3 relies on or must not break** (SP3 sections 3 to 6 give file and
line):

- `phases/planar.py` grew from 1,733 to 2,028 lines. SP3's spatial planner is a copy of it as
  it stands at SP3's start: the linear motor's release-referenced ignition (D-SP7-25) and the
  flight inside the shaft after a release below the mouth, with `SHAFT_EXIT_EVENT`,
  `SHAFT_APEX_EVENT`, `SHAFT_TURNAROUND_EVENT`, `FlightStart.shaft_floor_m` and the
  `shaft_fallback` flag (D-SP7-51). Which of these it carries is decided in Plan mode (Q1, Q2).
- D-SP7-27: no field is added to any dataclass the 1-D golden dump reaches, because that golden
  can never be recaptured. tests/test_golden_dump_fields.py pins nine classes, so the lateral
  gravity row J_grav_lat rides in a spatial class, never as a `LossBudget` field.
- `OffloadProblem` carries an optional vehicle transform (`OffloadProblem.transform`, D-SP7-20);
  `RecordingProblem` is unchanged. The structural transform is planar-bound: `sim.flown_push_trace`
  flies a `SearchContext`, and `sim.structure_pad_cases` and `sim.structure_flight_cases` refuse
  a non-planar Result. Whether S1 carries it is SP4's question (Q6).
- config.py: `offload:` and `structure:` refuse every model but planar_2d, as the shared blocks
  do (Q3). `sim.run_ignition_specs` is a second dispatch on the model, beside `sim.run`.
- run_data.py: `check_run_dir` and `MODEL_COLUMNS` take planar_2d only, so `animate`, `replay`
  and `scene` refuse a spatial run and the app gives it no results panel (SP3 section 5.9).
- Added pins: tests/data/vented_pins.json with tests/test_sealed_shaft.py, the structure files'
  sha256, the offload-start digests of tests/test_structure_pipeline.py. The planar digest pin,
  the output capture, the exact 1-D golden tier and replay.html's sha256 stand as SP7 left them.
- S7d's gate passed the fast tier under 32 burners and a disk writer (KI-090, KI-091 closed).
  The SP7 file's S7d entry says what that does not show; the wall-clock bounds it loosened are
  in section 7 of C:/Users/rahul/.claude/projects/D--DEV-ClaudeProjects-SpaceRocketOptimization/sp7work/s7d/implement.md;
  two gaps stay in KI-093, and KI-051 stays open.

**Inventory.** SP3's sections 4, 6 and 13 were checked line by line at 6cf0fd2 on
2026-11-04, re-validated at d03367b on 2026-11-05 and corrected in place (SP3 header,
section 6's check line): 52 edits to the file, its first re-check since 2eebcae. Five gates
changed reading at C1, each a proposal step 0 confirms: exit criterion 3 and S1.2's rows
and pointwise dV/dt, and S1.3's kick event (exit criterion 4), read 1e-12 against the
quantity's scale; exit criterion 3 and S1.2's orbit gate read each component of h against
|h| and of the eccentricity vector against e, and state an rtol, 1e-12, since CLAUDE.md's
upper limit of 1e-9 fails it with no step cap; exit criterion 5 and S1.4's 28.5 deg vacuum
line compare r, v_r, v_theta and m with the kick started on the in-plane speed; and S1.4's
equatorial line keeps 1e-9 and 1e-8 s for the pad and silo_hot_full on a smooth test air
at a tightened rtol 1e-13 and `atol_scale` 1e-3, and reads the pad and silo_cold on the
shipped air at 1e-8, 1e-6 and 1e-5 s, with v_r against |v| on both lines (SP3 section 7,
Tolerances; reviews' replicas, not runs).
Nothing under src/ changed after 9fe125c. Drifted and unchecked: the design
input's line numbers (a record, never edited); the model tests of section 6
(`test_height_event.py` and `test_linear_motor_release.py` become models only if Q1 keeps
the shaft flight); run SP3's start check of section 6 against the HEAD it finds, and `git
diff --stat d03367b HEAD -- src tests configs experiments` shows what moved.

**Open items owned by SP3** (TODO.md): KI-001 (the read-only audit that no loss integral or
check reads the unwrapped `gamma_rel_rad`, step S1.6). No backlog item is owned by SP3.

## 6. Decisions to put to the user first

SP3 runs next: the planned order (D-SP1-18, D-SP2-40) and the user's request of 2026-10-19. A
different order is the user's call at this boundary.

**SP3's seven new questions, for its Plan mode** (phase file, section 10, with the full text,
beside the four older questions there; the recommendations on Q2, Q4, Q5 and Q6 and Q3's
clause on the `planar` key were drafted at SP7's close and have not been tried against a
design; Q7's is the physics review's):

- Q1, the altitude-up event and SP7's shaft flight. Recommended: refuse a release below the
  mouth on spatial_3d in SP3 with a one-line message; the model-to-model pair releases at the
  mouth, and the phase that first needs it ports it. Trade-off: no spatial early release yet.
- Q2, SP7's drives on a spatial run. Recommended: refuse the linear motor and the sealed shaft
  on spatial_3d in SP3. Trade-off: a later phase wires them; accepting them now adds keys,
  lines and tests no run of this phase uses.
- Q3, the shared and planar-only blocks. Recommended: `offload:` and `structure:` stay
  planar-only, only the shared-block rule is widened, and the shared blocks stay under the
  `planar` key. Trade-off: a planar-named key on spatial runs, against moving every digest.
- Q4, reused assumption lines that name the planar model. Recommended: edit none, and give the
  spatial path its own wording naming omega_E cos(lat). Trade-off: a spatial copy of the lines.
- Q5, the ECI epoch and the hold rows. Recommended: keep section 5.3's epoch (ECI and ECEF
  coincide at run clock t = 0) and write spatial hold rows and logged track events that turn
  with the ground. Trade-off: a spatial hold function beside the shared one, and `from_track`
  for the logged track events.
- Q6, what `SpatialSearchContext` offers beyond `RecordingProblem`. Recommended: nothing in
  SP3, with the file saying what it leaves out. Trade-off: SP4 adds it if the S1 re-check
  carries SP7's structure.
- Q7, the gravity turn's law, on which the bound |dP*| < 5 kg rests (added by C1's physics
  review, pass 2). Recommended: a zero-yaw gravity turn (e the projection of v_rel on the
  launch plane) in place of section 5.7's full vector. Trade-off: a steering row of 0.0095
  m/s over stage 1 that the payload does not feel, against a bound that does not hold: on
  that review's replica, not a run and not a finding, section 5.7 as written gives -20.2
  kg on the pad and -11.1 kg on silo_cold, and zero yaw -0.001 kg on both. The answer also
  settles which speed starts the kick (phase file, section 7, Tolerances). Any later
  change to the law or the bound followed that probe, so it is not a blind
  pre-registration; if neither changes, the expectation is still written after that
  number (phase file, 5.10 and Q7).

**Five of SP3's gates changed reading at C1** (section 5, Inventory; SP3 section 7,
Tolerances; the SP7 file's deviation 59). Recommended: confirm them in step 0. Trade-off: a
tightened setting; a smooth test air whose pressure step 0 chooses (tests/conftest.py's
`exp_atmosphere` has none); a shipped-air comparison read 10, 1,000 and 1,000 times looser
than the design on the states, J rows and event times (1e-8, 1e-6 and 1e-5 s against 1e-9,
1e-9 and 1e-8 s); and readings against a scale. The replicas show a correct model failing
the design's lines on S1.2's rows and orbit gate and on both S1.4 lines; S1.2's pointwise
dV/dt and S1.3's kick event take the scale reading by analogy. All are sized on reviews'
replicas, not runs.

**The session-made decisions still to report, for the user to confirm or change** (TODO.md's
decisions log holds each in full; section 2 places the earlier ones). Recommended: confirm
all eight. Each is built and tested, and those that
reach a registered run (D-SP7-49 to D-SP7-52, D-SP7-54, D-SP7-55) change only by an amendment
and a re-run.

- D-SP7-49: every watch of the linear motor's push is a terminal event, so each kink of the
  drive force lies on a sub-phase boundary (not taken: logging from a non-terminal pass).
- D-SP7-50: the force law's power cap applies to the flown, tapered force (KI-045).
- D-SP7-51: after a release below the mouth the vehicle flies the shaft in the open atmosphere
  and the shaft has a floor; a fall back ends there as an impact, with no catch modelled.
- D-SP7-52: a flown push charges the larger of the rise formula and the flown history's
  single-mode bound.
- D-SP7-53: dm' is about -4e-4 kg/kg on the cold force-law case; the tests assert design 4.4's
  floor, and no test push was chosen to make the sign positive.
- D-SP7-54: file B's sealed bore is 5.24 m, not the 3.7 m of the sources note, which the 5.2 m
  fairing cannot pass.
- D-SP7-55: file B's rules take M at full precision, 572,354.3962434949 kg, not the rounded
  572,354.4 kg.
- D-SP7-56: test_appform_is_pure_and_off_the_run_path is split as KI-035 split the scene's
  guard, and `QUICK_S` stays at 5 s.

**Waiting on the user, not blocking:**

- KI-026. Recommended: upload assets/brand/social-preview.png by hand under GitHub Settings,
  General, Social preview; GitHub has no API for it. Trade-off: until then the repository's
  link preview is GitHub's default.
- B-001, results retention. Recommended: keep every directory for now; deleting results needs
  the user's OK. Trade-off: disk space (SP7's nine directories alone hold about 680 MB).

## 7. State of the project

**Commits of the session**, newest first (`git log --oneline 22c62e9..HEAD` is the full list):

- the bookkeeping commit `Close SP7: trackers, handoff, next phase file` (step C2's; it holds
  this file);
- C1's tracker commit; ead6e38 C1 (the documents of the close);
- d03367b S8 trackers; 3a07f07 S8 (the public face);
- cf6d1db S7d trackers; cd14968 S7d (the fast tier under load);
- 6940273 the demo runs' four summaries (from 6cf0fd2);
- 6cf0fd2 S7c trackers; 9fe125c S7c (the program-level wording in code);
- 21bad0b S7b trackers; e5f64b3 S7b (the note completed); b291518 S7b (the two check scripts);
- 642e11e S6b trackers; 331891d S6b (file B, part 2 of the pre-registration);
- c99c683 the handoff at checkpoint 2; cc16ec0 S5a trackers; 2bd40bd S5a (the sealed shaft's
  wording); f120347 S5 trackers; 460c4d6 S5 (the sealed shaft);
- e12e524 S4b trackers; b0fcc31 S4b (the transform on linear-motor pushes); 8e4da84 S4a
  trackers; 7cdc24a S4a (target-speed release, the readers, the shaft floor); 52b6c6b S4
  trackers; 8c4b41a the merge; 25967be S4 (the linear motor);
- 1bc8ea7 S7a trackers; 6fa2ff0 S7a (the note and the run summaries); a5b21b8, 9b91473 and
  b82417b the S7a scripts; 2b343d7 S3c trackers; 74eb3c8 Amendment 1 (D-SP7-48); 77e1691 and
  1e4c732 S3c (the sweep's no-offload record); 0a12c36 the three S7a findings scripts;
- ac5c6bd the handoff at S7a; 1b5f9d4 S6a trackers; cbbd7bc S6a (files A and C, part 1);
- f10cf58 S3a trackers; 0a16a89 S3a; 77eb006 S3b trackers; 216a79c S3b; 6180ae1 S3 trackers;
  889f6ea S3; 15b4e6e D-SP7-41; 792dd69 S2 trackers; 45e39d4 S2; 4494fe1 S0 trackers; 81e045d
  S0; 1945144 S1 trackers; a3bd183 S1;
- a7c9f0a Start SP7.

**Tests and lint.** Full suite at the close: `<C2:full-suite-count>`; ruff:
`<C2:ruff>`. The last counts before C2: 2,271 tests, 2,217 fast and 54 slow, all passing (S7d's
gate, cd14968; S8's gate ran the fast suite again, 2,217).

**Results directories** on disk. Only each directory's top-level summary.md is tracked; a fresh
clone has no CSVs. Sizes by `du -sh` on 2026-11-05.

| Directory | What | Notes |
|---|---|---|
| results/silo_structure_2d/20261016T171513Z | Run A (git 1b5f9d4, clean); the note's record | 135 MB |
| results/silo_structure_2d/20261016T171522Z | Sweep A, first run (git 1b5f9d4, clean) | 40 MB; kept; it reproduces cell for cell in the re-run |
| results/silo_structure_2d/20261019T172327Z | Sweep A re-run under Amendment 1 (git 2b343d7, records dirty, deviation 45) | 40 MB; the note cites its shortfalls |
| results/silo_structure_2d_readme/20261016T171529Z | Run C, the README-loads fork (git 1b5f9d4, clean) | 18 MB |
| results/silo_drive_2d/20261103T231946Z | Run B, the drive cases (git 642e11e, clean) | 127 MB |
| results/silo_structure_2d/20261104T095619Z | Demo re-run of A (git 6cf0fd2, clean) | **never cited**; 135 MB |
| results/silo_structure_2d/20261104T095624Z | Demo re-run of the sweep (git 6cf0fd2, clean) | **never cited**; 40 MB |
| results/silo_structure_2d_readme/20261104T095630Z | Demo re-run of C (git 6cf0fd2, clean) | **never cited**; 18 MB |
| results/silo_drive_2d/20261104T095635Z | Demo re-run of B (git 6cf0fd2, clean) | **never cited**; 127 MB |
| results/silo_offload_2d/20261003T112934Z, results/silo_screening_2d/20260930T175743Z | SP1's run and Phase 2's screening run, the pinned records | see docs/handoff/archive/2026-10-07-SP2.md, section 7 |

The demo directories exist to show that the recorded ones reproduce (every metrics.json leaf
equal but /git/hash and /timestamp_utc, and the sweep's two index files and baseline series
in every cell, docs/demos/SP7/README.md); no finding cites them.

**Findings** (docs/findings/README.md): new in SP7, RQ1-structural-2d (preliminary), with a
dated pointer at the top of RQ1-fuel-offload-2d. Unchanged: CAL-f9-leo-2d, RQ3-silo-screening-2d,
RQ2-ignition-timing-2d, RQ6-aero-2d-preliminary and the two 1-D records.

**Open known issues that matter to SP3:** KI-001 (owned). KI-092 (a body arriving after a
404 on /cancel or /finish draws a reset; the fast tier does not cover the page's `{}` on
that path) and KI-093 (two coverage gaps of S7d): KI-092 is a defect in the app's video
routes that the fast tier no longer covers, KI-093 is two gaps in the tests; neither is on
SP3's path, and either needs a step that may edit src/ or tests/. KI-003 (update
`run_data.CALIBRATION_RECORDS` whenever the calibration is re-run; SP3 fits nothing).
KI-009 (silo_cold_lag's searched run sits near the 30 s budget; SP3 section 10, risk 6).
KI-019 and KI-031 belong to the phase that next edits replay.html, KI-040 and KI-053 to the
next that edits the scene template. Three of the open KIs from KI-043 to KI-089 reach SP3
whatever Q1 and Q2 decide: KI-049 (the delivered-thrust clamp stays unsplit in every ascent
BURN phase lit after release at p_amb > 0, at about the 1e-10 level; on a review's replica,
not a run, one step across it moves silo_cold's fairing time by up to 1.2e-6 s between two
step sequences, hence S1.4's 1e-5 s on the shipped air's event times) and KI-061 (a gravity
turn entered near the apex, which the shipped kick does not reach) come with the copy of
`phases/planar.py`, and KI-051 (a fast test that drew WinError 10053 in one burst in S4;
the preserved runs show no 10053 on it since, before or after S7d changed it, and no report
shows why it stopped) is on every gate, so a failure there is re-run alone before it is
read as real. All of that range are low; of the rest, the drive, release and sealed-shaft
items reach SP3 only if Q1 or Q2 keeps those paths, and the others are structure, reader
and test-map items. KI-094 to KI-102 are low, owned "later", none on SP3's path but KI-102:
its SP4 point is read at SP3's close, and its evidence point at SP3's start commit; until
then Q7's paths are where the user reads it.

## 8. How work is done

docs/process/SESSION_PROTOCOL.md: the start checklist (section 3), the step loop (section 4),
the end checklist (section 7). For SP3 in particular:

- Plan mode, and docs/physics.md in the same change, for anything touching the equations of
  motion, frames, events, integrator settings or loss accounting: every step of this phase.
- The planar pin (S1.0) is committed before any file under src/ is edited, with the expectation
  |dP*| < 5 kg in TODO.md. The bound is an expectation to test, not a target to tune toward.
  The bound predates Q7's probe; the expectation S1.0 commits does not, and that entry must
  say so.
- The reviewers and the standing gates are in SP3 section 7; the pass-3 rule and a gate's
  foreground rule are SP7's deviation 31, a gate's docs/physics.md line deviation 39.

The step loop as this session ran it is a workflow script outside the repository,
C:/Users/rahul/.claude/projects/D--DEV-ClaudeProjects-SpaceRocketOptimization/sp7work/step_loop.js:
one implementer from a written brief; the reviewers in parallel, three passes with a fix round
after each; verification passes up to pass 6 while majors remain; an independent gate with its
own scripts; the orchestrator commits, then the tracker commit, the push and the Pages check.
It is a working file, not a record: the protocol and the phase file are the authority, and a new
session may rewrite it. Briefs and reports go in a folder like sp7work/, never in %TEMP%.

## 9. Gotchas learned in SP7

New ones; the standing list is protocol section 11.

- **A test's clock under other projects' load.** On 2026-11-04 the fast suite failed on timing
  alone beside other projects' pytest runs: a fake encoder's chain (.bat, venv launcher, base
  python, pid file) outran a 1 s test limit. Those processes are not this session's to stop.
  S7d's rules (KI-091): shorten only the timeout under test, once its setup has finished; use
  events or counts in place of sleeps; prove each changed test by a mutation.
- **The demo's fast suite is part of the record.** It exited 1 at 6cf0fd2 and again on its re-run;
  docs/demos/SP7/ keeps both captures beside the passing one at cf6d1db, in order. A failed
  demo command is recorded and explained, never re-run away.
- **A long heredoc can come back empty** (reported by the orchestrator; no captured case).
  Besides the parse failure of protocol section 11, a long heredoc in a Bash call can return
  empty output with no error. Check that the file exists before relying on it, and write long
  scripts with the Write tool.
- **A push can fail on GitHub's side.** On 2026-11-04 `git push` failed with "Internal Server
  Error" and "fatal error in commit_refs" while GitHub's status API showed Git Operations
  degraded. C:/Users/rahul/.claude/projects/D--DEV-ClaudeProjects-SpaceRocketOptimization/sp7work/push_retry.sh
  retries `git push origin main` every 3 minutes, never with force; it went through on the
  first try, at 09:51:22Z.
- **A fact-check goes stale when steps follow it.** SP3's was made at 6cf0fd2, and S7d and S8
  came after it: three physics.md headings had moved, KI-090 had closed and the suite had grown
  by one. Re-validate every statement of a fact-check at the commit it is applied to. A
  document that a later step completes holds a named mark for each result that step
  produces, never the result early (as C1 did for C2).
- **Pass 3's majors get more rounds** before the gate, and **a gate never ends its turn on a
  running command** (both deviation 31): the fast suite in three chunks (tests/test_[a-c]*,
  [d-o]*, [p-z]*), the slow tier in groups, the frozen-sets tests one per command.
- **Workflows resume from their journal** after a usage limit or a network error
  (`Workflow({scriptPath, resumeFromRunId, args})`, the same args). Stop orphaned processes
  first (protocol section 11), and only those the session started.
- **Keep working files out of %TEMP%.** A temp-folder cleanup on 2026-11-02 deleted the
  session's scratch files while a workflow was paused (deviation 53).
- **The pre-registered runs need a quiet machine**: no suite, app or agent that runs the code
  beside them, and `git status --porcelain` empty apart from results/ before they start.
- **A local site build stamps the commit's date**, not the machine's (site/build.py); the
  deployed stamp is the last commit's.

## 10. Prompt to start SP3

Paste this into a fresh Claude Code session opened in this folder. It is the same text as
section 13 of docs/phases/SP3-3d-dynamics-s1-sphere.md; if the two ever differ, the phase
file's version is the one to use.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP3-3d-dynamics-s1-sphere.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links, then the inputs the phase file links
> (docs/phases/inputs/2026-09-30-design-3d-dynamics.md first), and sections 11 and 12 of
> docs/phases/SP7-structural-mass-push-load.md for what SP7 changed in the shared modules.
>
> We are continuing launch-assist-sim. SP7 is closed: a first-order structural sizing
> model (structure.py, configs/structures/) charged into SP1's offload solve through an
> optional vehicle transform; the force- and power-limited linear motor
> (assist/linear_motor.py) with release at a target speed, the shaft floor and the sealed
> shaft; and the findings note docs/findings/RQ1-structural-2d.md (a first-order station
> sizing at central coefficients, with an assumed 0.5 s rise time, zero margin, the pad's
> unthrottled flight as the envelope and the instant release flagged, not sized; planar,
> sweep-optimized and unthrottled, on the gate vehicle with its +14.3% calibration miss:
> the modelled structure cancels most of SP1's offload, and 11.42 t of 41.26 t is left).
> This session is phase SP3: stage S1 of true 3-D dynamics, a 3-DOF point mass in ECI
> Cartesian coordinates over a rotating sphere, built beside the planar model without
> changing any planar or 1-D number. SP3 uses nothing from SP2's app or SP7's structure
> model, but its copy of phases/planar.py and its inventory include SP7's edits.
>
> Follow the session protocol. Run its start checklist: a clean tree; HEAD's subject
> "Close SP7: trackers, handoff, next phase file", SP7's closing commit (named in the
> handoff) an ancestor, and `git diff --stat <that commit> HEAD` touching only bookkeeping
> files; the fast suite green with the count recorded; the entry criteria of the phase
> file's section 4 (the pins, the two recorded payload capacities 26,054.3962 and
> 27,553.2271 kg within 0.002 kg, SP1's solver built from a problem factory); the
> inventory of section 6 re-checked against HEAD (last checked at d03367b); the open KI and
> B items owned by SP3 listed (KI-001). If the session starts in Plan mode, do the
> read-only checks first and run the suite right after approval, as the protocol's section
> 3 says.
>
> Then work in Plan mode (step 0). Confirm or refine steps S1.0 to S1.8 against the code,
> put the open questions of section 10 to me, each with your recommendation first and the
> trade-off in one line, show me the plan with the step table, the gates and the
> tolerances, and wait for my approval before writing any code. My request of 2026-10-19
> to keep working through SP3-SP6 does not replace that approval. After approval, log the
> decisions as D-SP3-nn in TODO.md, save the design under docs/phases/inputs/, and make the
> start commit ("Start SP3: status in progress").
>
> Rules for the whole session. Plan mode, and docs/physics.md in the same change, for
> anything touching the equations of motion, frames, events, integrator settings or loss
> accounting; every step of this phase does. The planar pin test (S1.0) is committed before
> any file under src/ is edited, and every new physics feature passes its closed-form test
> before any experiment uses it. Write the expectation |dP*| < 5 kg against 26,054.4 kg
> into TODO.md and commit it with the planar pin (S1.0), before any file under src/ is
> edited and so before any searched 3-D run; write docs/findings/M2M-3d-vs-planar.md at the
> end (S1.8). The bound is an expectation to test, not a target to tune toward: a
> difference outside it is reported as a miss, as plainly as one inside it. The experiment
> file is committed before it is run, the run starts from a clean commit, and no results
> directory is ever overwritten or deleted.
>
> Run every step through the loop: implementer; adversarial reviewers (a physics or
> numerics skeptic and a CLAUDE.md compliance auditor on every code step, an honesty
> auditor on S1.7's summary rows and S1.8's note); up to two fix rounds, and an extra
> round (a fixer and verification reviewers) before the gate when a step's third review
> pass still has majors (SP7 deviation 31); an independent gate that runs every command in
> the foreground, in chunks under ten minutes, never ends its turn on a running command
> and has docs/physics.md in its file list; one commit per gate; the tracker commit at
> once ("SP3 step <k>: trackers (<hash>)"); then `git push origin main` and a check that
> the Pages deployment succeeded. Standing gates on every code step (the phase file's
> section 7): fast suite green, ruff clean, the exact 1-D golden tier, SP1's planar digest
> pin, the planar output capture, the golden-dump field lists, templates/replay.html's
> sha256, the structure files' and the vented byte pins, no shipped experiment, vehicle or
> structure file edited, and from S1.0 on the S1.0 pin (its slow part run by name); the
> full suite after every step from S1.2 to S1.7.
>
> At the end, run the end checklist of the protocol's section 7: an independent gate on
> each exit criterion (a criterion stays open only with my explicit acceptance, logged as a
> decision); the full suite and ruff with the counts recorded; the demo under
> docs/demos/SP3/; the phase file closed, the board, TODO.md, CLAUDE.md (status, layout,
> the spatial frame) and README.md updated, and the public face refreshed (landing page,
> deck and its PDF, gallery, manual) with the site built locally and no broken link; the
> close-out questions to me with the recommendation first (which phase runs next: SP4 in
> the planned order); the fact-check of the next phase's file against the code; the
> handoff archived and the new one written with the next prompt; the next prompt printed
> to me; the memory updated; the cold-read check by an agent that did not write the
> documents; the closing commit; the push and the Pages deployment confirmed.
