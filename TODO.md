# Work tracker

Program-level tracker for launch-assist-sim: milestones, the current phase, priorities,
backlog, decisions log, known issues and findings so far. Since 2026-09-30 the work runs as
one fresh Claude session per phase (D-SP1-08). The step tables of the SP phases live in the
phase files under docs/phases/; the Phase 0-2 step tables stay here as history.
Status marks: [x] done, [~] in progress, [ ] not started, [!] blocked or needs a decision.
IDs: decisions D-<phase>-<nn>; known issues KI-nnn (severity low|medium|high, status
open|closed|wontfix, owner phase); backlog B-nnn (priority P0-P3, target phase). Numbers are
assigned here and never reused; entries are closed or superseded in place, never deleted.
Last updated: 2026-10-05 (SP2 in progress: step A1 done, 9579f89; KI-002, KI-016, KI-017 closed).

## Program

Current phase: **SP2, in progress (session 2026-10-05)**. In step A0 the user answered Q1
to Q7 and approved the design saved as docs/phases/inputs/2026-10-05-SP2-design.md
(decisions D-SP2-01 to D-SP2-38 below). Its step table (13 steps, A0 to A8, with two
checkpoints) and its 17 exit criteria are in docs/phases/SP2-launch-app-2d-scene.md
(sections 7 and 8), with the session log (section 11). SP1 closed on 2026-10-04 (step 10 of
docs/phases/SP1-fuel-offload-planar.md; its closing commit is on the program board). A new
session resumes SP2 from docs/handoff/NEXT_SESSION.md and the step table of the phase file
(docs/process/SESSION_PROTOCOL.md section 10). Order after SP2 (D-SP1-18): SP7 (structural
mass of the push load and a force-limited drive), then SP3, SP4, SP5, SP6.

- How a session runs (start checklist, step loop, end checklist, ID conventions):
  [docs/process/SESSION_PROTOCOL.md](docs/process/SESSION_PROTOCOL.md).
- Program board (status, what each phase shows, dependency order, inputs, and a one-line
  summary of each phase's entry and exit criteria; the full criteria are in each phase
  file, sections 4 and 8): [docs/phases/README.md](docs/phases/README.md).
- Entry point for a new session: [docs/handoff/NEXT_SESSION.md](docs/handoff/NEXT_SESSION.md);
  earlier handoffs are in docs/handoff/archive/.
- The approved plan (2026-09-30):
  [docs/phases/inputs/2026-09-30-SP1-approved-plan.md](docs/phases/inputs/2026-09-30-SP1-approved-plan.md).

| Phase | One line | Status | Phase file |
|---|---|---|---|
| SP1 | Tracking system; launch settings (silo depth with exit speed, ramp start); fuel-offload solver; the headline finding on the planar model | done (2026-10-04, commit `5007515`) | [SP1-fuel-offload-planar.md](docs/phases/SP1-fuel-offload-planar.md) |
| SP2 | Local app (`launchsim app`) with the 2-D launch scene, a standalone scene page (`launchsim scene`) and an MP4 export | in progress (session 2026-10-05) | [SP2-launch-app-2d-scene.md](docs/phases/SP2-launch-app-2d-scene.md); approved design: [2026-10-05-SP2-design.md](docs/phases/inputs/2026-10-05-SP2-design.md) |
| SP7 | Structural mass of the push load and a force-limited drive (taken from README Phase 3, B-004 and B-005); runs after SP2 and before SP3 (D-SP1-18) | not started | [SP7-structural-mass-push-load.md](docs/phases/SP7-structural-mass-push-load.md) (written 2026-10-04 at SP1's close-out; its exit criteria and prompt are drafts: SP2's close finalises the prompt, SP7's Plan mode the criteria) |
| SP3 | 3-D dynamics S1: 3-DOF point mass on a rotating sphere | not started | [SP3-3d-dynamics-s1-sphere.md](docs/phases/SP3-3d-dynamics-s1-sphere.md) |
| SP4 | 3-D scene in the app; headline re-checked on S1 | not started | [SP4-3d-scene-and-recheck.md](docs/phases/SP4-3d-scene-and-recheck.md) |
| SP5 | 3-D dynamics S2: oblate Earth (J2, ellipsoid) | not started | [SP5-3d-dynamics-s2-oblate.md](docs/phases/SP5-3d-dynamics-s2-oblate.md) |
| SP6 | 3-D dynamics S3: 6-DOF rigid-body fly-out | not started | [SP6-3d-dynamics-s3-6dof.md](docs/phases/SP6-3d-dynamics-s3-6dof.md) |
| later | README Phase 3 (the rest: curved ramp, cable winch, air column, braking, tilted exit, and any part of the linear motor that SP7 does not build), Phase 5 (optimal control), Phase 6 (hobby scale) | not scheduled | none yet |

Phase numbers are identifiers, not positions: SP7 runs after SP2 and before SP3 (D-SP1-18;
docs/phases/README.md, "How to add a phase"). The structural-mass model decides whether the
headline survives. Until 2026-10-04 it sat after the 3-D work because of the order chosen
(D-SP1-07); at SP1's close-out the user moved it ahead of the 3-D dynamics as SP7, because
the structural cost decides whether SP1's 10% survives while the 3-D models are expected to
move it by kilograms (D-SP1-18).

## Milestones

- [x] M0 Plan approved: Phase 0 scaffold, Phase 1 1-D vertical rocket, concept-A silo push (2026-09-28)
- [x] M1 Phase 0 gate: 200 tests pass, all CLAUDE.md commands and the pip fallback work; first commit (2026-09-28)
- [x] M2 Phase 1 gate: rocket-equation, vertical-burn, coast-apex and staging tests pass; 269 tests green (2026-09-29)
- [x] M3 Silo push validated: straight-track, loads, assist-energy identity and failed-ignition tests pass (2026-09-29)
- [x] M4 First concept-A numbers: silo_screening_1d run + sweep, every identity line closes to ~1e-12 m/s, README-number smoke test passes (2026-09-29)
- [x] M5 Findings RQ2 and RQ3 (preliminary) in docs/findings/, status lines updated, commit (2026-09-29)
- [x] M6 Phase 2 plan (2-D ascent, rotation, drag, guidance, payload search, calibration): written 2026-09-29 from 3 designs, 9 reviews and a critique; defaults below apply unless the user objects
- [x] M7 Phase 2 gate (closed as a documented miss, accepted by the user 2026-09-30): validation tests pass; the pre-registered gate vehicle (set C) MISSES HIGH: P* 26,054 kg, +14.3%, 974 kg above the 25,080 kg band edge (set A 24,700 kg +8.3% inside; set B 25,416 kg +11.5% outside). Stopped for your decision (2026-09-30); docs/findings/CAL-f9-leo-2d.md
- [x] M8 2-D concept-A results: silo_screening_2d (with ignition sweeps), bridge and trigger studies; RQ2-2d, RQ3-2d, RQ6 preliminary (2026-09-30)
- [x] M9 Phase 2 closed: physics.md, CLAUDE.md layout and status, README status, TODO (2026-09-30)
- [x] M10 Phase V plan (Plan mode): the five decisions in the first handoff (now docs/handoff/archive/2026-09-30-phases-0-2.md, section 5). Done 2026-09-30: the plan was approved in Plan mode; decisions D-SP1-01 to D-SP1-13; the plan is docs/phases/inputs/2026-09-30-SP1-approved-plan.md
- [x] M11 Fuel replacement at fixed payload: a `propellant_offload` figure of merit and experiment on the Falcon 9 gate vehicle; % of stage-1 and total propellant replaced, energy ratio, with and without a structural penalty (headline question, user 2026-09-30). **Phase: SP1** (steps 5-9). Built as an `offload:` experiment block and a post-pass, not a figure-of-merit value (D-SP1-09); the structural penalty is parametric rows (D-SP1-04). Done 2026-10-04: docs/findings/RQ1-fuel-offload-2d.md (fd664a5), preliminary, with its caveats (see "Findings so far")
- [x] M12 Launch configuration knobs: silo depth with exit speed; thrust-ramp start by depth/speed. **Phase: SP1** (steps 1-4). The ramp start is also set by height, by event and by closed form (D-SP1-06). Done 2026-10-04 (SP1 close): steps 1-4 (e2fb6ab, 1fc92d3, 83d66dd, 1a0b2af)
- [ ] M13 Animated 2-D launch scene (`launchsim scene`): rocket, silo, plume, staging, camera. **Phase: SP2**, inside the local app (`launchsim app`, D-SP1-02); a separate `launchsim scene` command is no longer the plan. Corrected 2026-10-05: the scene is inside the app, and a standalone `launchsim scene` export (an HTML page that plays with no server) and an MP4 export from the app are in SP2 again (D-SP2-01, D-SP2-30). SP2 is in progress (session 2026-10-05); its exit criteria are in the phase file, section 8
- [ ] M14 3-D view of the planar runs on a globe. Changed by D-SP1-01: 3-D now means true 3-D dynamics in three stages, **SP3 (S1), SP5 (S2), SP6 (S3)**, with the 3-D scene in **SP4**. Done when M16-M19 are done
- [ ] M15 Phase 3 assist models (linear_motor, curved track, cable winch, air column, braking, tilted exit) and the structural mass for the 4 g push. **Phase: later** (README Phase 3; no SP number yet). Changed by D-SP1-18 (2026-10-04): the structural mass for the push and a force-limited drive move to **SP7** (M20); the rest stays later
- [ ] M16 SP3 gate: 3-D dynamics S1 (3-DOF point mass on a rotating sphere); tests green, model-to-model record against the planar gate, a 3-D run from the CLI
- [ ] M17 SP4 gate: 3-D scene in the app (the launch on a globe); the offload % reported on the planar and the S1 model
- [ ] M18 SP5 gate: 3-D dynamics S2 (oblate Earth: J2, ellipsoid); offload % on the oblate model, the effects of flattening and J2 separated
- [ ] M19 SP6 gate: 3-D dynamics S3 (6-DOF fly-out); attitude, gimbal and cold-start controllability results; attitude shown in the 3-D scene
- [ ] M20 SP7 gate: the structural mass of the push load and a force-limited drive (B-004, B-005), so that the stage-1 offload SP1 reported before any structural mass (10.04% of stage 1, docs/findings/RQ1-fuel-offload-2d.md) is re-judged against a modelled structure. **Phase: SP7**, after SP2 and before SP3 (D-SP1-18). Its exit criteria are drafted in its phase file (docs/phases/SP7-structural-mass-push-load.md, section 8, written at SP1's close-out); SP2's close fact-checks the file against the code and finalises its prompt, and SP7's Plan mode fixes the tolerances marked "proposed"

## Priorities

1. P0 SP2 (in progress, session 2026-10-05): the local app with the 2-D launch scene, the standalone scene page and the MP4 export (D-SP2-01). Next step: A1, the shared run-data module (phase file, section 7).
2. P0 (standing) Physics correctness and honest tests (validation first; closed forms computed in the tests).
3. P1 SP7, after SP2: the structural mass of the push load and a force-limited drive (B-004, B-005; D-SP1-18). It decides whether SP1's 10% of stage 1 survives.
4. P1 SP3, after SP7: 3-D dynamics S1, pinned against the planar gate.
5. P2 SP4, SP5, SP6: the 3-D scene and the re-check on S1; the oblate Earth; the 6-DOF fly-out.
6. P2 later: the rest of README Phase 3 (B-006 to B-009), Phase 5, Phase 6. Can be moved up at a session boundary.
7. P3 (standing) Polish: plots, docs completeness, slow-test hygiene.

Met earlier (kept as history):

- P1 Phase 0 and Phase 1 gates with the CLAUDE.md commands working on Windows (M1, M2).
- P2 Concept-A numbers and the two preliminary findings notes (M4, M5).
- P0 SP1 headline: the user's question, % of rocket propellant the silo push replaces at fixed payload on the Falcon 9 model, with caveats (stage 1 is the only headline; penalty rows and sensitivity beside it). Met 2026-10-04 (M11; docs/findings/RQ1-fuel-offload-2d.md).

## Backlog

Open work that no phase has taken yet. Each item came from "Todo (near term)" or "Future
items" below, where the original wording is kept.

| ID | Priority | Target phase | Status | Item |
|---|---|---|---|---|
| B-001 | P3 | any session boundary (needs the user) | [!] | Results retention: three run+sweep pairs from 2026-09-29 have tracked summaries (cited pair 103623Z/103634Z, reviewer pair 104503Z/104510Z, gate pair 105657Z/105707Z); decide whether to keep only cited pairs (deleting results needs your OK per CLAUDE.md) |
| B-002 | P3 | none | [x] closed 2026-09-30 | Phase 2 prep: re-source the F9 propellant loads and stage-2 dry mass in the calibration fork. Met by the Phase 2 mass sets B and C (D-P2-01, steps 18 and 26): configs/vehicles/generic_f9_class_2d.yaml carries the FT-table values (stage 1 410.9 t, stage 2 4.0 t dry and 107.5 t) with sources. The box was not ticked at the Phase 2 close; checked against the file on 2026-09-30 |
| B-003 | P2 | later (README Phase 5, with the optimized ascent) | [ ] | Throttling (max-Q is reported unthrottled; deferred by D-P2-05). The offloaded silo run's max-Q can exceed the pad's and is reported, not constrained |
| B-004 | P1 | SP7 (D-SP1-18, 2026-10-04; was: later, README Phase 3) | [ ] | Structural mass for the 4 g full-stack push and the interface-hardware mass penalty. Decides whether the headline survives; SP1 shows it only as parametric rows (D-SP1-04) |
| B-005 | P1 | SP7 for the force-limited drive (D-SP1-18, 2026-10-04); any remainder later (README Phase 3) | [ ] | `linear_motor`: force- and power-limited drive with efficiency. Needed before the hot-start question can be answered |
| B-006 | P2 | later (README Phase 3) | [ ] | Curved TrackGeometry and the frictionless-arc test; `cable_winch` (and the cable frequency test) |
| B-007 | P2 | later (README Phase 3) | [ ] | Air-column piston, friction, modelled carriage braking, release at a target speed |
| B-008 | P2 | later (README Phase 3) | [ ] | Tilted-exit abort with Coriolis |
| B-009 | P3 | later (README Phase 3) | [ ] | Engine shutdown transients |
| B-010 | P3 | later | [ ] | Parquet time series |
| B-011 | P3 | later | [ ] | Multiprocessing sweeps (`--jobs`; deferred by D-P2-05 unless an experiment exceeds 30 min serial; SP1's estimate is about 15 min for the run and 17 min for the sweeps) |
| B-012 | P3 | later | [ ] | Notebooks |
| B-013 | P2 | later (README Phase 5) | [ ] | optimize.py: optimal-control ascent; headline results re-run with optimized guidance |
| B-014 | P3 | later (README Phase 6) | [ ] | RocketPy comparison at hobby scale |
| B-015 | P1 | SP1 for RQ1 (planar); SP4 and SP5 for the 3-D re-checks; later for RQ4, RQ5, RQ7, RQ8 | [ ] | Findings for RQ1-RQ8. Preliminary notes exist for RQ2, RQ3 and RQ6 (concept A); RQ1 is SP1 step 9 (docs/findings/RQ1-fuel-offload-2d.md; written 2026-10-04, fd664a5, preliminary, the fuel-replacement form on the planar model) |

## Todo (near term)

Kept as written. Open items now carry a backlog id; their status is in the backlog table.

- [x] Plan Phase 2 in Plan mode (equations of motion, frames, events): PlanarDynamics2D, rotation and the 465.1 m/s release test, atmosphere in the RHS, drag and back-pressure, guidance, payload bisection, elliptical-orbit test, calibration fork of the F9 file.
- [x] Won't fix: track-normal g of 6e-17 on vertical tracks is cos(pi/2) roundoff; the summary prints 0 and a clamp would need a magic tolerance.
- [x] config.SweepPoint.sweep_index is now 1-based like the sweep_<n> directories (test added).
- [!] (B-001) Results retention: three run+sweep pairs from 2026-09-29 have tracked summaries (cited pair 103623Z/103634Z, reviewer pair 104503Z/104510Z, gate pair 105657Z/105707Z); decide whether to keep only cited pairs (deleting results needs your OK per CLAUDE.md).
- [x] (B-002, closed 2026-09-30 on the evidence in the backlog table) Phase 2 prep: re-source the F9 propellant loads and stage-2 dry mass in the calibration fork (FT spec sheet values differ from the README generics).

## Future items (deferred, with hooks in place)

Kept as written, with the backlog ids the open parts now carry.

- Phase 2: PlanarDynamics2D, Earth rotation (omega_p r release mapping, 465.1 m/s test, h0 gravity form), atmosphere in dynamics, drag, back-pressure, guidance (pitch kick, gravity turn, linear-tangent), payload bisection, max-Q, insertion, elliptical-orbit test, calibration fork of the F9 file, throttling. (Done in Phase 2, M7-M9, except throttling: B-003.)
- Phase 3: linear_motor, curved TrackGeometry and the frictionless-arc test, cable_winch, air-column piston, friction, modelled carriage braking, release at a target speed, tilted-exit abort with Coriolis, interface-hardware mass penalty, engine shutdown transients. (B-004 to B-009.)
- Later: parquet, multiprocessing sweeps, notebooks, optimize.py, RocketPy comparison, findings for RQ1-RQ8. (B-010 to B-015.)

## Decisions log

Oldest first; a new phase appends its group at the end. Decisions made before the id system
got their ids on 2026-09-30 (D-P0, D-P1, D-P2), numbered in date order and, within one date,
in the order they were recorded. The original wording is kept.

Phase 0 (all 2026-09-28; recorded in one "Phase 0-1" list and split here by subject):

- **D-P0-01** 2026-09-28 Vehicle YAML all-Quantity (source/assumed); experiment YAML bare numbers.
- **D-P0-02** 2026-09-28 CSV time series, argparse CLI, uv_build backend, ambiance without a numpy pin.
- **D-P0-03** 2026-09-28 atmosphere.py evaluates the ICAO layer closed forms directly from ambiance's constant table (450x faster in the ODE RHS); ambiance.Atmosphere stays the test oracle at 1e-12 relative.
- **D-P0-04** 2026-09-28 results/: only the top-level summary.md of each run directory is tracked (nested sweep-point summaries are ignored).

Phase 1 (all 2026-09-28; same original list):

- **D-P1-01** 2026-09-28 constant_accel means prescribed net acceleration (drive force solved each instant); hot start therefore buys no exit speed and trades propellant for drive energy; report plainly.
- **D-P1-02** 2026-09-28 Earth rotation off in Phase 1 (omega_p = 0 on the track and in the ascent).
- **D-P1-03** 2026-09-28 Pad baseline: engines lit at t = -2 s under hold-down, full thrust at release; pad_instant and silo_instant are unphysical yardsticks.
- **D-P1-04** 2026-09-28 1-D figure of merit: stage-1 burnout speed and altitude deltas vs pad, decomposed by the loss identity; no residual-propellant metric in 1-D.

Phase 2 pre-registration (2026-09-29; defaults from the plan, each open to objection until the pre-registration commit before step 26):

- **D-P2-01** Calibration mass sets A (README), B (recorded re-sourcing scope) and C (full FT table with Block 5 thrust, version mix disclosed) are all run and reported with equal prominence; default gate C on provenance (546.3 t of 549 t launch-mass closure). Prototype disclosure: A about 25,082 kg (+10.01%, 2 kg above the band edge), C roughly +10 to +14%, B not prototyped; indicative only.
- **D-P2-02** Reference orbit 200 km circular (r_t = 6,578,137 m), 28.5 deg, due east, expendable; never moved.
- **D-P2-03** Fitted or solved in calibration: guidance outputs only (gamma*_MECO, delta, LTG a and b). Fixed inputs: A_ref 10.52 m^2 (21.24 m^2 as a bound case), Braeunig C_D(M) with PCHIP, fairing jettison at 1,135 W/m^2, 11 s staging coast, stage-2 A_e 8.6 m^2 (assumed), no throttle, no reserves. On a miss: report, checklist, stop, ask.
- **D-P2-04** Shared across runs: guidance parametrisation, gamma* grid 8-36 deg step 2, tolerances, LTG settings; gamma* sweep-optimized per run. v_k = 50 m/s and the hold-to-alignment kick were chosen with prototype knowledge; the trigger study reports best-vs-best dP*, and headlines are quoted against the pad's best v_k if it beats v_k = 50 by more than 5 kg.
- **D-P2-05** Deferred: throttling (max-Q reported unthrottled), --jobs parallelism (unless an experiment exceeds 30 min serial).
- **D-P2-06** Layout: phases/ package; sim.py split into sim, metrics, compare, summary, results_io, plots; new guidance.py, orbit.py, search.py; optimize.py stays for Phase 5.
- **D-P2-07** Output angles in _rad; degrees only in summary cells and plot labels. Nothing in results/ is deleted.

User decisions, 2026-09-30 (answers to the step-26 questions):

- **D-P2-08** Calibration miss accepted as documented: the research experiments run on the gate vehicle (set C) as is, and every finding carries the miss (+14.3%).
- **D-P2-09** Mechanism check M2 becomes diagnostic only: still computed and reported, no longer sets bug_suspect; the rocket-equation closure, the loss identity and M3-M5 still block findings. Recorded as checks.m2_role: diagnostic in the planar experiments.
- **D-P2-10** Planar max_step cap of 2 s adopted (planar flight phases only; 1-D untouched); the inner-solve acceptance tightens accordingly. Recorded as an explicit shared setting; the calibration is re-run from the amended commit so its record matches.
- **D-P2-11** These change pre-registered experiment blocks, so they are committed as a pre-registration amendment before any research run; the original freeze (c2849b7) and its calibration run stay on record.

Phase 2 build (2026-09-30), deviations from the plan recorded as built (none changes a figure of merit beyond search noise; details in docs/physics.md):

- **D-P2-12** gamma* inner-solve acceptance: 3e-6 rad as first built (uncapped noise floor from the transonic C_D knots), tightened to 3e-7 rad with the 2 s planar step cap the user approved on 2026-09-30 (capped floor about 1e-7 rad; the plan's 1e-9 rad is below any floor). The cap moved the gate pad's P* by -0.0001 kg.
- **D-P2-13** A kick that times out inside the delta inner solve maps to a sentinel instead of failing the grid point (with rotation, the bracket's 0.1 deg low end never aligns).
- **D-P2-14** refine_capped is reported as a flag, not a search failure.
- **D-P2-15** The lag startup's step cap holds for the whole lag-lit burn (silo_cold_lag costs about 2.5x the pad's RHS calls); a cap over the first few tau only is left open.
- **D-P2-16** First-step carry-over across planar phase boundaries was measured and not adopted.
- **D-P2-17** The gamma*-sensitivity diagnostic step moved into the pre-registered checks block (gamma_sensitivity_step_deg: 0.5).
- **D-P2-18** Calibration runs record the frozen-input state (last commit touching configs/ and experiments/, dirty paths); a dirty or unknown state is marked in summary.md and the CLI as not a valid calibration record.

After the Phase 2 close (this entry was recorded in the "Phase 0-1" list; moved here by its date):

- **D-P2-19** 2026-09-30 CLAUDE.md Experiments rule reworded (user request): runs share the guidance parametrisation, sweep grid and optimizer budget; free guidance parameters are sweep-optimized per run.

SP1 planning (2026-09-30; taken in Plan mode with the user, plan approved the same day):

- **D-SP1-01** 3-D means true 3-D dynamics, built in three validated stages: S1 3-DOF point mass on a rotating sphere, S2 oblate Earth (J2, ellipsoid), S3 6-DOF rigid body (user).
- **D-SP1-02** The visual tool is a local app first: form, Launch button, scenes inside it (user).
- **D-SP1-03** Fuel offload: stage 1 (headline), stage 2, and both; tanks partly filled (dry mass unchanged); fixed payload = the full-load pad's payload capacity on the same vehicle and 200 km orbit (user).
- **D-SP1-04** Structural penalty shown as parametric rows: offload re-solved with assumed extra stage-1 dry mass (+2, +4, +8.1 t) (user).
- **D-SP1-05** Silo depth: stroke_m with exactly one of net_accel_g or exit_speed_mps (user).
- **D-SP1-06** Ramp start in all of these ways: time; depth or speed on the push; height above the mouth by event; height by closed form (user).
- **D-SP1-07** Order: settings and offload solver, headline findings on the planar model, the app with the 2-D scene, then 3-D (user).
- **D-SP1-08** One fresh session per phase; each phase tested, refined and completed before the next; the previous session prepares the next one's documents, memory and prompt; work tracking matured for this (user).
- **D-SP1-09** The offload is a separate experiment block (offload:) and a post-pass, not a new search.figure_of_merit value, so no pre-registered file or budget id changes (design, approved with the plan).
- **D-SP1-10** Every offload mode is also solved on the pad (pad control); stage-2 and both-stage numbers are reported net of it; stage 1 is the only headline (design, approved with the plan).
- **D-SP1-11** Under J2 (S2) the default target is an osculating circular orbit at geocentric R_E + 200 km at cutoff; revisit in SP5 (design, approved with the plan).
- **D-SP1-12** The 6-DOF model (S3) is a verification fly-out of the 3-DOF-optimised payload and guidance, not a new search (design, approved with the plan).
- **D-SP1-13** A one-case bridge of the offload on the README-loads vehicle (inside the calibration band) is part of SP1 step 8 (approved with the plan).
- **D-SP1-14** 2026-10-02: publish the repository publicly on GitHub now as khoks/RocketLaunchOptimizationSimulator, all rights reserved (public to read; no permission to copy, modify, share or use commercially; LICENSE). The user was told that publication makes the idea public prior art (relevant to any patent filing) and chose to publish. Existing commits keep the author email; commits from now on use the GitHub noreply address (user).
- **D-SP1-15** 2026-10-02: push main to the public repository after every step's tracker commit and at every phase close (docs/process/SESSION_PROTOCOL.md section 4, item 7) (user).
- **D-SP1-16** 2026-10-02: the repository carries a logo, banner, slide deck, animation examples, a user manual (docs/manual/) and a GitHub Pages site, kept current at every phase close (protocol section 7, item 6). Added to SP1 as step P (user).
- **D-SP1-17** 2026-10-03: the pre-registered SP1 experiment keeps its full design although both commands are estimated above the earlier 30-minute guide (run about 30-50 min, sweep 39-64 min); a trim is considered only above about 90 min. The 30-minute figure was a planning convenience; the fixed-exit-speed sweep is the test of whether only exit speed matters. Session lead's call, recorded for the user to overrule (they asked for the most complete answer).
- **D-SP1-18** 2026-10-04 (SP1 close-out): SP2 (local app with the 2-D launch scene) runs next as planned. Then a new phase, SP7: the structural mass of the push load and a force-limited drive (taken from README Phase 3; B-004, B-005), inserted before the 3-D dynamics phases SP3-SP6, because the structural cost decides whether SP1's 10% of stage 1 survives, while the 3-D models are expected to move it by kilograms. Phase numbers are identifiers and are never renumbered: SP7 is ordered after SP2 and before SP3 (docs/phases/README.md, "How to add a phase"). Answers the close-out question of SP1 section 10, item 8 (the B-004 order) and amends the order of D-SP1-07 (user, the recommended option).

Notes on the SP1 planning group:

- D-SP1-01 and D-SP1-02 go beyond the first handoff's recommendation (a 3-D view of the
  planar physics on a globe; CLI-generated scenes first). The user chose true 3-D dynamics
  up to 6-DOF and a local app.
- CLAUDE.md's "ask before expanding scope (6-DOF, 3-D Earth)" was satisfied by asking: the
  questions were put to the user in Plan mode and D-SP1-01 records the answer.
- The approved plan wrote decision ids as D-nnn; the per-phase form D-<phase>-<nn> replaces
  it (docs/process/SESSION_PROTOCOL.md, section 9).

SP2 planning (2026-10-05; Q1 to Q7 answered by the user in step A0, the design approved the same day):

- **D-SP2-01** 2026-10-05 (Q1) A scene can be exported in two ways, both in SP2's scope: as a standalone HTML page written by a new command, `launchsim scene`, and as a video. This puts a `launchsim scene` command back into the plan (milestone M13) and takes the video out of the brief's out-of-scope list; how the video is made is D-SP2-30 (user; more than the recommendation, which left the video to the backlog).
- **D-SP2-02** 2026-10-05 (Q2) The app and the scene work offline: no request leaves the machine, and they use system fonts, neither vendored nor Google fonts. The replay page stays as it is and keeps its font links (D-SP2-34) (user).
- **D-SP2-03** 2026-10-05 (Q3) App runs are written to `results/app/<UTC timestamp>/`, and each one's top-level summary.md is tracked in git like every other run's (user; the brief had recommended ignoring `results/app/` wholly).
- **D-SP2-04** 2026-10-05 (Q3, follow-up) Every app summary carries an exploratory banner, and app summaries are committed at step boundaries and before any pre-registered run, so that the tree is clean when a finding run starts (user). D-SP2-12 fixes the banner and D-SP2-37 the commit the summaries go in.
- **D-SP2-05** 2026-10-05 (Q4) The form's presets are SP1's configurations (the pad alone, silo_cold, silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, the fixed 5% and 10% offloads, the penalty rows +2, +4 and +8.1 t) plus the Phase 2 screening variants (silo_cold_lag, silo_hot_full, silo_hot_full_impinged, silo_sled_22t, silo_failed, silo_instant, pad_instant) (user; more than the recommendation, which was SP1's configurations). The design adds a condition: the two instant yardsticks are offered only if a one-variant launch reproduces the screening directory's numbers and flags, otherwise they are dropped with a logged deviation.
- **D-SP2-06** 2026-10-05 (Q5) The form uses the gate vehicle only (configs/vehicles/generic_f9_class_2d.yaml); the README-loads fork is not offered (user).
- **D-SP2-07** 2026-10-05 (Q6) The form offers a fixed offload and a solved one. The stage-2 and both-stage forms are under an Advanced switch, with the pad control forced on (D-SP1-10) (user).
- **D-SP2-08** 2026-10-05 (Q7) The scene is a schematic cross-section as in the mock-up the user saw (docs/phases/inputs/2026-10-05-SP2-mockups/), in light and dark (user).
- **D-SP2-09** 2026-10-05 The job runner is one daemon worker thread in the server process: one job at a time, no cancel. Measured in A0: 4,212 status polls during real jobs, median 17-21 ms, none above 250 ms; run results do not pickle, so a child process could not share the cached pad (design, approved with the plan).
- **D-SP2-10** 2026-10-05 The cached pad: app code composes the public pieces of the run path in `run_experiment`'s order, and results_io.py is unchanged. The cache key is the sha256 of the baseline's run dict, the vehicle dict and the server-start git state. Each hit is re-wrapped with `dataclasses.replace(cached, name=..., resolved=resolved.baseline)`, because identity tests in results_io make a verbatim cached object change the result; the re-wrap reproduces the CLI path (measured) (design, approved with the plan).
- **D-SP2-11** 2026-10-05 Provenance of a long-running server: `git_info` is read once at server start and stored as `server_start` in each launch's git record, beside the launch-time state; the top-level dirty flag is true if either state is dirty. A launch is refused when `git diff --quiet <start> HEAD -- src configs experiments pyproject.toml uv.lock` shows a change. So committing summaries or documents does not force a restart, and uncommitted code never reads clean (design, approved with the plan).
- **D-SP2-12** 2026-10-05 Exploratory marking: a third experiment label value, `exploratory` (config.py 157), and a banner at the top of summary.md that prints both git states. Text: "EXPLORATORY app run, not a finding. Launched from the local app's form, not from a committed experiment file, and not pre-registered. Code: the commit imported at server start (<hash>, clean or dirty); working tree at launch: clean or dirty. Do not cite; findings are in docs/findings/. Calibration +14.3%, no structural mass for the push, sweep-optimized, unthrottled." The mark travels: `replay.caveats` and `plots.animation_caveats` prepend one line for an exploratory directory, and the run browser shows each directory's label and git state. No results_io change and no pinned digest or captured output moves; summary.md is the only tracked file of an app run (design, approved with the plan).
- **D-SP2-13** 2026-10-05 Step A1's compatibility policy: `run_data.RunDataError(ValueError)`, with `AnimationError` and `ReplayError` derived from it; raising functions take the error type and the wording; the old names stay in plots and replay as re-exports or thin wrappers; the ffmpeg test and `plots.calibration_caveat` stay in plots; cli.py is not edited in A1; existing tests are unchanged. Reason: 17 `pytest.raises` name the concrete classes, and three monkeypatches pin names to plots (design, approved with the plan).
- **D-SP2-14** 2026-10-05 KI-017: one output-path rule, replay's stricter one, for animate, replay and scene; animate also says "not an experiment results directory" for a sweep point. A deliberate change of animate's behaviour, tested and logged; the seven animate path tests still pass under it (design, approved with the plan).
- **D-SP2-15** 2026-10-05 KI-016 is fixed in the reader. `read_events` returns every row; a pure `with_drop_masses` adds the mass before and after each drop for the four fairing cases (a fairing row in COAST_STAGING is after the drop, any other before); under the rule `staging`, which writes no fairing row, it adds a row marked `recorded=False`. The planner is not touched; physics.md's sentence on the fairing row is corrected (design, approved with the plan).
- **D-SP2-16** 2026-10-05 The scene's time grid is a selection of CSV rows, never a resample: both rows of every duplicate time, every event row, every 2nd row to 40 s after release, every 20th after, then rows inserted until every CSV row is within half of each tolerance. Stage, fairing-on and thrust-on are per-sample step series; an event's time is its matched row's time. Reason: the brief's grid misses its own criterion on recorded data (pitch by 10.7 deg, plume by 0.98, mass by 29.8 t). The numerics reviewer re-ran the selection on all 31 folders: one insertion pass, 191-987 samples, mass within 0.51 kg (design, approved with the plan).
- **D-SP2-17** 2026-10-05 Attitude: the vehicle is drawn along `pitch_rad` while thrust is on, in the hold and on the track. When unpowered, the drawn screen angle is held, for the vehicle and for separated bodies. The model's instant steps at the kick and at stage-2 ignition are shown as recorded. Reason: a point mass has no body axis; `pitch_rad` follows v_rel when unpowered and flips 180 deg in 0.1 s at a fall-back's apex (design, approved with the plan).
- **D-SP2-18** 2026-10-05 Display geometry lives in `configs/display/f9_class.yaml` (shapes; each number with `source` or `assumed: true`) and `configs/display/scene.yaml` (camera lengths, generic proportions; all assumed). Both are used only by a new pure module, `display.py`, not by config.py. A vehicle without a display file gets a generic shape from its reference area, labelled so. An import-guard test keeps display, scene and app out of the run path (design, approved with the plan).
- **D-SP2-19** 2026-10-05 The spent stage and the fairing halves are drawn on a numerical vacuum coast (mu/r^2, DOP853, stopped at the surface) from the rebuilt event state, clipped at the run's last time. Display-only, never model output. In the A0 prototype (survey 09) the rebuilt speed matched `speed_inertial_mps` to 9e-9 m/s, and the coast's energy and angular-momentum drift was at most 3.5e-13 (design, approved with the plan).
- **D-SP2-20** 2026-10-05 The carriage after release is drawn braking at `brake_decel_g` over `braking_distance_m` on rails above the release point; the model gives only the distance. On a run that ends in impact the carriage and rails become outlines and the ticker says that the planar model has no contact (design, approved with the plan).
- **D-SP2-21** 2026-10-05 Player code: seven helpers of the replay template (`readPalette`, `idxAt`, `valAt`, `phaseAt`, `setupCanvas`, `tick`, `setPlaying`) are copied verbatim into the scene template and pinned by a source-comparison test. The scene has its own rate law, because the replay's Auto rate is tuned for graphs: staging and the fairing drop would pass in 1.5 wall seconds. templates/replay.html is not edited in SP2 (a sha256 test) (design, approved with the plan).
- **D-SP2-22** 2026-10-05 The app shows the scene in a same-origin iframe of the server-rendered scene page, in an embed mode. The page in the app is the exported page: one renderer, one QA target (design, approved with the plan).
- **D-SP2-23** 2026-10-05 Step A1a, before the scene: caveat wording is fixed at source in replay.py, so that replay and scene share one caveat source. `drive_caveat` becomes data-driven (KI-029); the structure caveat names the run's own load; the paired-pad label and note, the comparison note, the rounding, the subtitle and one verb are corrected. site/build.py keeps only its three template canvas patches (replay.html is frozen in SP2; KI-031) and its editorial additions, re-keyed. Reason: the scene would otherwise inherit text that site/build.py patches by hand, or carry a second copy (design, approved with the plan).
- **D-SP2-24** 2026-10-05 KI-018: Pillow is declared in the dev extra, because the tests import it; it has no runtime use (D-SP2-30). The lock change must add only that line (design, approved with the plan).
- **D-SP2-25** 2026-10-05 Progress: the five stages the app owns, with the elapsed time and an expected range from `resolved.offload`. No callback is added to results_io.py or offload.py. Every solve launch runs its pad control, stage 1 too (D-SP1-10). Only the pad baseline is cached, not the pad controls or a paired pad (design, approved with the plan).
- **D-SP2-26** 2026-10-05 App launches write no PNG plots: a PNG of an exploratory run would carry no mark, and the scene replaces it (design, approved with the plan).
- **D-SP2-27** 2026-10-05 A fixed offload is labelled "imposed offload", never "saved". The panel shows P* - P_ref with its reading: positive means the run carries more than the pad, so the offload is not the largest possible; negative means a payload loss. No fly-out at P_ref is added; this is how SP1 records a fixed case (design, approved with the plan).
- **D-SP2-28** 2026-10-05 Default pair of runs for any directory: the baseline on the left; on the right the first solved stage-1 case, else the first assisted variant that is not a yardstick, else nothing (one full-width panel). The replay's default would put a yardstick pad beside the pad (design, approved with the plan).
- **D-SP2-29** 2026-10-05 The command: `launchsim app` on port 8765, with `--port N` (0 = a free port), one error line if the port is busy, `--open` and `--results-root PATH`. The URL is printed as http://127.0.0.1:<port>/, because the name `localhost` costs 2 s per request on this machine (design, approved with the plan).
- **D-SP2-30** 2026-10-05 Video: MP4 through ffmpeg only, by frame-stepped capture. The app page asks the framed scene for each frame (`captureFrame(t)`) and posts the PNG to the server, which pipes it to ffmpeg. No GIF from the app, so the server never decodes an upload; the gallery's GIF and poster are made from the MP4 with ffmpeg at the close. No headless browser, no second renderer, no new dependency, and no CLI video command (design, approved with the plan).
- **D-SP2-31** 2026-10-05 Requests: whitelisted keys, enumerated choices, real booleans, finite bounded numbers. The server builds the experiment from a frozen basis loaded once from the two committed experiment files, so the shared blocks, the baseline and the vehicle can never come from a request. The request carries no run, case or experiment name: a launch keeps a committed name only when its resolved configuration equals the committed one, otherwise it is `silo` and `silo_<mode>`, so that a public summary cannot carry SP1's row name with another configuration (design, approved with the plan).
- **D-SP2-32** 2026-10-05 Server guard: a per-route policy table (method, content type, body cap, Host, Origin, Sec-Fetch-Site, frame and CSP headers), tested by raw sockets, because cross-site GETs and "simple" POSTs pass a Host-only check. Neither new template assigns HTML from data: values go in with `textContent` (design, approved with the plan).
- **D-SP2-33** 2026-10-05 Brand: the app page inlines assets/brand/logo-mark.svg as its header mark and favicon.svg as a data-URI tab icon, because assets/ does not ship in the package; tests compare each copy with its file. The scene page carries the tab icon only (design, approved with the plan).
- **D-SP2-34** 2026-10-05 templates/replay.html does not take the site's contrast tokens in SP2: its sha256 is pinned, and the gallery frame overrides them. KI-019 is re-owned to the phase that next edits replay.html; the measured contrast is logged in KI-031 (design, approved with the plan).
- **D-SP2-35** 2026-10-05 Each panel has a fixed-scale close-up of the vehicle beside the true-scale view. The true-scale view shows the rocket while its body is at least 3 px wide, then a position marker with a heading tick on a path trace. Reason: drawn to scale, the rocket is under 2 px wide after 28% of the playback, and the pad's kick moves the nose 1.2 px (design, approved with the plan).
- **D-SP2-36** 2026-10-05 The results panel and every caveat are built from the directory shown. SP1's headline, where shown, carries the six caveat groups of the findings note and lives in one constant that a test checks against docs/findings/RQ1-fuel-offload-2d.md. A launch equal to a committed case says "a reproduction, not new evidence". Reason: fixed sentences are false for some presets (the 22 t sled, the penalty rows, the 200 m shaft) (design, approved with the plan).
- **D-SP2-37** 2026-10-05 Commits: app summaries are results and go in their own commit (`SP2 step <k>: app summaries`), never in a tracker or bookkeeping commit. Reviewers and gates launch into a scratch results root; only the demo launches, made from a clean tree after the last code commit, go to results/app/. Gallery, deck and manual material comes only from the two recorded directories. Reason: protocol sections 4 and 7; a review launch would otherwise be a permanent public file from a dirty tree. Amends docs/process/SESSION_PROTOCOL.md (section 4, "App runs") (design, approved with the plan).
- **D-SP2-38** 2026-10-05 SP2 has 17 exit criteria (docs/phases/SP2-launch-app-2d-scene.md, section 8), with their changes against the brief's 14 listed there. Reason: three of the brief's tolerances were unmeasurable or vacuous on recorded data (design, approved with the plan).

Notes on the SP2 planning group:

- The full design, with the reasons and the measurements behind these decisions, is
  docs/phases/inputs/2026-10-05-SP2-design.md. Its sources are saved beside it: nine survey
  reports, six reviews of the first draft (2 blocker, 49 major and 31 minor findings; the
  approved design is the second version) and the two mock-ups.
- D-SP2-37 amends the session protocol: docs/process/SESSION_PROTOCOL.md section 4 has a
  new paragraph, "App runs (decision D-SP2-37)".
- D-SP2-01 supersedes the note on milestone M13 that a separate `launchsim scene` command
  was no longer the plan, and D-SP2-03 goes against the brief's recommendation for Q3.
- Not taken: vendored or Google fonts (Q2); the README-loads vehicle (Q5); a cancel
  button; sensitivity arms and sweeps from the form; a CLI video command; a GIF from the
  app.
- Changes against the brief are listed in the phase file, section 12.

## Known issues and observations

Format: **KI-nnn** [severity, status, owner phase] entry. "Owner: standing" means a rule or
an observation that every phase keeps in mind, with no fix planned. The original wording is
kept; notes added on 2026-09-30 follow it in parentheses.

- **KI-001** [low, open, owner SP3] timeseries.csv records gamma_rel_rad outside (-pi, pi] on a vertical fall-back with rotation (silo_failed reaches 4.673 rad, the unwrap documented in physics.md); replay wraps it for display. Check that no loss integral or check uses the unwrapped value. (The check has not been done. Seen only on the fall-back run; SP3 re-derives the loss identity for 3-D and is the natural place for the audit, which is read-only and can be done earlier. The audit is a line of SP3's scope and of its step S1.6.)
- **KI-002** [low, closed 2026-10-05 in SP2 step A1 (9579f89): one reader pair, one event reader and one output-path rule in src/launchsim/run_data.py; replay.py calls no private plots name and no longer imports plots. The two `calibration_caveat` sentences stay in their modules by design (D-SP2-13), reading one record] replay.py calls the private plots._results_tree and plots._is_inside and duplicates plots' JSON/YAML readers; make them public (plots.py or results_io.py) and switch animate and replay over together. (SP2 plans a shared read-only run-directory loader; details in docs/phases/inputs/2026-09-30-survey-animate-replay-visuals.md, sections 2 and "Recommendation". Two more copies of the same kind, from the same survey, are covered by this entry: `replay.run_events` duplicates `plots._events`, and `calibration_caveat` exists in both replay.py and plots.py with different wording; SP2 phase file, section 5.8 item 3.)
- **KI-003** [low, open, owner standing] run_data.CALIBRATION_RECORDS (re-exported by plots since SP2 step A1; plots.CALIBRATION_RECORDS before) feeds the calibration caveat in animate and replay; update it whenever the calibration is re-run.

- **KI-004** [low, open, owner later (README Phase 5)] Probe citations in RQ3-2d rest on labelled probes kept in docs/findings/probes/RQ3-2d/ (launchsim equal-gamma* probe, a low-v_k probe, and a reviewer's independent stage-2 swap probe); none is a shipped run.
- **KI-005** [low, open, owner later] Sensitivity was pre-registered only for silo_cold and silo_hot_full; silo_hot_ramp_on_track, the ignition-timing points and silo_instant carry no +/-10% range.
- **KI-006** [medium, open, owner later (README Phase 5)] M4 (blocking) is not robust over gamma* +/- 0.5 deg at some sweep points and at pad_instant; M2 (diagnostic) likewise at several points. The verdicts at gamma*_ref stand and the notes disclose all. (Watch in SP1 step 9: the same checks run on the offload runs.)
- **KI-007** [low, open, owner later (README Phase 5)] A reviewer's richer stage-1 guidance probe (untested integrator) suggests both runs gain about 0.9 t with better guidance and the gap widens; worth a launchsim check as a Phase 5 pre-study.
- **KI-008** [low, open, owner later] summary.md also lists cross-vehicle sensitivity comparisons (a perturbed variant against the unperturbed baseline, not_checked by design) as 'Unexplained beats'; the same-perturbation comparisons are attributed and ok.

- **KI-009** [low, open, owner later] silo_cold_lag's searched run takes about 25 s at normal machine speed, close to the 30 s per-run budget, because the lag's step cap holds for the whole lag-lit burn; options (a planar lag cap over the first few tau) are open, not needed for correctness.
- **KI-010** [low, open, owner standing] Planar convergence tests now run in the slow tier only (with the cap each takes just over 5 s).

- **KI-011** [low, open, owner later] summary.md labels +/-10% vehicle-perturbation sensitivity cases of a pad baseline as 'Unexplained beats'; the screening rule should not apply when the baseline is a pad without an assist (cosmetic).
- **KI-012** [low, open, owner later (if the calibration is revisited)] Literature sizing of flight-performance reserve, unusable residuals and payload adapter mass is not in the calibration note (it uses the run's own conversions and says so); add it with citations if the calibration is revisited.

- **KI-013** [low, closed 2026-09-30, owner none] README says one EMALS launch is 122 MJ; 45 t at 67 m/s is about 101 MJ (122 MJ is the rated maximum). Note in findings, do not edit silently. (Closed: the README now carries the correction marked as corrected, and RQ3-1d and RQ2-1d note it; checked 2026-09-30.)
- **KI-014** [low, closed 2026-09-30, owner none] README ignition-loss band (5-25 m/s) covers the linear ramp; a first-order lag with tau = 1-3 s gives 10-39 m/s. (Closed: the README's "Simulation updates" state the lag band, 9.8-39.2 m/s, from RQ2-1d; the hand number is kept as the first-order record; checked 2026-09-30.)
- **KI-015** [low, open, owner standing] The Bash tool failed to parse one very long multi-heredoc script; keep file-writing calls to ~150 lines. (Also in docs/process/SESSION_PROTOCOL.md, section 11.)

Added 2026-09-30 from docs/phases/inputs/2026-09-30-survey-animate-replay-visuals.md (line numbers there are for commit 2eebcae):

- **KI-016** [low, closed 2026-10-05 in SP2 step A1 (9579f89): `run_data.read_events` plus the pure `with_drop_masses` give the mass before and after each drop for all four fairing cases, tested on planner-produced rows; the planner's logging is unchanged; docs/physics.md states the four conventions] The fairing event's mass convention differs between drop cases: a fairing dropped during the stage-2 burn (or at stage-2 ignition) is logged in events.csv with the mass before the drop (it still includes the 1.7 t fairing); a fairing dropped at staging (heating criterion already met) is logged after both drops. No physics is affected; a scene or loader that rebuilds separation masses from events.csv must handle both (survey section 10). (Note 2026-09-30, from phases/planar.py `_stage_and_coast` at 2eebcae: under `fairing_drop: staging` no fairing row is written at all; the drop is inside the staging row. No shipped planar vehicle uses that rule; the 1-D reference vehicle does. SP2 phase file, section 5.8 item 1.)
- **KI-017** [low, closed 2026-10-05 in SP2 step A1 (9579f89): one rule, replay's stricter one, for animate, replay and the scene (D-SP2-14); animate newly refuses output inside any folder named results in any letter case and moves its default path out of it, tested] animate and replay disagree on the output-path rule: plots._results_tree matches the folder name "results" case-sensitively and check_animation_out refuses only the run's own results tree; replay matches case-insensitively and refuses output inside any folder named results (survey section 2).
- **KI-018** [low, open, owner SP2] Pillow is imported by tests (tests/test_animate.py imports PIL) but is not declared as a dependency in pyproject.toml; it arrives through matplotlib (survey section 9). Declaring it needs the one-line dependency justification CLAUDE.md asks for. (SP2 phase file, section 5.8 item 4 and step A1.)
- **KI-019** [low, open, owner the phase that next edits replay.html (re-owned 2026-10-05 by D-SP2-34; was SP2)] The replay page loads its fonts (Barlow Condensed, IBM Plex Sans, IBM Plex Mono) from Google Fonts, with local fallbacks, so the page is not fully offline (survey section 3). Matters for the local app on 127.0.0.1. (Note 2026-10-05: the app and the scene make no external request and use system fonts (the user's answer to Q2, D-SP2-02), so the issue no longer touches them. The replay page keeps its font links: templates/replay.html is not edited in SP2 (D-SP2-21, D-SP2-34). Fix it together with KI-031 when the template is next edited.)

Added 2026-09-30 in SP1 step T (from the session itself):

- **KI-020** [low, open, owner standing] The output files of background subagents were 0 bytes in the 2026-09-30 session, so a subagent's report existed only in its notification text; background Explore agents also took from 10 minutes to 2.5 hours of wall clock. Save a design, survey or review worth keeping to a repository file (docs/phases/inputs/) as soon as it arrives. (Also in docs/process/SESSION_PROTOCOL.md, section 11.)

Added 2026-10-02 in SP1 step 2:

- **KI-021** [low, open, owner later: the next phase that may touch those tests (SP1 closed without touching them)] tests/test_silo.py states the 3 g0, 100 m felt load as 3.9992 g0 (module docstring, the `test_cold_felt_acceleration_and_interface_force` docstring and its 1e-4 hand-number literal); the value (3 g0 + mu/R_E^2)/g0 = 3.99915 is 3.9991 to four decimals (docs/physics.md corrected in SP1 step 2). Correct all three together when a step may touch that existing test; the check passes with either value.

Added 2026-10-02 in SP1 step 5:

- **KI-022** [low, open, owner later: the next phase that may touch those tests (SP1 closed without touching them)] Test docstrings tests/test_convergence_2d.py:34-38 ("the only planar tests that fly the shipped search rtol of 1e-8"), tests/test_search.py:72-74 and tests/test_payload_search.py:80 ("the convergence tests alone fly the shipped 1e-8") are no longer accurate: tests/test_calibration.py, tests/test_silo_screening_record.py and the convergence test of tests/test_offload.py also fly it, as docs/physics.md "Validation" and "Convergence (planar)" now say. Docstring-only fix.

Added 2026-10-02 in SP1 step 3:

- **KI-023** [low, open, owner later: the next phase that may touch those tests (SP1 closed without touching them)] Two comments in existing tests in tests/test_config.py are stale since SP1 step 3: the comment in `test_exclusive_family_table_is_the_design_and_is_scoped_by_key_name` ("the ignition group's other families arrive in step 3") and the end of the docstring of the step-1 sweep-axis test ("the depth arrives in step 3"). The fields exist and `test_depth_sweep_axis_over_a_timed_parent_resolves_to_the_depth_alone` resolves the depth end to end. Comment-only edits, together with KI-021 and KI-022.

Added 2026-10-02 in SP1 step 6:

- **KI-024** [low, closed 2026-10-03 in SP1 step 7 (6719f92): `_worst_abs` makes a NaN residual fail the check in any position, tested; no existing verdict moved] `compare._attribution_check` (reused by the cross-vehicle decomposition) takes max(abs(...)) over a tuple of residuals, so a NaN residual that is not first in the tuple can be skipped silently. Add a math.isfinite guard (a NaN residual should fail the check) in a step that may touch it, with a test.

Added 2026-10-03 in SP1 step P:

- **KI-025** [low, closed 2026-10-04 at SP1's close-out (step 10): the refreshed deck draws slide 13's y axis with ticks every 500 kg from 24,500 to 27,500 kg, checked in site/deck/index.html; committed in the bookkeeping commit `Close SP1: trackers, handoff, next phase file`, whose hash a file in it cannot carry] Deck slide 13 (site/deck/index.html) has unevenly spaced y-axis labels (24,000 / 25,000 / 26,000 / 27,000 / 27,500 kg). Cosmetic; fix when the deck is refreshed with SP1's finding. (Note 2026-10-04: the step-10 deck refresh, uncommitted when this note was written, redraws the slide with ticks every 500 kg from 24,500 to 27,500 kg; close this entry with that commit's hash.)
- **KI-026** [low, open, owner the user] The repository's social preview image (assets/brand/social-preview.png, 1280 x 640) must be uploaded by hand under GitHub Settings, General, Social preview; GitHub has no API for it.

Added 2026-10-03 in SP1 step 7:

- **KI-027** [low, closed 2026-10-03 in SP1 step 8a (d336933)] plots.py's calibration footnote multiplies by 100 itself instead of calling `units.to_percent` (output identical; the units.py docstring says so). Switch it when plots.py is next touched.

Added 2026-10-03 in SP1 step 8:

- **KI-028** [low, closed 2026-10-03 in SP1 step 8a (d336933): solve_gamma_star_rad and n_flags columns, flag lines in the sweep Checks] A sweep point's offload solve writes none of its own record to disk (gamma*_ref, flags); sweep_index.csv carries only OFFLOAD_SWEEP_COLUMNS and its gamma_star_rad column is the point's payload search, not the solve at x*. Differences between sweep points are then read with the gamma* allowance at its cap rather than from recorded values. Fix before the SP1 run (step 8a), as a pre-registration-note amendment.

Added 2026-10-03 at the SP2 fact-check:

- **KI-029** [low, open, owner SP2] `replay.drive_caveat` (replay.py) ends "Each of these favours the assisted runs.", which is misleading; site/build.py (`REPLAY_TEXT_FIXES`) rewrites the sentence in the gallery pages. Fix it in replay.py (and drop the site rewrite) when SP2 touches replay (SP2 section 5.8 item 5).

Added 2026-10-05 in SP2 step A0 (found by the code survey and the review of the design; severity and owner as the approved design gives them, docs/phases/inputs/2026-10-05-SP2-design.md section 8; line numbers are for commit b69ff0c):

- **KI-030** [medium, open, owner SP7] The config accepts `true`, numeric strings, inf and NaN for several numbers. The models are not strict and most numeric fields do not set `allow_inf_nan=False`. Measured in A0, each of these passes `resolve_experiment`, `check_result_names` and `check_resolved`: `stroke_m: true` (taken as 1.0 m); `stroke_m: "100"` and `fixed.stage1_fraction: "0.05"` (strings); `paired_pad: "yes"` (taken as true); `stroke_m: inf` with `net_accel_g`; `net_accel_g`, `brake_decel_g` and `carriage_mass_t` of inf; `t_ign_s` of NaN, inf, 1e9 or -1e9 (no bound); `track.exit_altitude_m` of NaN, -1000 or 5000 (no bound); `startup.t_ramp_s: inf`. Refused as they should be: `exit_speed_mps: inf`, NaN where a bound exists, non-finite `at_*` values and offload masses. The same models validate experiment YAML files, and Python's `json.loads` reads NaN and Infinity, so such values can also arrive in a request body. SP2 does not change the config for this: the app's request parser takes only real booleans and finite bounded numbers (D-SP2-31; SP2 exit criterion 4). Evidence: docs/phases/inputs/2026-10-05-SP2-survey/03-config-and-form.md, section 3.3.
- **KI-031** [low, open, owner the phase that next edits replay.html] Two faults of templates/replay.html stay, because the template is frozen in SP2 (D-SP2-21, D-SP2-34). (a) Three canvas labels: the close-up's "silo floor" label runs into the time axis, and an x-axis tick label and a timeline event label can leave their canvas. site/build.py patches the template's JavaScript for them in the gallery pages only (three of the five `REPLAY_TEXT_FIXES` pairs, site/build.py 123-166); a page written by `launchsim replay` itself still has them. After SP2 step A1a these three patches are what is left of that table, beside the site's editorial additions (D-SP2-23). (b) Small text below 4.5:1: the template's `--ink-3` measures 3.36:1 on `--bg`, 3.64:1 on `--panel` and 3.21:1 on `--caution-bg` in light mode, and 4.68, 4.38 and 3.88 in dark mode; its light `--caution` on `--caution-bg` measures 4.02:1. The canvas axis text uses `--ink-3`. The site's values for the same pairs measure 4.57 to 5.72; the gallery frame (site/templates/replay-frame.html) overrides the two tokens with them, and a page written locally keeps the template's values. Fix both in the template together with KI-019, drop the three patches and regenerate the gallery pages in the same change. Evidence: docs/phases/inputs/2026-10-05-SP2-survey/04-replay-template-and-brand.md (section 1, the contrast table) and 01-inventory-recheck.md (section 6).
- **KI-032** [low, open, owner later] The metric `drive_power_peak_t_s` is on the absolute run clock (metrics_planar.py 1012), while the other time metrics of a planar run are after release, `t_release_s` excepted. It reads 2.6073 s on silo_cold and 5.2146 s on silo_cold_200m: the release instant, which is 0.0 after release. `felt_g_track_peak_t_s` beside it is after release (-2.607 s). A reader subtracts `t_release_s` before showing it on the release clock. Evidence: docs/phases/inputs/2026-10-05-SP2-survey/05-run-data-on-disk.md (sections 4, 10 and 11).
- **KI-033** [low, open, owner later] An offload case on a variant with `assist: {model: none}` resolves. The config refuses a case only when its `of` is the baseline or an unknown name (config.py 2046-2053), so the rule that an offload applies to an assisted launch (the pad's own offload is the pad control) is not enforced for a second pad given as a variant. The app's form does not offer it: a pad-only launch disables the offload. Evidence: docs/phases/inputs/2026-10-05-SP2-survey/03-config-and-form.md (section 9, item 2).
- **KI-034** [low, open, owner later] A step startup at release records thrust 0 on its first flight row. In results/silo_screening_2d/20260930T175743Z/silo_instant/timeseries.csv both rows at t_rel 0 (ASSIST and KICK) have `thrust_vac_N` = 0; the next row, at +0.0427 s, has 8,226,900 N, with `m_kg` already 115.13 kg lower (full flow from the ignition instant). The metric `t_ign_rel_release_s_stage1` is 1.78e-15 s, so the row is sampled a rounding step before ignition (vehicle.py 104: dt < 0 gives 0). The same in silo_bridge_2d_readme. pad_instant (first row 1.0) and stage-2 ignition (0, then 1) are as expected. Consequences for a reader: linear interpolation between the two rows draws a 43 ms thrust ramp the model does not have, and a check that rebuilds mass by integrating thrust must leave out that first interval (57.6 kg). Evidence: docs/phases/inputs/2026-10-05-SP2-review/01-numerics.md, finding 5.

## Findings so far (details in docs/findings/; index in docs/findings/README.md)

- SP1 (2026-10-03, docs/findings/RQ1-fuel-offload-2d.md; preliminary, sweep-optimized, unthrottled, gate vehicle +14.3% calibration miss): at the pad's payload and orbit the 3 g0, 100 m cold-start silo leaves out 41.26 t of stage-1 propellant, 10.04% of stage 1 and 7.96% of the total (2.76x the ideal-screening estimate, explained by the decomposition; +/-10% arms 38.67-44.46 t; README-loads bridge 36.01 t, 9.10%). Against it: an assumed +8.1 t of stage-1 dry mass leaves 1.98 t (about 8.5 t, extrapolated, cancels it); read as pre-registered, most of the offload is the lighter stack's thrust-to-weight (paired pad 1.4 t short), while a delta-v reading chosen after the run gives the lighter stack 28-29%; max-Q 3.4% above the pad's; the stage-2 case failed its verification. Only exit speed matters (200 m at 1.5 g0 gives the same offload with 2.5 g0 felt on the track). Energy: removed RP-1 heat about 128x the push's electricity (not an efficiency claim).

- Cold start after a 3 g0 / 100 m push: +69.6 m/s at stage-1 burnout vs the pad = 76.7 exit + 5.4 hold-down credit - 14.7 ignition loss (0.5 s + 2 s ramp; exact constant-g form) + 2.2 altitude term. Ideal-screening equivalent 621 kg vs the README's 685 kg: the ignition loss outweighs the pad's hold-down waste.
- Hot starts under a prescribed-acceleration drive buy no exit speed: they trade 2.7-9.7 t of propellant (5.6-20.6 m/s at burnout vs the instant yardstick) for 0.47-0.85 GJ less drive energy and up to 40% less peak power, and only if the exhaust misses the carriage (f_imp = 1 removes the saving). A force-limited drive (Phase 3) is needed before the hot-start question can be answered.
- Loads: 4.0 g0 on the full 542.6 t stack during the push (21.3 MN interface force), against 5.7 g0 at stage-1 burnout in every variant (unthrottled).
- Lag startups cost more than the README's 5-25 m/s band: tau = 1/2/3 s gives 14.7/24.5/34.3 m/s with a 0.5 s delay.
- Failed ignition: apex 300.3 m at 7.83 s; the vehicle meets a carriage parked 60 m up the shaft at 14.8 s at 68.6 m/s, or the mouth at 15.66 s at 76.7 m/s.
- Sensitivity: the assist's benefit moves < 0.5 m/s under +/-10% stage-1 dry mass or Isp when compared against a baseline with the same perturbation.

- Stage-1 measurement, not a finding (physics.md, Time-shift mechanism): at equal gamma* at MECO, a 77 m/s vertical silo release saves about a quarter of the gravity loss the plan's time-shift estimate predicted when both runs light at release, and about none for the cold start (0.5 s + 2 s ramp in the air); the silo leaves about 9% heavier than the pad at the same speed.

- 2-D, gate vehicle, sweep-optimized and unthrottled: silo_cold (3 g0, 100 m, cold start) carries +1,498.8 kg more to 200 km than the pad (+5.75%; +1,345 to +1,667 kg under +/-10% vehicle and drive perturbations), about 2.0x the 765 kg ideal-screening estimate at its release speed. The loss breakdown explains it: release speed, the pad's clamped-ramp burn (130.7 kg gross, 83.1 kg net), and a trajectory gain that for the cold start appears after MECO. Against the unphysical pad_instant the gain is +1,415.8 kg.
- The costs not yet charged are large: no structural mass is modelled for the 4.0 g0 full-stack load (22.5 MN); about 8.1 t of silo-only stage-1 strengthening would cancel the gain (184 kg of payload per tonne of stage-1 dry mass, derived). The drive is prescribed-acceleration, the carriage is 0 t, the shaft has no air drag, and the kick has no alpha aero.
- Ignition timing in 2-D costs more than 1-D predicted: the 0.5 s + 2 s cold-start loss is 2.14x the 1-D value on the same masses (301 kg on README masses, 327 kg on the gate vehicle). The hot ramp ending at release beats cold by about 235 kg; a full hot start ties cold (-18.5 to +0.1 kg under +/-10%).
- Unthrottled max-Q falls about 16% for every silo variant (a faster, higher trajectory through the transonic region), while q-alpha is above the pad's in every silo variant.

- Viewing results (2026-09-30): there is no GUI; `launchsim animate <run_dir>` renders a 2-D run as an MP4 or GIF (docs/media/ascent_pad_vs_silo_cold_2d.mp4 and .gif), and `launchsim replay <run_dir>` writes a self-contained interactive HTML replay page (a published copy is the private claude.ai artifact "Ascent Replay").

- Probe (2026-09-30, not a finding; docs/findings/probes/handoff-2026-09-30/probe_offload.py): the 3 g / 100 m cold-start silo carries the full-load pad's payload (26,061 vs 26,054 kg) with 10% less stage-1 propellant (41.1 t, 7.9% of total); roughly 12 t of RP-1 (~530 GJ) against ~1.2 MWh of electricity at 50% drive efficiency. Same caveats as the 2-D findings, above all no structural mass for the 4 g push. (SP1 step 9 replaces this probe with a solved, pre-registered result; the probe is a sanity check for it, not a target.)

## Open questions for you

- None open. The Phase 2 questions were answered 2026-09-30 (D-P2-08 to D-P2-11); the SP1
  planning questions were answered 2026-09-30 (D-SP1-01 to D-SP1-08); the SP1 close-out
  question (which phase runs next, and the B-004 order) was answered 2026-10-04 (D-SP1-18);
  the SP2 planning questions Q1 to Q7, with a follow-up to Q3, were answered 2026-10-05
  (D-SP2-01 to D-SP2-08), and the SP2 design was approved the same day (D-SP2-09 to
  D-SP2-38).
- Deferred to later phases' Plan mode; each phase file lists them in its section 10 (Risks
  and open questions), marked where they need you. Known today from the approved plan: the
  detailed design of the app and the 2-D scene (SP2's Plan mode; done 2026-10-05,
  docs/phases/inputs/2026-10-05-SP2-design.md); the target-orbit
  definition under J2 (D-SP1-11, revisit in SP5); whether to move the structural-mass
  model (B-004) ahead of the 3-D work (any session boundary; answered 2026-10-04 at SP1's
  close-out: yes, as SP7 after SP2, D-SP1-18).
- Waiting on you, not urgent: B-001 (results retention; deleting results needs your OK).

## History: step tables of Phases 0-2 and Phase V

These tables are the record of how Phases 0-2 were built. They are not updated any more.
"Plan" in the two headings below does not mean the SP1 plan of 2026-09-30. Build steps
1-13 followed the plan approved on 2026-09-28 (Phase 0 + Phase 1 + vertical
constant-acceleration silo push; milestone M0). Steps 14-28 followed the Phase 2 plan of
2026-09-29 (milestone M6; its path is in the archived handoff,
docs/handoff/archive/2026-09-30-phases-0-2.md, section 7). Milestones M0-M9 follow the
README roadmap.

### Build steps (plan, "Build sequence")

| # | Step | Status | Gate / notes |
|---|---|---|---|
| 1 | git init, pyproject, constants, units, cli stub, scaffold tests | [x] | 10 tests pass, ruff clean, ambiance runs warning-free on NumPy 2.5.3 |
| 2 | atmosphere.py + ICAO/extension tests + docs/physics.md start | [x] | ICAO layer closed forms from ambiance's constant table (ambiance.Atmosphere is the 1e-12 oracle); 2 review rounds |
| 3 | config.py, vehicle.py, F9 YAML, experiment YAML, toy data, fixtures, tests | [x] | 542,570 kg; README screening table reproduced; 2 review rounds |
| 4 | cli.py + sim.py results I/O (placeholder run), tests -> Phase 0 gate | [x] | run/sweep write results dirs; independent gate passed |
| 5 | dynamics.py (gravity, 1-D RHS), phases.py engine, rocket-eq/vertical-burn/coast/events tests | [x] | event rules verified against scipy; 2 review rounds |
| 6 | VerticalPlanner, simulate/run, losses.py, staging/hold/ignition-loss/identity tests -> Phase 1 gate | [x] | exact ignition-loss forms and identity closure tested; 2 review rounds |
| 7 | assist/* (constant_accel, track, none), track RHS, release map, energy budget, silo tests | [x] | closed forms for exit speed, loads, energy identity (hot starts, f_imp 0/0.5/1) at 1e-10; 2 review rounds |
| 8 | failed-ignition coast + test | [x] | apex 300.27 m at 7.829 s, back at 15.658 s; also the parked carriage 60 m up the fall-back path at 14.83 s |
| 9 | full metrics, comparison, sensitivity, summary.md with identity line, plots | [x] | identity decomposition, screening payload equivalent (labelled), sensitivity vs both baselines |
| 10 | convergence test, slow marks | [x] | < 1e-6 relative under 10x tighter tolerances; no test exceeds 5 s |
| 11 | docs/physics.md complete (assumptions, test-to-equation map, Phase 2 note); ruff clean | [x] | 1,575 lines, checked against the code by a reviewer |
| 12 | run + sweep silo_screening_1d; verify identity lines; test_readme_numbers | [x] | results/silo_screening_1d/20260929T103623Z (run) and 103634Z (sweeps); two reproduction pairs |
| 13 | findings RQ2/RQ3 (preliminary); CLAUDE.md + README status lines; commit | [x] | 345 tests |

### Phase 2 build steps (plan section 10 and section 14 amendments)

| # | Step | Status | Gate / notes |
|---|---|---|---|
| 14 | Pre-registration of decisions (no code); tracker rows | [x] | decisions logged below with defaults |
| 15 | Golden capture of every 1-D output + test_golden_1d | [x] | 121 golden tests (silo_screening_1d plus a paths set covering staging, apex, no-liftoff, drive-limit, fall-back ignition) |
| 16 | Split sim.py into sim, metrics, compare, summary, results_io, plots | [x] | 1-D CLI outputs byte-identical (23/23 experiment, 129/129 sweep digests) |
| 17 | phases/ package (engine, trace, prelude, vertical); y_events, nfev, dense-off setting | [x] | full suite + golden |
| 18 | Aero data layer: ambient_scalar, C_D PCHIP, drag, fairing rule; three 2-D vehicle forks | [x] | full suite + golden |
| 19 | Config schema: dynamics, shared blocks, target orbit, search/ltg/checks, bounds, cases; four experiment YAMLs | [x] | 1-D resolved dicts identical; all four YAMLs resolve |
| 20 | Planar EOM, orbit.py, H0 gravity; orbit/coast/rocket-eq/pointwise-identity/reduction tests | [x] | elliptical orbit (DOP853 and RK45) drift < 1e-8 |
| 21 | Stage-1 planner and guidance: hold, release map, rise, kick, gravity turn, staging, gamma* solve | [x] | 465.1 m/s release test; Culler-Fried gravity turn |
| 22 | Stage 2: LTG law and shooting, energy cutoff, fairing, insertion, max-Q, loads | [x] | full-ascent loss budget closes < 1e-5 m/s (pad, silo, clamped thrust, fall-back) |
| 23 | search.py: residual, payload capacity, gamma* sweep, final verify | [x] | searched pad run 7-10 s; lag variants 25-28 s |
| 24 | Pipeline: dispatch, planar metrics, compare with closure/attribution/checks, summary, plots | [x] | full suite + golden |
| 25 | Convergence and performance gate; slow marks | [x] | every CLAUDE.md Phase 2 required test green; fast tier 43 s, full 230 s |
| 26 | Calibration (labelled): three mass sets, checklist, CAL-f9-leo-2d.md | [x] | frozen at c2849b7; run 20260930T100100Z; gate C misses high (M7 [!]); every numerical check passes; slow regression test without a band |
| 26a | Step cap (2 s, planar) and M2 as diagnostic; pre-registration amendment; calibration re-run | [x] | amendment 7ad381f; calibration re-run 20260930T173928Z reproduces every case within 0.002 kg |
| 27 | Research experiments: trigger study, silo_screening_2d, bridge; RQ2/RQ3-2d, RQ6 | [x] | runs from clean 7ad381f; v_k rule did not fire (pad best v_k 30, +0.72 kg); every screening beat explained by the matched attribution (no bug_suspect); findings RQ2-2d, RQ3-2d, RQ6 with physics, honesty and compliance reviews |
| 28 | Close Phase 2 | [x] | physics.md research notes, probe records kept in docs/findings/probes, status lines |

Note on step 14's "decisions logged below": they are D-P2-01 to D-P2-07 in the decisions
log above.

### Phase V: visual launch simulator and fuel-replacement experiments (superseded 2026-09-30)

**Superseded by the phase files under docs/phases/.** This table was the first handoff's
proposal (docs/handoff/archive/2026-09-30-phases-0-2.md: the user's request verbatim,
requirements, fact-checked inventory, decisions, plan, gotchas, and the prompt that started
SP1). The approved plan replaced it. The status of V1-V4 is tracked in the phase files, not
here.

| # | Step | Status | Gate / notes | Superseded by |
|---|---|---|---|---|
| R1 | `launchsim replay` command (interactive HTML replay page) | [x] | 2026-09-30 | done before SP1 |
| V0 | Plan mode: decisions (3-D view vs physics, tool type, offload semantics, depth and ramp-start parameterisation) | [x] | user approval: 2026-09-30 | done: the approved plan (M10; D-SP1-01 to D-SP1-13) |
| V1 | Config knobs + `propellant_offload` figure of merit + experiments/silo_offload_2d.yaml | superseded | full suite, golden 1-D unchanged | SP1 steps 1-8 (the offload is an `offload:` block, D-SP1-09) |
| V2 | 2-D animated launch scene | superseded | visual QA against run data | SP2 (inside the local app, D-SP1-02) |
| V3 | 3-D scene (view of the planar runs on a globe) | superseded | visual QA | SP3, SP5, SP6 (true 3-D dynamics, D-SP1-01) and SP4 (the 3-D scene) |
| V4 | Fuel-replacement findings (offload at fixed payload, energy ratio, structural penalty), depth and ramp-start sweeps | superseded | honesty review | SP1 step 9 |
