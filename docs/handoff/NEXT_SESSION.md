# Handoff: SP2 closed; start SP7 (structural mass of the push load, and a force-limited drive)

## 1. Header

- Written 2026-10-07, at the close of phase SP2 (session started 2026-10-05), following
  docs/process/SESSION_PROTOCOL.md sections 7 and 8.
- Phase just closed: **SP2**, the local app and the 2-D launch scene,
  docs/phases/SP2-launch-app-2d-scene.md.
- Closing commit (the last commit that changed code or results): `3a1b243`
  (step A7 part 2: the demo launches' app summaries under results/app/). The code commits of the session end with 7cb440f (step A7 part 1);
  every commit after the closing commit changed documents, site pages and trackers only
  (`git diff --stat 3a1b243 HEAD` touches CLAUDE.md, README.md, TODO.md, docs/, site/
  and nothing under src/, tests/, configs/, experiments/ or results/).
- This file is part of the bookkeeping commit that follows, subject
  `Close SP2: trackers, handoff, next phase file` (protocol section 7, item 12). A file
  cannot hold the hash of its own commit, so HEAD is identified by that subject. main was
  pushed to origin after it and the Pages deployment checked
  (`gh run list --workflow pages.yml --limit 1`); if a later docs-only commit records that
  check, its subject starts with `SP2:` and the start checklist's HEAD-subject test fails
  literally for that known reason, as it did at SP2's start (SP2 session log, 2026-10-05).
- Next phase: **SP7**, docs/phases/SP7-structural-mass-push-load.md. After it: SP3, SP4,
  SP5, SP6 (decision D-SP1-18, confirmed at this close by D-SP2-40).

Read in this order (protocol section 3, item 1):

1. This file.
2. docs/process/SESSION_PROTOCOL.md.
3. docs/phases/README.md (the program board).
4. docs/phases/SP7-structural-mass-push-load.md (the phase file).
5. CLAUDE.md.
6. TODO.md. While reading it, list the open known issues and backlog items owned by SP7
   (section 5 below lists them as of this handoff).
7. README.md.
8. The memory index and the notes it links:
   C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md
9. The inputs the phase file links. SP7 has none under docs/phases/inputs/ yet (its Plan
   mode writes the first); its prompt names the record to read instead.

## 2. The request

No new research request in SP2. The user's original request and the headline question are
in section 1 of docs/handoff/archive/2026-09-30-phases-0-2.md; SP2 served the part that
asked to see the launch happen in 2-D with the depth, the ramp start and the offload
configurable (quoted in section 1 of the SP2 phase file).

Choices the user made in SP2's Plan mode on 2026-10-05 (D-SP2-01 to D-SP2-08): a standalone
HTML scene export and an MP4 video; offline with system fonts; app runs in
results/app/<timestamp>/ with their summaries tracked and an exploratory banner, committed
at step boundaries; presets from SP1's experiment and the Phase 2 screening variants; the
gate vehicle only; fixed and solved offloads with stage 2 and both under Advanced; a
schematic look. On 2026-10-06 the user asked, mid-phase, that workflow agents run on
Fable 5.1 again after a usage limit had moved the session to Opus 5.5 (agents inherit the
session model; no decision needed). At the close-out question (protocol section 7, item 7)
the user chose SP7 as the next phase, the recommended option (D-SP2-40).

## 3. What was finished in SP2

**Steps** (SP2 phase file, section 7; every row with its commit):

| Step | What | Commit |
|---|---|---|
| A0 | Plan mode: the seven questions, the design, two mock-ups, an adversarial review of the design (2 blockers, 49 major, 31 minor, folded in) | `a5b8133` (the start commit) |
| A1 | Shared read-only run-data module; animate and replay switched; KI-002, KI-016, KI-017 | `9579f89` |
| A1b | Pillow in the dev extra (KI-018) | `78eaefd` |
| A1a | Replay caveat wording fixed at source (KI-029); gallery pages regenerated | `41f838a` |
| A2 | Display geometry, display-only reconstructions, the scene payload, the physics.md section | `58d1ad2` |
| A3 | Scene page part 1 and the `scene` command | `3f8b807` |
| A3b | Two panels on one clock, flight to orbit, separated bodies, the rate law | `a864a57` |
| A4 | The form builder and the launch function with the cached pad | `6f22046` |
| A4b | The local server and the `app` command | `48c540f` |
| A5 | The app page | `ed0f4bb` |
| A6v | MP4 export from the app | `637994a` |
| A7 | Full visual QA, QA fixes, the gallery scene page and video (part 1); the demo launches (part 2, app summaries in their own commit per D-SP2-37) | `7cb440f`; `3a1b243` |
| A8 | Close: documents and the public face with SP7's file fact-checked (part 1); the exit-criteria gate, the trackers, this handoff (part 2) | `96bbfa1`; the bookkeeping commit |

**Exit criteria** (SP2 phase file, section 8; 17 criteria, tolerances fixed by D-SP2-38).
The independent gate of step A8 (six agents, one criterion group each, and a cross-checker;
run at cb305a5 on 2026-10-07 with its own scripts) recorded its verdicts in that section.
Summary:

| # | Criterion | Verdict |
|---|---|---|
| 1 | The app starts (127.0.0.1 only, URL printed, a second server fails) | pass |
| 2 | A launch works for every setting and the screening presets | pass (19 launches) |
| 3 | Same numbers as the CLI | pass (303 values, worst 0.000 kg) |
| 4 | Refusals | pass (43 bad bodies, 422, nothing written; busy and code change refused) |
| 5 | The scene matches the run data | pass (worst 0.10 of each tolerance) |
| 6 | The offload is visible and right | pass (rebuilt mass within 0.050 kg) |
| 7 | Honest labels | **fail, accepted (D-SP2-41)**: an app summary with an imposed offload carries SP1's heading "Propellant saved at fixed payload" and its P_ref basis line; KI-039, owner SP7 |
| 8 | Browse and replay | pass (21 of 21 listed, both recorded directories play) |
| 9 | The pad is cached | pass |
| 10 | Loader and fixes | pass (reference page identical at A1; at the close only A1a's text keys differ) |
| 11 | Tests and guards | **fail, accepted (D-SP2-42)**: six new slow tests instead of one slow launch (the other five run real ffmpeg, Edge or a console interrupt) |
| 12 | Dependencies, no request off the machine | pass |
| 13 | Documents and public face | failed at the gate on two close-out items (TODO.md's priorities line, this handoff), fixed in the close; checked by the cold read |
| 14 | Demo recorded | pass |
| 15 | Export (standalone page, MP4) | pass |
| 16 | Watchable | pass (close-up at least 121 px; kicks 5.34, 7.78, 4.45 px; windows 1.667 and 2.500 wall s) |
| 17 | Requests from another origin are refused | the behaviour passed (196 hostile requests, none answered 2xx); the demo's real-browser record was missing at the gate and was added in the close: docs/demos/SP2/criterion17-browser-check.md |

The evidence of every row is in the phase file, section 8 ("Exit criteria results").

**What you can run.** `uv run python -m launchsim app` (127.0.0.1 only; Ctrl+C stops it);
`uv run python -m launchsim scene results/<experiment>/<timestamp> --runs pad silo_cold_s1
--out <file>.html`. The user manual's chapter docs/manual/07b-app.md describes both.

**The reproduction result (exploratory, not new evidence).** The app's `silo_cold_s1`
preset, launched through the app at the shipped search budget, gives the pad payload
26,054.396 kg, silo_cold 27,553.227 kg and the stage-1 offload 41,262.908 kg of
results/silo_offload_2d/20261003T112934Z with every difference 0.000 kg, and its time
series and events are byte-identical to the recorded ones (A4's gate; repeated by the demo
launch results/app/20261007T130614Z, 70.4 s with the pad cached). The app and the CLI run
the same code; the number is SP1's, with SP1's caveats (docs/findings/RQ1-fuel-offload-2d.md:
the gate vehicle calibrates +14.3% high; no structural mass is charged for the 4 g push;
sweep-optimized and unthrottled; most of the offload is the lighter stack's
thrust-to-weight; max-Q 3.4% above the pad's; the stage-2 case failed its verification;
the energy ratio is not an efficiency claim).

**What the scene shows that the model does not support** (named on every page, in the
manual and in the gallery): every shape and length; the body attitude (held when
unpowered); the spent stage and the fairing halves on a drag-free display-only coast; the
plume inside the shaft on hot starts; the carriage after release; one propellant level per
stage; the pad's liftoff marker; the position marker that replaces the rocket.

**Nothing in SP2 bears on the hypothesis.** SP2 changed no equation, event, integrator
setting, loss accounting, search, guidance or offload solver, ran no pre-registered
experiment and produced no finding; the six app runs under results/app/ are the recorded
demo, labelled exploratory.

**Recorded demo:** docs/demos/SP2/README.md (the QA table, 38 screenshots in both themes
plus the demo launches' 85, the demo launches with their API record and wall times, the
video numbers, the headless Edge commands) and docs/demos/SP2/criterion17-browser-check.md
(the real-browser cross-origin check, recorded by the exit gate at cb305a5).

**Public face.** The landing page, the deck (20 slides, with its PDF) and the manual were
refreshed; the gallery has the scene page site/examples/pad-vs-silo-offload-scene.html and
the scene video, both made from results/silo_offload_2d/20261003T112934Z, never from an
app run; the landing page and deck slide 18 show one demo screenshot of an app run
(docs/demos/SP2/shots/03-solve-done-tank-part-full-light.png, launch
results/app/20261007T130614Z), captioned exploratory.

**Decisions of the session** (full text in TODO.md): D-SP2-01 to D-SP2-08 (the user's
answers), D-SP2-09 to D-SP2-38 (the design, approved with the plan), D-SP2-39 (the
`pad_variant` name), D-SP2-40 (SP7 next), D-SP2-41 and D-SP2-42 (exit criteria 7 and 11 accepted as
logged misses at the close).

## 4. Requirements and status

| # | Requirement | Status on 2026-10-07 |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done before SP1; its caveat wording fixed at source in SP2 (A1a) |
| R2 | An animated scene of the launch itself, 2-D first | Done: SP2 (the app's scene, the standalone export, the MP4) |
| R3 | The same in a 3-D world | Not started: SP3, SP5, SP6 (dynamics), SP4 (the scene), after SP7 |
| R4 | Configure the launch depth in the silo | Done in SP1; in the app since SP2 |
| R5 | Configure where the thrust ramp starts | Done in SP1 (five ways); in the app since SP2 |
| R6 | Reduce the rocket's propellant at fixed payload and report the fraction replaced | First answer in SP1 (docs/findings/RQ1-fuel-offload-2d.md); the app solves or imposes it since SP2, exploratory; its survival depends on SP7 |
| R7 | Stay on the Falcon 9-class model | Standing; the app offers the gate vehicle only (D-SP2-06) |
| R8 | Lose nothing between sessions | Second full phase close by the protocol |
| R9 | One fresh session per phase; the previous session prepares the next | Exercised at this close |
| R10 | Public repository, pushed after every step, with a current logo, banner, deck, gallery, manual and Pages site | Done; refreshed at this close |

## 5. The next phase: SP7

Open docs/phases/SP7-structural-mass-push-load.md. It is a brief with recommendations,
not the design: SP7's Plan mode makes the design and saves it under docs/phases/inputs/.

**Goal** (SP7 section 1). Charge the structural mass that the 4 g full-stack push needs,
with a first-order sizing model validated against closed forms, so that SP1's headline
(41.26 t of stage-1 propellant, 10.04% of stage 1, before any structural mass) carries a
modelled structural cost with an uncertainty band beside the assumed penalty rows (+2, +4
and +8.1 t leave 32.29, 22.88 and 1.98 t; about 8.5 t leaves nothing); re-open the depth
question (a deeper, gentler push needs less structure); and build the drive realism that
interacts with it: a force- and power-limited `linear_motor` with carriage mass and, if
kept in Plan mode, modelled braking and the silo air column. It may undercut the
hypothesis; that result is reported as plainly as any other.

**What SP2 built that SP7 relies on or must not break** (SP7 section 5.1 and the re-check
block at the top of its section 6 give file and line):

- `run_data.CALIBRATION_RECORDS` (re-exported by plots) is the one calibration record
  behind the replay and animation caveats (KI-003); `replay.py`'s caveat functions are
  data-driven since A1a (one caveat source, D-SP2-23).
- The sentences a modelled structure must change, each pinned by tests: plots.py's
  animation footnote ("no sized structural mass", naming a penalty row's assumed mass),
  replay.py's structure caveat ("No structural mass is charged"), summary.py's exploratory
  banner line (`EXPLORATORY_PUSH_CAVEAT`, "no structural mass for the push"), appform.py's
  field text for `stage1_dry_mass_added_t`, and the manual's penalty-row wording
  (05b-offload.md, 12-faq-glossary.md). SP7 risk R11 names the eight test files that pin
  them; reword at source with the honesty review, update the pinned tests, regenerate the
  six gallery pages with the diff recorded, as A1a did.
- The app's basis: `launchsim app` copies the shared blocks and the baseline of
  experiments/silo_offload_2d.yaml and the presets of both committed planar experiment
  files at server start (SP7 entry criterion 8). A change to those files changes what the
  app launches; it is allowed but must be stated. The label value `exploratory` is reserved
  for app runs; configs/display/ is never read by the run path.
- The app's form offers `stage1_dry_mass_added_t` as its only structural input and a
  `constant_accel` push only (appform.py); whether it gains SP7's structural switch or a
  linear-motor launch is an open design point of SP7 section 10, not a requirement.
- The standing gate that templates/replay.html's sha256 is
  1fa6eba6be18c5c2a8d10a3e42880ae556375dcf1508f6feb937aca641916990 (frozen in SP2,
  D-SP2-21; KI-031 and KI-019 go to the phase that next edits it).
- Nothing else: SP2 did not touch results_io.py, sim.py, offload.py, search.py,
  guidance.py, dynamics.py, phases/, losses.py, compare.py, metrics*.py, the assist
  package, experiments/ or configs/vehicles/ (SP7 entry criterion 4, confirmed at 705025f).

**Inventory.** SP7's sections 4, 6 and 13 were fact-checked at 705025f on 2026-10-07
(commit 96bbfa1: 32 moved line references corrected, entry criterion 8 added, the prompt
made final; an independent reader's 12 corrections were applied; 96bbfa1's message). The commits after 705025f (96bbfa1, cb305a5 and the bookkeeping commit) changed
no path the inventory names; the close added KI-039 to SP7's section 10 and to its prompt: at the start of SP7,
`git diff --stat 705025f HEAD -- src tests configs experiments pyproject.toml uv.lock
site/build.py` must be empty; if it is not, re-check section 6 against HEAD (SP7 entry
criterion 6, risk R9). The manual's glossary row **penalty row** is at
docs/manual/12-faq-glossary.md 191 at HEAD (167 at 705025f), as SP7 section 5.1 says.

**Open items owned by SP7** (TODO.md): B-004 (P1, structural mass for the 4 g push and
the interface-hardware penalty), B-005 (P1, `linear_motor`; any remainder later), parts of
B-007 (air-column piston, modelled braking, release at a target speed; P2, "later" unless
SP7's Plan mode re-targets it), KI-030 (medium: the config accepts `true`, numeric
strings, inf and NaN for several numbers; SP7 step S4 adds the validators). KI-036 (the
replay page reads an unknown git state as clean) falls to SP7 if its step S3 edits
replay.py; KI-032 (the peak-power time metric on the absolute clock) if S4 touches that
metric. KI-039 (low, from D-SP2-41): the summary's offload section is headed
"Propellant saved at fixed payload" and its basis line says every offload is measured at
P_ref, also for imposed cases, which fly their own P*; SP7's step S3 rewords both at source
with the honesty review (SP7 section 10).

## 6. Decisions to put to the user first

None left open by SP2. In SP7's Plan mode (step 0) put the questions of SP7 section 10,
each with the recommendation there first and the trade-off in one line, and give the
ambitious option fairly with its cost:

- Q1 structural model fidelity: recommended B, first-order station sizing (testable closed
  forms, sourceable coefficients); A adds little to the penalty rows; C (FEM) is a scope
  expansion that needs the user's approval and whose inputs are not public.
- Q2 sizing basis: recommended the offloaded stack actually flown, with the full-load
  sizing as a bound row.
- Q3 the existing stage-1 margin over its pad envelope: recommended none (zero margin
  charges the most and does not favour the assist), with a margin as a sensitivity.
- Q4 drive scope: recommended the linear motor and carriage mass in; modelled braking and
  the air column in but first to cut; the curved track and cable winch out. Ambitious
  option: take the curved track (frictionless-arc test) and the cable winch (frequency
  test) too, at the cost of a second session or a split phase.
- Q5 where the carriage load enters: recommended an aft ring at the stage base, with the
  thrust structure as the alternative row.
- Q6 findings: recommended a new note (for example RQ1-structural-2d.md) with a dated
  pointer at the top of RQ1; RQ1's record kept.
- Q7 dynamic load factor at push start: recommended charge it from a stated force rise
  time and an assumed structural period, with the quasi-static value beside.

Then the open design points listed there (option (i) or (ii) of SP7 section 5.5; the
structure file's place and schema; sweep or cases for the stroke series; the target-speed
release event; the app's form; the push metrics and labels of a linear-motor run;
KI-039's reword of the offload heading and basis line (S3); KI-030's validators).

Waiting on the user, not blocking: KI-026 (upload assets/brand/social-preview.png by hand
under GitHub Settings, General, Social preview) and B-001 (results retention; deleting
results needs the user's OK).

## 7. State of the project

**Commits of the session**, newest first (`git log --oneline b69ff0c..HEAD` is the full
list):

- the bookkeeping commit `Close SP2: trackers, handoff, next phase file` (holds this
  file; it follows cb305a5 directly);
- cb305a5 A8 trackers part 1 (KI-037 closed, KI-038 logged); 96bbfa1 A8 part 1
  (documents, the public face, SP7's file fact-checked);
- 705025f A7 trackers (D-SP2-40); 3a1b243 A7 part 2 (the demo launches' app summaries and
  their record); fb34b24 A7 trackers part 1; 7cb440f A7 part 1 (visual QA, QA fixes, the
  gallery scene page and video);
- 931b19b A6v trackers; 637994a A6v (MP4 export); e248fe2 A5 trackers; ed0f4bb A5 (the
  app page); 7f36e8d A4b trackers; 48c540f A4b (the server and the `app` command);
  1c3e22d A4 trackers; 6f22046 A4 (the form builder and the launch function);
- f77f57c A3b trackers; a864a57 A3b (two panels, flight to orbit, separated bodies, the
  rate law); 3b5cbad A3 trackers; 3f8b807 A3 (scene page part 1, the `scene` command);
  1c30421 A2 trackers; 58d1ad2 A2 (display geometry, the payload);
- 8512bee A1a trackers; 41f838a A1a (caveat wording at source); 20d0039 A1b trackers;
  78eaefd A1b (Pillow); 5bac09a A1 trackers; 9579f89 A1 (run_data.py);
- a5b8133 Start SP2.

**Tests and lint.** Full suite at cb305a5 (the tree the exit gate ran on; no file under
src/, tests/ or configs/ changed after 7cb440f): 1719 passed (1678 fast, 41 slow) in 3,062.98 s (51 min; pytest prints 0:51:02) with LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1,
the exit gate's second run, on a machine loaded by the parallel gates. Its first run had
28 failures and 3 skips, every one a subprocess exiting 0xC0000142 at start; all 31
passed on an immediate re-run (SP2 session log, step A8 part 2). The log is in the SP2
session's scratch folder, C:\Users\rahul\AppData\Local\Temp\claude\D--DEV-ClaudeProjects-SpaceRocketOptimization\6999a833-8705-4f59-babb-7d35feacc46d\scratchpad\a8\exit\loader-tests-deps\full_suite_run2.txt
(temporary, not in the repository, and may be cleaned; the counts are also in the SP2
session log); ruff check: all checks
passed; ruff format --check: 109 files already formatted. The last fast run recorded in the SP2
session log: 1678 passed, 41 deselected (7cb440f).

**Results directories** on disk. Only each directory's top-level summary.md is tracked; a
fresh clone has no CSVs and must re-run an experiment before `animate`, `replay`, `scene`
or the app's run browser can play it.

| Directory | What | Notes |
|---|---|---|
| results/silo_offload_2d/20261003T112934Z | SP1 run (git b3150c1, clean); the RQ1 record | 19 run folders with timeseries.csv, 72 MB; the source of the gallery's scene page and video |
| results/silo_offload_2d/20261003T112949Z | SP1 sweeps | 5 sweeps, 20 points; no top-level metrics.json |
| results/silo_offload_2d_readme/20261003T112956Z | SP1 bridge on the README-loads fork | 5 run folders |
| results/silo_screening_2d/20260930T175743Z | Phase 2 screening run (git 7ad381f) | 12 run folders, 45 MB; SP2's reference directory for the replay page (247,949 bytes, sha256 3ca23dc5... before A1a) |
| results/silo_screening_2d/20260930T182453Z | Phase 2 screening sweeps | baseline and 3 sweeps, 24 points (25 timeseries.csv) |
| results/app/20261007T125946Z, ...130614Z, ...130817Z, ...130924Z, ...130950Z, ...131031Z | SP2 demo launches (git fb34b24, clean): silo_cold; silo_cold_s1 (the reproduction); the +8.1 t penalty row; ramp start by depth; by height by event; the failed ignition | 17 run folders, 57 MB in all; exploratory, never cited; summaries committed in 3a1b243 |
| results/calibration_f9_2d/ (two), results/guidance_trigger_2d/, results/silo_bridge_2d_readme/, results/silo_screening_1d/ (six) | Phases 0 to 2 | listed in the archived handoffs |

Sizes by `du -sh` on 2026-10-07.

**Findings** (docs/findings/README.md): unchanged in SP2 (CAL-f9-leo-2d, RQ1-fuel-offload-2d,
RQ3-silo-screening-2d, RQ2-ignition-timing-2d, RQ6-aero-2d-preliminary, and the 1-D
records). No app run is a finding.

**Open known issues that matter to SP7:** KI-030 and KI-039 (owned); KI-032 and KI-036 (conditional,
section 5); KI-003 (update `run_data.CALIBRATION_RECORDS` whenever the calibration is
re-run); KI-021, KI-022 and KI-023 (stale test comments and docstrings in tests SP7 may
touch); KI-035 (fast-tier tests can exceed the 5 s mark under load; standing). KI-031,
KI-019 and KI-038 belong to the phase that next edits replay.html or scene.py; KI-033 and
KI-034 are "later".

## 8. How work is done

docs/process/SESSION_PROTOCOL.md: the start checklist (section 3), the step loop
(section 4), the end checklist (section 7). For SP7 in particular:

- Plan mode, and docs/physics.md in the same change, for anything touching the equations
  of motion, frames, events, integrator settings or loss accounting: the linear motor, the
  air column and braking touch the track equation and its events.
- Every structural coefficient is sourced or `assumed: true`, in a structure file, never in
  a calibrated vehicle file (CLAUDE.md: copy a calibrated config, never edit it).
- Pre-registration: the experiment file and its expected readings are committed before any
  run; runs start from a clean commit; no results directory is overwritten or deleted.
- No validated number may move: the pad and silo_cold payload capacities (26,054.3962 and
  27,553.2271 kg, pinned in tests/data/silo_screening_2d_record.json) and SP1's headline
  with the structural model off; the golden 1-D outputs, the planar digest pin and the
  output capture unchanged; replay.html's sha256 unchanged.
- Reviewers per SP7 section 7: a physics or numerics skeptic on every code step, a
  CLAUDE.md compliance auditor on every step, an honesty auditor on S0, S6, S7 and on
  every caveat or label reworded.
- App runs follow D-SP2-37 (protocol section 4, "App runs"): reviewers and gates use a
  scratch results root; demo launches come from a clean tree after the last code commit
  and their summaries go in their own commit; no app run is cited in a finding.
- Push main after every tracker commit and check the Pages deployment
  (`gh run list --workflow pages.yml --limit 1`).

## 9. Gotchas learned in SP2

New in this session. The standing list is protocol section 11 (the Plan-mode freeze of
background workflow agents was added there during SP2).

- **Workflow agents die mid-step** (a model usage limit on 2026-10-05, an API 529 on
  2026-10-06). The workflow's journal (`subagents/workflows/<run>/journal.jsonl` under the
  session's transcript directory) keeps every finished agent's result;
  `Workflow({scriptPath, resumeFromRunId})` replays them from cache and runs only the lost
  agents. A lost fix round is not fatal: the next review pass re-finds its findings. The
  step pattern that held up over SP2 (implementer; two to four adversarial reviewers in
  parallel; up to three fix rounds; an independent gate with its own scripts; the
  orchestrator commits) found many real findings per step on the first pass (A5's
  reviewers: 49; SP2 session log). A workflow's result in the task notification is truncated (at about 25,000
  characters in this session): read the output file or the journal for the gate verdict.
- **Literal "only these files changed" gates fail on the orchestrator's own edits.** A8's
  documents gate failed G6 because the SP7 fact-check (protocol item 8) sat in the same
  working tree. Run a close-out's parallel document workflows on disjoint file sets, tell
  each gate which other files it will see, or accept and log the literal failure.
- **Agent edits arrive with CRLF line endings** on Windows. Check with
  `git ls-files --eol` (or count `\r\n` in Python) and normalise to LF before every commit;
  the gates and the site build report CRLF as a finding.
- **Loopback connection churn loses HTTP/1.0 posts.** Under the video export (one frame
  per POST) the standard-library server on HTTP/1.0 lost a frame per connection; the
  server answers HTTP/1.1 with a per-request deadline since A6v, the page retries, and the
  default fps is 20 so the default pair's natural length fits the 1,800-frame cap.
- **`localhost` costs about 2 s per request on this machine** (the IPv6 attempt times out
  first); the app prints and binds 127.0.0.1 (D-SP2-29). A busy or reserved port is one
  error line; `--port 0` picks a free one.
- **Headless Edge** (C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe) writes
  no file when started from Git Bash while Edge is running: run it from PowerShell with its
  own `--user-data-dir`. It ignores a `#hash` scroll position for screenshots (page tops
  only), lays out at about 500 px however `--window-size` is set (SP1's handoff,
  docs/handoff/archive/2026-10-04-SP1.md section 9), and prints a deck to PDF
  only against the built site served on 127.0.0.1 (images must resolve) with the deck's
  `?print` layout. The earlier gates' CDP drivers are under the SP2 session's scratch
  folder (C:\Users\rahul\AppData\Local\Temp\claude\D--DEV-ClaudeProjects-SpaceRocketOptimization\6999a833-8705-4f59-babb-7d35feacc46d\scratchpad\a5\gate\cdp_lib.mjs and a6v\gate\; temporary); the demo record has the commands.
- **PowerShell 5.1 lacks `[System.Text.Encoding]::Latin1`**: read a PDF's page count or
  CreationDate back with Python, not PowerShell.
- **`uv run ... app` exits 3221225786 on Ctrl+Break** (0xC000013A) although the server
  exits 0; Ctrl+C is the documented stop (KI-037, closed in the manual).
- **The site build warns on italic captions that contain commas** (markdown's emphasis
  rule); put the path in backticks and reword.
- **The exploratory label travels through three places**: config.py's third label value,
  summary.py's banner (both git states), and the one-line prefix `replay.caveats` and
  `plots.animation_caveats` add for an exploratory directory. A new output of an app run
  must carry it too (exit criterion 7); a test scans the templates for sinks that would
  let data become HTML.
- **The cached pad is re-wrapped, not reused**: `dataclasses.replace(cached, name=...,
  resolved=resolved.baseline)` reproduces the CLI path; a verbatim cached object changes
  the result through results_io's identity tests (D-SP2-10). The cache key includes the
  server-start git state, and a launch is refused after `git diff --quiet <start> HEAD --
  src configs experiments pyproject.toml uv.lock` shows a change (D-SP2-11).
- **A usage limit leaves the dead agents' processes running.** At the close a limit
  stopped five of the exit gate's seven agents; three app servers, static servers, a
  launch driver still posting, headless Edge on temporary profiles and a `tail -f` kept
  running. They were stopped by command line (only this session's), the partial scratch
  folders moved aside, and the workflow resumed from its journal (protocol section 11).
- **A loaded machine breaks subprocess tests.** With several gates running, the full
  suite took 51 min and its first run lost 28 tests to subprocesses exiting 0xC0000142
  (DLL initialisation failed); all passed on re-run. Re-run such failures alone before
  reading them as real; run the full suite when nothing heavy runs beside it.
- **Fast-tier tests can exceed the 5 s mark under load** (KI-035): judge a slow test by a
  quiet-machine timing before marking it `slow`.
- **The scene's grid is a selection of CSV rows, never a resample** (D-SP2-16): both rows
  of every duplicate time, every event row, then rows inserted until every CSV row is
  within half of each tolerance. A resampled grid misses the model's instant steps at the
  kick and at staging.

## 10. Prompt to start SP7

Paste this into a fresh Claude Code session opened in this folder. It is the same text as
section 13 of docs/phases/SP7-structural-mass-push-load.md; if the two ever differ, the
phase file's version is the one to use.

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
