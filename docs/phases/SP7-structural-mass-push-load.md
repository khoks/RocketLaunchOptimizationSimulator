# SP7: Structural mass of the push load, and a force-limited drive (planar model)

Status: done (2026-11-09, commit `3a07f07`)

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-10-04 in
the SP1 session (step 10, the close-out) after decision D-SP1-18, which added this phase
and ordered it after SP2 and before the 3-D phases SP3-SP6. The number is an identifier,
not a position (board, "How to add a phase"). When it was written, nothing in it had been
built or run and no design input existed under docs/phases/inputs/ (SP7's own Plan mode
made the design and saved it there). SP7's progress since 2026-10-08 is in the step table
(section 7) and the session log (section 11). Sections 4, 6 and 13 were re-checked against
the code at commit 705025f on 2026-10-07 by SP2's close-out (protocol section 7, item 8): the
corrections are listed at the top of section 6, the entry criteria carry their state, and
the prompt of section 13 is final. SP7's step 0 (2026-10-08) made and the user approved the
design docs/phases/inputs/2026-10-08-SP7-design.md (decisions D-SP7-01 to D-SP7-35); it
supersedes sections 5, 7 and 8 of this brief where they differ, and sections 7 and 8 below
are now the approved ones.

This file is a brief, not the detailed design. Where it offers options, it gives a
recommendation; SP7's Plan mode settles them with the user before any code is written.

## 1. Goal and what you can see at the end

**Goal.** Charge the structural mass that the 4 g full-stack push needs, so that the
fuel-offload and payload findings carry a modelled structural cost instead of the assumed
penalty rows; and build the drive realism that interacts with that cost: a force- and
power-limited linear motor, carriage mass and modelled braking, and the silo air column.
These are the README roadmap Phase 3 items that bear on the answer (README, "Roadmap";
TODO.md B-004, B-005, and parts of B-007).

Why now (D-SP1-18): SP1's headline is 41.26 t of stage-1 propellant, 10.04% of stage 1
and 7.96% of the total, at the pad's payload and orbit, before any structural mass
(docs/findings/RQ1-fuel-offload-2d.md). Its assumed penalty rows show how fragile that is:
+2, +4 and +8.1 t of stage-1 dry mass leave 32.29, 22.88 and 1.98 t, and about 8.5 t
(extrapolated) leaves nothing. How much strengthening the 4 g push really needs, at the
low end of those rows or near their top, therefore decides whether the 10% survives,
while the 3-D models are expected to move the
headline by kilograms (D-SP1-18; SP3 pre-registers |dP*| < 5 kg of payload against the
planar gate). So the structural question comes first.

At the end you can see:

- a first-order structural sizing model, validated against closed forms, that turns a
  push (felt g, the stack mass and propellant levels on the track, where the load enters)
  into an added stage-1 dry mass, with every coefficient sourced or `assumed: true`;
- the headline offload re-solved with that modelled mass, as a central value with an
  uncertainty band, beside SP1's parametric penalty rows (which stay as the bracket);
- the depth question re-opened: at a fixed exit speed a deeper, gentler push needs less
  structure, so with structure charged the offload no longer stays the same by
  construction across strokes (RQ1, "Depth and g-level");
- a `linear_motor` silo run (force and power limits, efficiency, carriage mass) beside
  the `constant_accel` run it replaces, and the hot-start question that RQ1 left open
  under the prescribed drive;
- `uv run python -m launchsim run experiments/<SP7 file>.yaml` reproducing it from a
  pre-registered experiment; the findings note updated; a recorded demo under
  docs/demos/SP7/.

This phase may produce a result that undercuts the hypothesis (a modelled structure that
cancels most of the offload). That result is reported as plainly as any other (CLAUDE.md,
"Project"; protocol section 6).

## 2. Scope and out of scope

**In scope (proposed; Plan mode confirms each line)**

Confirmed in step 0 (2026-10-08), with the changes of section 12: items 1 to 5, 7 and 8 as
the approved design states them (stage 2 sized where the push exceeds MECO, D-SP7-11); item
6 as braking functions in closed form (D-SP7-12) and the sealed shaft (D-SP7-26), both first
to cut; item 9 (KI-030) in step S4 with named range bounds (D-SP7-28).

1. A first-order structural sizing model of the stage-1 load path for the push, as a pure
   module: tank walls (hoop stress from ullage plus hydrostatic pressure at the felt g;
   axial compression from the inertial load less the pressure relief, against a buckling
   allowable), the tank bottoms, the structure where the carriage load enters, and the
   interface hardware on the rocket (B-004 names it). Charged as the increment over the
   vehicle's existing load envelope (section 5.2), so a push inside the envelope costs
   nothing.
2. A structure file per vehicle with the sizing coefficients and a stage-1 mass breakdown,
   every number sourced or `assumed: true`; the calibrated vehicle files stay untouched.
3. The coupling of the modelled mass into SP1's offload solve and into the payload search,
   reported beside the penalty rows (the rows stay; D-SP1-04).
4. An uncertainty band: the headline re-solved at low, central and high coefficient sets
   (section 5.6).
5. `linear_motor`: F = min(F_max, P_max / sdot) with efficiency eta, a stated force rise
   time (finite jerk), carriage mass, and release at s = L or at a target speed
   (CLAUDE.md, "Physics model", items 2 and 3). It replaces the `PlannedAssistConfig`
   placeholder for that key (config.py 78, 713; the refusal at 723; tests/test_config.py
   219-220 and 283-289 pin the placeholder and change with it; appform.py 187 builds
   `ASSIST_UNION_TAGS` from `PLANNED_MODELS` and follows automatically).
6. Modelled carriage braking after release (distance, time, energy) instead of the closed
   form added to the facility length, and a sealed-shaft air column (adiabatic trapped
   column) beside the vented default. Proposed, and the first items to cut if the session
   runs short: they move facility length, drive force and energy, and under the
   force-limited drive the exit speed, but they are not the structural answer (section
   5.7). TODO.md B-007 is re-targeted when Plan mode confirms them.
7. Validation tests for each new physics piece before any experiment uses it (section
   5.9); `docs/physics.md` updated in the same change as each.
8. A pre-registered experiment (committed before it is run), the runs from a clean
   commit, the findings, and SP7's close per the protocol (public face, SP3's file
   fact-checked, handoff, memory).
9. KI-030 (TODO.md, medium, owner SP7 since SP2 step A0): the config accepts `true`,
   numeric strings, inf and NaN for several numbers. Closed on the existing models by
   strict types, `allow_inf_nan=False` and bounds, which validate and change no resolved
   dict (section 5.10, risk R4): `ConstantAccelConfig` (config.py 618: `stroke_m`,
   `net_accel_g`, `brake_decel_g`, `carriage_mass_t`), `TrackConfig` (589:
   `exit_altitude_m`), the ignition and startup models (`t_ign_s`, `t_ramp_s`) and
   `OffloadCaseConfig` (1624: `paired_pad`, the fixed block's `stage1_fraction`);
   `LinearMotorConfig` is born with them. Proposed for step S4's config change; Plan mode
   confirms (added at the re-check of 2026-10-07).

**Out of scope (each has a home)**

- Structural FEM, shell buckling analysis beyond closed forms, or any load model beyond
  first order. CLAUDE.md lists structural FEM as a scope expansion that needs the user's
  approval; this file does not propose it (section 5.3, option C).
- Bending from wind or q-alpha, lateral loads on the track, and the max-Q load case as a
  sizing input beyond what the envelope check needs. The kick has no angle-of-attack
  aerodynamics in the model (RQ6); a q-alpha structural case needs that first.
- The curved track and the frictionless circular-arc ramp test, the cable winch and its
  small-oscillation test, friction, the tilted-exit abort with Coriolis, engine shutdown
  transients: the README Phase 3 remainder (TODO.md B-006, B-008, B-009, friction in
  B-007), on the board's "Later" table. Friction from the normal load is zero on a vertical
  straight track (its track-normal load is 0; RQ3-2d, "Loads"), so it belongs with the
  curved and inclined tracks.
- A resized vehicle (tanks shrunk around the offload; RQ7) and interface hardware on
  stage 2.
- Throttling and a max-Q constraint (TODO.md B-003, README Phase 5).
- The 3-D models (SP3-SP6) and the app's form: SP2's app offers `stage1_dry_mass_added_t`
  as its only structural input (appform.py 398-405, "Assumed structural penalty, stage-1
  dry mass added (0: none)", D-SP1-04) and a `constant_accel` push only (appform.py
  104-105); a modelled-structure switch or a linear-motor launch in the form is a backlog
  item unless the user asks for it in Plan mode (section 10). The app copies the shared
  blocks and the baseline of experiments/silo_offload_2d.yaml at server start, so a
  change to that file changes what the app launches: allowed, but stated (entry
  criterion 8).
- Any change to a validated number: the pad baseline, the 1-D golden outputs, the planar
  digests, SP1's recorded runs (section 5.10).

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-18 (2026-10-04, user): SP2 runs next as planned; then this phase, SP7, for the
  structural mass of the push load and a force-limited drive, inserted before the 3-D
  phases SP3-SP6, because the structural cost decides whether SP1's 10% survives while
  the 3-D models are expected to move it by kilograms. Phase numbers are never
  renumbered. It amends the order of D-SP1-07.
- D-SP1-04: the structural penalty is shown as parametric rows (+2, +4, +8.1 t of assumed
  stage-1 dry mass on the assisted run only). SP7 keeps those rows beside the modelled
  mass; it does not replace them.
- D-SP1-03: offload semantics (stage 1 is the headline; tanks partly filled, dry masses
  unchanged except a penalty; fixed payload P_ref = the full-load pad's P* on the same
  vehicle and orbit). The modelled structure is an added dry mass on the assisted run
  only; the pad keeps its vehicle.
- D-SP1-09 and D-SP1-10: the `offload:` block and post-pass; pad controls; stage 1 the
  only headline.
- D-SP1-08: one fresh session for the phase; it prepares the next phase's documents,
  memory and prompt (SP3 in the planned order).
- D-SP1-14 to D-SP1-16: push after every step; public face kept current at the close.
- D-P1-01: `constant_accel` is a prescribed net acceleration, so carriage mass and drive
  efficiency move only energy and power, and a hot start buys no exit speed. The linear
  motor is the model where they can move the exit speed and the offload.
- D-P2-08: the gate vehicle's +14.3% calibration miss travels with every number.
- D-SP7-01 to D-SP7-35 (2026-10-08, step 0): the user's answers to Q1-Q7 and the app point
  (D-SP7-01 to D-SP7-08), the four follow-ups after the review of the draft (D-SP7-09 to
  D-SP7-12), and the design approved with the plan (D-SP7-13 to D-SP7-35; D-SP7-35 amends
  D-SP1-03). The design and its reasons: docs/phases/inputs/2026-10-08-SP7-design.md.

## 4. Entry criteria

Checked 2026-10-07 at 705025f by SP2's close-out (protocol section 7, item 8); each item
carries its state at that check. SP7's start checklist (protocol section 3) re-runs entry
criteria 2, 3, 6 and 7 against the HEAD it finds: the Close SP2 commit follows 705025f, so
the inventory's stated commit is not that HEAD and protocol section 3, item 5 re-checks
section 6 (the prompt of section 13 asks for it).

1. SP2 is "done" on the program board (the planned order, D-SP1-18, confirmed at SP2's
   close by D-SP2-40). SP7's physics uses nothing from SP2's app, but SP2's readers now
   display what SP7 produces and the app copies an experiment file (item 8), so the order
   matters: had the user moved SP7 ahead of SP2, SP1 "done" would have been enough, logged
   as a decision, with SP2's file re-checked afterwards.
   State at this check (705025f, before the close-out's remaining items): the board row
   and the SP2 phase file still read "in progress (session 2026-10-05)"; SP2's session
   log ended at step A7 part 2 with step A8 (the exit-criteria gate, the full suite, this
   fact-check, the handoff) named as next and its section 8 held no pass/fail record;
   docs/handoff/NEXT_SESSION.md was still SP1's (closing commit 5007515). The last commit
   that changed code or results was 3a1b243 (the demo launches); HEAD was 705025f (SP2
   step A7's tracker commit, D-SP2-40). Protocol section 7, items 1, 4, 5 and 9 record
   the 17-criterion gate in SP2's section 8, set the board to "done (2026-10-07, commit
   3a1b243)" and write the new handoff naming 3a1b243, all before the Close SP2 commit;
   the start checklist confirms the three, and this criterion fails if any is missing.
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3), subject "Close SP2: trackers, handoff,
   next phase file"; `git diff --stat <closing commit> HEAD` touches only docs/, TODO.md,
   CLAUDE.md, README.md, .gitignore and site/ (the public-face refresh, as at SP2's start).
   State: the tree was clean at 705025f when this check ran; the start checklist confirms
   the subject and the ancestry.
3. Fast suite green (`uv run pytest -q -m "not slow"`); ruff clean; the 1-D golden tier,
   SP1's planar digest pin
   (`tests/test_config_planar.py::test_shipped_planar_resolved_dicts_match_the_pinned_digests`,
   323; `PLANAR_EXPERIMENTS` at 62) and the planar output capture
   (`tests/test_planar_pipeline.py::test_written_outputs_keep_the_captured_structure`,
   1146) pass; the pad and silo_cold payload capacities reproduce 26,054.3962 and
   27,553.2271 kg within 0.002 kg (SP1 step 5 gate).
   State: the last recorded fast run before the close is 1678 passed, 41 deselected (SP2
   step A7 part 1, 7cb440f); the close-out's full-suite count is recorded in the handoff
   written at the close (docs/handoff/NEXT_SESSION.md, section 7). The two
   capacities are pinned at full precision in tests/data/silo_screening_2d_record.json
   (pad 26054.396243494975 kg, silo_cold 27553.227114190096 kg; git 7ad381f, the recorded
   results/silo_screening_2d/20260930T175743Z) and re-solved within `PAYLOAD_TOL_KG` =
   0.002 kg by the slow
   `tests/test_silo_screening_record.py::test_recorded_payload_capacity_reproduces`
   (40-57); tests/test_planar_pipeline.py 1290-1322 checks the record's provenance
   (`RECORDED_SILO_COLD_PAYLOAD_KG` at 1293). SP2's step A4 gate reproduced both and the
   headline offload (41,262.908 kg) through the app's launch function with every
   difference 0.000 kg (6f22046); the app pins them as `SP1_HEADLINE` with
   `REPRODUCTION_TOL_KG` 0.002 kg (app.py 1420, 1542).
4. SP1's offload solver and pipeline exist as SP1 left them: `OffloadProblem` built from a
   problem factory (offload.py 151, 256), the `offload:` block with
   `stage1_dry_mass_added_t` (config.py 1642), the cross-vehicle decomposition with a
   dry-mass difference (compare.py 1534), and the slow test that re-solves the headline
   (`tests/test_offload.py::test_gate_silo_offload_recorded_run_and_verification`, 795).
   State: confirmed at 705025f. SP2 changed none of offload.py, vehicle.py, sim.py,
   results_io.py, compare.py, search.py, guidance.py, dynamics.py, losses.py, metrics.py,
   metrics_planar.py, the phases and assist packages, tests/test_offload.py,
   tests/test_config.py, tests/test_config_planar.py, tests/test_planar_pipeline.py, the
   experiment files or the vehicle files (`git diff --stat a5b8133 705025f`). Of the
   inventoried run-path files only config.py (+13 lines net, the `exploratory` label) and
   summary.py (+191 lines net, 205 changed; the exploratory banner) moved.
5. SP1's run data on disk for comparison: `results/silo_offload_2d/20261003T112934Z` (the
   headline and the penalty rows) and `results/silo_offload_2d/20261003T112949Z` (sweep 2,
   the fixed-exit-speed strokes), or re-runs of them from SP1's closing commit (CSVs are
   not tracked).
   State: both on disk at this check. 20261003T112934Z holds metrics.json,
   resolved_config.yaml, summary.md, plots/ and the run folders (pad, the three pad
   controls pad__offload_stage1, _stage2 and _both, silo_cold, silo_cold_200m,
   silo_cold_200m_s1, silo_cold_both, silo_cold_fix5pct, silo_cold_fix10pct, silo_cold_s1,
   silo_cold_s1__pad, silo_cold_s1_dry+2t, +4t and +8.1t, silo_cold_s1_s2pre2t,
   silo_cold_s2, ...), each with timeseries.csv and events.csv (silo_cold_s1 checked);
   20261003T112949Z holds baseline/, sweep_1 to sweep_5 and summary.md. results/app/
   holds SP2's six demo launches (20261007T125946Z to 20261007T131031Z): exploratory,
   never cited (D-SP2-37).
6. Section 6 of this file has been re-checked at the current HEAD and its commit and date
   updated by the session before SP7.
   State: done 2026-10-07 at 705025f (the block at the top of section 6). SP2 edited
   plots.py, replay.py, cli.py, summary.py and config.py (the label value only; no display
   block, D-SP2-18) and added modules; it did not touch results_io.py.
7. `gh` is authenticated and the last Pages deployment is green (push cadence, D-SP1-15).
   State: the handoff's section 1 names the check (`gh run list --workflow pages.yml
   --limit 1`); the last green run before SP2's close is 37713777230 at cb305a5; the start
   checklist re-runs the check against HEAD.
8. SP2's app and scene exist and SP7 keeps the app's basis valid (added at the re-check).
   `launchsim app` (app.py; cli.py 217) copies the six shared blocks and the baseline of
   experiments/silo_offload_2d.yaml, which must agree with experiments/silo_screening_2d.yaml,
   at server start (`app.OFFLOAD_EXPERIMENT` 164, `load_basis` 296 reads them at the
   server-start HEAD; `appform.make_basis` 582-633 checks the agreement and that every
   preset names a committed run or case). A change to silo_offload_2d.yaml therefore
   changes what the app launches and ends the app's "reproduction of SP1's headline" mark
   (`app.SP1_HEADLINE` 1420; `app.sp1_files_same` 2632-2657 and `app.sp1_comparison`
   2660): allowed, as a pre-registration amendment, but stated in the
   step that makes it, in the manual and in the findings; SP7's own experiment is a new
   file, so the default leaves the basis untouched. The display files under
   configs/display/ are never read by the run path (tests/test_scene.py 1373). The label
   `exploratory` (config.py 157-164) is reserved for app runs; no SP7 experiment uses it.
   State: `launchsim scene` and `launchsim app` present at 705025f with their tests;
   the demo record in docs/demos/SP2/.

## 5. Design

The brief's proposal, kept as written. **Superseded where it differs by the approved design,
docs/phases/inputs/2026-10-08-SP7-design.md** (2026-10-08); section 12 lists the changes.

Proposed, for SP7's Plan mode to confirm or change. Three CLAUDE.md rules bind it:

- Plan mode for anything touching equations of motion, frames, events, integrator settings
  or loss accounting, with `docs/physics.md` updated in the same change. The linear motor,
  the air column and the braking phase touch the track equation and events; the
  structural model changes a vehicle input (dry mass) only.
- No physics feature is used in an experiment until its closed-form test passes.
- Never tune a parameter to make an assist look better; never edit a calibrated vehicle
  file (copy it); justify every new dependency in one line.

### 5.1 What is charged today

Nothing structural. The 4 g0 full-stack push (3.996 g0 felt at 3 g0 net; 22.49 MN at the
interface for the full-load silo_cold, 20.81 MN for the offloaded headline) carries no
added mass. The README's first-order row: the interface carries 21.5 MN, 2.8 times
Falcon 9's liftoff thrust, and the hydrostatic pressure at the tank bottoms rises about
2.8 times over liftoff (README, "What can eat the gain"). The only stand-ins are:

- payload space (RQ3-2d): 184 kg of payload per tonne of stage-1 dry mass, from the
  +/-10% dry-mass cases; about 8.1 t of silo-only strengthening cancels the +1,498.8 kg
  gain (a linear extrapolation);
- offload space (RQ1): the penalty rows above; each tonne of assumed structure takes 4.5
  to 5.1 t off the offload, and the erosion steepens.

Both notes say plainly that the needed mass is unknown. SP7's model supplies an estimate
of it with an uncertainty band; it does not make the rows obsolete.

Where the code and the documents say "nothing structural" today (re-check of 2026-10-07
at 705025f). Each is a sentence SP7's modelled structure must change, at its source,
because SP2 step A1a made the replay page and the scene share one caveat source
(D-SP2-23) and regenerated the gallery pages when it reworded them: the run path's
`summary.OFFLOAD_CAVEATS` (summary.py 1680-1682: "no structural mass is charged for the
push load ...; the penalty rows add an assumed stage-1 dry mass, a parametric
assumption, not a sized structure"), `sim.offload_penalty_assumption` (sim.py
1690-1696: "not a structure sized for the push load", quoted in docs/physics.md
5997-6000) and the note `config.offload_overrides` (config.py 2671) writes on the penalty
case's stage-1 dry mass (2702-2705: "an assumed structural penalty, not a sized
structure"; it enters the case's resolved vehicle dict, outside the digest pin, which
covers the four pinned experiments and they declare no offload block,
tests/planar_pin_support.py 142-143); the replay and scene pages'
`replay.uncharged_structure_sentence` (replay.py 966: "No structural mass is charged for
the assist load case") and
`replay.penalty_structure_sentence` (1004-1008: "a parametric assumption, not a sized
structure; no structural model exists"), composed by `replay.structure_caveat` (1011);
the animation footnote `plots.animation_caveats` (plots.py 1069: "no sized structural
mass for the <peak> g push load", 1070-1074 the penalty-row clause); the exploratory
banner's `EXPLORATORY_PUSH_CAVEAT` (summary.py 761: "no structural mass for the push");
the manual (docs/manual/05b-offload.md 100: "not a sized structure"; 12-faq-glossary.md,
the glossary row **penalty row**, line 191 at the close: "a parametric stand-in for
structure, not a sized one"); and the app form's field text
(templates/app.html 1216: "a parametric stand-in for the structure a push needs, not a
sized structure"). Tests pin this wording in eight files (section 6: the six SP2 tests,
tests/test_offload_pipeline.py 232 on config.py's note and tests/test_app_page.py 1937 on
the form's text), so rewording it is a deliverable of step S3 with an
honesty review, not a side effect. A run with the structure charged says what was charged
and by which model; a run without it keeps today's sentences.

### 5.2 The load case the push adds

The push is one more quasi-static axial load case: every station x of the stack carries
the compressive load m_above(x) n g0, and each tank's liquid presses on its bottom with
p(h) = p_ullage + rho n g0 h, where n is the felt axial load factor and h the depth below
the liquid surface. What makes the push new is the combination of a high n with full
stage-1 tanks. The existing vehicle already flies (from the pad run's own time series):

- liftoff: about 1.36 g0 felt at release with full tanks (RQ3-2d, "Loads");
- MECO: 5.195 g0 felt on the 161.5 t stack, stage 1 nearly empty (RQ3-2d, "Loads";
  5.19547 g0 in RQ1's "Headline" table);
- max-Q in between (37.19 kPa unthrottled, pad).

The model charges only what the push needs beyond that envelope, station by station. A
first look from the recorded values, for the Plan mode to confirm with the model: at the
interstage and above, the mass is the same at the push and at MECO (stage 2 full, the
payload, the fairing), and the push's 4.0 g0 is below MECO's 5.2 g0, so the push should
not size stage 2 or the interstage. In the stage-1 tanks and the aft structure the push
carries the stage-1 propellant (all of it, less any offload) at about 4 g0 against
1.36 g0 at liftoff with the same tanks full, so that is where the mass goes. These statements are quasi-static. A sudden push overshoots: the
`constant_accel` model has infinite jerk at push start (its own assumption list), and a
step load on an undamped elastic structure peaks at twice the static load (the
dynamic-load-factor closed form for a step; for a linear ramp of rise time t_r it is
1 + |sin(pi t_r / T)| / (pi t_r / T), T the structure's period). The linear motor's force
rise time therefore enters the structural load, and the Plan mode decides whether SP7
charges a dynamic load factor from a stated rise time and an assumed period, or reports
the quasi-static mass with the factor as a sensitivity.

Where the load enters is a design choice with mass consequences (question Q5): an aft
ring at the stage base (the whole stack above is compressed, as under thrust), the thrust
structure (it then carries 22.5 MN instead of the engines' 8.23 MN vacuum thrust), or
supports along the body (they fly, and the README notes they concentrate loads). The
hydrostatic pressure at the tank bottoms is the same whichever way the stack is pushed.

### 5.3 Structural sizing model: options

| Option | What it is | Cost | Fit |
|---|---|---|---|
| A. Parametric fraction | Added mass = a load-bearing fraction of stage-1 dry mass times (n_push / n_envelope - 1), coefficients assumed | Small | Little more than the penalty rows with a rule for picking the row; the coefficients carry the whole answer and no closed form checks them |
| **B. First-order station sizing (recommended)** | Thin-walled cylinders and domes per tank: wall thickness from hoop stress (Barlow, p r / t) at ullage plus hydrostatic pressure, and from axial compression (inertial load less pressure relief p pi r^2) against a classical buckling allowable times a knockdown factor; tank bottoms sized by the hydrostatic pressure; the load-entry structure and the interface hardware scaled with the peak interface force by a sourced or assumed coefficient. Each element's thickness is taken as the larger of the push requirement and the envelope requirement; only the excess mass is charged | Medium: one pure module, about a dozen closed-form tests, a structure file with sourced coefficients | Every term has a closed form to test, the coefficients are physical (material allowables, factors of safety, knockdown, densities, ullage pressures) and can be sourced, and the increment is zero inside the envelope by construction |
| C. FEM or detailed shell analysis | A finite-element or shell-buckling model of stage 1 | Large, and a scope expansion that needs the user's approval (CLAUDE.md) | Not proposed: the model's inputs (geometry, the real envelope and margins) are not public, so the extra fidelity would rest on assumptions anyway |

Recommendation: B. Candidate sources to check in step S0 (named here as places to look,
not as values): NASA SP-8007 (buckling of thin-walled circular cylinders; knockdown
factors), NASA-STD-5001 (structural factors of safety for spaceflight hardware), material
data for the tank alloy, the propellant densities behind the vehicle file's LOX/RP-1 split
(287.4 t LOX and 123.5 t RP-1 in stage 1, configs/vehicles/generic_f9_class_2d.yaml), and
any public breakdown of the 22.2 t stage-1 dry mass (engines, thrust structure, tanks,
interstage). Where no source exists the number is `assumed: true` and gets a sensitivity.

A plausibility check, labelled calibration and not validation: the model's tank mass for
the pad's own envelope, against the stage-1 dry mass and its breakdown. Nothing is tuned
toward a target; a large disagreement is reported and widens the band.

### 5.4 Where the coefficients live

Proposed: `configs/structures/<vehicle>.yaml` (one per vehicle that an SP7 experiment
flies: the gate vehicle and, for the bridge, the README-loads fork), every number with
`source:` or `assumed: true`, validated by a pydantic model, read only by the structural
model. Alternatives: a `structure:` block inside a forked vehicle file (a copy of the
calibrated file, CLAUDE.md), or inside the experiment's `offload:` block. The separate
file keeps the calibrated vehicle files and every resolved dict of the shipped experiments
unchanged, which the digest pin checks (section 5.10).

### 5.5 Coupling to the offload solve

The structural mass depends on the stack on the track, which depends on the offload x
itself: a lighter stack needs less strengthening. Options:

| Option | How | Trade-off |
|---|---|---|
| **(i) Inside the problem factory (recommended)** | Wrap the factory SP1 built: the problem at offload x flies the vehicle offloaded by x with stage-1 dry mass raised by dm(x), the sizing model applied to that vehicle's push. `solve_offload` is unchanged | One solve; the solver's own monotonicity check (`offload_nonmonotone`) tests the argument that m_res still falls with x (dm falls as x grows, so this must be checked, not assumed) |
| (ii) Fixed point | Solve x with dm fixed, re-size at x*, repeat until dm changes by less than a tolerance | Uses the penalty-row path as it is; several solves (about 90-110 s each with the verification, measured in SP1) |
| (iii) Size for the full-load push | dm computed once for the full stack and charged at every x | Simple and conservative (a vehicle that can also fly full); over-charges the offloaded vehicle. Proposed as a bound row beside (i) |

Which load the structure is sized for (the offloaded stack actually flown, or the full
load) is a modelling choice that changes the answer; it is question Q2 for the user. A
cross-check that fixes the coupling: the structural model forced to return a constant
2 t must reproduce SP1's `silo_cold_s1_dry+2t` row (32,285 kg; RQ1) within the
reproduction tolerance SP1 used for its headline (about 3.8 kg; RQ1, "Headline").

Pre-registration idea for step S6: the modelled dm at the headline, computed before any
solve, placed on the penalty-row curve (32.29, 22.88, 1.98 t at +2, +4, +8.1 t) by
interpolation, gives the expected offload; the solve should land near it, differing only
through dm's dependence on x.

The payload form (RQ3) is re-solved the same way: silo_cold's P* with the modelled dm of
its full-load push, against the pad's 26,054.4 kg and the 184 kg-per-tonne line.

### 5.6 Uncertainty band

The coefficients, not the solver, set the uncertainty. Proposed: three coefficient sets
(low, central, high) fixed in the structure file before the run, each propagated through
a full offload solve; plus one-at-a-time sensitivities on the coefficients that move dm
most (identified in step S2 from the sizing model alone, without flying). The band is
reported as the offload range, with dm beside each end. If the band is wider than the
offload itself, the note says the model cannot decide whether the 10% survives, and why.

### 5.7 Drive realism and how it reaches the structural answer

| Item | Under `constant_accel` today | Under a force-limited drive | Reaches the structural answer by |
|---|---|---|---|
| Force and power limits (`linear_motor`) | Drive force unbounded, solved from the prescribed acceleration | F = min(F_max, P_max / sdot): constant force, then constant power; the exit speed follows from the limits and the stroke | Setting the felt g (and so dm) and the exit speed (and so the offload) together |
| Force rise time | Infinite jerk | A stated ramp of the drive force | The dynamic load factor of section 5.2 |
| Carriage mass | Moves only drive energy (the 22 t sled changed nothing for the vehicle and added 3.8% drive energy; RQ3-2d) | At a fixed F_max a heavier carriage lowers the acceleration, the interface force and the exit speed | Lower felt g, lower exit speed |
| Hot start | Thrust on the track buys no exit speed; the interface force falls to 14.5-14.8 MN against 22.5 MN (RQ3-2d) while the tanks feel the same g | Thrust adds acceleration and exit speed | The tanks see a higher g; in the force-limited phase the interface force is (m_v / M) F_max - T (m_c + f_imp m_v) / M, from the track equation of assist/base.py (exactly F_max for a massless carriage and no impingement). RQ1's ordering of hot starts "may change with a force- or power-limited drive" |
| Air column (sealed shaft) | Moves only drive force and energy; the vented shaft's drag biases energy, power and interface force low by about 0.04%, 0.08% and 0.08% (RQ3-2d) | Lowers the exit speed; the README bounds the piston force at atmospheric pressure times the bore area (up to 1.1 MN for a 3.7 m bore) | Whether it acts on the carriage (below the vehicle) or on the vehicle decides whether it reaches the interface force at all |
| Braking | Distance v^2 / (2 a_brake) added to the facility length (60 m at 5 g0) | The same closed form, now a modelled phase | Facility length and the failed-ignition geometry only; not the structural mass |

Linear motor closed forms for the tests, on a vertical track with constant mass M (a cold
start) and g = g_eff: the force-limited phase has a = F_max / M - g, v = a t, s = a t^2 / 2,
up to the corner speed v_c = P_max / F_max. In the power-limited phase,
M dv/dt = P_max / v - M g; with v_inf = P_max / (M g), from (t_c, s_c, v_c):

    t - t_c = (1/g) [ (v_c - v) + v_inf ln((v_inf - v_c) / (v_inf - v)) ]
    s - s_c = (1/g) [ (v_c^2 - v^2)/2 + v_inf (v_c - v) + v_inf^2 ln((v_inf - v_c) / (v_inf - v)) ]

and on a horizontal track (g = 0), v^2 = v_c^2 + 2 P_max (t - t_c) / M and
v^3 = v_c^3 + 3 P_max (s - s_c) / M. The assist energy identity of CLAUDE.md ("Validation
first") holds with eta and the piston work as stated terms. Parameter values (F_max,
P_max, rise time, carriage mass) are design choices marked `assumed: true`, chosen in Plan
mode by a rule stated before any run (for example: the limits that reach the headline's
76.7 m/s at 100 m with a stated rise time), never adjusted toward a better offload.

What SP2's readers do with a drive that is not `constant_accel` (re-check of 2026-10-07):
`replay.drive_caveat` (replay.py 1172; docstring 1177-1195, "no bias direction is
claimed" at 1190-1191) already puts such a run in its other-drive branch: the
classification loop 1209-1232 files a run whose `assist.model` is not `constant_accel`
under `others`, and the clause built for it at 1278-1291 says the carriage mass and the
shaft drag change the release speed and that their size "is not established here";
tests/test_caveat_wording.py 479-489 and 689-712 exercise it with `model: linear_motor`.
The replay labels read the push's acceleration from the metric `net_accel_g`, else the
assist block's `net_accel_g` (`replay.push_accel_g` 699-706); the scene reads
`net_accel_mps2`, `exit_speed_mps` and `stroke_m` from the metrics, else the assist
block, and derives the missing one of acceleration and exit speed from the stroke
(scene.py 513-528; `PUSH_SETTING_METRICS`, metrics_planar.py 933, names the push as a
setting). Under a
linear motor the exit speed is a result and the acceleration is not constant, so step S4
decides what those metrics hold for it (for example the mean acceleration and the
measured exit speed, named as such) and its gate looks at the replay and scene pages of a
linear-motor run; the scene's carriage and tank levels come from the time series and need
nothing new.

### 5.8 Experiments (proposed; pre-registered in step S6)

1. The headline case (3 g0, 100 m, cold start, stage-1 solve) with the modelled structure:
   central, low and high sets; the full-load-sizing bound row; SP1's penalty rows re-run
   or cited beside it.
2. The stroke at the fixed exit speed 76.7072 m/s (50, 100, 200, 300 m; SP1's sweep 2:
   felt 7.0, 4.0, 2.5, 2.0 g0; electricity 1,012 to 1,733 kWh; facility 110 to 360 m)
   with the structure charged: where depth stops being the same by construction, and
   whether a stroke exists where the structural cost is small against the offload.
3. `linear_motor` against `constant_accel` at the same exit speed and stroke; a hot start
   under the force-limited drive; carriage mass 0 against 22 t.
4. The air column (vented against sealed) under the force-limited drive, if taken.
5. The payload form: silo_cold's P* with the modelled structure.
6. The bridge on the README-loads fork (robustness against the calibration miss), one
   case.

The run time is minutes per solve (SP1: about 90-110 s per solve with its verification,
about 30 s per pad control; the full SP1 run about 14 min and its sweep about 21 min, with
the three SP1 commands running at once); Plan mode budgets the design against that.

### 5.9 Validation tests (before any experiment uses the piece)

- Hydrostatic pressure p = p_ullage + rho n g0 h against the closed form; the load factor
  of a push equals (a + g_eff) / g0 (3.9991 g0 at 3 g0 net in the 1-D model without
  rotation, docs/physics.md "Silo model"; 3.996 g0 on the planar track at 28.5 deg).
- Thin cylinder: hoop thickness p r / sigma; axial stress p r / (2 t) - F / (2 pi r t);
  classical buckling stress E t / (r sqrt(3 (1 - nu^2))) times the knockdown; dome
  thickness p r / (2 sigma) for a hemisphere. Each against a hand-computed value in the
  test, not the code's own formula.
- Zero increment inside the envelope, exactly; the increment non-decreasing in n and in
  the propellant on board; the pad's own load cases give zero.
- The coupling cross-check of section 5.5 (a constant 2 t reproduces the +2 t row).
- Linear motor: the force-limited and power-limited closed forms of section 5.7 (vertical
  and horizontal), the force and power limits honoured at every sample, the assist energy
  identity with eta (relative error < 1e-6, the CLAUDE.md bound), release at a target
  speed.
- Dynamic load factor: step (2) and linear ramp closed forms, if Plan mode takes it.
- Braking: distance v^2 / (2 a) and time v / a for a constant deceleration.
- Air column: p = p0 (V0 / V)^gamma for the trapped column and its work integral in the
  energy identity; the force bounded by p_atm A.
- Convergence: tightening tolerances 10x changes the structural offload by < 0.1%.

### 5.10 What must not move

- The 1-D golden tier, SP1's planar digest pin and the planar output capture.
- The pad and silo_cold P* within 0.002 kg; SP1's headline offload with the structural
  model off (the slow test of entry criterion 4).
- The shipped experiment and vehicle files, byte for byte. New config fields go on the new
  models (`LinearMotorConfig`, the structure file) or are left out of `model_dump` when
  unset, as SP1 did for `exit_speed_mps`; a default added to `ConstantAccelConfig` would
  change every resolved dict and break the digest pin (the same risk as SP3's risk 5).
- `templates/replay.html`'s sha256 (the template is frozen since SP2, D-SP2-34; KI-019
  and KI-031 wait for the phase that edits it, which SP7 does not) and the six committed
  gallery pages under site/examples/ (five replay pages and the scene page
  pad-vs-silo-offload-scene.html, D-SP2-23), unless a deliberate wording change regenerates them
  with the diff recorded, as SP2 step A1a did (added at the re-check of 2026-10-07).

### 5.11 Module layout (proposed)

| File | Content |
|---|---|
| `src/launchsim/structure.py` (new, pure) | load cases from a run's track and flight records, the envelope, the sizing elements, the increment |
| `src/launchsim/assist/linear_motor.py` (new, pure) | `LinearMotorAssist` behind `assist.base.AssistModel`, registered in `assist.ASSIST_MODELS` |
| `src/launchsim/config.py` | `LinearMotorConfig` (replacing the placeholder for that key), the structure-file model, the offload case's structure switch |
| `src/launchsim/offload.py`, `sim.py` | the factory wrapper of section 5.5 (or the fixed point) |
| `src/launchsim/results_io.py`, `summary.py`, `compare.py`, `metrics_planar.py` | structural rows in the offload block, metrics keys, assumptions; the decomposition already takes a dry-mass difference |
| `configs/structures/` (new) | coefficients and mass breakdown, sourced or assumed |
| `docs/physics.md` | sections for the structural model, the linear motor, braking and the air column; the assumptions; the test-to-equation map |
| `src/launchsim/replay.py`, `plots.py`, `summary.py` (the exploratory banner), `config.py` (the penalty note of `offload_overrides`, 2702-2705), `templates/app.html` (the form's field text, 1216), `docs/manual/` | the structural sentences of section 5.1 reworded at source for a run with the structure charged, and the tests of section 6 that pin them (added at the re-check of 2026-10-07) |
| `src/launchsim/run_data.py` (SP2, read-only reader) | unchanged unless a new metric needs a reader (the replay and the scene read through it); a new vehicle fork needs a `CALIBRATION_RECORDS` entry (run_data.py 958) or gets the no-record caveat |
| tests/test_scaffold.py `PHYSICS_MODULES` (27-39), tests/test_scene.py `RUN_PATH_MODULES` (108-125) | extended with `structure` and `assist/linear_motor` (docstring check; no import of display or scene) |
| tests/test_config.py 219-220 and 283-289, appform.py 187 | `PLANNED_MODELS` loses `linear_motor`: the pin at 220 and the parametrized refusal change; `ASSIST_UNION_TAGS` follows |

CLAUDE.md's layout lists the new modules at SP7's close.

## 6. Inventory of the code this phase touches

The code, and the documents whose numbers SP7 builds on.

First checked at commit cfd9059 on 2026-10-04 by the SP1 close-out (every `def`, `class`
and constant line found by grep at that commit; the working tree then held only
document, site and `plots.py` edits). Re-checked at commit 705025f on 2026-10-07 by the
SP2 close-out (protocol section 7, item 8): every symbol below was grepped again in the
working tree, which held only SP2's close-out document edits (none under src/ or tests/).
The block below lists every correction with its old value, the files SP2 added that SP7
must know about, and the facts the design relies on; the tables after it are corrected in
place and hold the 705025f values.

### Corrections found by SP7 step 0 at 22c62e9 (2026-10-08)

Nothing under src/, tests/, configs/ or experiments/ moved since 705025f, so every line below
holds at 22c62e9. The surveys (inputs/2026-10-08-SP7-survey/) found these errors of fact in
this brief (the design's section 9):

- Run times (5.5, 5.8): about 35-45 s per verified solve under three-way concurrency and about
  15 s per pad control, not 90-110 s and 30 s (survey 09).
- 5.10 and R4: a defaulted field on `ConstantAccelConfig` moves no resolved dict and no digest
  (resolved dicts are raw merged YAML); it breaks the dump-key pin at tests/test_config.py
  432-443 (survey 02). A field on a dataclass the 1-D golden dump reaches breaks the golden
  tier (review N1).
- Section 2 item 5 and 5.11: removing `linear_motor` from `PLANNED_MODELS` drops it from
  `ASSIST_UNION_TAGS` (appform.py 187); it does not follow (surveys 01, 02, 04).
- 5.1's sources miss `scene.structure_note` (scene.py 1296-1314), `app.SP1_HEADLINE`'s
  "Structure." caveat (app.py 1473-1478), summary.py 1821's row label, the three "dry masses
  unchanged" sentences (sim.py 1680-1685, summary.py 1688-1689, compare.py 1639-1645) and
  `OFFLOAD_CAVEATS`' drive item (summary.py 1683-1685) (survey 04).
- 5.2: a step peaks near 1 + 2 (n - 1), about 7 g0, not 2n; release is a second step (surveys
  01, 07).
- 5.7: eta does not enter the mechanical identity; the piston work is not "dissipated"
  (survey 01); a power limit cannot lower the felt g at a fixed (L, v_e) (surveys 01, 07).
- 5.5: a factory wrapper alone leaves `offloaded_vehicle` and the verification without dm
  (survey 03 measured `bug_suspect`); the transform belongs in `vehicle_at`.
- Entry criterion 4: tests/test_offload.py 795 re-solves the headline but does not pin x*
  (survey 03).
- TODO.md lines: KI-030 is at 347 and KI-036 at 353 at 22c62e9 (survey 09; this block's
  section 6 text says 346 and 352).
- tests/test_scaffold.py's "phases" entry of `PHYSICS_MODULES` is silently skipped (no
  src/launchsim/phases.py; survey 09).

### Re-check of 2026-10-07 at 705025f (SP2 close)

**Method and what did not move.** `git diff --stat a5b8133 705025f -- src tests configs
experiments pyproject.toml .gitignore` (SP2's start commit to its last tracker commit)
lists 32 files: the new modules, templates and tests, `cli.py`, `config.py` (+13 lines
net), `plots.py`, `replay.py`, `summary.py`, `tests/test_animate.py`,
`tests/test_offload_pipeline.py` (one note assertion), `tests/test_scaffold.py` (one list
entry), `.gitignore`, `pyproject.toml` (Pillow in the dev extra, KI-018) and
`configs/display/`. Every other inventoried file is byte-identical to cfd9059 and every
line of it below holds: the assist package, `offload.py`, `vehicle.py`, `sim.py`,
`results_io.py`, `compare.py`, `dynamics.py`, `phases/prelude.py`, `phases/engine.py`,
`metrics.py`, `metrics_planar.py`, `tests/test_silo.py` (1,223 lines),
`tests/test_offload.py` (the slow gate-fork tier from 725, the gate test at 795),
`tests/test_config.py`, `tests/test_config_planar.py`, `tests/test_planar_pipeline.py`,
`tests/test_assist_energy.py`, the experiment files and the vehicle files.
`docs/findings/RQ3-silo-screening-2d.md` is unchanged ("Caveats" bullet 82-91, "Loads"
494-517).

**Corrections (symbol: old line -> line at 705025f).**

- `src/launchsim/config.py`, 16 moved (+5 from the `exploratory` label at 157-164; +13
  after the `ExperimentConfig` docstring at 1859-1862 and its validator at 1986-1990;
  `PlannedModel` 78 and `PLANNED_MODELS` 79 unchanged): `StageConfig` 434 -> 439;
  `TrackConfig` 584 -> 589; `NoAssistConfig` 607 -> 612; `ConstantAccelConfig` 613 ->
  618; `PlannedAssistConfig` 708 -> 713 (also section 2, item 5); `AssistConfig` 721 ->
  726; `OFFLOAD_STAGE1_INDEX` 1542 -> 1547; `OFFLOAD_DRY_MASS_KEY` 1547 -> 1552;
  `OffloadCaseConfig` 1619 -> 1624; the field `stage1_dry_mass_added_t` 1637 -> 1642
  (also entry criterion 4); the `paired_pad` refusal 1654 -> 1659; `ResolvedOffloadCase`
  2412 -> 2425; `offload_overrides` 2658 -> 2671; `offload_case_start` 2708 -> 2721;
  `offload_solved_run` 2734 -> 2747; `resolve_experiment` 2816 -> 2829. Added to the
  table: `shaft: Literal["vented"]` 646, `_dump_one_push_key` 679, the "planned for Phase
  3" refusal 723, `ExperimentLabel` and `EXPLORATORY_LABEL` 157 and 160. One reference
  made precise (it was imprecise at cfd9059 already, the file being unchanged):
  "tests/test_config.py 219-220, 283" -> 219 and 283-289 (`test_other_drives_are_phase_3`
  matches "Phase 3" at 285 and 288); 220 pins `PLANNED_MODELS == ("linear_motor",
  "cable_winch")`.
- `src/launchsim/summary.py`, 3 moved (the exploratory banner, 702-866, sits above them):
  `OFFLOAD_CAVEATS` 1500 -> 1677; `offload_caveats` 1553 -> 1730; `offload_section` 1897
  -> 2074. Added: `exploratory_banner` 814, `offload_calibration_caveat` 1707.
- `docs/physics.md`, 8 moved (SP2 added 299 lines, the display-only section among them):
  "Propellant offload at fixed payload" 1986 -> 2009; "Cross-vehicle decomposition" 3220
  -> 3243; "Assist energy identity" 4513 -> 4536; "Silo model (constant_accel, vertical)
  and every reported quantity" 4568 -> 4591; "Assumptions" 5750 -> 5786; the offload
  penalty line 5963 -> 5997-6000; "SP1 research notes" 6082 -> 6118; "Test-to-equation
  map" 6163 -> 6457. Added: "Experiment schema (planar)" 5412 with the label paragraph at
  5528-5539; "Display-only reconstructions (not part of the model)" 6199-6456.
- `docs/findings/RQ1-fuel-offload-2d.md`, 4 moved (12 lines changed since cfd9059, by
  SP1's own close-out): "Structural penalty rows and break-even" 284-317 -> 288-321;
  "Depth and g-level" 319-408 -> 323-412; "Max-Q and loads" 613-638 -> 617-642; "Limits"
  693-710 -> 701-718.
- `.gitignore` (section 9's note): SP2 added `*_scene.html` and `*_scene.mp4` to the
  ignored default outputs and did not add `!docs/demos/**`; its demo page is
  docs/demos/SP2/pad-vs-silo-cold-scene.html (hyphens, so not ignored).

Counts: config.py 16 moved, 4 rows added, 1 reference made precise; summary.py 3 moved, 2
added; physics.md 8 moved, 2 added; RQ1 4 moved; .gitignore 1 note; every other file 0.

**Files SP2 added or changed that SP7 must know about.**

- `src/launchsim/run_data.py` (new, 1,100 lines): the read-only reader that plots.py,
  replay.py, scene.py and summary.py use. `CALIBRATION_RECORDS` 958 is the one record
  (the gate vehicle 26,054.4 kg and the README-loads fork 24,700.0 kg against 22,800 kg);
  `plots.CALIBRATION_RECORDS` (plots.py 516) is the same object, `results_io.py` imports
  it from plots (143) for the offload caveats (1798), and `replay.calibration_caveat`
  (replay.py 876) and `summary.exploratory_banner` (summary.py 850) read run_data's
  directly (summary.py 1711's docstring still says `plots.CALIBRATION_RECORDS`). The
  bridge's README-loads fork has a record; a new vehicle fork gets the "no calibration
  record" caveat (summary.py 1715-1719) unless SP7 adds one, and tests/test_animate.py
  checks each entry against its findings note. Also `offload_role` 511,
  `CALIBRATION_GATE_VEHICLE` 982, `calibration_gap` 986.
- `src/launchsim/replay.py` (1,892 lines; its caveats are data-driven since step A1a,
  D-SP2-23, and the scene page reuses them): `uncharged_structure_sentence` 948 (the
  sentence "No structural mass is charged for the assist load case" at 966),
  `penalty_structure_sentence` 978 ("a parametric assumption, not a sized structure; no
  structural model exists", 1004-1008), `structure_caveat` 1011, `drive_caveat` 1172
  (docstring 1177-1195, "no bias direction is claimed" at 1190-1191; the classification
  loop 1209-1232 files a run whose `assist.model` is not `constant_accel` under `others`
  and its clause is built at 1278-1291), `comparison_caveats` 1455, `caveats` 1492,
  `calibration_caveat` 876, `push_accel_g` 699 (the metric `net_accel_g`, else the assist
  block's), `EXPLORATORY_LABEL` 129, `EXPLORATORY_CAVEAT` 133, `is_exploratory`
  737, `run_record` 1646, `replay_data` 1779.
- `src/launchsim/plots.py` (1,799 lines): `animation_caveats` 1049 with the footnote
  clause "no sized structural mass for the <peak> g push load" at 1069 and the penalty-row
  clause at 1070-1074; `calibration_caveat` 1020.
- `src/launchsim/summary.py`: `OFFLOAD_CAVEATS` 1680-1682 ("no structural mass is charged
  for the push load ...; the penalty rows add an assumed stage-1 dry mass, a parametric
  assumption, not a sized structure"); the exploratory banner 702-866 with
  `EXPLORATORY_PUSH_CAVEAT` = "no structural mass for the push" (761). Unchanged by SP2
  but the fourth and fifth sources of the sentence: `sim.offload_penalty_assumption`
  1690-1696 ("not a structure sized for the push load"), quoted in physics.md 5997-6000,
  and the note `config.offload_overrides` (config.py 2671) puts on the penalty case's
  stage-1 dry mass (2702-2705: "an assumed structural penalty, not a sized structure"),
  pinned by tests/test_offload_pipeline.py 232 (`"assumed structural penalty" in
  pen["note"]`). That note sits in the case's resolved vehicle dict, which the digest pin
  does not cover (the four pinned experiments declare no offload block,
  tests/planar_pin_support.py 142-143).
- `src/launchsim/config.py` 157-164: `ExperimentLabel` gains `exploratory`
  (`EXPLORATORY_LABEL` 160), reserved for the app's experiments (D-SP2-12): planar_2d, no
  sweeps, no cases, the banner (validator 1986-1990). No display block was added
  (D-SP2-18).
- `src/launchsim/display.py` (pure), `scene.py`, `appform.py`, `app.py`, `video.py`,
  `templates/scene.html`, `templates/app.html` (new) and `cli.py` (subcommands: run 90,
  sweep 108, animate 118, replay 163, scene 185, app 217). `configs/display/f9_class.yaml`
  and `scene.yaml` are read by scene.py only. tests/test_scene.py 1373
  (`test_run_path_modules_never_import_display_or_scene`; `RUN_PATH_MODULES` 108-125)
  guards that no run-path module imports display or scene: a new run-path module
  (`structure.py`, `assist/linear_motor.py`) goes into that tuple and, as a pure physics
  module, into `PHYSICS_MODULES` of tests/test_scaffold.py 27-39 (the docstring check).
- The app's basis: `app.OFFLOAD_EXPERIMENT` 164 (experiments/silo_offload_2d.yaml) and
  `SCREENING_EXPERIMENT` 167, read at the server-start HEAD by `app.load_basis` 296 (`git
  cat-file`), which calls `appform.make_basis` 582-633; that requires the two files to
  agree in their six shared blocks (`config.SHARED_KEYS` 171: dynamics, site, guidance,
  search, target_orbit, checks) and baseline and every preset (appform 217-235: pad, silo_cold,
  silo_hot_ramp_on_track, silo_cold_200m, silo_cold_s1, silo_cold_fix5pct,
  silo_cold_fix10pct, the three penalty rows, silo_cold_lag, silo_hot_full,
  silo_hot_full_impinged, silo_sled_22t, silo_failed, silo_instant, pad_instant) to name
  a committed run or case; `SILO_FRAGMENT_VARIANT` = silo_cold (96). `app.SP1_HEADLINE`
  1420 (41,262.908 kg, SP1's commit and directory) with `REPRODUCTION_TOL_KG` 0.002 kg
  (1542): a launch is called a reproduction of SP1's headline only while the experiment
  and vehicle files are unchanged since SP1's commit (`app.sp1_files_same` 2632-2657, a
  read-only `git diff --quiet`) and the committed case name and x* match (`app.sp1_comparison`
  2660). The form's assist is
  `constant_accel` only (appform 104-105); its only structural input is
  `stage1_dry_mass_added_t` (398-405, 0-100 t, `PENALTY_RANGE_T` 295); carriage mass 318;
  `ASSIST_UNION_TAGS` 187 is built from `PLANNED_MODELS`.
- Tests added: tests/test_run_data.py, test_display.py, test_scene.py, test_scene_page.py,
  test_appform.py, test_app.py, test_app_server.py, test_app_page.py, test_video.py,
  test_caveat_wording.py, test_site_build.py and tests/app_support.py. The structural
  wording is pinned in six of them, 25 occurrences: test_caveat_wording.py 12 (the four
  structure-caveat tests at 721, 746, 775 and 840), test_animate.py 4, test_scene.py 4,
  test_app.py 2, test_video.py 2, test_app_server.py 1. Two more files pin it, eight in
  all: tests/test_offload_pipeline.py 232 (an SP1 run-path test: `"assumed structural
  penalty" in pen["note"]`, the note `config.offload_overrides` writes at 2702-2705, so S3
  breaks it when it rewords that note) and tests/test_app_page.py 1937 (`template.count("a
  parametric stand-in for the structure a push needs") == 1`, the penalty field's text in
  templates/app.html 1216; changes only if the form's text changes). `linear_motor` as a run's model
  already appears in test_caveat_wording.py 479-489 and 689-712 (the drive caveat's
  other-drive branch) and in tests/test_config.py 219-220 and 283-289 (the refusal).
- TODO.md: KI-030 (medium, owner SP7, line 346; section 2, item 9); KI-032 (owner later):
  `drive_power_peak_t_s` is on the absolute run clock (metrics_planar.py 1012), the
  metric the linear motor's peak power reports, so S4 may take it; KI-036 (owner "the
  phase that next edits replay.py", 352): the replay page reads an unknown git state as
  clean, so it falls to SP7 when S3 edits replay.py; KI-019 and KI-031 stay with the
  phase that edits replay.html (SP7 does not). Decisions: D-SP2-37 (the app-runs rule,
  protocol section 4), D-SP2-39 (`pad_variant`), D-SP2-40 (SP7 next).
- docs/manual/05b-offload.md 100 describes the penalty row as "not a sized structure" and
  12-faq-glossary.md 167 (the glossary row **penalty row**) as "a parametric stand-in for
  structure, not a sized one".
  README.md: "What can eat the gain" 219 with its "Simulation updates" paragraph 238;
  "Roadmap" 407. These are the lines at 705025f; the close-out's README and manual edits
  (committed in 96bbfa1) move the glossary
  entry to 191 and the README anchors to 233, 252 and 421, and leave 05b-offload.md 100
  where it is; SP7's start reads them at that commit.

**Documents (the record SP7 builds on)**

| Where | What |
|---|---|
| README.md, "What can eat the gain" | the axial-load row (21.5 MN, 2.8 times liftoff thrust; hydrostatic about 2.8 times liftoff), the interface-hardware row (1 kg on stage 1 costs about 0.13 kg of payload in the screening; 0.18 kg in 2-D), the silo-air and carriage-braking rows, and the "Simulation updates" below the table |
| README.md, "Roadmap" | Phase 3's items and its "Done when" (track, ramp-energy, release-mapping, energy-balance and cable tests) |
| TODO.md, backlog and "Future items" | B-004 (structural mass and interface hardware) and B-005 (linear motor), re-targeted to SP7 by D-SP1-18; B-007 (air column, friction, modelled braking, release at a target speed), still "later" when this file was written; B-006, B-008, B-009 stay later |
| docs/findings/RQ1-fuel-offload-2d.md | "Structural penalty rows and break-even" (288-321): the four rows, erosion 4.5-5.1 t/t, zero at about 8.5 t extrapolated, screening level at about 5.5 t; "Depth and g-level" (323-412): sweep 2 and the reading that a lower felt g pays off only through a lighter structure; "Max-Q and loads" (617-642); "Limits" (701-718) |
| docs/findings/RQ3-silo-screening-2d.md | "Caveats", no structural penalty (82-91): 184 kg of P* per tonne, break-even about 8.1 t; "Loads" (494-517); the 22 t sled and the vented-shaft bias |
| docs/physics.md | "Propellant offload at fixed payload" (2009), "Cross-vehicle decomposition" (3243), "Assist energy identity" (4536), "Silo model (constant_accel, vertical) and every reported quantity" (4591), "Experiment schema (planar)" (5412; the label paragraph 5528-5539), "Assumptions" (5786; the offload penalty line at 5997-6000), "SP1 research notes" (6118), "Display-only reconstructions (not part of the model)" (6199-6456, SP2; nothing of the model), "Test-to-equation map" (6457) |
| configs/vehicles/generic_f9_class_2d.yaml | stage-1 dry 22.2 t, propellant 410.9 t (287.4 LOX + 123.5 RP-1), reference area 10.52 m^2 (3.66 m body); calibrated, never edited |

**Assist package: `src/launchsim/assist/` (the drive models that exist)**

| Symbol | File and line | Note |
|---|---|---|
| `ASSIST_MODELS`, `build_assist` | `__init__.py` 27, 36 | registry keyed by the config's `model`; a new drive is registered here |
| `TrackGeometry`, `AssistForces`, `AssistModel`, `AssistBuilder`, `normal_load_N` | `base.py` 36, 69, 89, 175, 192 | the seam: `state_rate` returns sddot, drive force, normal force, interface force, dissipated power and extra-state rates; `extra_state_names` for a drum or cable state; `push_time_estimate` is "an estimate for a force-limited drive" |
| `NoAssist` | `none.py` 17 | the pad |
| `ConstantAccelAssist` | `constant_accel.py` 31 | prescribed a; F_drive = M (a + g_eff sin phi) - (1 - f_imp) T; F_int = m_v (a + g_eff sin phi) - T; assumptions list "infinite jerk at push start and release" and "shaft vented (no air column), no friction" |
| `StraightTrack`, `VERTICAL` | `track.py` 18, 13 | straight track only; curved arcs are the Phase 3 remainder |

**Config: `src/launchsim/config.py`**

| Symbol | Line | Note |
|---|---|---|
| `PlannedModel`, `PLANNED_MODELS` | 78, 79 | `linear_motor`, `cable_winch`; refused as "planned for Phase 3" (the raise at 723; tests/test_config.py 219 and 283-289, the pin of the tuple at 220) |
| `ExperimentLabel`, `EXPLORATORY_LABEL` | 157, 160 | SP2: the app's label (D-SP2-12), validator at 1986-1990; never on an SP7 experiment |
| `StageConfig` | 439 | `dry_mass_t`, `propellant_mass_t` |
| `TrackConfig` | 589 | `angle_deg` 90 only ("a Phase 3 feature", 601) |
| `NoAssistConfig`, `ConstantAccelConfig`, `PlannedAssistConfig`, `AssistConfig` | 612, 618, 713, 726 | `shaft: Literal["vented"]` (646); `_dump_one_push_key` (679) is the model for leaving unset keys out of a dump |
| `OFFLOAD_STAGE1_INDEX`, `OFFLOAD_DRY_MASS_KEY` | 1547, 1552 | |
| `OffloadCaseConfig` | 1624 | `stage1_dry_mass_added_t` 1642; refused with `paired_pad` (1659) |
| `ResolvedOffloadCase` | 2425 | |
| `offload_overrides`, `offload_case_start`, `offload_solved_run` | 2671, 2721, 2747 | where a penalty enters the vehicle dict |
| `resolve_experiment` | 2829 | |

**Solver, pipeline and reporting**

| Symbol | File and line | Note |
|---|---|---|
| `OffloadProblem` (`vehicle_at`, `problem_at`), `planar_problem_factory`, `solve_offload` | `offload.py` 151, 256, 472 | the factory seam of section 5.5 |
| `with_offload`, `with_stage_propellant`, `offload_split_kg`, `Stage`, `Vehicle` | `vehicle.py` 653, 600, 613, 162, 480 | |
| `check_resolved`, `offload_penalty_assumption`, `offload_problem_factory`, `solve_resolved_offload`, `offload_run_result` | `sim.py` 932, 1690, 1708, 1717, 1728 | |
| `_offload_assumptions`, `planar_offload` | `results_io.py` 1291, 1687 | penalty rows in the post-pass |
| `OFFLOAD_CAVEATS`, `offload_caveats`, `offload_section` | `summary.py` 1677, 1730, 2074 | the summary block and its caveats (the structural sentence at 1680-1682); `exploratory_banner` 814 (SP2) |
| `cross_vehicle_decomposition` | `compare.py` 1534 | carries `xv_dry_mass_delta_kg` |
| `g_eff_track`, `TrackParams`, `rhs_track` | `dynamics.py` 114, 372, 438 | the track equation the linear motor and air column feed |
| `track_params`, `fly_track` | `phases/prelude.py` 737, 774 | the push to the track exit |
| `ev_track_end`, `ev_drive_limit` | `phases/engine.py` 674, 688 | release at s = L; a target-speed release needs its own event |
| `TRACK_COLUMNS`, `track_metrics`, `track_flags` | `metrics.py` 60, 441, 525 | |
| `PUSH_SETTING_METRICS`, `planar_track_metrics` | `metrics_planar.py` 933, 963 | |

**Tests to keep green and to copy from**

- `tests/test_silo.py` (1,223 lines): the straight-track closed forms, loads, felt g.
- `tests/test_assist_energy.py`: the assist energy identity, hot starts included.
- `tests/test_offload.py` (slow tier from 725) and `tests/test_offload_pipeline.py`.
- `tests/test_config.py` (planned models refused, 219 and 283-289; the tuple pinned at
  220), `tests/test_config_planar.py` (`PLANAR_EXPERIMENTS` 62: a new experiment file is
  classified there; the digest pin at 323).
- `tests/test_golden_1d.py`, the planar digest pin and the planar output capture
  (`tests/test_planar_pipeline.py` 1146); `tests/test_silo_screening_record.py` (slow:
  the two recorded payload capacities within 0.002 kg).
- SP2's: `tests/test_caveat_wording.py` (the structural and drive caveats, per clause),
  `tests/test_animate.py`, `tests/test_scene.py` (`RUN_PATH_MODULES`), `tests/test_app.py`,
  `tests/test_video.py`, `tests/test_app_server.py` (the pinned wording of section 5.1;
  with `tests/test_offload_pipeline.py` 232 and `tests/test_app_page.py` 1937 the eight
  files); `tests/test_scaffold.py` (`PHYSICS_MODULES`); `tests/test_run_data.py` (the
  reader).

## 7. Steps

The approved design's step table (docs/phases/inputs/2026-10-08-SP7-design.md, section 5), with
Status and Commit columns. It replaces the brief's table (kept in git at 22c62e9); section 12
lists the differences. Loop per step: implementer; adversarial reviewers (a physics or numerics
skeptic on every code step and on S0; a CLAUDE.md compliance auditor on every step, who also
checks docstring content; an honesty auditor on S0, S6a, S6b, S7a, S7b and on every step that
writes or rewords a summary sentence, caveat, label, metric name or assumption line; a visual
reviewer on anything drawn); up to two fix rounds (a third, for minors only, is logged as a
deviation); an independent gate; one commit; the tracker commit at once; push and the Pages
check. Standing gates on every code step: fast suite green; ruff clean; the exact 1-D golden
tier; the planar digest pin; the planar output capture; the field lists of the golden-dumped
dataclasses (a fast test, from S1); no shipped experiment or vehicle file changed (`git diff
--quiet <start commit> HEAD -- configs/vehicles` and the seven shipped experiment files);
templates/replay.html's sha256; docs/physics.md holds the step's section and test-map rows. The
full suite (in the background, beside the reviews) after S3, S3b, S4, S4a, S4b and S5 and in C2.
Tests run on synthetic directories, the synthetic structure file or short flights in a temporary
folder, never on results/ and never on a pre-registered case (D-SP7-31). Reviewer and gate runs
use `--results-root <scratch>` (D-SP2-37).

| # | Step | Main files | Gate | Status | Commit |
|---|---|---|---|---|---|
| 0 | Plan mode: checklist, nine surveys, the questions, draft v1 and its six reviews, version 2 | docs/phases/inputs/ | the user approves (2026-10-08) | [x] | the start commit ("Start SP7: status in progress") |
| S0 | Sources: every coefficient's range with its source or reason; both stages' layouts; the breakdowns; the Delta_gamma digitization; the ring's N_p, h/b and fitting factor; NOF by fidelity; t_r and f; the payload limits; the coefficient count; the linear-motor rules' method | docs/phases/inputs/2026-10-08-SP7-sources.md | every number sourced or assumed with a reason; no range narrower than its source's spread without a reason; honesty and physics review | [x] | 81e045d |
| S1 | Sizing primitives (pure structure.py), units, named constants, test hygiene (D-SP7-34, KI-035) | structure.py, units.py, constants.py, physics.md, tests | each closed form against a hand value at 1e-12 relative; one sizing evaluation timed | [x] | a3bd183 |
| S2 | Station model of both stages, `LoadCase`, the envelope from a pad Result, the flags, the plausibility rule, `StructureConfig`, the loader and the two structure files, the screened search and tornado frozen into the files | structure.py, config.py, cli.py, sim.py, configs/structures/, physics.md | the pad's own cases give 0.000 kg; stations converge (< 0.1 kg); provenance; shared sections identical; the frozen sets reproduce (slow, under 10 min); the sizing-only table in the session log | [x] | 45e39d4 |
| S3 | Coupling: the transform, its builder, dm in the verified dict with its provenance, memo keys, the offload case field and the experiment block, refusals, run-level keys, the pins | offload.py, sim.py, results_io.py, config.py, cli.py, physics.md | constant-2 t cross-check = SP1's +2 t row (<= 0.002 kg, slow); structure-off headline (<= 0.002 kg, slow); dm' bound and smoothness; vehicle_at bit-identical across call orders; xv_dry_mass_delta_kg = dm1 + dm2; with no structure block, `launchsim run experiments/silo_offload_2d_readme.yaml --results-root <scratch> --no-plots` at the start commit and at S3 give metrics.json and summary.md identical apart from timestamp and git; full suite | [x] | 889f6ea |
| S3b | Reporting: the payload cases, `structure_inputs`, the Structure subsection, the sweep and arm columns, the thickness figure, the post-hoc flight check | results_io.py, summary.py, plots.py, sim.py, physics.md | listed tests; full suite; visual and honesty review | [x] | 216a79c |
| S3a | Wording at every source (three-way, every run kind); KI-039, KI-036, KI-038 (version); the pinned wording tests; the gallery regenerated | summary.py, compare.py, sim.py, config.py, replay.py, scene.py, plots.py, app.py, docs/manual | the eight pinned files updated; the gallery diff is the one recorded line (read as: the scene page differs only in the four regions of section 12, deviation 32; the five replay pages byte for byte); honesty review | [x] | 0a16a89 |
| (checkpoint 1) | resolve and preflight of file A and one non-headline short structural case; an in-progress handoff point | | preflight of every run of A and C; one synthetic-file timing case (185.2 s) | [x] | cbbd7bc |
| S6a | Files A (silo_structure_2d.yaml) and C (silo_structure_2d_readme.yaml) and the pre-registration, part 1, committed before any run | experiments/, docs/phases/inputs/, tests/test_config_planar.py | the expected readings recomputed by the gate; `git diff --quiet <S2 commit> HEAD -- configs/structures/`; honesty review; clean tree | [x] | cbbd7bc |
| S7a | `run` A, `sweep` A, `run` C from the clean commit; the findings note's structural part | results/ (summaries), docs/findings/ | no `bug_suspect`; verifications within 1e-4 P_ref or flagged; reproductions within 0.002 kg; the frozen sets recomputed; honesty review | [x] | 6fa2ff0 |
| S3c | The sweep's no-offload record, added at S7a (D-SP7-48): `<case>.dv_shortfall_mps` appended to the sweep index, the no-offload lines under the sweep table; Amendment 1 of the pre-registration (74eb3c8); then `sweep` A re-run | results_io.py, summary.py, tests/test_offload_pipeline.py, physics.md | the column and lines on synthetic sweeps (fast tests); the standing gates; honesty review of the wording | [x] | 1e4c732 (pass-3 minors 77e1691) |
| S4 | linear_motor core: both control laws, ramp, taper, caps, carriage, braking functions, the pending ignition, refusals, metrics; KI-030; KI-021-KI-023 | assist/linear_motor.py, assist/base.py, config.py, appform.py, units.py, compare.py, phases/prelude.py, phases/engine.py, phases/planar.py, metrics*.py, physics.md | closed forms at 1e-9 relative; limits honoured at every sample; energy identity < 1e-9 (required 1e-6); hot interface force for f_imp 0, 0.5, 1; refusals; pending ignition in 1-D and planar; KI-030's sixteen cases refused with digests unchanged; braking functions; full suite | [x] | 25967be (merge 8c4b41a) |
| S4a | Release at a target speed; the readers (replay drive clause, scene push labels); the app lists linear-motor and structural directories; the force-against-speed figure; conditional summary rows | phases/prelude.py, phases/engine.py, replay.py, scene.py, summary.py, plots.py, app.py, physics.md | event at sdot = v_release with s from the closed form; track_end runs bit-identical; a scratch linear-motor run's replay and scene pages reviewed against metrics.json; the app started on that scratch root lists and plays it with no 500; full suite; gallery regenerated | [x] | 7cdc24a |
| S4b | The structural transform on linear-motor pushes | sim.py, structure.py, physics.md | n_peak, F_peak and DLF against closed forms (both laws, cold and hot, target speed, taper); a slow coupled linear-motor solve with no `offload_nonmonotone`; linear-motor convergence < 0.1%; full suite | [x] | b0fcc31 |
| S5 | The sealed shaft; the piston-work record | assist/linear_motor.py, dynamics.py, losses.py, physics.md | the adiabatic work closed form; F_p <= p_0 A; F_int lower by (m_v/M) F_p; the identity < 1e-9; `AssistEnergyBudget`'s fields unchanged; full suite | [x] | 460c4d6 |
| S5a | Sealed-shaft wording at the sources and the readers (added at S5's gate: KI-077, KI-079) | sim.py, phases/prelude.py, replay.py, scene.py, physics.md | no vented or constant_accel byte moves; a scratch sealed run's summary, replay and scene pages name the sealed shaft; honesty and visual review | [x] | 2bd40bd |
| (checkpoint 2) | the drive realism complete; an in-progress handoff point | docs/handoff/ | the handoff written at a step boundary, nothing running | [x] | cc16ec0 (the handoff commit follows) |
| S6b | File B (silo_drive_2d.yaml) and the pre-registration addendum | experiments/, docs/phases/inputs/ | the rule values recomputed independently to 1e-12; structure files unchanged; honesty review; clean tree | [x] | 331891d |
| S7b | `run` B; the note completed; RQ1's pointer; README results; the findings index; physics.md research notes; derived figures by a committed script | results/ (summary), docs/findings/ | B's silo_cold_s1_st within 0.002 kg of A's; lm_cmd's uncharged x* within 0.25 kg of SP1's; no `bug_suspect`; honesty review | [x] | e5f64b3 (scripts b291518) |
| S7c | Program-level wording in code (replay, the app's headline caveat, site/build.py, the compare.py docstring); the pinned tests; the gallery regenerated | replay.py, app.py, compare.py, site/build.py | `git grep -n "no structural model exists"` only in dated or archived records; full suite; honesty review | [x] | 9fe125c |
| S7d | A fast tier that holds under other projects' load (KI-090, KI-091; added after the demo's fast suite failed, deviation 57) | tests/, docs/physics.md's test-map rows | under 32 burners and a disk writer test_video.py and the sizing test 10 of 10, the fast suite in three chunks with and without the burner; a mutation for each changed test; full suite | [x] | cd14968 |
| S8 | Public face: the demo record, a gallery entry for an SP7 run, the deck slides and PDF, the manual chapters, the landing page, CLAUDE.md layout, status and commands, the protocol's caveat line | docs/demos/SP7/, site/, docs/manual/, CLAUDE.md, docs/process/ | site build with no broken link; visual, honesty and compliance review | [x] | 3a07f07 |
| C1 | Documents: this file, the board, TODO.md, SP3's file fact-checked, the handoff, memory | docs/, TODO.md, memory | compliance review | [x] | ead6e38 |
| C1a | The sweeps' missing columns: both sweep tables' peak electrical power (derived) and sweep 2's DLF in the findings note, after C2's first run failed criterion 7 (added, deviation 60) | docs/findings/RQ1-structural-2d.md | every added cell recomputed from the record; physics, compliance and honesty review | [x] | 185e35a |
| C2 | Independent exit gate on every criterion; full suite; cold read; closing commit; push; Pages | docs/ | each criterion passes or the user accepts a logged miss | [x] | the gate at e8c2366 (second run; the first, at a0e351e, failed criterion 7, deviation 60); the bookkeeping commit "Close SP7: trackers, handoff, next phase file" |

**If room runs out** (put to the user when it happens; compute-only cases and the CLAUDE.md arms
are never cut): S5 and lm_fixed_sealed; the payload cases; S4a's target-speed release with
lm_fixed_target; file C (the bridge); the thrust-structure row. A last resort tied to checkpoint
1: run A and C and write an in-progress handoff before building the drive. Since S7a's
commands started on 2026-10-16, three of these items are spent. The payload cases and the
thrust-structure row (silo_cold_s1_st_ts) are inside run A's command, and file C is run C.
All three are pre-registered and running or run, and dropping one would mean not reporting
a pre-registered result (pre-registration section 9). Only S5 with lm_fixed_sealed and S4a's
target-speed release with lm_fixed_target remain cut candidates.

**Effort**, by SP2's rhythm (three review passes on most steps): about 3 to 4 days of session
time; full suites in the background beside reviews; S0 in parallel with S1.

**Notes on the order.** The structural answer (files A and C) is registered and run after the
structural steps and before the drive is built (D-SP7-29), so a slip in the drive steps cannot
hold it up; file B's variants and rules are fixed by the approved design, so registering B
after A's results reopens no choice (said in B's addendum). The program-level wording (S7c) and
the public face (S8) come after the findings exist, as code steps with their own gates.

## 8. Exit criteria

Approved on 2026-10-08 with the design (docs/phases/inputs/2026-10-08-SP7-design.md, section 6);
the tolerances are fixed. They replace the brief's ten draft criteria (kept in git at 22c62e9);
the changes are listed after them.

1. **Validation first.** Every test of S1-S5 passes; each piece's test commit precedes the
   experiment commit that uses it (S6a or S6b; git log).
2. **Provenance and freeze.** Both structure files validate with every number sourced or
   assumed; their shared sections are identical; they are unchanged since S2's commit (or each
   change is a logged decision or amendment); configs/vehicles/ and the seven shipped
   experiment files unchanged since the start commit.
3. **Nothing validated moved.** The exact 1-D golden tier; the planar digest pin; the planar
   output capture; the golden-dumped dataclasses' field lists; the pad and silo_cold capacities
   within 0.002 kg; SP1's headline with the structure off within 0.002 kg of 41,262.908 kg (slow
   pin and S7a's case); SP1's three penalty rows within 0.002 kg (S7a); the constant-2 t
   cross-check within 0.002 kg of 32,285.203 kg; templates/replay.html's sha256; the gallery's
   six pages regenerated with only the recorded KI-038 line (read per D-SP7-47: the five
   replay pages byte-identical, the scene page differing only in deviation 32's four
   regions); the app's basis unchanged
   (`sp1_files_same` true) and the app's slow launch reproducing 41,262.908 kg within 0.002 kg
   after KI-030.
4. **The structural headline** from file A at a clean commit: the central case, the physics band,
   the outer envelope, the design-axis rows, the hot starts, the penalty rows; every case `ok`,
   or `no_offload` with its delta-v shortfall and payload deficit, or flagged; every verification
   within 1e-4 P_ref (2.605 kg) or flagged and reported as a bound; every decomposition
   explained; every structural case's `xv_dry_mass_delta_kg` equal to dm1 + dm2 at x* within
   1e-6 kg; no `bug_suspect`; no unexplained `offload_nonmonotone`; the pre-registered reading
   rules evaluated and every sentence that fired in the note's headline.
5. **The frozen sets** equal a fresh recomputation at S6a's commit and at C2; the extremality
   check's largest excess reported.
6. **Convergence.** Tightening the search tolerances 10x moves the central structural x* and one
   linear-motor structural x* by < 0.1%; doubling the stations moves dm by < 0.1 kg.
7. **Axes and drive.** The two sweeps and the nine linear-motor variants reported with felt g,
   DLF, n_peak, F_peak, dm by stage, x*, electricity, peak mechanical and electrical power, the
   facility length and, for the linear motor, the release position and speed; B's
   silo_cold_s1_st within 0.002 kg of A's; lm_cmd's uncharged x* within 0.25 kg of SP1's
   headline.
8. **The findings note** (docs/findings/RQ1-structural-2d.md) with RQ1's pointer, passing the
   honesty review, in the headline form of the design's 4.11; README results and the findings
   index updated; every structural sentence branched at its source; `git grep "no structural
   model exists"` only in dated or archived records; KI-030, KI-035, KI-036, KI-038, KI-039 and
   KI-021-KI-023 closed with their evidence.
9. **docs/physics.md** holds every new piece, its assumptions and its test-map rows.
10. **Full suite** green with the count recorded; ruff clean; no new dependency.
11. **Demo** recorded under docs/demos/SP7/.
12. **Close-out**: public face refreshed (landing page, deck and PDF, gallery with an SP7 entry,
    manual), site built with no broken link, main pushed and Pages green; SP3's file
    fact-checked; handoff, prompt and memory written; cold read done.

**Changes against the brief's ten.** Twelve criteria. Criterion 3's headline tolerance is
0.002 kg, not about 3.8 kg (same code and P_ref give the same bits; survey 03), and it adds the
cross-check, the penalty rows, the golden-dumped field lists, the gallery's recorded diff and the
app's basis. New: 5 (the frozen sets), 6 (convergence, out of 5.9), 7's cross-commit and lm_cmd
checks, 8's KI closures and the grep. The brief's 4 becomes 4 with the three layers and the
reading rules; its 5 becomes 7; its 6 becomes 8; 7 to 10 become 9 to 12.

**Exit criteria results (2026-11-09).** Checked by the independent gate of step C2 at
e8c2366 (clean tree, origin/main equal to HEAD), in four parts (criteria 1, 2 and 9; 3, 5,
10 and 12; 4, 6 and 7; 8 and 11), each with its own scripts outside the repository, every
command in the foreground and under ten minutes, nothing written in the repository or under
results/. This is the gate's second run. The first, at a0e351e
(2026-11-08 to 2026-11-09), passed criteria 1 to 6 and 8 to 12 and failed criterion 7 on
reporting only (the note's two sweep sections gave no peak electrical power, and sweep 2's no
DLF); the user chose to add the columns from the record and run the gate again in full
(D-SP7-57); step C1a added them (185e35a, deviation 60). The second run re-ran every criterion
from scratch and reused no verdict. All 12 pass. Criterion 12 covers what precedes the close's
documents; the cold read follows them (session log).

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Validation first | pass | All 306 SP7 tests come from 15 introducing commits (found with ast). Files A and C (registered cbbd7bc, run at 1b5f9d4, clean): S1 a3bd183, S2 45e39d4, S3 889f6ea, S3b 216a79c and S3a 0a16a89 precede both. File B (registered 331891d, run at 642e11e, clean): those five plus S4 25967be (merged 8c4b41a), S4a 7cdc24a, S4b b0fcc31, S5 460c4d6 and S5a 2bd40bd precede both. S3c (1e4c732, 77e1691; reporting only) follows cbbd7bc, was registered by Amendment 1 (74eb3c8) and precedes the sweep A re-run at 2b343d7 (dirty true, deviation 45, disclosed in the note). A and C use none of the S4-S5a drive pieces. No code changed between a registration commit and its run commit; the merge's src and tests equal 25967be's. "Every test of S1-S5 passes" rests on criterion 10's full suite |
| 2 | Provenance and freeze | pass | Both structure files validate through cli.load_structure and read_structure_file, the central set and all four frozen sets convert; every number sourced or assumed (gate file 496 of 496, fork 500 of 500; all 112 value/central mappings carry exactly one of source or assumed); the 15 shared sections identical. `git diff --quiet` exits 0 for configs/structures/ against 45e39d4 (its only commit), configs/vehicles/ and the seven shipped experiments against 22c62e9 and a7c9f0a, files A and C against cbbd7bc, file B against 331891d. The structure files' sha256 equal the pre-registration's and those recorded in every directory of A, B and C and all 27 sweep points |
| 3 | Nothing validated moved | pass | The exact 1-D golden tier (LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1) with the planar digest tests, the output capture and the golden-dump field lists: 284 passed, 0 skipped; tests/planar_pin_support.py "pins match". Slow pins: pad and silo_cold P*, SP1's structure-off headline (0.0 kg from the record), the constant-2 t cross-check (0.0 kg). Run A's silo_cold_s1 x* 41,262.90803733282 kg (+0.000037 kg from 41,262.908); its +2, +4 and +8.1 t rows equal SP1's to 0.000000000 kg. replay.html's sha256 1fa6eba6...6916990 in the tree, at HEAD, at a7c9f0a and in the installed package. Eight gallery pages regenerated, each byte-identical with HEAD; the five replay pages identical to a7c9f0a; the scene page differs from a7c9f0a only in deviation 32's four regions and KI-082's leaf (D-SP7-47). `sp1_files_same` true. The app, on a scratch results root, launched silo_cold_s1 complete in 80.1 s at 41,262.90803733282 kg; its sp1_comparison reproduces, differs [] |
| 4 | The structural headline | pass | Run A (results/silo_structure_2d/20261016T171513Z) and run C record git 1b5f9d4, dirty false; no code path changed from cbbd7bc. Run A: 24 cases (4 uncharged, 3 penalty, 17 structural), 21 ok, 3 no_offload, each with its shortfall and two-pass payload deficit (phys_hi 243.714 m/s, -2,080.41 kg; outer_hi 1,021.54 m/s, -7,804.35 kg; step 125.177 m/s, -1,086.88 kg). Every ok case verifies between +0.0006 and +0.0088 kg (bound 2.605 kg). All 24 decompositions and all 8 arms explained (worst residuals 8.4e-10 and -2.16e-9 m/s). `xv_dry_mass_delta_kg` equals dm1 + dm2 within 7.3e-12 kg on all 17 structural cases. No `bug_suspect`, no `offload_nonmonotone`, no fixed-point cap fired (at most 10 iterations of 25); run_checks ok on all 34 runs of A and 5 of C. The flags reported. Every pre-registered reading rule evaluated on the record; each fired sentence appears verbatim in the note's headline and the not-fired set matches; every fill of the fixed-form sentence matches the record (61 checks, 0 failed) |
| 5 | The frozen sets | pass | Both slow tests at e8c2366, one per command: generic_f9_class_2d 100.86 s, 6,789 evaluations; generic_f9_class_2d_readme_loads 101.33 s, 6,836; both counts equal the files' evaluation_count; set values compared exactly. Largest extremality excess 223.198 kg (file A, physics_low_mass, search B, one coordinate held, at rho_lox 1306.1); largest plain one-coordinate excess 11.806 kg (file A) and 7.671 kg (the fork); every random-sample check 0. These match the note |
| 6 | Convergence | pass | Central (silo_cold_s1_st, docs/findings/scripts/sp7_convergence.py, committed at 0a12c36 and byte-identical at HEAD): the shipped chain equals run A to the bit; the tightened x* 11,420.284416087732 kg moves +0.037778 kg (3.31e-6 relative, against 1e-3); doubling the stations moves dm by +6.2e-6 kg (against 0.1 kg); 0a12c36's code paths equal 1b5f9d4's. Linear motor (lm_fixed_s1_st): the report's sha256 equals the note's, its shipped x* and dm equal run B's to the bit, the tightened x* moves +0.027411 kg (2.42e-6). KI-089 (open, low) covers the linear-motor check's untightened track-peak scan and sampling step, as the note's Convergence section states (26 checks, 0 failed) |
| 7 | Axes and drive | pass | The note's sweep 1 (5 rows), sweep 2 (4 rows) and drive table (20 rows) against the sweep re-run's sweep_index.csv, point metrics.json and resolved_config.yaml and run B's metrics.json: 378 printed values, 0 mismatches. Every named column present: felt g, DLF, n_peak, F_peak, dm1 and dm2, x*, electricity, peak mechanical and electrical power, facility, and for the linear motor release position and speed (sweep 1's felt g and DLF and sweep 2's DLF in the sentence under each table; the sweeps' electrical peaks n/a with the derived bracket, the form D-SP7-57 decided). B's silo_cold_s1_st 11,420.246638573297 kg equals A's (0.000 kg, within 0.002). lm_cmd_s1's uncharged x* 41,262.909435 kg against SP1's 41,262.908037 kg (+0.0014 kg, within 0.25) |
| 8 | The findings note and the KI closures | pass | docs/findings/RQ1-structural-2d.md, preliminary: its headline matches the registered fixed form (design 4.11 with D-SP7-46) clause by clause, every branch the one the record selects, every number traced to run A. The honesty reviews of S7b, C1 and C1a pass on the record, and the gate's own spot check found nothing said beyond it. RQ1's pointer: one dated section (e5f64b3, 18 insertions, 0 deletions). README's SP7 section and the findings index trace to records A, C, B and the sweep re-run. Survey 04's C1-C11 and section 2.2's four sentences branch three ways at their source; offload_caveats() equals OFFLOAD_CAVEATS without structural records. `git grep "no structural model exists"`: only dated inputs, the archive, SP1's dated note line 37, this file and two quotations. KI-021, KI-022, KI-023 and KI-030 closed at 25967be (merged 8c4b41a), KI-035 at a3bd183, KI-036, KI-038 and KI-039 at 0a16a89, each read at source; KI-030 re-probed (16 of 16 inputs refused, the base resolves) |
| 9 | docs/physics.md | pass | The test-to-equation map read by a script: 464 rows, 823 named tests, 0 stale rows; all 306 SP7 tests (27 files, 12 new) have an explicit row, none on a whole-file row alone. Every new piece has a section or paragraph; every code-step commit changed physics.md; every SP7 assumption emitter is named in the Assumptions section |
| 10 | Full suite, ruff, no new dependency | pass | 2,271 of 2,271 passed at e8c2366: 2,217 fast in three chunks (738 + 581 + 898) and 54 slow in eight groups plus the two frozen-sets tests one per command (longest command 202 s); the junit files against the collected ids: none missing, extra, failed or skipped; nothing re-run. `ruff check .`: all checks passed; `ruff format --check .`: 133 files already formatted (ruff 0.16.9). pyproject.toml and uv.lock unchanged since a7c9f0a |
| 11 | Demo | pass | docs/demos/SP7/: 16 tracked files from 3a07f07, every command of section 9 with start and end times, the three fast-suite results in order; the README's 12 commits resolve and match. The gate's own comparer: run A 16,391 numeric leaves, C 2,161, B 14,967, 0 differing (only /git/hash and /timestamp_utc differ); the sweep's index files, baseline series and nine points 0 numeric difference. Every README number traced; 28 relative links resolve. Not re-checked: the two display defects the README discloses (they need a browser) |
| 12 | Close-out | pass (the parts before the close's documents) | Landing page, deck and PDF (24 pages), the gallery's SP7.1 entry with its MP4 and poster, and the manual present and carrying SP7's result. `uvx --with markdown==3.11 python site/build.py --out <scratch>`: 1,426 links, no broken link. origin/main = e8c2366 = HEAD; Pages run 42601122304 built e8c2366, build and deploy succeeded, the two runs before it too. SP3's section 6: "Checked at commit d03367b on 2026-11-05", no code or physics.md diff from d03367b to HEAD, 64 of 64 cited symbol lines at their line. The handoff with the marks C2 fills, its prompt equal to SP3's section 13 (79 identical lines), memory current |

Observations that fail no criterion: the central convergence check also leaves the sampling
step untightened (sp7_convergence.py line 305), which neither KI-089's text nor the note's
central bullets say, and its report file is not on disk, so its tightened x* and the stations
move are read from the note and the S7a log; tests/test_convergence_2d.py's docstring ("Every
other planar test uses the test budget") no longer holds since S4b's `lm_solves` fixture flies
the shipped budget, so TODO.md's closing words for KI-022 are out of date at HEAD (docstring
only; KI-022's own defects stay fixed); SP1's note line 37 is present tense inside its dated
record. The cold read logged these three as KI-104 (session log). The closing commit is
3a07f07, the last commit under src, tests, configs, experiments or results (`git log -1 --
src tests configs experiments results pyproject.toml uv.lock`); the last under results/ is
6940273 and the last under src/ is 9fe125c.

## 9. Demo script

Output goes to docs/demos/SP7/ (text captures with start and end times, a short README with the
commits, modelled on docs/demos/SP1/README.md). Names below are fixed by the approved design
(section 7); pages use hyphens, since `*_replay.html`, `*_scene.html` and `*_scene.mp4` are
ignored at any depth.

    uv run pytest -q -m "not slow"
    uv run pytest -q tests/test_structure.py
    uv run python -m launchsim run experiments/silo_structure_2d.yaml
    uv run python -m launchsim sweep experiments/silo_structure_2d.yaml
    uv run python -m launchsim run experiments/silo_structure_2d_readme.yaml
    uv run python -m launchsim run experiments/silo_drive_2d.yaml
    uv run python -m launchsim replay results/silo_structure_2d/<ts> --runs pad silo_cold_s1_st --out docs/demos/SP7/pad-vs-structural-offload.html
    uv run python -m launchsim scene results/silo_structure_2d/<ts> --runs pad silo_cold_s1_st --out docs/demos/SP7/pad-vs-structural-offload-scene-page.html
    uv run python -m launchsim replay results/silo_drive_2d/<ts> --runs silo_cold lm_cmd --out docs/demos/SP7/constant-accel-vs-linear-motor.html

Look at:

- the Structure subsection of silo_structure_2d's summary.md: the central case, the physics
  band, the outer envelope, the axes with their break-even values, the penalty rows beside, the
  element split, the plausibility table, the flags;
- the thickness-profile figure of the central case (pad envelope against the push);
- the exit-speed and depth sweeps with the structure charged;
- the linear-motor runs: force against speed (force limit, then power limit), the interface
  force, the release position and speed, the taper's cost;
- the findings note's headline sentence and its caveats.

The app (`launchsim app`) can show the same pair live; any launch made for the demo follows
D-SP2-37 (from a clean tree after the last code commit, its summary in its own commit, never
cited in a finding). The app's form itself is unchanged (D-SP7-08).

## 10. Risks and open questions

Answered in step 0 (2026-10-08): Q1 to Q7 by D-SP7-01 to D-SP7-07, every recommended option,
with the follow-ups D-SP7-09 to D-SP7-12 after the review of the draft. The open design points
below are settled by the approved design: option (i), placed in `vehicle_at` (D-SP7-20); the
structure file under configs/structures/ (D-SP7-21); the stroke and exit-speed series as
sweeps; the target-speed release on linear_motor only (design 4.7); the app's form unchanged
(D-SP7-08, B-016); the push metrics of a linear-motor run (design 4.6); KI-039 (D-SP7-23);
KI-030 (D-SP7-28); KI-036 and KI-038 in S3a; KI-032 stays later. The risks are the design's
section 8. The table below is the brief's, kept as the record.

**Questions SP7's Plan mode puts to the user** (recommendation first; give the ambitious
option fairly with its cost)

| # | Question | Recommendation | Why |
|---|---|---|---|
| Q1 | Structural model fidelity | B, first-order station sizing (section 5.3) | Testable closed forms and sourceable coefficients; A adds little to the penalty rows; C (FEM) needs your approval and its inputs are not public |
| Q2 | Size the structure for the offloaded stack actually flown, or for the full-load push | The flown stack, with the full-load sizing as a bound row | The flown stack is the least mass the offloaded vehicle needs; a vehicle that must also fly full loads needs the full-load structure, so both are shown |
| Q3 | How much spare margin does the existing stage 1 have over its pad envelope | None (the structure exactly meets the envelope), with a margin as a sensitivity | The real margins are not public; zero margin charges the most and does not favour the assist |
| Q4 | Drive scope | Linear motor and carriage mass in; modelled braking and the air column in but first to cut; the curved track and cable winch out (README Phase 3 remainder) | The first two set the felt g and exit speed that the structure depends on; braking and air move little of the answer; the ramp and cable belong to concept B. Ambitious option: take the curved track with its frictionless-arc test and the cable winch with its frequency test too, at the cost of a second session or a split phase |
| Q5 | Where the carriage load enters the vehicle | An aft ring at the stage base, with the thrust structure as the alternative row | It is the simplest load path to size; body supports fly and concentrate loads (README) |
| Q6 | Findings: update RQ1 or write a new note | A new note (for example RQ1-structural-2d.md) with a dated pointer section at the top of RQ1; RQ1's record kept | Keeps the pre-registered SP1 note intact and the new experiments with their own provenance |
| Q7 | Dynamic load factor at push start | Charge it from a stated force rise time and an assumed structural period, with the quasi-static value beside | A step load (the prescribed drive's infinite jerk) peaks at twice the static load on an undamped elastic structure; ignoring it would favour the assist |

**Risks**

| # | Risk | Resolution |
|---|---|---|
| R1 | The coefficients dominate the answer and the band is wider than the offload | Report it as the result: the model cannot decide, and which coefficient would decide it |
| R2 | A first-order model looks more certain than it is | Every element's assumptions in summary.md and the note; the penalty rows stay beside it; "first order, not a sized structure" in the caveats |
| R3 | The coupling breaks the solver's monotonicity | The solver's own `offload_nonmonotone` flag; the fixed point (option ii) as the fallback |
| R4 | New config fields change resolved dicts and break the digest pin | New fields on new models only, or left out of the dump when unset (section 5.10) |
| R5 | Linear-motor parameters chosen to flatter the assist | A selection rule stated before any run (section 5.7); no adjustment after |
| R6 | The existing envelope of the real vehicle is unknown | Q3; built from the pad run's own records; a margin sensitivity |
| R7 | Run time: a band of solves plus the stroke series plus the drive cases | Budget in Plan mode from SP1's measured times; run the commands in parallel as SP1 did |
| R8 | Scope creep toward FEM, bending or lateral loads | Out of scope (section 2); any expansion asked of the user first and logged |
| R9 | SP2 changes files this inventory names | Done: the re-check of 2026-10-07 at 705025f (section 6); the start checklist re-checks against the HEAD it finds |
| R10 | The calibration miss (+14.3%) | The bridge case on the README-loads fork with its own structure file |
| R11 | SP2's readers and eight test files (the six SP2 tests, tests/test_offload_pipeline.py 232 and tests/test_app_page.py 1937) pin the "nothing structural" wording (section 5.1), so a changed sentence breaks tests or, left alone, misstates a run with the structure charged | Reword at source in S3 (one caveat source, D-SP2-23) with the honesty review; update the pinned tests; regenerate the six gallery pages with the diff recorded, as SP2 step A1a did |

**Open design points for Plan mode (no user decision needed unless they change scope)**

- Option (i) or (ii) of section 5.5, after a monotonicity probe at a few x.
- The structure file's place and schema (section 5.4).
- Whether the stroke series is a sweep (`launchsim sweep`) or cases of the run command.
- The target-speed release: its event, and what happens to the unused stroke.
- Whether the app's form (SP2) gains the structural switch now or later (backlog): today
  it offers `stage1_dry_mass_added_t` only (appform.py 398-405) and a `constant_accel`
  push (104-105); a linear-motor launch from the form is the same question.
- What the push metrics (`net_accel_mps2`, `exit_speed_mps`; `PUSH_SETTING_METRICS`) and
  the replay and scene labels hold for a linear-motor run, whose exit speed is a result
  (section 5.7).
- KI-039 (added at SP2's close, D-SP2-41): the offload section's heading "Propellant
  saved at fixed payload" (summary.py `OFFLOAD_SECTION_NAME` 1668, `offload_section`
  2074) and its basis line (compare.py `OFFLOAD_COMPARISON_BASIS` 1639, also in
  metrics.json's `offload` record) also cover imposed (fixed) cases, which fly their own
  P*. Reword both in S3 with the honesty review and drop the app banner's disclaimer
  (`EXPLORATORY_IMPOSED_TEXT`, summary.py 710) once the section is right.
- KI-030's validators in S4 (section 2, item 9); KI-036, which falls to SP7 when S3
  edits replay.py; KI-032 if S4 touches the peak-power metric (section 6).

## 11. Session log

**2026-10-08 (session 1).**

- Start checklist (protocol section 3), run at 22c62e9:
  - The tree was clean; HEAD's subject is "Close SP2: trackers, handoff, next phase file"; the
    closing commit 3a1b243 is an ancestor; `git diff --stat 3a1b243 HEAD` touches CLAUDE.md,
    README.md, TODO.md, docs/ (18 files) and site/ (5 files) only.
  - Fast suite: 1678 passed, 41 deselected in 188.72 s. Ruff: all checks passed; 109 files
    already formatted.
  - Pins: the exact golden tier (LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1), the planar digest pin and the
    planar output capture: 123 passed in 35.9 s. Entry criteria 3 and 4:
    tests/test_silo_screening_record.py (the pad and silo_cold capacities within 0.002 kg) and
    tests/test_offload.py::test_gate_silo_offload_recorded_run_and_verification: 3 passed in
    103.7 s.
  - Entry criterion 5: SP1's run data on disk (results/silo_offload_2d/20261003T112934Z with 19
    run folders, 20261003T112949Z with 5 sweeps). Entry criterion 6: `git diff --stat 705025f
    HEAD -- src tests configs experiments pyproject.toml uv.lock site/build.py` is empty, so
    section 6 holds at HEAD; the surveys' corrections are in section 6's new block. Entry
    criterion 7: `gh` authenticated, Pages run 37732568686 green. Entry criterion 8: the app's
    basis files unchanged since b3150c1 (survey 04).
  - Open items owned by SP7: B-004, B-005, KI-030, KI-039. Falling to SP7 by their owner rules:
    KI-035 (S1), KI-036 and KI-038 (S3a), KI-021-KI-023 (S4). B-007 re-targeted in part.
- Step 0 (planning):
  - Nine read-only surveys by a workflow at 22c62e9 (45 min): code seams, config and KI-030,
    the offload pipeline, wording, the recorded loads, sources (two), closed forms with a
    labelled planning probe, process and budget. Saved as inputs/2026-10-08-SP7-survey/.
  - Q1 to Q7 and the app point put to the user while the surveys ran; every recommended option
    taken (D-SP7-01 to D-SP7-08).
  - Draft v1 of the design read by six independent adversarial reviewers (structures physics,
    numerics and code, honesty, compliance, delivery, experiment design): 5 blocker, 52 major
    and 55 minor findings. The blockers: v1's rise-time rule pinned the dynamic factor at
    1.03-1.10 by construction; the 2^k corner search was infeasible and mislabelled; a new field
    on `AssistEnergyBudget` would have broken the 1-D golden tier. Four findings changed an answer
    the user had given and were put to the user (D-SP7-09 to D-SP7-12; all recommended options).
    Version 2 folded in the rest; appendix A of the design gives every disposition.
  - The user approved version 2 (D-SP7-13 to D-SP7-35). Saved as inputs/2026-10-08-SP7-design.md
    and inputs/2026-10-08-SP7-review/ (draft v1 and the six reviews). One count in the approved
    text was corrected before the commit: the reviews' minor findings are 55, not 50 (the
    experiment-design review's minors are 10).
  - Bookkeeping for the start commit: the status in three places and the handoff line; D-SP7-01
    to D-SP7-35, B-016, B-007's re-target and the KI ownership notes in TODO.md; this file's
    sections 2, 3, 5, 6, 7, 8, 9, 10 and 12 brought to the approved design.
- Process note: the surveys and the review ran as workflows outside Plan mode (protocol section
  11); Plan mode was entered only to present the finished plan.
- Next: S0 (sources), with S1 (sizing primitives) in parallel.
- Step S1 (2026-10-08): structure.py's sizing primitives with closed-form tests, units, the
  SP-8007 constants, the golden-dump field-list test, the docstring check made strict, KI-035's
  split. Workflow: implementer; physics/numerics and compliance reviewers, three passes; two fix
  rounds. Two deviations recorded in section 12 (the ring's closed-ring moment, conservative;
  the plateau reference 29.84 m/s^2, review SP-8's 29.77 being an arithmetic slip). The
  independent gate failed G3 (its 1e-9 inverse tolerance, written by the orchestrator, was
  tighter than the design's 1e-12 m root tolerance allows below 2.55 mm walls; every wall
  carries its load) and G5 (one missing test-map row); the row and the bound's last digit
  (2.5534) were fixed and an independent re-gate passed both (5,200 random cases, worst excess
  0.997 of the documented bound). Fast suite 1727 passed, 42 deselected; ruff clean; exact
  golden tier, digest pin and output capture pass. Per-evaluation times: 1-2 us per primitive,
  28 us per monocoque solve, 17 us per 100-station increment. Commit a3bd183. Next: S0's gate
  (running), then S2.
- Step S0 (2026-10-08 to 2026-10-09): the source note docs/phases/inputs/2026-10-08-SP7-sources.md
  (1,520 lines; 27 physics coefficients, 8 design axes, the drive values). Workflow: writer;
  physics, honesty and compliance reviewers, three passes; two fix rounds; the gate failed G3
  (two range ends from quoted-only values). A third fix round (with majors; a deviation,
  section 12), a verification pass and a clean-up, then a fresh independent gate passed G1-G8.
  The note's section 13 sent fifteen corrections of the approved design: item 14 (the
  interstage's stage) was put to the user, who chose stage 1 (D-SP7-36); the rest were
  adopted (D-SP7-37), with k_ts's central taken per relation (0.2805). The search budget now
  stands at about 3,263 sizings (section 9.3), which needs about 0.18 s per sizing to fit S2's
  10 min gate; S2 times one sizing first. Commit 81e045d. Next: S2.
- Step S2 (2026-10-09; commit 45e39d4): the station model of both
  stages, the envelope, the flags, the plausibility rule, `StructureConfig` and the two
  structure files, the screened search with its polish and checks (D-SP7-38) and the frozen
  sets. Workflow: implementer; physics, compliance and honesty reviewers, two rounds; two fix
  rounds. Decisions made in the step: D-SP7-38 to D-SP7-40 (section 12, entries 11-13).
  - **Timing before the search** (source note 9.3; `sim.time_structure_sizing`, the median of
    20 central sizings with a fresh geometry and envelope after a warm-up, on the development
    machine before the frozen run): the gate's 22.1 ms at the headline and 39.9 ms at the step
    row, the fork's 22.7 and 40.1 ms. Planned: 6,198 sizings (the note's 3,263 plus the
    polish's bound of 2,935), so 6,198 x 39.9 ms = 247 s (the fork's 249 s) against the 600 s
    budget: no fallback. Then: searches A to C took 6,789 distinct sizings in 218 s for the
    gate (A 2,866, B 643, C 3,280) and 6,836 in 235 s for the fork (C 3,327); D 46 in 1.1 s;
    the slow reproduction test 251 s and 255 s, the pad flights 32 s of each.
  - Cross-file record: CLAUDE.md's layout line for constants.py ("Earth and physical
    constants") is S8's to update: constants.py now also holds SP1's recorded penalty rows
    (model results, pinned to tests/data/silo_offload_2d_record.json, D-SP7-30, by a fast
    test).

  **The sizing-only table** (S2's gate item; design 4.2.6). Every number is a sizing at the
  push of the search (SP1's headline offload, constant_accel 3 g0, 100 m, cold, the pad as
  flown), not a finding; every x* is a coupled-placement estimate on SP1's penalty curve
  (survey 08 section 8; stage 2 at w = 5.478), never a solved offload, and a no-offload end
  says so. The curve is concave, so an x* placed between its rows is biased against the
  assist and one beyond 8.1 t (extrapolated) for it. Gate unless marked; the fork has no
  penalty curve.

  | set or row (headline unless stated) | dm1 + dm2 [kg] | x* estimate [kg] (of 41,262.9) | fork dm1 + dm2 [kg] |
  |---|---|---|---|
  | central | 5,868.2 + 0 | 11,298 (27.4%) | 5,583.6 + 0 |
  | central, naive placement (dm at 41.26 t read off the curve; favours the assist) | 5,868.2 | 13,355 (32.4%) | |
  | physics_low_mass | 3,677.1 + 0 | 23,717 (57.5%) | 3,451.5 + 0 |
  | physics_low_mass x 0.7390 (the plausibility rule, D-SP7-40; fork x 0.7649) | 2,717.5 | 28,546 (69.2%) | 2,639.9 |
  | physics_high_mass | 18,603.8 + 0 | 0 (no offload; extrapolated) | 17,685.6 + 0 |
  | outer_low_mass (margin 0.25, no cap) | 2,186.2 + 0 | 31,113 (75.4%) | 2,033.6 + 0 |
  | outer_high_mass (margin 0, cap 4.0 g0; stage 2 sized) | 50,497.9 + 1,362.1 | 0 (no offload) | 48,201.8 + 1,138.5 |
  | physics sets at the step row (B; stage 2 sized) | 8,306.7 + 185.8; 36,128.7 + 668.2 | | 7,308.3 + 104.0; 34,020.0 + 409.5 |

  Central at the headline: n_q 4.0057 g0, DLF 1.1273, n_peak 4.3889 g0, F_peak 22.858 MN, the
  ramp's plateau cost 0.31%; the elements: the aft skirt 1,957.1 kg (ring + common Z, all 200
  stations), the ring 1,457.1 (bending), the RP-1 barrel 2,067.9 (ring + common Z), the
  common dome 267.6, the aft dome 116.7, the LOX barrel 0.7 (combined at 29 stations), the
  tube 1.2; stage 2 and the interstage not sized (n_peak U below MECO's 5.195 g0 U).

  Polish and checks (D-SP7-38; excess = how far a trial goes beyond the end, kg; fork in
  brackets): the polish moved only the physics high-mass end, +413.0 kg [+421.0] (the RP-1
  MEOP 3.31 to 2.62 bar, +132.0 [+153.2]; the LOX density 1,306.1 to 1,141.2 kg/m^3, +281.0
  [+267.8]), and the fork's outer high-mass end +2.2 kg (stage 2's LOX p_min fraction 0.93 to
  0.7975). One-coordinate excess: A low 11.8 [4.9] (ring_h_over_b 7.875), A high 0 [0], B low
  2.0 [0] (stage 2's LOX MEOP 2.965 bar), B high 0 [0], C low 1.4 [0], C high 8.0 [7.7] (stage
  2's RP-1 MEOP 1.585 bar). B's held check over the 22 stage-1 coefficients at the step row:
  low 223.2 [149.1] (the LOX density at 1,306.1; the low end overstated, against the assist),
  high 67.3 [43.2] (the RP-1 MEOP at 2.965 bar; the high end understated, for the assist).
  Scored on the charged dm1 + 5.478 dm2: B low 11.1 [0], B's held low 280.1 [181.0], held
  high 67.3 [43.2], C high 43.6 [42.0]. Samples' most extreme dm against the end: A 4,465
  against 3,677 and 14,866 against 18,604; C 2,723 against 2,186 and 41,610 against 51,860.

  Tornado (search A, the gate, the design axes central; dm at the range's ends [kg], x* each):

  | coefficient | swing [kg] | dm at the ends (x* estimate) |
  |---|---|---|
  | gerard_row (plate_limited) | 4,851.6 | 10,719.8 (0) |
  | aft_skirt_length_m 2.0 / 10.09 | 2,619.1 | 4,558.7 (18,795) / 7,177.8 (3,580) |
  | eta_weld 0.7 / 1.0 | 1,828.2 | 7,696.5 (0) / 5,868.2 |
  | ring_h_over_b 1.0 / 12.0 | 1,269.0 | 7,130.4 (4,049) / 5,861.4 (11,288) |
  | skirt_envelope_path (flight_thrust) | 325.1 | 5,543.1 (13,082) |
  | k_stiff 0.65 / 0.75 | 305.8 | 5,868.2 / 5,562.4 (12,945) |
  | stage 1 LOX MEOP 1.24 / 4.0 bar | 246.3 | 5,835.0 (11,669) / 6,081.3 (9,481) |
  | E 72.0 / 79.6 GPa | 237.4 | 5,995.0 (10,627) / 5,757.6 (11,880) |
  | stage 1 RP-1 MEOP 1.24 / 4.0 bar | 225.5 | 5,758.6 (11,917) / 5,984.1 (10,531) |
  | F_tu 520.0 / 558.5 MPa | 136.0 | 6,004.2 (10,130) / 5,868.2 |
  | the other 12 | 132.1 down to 0.3 each | (tube diameter, dome alloy, RP-1 density, dome a/b, RP-1 p_min fraction, t_min, ullage, wall density, LOX density 8.0, LOX p_min fraction, s_dg 0.7, nu 0.3) |

  Design-axis rows at central: margin 0.10 dm 5,555.7 (x* 13,133, 31.8%), 0.25 dm 5,105.5
  (15,585, 37.8%); cap 4.5 g0 (x* 10,374, 25.1%), 4.0 g0 (5,039, 12.2%); quasi_static dm
  5,261.4 (14,888, 36.1%); the step row dm 12,251.9 (no offload); the thrust-structure entry dm
  6,558.2 (6,276, 15.2%). Sizing-only lines (outside every band): FS_u 1.25 dm 5,447.1 (13,891,
  33.7%); k_stiff 0.85 5,399.7 (13,782, 33.4%); k_stiff 0.52 6,444.9 (7,898, 19.1%); Gerard
  ring_common_y 5,554.8 (12,985, 31.5%), ring_improved_z 5,409.3 (13,508, 32.7%),
  ring_improved_y 5,299.4 (14,136, 34.3%).

  Plausibility (central; D-SP7-33, D-SP7-40): M_model 10,621.8 kg [9,977.1] (the LOX barrel
  7,541.9, the RP-1 barrel 2,588.8, the domes 157.6, 175.8 and 157.6; 11,206.3 on the
  cylinder-equivalent lengths), R 6,038.3 kg [5,870.0] (per tank 7,151.7), the band
  4,226.8-7,849.9 kg, M/R 1.759 [1.700]: the low-mass end's factor 0.7390 [0.7649], the
  high-mass end unchanged; beside: Akin 4,903.0, the interstage relation 934.4, k_ts T_max
  2,307.6, stage 1 less its engines 17,970.0 kg.

  Release flag at the central headline (D-SP7-39; fired): the swing -4.389 g0 (the plateau's
  -4.006) against MECO's -5.195 g0; stage-1 LOX bottom -911.6 kPa gauge (-810.3 absolute), RP-1
  -282.8 (-181.5), MECO's (empty tanks) +132.4 and +162.7; stage-2 LOX -161.6 (-60.3) against
  MECO's (full) -231.7, stage-2 RP-1 +39.5 (+140.8) against +6.3; the common dome's reverse
  pressure 363.3 kPa (the floor) against MECO's 129.6; the upper stack's swing -5.99 MN
  against MECO's -7.10 MN. The payload-limit flag fires on the swing (below -2.0 g0).

  Search D, the break-even values (estimates; the other coefficients central; 50%: x_t
  20,631.5 kg at dm 4,440.4 kg, interpolated, biased against the assist; 0%: dm 8,488.6 kg,
  extrapolated, biased for it):

  | axis (range) | 50% of the headline | 0% (no offload) |
  |---|---|---|
  | nof_barrel (1.54-1.90) | not reached: below 50% at every admissible value (dm 5,923.9-6,227.3) | 4.128, outside |
  | nof_stiffened (1.45-1.90) | not reached, below (5,724.4-6,901.6) | 2.364, outside |
  | nof_dome (1.50-2.36) | not reached, below (6,055.7-6,243.4) | 10.69, outside |
  | nof_entry_ratio (1.05-1.47) | not reached, below (5,134.1-6,143.0) | 2.299, outside |
  | k_ts (0.197-0.628 kg/kN; thrust-structure entry) | 0.1178, outside (below the range) | 0.3476, in range |
  | rise time (0.1-1.0 s) | below throughout (10,235.6-5,870.7) | 0.1438 s, in range |
  | axial frequency (2-10 Hz) | below throughout (7,160.4-5,821.9) | above throughout (7,519.4-6,084.3) |
  | ring pads (4-8 in the file; D adds 3) | below throughout (12,550.0 at 3, 6,143.0 at 8) | between 4 (no offload) and 5 |


  Gate (independent, its own scripts on fresh flights of both committed pad baselines, P*
  equal to SP1's P_ref): G1-G8 pass (the pad's own cases give 0.0 kg for every element except
  the ring frame, which gets no envelope credit as new hardware; doubling the stations moves dm
  by at most 0.04 kg; the fast envelope equals a brute force to 1.5e-15; the files' values equal
  the note's; the slow reproduction 245 s per file; the central dm recomputed: 5,868.2 kg). Fast
  suite 1781 passed, 44 deselected; ruff clean; the exact golden tier, the digest pin, the output
  capture and the golden-dump field lists pass. D-SP7-40 (the plausibility rule's firing) was put
  to the user, who kept the rule as approved, both ends printed (D-SP7-41). Next: S3.
- Step S3 (2026-10-09 to 2026-10-11; commit 889f6ea): the structural sizing coupled into the
  offload solve (the transform in `OffloadProblem.vehicle_at`, the case field and the experiment
  block, the loader, the verification flying the restated dm with a modelled provenance, the
  memo keys, the run-level record keys, the pins). Workflow: implementer; numerics, compliance
  and honesty reviewers, three passes; two fix rounds; then a minors-only third round (10
  minors; a deviation, section 12 item 22). A weekly usage limit stopped the workflow after
  the implementer on 2026-10-09 (the three reviewers and the gate lost; nothing orphaned); it
  resumed from its journal on 2026-10-11 with the session model changed to Fable 5.1 (agents
  inherit the session model; no criterion depends on the model). Measured: SP1's headline with
  the structure off and the constant-2 t cross-check reproduce SP1's x* and verification P* to
  0.0 kg; the inner iteration contracts by 0.005 at central (0.050 on the outer high-mass set,
  10 sizings; cap 25, D-SP7-44); a transform call costs about 21 ms against 0.8 s per ascent
  evaluation; dm'(x) between -0.015 and -0.128 kg/kg, inside the hard bound -1/E. Decisions
  made in the step and reported here: D-SP7-42 to D-SP7-44; deviations 14-22. Gate
  (independent, own scripts): G1-G8 pass; full suite 1878 passed in 22.6 min with no spurious
  subprocess failures; after the minors round the standing gates re-run by the orchestrator:
  fast suite 1833 passed, 47 deselected; the golden tier, the golden-dump field lists, the
  digest pin and the output capture 126 passed; ruff clean; replay.html's sha256 unchanged.
  Next: S3b.
- Step S3b (2026-10-11; commit 216a79c): the reporting (the payload cases, the plausibility-scaled
  row, `structure_inputs`, the sweep and arm columns, the Structure subsection, the thickness
  figure, the post-hoc flight check). Workflow: implementer; numerics, compliance, honesty and
  visual reviewers, three passes; two fix rounds. The loop's third pass left six majors (the
  flight check flagging a payload case's own payload gain as the push's; a payload-only block
  passing validation and flying nothing; the payload table without its settings; a caption's
  wrong sizing payload; the flight check's element scope unstated; margin, cap and dynamic
  cases printed as band ends) and the first gate ended without a verdict (it launched the
  full suite in the background and ended its turn on a status line, which the workflow took
  as its result). A third fix round, two verification reviewers (six residuals, fixed), and a
  fresh independent gate run with every suite command in the foreground followed (deviation
  31). Gate 2: G1-G8 pass with its own numbers (the payload contraction recomputed to 1e-12;
  the plausibility factor from its own M_model / R; 297 printed numbers traced to record
  keys; an SP1-type sweep index byte-identical to the S3 commit's; the flight exceedance
  re-sized station by station to 1e-9 kg; the figures opened); fast suite 1848 passed, 47
  deselected; the slow tier 47 passed in 1,150.9 s (the suite 1895); ruff clean; the golden
  tier, the pins and the golden-dump field lists pass; replay.html's sha256 unchanged. One doc
  defect the gate found (physics.md's band fraction of the synthetic file) fixed by the
  orchestrator before the commit. Deviations 23-31. Next: S3a.
- Step S3a (2026-10-15; commit 0a16a89): the three-way structural wording at every source and
  run kind, a structure payload case as the offload block's fourth run kind, KI-039, KI-036,
  KI-038 (version). Workflow: implementer; honesty, compliance and numerics reviewers, three
  passes (3, 4 and 2 majors; 47 findings in all); three fix rounds (the third under
  deviation 31's rule) and a verification review whose four minors were fixed. Two
  interruptions: a usage limit stopped pass 2 and the gate, a network error the gate's
  retry; both resumed from the workflow journal. The gate failed G1 (the animate footnote
  gave no stage split, file or band and no deviation said so) and read G5 against the
  design's one-line expectation; a footnote fix (deviation 38), a review (one major, five
  minors, fixed) and an independent re-gate followed. Re-gate: G1' and G5' pass (84 no-model
  caveat lists and 56 rendered frames equal 77eb006's; every line inside the limit at four
  widths; the five replay pages byte-identical; the scene page in deviation 32's four
  regions); fast suite 1875 passed, 47 deselected; the readers' slow tests 7 passed; the
  first gate's slow tier 47 passed (3,424.9 s; suite 1,921); ruff clean; the golden tier,
  pins and golden-dump field lists pass; replay.html's sha256 unchanged. Deviations 32-34
  accepted by the session (reasons in section 12); 32 changes the literal reading of exit
  criterion 3's gallery clause and goes to the user at C2. Deviations 32-38. KI-036, KI-038
  and KI-039 closed; KI-040 opened (deviation 37's video fit). Next: checkpoint 1.
- Checkpoint 1 and step S6a (2026-10-15 to 2026-10-16; commit cbbd7bc, the pre-registration
  commit): files A and C, their listing and resolve tests, the pre-registration part 1
  (docs/phases/inputs/2026-10-15-SP7-preregistration.md). Checkpoint 1: every run of A (70)
  and C (4) resolves and passes `sim.check_resolved`; one structural case on the synthetic
  structure file took 185.2 s (92.6 s for the structural case; its x* 15,195.4 kg is a
  synthetic number, used only to measure the placement's error, -297 kg). Workflow:
  implementer; honesty, compliance and numerics reviewers, three passes (4, 3 and 2 majors);
  three fix rounds; a verification review (one major, fixed) and a clean-up; an independent
  gate. The freeze held: no agent ran or solved a case of A or C (the gate searched
  results/ and 611 scratch metrics.json files); only pad baselines were flown, every P*
  equal to SP1's record to 0.0 kg. Gate: G1-G6 pass (shared blocks byte-identical; every
  case's resolved settings listed; the frozen sets reproduce, 317.9 s and 298.7 s; the
  expected readings recomputed by the gate's own placement; the RP-1 pressure extra moves dm
  by -93.3 kg, not flown); G7 failed on its own list, which omitted docs/physics.md, the
  file holding the step's test-map rows (the orchestrator's error in the gate's wording;
  accepted, deviation 39). Fast suite 1881 passed, 47 deselected; ruff clean; the golden
  tier, pins and field lists pass; replay.html's sha256 unchanged. Put to the user at the
  gate and decided: both fork tests registered and quoted (D-SP7-45), the headline form's
  four amendments (D-SP7-46), exit criterion 3's gallery clause read as deviation 32's four
  regions (D-SP7-47). Estimates registered (none is a target): the headline about 11.1 t
  (26.9% of 41.26 t, "cancels most"), the physics band no offload to 28.5 t ("undecided"),
  sweep 1 no offload at 25 and 50 m. Runtime estimate: about 59 min at this machine's rate,
  56-80 min pessimistic, under D-SP1-17's 90 min. Deviations 39-41. Next: the in-progress
  handoff, then S7a from a clean commit.
- In-progress handoff at checkpoint 1 (2026-10-16; protocol section 10): SP2's handoff moved
  to docs/handoff/archive/2026-10-07-SP2.md, docs/handoff/NEXT_SESSION.md rewritten as an
  in-progress handoff, the Resume prompt added to section 13. S7a's three commands were
  started together from the clean commit 1b5f9d4, with plots: `run` A at
  2026-10-16T17:15:10Z (results/silo_structure_2d/20261016T171513Z), `sweep` A at
  17:15:19Z (results/silo_structure_2d/20261016T171522Z), `run` C at 17:15:26Z
  (results/silo_structure_2d_readme/20261016T171529Z; its summary.md written at 17:21:03Z,
  not yet checked). No suite, app or agent ran the code beside them; the handoff's edits are
  documents only, and nothing else is uncommitted apart from the S7a summaries under
  results/. Resume point: S7a [~]. Done inside it: the three commands started; run C
  finished. Not done: run A and sweep A (running when the handoff was written); the
  pre-registration's section 9 checks on all three directories; the convergence check of
  its section 1 (after the runs, never beside them); the frozen sets at the run's commit;
  the structural part of docs/findings/RQ1-structural-2d.md; the honesty review and the
  gate. The code writes FAILED.txt for any exception, Ctrl+C included (results_io.py,
  `write_failure_marker` under `except BaseException`), so its traceback decides. If a
  command was interrupted (FAILED.txt ending in `KeyboardInterrupt`, or neither summary.md
  nor FAILED.txt with no live process), its directory stays, the command is re-run from a
  clean commit that changes no code (pre-registration section 12) and the interruption is
  logged here. If a command raised (FAILED.txt with any other exception), nothing is re-run.
  It goes to the user first, because a fix changes code and needs a logged decision or a
  pre-registration amendment before any re-run (handoff section 6, item 5). The run's commit
  is 1b5f9d4. The convergence script gets its own commit under docs/findings/scripts/, and
  it runs, as do the frozen sets, only from a commit whose src/, configs/, experiments/,
  pyproject.toml, uv.lock and tests/ equal 1b5f9d4's (handoff section 6, item 3). First
  command for a new session: the process check of the handoff's section 6, item 1, before
  any suite. Next: S7a's checks and write-up, then S4.

**2026-10-19 (session 2, resuming SP7 at S7a).**

- Resume (protocol section 10, then section 3 without the status change): no launchsim or
  pytest process alive; HEAD ac5c6bd ("SP7 in progress: handoff at step S7a"); every [x]
  row's commit in `git log`; the tree clean apart from S7a work products that session 1
  left untracked after the handoff (results/silo_structure_2d/,
  results/silo_structure_2d_readme/, docs/findings/RQ1-structural-2d.md with its tables,
  ten figures and three scripts under docs/findings/scripts/). The three commands had
  finished on 2026-10-16 (summary.md written, no FAILED.txt): run A at 18:19:59Z (64.8
  min), sweep A at 17:48:15Z (32.9 min), run C at 17:21:03Z (5.6 min). After the handoff,
  session 1 had run the frozen-sets test at the run's code (both files pass, 317.5 s and
  290.0 s), run the convergence check from the then uncommitted script, and drafted the
  note, which reports one blocking check of pre-registration section 9 failing (the three
  no-offload sweep points carry no shortfall) and holds the S1 sentence and S2's 50 m
  clause.
- The three scripts committed (0a12c36, documents only; `git diff --quiet 1b5f9d4 HEAD --
  src configs experiments pyproject.toml uv.lock tests` exit 0), then the convergence check
  re-run from the committed script in the foreground, part by part (2026-10-19 06:34:53Z
  to 06:39:58Z, 277.5 s of parts; nothing else running): the same bits as the first run
  (shipped x* 11,420.246638573297 kg = run A's to 0.0 kg; tightened +0.0378 kg, 3.3e-6
  relative; dm with 400 stations +6.2e-6 kg): passes (deviation 42).
- The failing check put to the user; decided: fix the reporting, amend, re-run the sweep
  (D-SP7-48). Step S3c added (deviation 43). Workflow: implementer; numerics, compliance and
  honesty reviewers, three passes (15, 9 and 11 findings; 0, 2 and 0 majors); two fix rounds
  (19 fixed, 5 rejected with reasons: three are the manual row (KI-041), one the design's
  fixed wording, one pre-existing (KI-042)); an independent gate, every command in the
  foreground: step criterion, fast suite 1882 passed, 47 deselected (three chunks), ruff,
  the exact golden tier (121 passed), the planar digest pin and output capture, the
  golden-dump field lists, the frozen files and replay.html's sha256, physics.md's rows,
  the file list: all pass. Commit 1e4c732. The third pass's eleven minors, ten of them
  sentences that S3c made false or wraps, fixed after the gate in 77e1691 (deviation 44;
  98 fast tests of the touched files and the slow end-to-end sweep test, 505.5 s, pass);
  the eleventh (H3-02) went into the amendment. Amendment 1 committed (74eb3c8).
- Next: `sweep` A re-run from the clean tracker commit after 74eb3c8, alone, on a quiet
  machine; then the reproduction check of every pre-existing column, the note's update,
  the honesty review and S7a's gate.
- Step S7a closed (2026-10-19; commit 6fa2ff0, the findings note with the run summaries).
  After the re-run (17:23:21Z to 17:55:41Z, 32.3 min, exit 0; reproduction 657 cells, 0
  differ; shortfalls 60.2, 18.3 and 190.0 m/s; deviation 45 for its dirty flag), the scripts
  were fixed for review pass 1 (b82417b) and the section 9 checks script added (9b91473; all
  ten checks PASS). Workflow: four read-only reviewers (honesty, number tracer, pre-registration
  compliance, figures) in four passes (pass 1: 54 findings, 12 major; pass 2: 27, 1; pass 3:
  19, 2; verification pass 4: 16, 1), each pass's findings fixed by a note fixer (none
  rejected); the figures redrawn with the review's caveats (a5b21b8); an independent gate in
  the foreground: no bug_suspect; every pad at P_ref to 0.0 kg; every registered reproduction
  0.0 kg off and the nine uncharged sweep points equal to SP1's index at 12 digits; every
  structural verification within 1e-4 P_ref (at most +0.488 kg); xv_dry_mass_delta_kg = dm1 +
  dm2 to 7.3e-12 kg; the structure files' sha256 at every commit and in 74 records; Amendment
  1's reproduction by its own comparison; the frozen sets reproduce at HEAD (301.9 s and the
  fork's; the code differs from the run's only in reporting); the convergence numbers match
  report.json; no major open; the code paths equal 2b343d7's: PASS. The structural headline:
  11.42 t of stage-1 propellant (2.78% of stage 1, 27.7% of SP1's uncharged 41.26 t) with the
  central structure; "cancels most" fired as registered; the physics band no offload to
  28.57 t ("undecided"); the outer envelope no offload to 31.12 t; the lowest exit speed of
  sweep 1 that still offloads 76.71 m/s (100 m), the 25 and 50 m points 60.2 and 18.3 m/s
  short (the extra speed helped but did not pay for the structure). Deviations 45 and 46;
  KI-043 and KI-044 opened. Next: S4 (in progress in the worktree sp7-s4).
- Step S4 closed (2026-10-24; commit 25967be on branch sp7-s4, merged into main as 8c4b41a,
  a merge commit because main had moved on with S7a's documents; the branch touched no file
  S7a touched). Built in a git worktree outside the repository by two implementers (part A:
  KI-030's strict, finite numbers with the bounds T_IGN_LIMIT_S and EXIT_ALTITUDE_LIMIT_M,
  and the KI-021 to KI-023 test hygiene; part B: the linear motor). The workflow stopped
  twice at usage limits and resumed from its journal; the agents cut off re-ran on the
  current tree. Three reviewers (physics, compliance, honesty) in three passes (15, 9 and 6
  findings; 2, 0 and 0 majors), every finding fixed, none rejected. An independent gate,
  every command in the foreground: the step criterion item by item (139 linear-motor cases
  at 1e-9 against closed forms, limits at every step and sample at 1e-12, the energy
  identity cold, hot and ramped, the hot interface force for f_imp 0, 0.5 and 1, the
  refusals, the pending ignition in 1-D and planar, KI-030's sixteen inputs refused under
  the new source and accepted under 2b343d7's, 288 resolved digests of the nine shipped
  experiment files unchanged); fast suite 2057 passed (three chunks); ruff; the exact 1-D
  golden tier (121 passed); the planar digest pin and output capture; the golden-dump field
  lists; the frozen files and replay.html's sha256; physics.md's section and 44 test-map
  rows; the full suite 2104 passed (47 slow in 11 groups): all pass. After the merge the
  fast suite and ruff pass on main. KI-021, KI-022, KI-023 and KI-030 closed. The event set
  goes beyond design 4.6 (deviation 47, D-SP7-49); the force-law taper and power-cap order
  breaks the step's own criterion F sdot <= P_max in an edge the tests do not reach
  (deviation 48, D-SP7-50, KI-045; fixed in S4a). KI-045 to KI-052 opened from the fix
  rounds' candidates. Next: S4a.
- Step S4a closed (2026-10-25; commit 7cdc24a). First the force law's power cap moved onto the
  flown, tapered force (D-SP7-50, KI-045), with an arc-track test of the edge P_max/sdot < F_h
  against an independent quadrature; then the release at a target speed, KI-052's keys, the
  readers (replay, scene, the force- and power-against-speed figure, the conditional summary
  rows, KI-042's cells) and the app's listing. After a release below the mouth the vehicle
  flies the shaft in the open atmosphere and a fall back ends at the shaft floor, the parked
  carriage (D-SP7-51; deviation 50). Workflow: one implementer; physics, compliance, honesty
  and visual reviewers in four passes (50, 24, 15 and 17 findings; 10, 8, 2 and 3 majors),
  four fix rounds (3 rejected with reasons, the rest fixed); the independent gate after round
  4: the step criterion item by item, fast suite 2101, full suite 2150 (49 slow in 11
  groups), ruff, the exact 1-D golden tier, the planar pins, the golden-dump field lists, the
  frozen files and replay.html's sha256, the gallery's six pages byte-identical, the scratch
  linear-motor run's replay and scene pages against its metrics.json and the app on that
  scratch root answering 200: all pass. Round 4 was unreviewed, so the session added a
  focused fifth pass (physics, honesty, compliance: 14 findings, 3 majors, all wording of the
  soft-brake apex case), a fifth fix round and a re-gate (fast suite 2103, the exact golden
  tier and planar pins, the touched slow tests, 593 tests of the touched files with their slow
  cases, the gallery byte-identical): pass (deviation 49). KI-042, KI-045 and KI-052 closed;
  KI-053 to KI-066 opened from the fix rounds' candidates. Next: S4b.
- Step S4b closed (2026-10-25; commit b0fcc31). Each sizing of a linear-motor case flies the push
  alone on the vehicle carrying dm and reads the load cases at the exact maxima of its dense
  output; the dynamic factor is the larger of the rise formula with the drive's t_r and the
  phase-free single-mode bound of the flown history (D-SP7-52, from review pass 1's major M1:
  the formula alone ran up to 3.9% (n) and 5.3% (F_int) below a single mode on a hot step at
  clamp release or an early peak); the release at the flown release instant; the fixed point
  from dm = 0 (6 sizings and a contraction of 0.0104 at the synthetic case's x*); exact track
  peaks on linear-motor runs (KI-046; the sampled rows were 1.98e-5 low). Workflow: one
  implementer; physics, compliance and honesty reviewers in four passes (27, 21, 12 and 9
  findings; 6, 5, 2 and 0 majors), four fix rounds, none rejected; the gate (its first agent
  cut by a network error, re-run from the journal): the step criterion item by item, fast
  suite 2155, full suite 2206 (51 slow in 13 groups, the frozen sets one per command), ruff,
  the exact 1-D golden tier, the planar pins, the golden-dump field lists, the frozen files
  and replay.html's sha256, the constant-2 t and structure-off pins: all pass. Two results
  against the design's expectation, recorded (deviation 51, D-SP7-53): dm'(x) is about -4e-4
  kg/kg on the cold force-law case (design 4.4 expected dm' > 0), above the -1/(2 E) floor
  with no `offload_nonmonotone`; the brief's 50 m synthetic push ends no_offload, so the slow
  solve and its convergence use the same drive over 100 m (x* 13,160.9 kg, synthetic, not a
  finding; 3.4e-7 under the tightened budget). KI-046 closed; KI-067 to KI-075 opened. Next:
  S5.
- Step S5 closed (2026-10-25; commit 460c4d6). The sealed shaft: the trapped column at the ICAO
  pressure of the track start acting on the carriage, F_int lower by (m_v/M) F_p under the force
  law, the work W_piston_J as a model state and `losses.PistonWork` outside
  `AssistEnergyBudget`, conditional metrics, rows and lines. Workflow: one implementer;
  physics, compliance and honesty reviewers in three passes (28, 14 and 8 findings; 8, 1 and 0
  majors), three fix rounds (1 rejected with a reason: two pre-existing physics.md lines); the
  gate: the step criterion item by item (the work closed form and the identity at 1e-9, F_p <=
  p_0 A, F_int sample by sample, the refusals, the flown structural push: 5,812 kg sealed
  against 5,903 kg vented on the synthetic file, not a finding), fast suite 2205, full suite
  2256, ruff, the exact 1-D golden tier, the planar pins, the golden-dump field lists, the
  frozen files and replay.html's sha256, vented and constant_accel digests pinned before the
  change and byte-identical after: all pass. The review found the design's 3.7 m bore cannot
  pass the 5.2 m fairing (D-SP7-54: file B's bore 5.24 m) and that two run-level lines and the
  readers still call a sealed shaft vented: a step S5a is added for that wording before S6b
  (deviation 52). KI-076 to KI-080 opened. Next: S5a, checkpoint 2, S6b.
- Step S5a closed (2026-11-03; commit 2bd40bd). The sealed shaft's wording: a sealed planar
  run's own track-push line (`sim.PLANAR_SEALED_TRACK_PUSH_ASSUMPTION`: the column's net
  force on the carriage, the shaft open at its top, no drag, q or Mach on the vehicle during
  the push, the bore checked against the diameter of the run's A_ref only), the early-release
  line's sealed clauses, and the readers (replay's `shaft_kind`, the drag, close-up and drive
  clauses with the column's peak force and work; the scene's display-only list and a sealed
  run's note against the 7 m shaft drawn; the app's `pair_shafts`). Workflow: one
  implementer; physics, compliance, honesty and visual reviewers in three passes (31, 9 and 9
  findings; 4, 0 and 0 majors), three fix rounds (2 rejected with reasons: a finding that asked
  for no change, and the configs/display note the brief kept out); the gate: the run-level
  lines on a scratch experiment (pad, vented, sealed, sealed with a target-speed release) read
  against metrics.json and the same experiment under HEAD's code (identical metrics, events
  and series; summary.md differs only in the sealed lines and the vented line's run tag), the
  vented and constant_accel digests under HEAD and the tree, the readers' pages, the app on
  the scratch root (17 routes 200, no 500), the gallery's six pages byte-identical, fast suite
  2210, ruff, the exact 1-D golden tier, the planar pins and capture, the golden-dump field
  lists, the frozen files and replay.html's sha256, the touched readers' slow tests: all pass.
  The full slow tier was not run (the brief named the readers' slow tests; 17 of 53 slow
  tests ran). A temp-folder cleanup deleted the step's brief and pass 1-2 reports while the
  workflow was paused at a usage limit (deviation 53). KI-077 and KI-079 closed; KI-081 to
  KI-087 opened. Next: checkpoint 2, S6b.
- In-progress handoff at checkpoint 2 (2026-11-03; protocol section 10): the checkpoint-1
  handoff moved to docs/handoff/archive/2026-10-16-SP7-checkpoint-1.md, a new
  docs/handoff/NEXT_SESSION.md written as an in-progress handoff, and the Resume prompt of
  section 13 replaced by checkpoint 2's (checkpoint 1's text stays in the archived
  handoff's section 10). The tree is clean apart from these documents; nothing runs.
  Resume point: S6b [ ], not started; its brief and the step-loop script are working
  notes outside the repository (handoff section 4). First command: the fast suite.
  Next: S6b, S7b, S7c, S8, C1, C2.
- Step S6b closed (2026-11-03; registration commit 331891d). File B
  (experiments/silo_drive_2d.yaml): silo_cold verbatim from file A, the nine linear-motor
  variants of design 4.10 with every rule value computed from the sources' closed forms by
  docs/findings/scripts/sp7_drive_rules.py (21 validity checks), 20 stage-1 offload cases and
  the stage-1 pad control; no sweep, payload case or sensitivity arm (design 4.10 names
  none). Part 2 of the pre-registration is the separate file
  docs/phases/inputs/2026-11-03-SP7-preregistration-part2.md, with a pointer paragraph in part
  1's header. Two tests hold the YAML to the closed forms (1e-12, worst 3.7e-14) and to design
  4.10's table. Workflow: one implementer; physics, compliance and honesty reviewers in four
  passes (35, 17, 11 and 8 findings; 6, 1, 1 and 0 majors), four fix rounds (none rejected);
  the independent gate: its own 60-digit recomputation of every rule value (within 2.4e-15)
  and the 20 validity conditions, checks (1)-(4) by its own push-only flights, section 7's
  expected values by its own implementation of the method, a mutation check of the rules test
  (50 of 50 caught), fast suite 2214, ruff, the exact 1-D golden tier, the planar pins and
  capture, the golden-dump field lists, the frozen files and replay.html's sha256: all pass.
  The gate's verdict was not passed on one item: the full-load mass M was a choice the brief
  had not made (compliance:M2). The orchestrator closed it as the gate prescribed, logging
  D-SP7-55 (M at full precision) and citing it in the addendum's section 6, item 2, with no
  value moved, and accepted the addendum's reading that KI-067 does not reach file B's hot
  starts (neither holds on the clamp; the gate's flights give F_rest = m_v g_eff exactly)
  (deviation 54). D-SP7-54's 5.24 m bore was registered as session-made; no answer from the
  user had arrived. No run, sweep or solve of file B was made before the commit. KI-088
  opened. Next: S7b (`run` B, alone, from this commit).
- Step S7b closed (2026-11-03; note commit e5f64b3, scripts b291518). `run` B
  (results/silo_drive_2d/20261103T231946Z) ran alone from 642e11e (no code change against
  331891d), 2026-11-03T23:19:44Z to 2026-11-04T00:01:31Z, exit 0, 388 files, no FAILED.txt,
  dirty false; other projects' processes (a Blender MCP server, a VideoSearchDB server and
  two celery workers) were running on the machine and are recorded in the note. Part 1
  (b291518, documents only): docs/findings/scripts/sp7_s7b_checks.py (the 11 blocking checks of
  part 2's section 9, E1 and E2, the fixed sentences) and sp7_lm_convergence.py (the
  registered linear-motor convergence check in seven parts); physics, compliance and honesty
  reviewers in three passes (32, 15 and 10 findings; no major), three fix rounds, the
  independent gate passed. The convergence check then ran alone from b291518
  (2026-11-04T02:57:04Z to 03:03:48Z, parts 33-104 s): lm_fixed_s1_st's x* moved +0.0274 kg
  (2.4e-6 relative, against 0.1%), the shipped chain equal to run B's x*; it leaves
  TRACK_PEAK_SCAN_POINTS and sample_dt_s untightened (KI-089). The blocking checks: 11 of 11
  pass (silo_cold_s1_st 0.0 kg from run A's and from SP1's; lm_cmd's uncharged x* +0.0014 kg
  from SP1's; no `bug_suspect`; every verification within 1e-4 P_ref); E1 and E2 met. Part 2
  (the note, docs/findings/RQ1-structural-2d.md, status preliminary): the drive-cases table
  (silo_cold and the nine linear-motor variants, uncharged and central), the 25 fixed
  sentences filled by the checks script, the departures from section 7's estimates stated
  plainly (lm_fixed_hot 7.35 t against 3.75 t estimated, +96%), What goes against and Limits
  extended, the headline paragraph kept; three figures by
  docs/findings/scripts/sp7_drive_figures.py; the committed copies of the checks output; a
  dated pointer in RQ1-fuel-offload-2d.md; README results and the findings index; physics.md's
  S7b research notes (the measured dm' chord signs). Physics, compliance, honesty and visual
  reviewers in three passes (46, 25 and 12 findings; 5, 0 and 0 majors), three fix rounds;
  the independent gate: its own trace scripts (759 and 231 checks, 0 failed; every one of the
  1,801 numbers in the added lines resolved), the 25 sentences filled independently, the
  figures spot-checked and looked at, the site built with no broken link, fast suite 2214,
  ruff, the exact 1-D golden tier, the planar pins and capture, the golden-dump field lists,
  the frozen files and replay.html's sha256, run B's directory byte-identical: all pass.
  Result: every central case cancels most of its offload, 2.48 t (lm_cmd_taper) to 18.27 t
  (lm_cmd_hot, a hot start the unmodelled exhaust favours); on the same 100 m silo the two
  drives that exit faster than silo_cold keep less (lm_fixed_hot 4.07 t less, lm_fixed 82 kg
  less); the stop taper costs 8.94 t. A wall-clock test failed in 2 of 3 [p-z] chunk runs and
  passed alone 9 of 9 (KI-090). KI-089 and KI-090 opened. Next: S7c.
- Step S7c closed (2026-11-04; commit 9fe125c). SP1's present-tense claim "no structural
  model exists" is retired at every source: replay's penalty sentence ends with
  `replay.PENALTY_MODEL_POINTER` ("SP7's first-order structural model is reported
  separately (docs/findings/RQ1-structural-2d.md)"), dropped only beside a modelled run (S3a
  fix round 2's directory rule and `summary.offload_charges_modelled` withdrawn: deviation
  56); app.py's SP1 headline caveat "Structure." quotes SP7's 11.42 t of 41.26 t with its
  caveats (six phrases a test checks against both notes; the gate's mutation probe caught 8
  of 8); the compare.py docstring; site/build.py's editorial addition; the landing page
  (131 and, on review findings, 191, 292, 316, 353-356 and 369) and the gallery index (256,
  360, 410, 601); the manual (03, 05b, 07b, 09, 12); physics.md's "Program-level sentences
  (SP7 step S7c)" paragraph and rows. A new scan test keeps the phrase out of src/,
  the templates, site/build.py, the landing page, the gallery pages and the manual. `git grep
  -n "no structural model exists"` now hits only dated or archived records
  (docs/phases/inputs/, SP1's dated note line 37, which the brief fixed) and quotations (the
  handoff's and this file's statements of the grep, physics.md's record of the retirement,
  the scan test's literal). Workflow: one implementer; physics, compliance, honesty and
  visual reviewers in three passes (27, 10 and 6 findings; 6, 1 and 0 majors), three fix
  rounds; the independent gate: its own scan for the phrase and its variants over 355
  tracked files, the six gallery pages regenerated byte-identical (the built copies of
  pad-vs-silo-offload and offload-vs-paired-pad differ from HEAD's build only in the
  editorial addition), the site build (1,326 links, none broken), the app on a scratch
  results root showing the new caveat, fast suite 2,217, full suite 2,270 (the slow tier in
  eight commands, the frozen sets one per command), ruff, the exact 1-D golden tier, the
  planar pins and capture, the golden-dump field lists, replay.html's sha256: all pass.
  Left to S8 (its public-face prose): the deck and its PDF (lines 1063, 1180, 1195, 1202),
  README's caveat list and status line, the landing page's run-true lines and roadmap row,
  the FAQ's "So what has been found?", the findings index line 24, manual 09's "(Phase 3)"
  pointer. TODO.md's B-005 row and its hot-start finding line, which S7b made stale, are
  updated in this tracker commit. Next: S8.
- The demo runs (2026-11-04; committed 6940273): the phase file's section 9 commands from
  6cf0fd2, clean tree. Every leaf of metrics.json equals the recorded directory's (run A
  16,391 numeric leaves, run C 2,161, run B 14,967; only /git/hash and /timestamp_utc
  differ), and the sweep's two index files equal the re-run's in every cell. Its fast suite
  exited 1 (1 failed, 2,216 passed), then 2 failed on a re-run, both in test_video.py, with
  other projects' pytest runs on the machine. Those processes are not this session's to stop,
  so the tier was made to hold (S7d).
- Step S7d closed (2026-11-04; commit cd14968; tests and docs/physics.md rows only). Scan of
  every wall-clock dependency in tests/ (65 rows: 34 safe, 26 races, 4 slow tier, 1 not
  clocks). ROOMY limits are now serving's default and ArmedLimits shortens only the timeout
  under test once its setup has finished; process_alive uses OpenProcess; the app-server
  races use events or counts; KI-090's ordering is replaced by a scripted clock giving exactly
  (2.0, 4.0) and the sizing's own stage2_sized record; child-import guards 600 s. The appform
  guard is split as KI-035 split the scene's, with a new scan test over every module of the
  package (D-SP7-56). Two tests that did not catch what their docstrings said, at HEAD too,
  were strengthened. Mutations: 95 by the gate's own plugin, 92 caught; the three survivors
  are one equivalent mutant and two disclosed gaps (KI-093). Every loosened wall-clock bound
  is listed with what it no longer catches (the step's report, section 7). Workflow: one
  implementer; physics, compliance and honesty reviewers in six passes (36, 19, 14, 12, 14
  and 13 findings; 7, 3, 2, 1, 6 and 3 majors), six fix rounds; the independent gate: under 32
  burners and a disk writer test_video.py 10 of 10 and the sizing test 10 of 10, the fast
  suite 2,217 in three chunks twice, beside eight VideoSearchDB pytest runs on the first
  pass; without the burner 2,217 twice; slow tier 54 of 54 in nine commands, none re-run; full
  suite 2,271; ruff, the exact 1-D golden tier, the planar pins and capture, the golden-dump
  field lists, replay.html's sha256; src/, configs/, experiments/, results/, site/ and
  docs/manual/ untouched. What the gate does not show: it ran 32 busy processes, not 64, so a
  1-in-50 failure of fix round 6's writer fix at 64 would not appear, and the frozen sets were
  not run under the burner. A real src defect surfaced and stays open: KI-092 (a body arriving
  after a 404 on /cancel or /finish draws a reset); the tests no longer send the page's `{}` on
  that path, so the fast tier does not cover it until it is fixed. KI-090 and KI-091 closed;
  KI-092 and KI-093 opened. Next: S8.
- Step S8 closed (2026-11-05; commit 3a07f07). docs/demos/SP7/: README, 8 console captures with
  the three fast-suite results in order (exit 1 at 6cf0fd2, exit 1 on its re-run, exit 0 at
  cf6d1db after S7d), the comparisons and three pages from the demo directories. Gallery
  entry SP7.1 (pad beside silo_cold_s1_st, replay and scene pages, MP4 and poster) from run
  A's recorded directory. KI-082: the shaft note reworded; five replay pages byte-identical,
  the gallery's scene page grows 90 bytes, one data leaf on line 316. The deck: four new
  slides 16-19, the status slide, S7c's lines; PDF re-exported at 24 pages. The landing page's
  answer box now leads with 11.42 t, SP1's 41.26 t beside it. The manual: every SP7 setting
  and output, KI-041, KI-083, KI-084. CLAUDE.md's layout and commands, the protocol's caveat
  line branched, README's status and roadmap. Workflow: one implementer; physics, compliance,
  honesty and visual reviewers in four passes (55, 26, 19 and 15 findings; 16, 2, 3 and 0
  majors), four fix rounds; the independent gate: site build 1,426 links, none broken; 8
  gallery and 3 demo pages regenerated byte for byte; 812 public and 154 demo tokens traced,
  253 claims recomputed from the directories' own files; the deck PDF's 24 pages (16-20 read
  at 1600 px, 8 on contact sheets, 11 by text only); landing, gallery, replay and scene in a
  browser at 1280 and 375 px, light and dark; the manual's new statements against the code;
  fast suite 2,217; ruff; the exact 1-D golden tier; the planar pins and capture; the
  golden-dump field lists; replay.html's sha256. Not shown by that gate: the full suite (C2's),
  the MP4 played, playback of the replay and scene pages watched. Reviewers' note on "the same
  rocket" (landing, deck, README, beside a structural run carrying 6.31 t the pad does not):
  the sentences describe the baseline and stay true of it; the landing's one sentence about the
  rocket after release goes to C1, the deck's stay, slide 13 saying two different vehicles.
  KI-041, KI-082, KI-083, KI-084 closed; KI-094 to KI-099 opened. Next: C1.
- Step C1, the documents of the close (2026-11-05 to 2026-11-08; commit ead6e38; documents only, no
  file under src/, tests/, configs/, experiments/ or results/). SP3's file: the fact-check made
  at 6cf0fd2 (52 edits, 2 outside the file, 6 questions) re-validated at d03367b. Its 157 line
  claims all hold, since no file under src/ changed after 9fe125c; 19 changes in 13 edits (the
  commit and date of each statement; three physics.md headings; S7d's counts and KI-090; the
  four demo summaries committed at 6940273; S7d and S8 done; a caveat clause in the prompt), each
  fixed in the edit; X2's commit likewise. All applied, each old text checked to occur exactly
  once; the six questions added to that file's section 10 with a recommendation first (the
  fact-check had one and part of another; the rest are drafted and say so), and a seventh, Q7,
  from the physics review's pass 2 (deviation 59). The board, TODO.md
  (B-004 and B-005 stay in progress until the exit gate, B-017 opened for the interface
  hardware B-004 leaves unsized, B-007, B-015 and B-016 updated, D-SP7-56 flagged, KI-051
  reworded, KI-100, KI-101 and KI-102 opened; M20 stays in progress), the handoff archived as
  docs/handoff/archive/2026-11-03-SP7-in-progress.md and the new one written with marks for
  what C2 produces, the memory. Every KI exit criterion 8 names is closed with its evidence in
  TODO.md (KI-021, KI-022, KI-023, KI-030, KI-035, KI-036, KI-038, KI-039). The wording S8's
  reviews left, each traced to the recorded metrics.json (the design axes and the outer
  envelope to structure.py, the experiment files and S2's log entry) with no number changed:
  the payload-limit flag's scope, which rows fly which design axes, what the outer envelope
  moves and a start mass in the note, the settling clause and lm_cmd_hot's clause in README,
  the index's 18.27 t, the landing page's one sentence (deviation 59). Reviews and gate:
  physics, compliance and honesty reviewers in six passes (39, 16, 17, 12, 13 and 9 findings;
  5, 3, 2, 1, 2 and 1 majors), six fix rounds; from pass 2 on, the physics reviews flew a
  review's replica of SP3's 3-D model and re-read S1.4's tolerance lines (Q7, the five changed
  gates, deviation 59); the independent gate on 2026-11-08: item 7 traced by its own script
  (15 of 15), the SP3 file's added lines against HEAD (every commit, 101 symbol-line pairs),
  the 52 edits and 2 outside each applied or changed with a reason, the prompt byte-identical
  in both places, 51 handoff commits resolving, the site built with 1,426 links and none
  broken, fast suite 2,217 in three chunks, ruff, the exact 1-D golden tier, the planar pins,
  the golden-dump field lists, replay.html's sha256. Pass 6's one major was checked by the
  gate against its probes' logs, since no later pass ran. While the handoff holds one of C2's
  marks, SP7 is not closed.
  Next: C2.
- Step C2, first run (2026-11-08 to 2026-11-09, at a0e351e; no file changed). Criteria 1
  to 6 and 8 to 12 passed (12 as far as it can before the closing documents): the full
  suite 2,271 of 2,271 (2,217 fast in three chunks, 54 slow in ten groups), ruff, no new
  dependency, the frozen sets recomputed (largest extremality excess 223.198 kg), the
  exact 1-D golden tier and the planar pins, the app's slow launch at 41,262.908 kg.
  Criterion 7 failed on reporting only: the note's two sweep sections gave no peak
  electrical power, and sweep 2's gave no DLF; every number it checked held (299 checks).
  The closing documents and the cold read did not run. The user decided to add the two
  columns from the record and run the gate again in full (D-SP7-57).
- Step C1a closed (2026-11-09; commit 185e35a). The findings note's sweep tables gain a peak
  electrical power column for the full-load point runs: n/a, since a constant_accel run
  writes none, with the recorded mechanical peak over the point's drive efficiency (0.5,
  from each resolved_config.yaml) in brackets, derived, and the assumption stated that the
  efficiency the electricity is charged at holds at the power peak; sweep 2 gains its DLF,
  1.1273 at every point, from the re-run's sweep_index.csv. A dated line in the note; no
  number changed. Workflow: one implementer; physics, compliance and honesty reviewers in
  three passes (8, 3 and 1 findings; no major), three fix rounds; the independent gate:
  every added cell recomputed from the record, a number-token diff with no token lost or
  changed, the site built with 1,426 links and none broken, every table rendering evenly,
  fast suite 2,217 in three chunks, ruff, the exact 1-D golden tier, the planar pins, the
  golden-dump field lists, replay.html's sha256. KI-103 opened. Next: C2's second run.
- Step C2, second run (2026-11-09, at e8c2366; the gate wrote nothing in the repository or
  under results/). Every criterion re-run from scratch, no verdict of the first run reused:
  all 12 pass (section 8, "Exit criteria results"). Full suite 2,271 of 2,271 (2,217 fast in
  three chunks, 54 slow in ten commands, the frozen sets one per command; none failed,
  skipped or re-run); ruff check and format --check clean (133 files); no new dependency
  since a7c9f0a. Criterion 7 now holds: 378 printed values against the record, 0
  mismatches, every named column present. The frozen sets recomputed (largest extremality
  excess 223.198 kg); the exact 1-D golden tier and the planar pins 284 passed, 0 skipped;
  the app's slow launch at 41,262.908 kg (+0.000037 kg). Observations that fail no
  criterion: the central convergence check leaves the sampling step untightened and its
  report file is not on disk; tests/test_convergence_2d.py's docstring is out of date since
  S4b's `lm_solves` fixture; SP1's note line 37 is present tense inside its dated record
  (section 8). The closing commit is 3a07f07, found with `git log -1 -- src tests configs
  experiments results pyproject.toml uv.lock` (the last under results/ is 6940273, an
  ancestor; the last under src/ 9fe125c; the five commits after 3a07f07 change documents
  only). The close's documents (the brief's "After the gate"): the handoff's marks filled
  (the verdict, the closing commit, the twelve criteria, the suite and ruff counts); this
  file (status, the C2 row, section 8's results, this entry, deviation 61); the board
  (SP7's row closed); TODO.md (M20 done, SP3 the current phase, B-004 and B-005 closed
  2026-11-09, the priorities); CLAUDE.md's status and docs/demos/ lines; memory; and the
  public status texts that said SP7 was not closed, each to closed or done with the date,
  no number changed: README.md's status, roadmap and layout lines, docs/manual/README.md,
  the landing page's SP7 row and label (and SP3's row to "Next", as SP7's was at SP2's
  close), the deck's badge, date, roadmap entries and Phase 3 card. The deck PDF re-printed
  by headless Edge from PowerShell against the built site on 127.0.0.1 (24 pages, 1280 x 720
  px, 1,292,063 bytes); its text differs from HEAD's only on pages 1 and 20, both looked at,
  with the other 22 pages on a contact sheet; the landing page's status table looked at in
  both themes. Site built (1,426 links, none broken); tests/test_caveat_wording.py and
  tests/test_site_build.py 54 passed; `git grep` for the not-closed phrases finds nothing
  that speaks of SP7 now outside dated or archived records.
- The cold read (2026-11-09; a second agent, from docs/handoff/NEXT_SESSION.md, reading only
  what it names): every check the brief names passes (paths, commit hashes, test counts,
  results directories, memory against the board, the prompt identical in the handoff and
  SP3's section 13). Three minor completeness points, none touching a number, fixed: the
  handoff's section 7 now runs to KI-104 (it had left KI-103 out); the gate's three
  observations are logged as KI-104, with a dated note on KI-022's entry, and the handoff
  says where they are; the memory note says so and no longer reads as listing every open
  SP7 KI. The cold read ran three times, each by a fresh agent. The second found one
  completeness point: the handoff's section 2 left out D-SP7-57; fixed by a sentence there
  naming it, and section 4's header redated "Status on 2026-11-09" (no row changed). The
  third found every check the brief names passing and one record gap, this entry naming
  only the first read; fixed here by the orchestrator, with D-SP7-57 marked as the
  recommended option in the handoff and TODO.md (the question put to the user offered it
  as recommended). No number, status or path changed in any of the three.
- Phase closed 2026-11-09. Next: SP3 (D-SP1-18, D-SP2-40), from docs/handoff/NEXT_SESSION.md.

## 12. Deviations from the plan

Step 0 (2026-10-08): what the approved design changes against this brief. The user approved
them with the design (D-SP7-01 to D-SP7-35); the full list is the design's section 6.1.

1. **Scope added**: stage-2 and interstage sizing where the push exceeds MECO (D-SP7-11); a von
   Mises combined mode, the LOX transfer tube's hoop and a ring frame in closed form instead of a
   per-load coefficient (D-SP7-14, D-SP7-17); uncertainty in three layers instead of three
   coefficient sets (D-SP7-18); the exit-speed sweep, the constant_accel hot starts and an
   envelope-cap row; the linear motor's acceleration law and stop taper (D-SP7-24); payload cases
   as a new record kind; the thickness and force-against-speed figures; a synthetic structure
   file and tests/data/silo_offload_2d_record.json; KI-035, KI-036, KI-038 and KI-021-KI-023 taken
   by their owner rules.
2. **Scope reduced**: braking as closed-form functions, not a modelled phase (D-SP7-12; B-007
   keeps the phase); a release ramp-down only as one flown variant (D-SP7-10); the brief's
   propagated one-at-a-time coefficient solves replaced by a sizing-only tornado with estimated
   x* (D-SP7-18).
3. **Step table**: S3 split into S3, S3b and S3a; S4 into S4, S4a and S4b; S6 and S7 into S6a/S7a
   (the structural files, before the drive) and S6b/S7b (the drive file); S7c (program-level
   wording) and S8 (the public face) added before the close; the close in two parts (C1, C2);
   two checkpoints as in-progress handoff points (D-SP7-29; the delivery review).
4. **Exit criteria**: twelve instead of ten, with criterion 3's headline tolerance at 0.002 kg
   instead of about 3.8 kg (section 8, "Changes against the brief's ten").
5. **Coupling**: the transform lives in `OffloadProblem.vehicle_at`, not in a factory wrapper
   (a wrapper alone left the verification without dm; survey 03).
6. **Dynamic factor** (D-SP7-09, D-SP7-16): the assumed rise time is ranged and independent of the
   stack frequency, and for constant_accel the ramp's plateau cost is charged, against the brief's
   single stated rise time.

Step S1 (2026-10-08): two physics changes against the approved design and its review numbers,
found in S1's reviews (PHYS-S1-02, PHYS2-03, S1-COMP2-02); docs/physics.md, "Structural sizing
of the push load (first order)", derives both, and the review records stay unedited.

7. **Ring frame moment** (design 4.2.3, D-SP7-17): `ring_frame_mass_kg` sizes the ring for the
   bending moment at the pads of a closed thin ring on N_p equally spaced supports,
   M = q r^2 (1 - alpha cot alpha) with alpha = pi/N_p, not the straight continuous beam's
   interior-span moment q l^2/12 (l = 2 pi r/N_p) that the design states. It tends to q l^2/12
   as N_p grows and is larger by 1.0% at 8 pads, 1.9% at 6, 4.4% at 4 and 8.2% at 3 (the ring's
   mass by 0.7%, 1.3%, 2.9% and 5.4%): conservative, it charges the assist more mass. The ring's
   mass is ideal; the caller applies the barrels' NOF (S2).
8. **Ramped plateau reference** (design 4.2.1, review SP-8): at L = 100 m, v_e = 76.707 m/s
   (3 g0 over 100 m) and t_r = 1.061 s the closed form and an integration of the ramp's
   kinematics both give a' = 29.84 m/s^2 (1.42% above v_e^2/(2 L) = 29.42), so the felt load
   factor is 4.043 g0, not review SP-8's 29.77 m/s^2 and 4.032 g0 (an arithmetic slip: 29.77
   corresponds to t_r of about 0.97 s). S2 consumes 29.84 m/s^2 and 4.043 g0.

Step S0 (2026-10-09):

9. **A third fix round with majors** (protocol: up to two fix rounds): the third review pass of
   the source note found six majors (the ring's torsion and shear, the stiffened factor's low
   end, the completeness of section 1.4, the ring pad count, stage 2's tank order, the
   interstage rule) and the gate failed G3. A document is cheap to fix, so a third round, a
   verification pass and a clean-up ran, and a fresh independent gate passed. No coefficient was
   changed to move the result: every change is listed in the note's two revision sections with
   its direction on dm.
10. **The note's corrections of the design** (its section 13): adopted as D-SP7-37, with the
    interstage charged to stage 1 by the user's answer D-SP7-36 (amending D-SP7-11's wording).

Step S2 (2026-10-09), from its first review round (session-made; reported to the user at S2's
gate):

11. **The search's polish and one-coordinate check** (D-SP7-38): source note 9.3's method
    gains a polish after step 3 (each varied coefficient alone over its scan points or
    choices, until a pass moves nothing) and a one-coordinate extremality check recorded
    beside the seeded samples; every move and every check's numbers go into the frozen sets.
    The note's step 3 read each monotone direction at the base only, so the first frozen
    high-mass ends were not one-coordinate extremes (the gate's by 413 kg). The polish only
    moves an end outward; the budget estimate adds its bound (2,935 sizings, 6,198 planned).
    What remains, recorded: the one-coordinate excess at most 11.8 kg at the headline; B's
    held check at the step row puts the physics low-mass set 223.2 kg above the step row's
    one-coordinate low (the fork's 149.1; the low end overstated, against the assist) and
    the high-mass set 67.3 kg below its high (the fork's 43.2; the high end understated, for
    the assist); scored on the charged dm1 + 5.478 dm2 instead of the search's unweighted sum,
    280.1 and 67.3 kg, and C's high end 43.6 kg (8.0 recorded).
12. **The release flag** (D-SP7-39, amending design 4.2.2's "n_rel"): the release swings from
    the release's peak, the ramp's undamped residual included, as the peak is sized; heads to
    the dome's crown; the dome's reverse pressure judged against MECO's; MECO's pressures
    gauge. Round 2: the dome's LOX side floored at zero absolute (a separated column); the
    stage-2 tanks' numbers recorded beside, since the same treatment separates stage 2's LOX
    column on the pad's own MECO, so the separation is not specific to the push and S3a's and
    S6a's caveat wording must say so. Flags only.
13. **The plausibility rule fires** (D-SP7-40): at central the gate's M_model is 1.759 R (the
    fork's 1.700 R), so the band's low-mass end is cut by 26.1% (the fork's by 23.5%), driven by
    the LOX barrel's MECO buckling envelope carrying `nof_barrel`; the rule is applied
    unchanged and the question goes to the user before S6a.

Step S3 (2026-10-11), from its first review round (session-made; to report at S3's gate):

14. **The cross-check's verification criterion** (D-SP7-42, amending the step's item 6(b)):
    SP1's own +2 t verification ended 0.00299 kg above P_ref, so "P* equals P_ref within
    0.002 kg" is unattainable by the run the cross-check reproduces; the pin compares x* and
    the verification's P* with SP1's recorded values within 0.002 kg (measured 0.0 kg, the
    same bits) and holds P* to P_ref within the flag tolerance only. Criterion 3 (x*) is
    unchanged.
15. **The recorded structure path** (design 4.3 and 4.4 write `configs/structures/<file>`):
    the provenance, the run-level `structure_file` and resolved_config.yaml's `structure.file`
    quote the file by `cli.recorded_config_path`, its path relative to the repository root
    whenever it lies under the repository (a rooted path or one found next to the experiment
    included), as named only for a file outside it, so no machine-specific path enters a
    record or a tracked summary (honesty finding H-S3-04).
16. **What S3 leaves self-contradictory until S3a** (honesty finding H-S3-02): a structural
    run written at S3's commit would carry SP1's caveat "no structural mass is charged for
    the push load" and a 0 in the case table's "assumed stage-1 dry mass added" beside its
    own `structure_charged: true`; no experiment under experiments/ has a structure block and
    none is written before S3a rewords those lines (stated in physics.md's S3 section). The
    run's own assumptions list is not on this inventory any more: round 2 (honesty finding
    H-S3-P2-02) replaced, on a structural run only, SP1's offload sentence "every dry mass
    (tank structure included) ... unchanged" by `sim.OFFLOAD_STRUCTURE_ASSUMPTIONS`, whose
    dry-mass clause excepts the modelled increment (S3a still owns the final wording).
17. **A caveat for the dry-mass arm, carried to S3a, S3b and S6a** (numerics finding N5):
    under a `vehicle.stages.stage1.dry_mass_t` arm the geometry is built from the perturbed
    variant, but the stations are loaded from the structure file's mass breakdown, so the
    perturbed dry mass reaches the sizing only through the push's interface force and the
    perturbed pad's envelope, never through the stage-1 station loads (measured on the
    synthetic file at the headline, envelope held: +10% dry mass gives +10.4 kg of dm,
    +0.20%); the sentence goes beside the arms wherever they are reported.
18. **Records at this step**: a structural sensitivity arm's and sweep point's structure keys
    exist on the in-memory case record only (a test spies on them); the arm record in
    metrics.json and the sweep columns carry none until S3b's columns, so on disk such a run
    is marked only by its case name (numerics N1, compliance S3-R1-03, honesty H-S3-01).

Step S3 (2026-10-11), from its second review round (session-made; to report at S3's gate):

19. **The overrides are recorded and named at source** (D-SP7-43, amending design 4.4's
    record list; honesty finding H-S3-P2-01): a case's design-axis overrides changed the
    sizing but reached disk nowhere (only the memo key saw them), so an axis row's restated
    dry mass would have carried `source: ..., set central` for a mass the central set did not
    produce. `structure_overrides` is now a run-level key, and the provenance (the dry mass's
    `source`, the assumption line) appends `, overrides <path> <value>[, ...]`.
20. **The fixed point's cap raised from 10 to 25** (D-SP7-44, amending design 4.4; numerics
    finding N-S3-R2-01): sizing only on the synthetic pad and on the pad flown afresh, the
    gate file's outer_high_mass set needs exactly 10 sizings at every offload (contraction
    0.050), so the design's cap left the flag no margin; the cap flag now records the cap and
    the measured contraction. The same set's dm'(x) = -0.128 kg/kg at x = 0 (flattening to
    -0.121 at 60 t) lies below the fast test's
    half-bound -1/(2 E) (which is asserted on the synthetic file only) and above -1/E; a fast
    test now holds the four frozen sets to the hard bound (physics.md, Contraction and
    Monotonicity, carry the per-set sizings, contractions and slopes).

Step S3 (2026-10-11), from its third review round (session-made; to report at S3's gate):

21. **Step item 7's before/after identity test** (honesty finding H-S3-P3-03): the item asked
    for a fast test of the no-structure-block byte identity of a written run before and after
    the change. The fast test implemented,
    `tests/test_structure_pipeline.py::test_a_written_run_without_a_structure_block_has_no_structure_key`,
    compares the current code with and without a structure loader (the same code on both
    sides; its docstring and the physics.md test-map row say so). The before/after comparison
    against 15b4e6e was done as a manual check by the implementer and by the gate:
    `launchsim run experiments/silo_offload_2d_readme.yaml --no-plots` at 15b4e6e and in the S3
    working tree gave identical metrics.json, resolved_config.yaml and every CSV, and a
    summary.md identical apart from its three title, timestamp and git lines.

22. **A third fix round, minors only** (protocol: up to two fix rounds; the design's section 5
    allows a third for minors, logged): the third review pass left ten minors (docstring numbers,
    physics.md's over-precise slope statement, the structure flags not promoted to the run's
    `flags`, an unrefused `stage2_offload_t` with `structure`, the provenance string without
    the case's sizing, dynamic, entry, margin and cap, a documented but forbidden paired pad);
    one fixer applied all ten after the independent gate had passed, and the orchestrator
    re-ran the standing gates before the commit. No number of the model changed.

Step S3b (2026-10-11), from its first review round (session-made; to report at S3b's gate):

23. **The tornado and break-even values are not in the record** (compliance finding
    S3B-C1-04; design 4.4's "Records" lists "the tornado, the axes' break-even values" among
    `structure_inputs`): the structure file freezes the four sets of searches A to C and
    their checks only; its `sets.method` says search D is not frozen there, and it holds no
    tornado table (S2's sizing-only tornado and break-even estimates live in this file's
    step S2 session log). `structure_inputs` records `tornado` and `break_even` as null
    with `tornado_note` (`STRUCTURE_SETS_NOT_IN_FILE`) saying so, rather than quoting a
    number from outside the file. Adding them to the frozen file is a change to
    configs/structures, which D-SP7-31 governs before S6a.
24. **The flight check evaluates the flight as the envelope evaluated the pad** (numerics
    finding N-S3b-R1-02; design 4.2 says only "against the same envelope"): the recorded
    run's stage-1 rows have their felt n capped at the case's envelope cap, as the pad's
    were when the envelope was built (stage-2 rows never capped, as on the pad), and the
    flight is evaluated unfactored (as the push is sized) against the envelope at the
    case's margin. Without the cap treatment the pre-registered `_st_cap45` row would have
    reported the pad's own unthrottled loads above 4.5 g0 (736 kg on the synthetic pad; 0 kg
    capped) as the push's; with the margin treatment a margin row's check fires only above
    the margin's headroom, which the row label, the flag line and physics.md now say. The
    check covers the tank elements with a station envelope (`FLIGHT_CHECK_ELEMENTS`: the two
    barrels, the three domes and the tube of stage 1, and of stage 2 when the push sized
    it); the aft skirt and the load ring are left out, against the design's "any
    exceedance": the skirt's flight load is the thrust path, which the pad's own flight
    carries to the engines' inertia on the pad and on the assisted run alike, and its
    envelope path is the modelling choice of D-SP7-17, so a flight exceedance there would
    charge the assist for a pad load; the ring is new hardware sized to the push alone. From
    the second review round (numerics N-S3b-R2-01): under a plate-limited stiffened row (the
    frozen file's physics_high_mass and outer_high_mass sets) the flight's barrel is anchored
    at the pad envelope's N_env, as the push sizing is, not at the flight's own load as the
    reduction anchors the pad envelope itself, which under-reported the exceedance by ~40 %
    on the synthetic high-mass set (94.5 against 159.5 kg at +5 % n); the exceedance is the
    unscaled sizing beside a plausibility-scaled row's scaled dm, and the flag's values name
    the dm's factor (`sim.FLIGHT_DM_FACTOR_KEY`).
25. **The band lines' applicability is printed, not computed** (honesty finding H-S3B-04;
    design 4.2.6: other pushes get central solves, their band ends "sizing-only estimates
    labelled 'the headline's sets'"): the frozen file records the push the sets were found
    at in its `sets.method` prose only, so a per-case comparison of the case's push with the
    search's cannot be made from the file without structured fields (configs/structures,
    D-SP7-31). The Structure subsection prints the method verbatim (where the sets were
    found) and an unconditional applicability line (`STRUCTURE_SETS_APPLICABILITY`) on every
    run; a structured push record in the file is for S6a to decide with D-SP7-31.

Step S3b (2026-10-11), from its second review round (session-made; to report at S3b's gate):

26. **Three sweep columns beyond the step's list** (compliance finding S3B-C2-03; the step's
    scope item 4 lists fifteen columns): `OFFLOAD_STRUCTURE_SWEEP_COLUMNS` carries eighteen,
    adding `structure_plausibility_scaled` and `structure_overrides` after the fifteen and,
    from the third review round (honesty H-S3B-P3-09), `structure_plausibility_ratio`. A
    sweep point writes no case record, so without them a point's dm would be on disk with
    neither the plausibility factor's application nor the overridden coefficients that sized
    it (D-SP7-43's intent: the coefficients that sized dm are on disk, not only in the memo
    key), and a sweep of a central case would carry no trace of the rule's state (M/R 1.76
    on the gate file): the factor column is empty off the two physics sets, as the summary
    prints "n/a (not a band end)", and the ratio column carries M_model / R on every point.
    Appended, so the fifteen keep their names and places. The sweep point's
    resolved_config.yaml carries the structure file only when a structural case was solved
    at that point (the run path's rule; compliance S3B-C2-01), not for every point of an
    experiment with a block as the step's item 4 words it.
27. **A payload case whose P_2* search fails writes nothing** (honesty finding H-S3B-P2-01):
    the first implementation wrote the failed search's run under the case's name, listed its
    figure and printed the flag as not fired. The case now ends with the search's status,
    `run` null, nothing written and no figure (the offload cases' rule for a search_failed
    solve), its dm_1 and structure keys kept on the record, and the payload table prints the
    status of both passes and n/a cells that say the search failed.

Step S3b (2026-10-11), from its third review round (session-made; to report at S3b's gate):

28. **The post-hoc flight check is not run on a structure payload case** (numerics finding
    N-S3b-R3-01; the step's item 7 and design 4.2 name the recorded structural run of the
    solve at P_ref, which the first implementation extended to the payload cases): a payload
    case's recorded run flies its own P_2* while the envelope is the pad's at P_ref, so the
    check measured the payload gain P_2* - P_ref, not the push: on SP1's experiment with the
    synthetic file the pad itself flown at the silo's P* (27,553 kg) against its own P_ref
    envelope needs 7.65 kg, the silo at that payload 7.97 kg, the push's share about 0.3 kg
    under the 1 kg threshold, so the flag fired on every payload gain above roughly +0.2 t.
    Comparing against the pad's own flight at P_2* would cost a further pad flight per case,
    so the payload cases are marked not applicable instead (`flight_check` on the record,
    the run's assumption line, the payload table, `STRUCTURE_PAYLOAD_FLIGHT_CHECK_NA`), with
    `structure_flight_exceedance_kg` null and no flight flag; the offload cases, which fly
    P_ref, keep the check. Every printed flight-check mass now states the element scope
    (deviation 24's tank elements only; honesty H-S3B-P3-03: in short in the case table's
    row label, which visual V7 keeps under 160 characters, in full in the note under the
    table and in the flag line) and the flag line says "stage 2 not checked" rather than
    "0 kg" when stage 2 was not sized (H-S3B-P3-08).
29. **Two refusals the first implementation lacked** (compliance S3B-C3-01, numerics
    N-S3b-R3-02): a structure block with payload cases and no `offload` block was accepted
    and its cases silently never flew (the payload form runs inside the offload pass); it is
    refused when the experiment validates. A block whose reference pad lights stage 1 at or
    after its hold-down release never holds down under thrust above its weight: with a step
    startup it flies no HOLD phase and `structure.pad_load_set` raised only after the
    nominal runs had flown (FAILED.txt); with the shipped 2 s ramp it holds through the
    liftoff extension at TWR < 1 (lit at 0 s: 1.5 s, 4 HOLD rows, measured in the third
    review's follow-up), whose HOLD rows carry the weight alone, so the skirt's hold-down
    envelope would lack the restrained-thrust case. The preflight `sim.check_resolved`
    refuses both before any run directory exists (`structure_block_needs_hold`): a
    modelling choice of the structural reference, stricter than the pass's own requirement
    of one HOLD row. The refusal's first wording claimed "no HOLD phase" for the ramp case
    too (false: the extension's rows are HOLD rows); the follow-up made the message, the
    docstrings, physics.md and the test state the real reason and how the pad lights.
30. **The layer labels follow D-SP7-18 and design 4.2.6 literally** (honesty H-S3B-P3-04;
    the first implementation treated only the overrides as layer 2): a case that moves a
    margin above 0, an envelope cap, the dynamic mode or any override is a design-axis row
    (layer 2), named with what it moves; a case that moves only the entry path or the sizing
    basis is "a row, not a band end"; only cases at the headline settings (flown, rise_time,
    aft_ring, margin 0, no cap, no overrides) on the physics or outer sets are band ends
    (an outer set's own margin and cap never count), and the central layer-1 label applies
    only to the central set at the headline settings; the band lines, a layer-2 line and a
    settings-rows line name every case accordingly. The payload table gained the case's
    settings rows (H-S3B-P3-01) and its heading names, per payload case, the full_load row
    of the same variant and settings; the figure's caption names the sizing payload P_1*
    (H-S3B-P3-02), the dashed envelope's margin and cap (H-S3B-P3-12), and its labels are
    placed by an overlap test with leader lines where an inset is crowded (visual V1 to V6).

31. **A third fix round with majors, and a gate without a verdict** (process; protocol: up to
    two fix rounds): S3b's third review pass still carried six majors, which the loop does not
    fix by design, and its gate agent ended its turn while its background full suite was still
    running, so the workflow recorded a status line as the verdict. An extra workflow ran one
    fixer over every pass-3 finding, two verification reviewers, a clean-up of their six
    residuals, and a fresh independent gate instructed to run every suite command in the
    foreground in chunks under ten minutes. For later steps: a gate must never end its turn
    on a running command, and a step whose third pass still has majors gets this extra round
    before its gate. No number of the model changed in the round.

Step S3a (2026-10-12), from its review rounds (session-made; to report at S3a's gate):

32. **The gallery's scene page differs from HEAD in four regions, not one line** (honesty
    H-S3a-P3-07, compliance S3A-CMP3-02; the S3a row's gate and design 4.5 expect the
    KI-038 version line alone): `pad-vs-silo-offload-scene.html`, regenerated with its
    recorded command, differs from 77eb006 in (1) the CSP script hash (the template's
    script changed), (2) the data block's `"version":"0.1.0"` (KI-038; no other data key
    changes), (3) the run selector's `ROLE_GROUPS` gaining `["offload", "structure payload
    case", "Structure payload cases"]` (fix round 1, H-S3a-01: a structure payload case's
    run is the offload block's fourth kind, so it needs a group of its own rather than
    "Other run folders") and (4) the Data line ending ", drawn by launch-assist-sim " +
    DATA.version (KI-038). The five replay pages regenerate byte for byte, every fresh
    render equals the working-tree file, and the site build is clean (1,313 links, none
    broken, no fix-table warning). `site/examples/index.html` records the re-render and
    points here. The gate is read as: the scene page differs only in these four regions.
33. **The exploratory banner's penalty branch is reworded** (fix round 1, H-S3a-05; step
    item 1 says the assumed-penalty branch keeps today's text): the bare "no structural
    mass for the push" was false beside a penalty row, so a banner whose offload record
    holds one reads "no structural mass for the push except the assumed stage-1 dry mass
    of the penalty row ... (an assumption, not a sized structure)", an app launch whose
    form adds a stage-1 dry mass included (`summary.exploratory_push_caveat`).
34. **The penalty sentence's program-level clause is dropped where a modelled mass is
    charged** (fix rounds 1 and 2, H-S3a-02 and H-S3a-P2-03; the step's scope leaves the
    program-level claims to S7c): `replay.penalty_structure_sentence`'s closing "; no
    structural model exists" is dropped beside a modelled run and in any directory whose
    offload record charges one anywhere (`summary.offload_charges_modelled`), since the
    next sentence, or the block caveat printed beside it on the scene page and in the
    app's panel, names the model. A directory without a structural record keeps SP2's
    text word for word, and the clause itself stays S7c's to reword.
35. **KI-036 reaches beyond replay.py's git string** (fix rounds 1 and 2, H-S3a-08 and
    N2-04; the step names replay.py 1819-1820): `summary.tree_state` reads any
    non-boolean dirty flag as unknown, never by its truth value, and `scene.git_record`
    writes dirty None for a no-git hash, which changes SP2's pinned assert at
    tests/test_scene.py 1222: a directory written outside a repository now reads "state
    unknown" on the scene page.
36. **Files outside the step's file list** (compliance S3A-CMP3-03): `run_data.py` (the
    fourth offload role `OFFLOAD_STRUCTURE_PAYLOAD` and its note; fix round 1),
    `results_io.py` (`offload_block_drives`, fix round 2; `offload_uncharged_cases`, fix
    round 3, S3A-NUM-03), `structure.py` (`SEARCH_HEADLINE` and `SEARCH_STEP`, the names
    the readers quote the headline polish by), `templates/app.html` (the selector group,
    fix round 1; the fit check under the server's footer, fix round 3),
    `summary.py`'s `sweep_structure_lines` (fix round 2, H-S3a-P2-07: a sweep point writes
    no case record, so the sweep summary words its structural cases) and
    `tests/test_app_page.py` (fix round 3, S3A-CMP3-06).
37. **The video footer's structural line goes unwrapped and the fit check draws under the
    server's footer** (numerics S3A-NUM-01, fix round 3): `app.video_footer` hands
    plots.animation_caveats' structural line over in one piece (the scene canvas wraps
    every footer line at the frame's width, so a line pre-wrapped at 1280 px cost a
    canvas line at each break); the results panel carries the same lines for the pair it
    describes (`video_footer`, `app.panel_video_footer`, a new panel key), and the app
    page's fit check (`videoFit`, `panelFooter`) draws its test frame under them, where it
    used the payload's shorter frame caveat. Measured in the browser pane on a scratch
    copy of the gallery directory whose two cases were given SP7 headline-like records
    (physics_low_mass, scaled x0.739, the release flag fired with D-SP7-39's pressures,
    payload_limit fired, the band record): a pad beside one modelled run fits 1280 x 720;
    two modelled runs, each with its full frame note (1,276 characters), do not (the
    footer took 250 px at fix round 3, 264 px with the pre-wrapped line) and fit
    1920 x 1080. Re-measured after the S3a gate fix and its review (R-G1-06), in headless
    Edge on the same probe copy and the current tree: the pair's footer takes 264 px at
    1280 x 720 with the current footer and with fix round 3's alike (the 14 px come from
    the scene page's changes after fix round 3, not from the footer), 292 px when one
    run's record gives a 312.4 kg stage-2 share; the pad pair still fits 1280 x 720 and
    the two-run pair 1920 x 1080 (at 960 x 540 both pairs are refused, as with fix round
    3's footer; the pad pair's footer takes 236 px there, 222 px with fix round 3's). The
    app now refuses 1280 x 720 for that pair before Save is offered ("choose a wider frame")
    instead of on the first frame. Shortening a frame's per-run note (its band clause is
    the block's, repeated per run) would change the scene payload's keys and the gallery
    page again; it is not done in S3a and is an open item for the tracker.
38. **The `animate` footnote points to the summary for the structure file and the band**
    (S3a gate, G1; the step's three-way wording names the stages, file and band for every
    per-run reader; reworded after the gate fix's review, R-G1-01 to R-G1-05):
    `plots.animation_caveats`, the only caveat on a `launchsim animate` frame, states each
    modelled run's mass, by stage when its record's stage-2 share is above zero
    ("8,900.1 kg (stage 1) and 200.2 kg (stage 2) of modelled structural mass" on the
    tests' synthetic record, to 0.1 kg as the replay caveat prints it, so a share under
    0.5 kg never reads "0 kg (stage 2)": R-G1-05; the total alone otherwise), its set,
    the plausibility scaling and the fired flags, and ends its structural line, once,
    with "modelled mass by stage: the caveats of summary.md's offload section; structure
    file and x* at the physics band's ends: its Structure subsection"
    (`STRUCTURE_FOOTNOTE_POINTER`). The offload section's caveats give every structural
    case's and structure payload case's mass by stage; the Structure subsection's
    payload-cases table gives only a payload case's dm_0 and dm_1 totals (R-G1-03). The
    Structure subsection names the structure file and gives x*, the tonnes of offload of
    the experiment's cases at the physics band's ends ("not flown" at an end no case
    ran): a different quantity from the band's sizing-only dm ends at the structure
    file's headline push (3,677 and 18,604 kg for the gate structure file), which no
    summary.md prints and which the replay caveat and the scene frame's per-run structure
    note quote with their scope sentence (R-G1-02). The frame leaves the file's path and
    those dm ends off by a choice about vertical space, not width (R-G1-01): the path
    fits a footnote line (it ends 427.5 px into the 1,260.8 px of a 1280 px frame's line,
    162.7 into 472.8 at 480 px), but the path and the dm ends with a shortened scope
    sentence take one or two footnote lines more than the pointer on the tests'
    selections at 480 and 1280 px (two or three with the pointer kept), and each line
    past `FOOTNOTE_BASE_LINES` moves the panels' bottom up one line. The app's video
    footer (`app.video_footer`, deviation 37) is these lines, unwrapped, with the pointer
    and without the file or the dm ends; an app video frame carries the full sentence
    only through the scene page's per-run structure note, which scene.html's
    `frameFooterLines` draws under the video footer (R-G1-04). physics.md's footnote
    paragraph ("Wording the structure (SP7 step S3a)") and the docstrings say the same.

Checkpoint 1 and step S6a (2026-10-16):

39. **docs/physics.md in the pre-registration commit** (S6a gate G7): the step's file list
    (design 5: experiments/, docs/phases/inputs/, tests/test_config_planar.py) and the gate's
    G7 wording left out docs/physics.md, which the standing gate requires to hold the step's
    test-map rows; the commit carries its shipped-experiments table rows and two test-map
    rows, documentation only (checked by the gate against the tests and files). Accepted by
    the session at the gate. The same commit also rewords two sentences that list the
    shipped planar experiments so that they name the two new files (15 lines in all, `git
    show --stat cbbd7bc`; added at the handoff's cold read, 2026-10-16).
40. **Cases beyond design 4.10's lists** (pre-registration section 6, items 2, 4, 5 and 11):
    the plausibility-scaled twin of the low-mass end (silo_cold_s1_st_phys_lo_scaled,
    D-SP7-33 and D-SP7-41 make it the band's low end); silo_cold_200m's pair (sweep 2's base);
    two payload cases for the rows expected to end no_offload (outer high-mass, step), so a
    no_offload end carries its payload deficit as D-SP7-32 asks; the 4.0 g0 envelope-cap row
    (design 4.2.6 names both caps); and the uncharged case solved at every sweep point beside
    the central one. Each was added at a review, its estimate known and disclosed; the
    runtime stays under D-SP1-17's 90 min.
41. **The timing case measures the placement's error** (pre-registration section 2(d);
    beyond step S6a's item 4, which asked for its wall time only): the synthetic-file case's
    solved x* (15,195.4 kg) against the coupled placement's 14,898.0 kg (-297 kg, 2.0%) is
    quoted as the method's measured error on a synthetic file, labelled as such; S3's slow
    pin computes the same case on every slow run. Kept by the gate.

42. **The convergence check first ran before its script was committed** (pre-registration
    section 1: "a committed script"): session 1 wrote docs/findings/scripts/sp7_convergence.py
    at S7a and ran it from the working tree at ac5c6bd (2026-10-16, 18:32:41Z to 18:40:13Z)
    before committing it. Session 2 committed the three scripts (0a12c36, documents only;
    the code paths equal 1b5f9d4's) and re-ran the check from the committed script
    (2026-10-19, 06:34:53Z to 06:39:58Z): every number the same to the bit. The note quotes
    the committed run. Accepted by the session.
43. **Step S3c added, and sweep A re-run on code that differs from run A's** (pre-registration
    section 9, last bullet; section 12's "a later clean commit that changes no code"): the
    three no-offload sweep points carried no shortfall, a reporting defect section 9 says to
    fix first. The fix (one appended column, the no-offload lines) is code, so the sweep's
    re-run starts from a commit whose src/ differs from 1b5f9d4's in results_io.py and
    summary.py (reporting) only. The user decided it (D-SP7-48) and Amendment 1 (74eb3c8)
    registers it; the reproduction of every pre-existing sweep column against the first
    sweep is the check that the physics did not move. Run A and run C are not re-run.
44. **The third review pass's minors fixed after the gate** (protocol: the loop leaves the
    third pass's minors unfixed): ten of S3c's eleven pass-3 minors were sentences that the
    step itself made false ("an SP1-type sweep's index is unchanged"; "keeps its name and
    place"), physics.md wraps, and one assertion of the slow end-to-end sweep test; fixed in
    77e1691 (docstrings, physics.md, two test files; no output changes), checked by ruff, the
    touched fast tests (98 passed) and that slow test (passed, 505.5 s). The eleventh
    (H3-02) corrected the amendment's draft before its commit. Accepted by the session.

45. **The sweep re-run recorded a dirty tree, and its quiet machine rests on this session's
    records only** (protocol section 4: a run starts from a clean committed tree "so the results
    directory records ... no dirty flag"; pre-registration section 11 and Amendment 1: a quiet
    machine): the re-run of `sweep` A started 2026-10-19T17:23:21Z from 2b343d7 and recorded
    `2b343d7f25eb`, dirty true. `results_io.git_info` counts untracked files outside results/;
    by the session's account the only ones at the start were the 13 draft files of the findings
    note under docs/findings/ (the note, its tables .md/.json and ten PNGs), and `git status
    --porcelain -- src configs experiments tests pyproject.toml uv.lock` was empty four seconds
    before the start, with no tracked file modified. The re-run reproduces all 657 pre-existing
    cells of the first sweep's two indexes, so the dirt reached no number. Beside the re-run
    this session ran only read-only review agents (stdlib reads of results files, 17:24 to
    17:39Z) and a git worktree checkout outside the repository; its records do not cover
    other Claude Code sessions on the machine, and sessions of two other projects wrote
    transcript files in the re-run's window (file times only), as another did during the
    convergence check's re-run (06:38Z). Results are deterministic, so load moves wall times
    only. Not re-run a third time (a third sweep directory for a flag that measures untracked
    documents); accepted by the session, not a user decision, and disclosed in the note's
    Provenance and Reproduction. The lesson is in the protocol's section 11.
46. **Step S7a's findings scripts grew beyond the registration's two** (pre-registration
    section 5 and design 4.11 name a committed tables script and a figures script): a third,
    docs/findings/scripts/sp7_s7a_checks.py (9b91473), evaluates section 9's checks and
    Amendment 1's reproduction read-only, so their conclusions trace to a kept file (review
    finding H-14); its output is docs/findings/RQ1-structural-2d-checks.txt. The tables and
    figures came first from the uncommitted working tree (2026-10-16) and were regenerated from
    the committed scripts after review (tables b82417b; figures, after review passes 2-4,
    a5b21b8). Accepted by the session.
47. **The linear motor's event set goes beyond design 4.6** (design 4.6 names the events
    `drive_ramp_end`, `power_limit`, `drive_cap` and `taper_start` as logged boundaries of the
    push): S4 makes every watch a terminal event that ends a sub-phase, re-flies the step to
    the crossing, adds the end events `power_limit_end` and `drive_cap_end`, scans each first
    flight for a watch value passed over inside one step, and splits at the delivered-thrust
    clamp of a hot push, so that every kink of the drive force lies on a sub-phase boundary and
    the closed forms hold at 1e-9. docs/physics.md "Linear motor (SP7 step S4)", *Sub-phases
    and events*, states the set and what it leaves unsplit (KI-048). Decided by the session
    (D-SP7-49); no constant_accel or pad path changed (the goldens and digests pin them).
48. **The force law's stop taper is applied after the power cap** (design 4.10: "the command
    or the force limit is scaled ... toward the holding value", and S4's criterion "F sdot <=
    P_max at every sample"): S4's `drive_force_N` caps the law's force at P_max/sdot and then
    scales it toward F_h = M g sin phi - T_sys, so the cap limits a force that is not flown.
    Where P_max/sdot >= F_h the flown power F_h sdot (1 - w) + P_max w stays below P_max (the
    review's probe: a 30 m taper inside the power phase reads power-limited at 0.970 P_max and
    exits 0.19 m/s, 0.28%, below the cap-after-taper order); where P_max/sdot < F_h (a drive
    too weak to hold the stack at that speed) the flown power exceeds P_max, which the tests do
    not reach. physics.md left the order open for the user; the session settled it from the
    approved design's own words (D-SP7-50): the cap applies to the flown, tapered force, fixed
    in S4a (KI-045). No registered run has flown a linear motor yet.
49. **Step S4a ran five review passes and five fix rounds** (protocol: up to two fix rounds,
    an extra round for pass-3 majors): passes 3 and 4 found majors in the fix rounds' own
    changes (the fall back inside the shaft, deviation 50), so round 4 ran after pass 4, and
    since nothing had reviewed it the session added a fifth pass on round 4's changes alone, a
    fifth fix round and a targeted re-gate (the step's full suite ran at the main gate, after
    round 4; round 5 changed wording, docstrings and tests, with its touched slow tests run).
    Accepted by the session.
50. **Step S4a reached files outside its row** (the row names prelude.py, engine.py, replay.py,
    scene.py, summary.py, plots.py, app.py and physics.md): the planners (phases/vertical.py,
    phases/planar.py, `FlightStart`), sim.py and video.py. A release below the mouth needs the
    flight to start inside the shaft: planar burns that started there were ended at once as an
    impact by the ground event's already-past rule, so the burns list `shaft_exit` and
    `shaft_apex` while below ground, and a fall back ends at the shaft floor (D-SP7-51). The
    floor applies to any release below the ground, so a constant_accel push to a buried exit
    that falls back now ends on its carriage; no shipped experiment has a buried exit and every
    track_end comparison of the gate is bit-identical. Accepted by the session.
51. **Step S4b's measured monotonicity and test push differ from the design and the brief**
    (design 4.4: "dm' > 0 under a force-controlled linear motor"; the S4b brief: a slow
    coupled solve "with no `offload_nonmonotone` and dm' > 0 recorded" on a short push):
    on the synthetic cold force-law case dm'(x) is about -4e-4 kg/kg (-4.594e-4 at x*): with a
    fixed force n rises as the stack lightens, but each tank's head F m_prop/(M g0) falls as the
    offload empties it. The hot push without a carriage gives +0.0092 and +0.0103. The solve
    raised no `offload_nonmonotone`, and the test records the sign and asserts design 4.4's
    floor -1/(2 E) = -0.114 kg/kg, not the sign; no push was chosen to make the sign positive
    (D-SP7-53). The brief's 50 m push ends no_offload carrying the synthetic file's 5.9 t, so
    the solve and the convergence check fly the same drive over 100 m. The step's files also
    reached metrics.py, metrics_planar.py (exact track peaks), config.py (the refusal of an
    unused rise-time override), results_io.py and summary.py (the flown-push line and flag
    keys), beyond the row's sim.py and structure.py. Accepted by the session.
52. **Step S5's choices beyond the brief, and a step S5a added** (the S5 row names
    assist/linear_motor.py, dynamics.py, losses.py and physics.md): the implementer added three
    refusals the brief did not name (a sealed shaft with the force law's stop taper, whose
    holding target ignores the column; a vehicle with no aero block, whose body diameter is
    unknown; a push that cannot beat the weight plus the column force at the track end, as
    `drive_stall`), and the change reached config.py, atmosphere.py, metrics*.py, summary.py and
    replay.py. Two run-level lines (`sim.PLANAR_ASSUMPTIONS`, the early-release line) and the
    readers (replay's vented test, the scene's display-only list) still describe a sealed shaft
    as vented; since file B registers a sealed variant, the wording is fixed in an added step
    S5a before S6b rather than left to S7c. Accepted by the session.
53. **Step S5a's files beyond the row, and its reports rebuilt** (the S5a row names sim.py,
    phases/prelude.py, replay.py, scene.py and physics.md): the change also reached app.py
    (`pair_shafts`), assist/linear_motor.py (the drive's shaft line), metrics_planar.py,
    phases/planar.py, plots.py and run_data.py (the sealed wording where they state the shaft),
    with no vented or constant_accel byte moved. The workflow paused at a usage limit during
    review pass 3; on 2026-11-02 a temp-folder cleanup deleted the step's brief and its pass
    1-2 review and fix reports (the workflow journal survived). The brief was restored from
    the session record, the reports were rebuilt from the journal's result lines, and the
    workflow resumed from the journal (passes 1-2 replayed, pass 3 and the gate run live).
    Briefs, step scripts and reports now live outside the temp folder. Accepted by the
    session.
54. **Step S6b's gate item closed by the orchestrator, its files beyond the row, and a reading
    against the brief** (the S6b row names experiments/ and docs/phases/inputs/): the step
    also added the committed rules script (docs/findings/scripts/sp7_drive_rules.py), file B's
    tests (tests/test_config_planar.py; tests/test_config.py's file count) and physics.md's
    rows, as the brief asked. The gate found every technical check passing and one item open:
    the choice of M (full precision against the rounded 572,354.4 kg the brief and the
    sources write). The orchestrator logged it as D-SP7-55 and cited it in the addendum, with
    no value moved, and did not run the gate again. The brief named KI-067 an unconservative
    bias of lm_cmd_hot and lm_fixed_hot; the addendum states that it does not reach them
    (neither holds on the clamp before its push start), the gate's flights support it, and
    the orchestrator accepted it. Accepted by the session.
55. **Step S7b in two parts with two commits, and its files beyond the row's folders** (the
    S7b row names results/ and docs/findings/): part 1's two check scripts were committed
    first (b291518, documents only) so that the registered convergence check ran from committed
    scripts and from run B's code (`git diff --quiet 642e11e b291518 -- src configs experiments
    pyproject.toml uv.lock tests` exits 0); the orchestrator ran the convergence check and the
    blocking checks between the parts; part 2's note followed (e5f64b3). Part 2 also changed
    README.md (its results section, and the SP1 bullet's "No structural model exists yet.",
    which the new SP7 subsection below it made false) and docs/physics.md (its S7b research
    notes), both named in the row's text. Accepted by the session.
56. **Step S7c withdraws S3a's directory rule, and its files beyond the row** (the S7c row
    names replay.py, app.py, compare.py and site/build.py): deviation 34's directory rule
    (H-S3a-P2-03: the closing clause dropped in any directory whose offload record charges a
    modelled mass, `summary.offload_charges_modelled`) is withdrawn with the old claim (fix
    round 1, V1 and H-S7c-P1-04): the new pointer is true beside the block caveat that names
    the model, and the replay page prints no block caveat, so under the rule a penalty-only
    selection of a structural directory carried neither. The function is removed and a test
    asserts it is gone; deviation 34 stays as the record. The step also changed summary.py
    (that removal), templates/app.html (a comment), the landing page and the gallery index
    beyond the brief's one landing line (on review majors: the landing page's loads caveat
    and results box now state SP7's reading, with no new number), five manual chapters,
    docs/physics.md and four test files, as the brief's wider list asked. Accepted by the
    session.
57. **Step S7d, added beyond the plan** (the step table had no such row): the demo's fast
    suite failed for reasons unrelated to the code under test, on a machine carrying other
    projects' pytest runs, and exit criterion 10 needs the suite green whatever else the
    machine is doing. Tests and physics.md's test-map rows only; two findings (KI-092, KI-093)
    left open rather than fixed in src/, which the step could not edit. The step also went past
    the brief's named tests where the scan found the same race (eight test files), and split
    one guard (D-SP7-56), so the slow tier grew by one to 54 and the suite to 2,271; the fast
    count is unchanged at 2,217. Accepted by the session.
58. **Step S8's files beyond the brief's list:** tests/test_caveat_wording.py (the deck joins
    the scan's sources; the docstring named this rewrite, and the gate accepted it under the
    brief's exception), site/templates/replay-frame.html and site/assets/site.css (a phone
    overflow on every framed page, the unframed demo page keeping its 7 px), docs/manual/02
    and 10, docs/physics.md's section, and README's "planned for Phase 3" bullet, which was
    false. Accepted by the session.
59. **Step C1's fact-check predates two steps, its questions gained recommendations, and
    its files go beyond the row** (the C1 row names docs/, TODO.md and memory): SP3's
    fact-check was made at 6cf0fd2, before S7d and S8 were added or run, so C1 re-validated
    it at d03367b and fixed in the edit what had moved. The brief asks every open question
    with the recommendation first; the fact-check recommended on Q1 and on Q3's planar-only
    blocks only, so Q2, Q4, Q5, Q6 and Q3's clause on the `planar` key carry
    recommendations drafted from the SP3 file's own text, marked as drafted there and in
    the handoff, and answered by no one. The brief's item 7 reaches outside the row's
    files: README.md (two sentences) and site/index.html line 93 (one clause). Its fix
    round went one clause past item 7(b) in the note: the sentence 7(b) re-cut said the
    layer-2 rows move every design axis, and two reviews graded that major, so it now says
    which rows fly which axes and the dated line at the note's status block says so; what
    stays outside is KI-101. The board also gained the three SP7 inputs its table lacked
    and lost its stale "No structural mass is charged today", and section 13 here gained
    one dated line, since the live handoff's section 10 now holds SP3's prompt. Pass 2 of
    the physics review added a seventh question, Q7, beyond the brief's six: on a replica,
    not a run, the reason section 5.10 gives for the 5 kg bound does not hold under section
    5.7's law, in text that predates this step. The bound, its number and the prompt's
    sentence on it stay; dated lines at 5.10 and risk 4 and clauses at 5.5 and 5.7 say what
    changed. Five of SP3's gates changed reading at this step, each a proposal its step 0
    confirms: exit criterion 3 and S1.2's rows and pointwise dV/dt, and S1.3's kick event
    (exit criterion 4), now read 1e-12 against the quantity's scale; exit criterion 3 and
    S1.2's orbit gate read each component of h against |h| and of the eccentricity vector
    against e, and state an rtol, 1e-12, since CLAUDE.md's upper limit of 1e-9 fails it
    with no step cap; exit criterion 5 and S1.4's 28.5 deg vacuum line now compare r, v_r,
    v_theta and m with the kick started on the in-plane speed; and exit criterion 5 and
    S1.4's equatorial line keep the design's 1e-9 and 1e-8 s on a smooth test air, on the
    pad and silo_hot_full, at a tightened rtol 1e-13 with `atol_scale` 1e-3, since no
    setting tried clears the shipped air's kinks with margin, and read the shipped air, on
    the pad and silo_cold, at 1e-8, 1e-6 and 1e-5 s, with v_r read against |v| on both
    lines (that file's section 7, Tolerances;
    reviews' replicas, not runs). For the user's review at the close: handoff section 6
    puts the five to the user beside SP3's questions.
60. **Step C1a added beyond the plan.** The exit gate's first run failed criterion 7 on
    two missing columns in the note's sweep sections. Under protocol section 6 the open
    criterion went to the user, who chose to add the columns from the record and run the
    gate again in full (D-SP7-57), rather than accept a logged miss. The criterion was
    not reworded. The electrical peak is derived, not recorded, and its assumption is
    stated in the note.
61. **Step C2's files beyond its row, and the gate run twice** (the C2 row names docs/):
    the exit gate ran twice at the close (deviation 60 for why). Its close changed TODO.md,
    CLAUDE.md, README.md, docs/manual/README.md, site/index.html, site/deck/index.html and
    the deck PDF, and the memory notes, as its brief's "After the gate" asked: each a status
    text, no result number changed. Two edits went one line past the brief's list, to keep
    the pages in agreement: README's roadmap row for Phase 3 ("its close still to come",
    found by the brief's own grep) and the landing page's SP3 row, now "Next", as SP7's row
    was at SP2's close and as the deck's roadmap now shows. The gate read the brief's "start
    commit" 22c62e9 (SP2's close, the parent of "Start SP7") and also checked a7c9f0a, with
    the same result. Accepted by the session.

## 13. Prompt to start this phase

Final (2026-10-07, SP2's close-out at 705025f; KI-039 added at the close). Kept as the
record of how SP7 was started. SP2's handoff, archived as
docs/handoff/archive/2026-10-07-SP2.md, holds the same text. To resume SP7, use the
"Resume SP7" prompt below; docs/handoff/NEXT_SESSION.md section 10 holds that one.
(Dated note, 2026-11-05, step C1: that copy is now
docs/handoff/archive/2026-11-03-SP7-in-progress.md, section 10; the live handoff's section
10 holds SP3's prompt. Both prompts below stay as the record.)

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP7-structural-mass-push-load.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links, then the inputs the phase file links: none exist under
> docs/phases/inputs/ for SP7 yet (its Plan mode writes the first), so read the record it
> builds on instead: docs/findings/RQ1-fuel-offload-2d.md ("Structural penalty rows and
> break-even", "Depth and g-level", "Max-Q and loads", "Limits"),
> docs/findings/RQ3-silo-screening-2d.md ("Caveats", "Loads"), and sections 11 and 12 of
> docs/phases/SP2-launch-app-2d-scene.md for what SP2 changed.
>
> We are continuing launch-assist-sim. SP2 is closed: the local app (`launchsim app`), the
> 2-D scene (`launchsim scene`), the shared read-only reader run_data.py, caveats worded
> from each run's record, and the label `exploratory` on every app run. This session is
> phase SP7 (D-SP1-18, confirmed by D-SP2-40): charge the structural mass that the 4 g
> full-stack push needs, with a first-order sizing model validated against closed forms,
> so that SP1's headline (41.26 t of stage-1 propellant, 10.04% of stage 1, before any
> structural mass) carries a modelled structural cost with an uncertainty band beside the
> assumed penalty rows; and build the drive realism that interacts with it: a force- and
> power-limited linear motor with carriage mass and, if we keep them, modelled braking and
> the silo air column. The phase file is a brief with recommendations, not the design.
>
> Follow the session protocol. Run its start checklist: a clean tree; HEAD's subject
> "Close SP2: trackers, handoff, next phase file", SP2's closing commit (named in the
> handoff) an ancestor, and `git diff --stat <that commit> HEAD` touching only bookkeeping
> files; the fast suite green with the count recorded; the entry criteria of the phase
> file's section 4 (the pins, the two recorded payload capacities 26,054.3962 and
> 27,553.2271 kg within 0.002 kg, SP1's solver and run data, the app's basis); the
> inventory of section 6 re-checked against HEAD (last checked at 705025f); the open KI
> and B items owned by SP7 listed (B-004, B-005, KI-030, KI-039; B-007 if Plan mode
> re-targets it; KI-036 falls to the phase that edits replay.py). If the session starts in Plan mode, do
> the read-only checks first and run the suite right after approval, as the protocol's
> section 3 says.
>
> Then work in Plan mode (step 0). Put the questions of section 10 to me, each with your
> recommendation first and the trade-off in one line, and give the ambitious option fairly
> with its cost: Q1 model fidelity, Q2 the sizing basis (the flown stack or the full
> load), Q3 the existing margin, Q4 the drive scope, Q5 where the carriage load enters, Q6
> the findings note, Q7 the dynamic load factor. Settle the open design points of section
> 10. Structural FEM is a scope expansion: do not plan it without my approval. Show me the
> detailed design, the step table with gates and the exit criteria with their tolerances,
> and wait for my approval before writing any code. After approval, log the decisions as
> D-SP7-nn in TODO.md, save the design under docs/phases/inputs/, and make the start
> commit ("Start SP7: status in progress").
>
> Rules for the whole session. Plan mode, and docs/physics.md in the same change, for
> anything touching the equations of motion, frames, events, integrator settings or loss
> accounting (the linear motor, the air column and braking touch the track equation and
> its events). Every structural coefficient is sourced or marked assumed, in a structure
> file, never in a calibrated vehicle file. Every new physics piece passes its closed-form
> test before an experiment uses it. Never choose a drive or structural parameter to make
> the assist look better; published claims and probe numbers are comparisons, never
> targets. The experiment file and its expected readings are committed before any run
> (pre-registration), the runs start from a clean commit, and no results directory is ever
> overwritten or deleted. App runs follow D-SP2-37: reviewers and gates use a scratch
> results root, demo launches come from a clean tree after the last code commit, their
> summaries go in their own commit, and no app run is cited in a finding. Keep SP1's
> penalty rows beside the modelled number.
>
> Run every step through the loop: implementer; adversarial reviewers (a physics or
> numerics skeptic on every code step, a CLAUDE.md compliance auditor on every step, an
> honesty auditor on S0, S6, S7 and on every caveat or label you reword); up to two fix
> rounds; an independent gate; one commit per gate; the tracker commit at once ("SP7 step
> <k>: trackers (<hash>)"); then `git push origin main` and a check that the Pages
> deployment succeeded. Standing gates on every code step: fast suite green, ruff clean,
> the golden 1-D outputs byte-identical, the planar digest pin and the planar output
> capture unchanged, no shipped experiment or vehicle file changed, replay.html's sha256
> unchanged; the full suite after any physics-core change. No validated number may move:
> the pad and silo_cold payload capacities, and SP1's headline with the structural model
> off.
>
> At the end, run the end checklist of the protocol's section 7: an independent gate on
> each exit criterion (a criterion stays open only with my explicit acceptance, logged as
> a decision); the full suite and ruff with the counts recorded; the demo under
> docs/demos/SP7/; the phase file closed, the board, TODO.md, CLAUDE.md (status, commands,
> layout) and README.md updated, and the public face refreshed (landing page, deck and its
> PDF, gallery, manual) with the site built locally and no broken link; the close-out
> questions to me with the recommendation first (which phase runs next: SP3 in the planned
> order); the fact-check of the next phase's file against the code; the handoff archived
> and the new one written with the next prompt; the next prompt printed to me; the memory
> updated; the cold-read check by
> an agent that did not write the documents; the closing commit; the push and the Pages
> deployment confirmed. Report anything that undercuts the hypothesis, a modelled
> structure that cancels most of the offload included, as plainly as the rest.

**Resume SP7** (written 2026-11-03 at checkpoint 2, with the in-progress handoff; it
replaces checkpoint 1's text of 2026-10-16, which stays in
docs/handoff/archive/2026-10-16-SP7-checkpoint-1.md, section 10; paste it into a fresh
Claude Code session opened in this folder if this session ends before SP7 is complete;
docs/handoff/NEXT_SESSION.md section 10 holds the same text, and this version wins if the
two differ):

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP7-structural-mass-push-load.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links, then the inputs the phase file links:
> docs/phases/inputs/2026-10-08-SP7-design.md (the approved design; section 4.10 is file B),
> docs/phases/inputs/2026-10-08-SP7-sources.md (section 10: the drive rules) and
> docs/phases/inputs/2026-10-15-SP7-preregistration.md (part 1 and Amendment 1), and the
> draft note docs/findings/RQ1-structural-2d.md.
>
> We are resuming phase SP7 of launch-assist-sim, in progress since 2026-10-08: the
> structural mass that the 4 g full-stack push needs, charged by a first-order station
> sizing model into SP1's offload solve with an uncertainty band beside SP1's penalty rows,
> and the drive realism that interacts with it (a force- and power-limited linear motor
> with carriage mass, braking functions, the sealed shaft). Resume SP7 from the step table
> in section 7 of the phase file; the session log in section 11 holds the resume point and
> section 12 the deviations. Steps to S5a and checkpoint 2 are done; nothing is running.
> The next step is S6b: file B (experiments/silo_drive_2d.yaml) and the pre-registration
> addendum, built and committed before any run of file B (D-SP7-31: no run, sweep, offload
> solve or coupled structural solve of any of its cases until then). D-SP7-54 (the sealed
> bore of 5.24 m) is open to my change until that commit.
>
> Follow the session protocol for a phase in progress: the checks of its section 10, then
> the start checklist of section 3 without the status change. Then S6b; S7b (`run` B from
> the clean registration commit, alone on a quiet machine, then the registered convergence
> check, never beside it, and the note completed); S7c; S8; C1 and C2.
>
> Rules for the rest of the phase. The freeze D-SP7-31 holds: tests never solve a
> pre-registered case, the structure files stay as frozen at S2's commit, and a change to a
> structure file or to files A, B and C after their registration is a pre-registration
> amendment (its own commit, a logged decision, the note extended, never rewritten). Plan
> mode, and docs/physics.md in the same change, for anything touching the equations of
> motion, frames, events, integrator settings or loss accounting. Never choose a drive or
> structural parameter to make the assist look better: every value of file B comes from a
> rule fixed in the design or the sources note, and if a rule cannot be applied as written,
> stop and report it. The registered estimates and published claims are comparisons, never
> targets. App runs follow D-SP2-37. Keep SP1's penalty rows beside the modelled number.
> Run every step through the loop: implementer; adversarial reviewers as section 7 of the
> phase file names them; fix rounds and verification passes while majors remain
> (deviation 31); an independent gate that runs every command in the foreground, in chunks
> under ten minutes, and never ends its turn on a running command, with docs/physics.md in
> its file list (deviation 39); one commit per gate; the tracker commit at once; then
> `git push origin main` and the Pages check. The standing gates of section 7 hold on every
> code step. No validated number may move: the pad and silo_cold payload capacities
> (26,054.3962 and 27,553.2271 kg) and SP1's headline with the structural model off
> (41,262.908 kg). Close with the end checklist of the protocol's section 7 (steps C1 and
> C2). Report anything that undercuts the hypothesis, a modelled structure that cancels
> most of the offload included, as plainly as the rest.
