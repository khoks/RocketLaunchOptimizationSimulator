# Program board

The work after Phases 0-2 is split into phases, each done by one fresh Claude Code session
and each ending with something that can be run or looked at (decision D-SP1-08). This file
is the board: one row per phase with its goal, what you can see at the end, status,
session date and closing commit, a one-line summary of its entry and exit criteria, and a
link to the phase file that holds the brief, the step table, the full criteria and the
session record. How a session runs is in
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). The program-level
tracker (milestones, decisions, known issues, backlog) is [TODO.md](../../TODO.md). The
split, order and designs of SP1-SP6 come from the plan the user approved on 2026-09-30
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md)). SP7
(the structural mass of the push load and a force-limited drive) was added at SP1's
close-out on 2026-10-04 and ordered after SP2 and before SP3 (decision D-SP1-18).

Last updated: 2026-10-07 (SP2 closed, commit 3a1b243, with exit criteria 7 and 11
accepted as logged misses, D-SP2-41 and D-SP2-42; SP7 next, D-SP2-40).

## Phases

Status is one of: not started, in progress (session <date>), done (<date>, commit <hash>).
The closing commit is filled in when the phase's exit criteria pass.

Rows are in the planned run order (D-SP1-07, amended by D-SP1-18): SP1, SP2, SP7, SP3,
SP4, SP5, SP6. Phase numbers are identifiers, not positions, and are never renumbered.

| Phase | Title | Goal | What you can see at the end | Status | Session date | Closing commit | Phase file |
|---|---|---|---|---|---|---|---|
| SP1 | Launch settings and fuel offload at fixed payload (planar model) | Tracking system; launch settings (silo depth with exit speed, ramp start); fuel-offload solver; the headline finding on the planar model | A findings note with the % of propellant replaced; `launchsim run experiments/silo_offload_2d.yaml` reproducing it; a replay page of the full pad against the offloaded silo | done (2026-10-04, commit `5007515`) | 2026-09-30 to 2026-10-04 | `5007515` | [SP1-fuel-offload-planar.md](SP1-fuel-offload-planar.md) |
| SP2 | Local app and 2-D launch scene | A local app: form, Launch button, the 2-D scene inside it | `launchsim app`: set depth, ramp start and offload, press Launch, watch pad and silo side by side | done (2026-10-07, commit `3a1b243`) | 2026-10-05 to 2026-10-07 | `3a1b243` | [SP2-launch-app-2d-scene.md](SP2-launch-app-2d-scene.md) |
| SP7 | Structural mass of the push load, and a force-limited drive (planar model) | Charge the structural mass the 4 g full-stack push needs with a first-order sizing model, so the offload and payload findings carry a modelled structural cost instead of only the assumed penalty rows; the drive realism that interacts with it (force- and power-limited linear motor, carriage mass, modelled braking, the silo air column) | SP1's headline offload re-solved with a modelled structural mass and its uncertainty band, beside the penalty rows; the stroke at a fixed exit speed with the structure charged; a linear-motor silo run; the findings note updated | not started | | | [SP7-structural-mass-push-load.md](SP7-structural-mass-push-load.md) |
| SP3 | 3-D dynamics S1, a 3-DOF point mass over a rotating sphere | The first stage of true 3-D dynamics, validated against the planar model | Tests green; a model-to-model record against the planar gate; a 3-D run from the CLI | not started | | | [SP3-3d-dynamics-s1-sphere.md](SP3-3d-dynamics-s1-sphere.md) |
| SP4 | 3-D scene in the app, and the headline re-checked on S1 | The launch shown on a globe from the 3-D time series; the offload experiment re-run on S1 | The launch on a globe; offload % on the planar and the 3-D model | not started | | | [SP4-3d-scene-and-recheck.md](SP4-3d-scene-and-recheck.md) |
| SP5 | 3-D dynamics S2, oblate Earth (J2, ellipsoid) | The Earth model extended to an ellipsoid with J2 | Offload % on the oblate model; the effects of flattening and J2 separated | not started | | | [SP5-3d-dynamics-s2-oblate.md](SP5-3d-dynamics-s2-oblate.md) |
| SP6 | 3-D dynamics S3, the 6-DOF verification fly-out | A 6-DOF verification fly-out of the 3-DOF-optimised payload and guidance | Attitude, gimbal and cold-start controllability results; attitude shown in the 3-D scene | not started | | | [SP6-3d-dynamics-s3-6dof.md](SP6-3d-dynamics-s3-6dof.md) |

### Entry and exit criteria (one line each)

A summary for orientation. The criteria that are checked are the full text in each phase
file: section 4 (entry) and section 8 (exit). If this table and a phase file disagree, the
phase file wins and this table gets fixed.

| Phase | Entry criteria (phase file, section 4) | Exit criteria (phase file, section 8) |
|---|---|---|
| SP1 | Phases 0-2 closed; clean tree at 2eebcae; fast suite green and ruff clean; the plan approved; the inputs present; the shipped planar experiments and the gate vehicle file unedited; the previous handoff archived | 8 criteria: tracking system and the SP2 handoff; the exit-speed option and the four ramp-start settings pass their closed-form tests; the offload solver passes its toy closed forms, the stage-1 pad control and the P_ref reproduction; run and sweeps from a clean commit with no `bug_suspect`; the findings note passes the honesty review; full suite green with the 1-D golden tier and the planar digests unchanged; demo recorded; the public repository current and the Pages site live with SP1's finding |
| SP2 | SP1 closed; the settings, the `offload:` block, the in-memory entry point and replay of offload runs exist with tests; run data on disk; clean tree and green suite with the pins; section 6 re-checked and the prompt finalised | 17 criteria (approved 2026-10-05, D-SP2-38): the app starts on 127.0.0.1 only and a second server on its port fails; a launch works for every setting and the screening presets; same numbers as SP1's recorded run; refusals write nothing; the scene matches the run data; the offload is visible and right; honest labels, with the exploratory mark on every export; browse and replay; the pad baseline is cached; one loader and the fixes; tests and guards; Pillow the only new dependency and no request off the machine; documents and public face; demo recorded; the standalone scene page and an MP4 export; the scene is watchable; requests from another origin are refused. Closed with 7 and 11 as accepted misses (D-SP2-41, D-SP2-42) |
| SP7 | SP2 done (SP1 done is enough if the user moves SP7 earlier, logged as a decision); clean tree and green suite with the pins and the two recorded payload capacities; SP1's offload solver, penalty field and decomposition, with the slow test that re-solves the headline; SP1's run data on disk; section 6 re-checked; `gh` and Pages green; the app's basis kept valid (`launchsim app` copies experiments/silo_offload_2d.yaml; criterion 8) | 10 criteria (draft): validation tests before use; coefficients sourced or assumed, vehicle and experiment files unchanged; nothing validated moved (pins, P*, SP1's headline with the model off); the headline offload re-solved with a modelled structural mass and its uncertainty band, verified, no `bug_suspect`; the stroke series and linear-motor cases reported; the findings note updated after the honesty review; physics.md; full suite; demo; close-out (public face, the next phase's file, handoff, memory) |
| SP3 | SP1 done (SP2 too in the planned order, but nothing from it is used); clean tree and green suite with the pins and the two recorded payload capacities; SP1's offload solver built from a problem factory; section 6 re-checked | 12 criteria: the planar pin committed before any edit under src/; frames, dynamics, guidance, planner and search tests; loss identity, closure and convergence; a spatial run from the CLI; the model-to-model record against its pre-registered expectation; run times recorded; full suite; demo and the SP4 handoff |
| SP4 | SP2 and SP3 done; clean tree and green suite with the pins; the model-to-model record with no open `bug_suspect`; a spatial results directory on disk; SP1's solver takes a problem factory; the app starts; sections 5 and 6 rewritten against the code | 9 criteria: a spatial run shown on a globe with three cameras; visual QA against the run data; payload tests; the three.js decision logged; the spatial offload file and expectation committed before the run; the S1 offload solved with its checks; the findings note with planar and S1 side by side; full suite and pins; demo and the SP5 handoff |
| SP5 | SP3 done; SP4 done for the offload re-check (step R), otherwise step R is deferred; clean tree and green suite with the pins; the S1 tests and the model-to-model record; section 6 re-checked | 11 criteria: an S1 pin committed before any spatial module is edited; geodesy; J2 gravity and orbit rates; surface gravity; the zero-J2, zero-flattening limit equals S1; loss identity and convergence; the target definition stated; the S2 expectation committed before S2 is runnable, and the decomposition record; the offload on `wgs84_j2`; full suite; demo and the SP6 handoff |
| SP6 | SP5 done; SP4 done for step V and for the offloaded fly-out case; clean tree and green suite with the pins and the S2 tests; the 3-DOF results to fly on record; the `SpatialPlanner` model kit exists; section 6 re-checked | 13 criteria: mass properties; rotational core; aerodynamics; controller; prescribed-attitude mode reproduces S1 and S2; loss identity; the vehicle fork with every number sourced or assumed; fly-out only; the fly-outs from a committed experiment; the findings note as sensitivities; attitude in the 3-D scene; full suite; demo and the next phase agreed with the user |

### Later (no phase file yet)

These follow the README roadmap. Each gets an SP number and a phase file when it is
scheduled.

| Roadmap item | Content | Status |
|---|---|---|
| README Phase 3: the remainder | Curved ramp with the frictionless circular-arc test, cable winch with the cable frequency test, friction (zero normal load on a vertical straight track, so it belongs with the curved and inclined tracks), tilted-exit abort with Coriolis, engine shutdown transients (TODO.md B-006, B-008, B-009, and friction from B-007). The structural mass for the 4 g push and the linear motor moved to SP7 (D-SP1-18); SP7 also proposes to take the air column, modelled braking and release at a target speed, which its Plan mode confirms | not scheduled |
| README Phase 5: fair comparison | Optimal-control ascent for each configuration; headline results re-run with optimized guidance | not scheduled |
| README Phase 6: hobby scale | RocketPy model of a real rocket with an assist before the rail; apogee within ±5% | not scheduled |

**The structural-mass model decides whether the headline survives, and it is now SP7.**
No structural mass is charged today for the 4 g full-stack push. SP1's finding
(docs/findings/RQ1-fuel-offload-2d.md) is 41.26 t of stage-1 propellant, 10.04% of
stage 1, before any structural mass; its assumed penalty rows (+2, +4, +8.1 t of stage-1
dry mass; D-SP1-04) leave 32.29, 22.88 and 1.98 t, and about 8.5 t (extrapolated) leaves
nothing. In payload terms the 2-D findings put the break-even at about 8.1 t
(docs/findings/RQ3-silo-screening-2d.md). Until 2026-10-04 the item sat after the 3-D work
because of the order chosen (D-SP1-07). At SP1's close-out the user moved it ahead of the
3-D dynamics as SP7, after SP2, because the structural cost decides whether the 10%
survives while the 3-D models are expected to move it by kilograms (D-SP1-18).

README Phase 4 (experiments and findings for research questions 1-8) is not a separate
row: findings are produced inside the phases (SP1 writes RQ1 on the planar model; SP7
re-judges it against a modelled structure; SP4 and SP5 re-check it on the 3-D models).

## Dependency order

The planned order is SP1, SP2, SP7, SP3, SP4, SP5, SP6 (D-SP1-07; SP7 inserted after SP2
and before SP3 by D-SP1-18 on 2026-10-04). What each phase needs:

| Phase | Needs | Why |
|---|---|---|
| SP1 | Phases 0-2 (done) | Builds on the planar model, the payload search and the constant-acceleration silo push |
| SP2 | SP1 | The app's form drives SP1's settings (depth, exit speed, ramp start) and calls SP1's offload entry point with an in-memory experiment |
| SP7 | SP1; SP2 only by the order chosen (D-SP1-18) | Charges a modelled structural mass on SP1's offload solve (through SP1's problem factory or the vehicle at each offload) and on the payload search, beside SP1's penalty rows; the linear motor plugs into the assist registry and replaces the `linear_motor` placeholder SP1 left. Nothing from SP2's app is used. If SP7 runs before SP2, SP2's inventory moves (config.py, the assist package, the offload reporting) and SP2's re-check catches it |
| SP3 | SP1 closed; nothing from SP2 or SP7 | New dynamics written beside the planar code as the earlier phases leave it, and pinned against the planar gate; no app or scene code is used. In the planned order it starts after SP7, so its copy of the planar code and its inventory include SP7's edits (config.py, the assist package, the offload reporting); the session before SP3 re-checks them |
| SP4 | SP2 and SP3 (and SP1's offload solver) | The globe scene lives in the SP2 app and draws SP3's spatial time series; the offload re-check runs SP1's solver on SP3's model (SP1 builds the solver from a problem factory so the 3-D models can reuse it). If SP7 has run, whether the S1 re-check also carries SP7's modelled structure is settled when SP4's file is fact-checked |
| SP5 | SP3; SP4 for the offload re-check (step R) | The oblate Earth model extends S1; the zero-J2, zero-flattening limit must equal S1. Step R copies SP4's spatial offload experiment file and extends SP4's 3-D findings note; if SP5 runs before SP4, step R moves to SP4 (SP5 entry criteria 1 and 5) |
| SP6 | SP5; SP4 for step V and for the offloaded fly-out case | The 6-DOF fly-out flies the payload and guidance optimised on the 3-DOF models and must reproduce S1/S2 in prescribed-attitude mode. The attitude display (step V) lives in SP4's scene, and the offloaded silo run's 3-DOF result on a spatial model comes from SP4 or from SP5 step R (SP6 entry criteria 1 and 4) |

```text
SP1 --> SP2 ------> SP4 . . . . . . . . . .
 |\                 ^      :              :
 | `--> SP3 --------'      : step R only  : step V and the
 |       \                 v              v offloaded fly-out
 |        `-------------> SP5 ---------> SP6
 |
 `----> SP7
```

Solid arrows are needed by the whole phase; dotted ones only by the steps named. The
diagram shows needs, not the run order: SP7 needs only SP1 and runs after SP2 and before
SP3 by decision (D-SP1-18).

SP3 needs nothing from SP2 or SP7, and SP7 needs nothing from SP2, so the order of SP2,
SP7 and SP3 can change at a session boundary; that is a user decision, logged in TODO.md.
SP4 waits for SP2 and SP3. SP5's dynamics and its decomposition runs need only SP3; its
offload re-check (step R) needs SP4. SP6's dynamics, the pad fly-out and the full-load
silo fly-outs need only SP5; its attitude display (step V) and the offloaded silo fly-out
need SP4.

## Inputs (docs/phases/inputs/)

Dated source material the phase files were written from. The 2026-09-30 files were
produced in the SP1 planning session, and line numbers in them are for commit 2eebcae;
the 2026-10-02 and 2026-10-03 files were written during SP1's steps; the 2026-10-05 files
and folders were produced in SP2's step A0, and line numbers in them are for commit
b69ff0c. Line numbers drift as the code changes. The files are a record and are not
edited; corrections go into the phase files. SP7 has no input yet: its design is made in
its own Plan mode and saved here then.

| File | What it is | Feeds |
|---|---|---|
| [2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md) | The plan the user approved: the decisions taken, the program split, the tracking system, the SP1 step table with gates and exit criteria, and the designs for SP2-SP6. The source of truth for scope | all phase files, this board, the protocol |
| [2026-09-30-design-settings-and-offload.md](inputs/2026-09-30-design-settings-and-offload.md) | Design for the launch settings and the fixed-payload offload: claim check against the code, design decisions, steps, risks, effect on validated numbers | SP1 |
| [2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md) | Design for true 3-D dynamics in three stages (S1 sphere, S2 oblate, S3 6-DOF): coupling to the planar layout, equations, gates, calibration and comparability, outputs, runtime, risks, size | SP3, SP4, SP5, SP6 |
| [2026-09-30-survey-config-search-compare.md](inputs/2026-09-30-survey-config-search-compare.md) | Code survey of config, search, the run pipeline, comparison, summary and vehicle, with the tests that must stay green and the constraints that make changes awkward | SP1 |
| [2026-09-30-survey-ignition-assist-physics.md](inputs/2026-09-30-survey-ignition-assist-physics.md) | Code survey of ignition timing, the silo assist, the phase engine, release mapping and events, with the closed forms for the ramp-start conversions | SP1 (steps 2-4) |
| [2026-09-30-survey-animate-replay-visuals.md](inputs/2026-09-30-survey-animate-replay-visuals.md) | Code survey of animate, replay, the run data on disk and what a launch scene needs (loaders, missing geometry, objects after separation), with a recommendation for organising the scene code | SP2 (re-checked at SP1's close, because SP1 touches replay and the pipeline) |
| [2026-10-02-source-rp1-heating-value.md](inputs/2026-10-02-source-rp1-heating-value.md) | Source note: the RP-1 net heat of combustion used by the offload energy comparison | SP1 (step 8) |
| [2026-10-03-sp1-preregistration.md](inputs/2026-10-03-sp1-preregistration.md) | SP1's pre-registration of the offload experiments (with Amendment 1): what is registered, the expected readings, the blocking checks | SP1 (steps 8 and 9); the model for SP7's pre-registration (SP7 step S6) |
| [2026-10-05-SP2-design.md](inputs/2026-10-05-SP2-design.md) | The SP2 design the user approved on 2026-10-05 in step A0 (the second version of the plan): the start checklist, decisions D-SP2-01 to D-SP2-38, the design of the run-data module, the scene, the launch function, the server, the app page and the video, the step table with its deferral order, the 17 exit criteria, verification and risks. It supersedes sections 5, 7 and 8 of the SP2 phase file where they differ | SP2 |
| [2026-10-05-SP2-survey/](inputs/2026-10-05-SP2-survey/README.md) | Nine read-only code surveys made at b69ff0c (README.md and 01 to 09): the re-check of the SP2 inventory, the run path, config and form, the replay template and the brand, the run data on disk, the move plan for `run_data.py`, the server and worker, documents, site and test conventions, and the scene's arithmetic tried on recorded runs. The scratch scripts they mention are not in the repository | SP2 (the design; section 6 of the phase file; the evidence for TODO.md KI-030 to KI-033) |
| [2026-10-05-SP2-review/](inputs/2026-10-05-SP2-review/README.md) | Six independent reviews of the first draft of the SP2 design (numerics, honesty, compliance, security, delivery, interaction design): 2 blocker, 49 major and 31 minor findings, folded into the approved second version | SP2 (the design; the evidence for TODO.md KI-034) |
| [2026-10-05-SP2-mockups/](inputs/2026-10-05-SP2-mockups/README.md) | The two mock-ups the user approved with the design: one frame of the scene, one second before release (`scene-frame.svg`), and the app page (`app-page.html`). Every number in them is illustrative | SP2 (D-SP2-08; steps A3 to A5) |

## How to add a phase

1. Ask the user first if the phase is new scope or changes the order (CLAUDE.md "ask
   before expanding scope"); log the answer in TODO.md as a decision (D-<phase>-<nn>).
2. Take the next free number. Numbers are identifiers, not positions: a phase inserted
   between two others keeps its new number and the order is stated in "Dependency order".
   Numbers are never reused or renumbered.
3. Create `docs/phases/SP<n>-<slug>.md` with the thirteen sections of the phase file
   template, in order: 1 Goal and what you can see at the end; 2 Scope and out of scope;
   3 Decisions already taken; 4 Entry criteria; 5 Design; 6 Inventory of the code this
   phase touches; 7 Steps; 8 Exit criteria; 9 Demo script; 10 Risks and open questions;
   11 Session log; 12 Deviations from the plan; 13 Prompt to start this phase. Copy the
   layout from an existing phase file. Status line: "not started".
4. Put the design and any code survey it rests on under `docs/phases/inputs/` with a date
   prefix and the commit its line numbers were checked at; link them from section 5.
5. Write the exit criteria before the phase starts, each one checkable by an independent
   gate, and a demo script whose output goes to `docs/demos/SP<n>/`.
6. Add a row to the phase table above and to the dependency table; move the matching
   "later" row out if the phase comes from the README roadmap.
7. Update TODO.md (milestone, current and next phase). If the new phase becomes the next
   one to run, update `docs/handoff/NEXT_SESSION.md` and the previous phase's close-out so
   its fact-check and prompt target the new phase.
8. Mark the section 13 prompt "draft, the previous session finalises it" unless the phase
   is the next to run.
