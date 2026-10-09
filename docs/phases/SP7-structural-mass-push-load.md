# SP7: Structural mass of the push load, and a force-limited drive (planar model)

Status: in progress (session 2026-10-08)

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-10-04 in
the SP1 session (step 10, the close-out) after decision D-SP1-18, which added this phase
and ordered it after SP2 and before the 3-D phases SP3-SP6. The number is an identifier,
not a position (board, "How to add a phase"). Nothing in this file has been built or run.
No design input exists under docs/phases/inputs/ yet: SP7's own Plan mode makes the
design and saves it there. Sections 4, 6 and 13 were re-checked against the code at
commit 705025f on 2026-10-07 by SP2's close-out (protocol section 7, item 8): the
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
| S0 | Sources: every coefficient's range with its source or reason; both stages' layouts; the breakdowns; the Delta_gamma digitization; the ring's N_p, h/b and fitting factor; NOF by fidelity; t_r and f; the payload limits; the coefficient count; the linear-motor rules' method | docs/phases/inputs/<date>-SP7-sources.md | every number sourced or assumed with a reason; no range narrower than its source's spread without a reason; honesty and physics review | [ ] | |
| S1 | Sizing primitives (pure structure.py), units, named constants, test hygiene (D-SP7-34, KI-035) | structure.py, units.py, constants.py, physics.md, tests | each closed form against a hand value at 1e-12 relative; one sizing evaluation timed | [ ] | |
| S2 | Station model of both stages, `LoadCase`, the envelope from a pad Result, the flags, the plausibility rule, `StructureConfig`, the loader and the two structure files, the screened search and tornado frozen into the files | structure.py, config.py, cli.py, sim.py, configs/structures/, physics.md | the pad's own cases give 0.000 kg; stations converge (< 0.1 kg); provenance; shared sections identical; the frozen sets reproduce (slow, under 10 min); the sizing-only table in the session log | [ ] | |
| S3 | Coupling: the transform, its builder, dm in the verified dict with its provenance, memo keys, the offload case field and the experiment block, refusals, run-level keys, the pins | offload.py, sim.py, results_io.py, config.py, cli.py, physics.md | constant-2 t cross-check = SP1's +2 t row (<= 0.002 kg, slow); structure-off headline (<= 0.002 kg, slow); dm' bound and smoothness; vehicle_at bit-identical across call orders; xv_dry_mass_delta_kg = dm1 + dm2; with no structure block, `launchsim run experiments/silo_offload_2d_readme.yaml --results-root <scratch> --no-plots` at the start commit and at S3 give metrics.json and summary.md identical apart from timestamp and git; full suite | [ ] | |
| S3b | Reporting: the payload cases, `structure_inputs`, the Structure subsection, the sweep and arm columns, the thickness figure, the post-hoc flight check | results_io.py, summary.py, plots.py, sim.py, physics.md | listed tests; full suite; visual and honesty review | [ ] | |
| S3a | Wording at every source (three-way, every run kind); KI-039, KI-036, KI-038 (version); the pinned wording tests; the gallery regenerated | summary.py, compare.py, sim.py, config.py, replay.py, scene.py, plots.py, app.py, docs/manual | the eight pinned files updated; the gallery diff is the one recorded line; honesty review | [ ] | |
| (checkpoint 1) | resolve and preflight of file A and one non-headline short structural case; an in-progress handoff point | | | | |
| S6a | Files A (silo_structure_2d.yaml) and C (silo_structure_2d_readme.yaml) and the pre-registration, part 1, committed before any run | experiments/, docs/phases/inputs/, tests/test_config_planar.py | the expected readings recomputed by the gate; `git diff --quiet <S2 commit> HEAD -- configs/structures/`; honesty review; clean tree | [ ] | |
| S7a | `run` A, `sweep` A, `run` C from the clean commit; the findings note's structural part | results/ (summaries), docs/findings/ | no `bug_suspect`; verifications within 1e-4 P_ref or flagged; reproductions within 0.002 kg; the frozen sets recomputed; honesty review | [ ] | |
| S4 | linear_motor core: both control laws, ramp, taper, caps, carriage, braking functions, the pending ignition, refusals, metrics; KI-030; KI-021-KI-023 | assist/linear_motor.py, assist/base.py, config.py, appform.py, units.py, compare.py, phases/prelude.py, phases/engine.py, phases/planar.py, metrics*.py, physics.md | closed forms at 1e-9 relative; limits honoured at every sample; energy identity < 1e-9 (required 1e-6); hot interface force for f_imp 0, 0.5, 1; refusals; pending ignition in 1-D and planar; KI-030's sixteen cases refused with digests unchanged; braking functions; full suite | [ ] | |
| S4a | Release at a target speed; the readers (replay drive clause, scene push labels); the app lists linear-motor and structural directories; the force-against-speed figure; conditional summary rows | phases/prelude.py, phases/engine.py, replay.py, scene.py, summary.py, plots.py, app.py, physics.md | event at sdot = v_release with s from the closed form; track_end runs bit-identical; a scratch linear-motor run's replay and scene pages reviewed against metrics.json; the app started on that scratch root lists and plays it with no 500; full suite; gallery regenerated | [ ] | |
| S4b | The structural transform on linear-motor pushes | sim.py, structure.py, physics.md | n_peak, F_peak and DLF against closed forms (both laws, cold and hot, target speed, taper); a slow coupled linear-motor solve with no `offload_nonmonotone`; linear-motor convergence < 0.1%; full suite | [ ] | |
| S5 | The sealed shaft; the piston-work record | assist/linear_motor.py, dynamics.py, losses.py, physics.md | the adiabatic work closed form; F_p <= p_0 A; F_int lower by (m_v/M) F_p; the identity < 1e-9; `AssistEnergyBudget`'s fields unchanged; full suite | [ ] | |
| (checkpoint 2) | the drive realism complete; an in-progress handoff point | | | | |
| S6b | File B (silo_drive_2d.yaml) and the pre-registration addendum | experiments/, docs/phases/inputs/ | the rule values recomputed independently to 1e-12; structure files unchanged; honesty review; clean tree | [ ] | |
| S7b | `run` B; the note completed; RQ1's pointer; README results; the findings index; physics.md research notes; derived figures by a committed script | results/ (summary), docs/findings/ | B's silo_cold_s1_st within 0.002 kg of A's; lm_cmd's uncharged x* within 0.25 kg of SP1's; no `bug_suspect`; honesty review | [ ] | |
| S7c | Program-level wording in code (replay, the app's headline caveat, site/build.py, the compare.py docstring); the pinned tests; the gallery regenerated | replay.py, app.py, compare.py, site/build.py | `git grep -n "no structural model exists"` only in dated or archived records; full suite; honesty review | [ ] | |
| S8 | Public face: the demo record, a gallery entry for an SP7 run, the deck slides and PDF, the manual chapters, the landing page, CLAUDE.md layout, status and commands, the protocol's caveat line | docs/demos/SP7/, site/, docs/manual/, CLAUDE.md, docs/process/ | site build with no broken link; visual, honesty and compliance review | [ ] | |
| C1 | Documents: this file, the board, TODO.md, SP3's file fact-checked, the handoff, memory | docs/, TODO.md, memory | compliance review | [ ] | |
| C2 | Independent exit gate on every criterion; full suite; cold read; closing commit; push; Pages | docs/ | each criterion passes or the user accepts a logged miss | [ ] | |

**If room runs out** (put to the user when it happens; compute-only cases and the CLAUDE.md arms
are never cut): S5 and lm_fixed_sealed; the payload cases; S4a's target-speed release with
lm_fixed_target; file C (the bridge); the thrust-structure row. A last resort tied to checkpoint
1: run A and C and write an in-progress handoff before building the drive.

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
   six pages regenerated with only the recorded KI-038 line; the app's basis unchanged
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

## 13. Prompt to start this phase

Final (2026-10-07, SP2's close-out at 705025f; KI-039 added at the close). The handoff
holds the same text.

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
