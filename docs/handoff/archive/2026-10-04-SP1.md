# Handoff: SP1 closed; start SP2 (local app and 2-D launch scene)

## 1. Header

- SP2 started 2026-10-05. If you are a new session and the phase file says in progress, resume per SESSION_PROTOCOL.md section 10 from the step table.
- Written 2026-10-04, at the close of phase SP1 (session started 2026-09-30), following
  docs/process/SESSION_PROTOCOL.md sections 7 and 8.
- Phase just closed: **SP1**, launch settings and fuel offload at fixed payload (planar
  model), docs/phases/SP1-fuel-offload-planar.md.
- Closing commit (the last commit that changed code or results): `5007515`.
- This file is part of the bookkeeping commit that follows it, subject
  `Close SP1: trackers, handoff, next phase file` (protocol section 7, item 12). A file
  cannot hold the hash of its own commit, so HEAD is identified by that subject. main was
  pushed to origin after it.
- Next phase: **SP2**, docs/phases/SP2-launch-app-2d-scene.md. After SP2 comes SP7 (the
  structural mass of the push load and a force-limited drive), then SP3 to SP6 (decision
  D-SP1-18; section 5 below).

Read in this order (protocol section 3, item 1):

1. This file.
2. docs/process/SESSION_PROTOCOL.md.
3. docs/phases/README.md (the program board).
4. docs/phases/SP2-launch-app-2d-scene.md (the phase file).
5. CLAUDE.md.
6. TODO.md. While reading it, list the open known issues and backlog items owned by SP2
   (section 7 below lists them as of this handoff).
7. README.md.
8. The memory index and the notes it links:
   C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md
9. The inputs the SP2 phase file links: docs/phases/inputs/2026-09-30-survey-animate-replay-visuals.md,
   the section "SP2: local app and 2-D scene" of
   docs/phases/inputs/2026-09-30-SP1-approved-plan.md, and
   docs/findings/RQ1-fuel-offload-2d.md (the headline the app shows beside its caveats).

## 2. The request

No new research request in SP1. The user's original request and the headline question, in
their words, are in section 1 of docs/handoff/archive/2026-09-30-phases-0-2.md; section 1
of the SP2 phase file quotes the part SP2 serves.

Two new requests were made during the session. Neither was saved word for word; both are
recorded as decisions in TODO.md.

- **2026-10-02, public repository.** The user asked to put the repository on their GitHub
  in a new repository, to commit and push after every step, phase and milestone, and to
  keep a logo, banner, slide deck, animation examples, a user manual and a GitHub Pages
  site current. The one phrase of theirs that survives (memory note
  public-repo-and-push-cadence.md): the work is "not shareable and non commercializable",
  but should be public facing. Decisions D-SP1-14 to D-SP1-16; built as SP1 step P.
- **2026-10-04, order after SP1.** At the close-out the user chose the recommended option:
  SP2 runs next as planned; then a new phase, SP7, for the structural mass of the push load
  (and a force-limited drive), before the 3-D dynamics of SP3 to SP6, because the
  structural cost decides whether SP1's 10% survives while the 3-D models are expected to
  move it by kilograms. Decision D-SP1-18. Phase numbers are identifiers and are never
  renumbered: SP7 runs after SP2 and before SP3 (docs/phases/README.md, "How to add a
  phase").

## 3. What was finished in SP1

**Steps** (SP1 phase file, section 7; every row with its commit):

| Step | What | Commit |
|---|---|---|
| T | Tracking system: protocol, program board, phase files SP1 to SP6, TODO.md with ids | 98eb5a6 |
| 1 | Planar digest pin of the shipped experiments; output capture; exclusive key families in the merge | e2fb6ab |
| 2 | Silo depth with `exit_speed_mps` as the alternative to `net_accel_g` | 1fc92d3 |
| 3 | Ramp start by depth, by speed and by closed-form height; preflight before any results directory | 83d66dd |
| 4 | Ramp start at a height by an altitude event; `no_ignition` failure | 1a0b2af |
| 5 | Offload solver core (fixed-payload propellant offload), on branch sp1-step5 | a03e218 (merged 04f6542) |
| 6 | Cross-vehicle decomposition, on branch sp1-step5 | 9ca508b (merged c8e0020) |
| 7 | `offload:` experiment block, pipeline, reporting, replay role, in-memory entry point | 6719f92 |
| 8 | Pre-registered experiments (committed before any run) | c2a4cf0 |
| 8a | Reporting fixes before the run (pre-registration Amendment 1) | d336933 |
| 9 | Runs from the clean commit b3150c1; findings note RQ1-fuel-offload-2d | fd664a5 |
| P | Public repository and its face, on branch public-site | 9024d40 (merged e0b9fd8) |
| 10a | Added at the close: `animate` fixed for offload runs; the SP1 animation in the gallery | `5007515` (the closing commit) |
| 10 | Close SP1: exit criteria gate, demo, close-out decisions, SP2 fact-check, this handoff | the bookkeeping commit |

**Exit criteria** (SP1 phase file, section 8). The independent gate of step 10 records the
verdict of each criterion in that section; this table gives the evidence.

| # | Criterion | Evidence |
|---|---|---|
| 1 | Tracking system; phase files SP1 to SP6; handoff and prompt for SP2 | Step T; this file; the SP2 phase file fact-checked at b3150c1 (commit ac66fd0), its prompt final |
| 2 | Exit speed and the four ramp-start settings pass their closed-form tests | Gates of steps 2, 3 and 4 |
| 3 | Toy closed forms; stage-1 pad control within its bound; P_ref reproduced at each solved case, or the case flagged | Step 5 gate (bound 1.63 kg); shipped run: x_pad = 0 with m_res(0) = -0.0016 kg (a resolution effect); headline verification +0.0085 kg against 2.6 kg; the stage-2 case failed its verification and carries its flags |
| 4 | Run and sweeps from a clean committed tree, no `bug_suspect` | All three directories record git b3150c1754ee, not dirty; "No run and no comparison is bug_suspect" in all three summaries |
| 5 | Findings note passes the honesty review, headline with penalty rows and sensitivity | Step 9 gate (fd664a5) |
| 6 | Full suite green; golden 1-D and planar digests unchanged; ruff clean | On the closing tree: 1299 passed (1264 fast, 35 slow) in 13 min 8 s with LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1 at the closing commit 5007515 (2026-10-04); ruff check: all checks passed; ruff format --check: 91 files already formatted (section 7; SP1 session log). Before step 10a: 1295 passed at fd664a5, 14 min, exact golden tier |
| 7 | Demo recorded under docs/demos/SP1/ | docs/demos/SP1/README.md |
| 8 | Public repository current; Pages site live with the landing page, manual, deck and gallery updated with SP1's finding | Refreshed and built locally at the close; main is pushed after the bookkeeping commit and the Pages deployment is checked then (protocol section 7, item 14), so no file of that commit can record it. The gate's verdict is in SP1 section 8 |

The Phase 2 calibration miss (+14.3%, accepted 2026-09-30, D-P2-08) is not an SP1
criterion; it travels with every number below.

**Headline** (docs/findings/RQ1-fuel-offload-2d.md; preliminary, sweep-optimized,
unthrottled). At the full-load pad's payload (26,054.4 kg) and orbit (200 km circular,
28.5 deg, due east), the 3 g0 net, 100 m cold-start silo (exit 76.7 m/s; stage 1 lit 0.5 s
after release with a 2 s ramp) lets the Falcon 9-class gate vehicle leave out **41.26 t of
stage-1 propellant: 10.04% of the stage-1 load, 7.96% of the total** (case
`silo_cold_s1`). That is 2.76 times the ideal-screening estimate at the same release speed
(14.98 t); the cross-vehicle decomposition explains the difference. Under +/-10% of
stage-1 dry mass, Isp, C_D and drive efficiency the offload stays between 38.67 and
44.46 t. The caveats that travel with it:

- **Calibration.** The gate vehicle calibrates +14.3% high. On the README-loads fork,
  which calibrates inside the band (+8.3%), the same case removes 36.01 t, 9.10% of its
  stage-1 load. Read it as 9 to 10% of stage 1 on two forks of a model, not as a
  Falcon 9 figure.
- **No structural mass for the 4 g0 push.** An assumed +2, +4 and +8.1 t of stage-1 dry
  mass leave 32.29, 22.88 and 1.98 t; about 8.5 t (extrapolated) leaves nothing. These
  rows are assumptions, not a sized structure. SP7 exists to replace them.
- **Part of it is the lighter stack.** Flown from the pad with the same 41.26 t removed,
  the vehicle falls 1,402.0 kg short of the payload. Read as the pre-registration worded
  it, that shortfall is small against the offload, so most of the offload is the lighter
  stack's thrust-to-weight. A delta-v reading chosen after the run gives the lighter stack
  28 to 29% of the 228.2 m/s of ideal delta-v the offload removes. The note states both
  readings.
- **Loads.** The offloaded run's unthrottled max-Q is 3.4% above the pad's (38,438.5
  against 37,191.4 Pa); the full-load silo run flew 16% below it.
- **Stage 2.** The stage-2 case failed its independent verification: its figure is a
  flagged lower bound and a property of the vehicle model. Stage 1 is the only headline.
- **Energy.** The removed RP-1's combustion heat is about 128 times the push's metered
  electricity (1,156 kWh). That compares unlike quantities; it is not an efficiency claim.
- Also: sweep-optimized and unthrottled guidance; a free kick (no angle-of-attack
  aerodynamics); a prescribed-acceleration drive with no force or power limit, a massless
  carriage and no shaft drag; tanks partly filled with every dry mass kept.
- Only the exit speed matters: 200 m at 1.5 g0 net gives the same offload as 100 m at
  3 g0, with 2.5 g0 felt on the track.

**Recorded demo:** docs/demos/SP1/README.md (console output of the run, sweep and bridge;
the offload block of summary.md; the replay page pad_vs_offloaded_silo.html with a
screenshot).

**Public face.** The repository is public at
https://github.com/khoks/RocketLaunchOptimizationSimulator (all rights reserved; LICENSE).
The GitHub Pages site is https://khoks.github.io/RocketLaunchOptimizationSimulator/
(landing page, slide deck with its PDF, animation gallery, user manual), built by
site/build.py and deployed by .github/workflows/pages.yml on every push to main. At the
close it was refreshed with SP1's finding: the landing page, the deck, the gallery
(site/examples/pad-vs-silo-offload.html, site/examples/offload-vs-paired-pad.html and the
SP1 animation of step 10a) and the manual (new chapter docs/manual/05b-offload.md).

**Decisions of the session** (full text in TODO.md's decisions log):

| Id | Decision |
|---|---|
| D-SP1-01 | 3-D means true 3-D dynamics in three stages (S1 sphere, S2 oblate, S3 6-DOF) |
| D-SP1-02 | The visual tool is a local app first: form, Launch button, scenes inside it |
| D-SP1-03 | Offload of stage 1 (headline), stage 2 and both; tanks partly filled; fixed payload = the full-load pad's capacity |
| D-SP1-04 | Structural penalty as parametric rows (+2, +4, +8.1 t) |
| D-SP1-05 | Silo depth: `stroke_m` with exactly one of `net_accel_g` or `exit_speed_mps` |
| D-SP1-06 | Ramp start by time, depth, speed, height by event, height by closed form |
| D-SP1-07 | Order: settings and solver, planar headline, the app, then 3-D (SP7 inserted before the 3-D work by D-SP1-18) |
| D-SP1-08 | One fresh session per phase; each session prepares the next |
| D-SP1-09 | The offload is an `offload:` block and a post-pass, not a figure-of-merit value |
| D-SP1-10 | Every offload mode is also solved on the pad; stage 2 and both quoted net of it |
| D-SP1-11 | Target under J2: osculating circular orbit at R_E + 200 km (for SP5) |
| D-SP1-12 | The 6-DOF model is a verification fly-out (for SP6) |
| D-SP1-13 | One-case bridge on the README-loads fork |
| D-SP1-14 | The repository is public on GitHub, all rights reserved |
| D-SP1-15 | Push main after every step's tracker commit and at every phase close |
| D-SP1-16 | Logo, banner, deck, animation examples, user manual and Pages site, kept current at every phase close |
| D-SP1-17 | The pre-registered experiment keeps its full design despite the longer runtime |
| D-SP1-18 | SP2 next; then SP7 (structural mass of the push load, force-limited drive); then SP3 to SP6 |

## 4. Requirements and status

R1 to R8 come from the first handoff (docs/handoff/archive/2026-09-30-phases-0-2.md,
section 2), R9 from SP1 step T, R10 from 2026-10-02.

| # | Requirement | Status on 2026-10-04 |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done before SP1 (`launchsim replay`); SP1 added the offload role (step 7) |
| R2 | An animated scene of the launch itself, 2-D first | Not started. SP2, inside the local app (D-SP1-02) |
| R3 | The same in a 3-D world | Not started. True 3-D dynamics in SP3, SP5 and SP6, the 3-D scene in SP4 (D-SP1-01); all after SP7 (D-SP1-18) |
| R4 | Configure the launch depth in the silo | Done: `stroke_m` with `net_accel_g` or `exit_speed_mps` (SP1 step 2, D-SP1-05) |
| R5 | Configure where the thrust ramp starts | Done: by time, depth, speed, height by event, height by closed form (SP1 steps 3 and 4, D-SP1-06) |
| R6 | Reduce the rocket's propellant at fixed payload and report the fraction replaced (the headline question) | First answer on the planar model: docs/findings/RQ1-fuel-offload-2d.md (preliminary, with the caveats of section 3). Its survival depends on the structural mass (SP7); the 3-D re-checks are SP4 and SP5. In the app: SP2 |
| R7 | Stay on the Falcon 9-class model | Standing: configs/vehicles/generic_f9_class_2d.yaml, never edited |
| R8 | Lose nothing between sessions | Protocol, board, phase files, trackers, handoffs and memory; first full phase close done at SP1 |
| R9 | One fresh session per phase; the previous session prepares the next one's documents, memory and prompt | First exercised at this close |
| R10 | Public repository (all rights reserved), pushed after every step, with a current logo, banner, deck, gallery, manual and Pages site | Done in SP1 step P, refreshed at the close. The social preview image must be uploaded by hand (KI-026, owner the user) |

## 5. The next phase: SP2

Open docs/phases/SP2-launch-app-2d-scene.md.

**Goal.** A local app, started with `uv run python -m launchsim app` and served on
127.0.0.1 only, in which the user sets the silo depth (exit speed or net acceleration),
the stage-1 ramp start (any of the five ways), a propellant offload (solved or fixed;
stage 1, stage 2 or both; an optional stage-2 pre-offload) and an assumed structural
penalty, presses Launch, follows the job's progress, and watches the pad and silo launches
side by side in an animated 2-D scene; and browses recorded results directories and
replays any planar run as a scene. Every app run writes a normal results directory
labelled exploratory; no finding comes from it. SP2 changes no physics, search, guidance
or offload solver.

**What SP1 built that SP2 relies on** (SP2 section 3 and entry criteria 2 to 6 give the
file and line of each):

- The in-memory entry point: `config.resolve_experiment(exp_dict, vehicle_dict)`,
  `sim.run_resolved`, then `results_io.planar_experiment_result(...)`, which returns the
  whole result, the offload report included, and writes nothing; `results_io.write_run`
  writes it. Tested by `tests/test_offload_pipeline.py::test_offload_in_memory_writes_nothing`
  (slow tier).
- The settings and their key families (`ASSIST_KEY_FAMILIES`, `IGNITION_KEY_FAMILIES`),
  the `offload:` block (`OffloadConfig`) and `SweepConfig.offload`, and the preflight
  `sim.check_resolved` that refuses a bad configuration before any directory is made.
- Replay of offload runs (role `offload`; offload runs are named with `--runs`, they are
  not in the default selection).
- The planar metrics the form and the HUD read: `PUSH_SETTING_METRICS`,
  `RAMP_START_METRICS`, `RAMP_START_REQUEST_METRICS`, `OFFLOAD_METRIC_KEYS`.
- Measured costs: a stage-1 offload solve with its verification takes about 90 to 110 s on
  this machine, a pad control about 30 s more (SP2 section 5.6).

**Inventory.** SP2 section 6 was fact-checked at b3150c1 on 2026-10-03 (commit ac66fd0).
fd664a5 and cfd9059 changed none of the paths it inventories (checked:
`git diff --stat b3150c1 cfd9059 -- src tests configs experiments pyproject.toml .gitignore
site/build.py` is empty). The close changed four of them, in the code commits that end with
the closing commit:

- site/build.py: the public-face refresh (text fixes for the gallery's two offload replay
  pages);
- src/launchsim/plots.py: step 10a (`animate` reads and labels the runs of the offload
  block; `plots.offload_role`, `offload_tag`, `animation_record`, `legend_title`);
- src/launchsim/replay.py: step 10a (`offload_note` now takes the run's role from
  `plots.offload_role`);
- tests/test_animate.py: step 10a (four new tests).

So the re-check command of the SP2 header, `git diff --stat b3150c1 HEAD -- src tests
configs experiments pyproject.toml .gitignore site/build.py`, lists these four files at
SP2's start. Re-check them against section 6 (their line numbers have moved) before
planning from it (SP2 header, entry criterion 8, risk R1). Generate A1's reference replay
page at the SP2 start commit as section 7 says; that value is the reference. For
information: regenerated on 2026-10-04 from the working tree with step 10a's edits, before
its commit, the page was unchanged from b3150c1 (247,949 bytes, sha256 3ca23dc5...; the
reference directory has no offload runs).

**Open items owned by SP2** (TODO.md): KI-002 (private plots helpers and duplicate
readers), KI-016 (fairing event mass convention), KI-017 (output-path rule mismatch),
KI-018 (Pillow not declared), KI-019 (Google Fonts in the replay page), and KI-029 (the
replay page's drive caveat ends "Each of these favours the assisted runs.", which is
misleading; site/build.py rewrites it in the gallery). KI-029 is SP2 section 5.8 item 5.

**Order after SP2.** SP7 (structural mass of the push load and a force-limited drive),
then SP3, SP4, SP5, SP6 (D-SP1-18; the program board's dependency order). The SP2 phase
file names SP7 as the phase after it (section 3, step A8, exit criterion 13 and its
prompt). At SP2's close, SP7 is the "next phase" of protocol section 7, items 7 to 9,
unless the user reorders again: the SP2 session fact-checks SP7's phase file against the
code and finalises its section 13 prompt. That file,
docs/phases/SP7-structural-mass-push-load.md, was written at SP1's close-out as a draft
(its exit criteria and its section 13 prompt are marked draft).

## 6. Decisions to put to the user first

None left open by SP1. In SP2's Plan mode (step A0) put the questions of SP2 section 10,
each with the recommendation there first and the trade-off in one line, and give the
ambitious option fairly with its cost: Q1 standalone HTML scene export (recommended yes,
the only way to put a scene on the public site) and video (recommended no for now); Q2 an
offline page (recommended yes, no request leaves the machine); Q3 where app runs are kept
(recommended `results/app/<UTC timestamp>/`, wholly ignored by git); Q4 the presets
(recommended SP1's experiment configurations); Q5 the vehicle (recommended the gate vehicle
only); Q6 the offload input (recommended both fixed and solved, fixed by default, stage-2
and both behind an advanced switch with the pad control forced on); Q7 the look
(recommended a schematic cross-section in the brand palette, with dark mode). Then the
open design points listed there.

Waiting on the user, not blocking: KI-026 (upload assets/brand/social-preview.png by hand
under GitHub Settings, General, Social preview) and B-001 (results retention; deleting
results needs the user's OK).

## 7. State of the project

**Commits of the session**, newest first (`git log --oneline 2eebcae..HEAD` is the full
list):

- the bookkeeping commit `Close SP1: trackers, handoff, next phase file` (holds this file);
- the code commits of the close (step 10a, with site/build.py of the public-face refresh),
  the last of them the closing commit `5007515` (SP1 step table, row 10a);
- cfd9059 step 9 trackers; fd664a5 step 9 findings; ac66fd0 SP2 phase file fact-checked
  at b3150c1;
- b3150c1 step 8a trackers (the commit the pre-registered runs were made from); d336933
  step 8a; 7efbaab step 8a row; 7fcc81a step 8 trackers (D-SP1-17); c2a4cf0 step 8
  pre-registration;
- 4e057c8 step 7 trackers; 6719f92 step 7; 6cf6fa4 step P trackers; e0b9fd8 merge of
  public-site; 9024d40 step P; 910c6c3 RP-1 heat source note;
- c241fe2 step 4 trackers; c8e0020 merge of sp1-step5 (step 6); 1a0b2af step 4; e19d7ed
  step 6 trackers; 9ca508b step 6; 668a59e public-repository decisions; e4f36ee LICENSE;
- 7461ef6 step 3 trackers; 04f6542 merge of sp1-step5 (step 5); 83d66dd step 3; 689ac42
  step 5 trackers; a03e218 step 5; 534557d step 2 trackers; 1fc92d3 step 2;
- 1575b79 step 1 trackers; e2fb6ab step 1; c587a08 step T trackers; 98eb5a6 step T.

**Tests and lint.** Full suite on the closing tree (the closing commit):
1299 passed (1264 fast, 35 slow) in 13 min 8 s with LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1 at the closing commit 5007515 (2026-10-04); ruff check: all checks passed; ruff format --check: 91 files already formatted; also in the SP1 session log and SP1 exit criterion 6. Step 10a adds
four tests to tests/test_animate.py: on 2026-10-04, with its edits in the working tree,
1299 tests were collected, 1264 fast and 35 slow. The run before step 10a: 1295 passed at
fd664a5, 14 min, exact golden tier, that is 1260 fast plus 35 slow (the fast count at
b3150c1: 1260 passed, 35 deselected; no file under src/ or tests/ changed between b3150c1
and fd664a5).

**Results directories** on disk. Only each directory's top-level summary.md is tracked; a
fresh clone has no CSVs and must re-run an experiment before `animate`, `replay` or the
SP2 scene can read it.

| Directory | What | Notes |
|---|---|---|
| results/silo_offload_2d/20261003T112934Z | SP1 run (git b3150c1, clean) | 4 experiment runs, 11 offload-case runs, the paired pad, 3 pad controls: 19 run folders with timeseries.csv, 72 MB |
| results/silo_offload_2d/20261003T112949Z | SP1 sweeps | 5 sweeps, 20 points; no top-level metrics.json |
| results/silo_offload_2d_readme/20261003T112956Z | SP1 bridge on the README-loads fork | 5 runs |
| results/silo_screening_2d/20260930T175743Z | Phase 2 screening run (git 7ad381f) | 12 runs; SP2's reference directory for the replay page |

Re-run times: the three SP1 commands took 14.1, 20.9 and 2.1 min run side by side
(serial estimates 30-50, 39-64 and 3-6 min); silo_screening_2d took about 27 min.
Earlier results directories are listed in the archived handoffs.

**Findings** (docs/findings/README.md): CAL-f9-leo-2d, RQ1-fuel-offload-2d (new in SP1),
RQ3-silo-screening-2d, RQ2-ignition-timing-2d, RQ6-aero-2d-preliminary, and the 1-D
records RQ3-silo-screening-1d and RQ2-ignition-timing-1d.

**Open known issues that matter to SP2:** the six it owns (section 5); KI-003 (update
`plots.CALIBRATION_RECORDS` whenever the calibration is re-run; the replay caveat reads
it); KI-020 (save subagent reports to a file at once). KI-021, KI-022 and KI-023 (stale
test comments and docstrings, owner "SP1 or later") are still open.

## 8. How work is done

docs/process/SESSION_PROTOCOL.md: the start checklist (section 3), the step loop
(section 4), the end checklist (section 7). For SP2 in particular:

- Reviewers per SP2 section 7: a physics or numerics skeptic on every code step (A1 to
  A6), a CLAUDE.md compliance auditor on every step, a visual-QA reviewer on anything
  drawn, an honesty auditor on labels and caveats.
- Pages are tested through a server on 127.0.0.1, never as local files (protocol
  section 11).
- Push main after every tracker commit and check the Pages deployment
  (`gh run list --workflow pages.yml --limit 1`).
- App runs are exploratory and never cited in docs/findings/.

## 9. Gotchas learned in SP1

New in this session. The standing list is protocol section 11.

- **Usage limits stop workflows mid-step.** On 2026-10-01 a model usage limit ended every
  agent of the step-2 workflow; the implementer's edits stayed in the tree with no report.
  Relaunch the step with an instruction to review the partial diff critically and finish
  it; never commit unreviewed partial work.
- **Parallel steps in git worktrees.** Steps 5 and 6 ran on branch sp1-step5 and step P
  on public-site, each in its own worktree, while other steps ran in the main checkout.
  `uv sync` makes a .venv per worktree; merge with `--no-ff` and re-run the full suite on
  the merged tree. Watch shared tracker files: a phase file staged while another step was
  editing it carried that step's deviations into main early (e19d7ed, SP1 session log).
- **Headless Edge screenshots.** `msedge --headless=new --screenshot` writes no file when
  started from Git Bash while Edge is running: run it from PowerShell with its own
  `--user-data-dir`. `--window-size=390` does not give a 390 px layout (headless lays out
  at about 500 px); load the page in a 390 px iframe instead. The SP1 demo screenshot was
  taken with Playwright from a 127.0.0.1 server (docs/demos/SP1/README.md).
- **The replay page's drive caveat is stale (KI-029).** It ends "Each of these favours the
  assisted runs."; under the prescribed drive the massless carriage and the missing shaft
  drag bias only energy, power and interface force, while the free kick does favour the
  silo run. site/build.py (`REPLAY_TEXT_FIXES`) rewrites it in the gallery; the demo page
  in docs/demos/SP1/ keeps it as `replay` wrote it. Fix it in replay.py and drop the site
  rewrite in the same change (SP2 risk R17).
- **Offload solves are slow.** About 90 to 110 s per stage-1 solve with its verification,
  about 30 s per pad control. The design had estimated 33 s per solved case; step 5
  measured 89 s on a loaded machine, and step 8 replaced every runtime estimate made
  from the design figure.
- **The stage-2 offload is ill-conditioned.** The stage-2 case (`silo_cold_s2`) failed its
  independent verification (its payload search returned 15.36 kg above P_ref against a
  2.6 kg tolerance) and its pad control carries its own flag. An app launch of a stage-2
  or both-stage solve should be expected to come back flagged; show the flags and the pad
  control, do not hide them.
- **Form-to-config traps.** A key present in a dict counts as given, an explicit null
  included, so the form sends only the keys of the chosen family; and a YAML merge key
  (`<<: *silo`) is resolved by the loader, so adding `exit_speed_mps` over an anchor that
  carries `net_accel_g` is refused (SP1 step 1, deviations 4 and 6).
- **Ignored file names.** `.gitignore` ignores `*_replay.html`, `*_animation.mp4` and
  `*_animation.gif` at any depth: a page or animation saved under docs/demos/ needs
  another name (the SP1 demo uses pad_vs_offloaded_silo.html). Check with `git status`.
- **The social preview is manual (KI-026).** GitHub has no API for it; the user uploads
  assets/brand/social-preview.png under Settings, General, Social preview.

## 10. Prompt to start SP2

Paste this into a fresh Claude Code session opened in this folder. It is the same text as
section 13 of docs/phases/SP2-launch-app-2d-scene.md; if the two ever differ, the phase
file's version is the one to use.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP2-launch-app-2d-scene.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links. Then read the inputs the phase file links:
> docs/phases/inputs/2026-09-30-survey-animate-replay-visuals.md and the section "SP2: local
> app and 2-D scene" of docs/phases/inputs/2026-09-30-SP1-approved-plan.md, and
> docs/findings/RQ1-fuel-offload-2d.md for the headline the app will show beside its
> caveats.
>
> We are continuing launch-assist-sim. SP1 is closed: the launch settings (silo depth with
> the exit speed or the net acceleration; the stage-1 thrust-ramp start by time, depth,
> speed, height by event and height by closed form), the fuel-offload solver with its
> `offload:` experiment block and pad controls, an in-memory entry point
> (config.resolve_experiment, sim.run_resolved, results_io.planar_experiment_result, which
> writes nothing), replay of offload runs, and the headline finding on the planar model.
> This session is phase SP2: a local app with an animated 2-D launch scene.
>
> What I want to see at the end: I run `uv run python -m launchsim app`, open the printed
> 127.0.0.1 address, set the silo depth with the exit speed or the net acceleration, choose
> where the stage-1 thrust ramp starts (any of the five ways), choose a propellant offload
> (solved or fixed; stage 1, stage 2 or both; with an optional stage-2 pre-offload) and an
> assumed structural penalty, press Launch, follow the job's progress (an offload solve
> takes minutes), and watch the pad launch and the silo launch side by side in a 2-D scene:
> the silo cross-section and carriage, the rocket to scale with its attitude and plume, tank
> levels that show the offload, release, the kick, staging with stage 1 falling away, the
> fairing halves, a camera that zooms out to Earth's curvature, a HUD, and the caveats
> beside the numbers. I also want to browse the recorded results directories (including
> SP1's results/silo_offload_2d/20261003T112934Z) and replay any planar run as a scene.
> Every app run writes a normal results directory and is labelled exploratory: no finding
> comes from it.
>
> Decisions already taken (TODO.md decisions log; phase file section 3): D-SP1-02 (a local
> app first: form, Launch button, scenes inside it); D-SP1-07, D-SP1-08 and D-SP1-18 (SP2
> now, in one fresh session that also prepares SP7, the structural mass of the push load
> and a force-limited drive, which runs after SP2 and before SP3); D-SP1-05 and D-SP1-06
> (the depth and ramp-start settings); D-SP1-03, D-SP1-04, D-SP1-09 and D-SP1-10 (offload semantics, the penalty rows,
> the offload block, the pad control: stage 1 is the only headline, and stage-2 and
> both-stage numbers are shown net of the pad control as a property of the vehicle model);
> D-SP1-01 (later 3-D models add their series without a rewrite); D-SP1-14 to D-SP1-16
> (public repository, push after every step, public face kept current); D-P2-08 (the +14.3%
> calibration miss travels with every number). The route approved with the plan: the
> standard-library HTTP server bound to 127.0.0.1, no new dependency, the CLI's resolve,
> preflight and run path in a background worker, a cached pad baseline, canvas rendering
> that reuses the replay page's clock and helpers, display-only shapes with a source or
> `assumed: true`.
>
> Follow the session protocol. Run its start checklist: confirm a clean tree, that HEAD's
> subject is "Close SP1: trackers, handoff, next phase file" and that SP1's closing commit
> named in the handoff is an ancestor; run the fast suite and record the count; check the
> entry criteria in section 4 of the phase file; run the diff of the phase file's header,
> `git diff --stat b3150c1 HEAD -- src tests configs experiments pyproject.toml .gitignore
> site/build.py`: an empty diff is the re-check of section 6 (record it in the session
> log), and if it lists files, re-check those files against section 6 before planning from
> it; list the open known issues and backlog items whose owner is SP2 in TODO.md (at SP1's
> close: KI-002, KI-016, KI-017, KI-018, KI-019 and KI-029, the replay drive-caveat wording
> of section 5.8 item 5). If the session starts in
> Plan mode, do the read-only checks first and run the suite right after approval, as the
> protocol's section 3 says.
>
> Then work in Plan mode (step A0). Put the questions of section 10 to me, each with your
> recommendation first and the trade-off in one line, and give the ambitious option fairly
> with its cost: Q1 the HTML scene export (the only way to put a scene on the public site)
> and video; Q2 an offline page, fonts and brand; Q3 where app runs are kept; Q4 the
> presets; Q5 the vehicle; Q6 the offload input; Q7 the look. Settle the open design points
> of section 10 (what a fixed-offload launch shows, thread or child process, how the cached
> baseline enters the run path, the git provenance of a long-running server, A1's
> compatibility policy for the moved names, progress granularity, the exploratory label,
> the default run selection of an offload directory, brand assets in the package, whether
> SP2 takes the replay drive-caveat fix). Show me one static mock-up frame of the scene
> and one of the app page inline in the chat, then the detailed design, the step table
> with gates, and the exit criteria with their tolerances, and wait for my approval before
> writing any code.
> After approval, log the decisions as D-SP2-nn in TODO.md, save the design under
> docs/phases/inputs/, and make the start commit ("Start SP2: status in progress").
>
> Run every step of the table through the loop: implementer; adversarial reviewers (a
> physics or numerics skeptic on every code step, A1 to A6; a CLAUDE.md compliance auditor
> on every step; a visual-QA reviewer on anything drawn who checks the page state against
> the run's CSV through a server on 127.0.0.1; and an honesty auditor on labels and
> caveats); up to two fix rounds; an independent gate; one commit per
> gate; the tracker commit at once ("SP2 step <k>: trackers (<hash>)"); then `git push
> origin main` and a check that the Pages deployment succeeded. Step A1's first action,
> before any edit, is the reference replay page of section 7 and its sha256. Standing gates:
> fast suite green, ruff clean, golden 1-D, the planar digest pin and the planar output
> capture unchanged, no shipped experiment or vehicle file changed. An offload launch takes
> minutes (about 90-110 s per solve with its verification on this machine, plus about 30 s
> per pad control), so it runs in a background worker with progress and the page never
> blocks. Do not change the equations of motion, frames, events, integrator settings, loss
> accounting, search, guidance or the offload solver; a reader-side fix is preferred over
> any change to what the planner logs. Never delete or overwrite a results directory.
>
> At the end, run the end checklist: an independent gate on each of the 14 exit criteria (a
> criterion stays open only with my explicit acceptance, logged as a decision), the full
> suite, the demo recorded under docs/demos/SP2/ (pages served through 127.0.0.1,
> screenshots in light and dark mode, the visual-QA table), CLAUDE.md (commands, layout, the
> modules allowed to do I/O, the status line), the README quick start and status, the user
> manual, TODO.md and the program board, and the public face: the landing page, the deck and
> its PDF, the gallery (with an exported scene if Q1 chose the export) and the manual, with
> the site built locally and no broken link. Then put the close-out questions to me, with
> the recommendation first (which phase runs next, SP7 in the planned order, D-SP1-18),
> fact-check the next phase's file (SP7 in the planned order, or the phase I choose)
> against the code, archive the handoff and write the
> new one with the prompt for that phase, update the memory,
> have the cold-read check done, make the closing commit, push, and confirm the Pages
> deployment. Report anything that undercuts the hypothesis, and anything the scene would
> show that the model does not support, as plainly as the rest.
