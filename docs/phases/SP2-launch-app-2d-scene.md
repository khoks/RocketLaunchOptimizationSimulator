# SP2: Local app and 2-D launch scene

Status: in progress (session 2026-10-05)

Written 2026-09-30 in the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md), section
"SP2: local app and 2-D scene") and the code survey
([inputs/2026-09-30-survey-animate-replay-visuals.md](inputs/2026-09-30-survey-animate-replay-visuals.md)).
Fact-checked by the SP1 session on 2026-10-03 (SESSION_PROTOCOL.md section 7, item 8)
against the code at commit b3150c1 (SP1 step 8a's tracker commit, the commit SP1's
pre-registered runs were made from). Section 6 is re-checked line by line, sections 1-5,
7-10 are corrected for what SP1 actually built, and the prompt in section 13 is final.
SP1 steps 9 and 10 were planned to change only documents and results summaries. They did
not quite: step 10a, added at SP1's close, changed src/launchsim/plots.py,
src/launchsim/replay.py and tests/test_animate.py (`animate` for offload runs), and the
public-face refresh changed site/build.py. The diff below lists those four files.
Amended 2026-10-04 at SP1's close-out for decision D-SP1-18: the phase after SP2 is SP7
(the structural mass of the push load and a force-limited drive), not SP3, in sections 2,
3, 7, 8, 10 and 13.

The re-check of section 6 at SP2's start. Protocol section 3, item 5 re-checks the
inventory whenever its stated commit is not HEAD. At SP2's start HEAD is SP1's bookkeeping
commit ("Close SP1: trackers, handoff, next phase file"), never b3150c1, so the literal
rule always fires although only documents changed. For this phase the trigger of item 5
is this diff, over every path section 6 inventories:

    git diff --stat b3150c1 HEAD -- src tests configs experiments pyproject.toml .gitignore site/build.py

If it lists nothing, the commits since b3150c1 touched none of the inventoried files, the
line numbers of section 6 hold at HEAD, and the session log records the empty diff as the
re-check. If it lists files, those files are re-checked before planning from section 6.
Entry criterion 8, section 6, risk R1 and the prompt in section 13 all mean this command.
How a session runs: [../process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md).
Program board: [README.md](README.md).

This file is a brief, not the detailed design. The detailed design is made in SP2's own
Plan mode (step A0) and approved by the user before any code is written.

Started 2026-10-05. On 2026-10-05, in step A0, the user answered Q1 to Q7 (section 10) and
approved the design saved as
[inputs/2026-10-05-SP2-design.md](inputs/2026-10-05-SP2-design.md), with decisions D-SP2-01
to D-SP2-38 (section 3; full text in TODO.md). That design supersedes sections 5, 7 and 8
of this file where they differ. Section 7 and section 8 below now hold the approved step
table and exit criteria. Sections 1 to 5 are kept as the brief they were: read them for
the background and the constraints, and the design for what is built. Section 6 has a
re-check at b69ff0c at its top and keeps its older tables as written. Section 12 lists
what the design changed against this brief. The design's sources are saved beside it: nine
survey reports ([inputs/2026-10-05-SP2-survey/](inputs/2026-10-05-SP2-survey/README.md)),
six reviews of its first draft
([inputs/2026-10-05-SP2-review/](inputs/2026-10-05-SP2-review/README.md)) and the two
mock-ups the user approved
([inputs/2026-10-05-SP2-mockups/](inputs/2026-10-05-SP2-mockups/README.md)).

## 1. Goal and what you can see at the end

The user's request, in their words (the first handoff, section 1; archived as
[../handoff/archive/2026-09-30-phases-0-2.md](../handoff/archive/2026-09-30-phases-0-2.md)):

> Now enhance the simulator so that it can show the rocket actually getting launched in
> different configurations, in 2-D and then in a 3-D world. It will be intriguing to see it
> happen instead of seeing graphs only. I want to configure the depth from which the rocket
> is launched inside the silo. I want to configure when the rocket's thrust ramp-up starts
> [...] the system should let me reduce the amount of rocket fuel.

**Goal.** A local app, started with `uv run python -m launchsim app`, in which the user:

- sets the silo depth (`stroke_m`) with either the exit speed or the net acceleration;
- sets where the stage-1 thrust ramp starts, in any of five ways: by time (from release or
  from push start), by depth on the push, by speed on the push, by height above the mouth
  found by an event, by height above the mouth from the closed form;
- sets a propellant offload as SP1 defines it: solved (the largest offload of stage 1,
  stage 2 or both that still carries the full-load pad's payload to the 200 km orbit) or
  fixed (tonnes, or a fraction of a stage's load), with an optional stage-2 pre-offload
  before a stage-1 solve, and an assumed structural penalty (extra stage-1 dry mass on the
  assisted run);
- presses Launch, follows the job's progress (an offload solve takes minutes, section 5.6),
  and watches an animated 2-D scene of the pad launch and the silo launch side by side;
- browses the recorded run directories under `results/`, SP1's offload directories
  included, and replays any planar one as a scene.

**What you can see at the end.**

- The app page at `http://127.0.0.1:<port>/`: a form, a Launch button, a progress line, a
  results panel with the caveats beside the numbers, and the scene, in the project's brand
  (section 5.10).
- The scene: a silo cross-section with rings and a carriage, the rocket drawn to scale with
  its attitude, a plume that follows the thrust, tank fill levels (an offloaded stage starts
  visibly part-full), hold-down and release, the kick, staging with stage 1 falling away,
  the fairing halves, a camera that goes from the close-up to Earth's curvature, and a HUD.
- A normal results directory for every launch, labelled exploratory.
- A recorded demo under `docs/demos/SP2/`.
- The public face refreshed at the close (protocol section 7, item 6): the user manual
  gains the `app` command, the landing page and deck say the app exists, and the gallery
  shows a scene (an exported page if Q1 chooses the export; the Pages site is static and
  cannot run the app).

What SP2 does not show: anything in 3-D (SP4), and no new research number. A number seen in
the app is exploratory; findings come only from committed experiment files run from a clean
tree. The headline the app shows beside its caveats is SP1's, in
[../findings/RQ1-fuel-offload-2d.md](../findings/RQ1-fuel-offload-2d.md) (written in SP1
step 9).

## 2. Scope and out of scope

**In scope**

1. A shared, read-only run-directory module used by `animate`, `replay`, the scene and the
   app (one loader instead of three, one JSON/YAML reader pair instead of four copies, one
   output-path rule).
2. A display-only geometry block for the vehicle, the pad and the silo, every number with a
   source or `assumed: true`. It is never read by the run path.
3. The scene data payload: the extra time-series fields, an event-aligned time grid, tank
   levels, the rebuilt separation states, the display-only paths of the spent stage and the
   fairing halves.
4. The 2-D scene renderer (canvas, no library), reusing the replay page's clock, scrubber,
   run toggles, telemetry and caveats.
5. The app: a standard-library HTTP server bound to 127.0.0.1, a job runner in a background
   worker that uses the same resolve, preflight and run path as the CLI (SP1's in-memory
   path, section 5.6), a cached pad baseline, progress reporting, the form, the launch flow,
   the run browser.
6. The fixes listed in section 5.8 (fairing event mass convention, output-path rule
   mismatch, private helpers, housekeeping), and, if A0 takes it as a scope line, the
   replay drive-caveat wording (section 5.8 item 5).
7. Tests for the payload, the server API and the form-to-config mapping; visual QA against
   run data; the demo; the trackers, CLAUDE.md (commands, layout, the list of modules allowed
   to do I/O), the README quick start (README.md line 37 says "There is no graphical
   interface") and the user manual (docs/manual/02-quick-start.md says there is no
   graphical interface yet; docs/manual/07-commands.md gains `app`, and `scene` if Q1
   chooses it).
8. Closing the phase per the session protocol: the public face refreshed (landing page,
   deck and its PDF, gallery, manual; the site built with no broken link), main pushed and
   the Pages deployment checked, the next phase's file fact-checked (SP7 in the planned
   order, D-SP1-18, or the phase the user chooses at close-out; protocol section 7,
   item 7), the handoff and prompt for that phase, memory.

**Out of scope**

- 3-D of any kind: the globe scene is SP4, the 3-D dynamics are SP3, SP5 and SP6.
- Any change to the equations of motion, frames, integrator settings, loss accounting,
  search, guidance, the offload solver or the reporting of the `offload:` block. SP2 reads
  results; it does not change how they are produced. The one place where SP2 could touch
  event logging is the fairing event's mass convention; the recommended route (section
  5.8) fixes it in the reader and leaves the validated planner alone.
- New assist models, a throttle, a structural-mass model (README Phase 3).
- New findings. No app run is cited in `docs/findings/`.
- Sweeps from the form, and the offload block's sensitivity arms (each arm is another
  solve). One Launch runs one configuration against the pad.
- Remote access, accounts, several users, a job queue. The server listens on 127.0.0.1 only
  and runs one job at a time.
- Hosting the app publicly. GitHub Pages serves static files only; the public site can
  carry an exported scene page, screenshots or a recording (Q1), not the app.
- Editing a shipped experiment or vehicle file. The app builds its experiment in memory.
- Video export of the scene, unless the user asks for it in A0 (section 10, question Q1).

## 3. Decisions already taken

Decision ids are defined in TODO.md's decisions log; the text there is authoritative.

| Id | What it fixes for SP2 |
|---|---|
| D-SP1-02 | The visual tool is a local app first: form, Launch button, scenes inside it |
| D-SP1-07 | Order: SP2 comes after the settings, the offload solver and the planar headline (SP1), and before any 3-D work |
| D-SP1-08 | One fresh session for SP2; it is tested, refined and completed before SP7, the phase after it by D-SP1-18; it prepares SP7's documents, memory and prompt |
| D-SP1-18 | Order after SP2: SP7 (the structural mass of the push load and a force-limited drive), then the 3-D phases SP3-SP6. SP2's close-out fact-checks SP7's phase file and writes its prompt |
| D-SP1-05 | Form: `stroke_m` with exactly one of `net_accel_g` or `exit_speed_mps` |
| D-SP1-06 | Form: the ramp start by time; by depth or speed on the push; by height above the mouth by event; by height by closed form |
| D-SP1-03 | Form: offload of stage 1, stage 2, or both; tanks partly filled, dry mass unchanged; fixed payload = the full-load pad's payload capacity on the same vehicle and 200 km orbit |
| D-SP1-04 | Form: the structural penalty is an assumed extra stage-1 dry mass on the assisted run (+2, +4, +8.1 t are the rows SP1 reports) |
| D-SP1-09 | The offload is an `offload:` block and a post-pass inside `results_io.planar_experiment_result`, so the app passes it in the experiment dict; no `search.figure_of_merit` value changes |
| D-SP1-10 | Every offload mode is also solved on the pad; stage-2 and both-stage numbers are shown net of the pad control and labelled a property of the vehicle model; stage 1 is the only headline. The config refuses a stage-2 or both solve without `pad_control: true` |
| D-SP1-01 | 3-D is true dynamics in later phases; SP2 builds the run-data module and the payload so that a later model's time series (a superset of the planar columns) can be added without a rewrite |
| D-SP1-14, D-SP1-15, D-SP1-16 | The repository is public (all rights reserved); main is pushed after every step's tracker commit and at the phase close; the Pages site, deck, gallery and user manual are kept current at every phase close |
| D-P2-08 | The calibration miss (+14.3%) is accepted and travels with every number the app shows |

Approved with the plan as the route for SP2, details to confirm in A0:

- `launchsim app` on 127.0.0.1 with Python's standard-library HTTP server; no new dependency.
- Launch runs the same resolve and run path as the CLI, in a worker, and writes a normal
  results directory.
- The pad baseline is cached.
- App runs are labelled exploratory; findings come only from committed experiment files.
- The scene is drawn on canvas and reuses the replay page's clock, scrubber, run toggles,
  telemetry and caveats.
- Shapes are a display-only block with sources or `assumed`; the spent stage's path is a
  display-only ballistic coast from the staging event state.

Built in SP1 for SP2 (D-SP1-02, SP1 step 7): an experiment given as an in-memory dict runs
through `config.resolve_experiment(exp_dict, vehicle_dict)`, `sim.run_resolved` (baseline
and variants) and `results_io.planar_experiment_result(...)`, which returns the whole
`ExperimentResult`, the offload report included, and writes nothing; `results_io.write_run`
then writes it. Tested by
`tests/test_offload_pipeline.py::test_offload_in_memory_writes_nothing` (slow tier).

Standing rules that bind the design (CLAUDE.md): the calibrated vehicle file is never edited;
a results directory is never overwritten and nothing in `results/` is deleted without asking;
no magic numbers outside `constants.py` and configs; I/O lives only in the listed modules;
every new dependency is justified in one line; caveats are reported as plainly as results;
public text follows the same honesty rules and never calls the project open source.

**Decisions of SP2's own planning (2026-10-05, step A0).** D-SP2-01 to D-SP2-08 are the
user's answers to Q1 to Q7 (section 10); D-SP2-09 to D-SP2-38 are design decisions the
user approved with the plan. One line each; the text in TODO.md's decisions log is
authoritative, and the reasons and measurements are in the design
([inputs/2026-10-05-SP2-design.md](inputs/2026-10-05-SP2-design.md), section 3).

| Id | What it decides |
|---|---|
| D-SP2-01 | Q1: a standalone HTML export of the scene (`launchsim scene`) and a video export are in SP2 |
| D-SP2-02 | Q2: the app and the scene work offline with system fonts; the replay page stays as it is |
| D-SP2-03 | Q3: app runs go to `results/app/<UTC timestamp>/`, and each summary.md is tracked |
| D-SP2-04 | Q3 follow-up: app summaries carry an exploratory banner and are committed at step boundaries and before any pre-registered run |
| D-SP2-05 | Q4: the presets are SP1's configurations plus the Phase 2 screening variants |
| D-SP2-06 | Q5: the gate vehicle only |
| D-SP2-07 | Q6: fixed and solved offloads; the stage-2 and both-stage forms under Advanced, with the pad control forced on |
| D-SP2-08 | Q7: a schematic cross-section as in the mock-up, light and dark |
| D-SP2-09 | One daemon worker thread in the server process; one job at a time; no cancel |
| D-SP2-10 | The cached pad: app code composes the public pieces in `run_experiment`'s order (results_io.py unchanged); the key is a digest of the baseline's run dict, the vehicle dict and the server-start git state; each hit is re-wrapped |
| D-SP2-11 | Provenance: the git state is read once at server start and stored beside the launch-time state; a launch is refused when src, configs, experiments, pyproject.toml or uv.lock changed since the start |
| D-SP2-12 | Exploratory marking: a third experiment label value, `exploratory`, a banner in summary.md with both git states, and one line in the replay and animation caveats of that directory |
| D-SP2-13 | A1's compatibility policy: `run_data.RunDataError`; the old names stay in plots and replay; the ffmpeg test and `plots.calibration_caveat` stay in plots; cli.py is not edited in A1; existing tests unchanged |
| D-SP2-14 | KI-017: one output-path rule (replay's stricter one) for animate, replay and scene |
| D-SP2-15 | KI-016: fixed in the reader (`read_events` returns every row; `with_drop_masses` adds the mass before and after each drop for the four fairing cases); the planner is not touched |
| D-SP2-16 | The scene's time grid is a selection of CSV rows, never a resample |
| D-SP2-17 | Attitude: drawn along `pitch_rad` while thrust is on, in the hold and on the track; the drawn angle is held when unpowered |
| D-SP2-18 | Display geometry in `configs/display/` (`f9_class.yaml`, `scene.yaml`), read only by a new pure module `display.py`; an import-guard test keeps display, scene and app out of the run path |
| D-SP2-19 | Spent stage and fairing halves: a numerical vacuum coast from the rebuilt event state; display-only |
| D-SP2-20 | Carriage after release: drawn braking at `brake_decel_g` over `braking_distance_m` on rails above the release point; outlines on a run that ends in impact |
| D-SP2-21 | Player code: seven replay helpers copied verbatim and pinned by a test; the scene has its own rate law; replay.html is not edited in SP2 |
| D-SP2-22 | The app shows the scene in a same-origin iframe of the server-rendered scene page; the page in the app is the exported page |
| D-SP2-23 | Step A1a, before the scene: caveat wording fixed at source in replay.py (KI-029 and more), so replay and scene share one caveat source; site/build.py keeps only its three template canvas patches and its editorial additions |
| D-SP2-24 | KI-018: Pillow is declared in the dev extra |
| D-SP2-25 | Progress: the five stages the app owns, with elapsed time and an expected range; no callback in results_io.py or offload.py; every solve launch runs its pad control; only the pad is cached |
| D-SP2-26 | App launches write no PNG plots |
| D-SP2-27 | A fixed offload is labelled "imposed offload", never "saved"; the panel shows P* - P_ref with its reading; no fly-out at P_ref |
| D-SP2-28 | Default pair for any directory: the baseline on the left; on the right the first solved stage-1 case, else the first assisted variant that is not a yardstick, else one full-width panel |
| D-SP2-29 | The command: port 8765, `--port N` (0 = a free port), `--open`, `--results-root PATH`; the URL is printed as http://127.0.0.1:<port>/ |
| D-SP2-30 | Video: MP4 through ffmpeg only, by frame-stepped capture from the app page; no GIF from the app |
| D-SP2-31 | Requests: whitelisted keys, enumerated choices, real booleans, finite bounded numbers; the experiment is built from a frozen basis; a launch keeps a committed name only when its resolved configuration equals the committed one |
| D-SP2-32 | Server guard: a per-route policy table, tested by raw sockets; neither new template assigns HTML from data |
| D-SP2-33 | Brand: the app page inlines the logo mark and a data-URI tab icon, each compared with its file by a test; the scene page carries the tab icon only |
| D-SP2-34 | replay.html does not take the site's contrast tokens in SP2; KI-019 is re-owned to the phase that next edits replay.html |
| D-SP2-35 | Each panel has a fixed-scale close-up of the vehicle beside the true-scale view, which shows the rocket while its body is at least 3 px wide and a marker after that |
| D-SP2-36 | The results panel and every caveat are built from the directory shown; SP1's headline lives in one constant checked against the findings note; a launch equal to a committed case says "a reproduction, not new evidence" |
| D-SP2-37 | Commits: app summaries are results and go in their own commit; reviewers and gates launch into a scratch results root; only the demo launches go to results/app/ (amends the session protocol, section 4) |
| D-SP2-38 | Exit criteria: 17 (section 8), with the changes against the brief's 14 listed there |

Not taken (design, section 3): vendored or Google fonts (Q2); the README-loads vehicle
(Q5); a cancel button; sensitivity arms and sweeps from the form; a CLI video command; a
GIF from the app.

## 4. Entry criteria

All of these are true before the SP2 session writes code. The session checks them at its
start and records the check in section 11. The state given for each is the fact-check of
2026-10-03 at b3150c1.

1. SP1 is closed: `docs/phases/README.md` shows SP1 done with its closing commit, and each
   of SP1's eight exit criteria passed its gate or carries a user-accepted, logged miss.
   (2026-10-03: SP1 steps 9 and 10 still open.)
2. The settings exist and their tests pass (all present at b3150c1):
   - `assist.exit_speed_mps` as the alternative to `assist.net_accel_g`, exactly one of the
     two (`ConstantAccelConfig`, config.py 613; `ASSIST_KEY_FAMILIES` 88); tests in
     tests/test_config.py and tests/test_silo.py;
   - the stage-1 ramp start in one of four key families (`IgnitionConfig`, config.py 761;
     `IGNITION_KEY_FAMILIES` 91): `t_ign_s` with `reference: release | push_start`,
     `at_depth_m`, `at_speed_mps`, or `at_height_m` with `height_method: event |
     closed_form`. Depth, speed and height are for the first stage of a `constant_accel`
     run only; depth, speed and the closed-form height convert to a time before the run
     (`phases.prelude.resolve_ignition`); the event form fires the `ignition_height` event
     (prelude.py 84) and fails with `no_ignition` if the apex comes first; tests in
     tests/test_config.py, tests/test_silo.py, tests/test_height_event.py;
   - the `offload:` experiment block (`OffloadConfig`, config.py 1709): `reference` (the
     baseline), `cases` (each `name`, `of` a variant, exactly one of `solve: stage1 |
     stage2 | both` or `fixed:` with one of `stage1_t`, `stage1_fraction`, `stage2_t`,
     `stage2_fraction`, `both_fraction`; optional `stage2_offload_t` on stage-1 cases,
     `stage1_dry_mass_added_t`, `paired_pad`, which is refused together with a penalty),
     `pad_control` (required by a stage-2 or both solve), `sensitivity_of`, `energy`
     (sourced fuel split and heating value); `SweepConfig.offload` for sweeps; tests in
     tests/test_offload.py and tests/test_offload_pipeline.py;
   - the preflight `sim.check_resolved` (sim.py 932), called by `results_io.run_experiment`
     (results_io.py 831) and `run_sweep` (2143) before the directory is made, and by
     `cli.load_experiment` (cli.py 273), so a refused configuration writes nothing.
3. The in-memory entry point of section 3 exists and SP1 tests it
   (`test_offload_in_memory_writes_nothing`, slow). There is no single wrapper function:
   the caller composes the pieces. `results_io.run_experiment` still always runs the
   baseline (section 5.6).
4. `launchsim replay` accepts a results directory that holds offload runs: role `offload`
   (`replay.ROLE_OFFLOAD`; `run_source` reads metrics.json `offload.runs` and
   resolved_config.yaml `offload_runs`; `offload_note` says what each offload run is);
   tests `test_replay_shows_an_offload_run_beside_the_pad` (fast) and
   `test_offload_outputs_written_and_replayed` (slow) in tests/test_offload_pipeline.py.
   Offload runs are not in the default selection (the baseline plus three variants); they
   are named with `--runs`. Checked on 2026-10-03:
   `replay results/silo_offload_2d/20261003T112934Z --runs pad silo_cold_s1 silo_cold_s1__pad pad__offload_stage1`
   wrote a 298,591-byte page.
5. The planar metrics the form, the results panel and the HUD read exist (metrics_planar.py):
   `PUSH_SETTING_METRICS` (933: `stroke_m`, `net_accel_mps2`, `net_accel_g`, written by
   `planar_track_metrics` 963 beside `exit_speed_mps`, `push_time_s`,
   `braking_distance_m`, `facility_length_m`, `track_start_altitude_m`,
   `carriage_mass_kg`); `RAMP_START_METRICS` (1029: the achieved
   `ramp_start_t_rel_release_s`, `_alt_m`, `_depth_m`, `_height_m`, `_speed_mps`, `_phase`,
   on every recorded planar run); `RAMP_START_REQUEST_METRICS` (1041: `ramp_start_trigger`
   and `ramp_start_requested_{t_s, depth_m, speed_mps, height_m}`, written only when a
   trigger is set); `OFFLOAD_METRIC_KEYS` (1225) on offload runs.
6. Run data is on disk (CSV files are not tracked in git; all present on 2026-10-03):
   - `results/silo_screening_2d/20260930T175743Z` (12 runs with `timeseries.csv`), or a
     re-run of it;
   - SP1's pre-registered run `results/silo_offload_2d/20261003T112934Z` (git b3150c1,
     clean): 4 experiment runs, 11 offload-case runs, one paired pad and three pad
     controls, 19 run folders with `timeseries.csv`, 72 MB; the sweep
     `results/silo_offload_2d/20261003T112949Z` (5 sweeps, 20 points, no top-level
     metrics.json); the bridge `results/silo_offload_2d_readme/20261003T112956Z` (5 runs).
     On a fresh clone, re-run them from SP1's closing commit first (section 5.6 gives the
     wall-clock times).
7. The tree is clean; `uv run pytest -q -m "not slow"` is green; ruff is clean; the golden
   1-D tests, SP1's planar digest pin
   (`tests/test_config_planar.py::test_shipped_planar_resolved_dicts_match_the_pinned_digests`)
   and the planar output capture
   (`tests/test_planar_pipeline.py::test_written_outputs_keep_the_captured_structure`) pass.
   (2026-10-03: at b3150c1 the fast suite gives 1260 passed and 35 deselected, ruff check
   and format are clean, and the golden 1-D tests and both pins are fast-tier tests of
   that run. The tree is not clean yet: it becomes clean when SP1 steps 9 and 10 commit
   their findings, results summaries and documents.)
8. Section 6 of this file has been re-checked against the code and the prompt in section 13
   finalised by the SP1 session: done at b3150c1 on 2026-10-03 (header); the SP2 session
   runs the diff of the header (`src tests configs experiments pyproject.toml .gitignore
   site/build.py`). At SP1's close it lists site/build.py, src/launchsim/plots.py,
   src/launchsim/replay.py and tests/test_animate.py (SP1 step 10a and the public-face
   refresh; handoff section 5). Those files, and any other the diff lists, are re-checked
   against section 6 before planning from it, and the re-check is recorded in the session
   log.
9. The public repository is current: main pushed after SP1's closing commit and the last
   Pages deployment green (`gh run list --workflow pages.yml --limit 1`); `gh` is
   authenticated, because SP2 pushes after every step (protocol section 4, item 7).
   (Depends on SP1's close-out.)
10. Tools: a browser reachable through 127.0.0.1. Optional: node (for `node --check` of the
    page scripts; the test is skipped without it) and ffmpeg (only if video export is
    chosen). For the site build at the close: `uvx --with markdown==3.11 python site/build.py`.

## 5. Design

The brief below is what the plan approved plus the constraints the survey found, corrected
for what SP1 built. Full text: the plan's section "SP2: local app and 2-D scene" and the
survey's sections 1-10 and its "Recommendation" (line numbers there are for 2eebcae; section
6 of this file has the current ones). Items marked "proposed" are this file's suggestions for
A0 to confirm.

### 5.1 Shape of the system

    browser page (form, scene)                         127.0.0.1 only
        |  GET page, GET run list, GET scene payload, POST launch, GET job status
    app server (standard library)
        |-- job runner (one background worker; progress by stage)
        |       form values -> experiment dict (in memory; shared blocks and the offload
        |                      energy block copied from a committed experiment)
        |       -> config.resolve_experiment -> check_result_names -> check_resolved
        |          (the preflight; nothing is written if it refuses)
        |       -> make_run_dir -> sim.run_resolved (the pad from the cache) for the
        |          baseline and the variant -> results_io.planar_experiment_result
        |          (comparison, offload post-pass) -> write_run
        |       -> results/<root>/<UTC timestamp>/   (a normal results directory)
        |-- run-data module (read-only): directories, CSV, metrics, config, events
        |-- scene module: payload (JSON) from a results directory + display geometry
    scene template (canvas): clock, scrubber, camera, drawing, HUD, caveats

The scene never reads simulator objects. It reads a results directory, the same way for a
run launched a minute ago and for a run recorded last week. That keeps one code path and
makes every scene reproducible from files.

### 5.2 Shared read-only run-data module

Proposed name `src/launchsim/run_data.py` (I/O, read-only). The survey recommends it over
`results_io.py`, which is the writer side and imports `compare`, `summary` and `plots`. It
takes over:

- one `read_json` / `read_yaml` pair (today: `plots._read_json`/`_read_yaml`,
  `replay._read_json`/`_read_yaml`, plus `cli.load_yaml` with a different error type);
- `results_tree`, `is_inside`, `protected_tree`, `default_output_path(run_dir, cwd, suffix)`
  and `check_output`, with one rule for `animate`, `replay` and the scene page writer
  (and the export, if Q1 chooses it; section 5.8);
- the planar-directory check with a configurable error type (today `check_planar_run_dir`
  and `check_replay_run_dir` do the same work; only the replay one tells a sweep point from
  a 1-D run);
- run discovery and selection (`animation_run_names`, `select_runs`), `run_source` (the role
  of each run folder: run, bound, paired baseline, case, and offload, which SP1 step 7
  added with `offload_note`), `read_series`, and `read_events` returning every row with the
  mass before and after a drop;
- the resampling helpers (`replay_grid`, `defined_mask`, `series_values`, `run_series`),
  taking the field list as an argument so the scene can add fields;
- the calibration data: `CALIBRATION_RECORDS` (two vehicles since SP1 step 8a: the gate
  fork `generic_f9_class_2d` and the README-loads fork), `CALIBRATION_BAND`,
  `CALIBRATION_BAND_EDGE_REL_TOL`, `CALIBRATION_GATE_VEHICLE`, `calibration_gap` and
  `inside_calibration_band`. SP1 step 8a already moved these into `plots.py` and both
  caveats read them; the two caveat texts still differ (section 5.8 item 3).

`plots.py` and `replay.py` switch to the public names. None of today's loaders carries
`pitch_rad`, `thrust_N`, `thrust_vac_N`, `stage`, the track columns, the assist geometry or
the vehicle masses (`replay.REPLAY_COLUMNS` is animate's nine columns plus `gamma_rel_rad`
and `mach`); the scene payload adds them.

Compatibility policy for A1 (proposed; A0 confirms). Other code and many tests use the
names that move (section 6, "Users of the names A1 moves"):

- The old module-level names stay importable from `plots` and `replay` as re-exports of
  the run-data names, the private ones the tests call included (`replay._finite`,
  tests/test_replay.py 506). The existing tests then run unchanged.
- `results_io.py` keeps `from launchsim.plots import CALIBRATION_RECORDS, write_plots`
  (143; used at 1798 for the offload caveats) through that re-export, so results_io.py is
  not one of A1's files. `summary.offload_calibration_caveat` takes the record as an
  argument and names `plots.CALIBRATION_RECORDS` only in its docstring (1534).
- The two calibration sentences stay in their modules: `plots.calibration_caveat` (the
  animation footnote) and `replay.calibration_caveat` (the replay page). They are wording
  of their own outputs, and A1's byte-identical gate forbids unifying them (section 5.8
  item 3). Only the data and the helpers move: `CALIBRATION_RECORDS`,
  `CALIBRATION_BAND`, `CALIBRATION_BAND_EDGE_REL_TOL`, `CALIBRATION_GATE_VEHICLE`,
  `calibration_gap`, `inside_calibration_band`.
- `plots.calibration_caveat` keeps reading the name `CALIBRATION_RECORDS` from the plots
  module at call time. Then `tests/test_animate.py::test_calibration_band_includes_both_edges`
  (353: `mp.setattr(plots, "CALIBRATION_RECORDS", edge)`, then
  `plots.calibration_caveat("edge_2d")`) still sees its patch. A function moved into
  run_data would not. If A0 moves a caveat function anyway, that test is changed to patch
  `run_data.CALIBRATION_RECORDS`, as a logged deviation.
- Any other edit of an existing test is a logged deviation too. The one intended change of
  behaviour, animate's output-path rule (section 5.8 item 2), gets new tests. By reading,
  the animate path tests at b3150c1 (tests/test_animate.py 180-195 and 460-468) also hold
  under the stricter rule, because replay's `protected_tree` covers the run's own tree as
  well as any folder named results.

Constraint for later phases: the module keys its column sets by the run's `model`, so SP4
can add the spatial model's series (a superset of the planar names, per the 3-D design)
without changing the planar path.

### 5.3 Scene data payload

Built by a new `src/launchsim/scene.py` (proposed) from one results directory and a list of
run names. It keeps the replay's injection pattern: a single token in the template (a new
one, such as `__SCENE_DATA__`), `json.dumps(..., allow_nan=False, ensure_ascii=True)`, `<`
escaped, NaN written as null. The app serves the same payload as JSON.

Per run, beyond the replay's eight fields:

| Field | Source | Use in the scene |
|---|---|---|
| attitude | `pitch_rad` (thrust direction above local horizontal; pi/2 in HOLD; the track angle in ASSIST; along v_rel when unpowered; unwrapped per run, `metrics_planar.UNWRAPPED_COLUMNS`) | rocket rotation; wrapped for display |
| thrust state and size | `thrust_vac_N`, `thrust_N` | plume on or off and its length |
| stage | `stage` | which bodies are attached |
| track | `s_m`, `drive_force_N`, `interface_force_N`, `drive_power_W` (NaN outside ASSIST) | carriage position, HUD |
| mass | `m_kg` with the run's vehicle masses and payload | tank fill levels |
| events | every row of `events.csv`, with pre- and post-drop mass | markers, staging, fairing, hold-down release |
| assist geometry | config `assist.stroke_m`, `assist.track.exit_altitude_m`, `assist.track.angle_deg`, `assist.carriage_mass_t`, `assist.brake_decel_g`; metrics `braking_distance_m`, `facility_length_m`, `track_start_altitude_m`, `exit_speed_mps` | silo drawing |
| ramp start | metrics `ramp_start_*` (requested and achieved) | the ignition marker and its label |
| separated objects | rebuilt from the `staging` and `fairing` event rows (section 5.5) | spent stage and fairing paths |
| display geometry | the display block (section 5.5) | shapes |
| offload caveats | the directory's `metrics.json` `offload.caveats` (written per directory by results_io.py 1798: the vehicle's calibration caveat first, then the caveats as worded when the directory was written) | the caveat list beside an offload run's numbers (section 5.5) |

Design constraints from the survey and from SP1's outputs:

- **Time grid.** The replay samples every 0.1 s until 40 s after release, then every 1 s,
  and interpolates linearly. A scene has steps that must not be smeared: the mass drop at
  staging, thrust off at MECO, the stage label. Proposed: the grid also contains every event
  time, and step-like fields (`phase`, `stage`, thrust on or off) take the last row at or
  before the sample instead of an interpolated value. Phase boundaries are written twice in
  the CSV; the loader keeps the last of the duplicates, as replay does.
- **Tank levels.** The time series holds one stack mass. Propellant left in a stage is that
  mass minus everything else still attached, using the run's own vehicle block and the
  run's own payload, not the vehicle file's nominal payload.
  - Vehicle block. A run's entry in `resolved_config.yaml` is `runs.<name>`,
    `bound_runs.<name>`, `cases.<name>` or, for an offload run, `offload_runs.<name>`.
    Every entry carries `run`. It carries `vehicle` only when the run's vehicle differs
    from the experiment's top-level `vehicle` block: one rule for all four
    (`results_io._run_entry`, 625, and the same test inline for `runs`, 597-599). The
    payload builder falls back to the top-level `vehicle` block when an entry has none.
    An offloaded run's own block restates `propellant_mass_t` (and the raised
    `dry_mass_t` of a penalty row), marked `assumed: true` with a note giving the
    vehicle's full value. A run whose offload ended at 0 kg has no block of its own: in
    20261003T112934Z, `offload_runs.pad__offload_stage1` (`no_offload`) and
    `pad__offload_both` (`ok`, 0.0 kg) hold `run` only, and the other 13 offload runs
    carry `vehicle`.
  - Payload. The run's `payload_kg` from `metrics.json` (offload runs:
    `offload.runs.<name>`). A solved case's recorded run flies P_ref
    (`figure_of_merit: offload`, `payload_kg` = the reference payload); a fixed case's
    recorded run is its own payload search at its own P* (SP1 step 7, deviation 2).
    `payload_kg` is null on a run without a search result: for example `silo_failed` of
    the screening directory (`figure_of_merit: none`, `search_status` "skipped (end:
    impact (ignition stage1 fails))"). Such a run flies the vehicle block's
    `payload_mass_t` (`sim.run_planar`, the `none` branch), and the builder takes that
    value. On the 10 runs under `runs` of the
    screening directory and the 19 runs of 20261003T112934Z (checked 2026-10-03; the
    screening directory's two bound runs were not checked), `liftoff_mass_kg` equals the
    run vehicle's stage and fairing masses plus the payload, to rounding (silo_failed:
    569,100 kg = 22.2 + 410.9 + 4.0 + 107.5 + 1.7 t of vehicle plus 22.8 t of payload).
    The builder checks this identity on every run it loads.
  - Fill fraction. Taken against the full-load tank of the experiment's top-level
    `vehicle` block, so an offloaded stage starts below full. The payload builder checks
    that the rebuilt stack mass equals `m_kg`.
- **Clock.** Runs are aligned on time after release (`t_rel_release_s`), as in the replay.
  The pad's hold and the silo's push both lie before zero. The HUD says which clock is shown.
- **Frame.** `downrange_m` is an Earth-fixed arc and the scene is drawn in the Earth-fixed
  frame: a point sits at angle downrange/R_E on a circle of radius R_E + altitude
  (docs/handoff/archive/2026-09-30-phases-0-2.md, section 4.6). The drawn attitude is the
  pitch measured from the local horizontal at that point. R_E comes from `constants.py`.
- **Size.** The replay page of the reference directory's four runs (section 7) is 247,949
  bytes at b3150c1, 215,956 of them JSON (measured 2026-10-03; it was 300,810 and 268,817
  bytes at 2eebcae, so SP1 changed the page); four runs of the offload directory give
  298,591 bytes. The scene adds about five series per run; the payload should stay well
  under 1 MB for four runs (estimate, to measure in A2).
- **Old directories.** Runs recorded before SP1 lack SP1's metrics (push settings, ramp
  start) and the offload keys; the loader falls back to the config keys, as
  `replay.push_accel_g` does (replay.py 521).
- **Failed and odd runs.** `silo_failed` (371 rows, 372 lines with the header; ends in
  `impact`; `payload_kg` null, see the tank levels) must load and play. Its
  `gamma_rel_rad` is unwrapped past pi on the fall-back (TODO.md KI-001, owner SP3); angles
  are wrapped for display. The stage-1 pad control `pad__offload_stage1` of
  20261003T112934Z ends `no_offload` by grams, and its recorded run has status
  `short_of_orbit` with m_res = -0.0016 kg (a resolution effect, SP1 step 5, deviation 2);
  its resolved-config entry has no `vehicle` block (offload 0 kg). It must load, play with
  full tanks and be labelled a pad control, not a failure.

### 5.4 Scene content

Everything below is drawn from the payload. Items that the simulator does not model are
display-only and are labelled as such on the page (section 5.5).

- **Silo cross-section:** the shaft from the mouth down to the launch depth (`stroke_m`), the
  mouth at `track.exit_altitude_m`, rings along the shaft, the carriage moving with `s_m`
  during ASSIST, the floor label with the depth.
- **Pad:** a mount and hold-down clamps, released at the `release` event.
- **Rocket:** drawn to scale, both stages and the fairing, rotated by the attitude.
- **Plume:** on when the stage's thrust is on; length from `thrust_vac_N` relative to the
  stage's full vacuum thrust, so the startup ramp is visible.
- **Tank fill levels:** per stage, so the offload is visible from the first frame.
- **Events** (names as written to events.csv): `push_start`, `ignition` (stage 1 and
  stage 2), `ramp_end`, `release`, `liftoff`, `kick_start` and `kick_end`, `propellant`
  (MECO), `staging`, `fairing`, `cutoff`, `apex`, `impact`, `ignition_failed`, `end`; and
  `ignition_height`, the ramp-start event of `height_method: event` (SP1 step 4).
- **Staging:** stage 1 separates and falls away on its display-only path; stage 2 lights
  after the staging coast.
- **Fairing:** two halves separate at the `fairing` event.
- **Camera:** starts at the close-up (facility scale, about 100 to 200 m) and zooms out with
  altitude and downrange until Earth's curvature and the whole trajectory are in view. A
  scale bar is always shown. When the rocket would be smaller than a few pixels it is drawn
  as an enlarged icon, and the HUD says it is not to scale.
- **HUD:** clock, phase, altitude, Earth-relative speed, downrange, mass, felt axial g,
  dynamic pressure, Mach, thrust fraction, tank levels, and on the track the drive force and
  power. q and Mach are undefined in the vented shaft and show a dash.
- **Side by side:** two panels (the pad and the launched or chosen run) on one clock and one
  zoom level, each with its own scale bar. The existing limit of four runs per page stays for
  recorded directories (proposed: two panels by default, toggles for the others). For a
  directory with an offload block, proposed default: the pad beside the first solved
  stage-1 case (in 20261003T112934Z, `silo_cold_s1`), since the replay's default selection
  never includes offload runs.
- **Reuse from the replay page:** the playback clock, `tick`/`setPlaying`, the scrubber and
  rate select (Auto: 1x until 12 s, 5x until 45 s, 30x after), the run chips,
  `valAt`/`idxAt`/`phaseAt`, `setupCanvas`, `readPalette`, the telemetry cards, the results
  table, the caveats list and the provenance footer, the dark mode handling.

### 5.5 Data gaps and display-only items

The simulator records one point mass. No vehicle or silo geometry exists anywhere in the
configs or the code; the only size-like number is `aero.reference_area_m2` = 10.52 m^2, which
gives a 3.66 m diameter.

| Gap | Resolution (display-only, labelled on the page) |
|---|---|
| Stage lengths, fairing length and diameter, engine section | A display block, proposed as `configs/display/<vehicle>.yaml`, each number with `source:` (the Falcon User's Guide) or `assumed: true`; never in the vehicle file. A test checks that its body diameter agrees with the diameter implied by `reference_area_m2` |
| Shaft diameter, ring pitch and size, carriage shape, pad mount | The same display block, `assumed: true` |
| Spent stage 1 after staging | A ballistic coast from the staging event state. The state is rebuilt from the event rows: r = R_E + alt, v_r = V_rel sin(gamma), u = V_rel cos(gamma), v_theta = u + omega_p r, theta = downrange/R_E + omega_p (t - t_fs), with omega_p = omega_E cos(lat) sin(az). Check: hypot(v_r, v_theta) equals the row's `speed_inertial_mps` (about 3049 against 3049.68 m/s on the pad's staging row of the screening directory). Proposed: a vacuum coast under mu/r^2 with no drag and no attitude, as a pure function with an energy and angular-momentum test |
| Dropped stage-1 mass | `propellant` row mass minus `staging` row mass (22,200 kg on the pad run, equal to the stage-1 dry mass; a penalty row drops its raised dry mass). When the fairing leaves at staging (rule `staging`, or the heating criterion already met there) the staging row is logged after both drops, so the difference also contains the fairing mass; subtract it using the run's vehicle block |
| Fairing halves after the drop | The same coast from the `fairing` event state; the sideways separation is a drawing choice |
| Carriage after release | Not recorded; only `braking_distance_m` is known (60 m at 5 g on the shipped silo) and where the braking section sits is not modelled. Proposed: draw the carriage slowing at `brake_decel_g` over that distance, with the placement stated as a display choice; A0 decides |
| A carriage of 0 t | The shipped silo runs use a massless carriage; it is drawn anyway and the caveat list says so |
| Body attitude | `pitch_rad` is the thrust direction; a point mass has no body axis. The rocket is drawn along it, and the page says so |
| Plume shape | Length follows thrust; the shape and its growth with altitude are a drawing choice |

The scene's caveat list names every display-only item. It also carries the model caveats the
replay already generates (calibration +14.3%, sweep-optimized and unthrottled guidance, no
structural mass for the push, prescribed-acceleration drive, vented shaft) and, for offload
runs, the offload caveats as the directory recorded them: `metrics.json` `offload.caveats`
(section 5.3). Not `summary.OFFLOAD_CAVEATS` from today's code: that constant lacks the
vehicle's calibration caveat, which `summary.offload_caveats` (summary.py 1553) puts first,
and SP1 step 8a reworded its stage-2 caveat (SP1 deviations, step 8a item 6), so a
directory written before a wording change would be shown text it was never written with.
It must not carry the replay's stale closing sentence of the drive caveat (section 5.8
item 5).

The formulas of the display-only reconstructions are written down in one place. Proposed: a
short section in `docs/physics.md` titled as display-only, so they are not mistaken for the
model (A0 confirms the place).

### 5.6 App server and job runner

Decided route (section 3), with the proposed details:

- **Command:** `launchsim app [--port N] [--results-root PATH]`, registered in `cli.py` like
  `animate` and `replay`. It prints the URL and serves until interrupted.
- **Server:** `http.server` from the standard library, bound to 127.0.0.1 and nothing else.
  Every HTML and JSON response sends `charset=utf-8`; pages also carry `<meta charset>` and
  stay ASCII, as the replay page does (a local server sends no charset by default and the
  minus and degree signs turn into mojibake).
- **Proposed endpoints:** the app page; form defaults and presets; the list of results
  directories; the scene payload of one directory and run selection; start a launch (POST);
  job status and progress. A0 fixes the names.
- **Safety of a local server:** requests whose Host is not the loopback address are refused;
  launches are POST only; the client never sends a file path. A results directory is
  addressed by experiment name and timestamp and looked up in the results root's own listing,
  so a request cannot reach outside it.
- **Job runner:** one job at a time; a second Launch while one runs is refused with a clear
  message. Proposed: a worker thread in the server process, so the cached baseline lives in
  memory, with status polled by the page. The alternative is a child process running the
  pipeline, which can be cancelled and isolates a crash but cannot share the cache. A0
  decides after measuring how responsive the server stays during a solve (the search is
  CPU-bound Python under the GIL).
- **Run path:** the form's values become an experiment dict whose shared blocks (site,
  target_orbit, guidance, search, checks, the baseline's integrator) and the offload
  `energy` block (the sourced LOX/RP-1 split and heating value; the gate vehicle file has no
  fuel split) are copied from a committed experiment file. Proposed source:
  `experiments/silo_offload_2d.yaml`, which has the energy block and whose shared blocks
  equal those of every shipped planar experiment
  (`tests/test_config_planar.py::test_shared_blocks_are_identical_across_the_planar_experiments`).
  So app runs share the guidance parametrisation, sweep grid and optimizer budget with the
  committed experiments (CLAUDE.md, Experiments). Then the steps `cli.load_experiment`
  takes from a dict (`resolve_experiment`, `sim.check_result_names`, `sim.check_resolved`),
  the runs, `planar_experiment_result` and `write_run`. The form cannot change a shared
  block or the vehicle file.
- **Pad baseline cache:** at b3150c1, `results_io.run_experiment` (793) always runs the
  baseline (836). SP1's in-memory path makes the alternative cheap: `app.py` composes the
  public pieces (`check_result_names`, `sim.check_resolved`, `git_info`, `make_run_dir`,
  `sim.run_resolved`, `planar_experiment_result`, `write_run`, `write_failure_marker`) in
  the order `run_experiment` uses, with the baseline taken from the cache. Recommended:
  this composition, which leaves `results_io.py` unchanged. Proposed: the cache is keyed by
  a digest of the resolved baseline run dict and vehicle dict and by the git state
  recorded at server start (next item), lives only in the server process, and the cached
  baseline is written into every launch's directory, so each directory is complete and
  `replay`, `animate` and the scene can read it alone.
- **Provenance of a long-running server (proposed; A0 decides).** `results_io.git_info`
  (400) reads the live repository each time it is called. The code that runs a launch is
  whatever the server process imported at its start. If the user edits or commits while
  the server runs, a launch-time `git_info` records a hash and dirty flag that need not
  describe the code that ran, and the cached pad baseline may come from an earlier state.
  Proposed: the server calls `git_info` once at start. Each launch records that state as
  the state of the code that ran, beside the launch-time state. A0 picks where: extra keys
  of the run's `git` record, which resolved_config.yaml and metrics.json write as given
  (`dict(er.git)`, results_io.py 605 and 667) while `summary.provenance_lines` prints only
  the hash, the dirty flag and the error; or a separate provenance field. A launch is
  refused when HEAD differs from the start, with a message asking for a server restart. A
  working-tree change is recorded and flagged. The server-start state is part of the
  baseline cache key: redundant while the cache lives only in the server process (every
  cached run comes from the code imported at start; the risk there is the label, which
  the recorded server-start state fixes), but it keeps a persisted cache, if A0 ever adds
  one, from serving a baseline flown by other code. The exploratory caveats say that the
  code is the one imported at server start.
- **What is not cached:** the offload post-pass flies the baseline's matched run at P_ref
  (cheap) and solves a pad control per solve mode on every pass (`planar_offload`,
  results_io.py 1687; about 30 s each); a paired pad is one more payload search. Caching
  those across launches needs a hook in `planar_offload` (results_io.py). Recommended: no
  hook in SP2 unless the measured wait bothers the user; A0 decides.
- **Progress:** the pipeline has no progress callback; `planar_experiment_result` and the
  solver run to completion. A coarse stage line (resolving, pad cached or running, variant,
  offload pass, writing) needs no change to the pipeline; a finer one (each pad control,
  each case, the verification) needs a callback in results_io.py or offload.py. A0 decides;
  recommended: the coarse line, with the elapsed time and the expected range shown.
- **Results directories:** one normal directory per launch (resolved config, git hash,
  metrics, time series, summary). The directory is made after the preflight and before the
  runs, and an exception leaves `FAILED.txt` (`write_failure_marker`); the run browser shows
  such a directory as failed and does not offer it for replay.
- **Exploratory label:** shown in the app, in the scene's caveats, in `summary.md` and in
  `metrics.json`. The experiment `label` field exists (`ExperimentLabel`, config.py 157,
  with the values `calibration` and `guidance_study`; field at 1865) and has validators tied
  to it (`_labelled_features`, config.py 1948-1987); it is written to resolved_config.yaml
  and metrics.json (results_io.py 613, 676) and `summary.md` prints a banner for
  `calibration` only (summary.py 2021). A0 chooses between a new label value (with a banner)
  and a separate provenance field. The exploratory caveats include the server-start git
  state (the provenance item above).
- **Time per launch (measured in SP1, this machine):** a searched planar run takes 7 to
  25 s (Phase 2); one offload solve with its verification takes about 90 to 110 s (SP1
  step 5 measured 89 s on a loaded machine; the design estimate had been 33 s); a pad
  control about 30 s. Wall clock of SP1's directories, from the directory name to its
  `summary.md`, with the three commands running at once: the bridge (baseline, one
  variant, one stage-1 solve with its verification, its paired pad and a stage-1 pad
  control) 2 min 7 s; the full `silo_offload_2d` run (4 runs, 11 cases, 3 pad controls,
  a paired pad, 8 sensitivity arms, with reuse of equal trajectories) about 14 min; the
  sweep (20 points, each with a solve) about 21 min. Machine speed varies about 3x under
  load. So a Launch with an offload takes minutes: it runs in the background worker, the
  page shows the stage of the job and never blocks, and the cached pad saves only the
  baseline's 7-25 s.

### 5.7 The form

| Group | Fields | Config keys (as built in SP1) | Decision |
|---|---|---|---|
| Launch site | pad only, or silo | `assist.model` (`none` or `constant_accel`) | - |
| Depth | depth; exit speed or net acceleration (one of the two) | `assist.stroke_m`; `assist.exit_speed_mps` or `assist.net_accel_g` (`ASSIST_KEY_FAMILIES`) | D-SP1-05 |
| Silo details | carriage mass, braking deceleration, drive efficiency, exhaust impingement fraction | `assist.carriage_mass_t`, `brake_decel_g`, `drive_efficiency`, `exhaust_impingement_fraction` | proposed: fixed to the committed silo and shown read-only; A0 decides |
| Ramp start | one of: time `t_ign_s` with `reference: release` or `push_start` (push start on a silo run only); depth below the mouth `at_depth_m` (0 to the stroke); speed on the push `at_speed_mps` (0 to the exit speed); height above the mouth by event; height by closed form (`at_height_m` with `height_method: event` or `closed_form`, below the drag-free apex v_e^2/(2 g_eff), about 300 m at 76.7 m/s). Startup override as in the vehicle default (`startup: {kind, t_ramp_s, tau_s}`) | `ignition.stage1.*` (`IGNITION_KEY_FAMILIES`) | D-SP1-06 |
| Propellant | none; solve (mode `stage1`, `stage2` or `both`); or fixed (`stage1_t`, `stage1_fraction`, `stage2_t`, `stage2_fraction` or `both_fraction`); optional stage-2 pre-offload before a stage-1 case; optional paired pad; the pad control (required by a stage-2 or both solve) | `offload.cases[]` (`solve` or `fixed`, `stage2_offload_t`, `paired_pad`), `offload.pad_control`, `offload.reference` = the baseline | D-SP1-03, D-SP1-09, D-SP1-10 |
| Structural penalty | assumed extra stage-1 dry mass on the assisted run (not with a paired pad) | `offload.cases[].stage1_dry_mass_added_t` | D-SP1-04 |
| Presets | named starting points (section 10, Q4) | - | open |

- An offload case names a variant (`of`), never the baseline (the pad's own offload is the
  pad control), so offload fields apply to a silo launch. Run names follow SP1's rules
  (`results_io.check_run_name`: `NAME_PATTERN`, at most `MAX_NAME_LEN` = 64 characters);
  derived names are `<case>__pad` for a paired pad and `<baseline>__offload_<mode>` for a
  pad control (`config.pad_control_run_name`).
- Validation is the simulator's own. The form sends the values; `resolve_experiment` and the
  preflight accept or refuse them; the refusal's message is shown beside the form. The page
  may grey out impossible combinations, but the server is the judge.
- Refusals that must work, each with nothing written under the results root: both exit
  speed and acceleration given; two ramp-start families given; ramp-start depth beyond the
  stroke; ramp-start speed above the exit speed (beyond `ZERO_SPAN_S`); a height at or
  above the drag-free apex (both height methods, the preflight); a push-relative trigger or
  `reference: push_start` on a pad run; a fixed offload mass at or beyond the stage's load,
  or a fraction outside (0, 1); `stage2_offload_t` on a stage-2 or both case; a paired pad
  with a penalty; a stage-2 or both solve without the pad control; a missing or
  non-numeric value; an invalid name.
- Not a refusal but a failed run: a height by event in the band of about 0.41 m just below
  the drag-free apex passes the preflight but never lights under drag (`no_ignition`,
  reported `search_failed`; SP1 step 4, deviation 3). The app shows it as a failed run with
  its reason.
- The results panel shows what `summary.md` reports: payload capacity against the pad, or
  with an offload the section "Propellant saved at fixed payload"
  (`summary.OFFLOAD_SECTION_NAME`): the tonnes removed and the % of the stage-1, stage-2
  and total load; a stage-1 solve quoted gross (the headline form); a stage-2 or both solve
  quoted net of its pad control and labelled a property of the vehicle model; a fixed
  case's P* - P_ref; RP-1 and LOX removed, heat, electricity and their ratio labelled "not
  an efficiency claim" (`compare.OFFLOAD_ENERGY_RATIO_LABEL`); liftoff mass, MECO, max-Q
  against the pad's, felt g on the track, interface force, facility length; the
  ideal-screening offload and the ratio; the decomposition status ("explained" or
  `bug_suspect`); the verification delta; the pad control and its consistency verdict;
  the flags. `cli.offload_lines` (cli.py 317) is a compact model of one line per case.
  The caveats sit beside the numbers: calibration +14.3%, no structural mass for the 4 g
  push, sweep-optimized and unthrottled guidance, the offload caveats (the launch
  directory's `metrics.json` `offload.caveats`, section 5.5), and that the max-Q of an
  offloaded run can exceed the pad's.

### 5.8 Things to fix on the way

1. **Fairing event mass convention (TODO.md KI-016).** Unchanged by SP1 except the line
   numbers. At b3150c1 the `fairing` row of `events.csv` carries the mass before the drop
   when the fairing leaves in LTG_BURN: at stage-2 ignition (`phases/planar.py` 1299, logged
   before the map at 1305) or during the burn (logged by `_integrate`, 1351, at 1357,
   before the map at 1317). It carries the mass after both drops when the fairing leaves at
   staging because the heating criterion is already met (`_stage_and_coast`, 1672:
   `map_staging_planar` at 1689, the `staging` row at 1690, the `fairing` row at 1692,
   phase COAST_STAGING). There is a fourth case: under the rule `fairing_drop: staging`
   (1684) the fairing leaves in the staging map and no `fairing` row is written at all (the
   row at 1691-1692 is written only when the heating criterion is met); the drop has to be
   read from the staging row and the vehicle's fairing rule. No shipped planar vehicle
   uses that rule, but the schema allows it and the 1-D reference vehicle has it.
   Recommended: `read_events` in the run-data module reports the mass before and after for
   every drop, telling the cases apart by the run's `fairing_drop` metric where it exists
   (`metrics_planar.fairing_items`, 669: `FAIRING_IN_BURN`, `FAIRING_AT_IGNITION`,
   `FAIRING_AT_STAGING` or `FAIRING_KEPT`, 393-399; present since Phase 2, so every
   recorded planar directory has it), else by the row's phase and the vehicle's fairing
   rule. Changing what the planner logs touches events in validated code (Plan mode,
   physics.md in the same change, digest pins); do that only if A0 finds a reason the
   reader cannot cover.
2. **Output-path rule mismatch (TODO.md KI-017).** `plots._results_tree` (809) matches the
   folder name "results" case-sensitively and `plots.check_animation_out` (843) refuses
   output only inside the run's own tree; `replay.results_ancestors` (1190) matches
   case-insensitively and `replay.check_replay_out` (1224) refuses output inside any folder
   named results. Recommended: one rule, the stricter one (replay's), for `animate`,
   `replay` and the scene page writer (and the export, if chosen). This changes
   `animate`'s behaviour in one corner; it is
   recorded as a deliberate change and tested.
3. **Private helpers and copies (TODO.md KI-002).** `replay.py` calls `plots._results_tree`
   (1069, 1205) and `plots._is_inside` (1206) and copies the JSON/YAML readers (148, 157;
   plots 579, 588); `run_events` (447) duplicates `plots._events` (635); `calibration_caveat`
   exists twice with different wording (replay 664 says "within the gate" for a record
   inside the band; plots 956 names "Gate vehicle" or "This vehicle"), although both now
   read the same calibration data. The readers, the path helpers and the event reader move
   to public names in the run-data module; the two caveat sentences stay in their modules
   and read the moved data (section 5.2, compatibility policy). The refactor must leave
   the replay page of a fixed directory byte-identical, so the wording is not unified in
   the same step. `CALIBRATION_RECORDS` moves with the helpers and stays importable from
   `plots` (KI-003: it is updated whenever the calibration is re-run;
   tests/test_animate.py checks both records against the findings note).
4. **Housekeeping.**
   - `.gitignore` gains the scene's default output pattern (today, lines 16-19:
     `*_animation.mp4`, `*_animation.gif`, `*_replay.html`; lines 21-22 ignore `_site/`,
     added in SP1 step P). These patterns match at any depth, so a pattern such as
     `*_scene.html` would also ignore the demo file
     `docs/demos/SP2/pad_vs_silo_cold_scene.html` of section 9. At b3150c1 there is no
     `!docs/demos/**` line; SP1's close-out may add one for docs/demos/SP1 (check at the
     start). Otherwise add it after the patterns, or give demo files names that do not
     match; check with `git status` that the demo files show up.
   - `test_template_ships_as_package_data` (tests/test_replay.py 368) covers only the
     editable install; a second template should not make that weaker.
   - KI-018: Pillow is imported by tests/test_animate.py but is not declared in
     pyproject.toml (it arrives through matplotlib; `assets/brand/render_png.py` also needs
     it, outside the package). Declare it with the one-line justification CLAUDE.md asks
     for, or re-own the issue in TODO.md; A0 decides, A1 does it. Declaring a package that
     is already installed is not a new dependency in the sense of exit criterion 12, but it
     is logged the same way.
   - KI-019: the replay page's Google Fonts links; decided with question Q2.
5. **The replay drive caveat's last sentence (KI-029, owner SP2; not in TODO.md at the
   fact-check, logged at SP1 step 9's tracker commit cfd9059).**
   `replay.drive_caveat` (736) ends "Each of these favours the assisted runs." Under the
   prescribed-acceleration drive the massless carriage and the missing shaft drag do not
   raise the payload; they bias the drive energy, peak power and interface force low, while
   the kick without an aerodynamic penalty does favour the silo runs. `site/build.py`
   rewrites the sentence in the gallery's replay pages (`REPLAY_STALE_TEXT`,
   `REPLAY_TEXT_FIXES`) and says to drop that entry once replay.py is fixed. The scene's
   caveats must not inherit the sentence. Fixing replay.py changes the replay page's bytes,
   so it comes after A1's byte-identical gate as a deliberate, tested change, and in the
   same change the `REPLAY_TEXT_FIXES` entry is dropped and the gallery pages are
   regenerated (or the fix kept until they are). A0 decides whether SP2 takes it.

### 5.9 Code organisation (recommended by the survey)

| Module | Kind | Content |
|---|---|---|
| `src/launchsim/run_data.py` (new) | I/O, read-only | section 5.2 |
| `src/launchsim/scene.py` (new) | I/O plus pure helpers | payload, display-geometry loading, rebuilt separation states, the display-only coast, page rendering and export |
| `src/launchsim/templates/scene.html` (new) | template | the scene; shares the replay's clock and helpers through a common fragment or a deliberate copy guarded by a test, so the two pages do not drift |
| `src/launchsim/app.py` (new) | I/O | server, job runner, baseline cache, form-to-experiment mapping, the composition of SP1's in-memory path |
| `src/launchsim/templates/app.html` (new) | template | the form, progress, results panel, run browser, and the scene inside it |
| `src/launchsim/cli.py` | I/O | the `app` command, and `scene` if the export is chosen (Q1) |
| `src/launchsim/plots.py`, `replay.py` | I/O | switch to the run-data module's public names |
| `configs/display/` (new) | config | display geometry, sourced or assumed |
| `site/build.py`, `site/examples/` | site | only if Q1 puts an exported scene in the gallery: `build.py` frames only pages that carry the marker "Written by launchsim replay" (`REPLAY_MARKER`), so a scene page needs its own marker and frame rule, and the link check must pass |
| `tests/test_run_data.py`, `test_scene.py`, `test_app.py` (new) | tests | section 7 |

`replay.py` is 1,246 lines at b3150c1 (1,161 at 2eebcae), most of it caveat and
results-table text; the scene gets its own module instead of growing it. CLAUDE.md lists
the modules allowed to do I/O (today cli.py, sim.py, results_io.py, plots.py and replay.py)
and the layout; both are updated in SP2's close-out. No JavaScript tooling exists in the
project (no `package.json`, no bundler) and the 2-D scene needs none.

### 5.10 Brand, look and the public site

- Since SP1 step P the project has a brand: `assets/brand/` (logo, mark, `favicon.svg`,
  banner; palette and typography in `assets/brand/README.md`) and the site's tokens in
  `site/assets/site.css`. Both are the tokens of `templates/replay.html` with contrast
  fixes for small text (`--ink-3`, the light `--caution`, and `--accent-ink`, the orange for
  small text), so the app's pages and the Pages site share one design system. Proposed: the
  app and scene templates use the site's token values, light and dark.
- `assets/` is outside the package (only `src/launchsim/` ships), so the app cannot read
  the logo or favicon from `assets/brand/` on an installed package. Proposed: the mark is
  inlined in the app template as SVG, with a test that it matches `assets/brand/favicon.svg`.
- Typography: the brand uses Barlow Condensed, IBM Plex Sans and IBM Plex Mono, which the
  site and the replay page load from Google Fonts. Whether the app does too is Q2.
- Whether replay.html also adopts the contrast fixes changes the replay page's bytes: after
  A1, as a deliberate change, if A0 wants it.

## 6. Inventory of the code this phase touches

### Re-check of 2026-10-05 at b69ff0c (SP2 start)

Done in step A0 by a read-only survey (protocol section 3, item 5). The full tables, the
users of every moved name and the method are in
[inputs/2026-10-05-SP2-survey/01-inventory-recheck.md](inputs/2026-10-05-SP2-survey/01-inventory-recheck.md);
this subsection holds what a step needs first. The tables further down are kept as they
were written at b3150c1 and are not corrected in place.

**The diff of the header** listed four files, as the handoff said (673 insertions, 73
deletions): `site/build.py`, `src/launchsim/plots.py`, `src/launchsim/replay.py` and
`tests/test_animate.py` (SP1 step 10a, commit 5007515). Every other inventoried file is
byte-identical to b3150c1, and its lines below hold, with the one exception named at the
end of this list.

- The line numbers given below and in section 5 (5.2, 5.3, 5.8) for `plots.py`,
  `replay.py` and `tests/test_animate.py` are those of b3150c1 and have moved.
- `plots.py` is 1,881 lines (below: 1,701) and every line moved: by +3 near the top, +33
  at the calibration block, +48 at the readers, +153 from `load_animation_runs` to
  `frame_geometry`, +172 at `calibration_caveat`, +179 at `write_ascent_animation`.
- `replay.py` is 1,244 lines (below and in 5.9: 1,246). Nothing moved up to `run_source`
  (244-319); everything after `offload_note` (322-362) is 2 lines lower.
- `tests/test_animate.py` is 814 lines (below: 526) with 26 tests, none slow. The old
  tests moved by +18. It holds three monkeypatches on plots, not the one the brief names.
- `site/build.py` is 1,162 lines (1,028 at b3150c1). It has five `REPLAY_TEXT_FIXES`
  pairs, not one, and a second table, `REPLAY_PAGE_FIXES`, of eleven page-specific fixes.
- `_resolved_config_dict` is at `results_io.py` 590 (590-622), not 588; its inline `runs`
  block is 597-601, not 597-599. This was already so at b3150c1.

**`plots.py`: the symbols the brief and the design name**

| Symbol | Below (b3150c1) | At b69ff0c |
|---|---|---|
| `plot_stem` | not listed (it was at 90) | 93-96 (`PLOT_STEM_UNSAFE` at 90) |
| `AnimationError` | 309 | 312 |
| `ANIMATION_MAX_RUNS` | 321 | 324 |
| `RESULTS_TREE_NAME` | 344 | 347 |
| `CALIBRATION_RECORDS` | 474-487 | 507-510 (docstring to 520) |
| `CALIBRATION_BAND`, `CALIBRATION_BAND_EDGE_REL_TOL`, `CALIBRATION_GATE_VEHICLE` | 488, 492, 497 | 521, 525, 530 |
| `calibration_gap`, `inside_calibration_band` | 501, 508 | 534-538, 541-544 |
| `AnimationRun` | 528 | 573-610 (class line 574); new field `offload` (595) |
| `ANIMATION_COLUMNS` | 565 | 613-623 (the same nine columns) |
| `_read_json`, `_read_yaml` | 579, 588 | 627-633, 636-642 |
| `animation_run_names` | 597 | 645-658 |
| `check_planar_run_dir` | 613 | 661-680 |
| `_events` | 635 | 683-707 |
| `read_animation_run` | 662 | 813-844 (its record now comes from `animation_record`, 827) |
| `load_animation_runs` | 694 | 847-869 |
| `ascent_time_map` | 748 | 901-910 |
| `_results_tree` | 809 | 962-972 (the name test at 969) |
| `_is_inside` | 822 | 975-977 |
| `default_animation_path` | 827 | 980-993 |
| `check_animation_out` | 843 | 996-1017 (tree test 1006, ffmpeg test 1011) |
| `frame_geometry` | 867 | 1020-1032 |
| `calibration_caveat` | 956 | 1128-1146 (reads `CALIBRATION_RECORDS` at 1135) |
| `animation_caveats` | not listed | 1149 (calls `calibration_caveat` at 1161) |
| `_AscentFigure` | 1041 | 1213-1815 |
| `write_ascent_animation` | 1639-1701 | 1818-1881 (`FFMpegWriter(...)` at 1867) |

**`replay.py`: the symbols the brief and the design name.** Unchanged lines:
`ReplayError` 57, `REPLAY_TEMPLATE` 62, `REPLAY_DATA_TOKEN` 64, the grid constants 68-77,
the roles 93-97, `REPLAY_COLUMNS` 102, `SERIES_FIELDS` 119-128, `_read_json` 148,
`_read_yaml` 157, `check_replay_run_dir` 166, `select_runs` 198, `run_source` 244-319.

| Symbol | Below (b3150c1) | At b69ff0c |
|---|---|---|
| `offload_note` | 322 | 322-362 (rewritten on `plots.offload_role`; the same strings) |
| `read_series` | 367 | 365 |
| `_finite` | 385 | 383 |
| `replay_grid`, `defined_mask`, `series_values`, `run_series` | 396, 407, 417, 432 | 394, 405, 415, 430 |
| `run_events` | 447 | 445 |
| `push_accel_g`, `assist_text` | 521, 531 | 519, 529 |
| `calibration_caveat` | 664 | 662-685 |
| `structure_caveat` | not listed | 688 ("the fully fuelled stack" at 700) |
| `drive_caveat` | 736, the stale sentence at 763 | 734-761, the stale sentence at 761 |
| `comparison_caveats` | not listed | 805-840 (the offload sentence 831-839) |
| `caveats` | 845 | 843-878 |
| `closeup_notes` | not listed | 881-925 ("and leave" at 900) |
| `ROLE_LABELS`, `run_label` | not listed | 964-968, 972 |
| `run_record` | 982-1062 | 980-1060 |
| `source_text` | 1065 (`plots._results_tree` at 1069) | 1063 (1067) |
| `replay_data` | 1107 | 1105-1160 |
| `embed_json`, `load_template`, `render_page` | 1168, 1176, 1182 | 1166, 1174, 1180 |
| `results_ancestors` | 1190 | 1188 (`RESULTS_TREE_NAME` at 1193) |
| `protected_tree` | 1199 (`_results_tree` 1205, `_is_inside` 1206) | 1197 (1203, 1204) |
| `default_replay_path` | 1211 (`plots.plot_stem` at 1219) | 1209 (1217) |
| `check_replay_out` | 1224 | 1222-1234 |
| `write_replay_page` | 1239 | 1237-1244 |

**`tests/test_animate.py`.** `_make_run_dir` 134 (below: 119); the animate path tests of
section 5.2 are `test_default_output_is_outside_the_run_dir` 198-213 and
`test_custom_results_root_is_protected` 478-486 (below: 180-195 and 460-468);
`test_calibration_record_matches_its_findings_note` 299-326 (below: 281);
`test_calibration_band_includes_both_edges` 355-375 (below: its setattr at 353). New in
step 10a: `_make_offload_run_dir` 549-636, a synthetic results directory with an offload
block (three cases, one paired pad, three pad controls), and four tests (644, 679, 720,
739).

**The three monkeypatches** (all in `tests/test_animate.py`; no test patches the replay
module). They fix where a function may live after A1:

| Line | Patch | What it pins |
|---|---|---|
| 371 | `mp.setattr(plots, "CALIBRATION_RECORDS", edge)`, then `plots.calibration_caveat("edge_2d")` at 372 | `plots.calibration_caveat` must read the name `CALIBRATION_RECORDS` from the plots module at call time (the brief gives this one, at 353) |
| 515 | `monkeypatch.setattr(plots, "FFMpegWriter", _BrokenFFMpeg)`, then `main(["animate", ..., "--out", "a.mp4"])`, expecting "error: ffmpeg failed" | `check_animation_out` (ffmpeg test at plots 1011), `default_animation_path` (988) and `write_ascent_animation` (1867) all resolve `FFMpegWriter` in the plots namespace, so the ffmpeg test stays in a plots function. Not in the brief |
| 170 (`_no_ffmpeg`, used at 221, 245, 752) | `monkeypatch.setattr(plots.FFMpegWriter, "isAvailable", classmethod(lambda cls: False))` | patches matplotlib's class object; it holds wherever the check lives, as long as `plots.FFMpegWriter` stays an attribute of plots. Not in the brief |

**What step 10a added to `plots.py`** (no line below names them; A1 must house them):
`OFFLOAD_CASE` 488, `OFFLOAD_PAIRED_PAD` 489, `OFFLOAD_PAD_CONTROL` 490,
`OFFLOAD_SOLVED_KIND` 495, `NEAR_ORBIT_PHASE` 498, `LEGEND_TITLE` 503, `OffloadTag`
560-570, `_as_dict` 710-712, `_finite_kg` 715-719, `offload_role` 722-737, `offload_tag`
740-792, `animation_record` 795-810, `legend_title` 1118-1125, and the import
`from launchsim.offload import NO_OFFLOAD_STATUS` at 44. `replay.py` uses
`plots.offload_role` (330), `plots.OFFLOAD_PAIRED_PAD` (334), `plots.OFFLOAD_PAD_CONTROL`
(339) and `plots.OFFLOAD_SOLVED_KIND` (344); the tests use `plots.OFFLOAD_CASE`,
`OFFLOAD_PAIRED_PAD` and `OFFLOAD_PAD_CONTROL` (660, 661, 693, 729). `_as_dict` duplicates
`replay._mapping` (221), `_finite_kg` is close to `replay._finite` (383), and
`animation_record` repeats part of `replay.run_source` (244). Step 10a also added the
figure-layout constant `MAIN_HEADROOM_PER_SECOND_LINE` (412), which stays in plots.

**The two fix tables of `site/build.py`** (`REPLAY_MARKER` 88, `REPLAY_STALE_TEXT` 122,
`fix_replay_text` 918-938):

| Table | Lines | Content |
|---|---|---|
| `REPLAY_TEXT_FIXES` | 123-166 | Five (old, new) pairs applied to every framed replay page: (1) the drive caveat's stale closing sentence (replay.py 761); (2) "and leave" to "and leaves" (replay.py 900); (3) to (5) three patches of the template's canvas JavaScript: the close-up's lower bound, so the "silo floor" label clears the time axis, the x-axis tick label clamped inside its canvas, and the timeline's event label clamped |
| `REPLAY_PAGE_FIXES` | 200-260 | A dict from a page's file name to (old, new) pairs applied after the text fixes: four pairs for `pad-vs-silo-offload.html` and seven for `offload-vs-paired-pad.html`, sharing `REPLAY_OFFLOAD_DRIVE` (178), `REPLAY_OFFLOAD_ROUNDING` (183) and `REPLAY_OFFLOAD_STRUCTURE` (191); the others reword the subtitle, the paired pad's role label, the paired-pad note and the comparison caveat |

A page that still holds `REPLAY_STALE_TEXT` is a build error; a page fix that matches
neither its old nor its new text is only a warning.

**Facts the brief has wrong or missing**, each of which changes the design (design,
section 2; the evidence is in the survey reports, each of which ends with its own list):

- The shared blocks are `dynamics`, `site`, `guidance`, `search`, `target_orbit` and
  `checks`. The integrator is not a shared block (section 5.6 says it is, and omits
  `dynamics`).
- `propellant` is the generic depletion event; MECO is the `propellant` row with stage 1
  (section 5.4 reads as if the name meant MECO only).
- No `liftoff` row and no pad `ramp_end` row exist on disk (section 5.4 lists both among
  the events).
- In-phase events are also written twice in the CSV, not only phase boundaries (section
  5.3).
- A failed search writes a complete directory with an empty time series (section 5.6
  describes only the crash case, a directory with `FAILED.txt`).
- The composed run path writes `FAILED.txt` only if `app.py` does: the marker is written
  inside `run_experiment` (results_io.py 886-887), which the composition does not call.
- On Windows the standard-library server lets two processes bind one port unless exclusive
  binding is set.
- The config accepts `true`, numeric strings, inf and NaN for several numbers (section 5.7
  counts "a missing or non-numeric value" among the refusals that work; TODO.md KI-030).

### The inventory as checked at b3150c1 (2026-10-03)

Checked at b3150c1 on 2026-10-03 by the SP1 session: every `def`, `class` and constant line
below was found by grep at that commit; ranges are a definition's first and last line. The
previous check was at 2eebcae on 2026-09-30; SP1 changed `cli.py`, `config.py`,
`metrics_planar.py`, `offload.py` (new), `plots.py`, `replay.py`, `results_io.py`,
`sim.py`, `summary.py` and `phases/planar.py`, so most numbers moved. `templates/replay.html`,
`pyproject.toml` and `metrics.py`'s `TRACK_COLUMNS` did not change (the template's lines
were re-checked and hold). At the SP2 start, re-check the files that the diff of the header
lists (`git diff --stat b3150c1 HEAD -- src tests configs experiments pyproject.toml
.gitignore site/build.py`); an empty diff is the re-check of protocol section 3, item 5.

What the fact-check changed in this file, for the record: the entry criteria (section 4)
now name what SP1 built and where; the form (5.7) offers every ramp-start setting and the
offload settings as the block defines them; the run path uses SP1's in-memory composition
(5.6); the measured costs replace the estimates (5.6); the payload notes say where offload
runs live (5.3); the fairing reader can use the existing `fairing_drop` metric (5.8 item 1);
the replay drive-caveat item (5.8 item 5) and the brand section (5.10) are new; the
questions and risks (section 10) and the prompt (section 13) are updated. A cold read of
the file on 2026-10-03 then corrected: where a run's vehicle block lives and the payload
of a run without a search (5.3); the source of the offload caveats (5.3, 5.5, 5.7); A1's
compatibility policy and the users of the moved names (5.2, 5.8 item 3, this section);
the git provenance of a long-running server (5.6); the reviewer set (section 7, the
protocol's numerics skeptic); A3's serving route; the state lines of entry criteria 7 and
9; exit criteria 10 and 13; the re-check trigger and its path list (header). No step,
exit criterion or decision was removed.

**CLI: `src/launchsim/cli.py` (510 lines)**

| Symbol | Lines | Note for SP2 |
|---|---|---|
| module docstring usage | 11-17 | `run` and `sweep` gained `--no-offload` (and `run` `--no-sensitivity`) in SP1; a new command adds a usage line here |
| `build_parser` | 58-161 | `add_subparsers` at 65; parsers: `run` 67 (`--no-sensitivity` 73, `--no-offload` 79), `sweep` 85 (`--no-offload` 90), `animate` 95-138, `replay` 140-160. A new command adds a parser here |
| `load_yaml` | 191 | third YAML reader; raises `CliError` |
| `load_experiment` | 254-276 | reads the experiment and vehicle files, then `resolve_experiment`, `sim.check_result_names` (272) and the preflight `sim.check_resolved` (273); the app does the same from a dict |
| `results_root` | 285 | `--results-root`, else `<repo root>/results` |
| `OFFLOAD_NOT_QUOTED_REASONS`, `offload_lines` | 309, 317 | console text of an offload block (one line per case and pad control); a model for the results panel |
| `command_run` | 377-414 | the CLI run path: `sim.run_experiment(..., sensitivity=, offload=)` (re-exported from results_io) |
| `command_sweep` | 417-437 | |
| `command_animate` | 440-472 | catches `plots.AnimationError` |
| `command_replay` | 475-488 | `check_replay_run_dir`, `default_replay_path`, `write_replay_page` |
| `main` | 491-510 | dispatch dict at 497-502; exit 0, 1 (`CliError`, `OSError`, one ASCII `error:` line), 2 (usage) |

**Run path (read and composed by the app)**

| Symbol | File and lines | Note |
|---|---|---|
| `resolve_experiment(exp_dict, vehicle_dict, load_vehicle=None)` | `config.py` 2816-2898 | pure; takes dicts; resolves the offload block too; the app's entry |
| `ResolvedRun`, `ResolvedExperiment` | `config.py` 2346, 2470 | `ResolvedExperiment.offload` (2483) is the resolved block |
| `TrackConfig`, `ConstantAccelConfig`, `IgnitionConfig` | `config.py` 584, 613, 761 | form fields map to these; `exit_speed_mps` and the ramp-start keys added in SP1 |
| `ASSIST_KEY_FAMILIES`, `IGNITION_KEY_FAMILIES`, `RAMP_START_TRIGGERS`, `HEIGHT_METHOD_EVENT`/`_CLOSED_FORM` | `config.py` 88, 91, 143, 148-149 | the exclusive key families and trigger names |
| `StartupOverride` | `config.py` 726 | the ramp's startup override (`kind`, `t_ramp_s`, `tau_s`) |
| `OFFLOAD_FIXED_KEYS`, `OFFLOAD_GROSS_MODES`, `PAD_CONTROL_PREFIX` | `config.py` 1521, 1549, 1555 | the fixed-offload keys; stage 1 is quoted gross; pad-control names |
| `OffloadFixedConfig`, `OffloadCaseConfig`, `OffloadEnergyConfig`, `OffloadConfig` | `config.py` 1559, 1619, 1676, 1709 | the `offload:` block; the YAML key `reference` is read into `reference_run` (alias) |
| `SweepConfig` | `config.py` 1441 (`offload` field 1459) | sweeps are out of the form's scope |
| `pad_control_run_name`, `offload_run_names` | `config.py` 2102, 2107 | derived run names |
| experiment `label` rules | `config.py` 157-159 (`ExperimentLabel`), 1865 (field), 1948-1987 (`_labelled_features`) | `calibration`, `guidance_study` today |
| `IntegratorConfig`, `sample_dt_s` | `config.py` 875, 897 | time-series sampling 0.05 s |
| `check_result_names`, `NAME_PATTERN`, `MAX_NAME_LEN` | `results_io.py` 234, 186, 187 | run names become directories |
| `OffloadReport`, `ExperimentResult` | `results_io.py` 276, 292 | `ExperimentResult.offload` carries the report |
| `make_run_dir` | `results_io.py` 365 | never reuses a directory; adds `-2`, `-3` on a collision |
| `git_info` | `results_io.py` 400 | provenance, including the dirty flag; reads the live repository at every call (section 5.6, provenance) |
| `write_failure_marker`, `FAILED_MARKER` | `results_io.py` 567, 167 | `FAILED.txt` |
| `_resolved_config_dict`, `_run_entry` | `results_io.py` 588, 625 | resolved_config.yaml: `vehicle` in a run's entry only when it differs from the top-level block (`runs` inline at 597-599; `bound_runs`, `cases`, `offload_runs` through `_run_entry`); `git` written as given (605) |
| `write_run` | `results_io.py` 687 | the writer of a run directory |
| `run_experiment(resolved, out_root, plots, only_variant, repo_root, sensitivity, offload)` | `results_io.py` 793-889 | preflight 830-831, directory 834, always runs the baseline (836), planar branch 837-852, `FAILED.txt` 886-887 |
| `planar_comparisons`, `planar_bounds` | `results_io.py` 960, 999 | |
| `planar_offload` | `results_io.py` 1687 | the offload post-pass: pad controls, cases, arms; no cache hook |
| `planar_experiment_result(..., *, sensitivity, run_cases, offload=True)` | `results_io.py` 1973-2027 | pure apart from the runs it executes; writes nothing |
| `run_sweep` | `results_io.py` 2120 | preflight 2143 |
| `run_resolved`, `every_resolved_run`, `check_resolved` | `sim.py` 876, 896, 932 | one resolved run; every run a preflight visits (offload starts included); the preflight |
| `offload_problem_factory`, `solve_resolved_offload`, `offload_run_result` | `sim.py` 1708, 1717, 1728 | used by the post-pass, not by the app directly |
| `OffloadResult`, `solve_offload` | `offload.py` 307, 472 | the solver; out of scope to change |
| `OFFLOAD_SECTION_NAME`, `OFFLOAD_CAVEATS`, `offload_section`, `planar_experiment_summary` | `summary.py` 1491, 1500, 1897, 2008 | the summary's offload section and caveats |
| `OFFLOAD_COMPARISON_BASIS`, `OFFLOAD_ENERGY_RATIO_LABEL` | `compare.py` 1639, 1657 | basis line; "not an efficiency claim" |

**Replay: `src/launchsim/replay.py` (1,246 lines)**

| Symbol | Lines | Note |
|---|---|---|
| `REPLAY_TEMPLATE`, `REPLAY_DATA_TOKEN` | 62, 64 | `("templates", "replay.html")`, `__REPLAY_DATA__` |
| grid constants | 68-77 | early end 40 s, 0.1 s, then 1 s; decimals |
| `ROLE_RUN` ... `ROLE_OFFLOAD` | 93-97 | five roles; `ROLE_OFFLOAD` added in SP1 step 7 |
| `REPLAY_COLUMNS`, `SERIES_FIELDS` | 102, 119-128 | eight fields; no pitch, thrust, stage or track columns |
| `_read_json`, `_read_yaml` | 148, 157 | copies of `plots._read_json` (579), `_read_yaml` (588) |
| `check_replay_run_dir` | 166 | needs `metrics.json`, a `runs` dict, `model == "planar_2d"`; rejects 1-D and sweep points (a sweep directory has no top-level metrics.json) |
| `select_runs` | 198 | reuses `plots.animation_run_names`; at most `ANIMATION_MAX_RUNS` (4) |
| `run_source`, `offload_note` | 244, 322 | roles from metrics.json and resolved_config.yaml; offload runs from `offload.runs` / `offload_runs` |
| `read_series` | 367 | sorts on `t_rel_release_s`, drops duplicate times keeping the last |
| `_finite`, `replay_grid`, `defined_mask`, `series_values`, `run_series` | 385, 396, 407, 417, 432 | null and resampling logic to share |
| `run_events` | 447 | every event row; duplicates `plots._events` (635) |
| `push_accel_g`, `assist_text` | 521, 531 | metric first, config key as fallback (SP1 step 2) |
| `calibration_caveat` | 664 | second copy at `plots.py` 956, different wording, same data since SP1 step 8a |
| `drive_caveat` | 736 | ends with the stale sentence of section 5.8 item 5 (763) |
| `caveats` | 845 | generated caveat list to reuse |
| `run_record` | 982-1062 | per-run metrics for the page |
| `source_text`, `protected_tree` | 1065, 1199 | call `plots._results_tree` (1069, 1205) and `plots._is_inside` (1206) |
| `replay_data` | 1107 | payload builder |
| `embed_json`, `load_template`, `render_page` | 1168, 1176, 1182 | injection pattern to keep |
| `results_ancestors`, `default_replay_path`, `check_replay_out` | 1190, 1211, 1224 | the stricter output-path rule |
| `write_replay_page` | 1239 | |

**Replay template: `src/launchsim/templates/replay.html` (588 lines, unchanged since 2eebcae)**

| Item | Lines | Note |
|---|---|---|
| Google Fonts links | 7-9 | the page is not offline today (Q2; TODO.md KI-019) |
| "Written by launchsim replay" comment | 13 | `site/build.py` finds replay pages by this marker |
| data script tag | 197 | `<script type="application/json" id="replay-data">` |
| script (one strict IIFE, canvas 2D, no library) | 198-585 | `</script>` at 586 |
| `MARK_EVENTS` | 213 | propellant, fairing, cutoff, impact |
| `readPalette`, `idxAt`, `valAt`, `phaseAt`, `setupCanvas` | 230, 235, 242, 250, 263 | reusable |
| `drawTraj` | 348 | altitude against downrange on a flat axis |
| `drawCloseup` | 370-411 | altitude against time; the shaft is a filled band; no walls, rings, carriage or vehicle |
| `currentRate`, `tick`, `setPlaying`, `init` | 509, 516, 526, 539 | playback and wiring; Auto rate at 509-515 |

**Animate: `src/launchsim/plots.py` (1,701 lines)**

| Symbol | Lines | Note |
|---|---|---|
| `AnimationError`, `ANIMATION_MAX_RUNS`, `RESULTS_TREE_NAME` | 309, 321, 344 | |
| `CALIBRATION_RECORDS` | 474-487 | two vehicles since SP1 step 8a; update when the calibration is re-run (TODO.md KI-003) |
| `CALIBRATION_BAND`, `CALIBRATION_BAND_EDGE_REL_TOL`, `CALIBRATION_GATE_VEHICLE`, `calibration_gap`, `inside_calibration_band` | 488, 492, 497, 501, 508 | moved here from replay.py in SP1 step 8a |
| `AnimationRun`, `ANIMATION_COLUMNS` | 528, 565 | animate's loader type; no pitch, thrust or track columns |
| `_read_json`, `_read_yaml` | 579, 588 | |
| `animation_run_names`, `check_planar_run_dir` | 597, 613 | run discovery (default: baseline plus three variants; offload runs only in the "available" list); the planar check |
| `_events`, `read_animation_run`, `load_animation_runs` | 635, 662, 694 | |
| `ascent_time_map` | 748 | animate's piecewise timeline (not used by the replay page) |
| `_results_tree`, `_is_inside` | 809, 822 | private helpers used by `replay.py` |
| `default_animation_path`, `check_animation_out` | 827, 843 | the looser output-path rule |
| `frame_geometry` | 867 | |
| `calibration_caveat` | 956 | the footnote's wording ("Gate vehicle" / "This vehicle") |
| `_AscentFigure`, `write_ascent_animation` | 1041, 1639-1701 | FFMpegWriter (h264) or PillowWriter; no blitting, about 4 minutes for 600 frames at 1280 px |

Figures in `plots.py` are built from `matplotlib.figure.Figure` and saved through the Agg
canvas (module docstring), not through pyplot's global state.

**Users of the names A1 moves** (outside their own definitions; code lines unless marked
docstring; checked by grep at b3150c1 on 2026-10-03; section 5.2 gives the compatibility
policy)

| User | Lines | Names |
|---|---|---|
| `results_io.py` | 143, 1798 | `from launchsim.plots import CALIBRATION_RECORDS, write_plots`; `offload_caveats(vehicle_name, CALIBRATION_RECORDS.get(vehicle_name))` for metrics.json `offload.caveats` |
| `summary.py` | 1534 (docstring) | `offload_calibration_caveat` names `plots.CALIBRATION_RECORDS`; it takes the record as an argument and imports nothing from plots |
| `replay.py` | 103; 203, 214, 216; 668, 675, 677, 680; 1069, 1195, 1205, 1206; 1219 (docstrings 18-19, 172, 200-202, 665-666, 1191, 1201-1202) | `plots.ANIMATION_COLUMNS`; `plots.animation_run_names`, `plots.ANIMATION_MAX_RUNS`; `plots.CALIBRATION_RECORDS`, `calibration_gap`, `CALIBRATION_BAND`, `inside_calibration_band`; `plots._results_tree`, `plots.RESULTS_TREE_NAME`, `plots._is_inside`; `plots.plot_stem` |
| `cli.py` | 444, 446, 450; 480, 482 | `plots.load_animation_runs`, `plots.default_animation_path`, `plots.check_animation_out`; `replay.check_replay_run_dir`, `replay.default_replay_path` |
| `tests/test_animate.py` | 185-193, 255, 295-329, 348-354, 466-467 | `plots.default_animation_path`, `plots.animation_run_names`, `plots.CALIBRATION_RECORDS`, `plots.calibration_caveat`, `plots.calibration_gap`, `plots.inside_calibration_band`, `plots.check_animation_out`; 353 monkeypatches `plots.CALIBRATION_RECORDS` and then calls `plots.calibration_caveat` |
| `tests/test_replay.py` | 336-352, 381, 432, 483, 504, 506, 622-625 | `replay.calibration_caveat`, `replay.default_replay_path`, `replay.ROLE_BOUND`, `replay.replay_grid`, `replay.SERIES_FIELDS`, `replay._finite` (private) |
| `tests/test_config_planar.py` | 1376, 1378 | `plots.CALIBRATION_RECORDS` |
| `tests/test_offload_pipeline.py` | 842, 1087-1096, 1733, 2023, 2038, 2061 | `plots.CALIBRATION_RECORDS`; `replay.run_source`, `replay.ROLE_OFFLOAD` |

**Recorded data**

| Item | Where | Note |
|---|---|---|
| `PLANAR_FLIGHT_COLUMNS`, `PLANAR_TIMESERIES_COLUMNS` | `metrics_planar.py` 298, 340 | 32 columns; sampled every 0.05 s; about 10.5k rows and 3.6 MB per run (silo_cold_s1: 10,539 lines, 3,630,414 bytes) |
| `UNWRAPPED_COLUMNS` | `metrics_planar.py` 351 | `gamma_rel_rad` and `pitch_rad` unwrapped per run |
| `PLANAR_EVENT_COLUMNS` | `metrics_planar.py` 380 | `t_s` (absolute), `event`, `phase`, `stage`, and `PLANAR_COLUMNS` (`phases/planar.py` 174): `alt_m`, `downrange_m`, `speed_rel_mps`, `speed_inertial_mps`, `gamma_rel_rad`, `m_kg` |
| `TRACK_COLUMNS` | `metrics.py` 60 | `s_m`, `drive_force_N`, `interface_force_N`, `drive_power_W`, `track_normal_g_vehicle`, `track_normal_g_carriage`; NaN outside ASSIST |
| fairing forms, `fairing_items` | `metrics_planar.py` 393-399, 669 | the `fairing_drop` metric names the drop case (section 5.8 item 1) |
| `planar_track_metrics` | `metrics_planar.py` 963-1026 | track metrics plus `PUSH_SETTING_METRICS` (933) |
| `RAMP_START_METRICS`, `RAMP_START_REQUEST_METRICS`, `ramp_start_metrics` | `metrics_planar.py` 1029, 1041, 1062 | requested and achieved ramp start |
| `OFFLOAD_METRIC_KEYS`, `offload_metrics` | `metrics_planar.py` 1225, 1234 | per offload run |
| `PlanarView.row` | `phases/planar.py` 234 | how theta maps to `downrange_m` (0 for HOLD, ASSIST and RELEASE rows, `EARTH_FIXED_LABELS` 171) |
| `map_staging_planar`, `map_fairing_planar` | `phases/planar.py` 451, 475 | subtract mass only; r, theta and velocity unchanged |
| fairing event logging | `phases/planar.py` 1299 (before the map at 1305), 1357 via `_integrate` 1351 (before the map at 1317), 1692 | the mixed mass convention of section 5.8 |
| staging event logging | `phases/planar.py` 1672-1692 (`_stage_and_coast`; the row at 1690, after the map at 1689) | logged after the drop |
| `IGNITION_HEIGHT_EVENT` | `phases/prelude.py` 84 | `"ignition_height"` |
| metrics times | `metrics.json` | after release, except `t_release_s` (absolute) |
| resolved config | `resolved_config.yaml` | top-level keys `experiment`, `timestamp_utc`, `git`, `comparison_basis`, `baseline`, `vehicle`, `runs`, `model`, `label`, `bound_runs`, `cases`, `offload_runs`; every entry under `runs`, `bound_runs`, `cases` and `offload_runs` has `run`, and `vehicle` only when the run's vehicle differs from the top-level block (in 20261003T112934Z, `pad__offload_stage1` and `pad__offload_both` have `run` only) |
| metrics | `metrics.json` | offload record under `offload` (`basis`, `reference`, `reference_payload_kg`, `caveats`, `energy_inputs`, `pad_control`, `pad_controls`, `cases`, `sensitivity_basis`, `sensitivity`, `notes`, `runs`) |

**Tests to keep green and to copy from**

| File | Lines | Note |
|---|---|---|
| `tests/test_replay.py` | 682 | synthetic `results/<exp>/<ts>` under `tmp_path` (helpers 49-260, `_make_run_dir` 183), no simulation; strict JSON; ASCII page; L311 asserts `pitch_deg` is not embedded; `test_template_ships_as_package_data` 368; template string checks 628; `node --check` 665-682 (skipped without node) |
| `tests/test_animate.py` | 526 | fixture helpers 46-146 (`_make_run_dir` 119); output-path refusals; `test_calibration_record_matches_its_findings_note` 281 (both records); `test_custom_results_root_is_protected` 460 |
| `tests/test_offload_pipeline.py` | 2,374 | `test_replay_shows_an_offload_run_beside_the_pad` 1077 (fast, synthetic); the `offload_e2e` fixture 2165-2181 (the in-memory path); `test_offload_in_memory_writes_nothing` 2185 and `test_offload_outputs_written_and_replayed` 2291 (slow) |

No test in test_replay.py or test_animate.py is marked slow. There is no test file for
`plots.py` itself.

**Packaging and tools: `pyproject.toml` (unchanged since 2eebcae)**

- Dependencies: numpy, scipy, pandas, matplotlib, pydantic, pyyaml, ambiance. Pillow arrives
  through matplotlib and is not declared (TODO.md KI-018; section 5.8 item 4). Build backend
  `uv_build`, no package-data setting; the whole `src/launchsim` folder ships, `templates/`
  included (it has no `__init__.py`); `assets/` and `site/` do not ship.
- ruff: line length 100; `extend-exclude` `*.md`, `notebooks`, `docs/findings/probes`.
  pytest: `filterwarnings = error`, so library code never calls `warnings.warn`; marker
  `slow`.
- On this machine: ffmpeg 8.1, and node at `/c/nvm4w/nodejs/node`.
- `.gitignore` (22 lines): 9-14 `results/**` ignored except each run directory's top-level
  `summary.md`; 16-19 the default outputs of `animate` and `replay`; 21-22 `_site/`.
- Site: `site/build.py` (Python-Markdown 3.11 via `uvx`, CI only; not a project
  dependency) builds `_site/`; `.github/workflows/pages.yml` deploys it on every push to
  main.

**Data on disk for development (2026-10-03; CSV files are not in git)**

| Directory | Runs with `timeseries.csv` |
|---|---|
| `results/silo_screening_2d/20260930T175743Z` | 12: pad, pad__aero_bound, pad_instant, silo_cold, silo_cold__aero_bound, silo_cold_lag, silo_failed, silo_hot_full, silo_hot_full_impinged, silo_hot_ramp_on_track, silo_instant, silo_sled_22t (45 MB) |
| `results/silo_offload_2d/20261003T112934Z` | 19 (72 MB; git b3150c1, clean): runs pad, silo_cold, silo_hot_ramp_on_track, silo_cold_200m; offload cases silo_cold_s1 (the headline), silo_cold_s2, silo_cold_both, silo_cold_s1_s2pre2t, silo_cold_s1_dry+2t, silo_cold_s1_dry+4t, silo_cold_s1_dry+8.1t, silo_cold_fix5pct, silo_cold_fix10pct, silo_hot_ramp_s1, silo_cold_200m_s1; paired pad silo_cold_s1__pad; pad controls pad__offload_stage1, pad__offload_stage2, pad__offload_both |
| `results/silo_offload_2d/20261003T112949Z` | the sweep: baseline/ and sweep_1 to sweep_5 (20 points, each a single-run folder), 83 MB; no top-level metrics.json |
| `results/silo_offload_2d_readme/20261003T112956Z` | 5 (17 MB): pad, silo_cold, silo_cold_s1, silo_cold_s1__pad, pad__offload_stage1 (the bridge on the README-loads fork) |
| `results/calibration_f9_2d/20260930T173928Z` | 8 (the earlier `20260930T100100Z` holds the records `CALIBRATION_RECORDS` cites) |
| `results/silo_bridge_2d_readme/20260930T185034Z` | 4 |

Earlier work to look at: `docs/findings/probes/handoff-2026-09-30/template.html` and
`prep_data.py` (the prototype of the replay page; `prep_data.py` emits `pitch_deg`),
`docs/media/ascent_pad_vs_silo_cold_2d.mp4` and `.gif`, and the gallery's replay pages and
animations under `site/examples/`.

## 7. Steps

Approved by the user on 2026-10-05 (step A0). The table is the one of the design
([inputs/2026-10-05-SP2-design.md](inputs/2026-10-05-SP2-design.md), section 5) with the
Status and Commit columns added. It replaces the table this brief proposed; section 12
lists the differences.

Each step runs the protocol's loop: implementer; reviewers (a numerics skeptic on A1 to
A6v; a CLAUDE.md compliance auditor on every step; a visual-QA reviewer on anything drawn,
through a 127.0.0.1 server; an honesty auditor on labels and caveats; a security reviewer
on A4b and A6v); up to two fix rounds; an independent gate; one commit; the tracker commit
(`SP2 step <k>: trackers (<hash>)`); push; the Pages check. Standing gates: fast suite
green, ruff clean, golden 1-D, the planar digest pin and the output capture unchanged, no
shipped experiment or vehicle file changed, replay.html's sha256 unchanged. Tests run on
synthetic directories or a 1.5 s fixed-guidance run in a temporary folder, never on
results/. Reviewers and gates start the app with a scratch results root, so nothing they
launch is committed (D-SP2-37; protocol section 4, "App runs").

Status marks: `[ ]` not started, `[~]` in progress, `[x]` done, `[!]` blocked or needs a
decision.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| A0 | Plan and mock-ups | the design ([inputs/2026-10-05-SP2-design.md](inputs/2026-10-05-SP2-design.md)), this file | - | The user's approval (given 2026-10-05) | [x] | a5b8133 (the start commit, "Start SP2: status in progress") |
| A1 | run_data; plots and replay switched; KI-002, KI-016, KI-017 | run_data.py, plots.py, replay.py, physics.md, CLAUDE.md | test_run_data.py (27 of survey 06: readers, roles, the four fairing cases, output-path corners, the runs-block digest, import rule) | Reference page, seven more and the five gallery pages byte-identical; existing tests unchanged; no `plots._` call in replay.py | [x] | 9579f89 |
| A1b | Pillow in the dev extra (KI-018) | pyproject.toml, uv.lock | - | Lock diff is that line only; exact golden tier passes; reference sha256 unchanged | [ ] | |
| A1a | Caveat wording at source (KI-029) | replay.py, plots.py, site/build.py, site/examples/ | per-clause tests (22 t sled, failed run, q-alpha below the baseline, paired pad, an offloaded push) | The gate of the design's section 4.3 (below the table); honesty review; the diff against the reference page recorded | [ ] | |
| A2 | display.py, display files, payload, physics.md section | display.py, scene.py, configs/display/ | test_display.py (coast energy, angular momentum and the closed form; the coast reproduces the recorded staging-coast rows; separation state; row selection; transform), test_scene.py (strict JSON, nulls in the shaft, null payload, bound runs and cases, zero-offload pad control, offload caveats, refusals) | Independent comparison of the payload with the CSVs of the reference directory, silo_cold_s1, silo_cold_lag and silo_instant; the load-time checks pass on every run folder of every complete planar directory on disk (56 today), results in the session log; every display number sourced or assumed | [ ] | |
| A3 | Scene part 1 | scene.html, scene.py, cli.py | template checks (ASCII, package data, one data token, helper pin, sink scan, contrast, `parseHash` and `node --check`) | State-hook values and painted points within criterion 5 at push start, mid-push, release, ignition, ramp end and the kick for the five runs, and the whole of silo_failed; the exported page makes no request | [ ] | |
| A3b | Scene part 2, two panels | scene.html | rate law, camera and marker checks through node | The remaining times of criterion 5; criterion 16 (watchable); both themes | [ ] | |
| | Checkpoint 1: `launchsim scene` is complete | | | | | |
| A4 | appform and `run_launch` | appform.py, app.py, config.py, summary.py | each preset resolves to the committed variant; every refusal one line and nothing written; key-by-key equality with `run_experiment`; faked-seam offload launch with a fresh and a cached pad; counting test; banner and both git states; one slow real launch with a stage-1 solve | Fast and slow suites; honesty review of the banner | [ ] | |
| A4b | Server | app.py, cli.py | raw-socket guard table (the survey's 38 cases plus Sec-Fetch-Site, path decoding, body limits, two simultaneous launches); header table; injection test; leak test; Ctrl+Break subprocess test | Only 127.0.0.1 bound and a second server fails; no client path opened; an interrupted job leaves FAILED.txt; security review | [ ] | |
| A5 | App page | app.html, app.py | form mapping per field; disabled-state matrix; panel text per launch kind | Every preset fills the form and passes the dry run; three launches by click (plain, stage-1 solve, refusal); a driver posts every preset and every setting of criterion 2 to a scratch root and records directory, resolved config and wall time; honesty review of the panel | [ ] | |
| | Checkpoint 2: the request is met | | | | | |
| A6v | Video | video.py, app.html, app.py | PNG header checks, limits, fake encoders (hung, early exit), reservation | An MP4 of pad beside silo_cold_s1 from the app; frame count = fps x seconds; footer text checked on a sampled frame; security review | [ ] | |
| A7 | Full visual QA, demo launches, gallery material | docs/demos/SP2/, site/ | the QA table | Every row passes or is a logged deviation; screenshots in both themes; the exported scene page, the gallery entry, the frame rule and the video reviewed; site builds | [ ] | |
| A8 | Close | docs, TODO.md, memory | full suite | The 17 exit criteria; close-out question to the user; SP7's file fact-checked after the last code commit; handoff, memory, cold read; push and Pages | [ ] | |

"Criterion" in the table means an exit criterion of section 8; "survey 06" and "the
survey's 38 cases" are inputs/2026-10-05-SP2-survey/06-run-data-refactor-plan.md and
07-server-and-worker.md; what each step builds is in the design's section 4.

If room runs out, in this order and each put to the user when it happens: the video export
(logged as a backlog item, criterion 15's second half open only with the user's
acceptance); the seven screening presets; ticker and gauge polish. An in-progress handoff
is written at a checkpoint if A7 and A8 would no longer fit.

A1a's gate (the design's section 4.3): the build reports no fix-table warning; each
editorial replacement string is in the built offload pages; the diff of the five built
pages before and after is recorded; a page of silo_sled_22t alone does not say "massless".

The reference page of A1 and of exit criterion 10. "The reference directory" is
`results/silo_screening_2d/20260930T175743Z` with the runs `pad`, `silo_cold`,
`silo_hot_ramp_on_track` and `silo_failed` (four is the page's limit). The page made
"before the refactor" is generated at the SP2 start commit, as the first action of A1 and
before any file is edited:

    uv run python -m launchsim replay results/silo_screening_2d/20260930T175743Z --runs pad silo_cold silo_hot_ramp_on_track silo_failed --out <scratchpad>/reference_replay.html

Record its sha256 and the commit in the session log and keep the file in the scratchpad
for the session. The expected value at b69ff0c is 247,949 bytes, sha256
3ca23dc5ce6532e6b9e3fd4656ab4846bcb4cdddfced7a077ce05c9411fd1eab: the A0 survey generated
the page at b69ff0c, by this command and in memory, and got that value, the same as at
b3150c1 (survey 06, section 0). If A1 gets another value, find the cause before editing
anything. On a fresh clone the CSVs are missing: re-run the experiment first (entry
criterion 6) and use the new directory, naming it in the session log.

The reference page exercises only the `run` role, so more pages are compared in A1 (the
design's section 4.2): seven more pages that cover the bound, paired-baseline, case,
offload and second-calibration branches, hashed before and after; and the five committed
gallery pages, which, regenerated with their recorded commands, must leave
`git status --porcelain site/examples` empty. Kept as they are: the six `-0.0` tokens, the
key order, the `pd.read_csv` arguments.

Notes on the order. A1 comes first because the scene, the app and the two existing
commands all stand on it, and its gate (byte-identical pages) is cheap. A1b is its own
small step: its gate is that the lock diff is one line. A1a comes after A1's
byte-identical gate, never inside it, and before the scene, so that the scene takes its
caveats from wording already fixed at source (D-SP2-23); it changes the replay page's
bytes on purpose, and the diff against the reference page is recorded for exit criterion
10. The scene (A2, A3, A3b) is built and checked on recorded directories before the
server exists, so a drawing fault is never mixed up with a server fault. The page
contract is fixed before A3, and the camera and the close-up are in A3, because A3's gate
checks flights that leave the first view within seconds; A3b adds the rest of the flight,
the second panel, the rate law and the themes. Checkpoint 1 is a complete
`launchsim scene`. The form builder and the launch function (A4) come before the server
(A4b), which needs them, and the page (A5) comes last; the app then only has to produce a
directory and hand it to a scene that already works. Checkpoint 2 is the user's request
met. The video (A6v) comes after checkpoint 2 because it is the first item to be deferred
if room runs out. Public-site material is built and reviewed in A7, so that the close
(A8) does not overrun.

## 8. Exit criteria

Approved by the user on 2026-10-05 (step A0, D-SP2-38); the tolerances are fixed. The 17
criteria below are those of the design
([inputs/2026-10-05-SP2-design.md](inputs/2026-10-05-SP2-design.md), section 6), word for
word. They replace the 14 this brief proposed; the paragraph after the list says what
changed. Each is checked by an independent gate at the end of the phase. The phase closes
with an open criterion only if the user accepts the miss, and the miss is logged.

How to read the section numbers inside them: "section 5.7" is this file's; "section 4.4"
and "section 4.9" are the design's (the load-time checks of the tank series, and the list
of what the scene shows that the model does not support); "survey 08" is
inputs/2026-10-05-SP2-survey/08-docs-site-tests.md.

1. The app starts: 127.0.0.1 only, URL printed, a second server on the same port fails.
2. A launch works for: exit speed; net acceleration; each of the five ramp-start ways; a
   solved stage-1 offload; an imposed offload; a stage-2 offload with its pad control; a
   structural penalty; the screening presets. Each writes a normal results directory whose
   resolved config holds the form's values, and its scene plays, or the page says why there
   is none.
3. Same numbers as the CLI: the silo_cold_s1 preset launched from the app gives the payload
   capacity and offload of results/silo_offload_2d/20261003T112934Z within 0.002 kg.
4. Refusals: each bad input of section 5.7 gives a one-line message and writes nothing;
   1e400, a 400-digit integer, `true` and "3" in a number field are refused; a second
   Launch during a job and a launch after the code changed are refused.
5. The scene matches the run data, for pad, silo_cold, silo_hot_ramp_on_track, silo_cold_s1
   and silo_failed, at push start, mid-push, release, ignition, ramp end, the kick, MECO,
   staging, the fairing drop, cutoff or impact and at least five times between. At an event
   time the page shows the later of the two CSV rows. Altitude within the larger of 0.5%
   and 1 m; downrange within the larger of 0.5% and 10 m; attitude within 0.5 deg wherever
   the model defines one (thrust on, hold, on the track), measured from the painted base
   and nose; the base painted within 1 px of the transform; thrust on equal to the event
   rule at every CSV row; plume fraction within 0.02 at every CSV row except a run's last;
   the stage exact; each event at its row time within 1e-6 s. The payload builder checks
   the data half of this at every CSV row.
6. The offload is visible and right: every tank starts at one minus its offload fraction
   within 1e-4 of the full load; the stage-1 tank reads under 1 kg at the stage-1
   `propellant` event; the tank checks of section 4.4 hold at every row; the rebuilt stack
   mass equals `m_kg` within 1 kg (the interpolation and rounding check).
7. Honest labels: the page names every item of section 4.9; app runs are marked exploratory
   on the page, in metrics.json, in summary.md (with the server-start git state), in the
   replay and animation of that directory and in every video frame; caveats are those of
   the run shown and include every caveat the replay page gives; stage-2 and both solves
   are net of the pad control as a property of the vehicle model; an imposed offload is
   never called saved; shapes meet 3:1 and text 4.5:1 in both themes.
8. Browse and replay: the app lists the recorded directories and plays
   silo_screening_2d/20260930T175743Z and silo_offload_2d/20261003T112934Z; a 1-D
   directory, a sweep, a failed, an incomplete and an unreadable directory stay listed with
   their reason and the listing stays usable.
9. The pad is cached: a second launch does not fly the baseline again.
10. Loader and fixes: animate and replay pass their unchanged tests on run_data; at A1's
    commit the reference page was byte-identical; at the close it differs only by A1a's
    wording and the exploratory line, as a recorded diff shows; one output-path rule; no
    private cross-module call; mass before and after for the four fairing cases;
    replay.html unchanged.
11. Tests and guards: new tests in the fast tier (one slow launch); full suite green; ruff
    clean; golden 1-D, digest pin and output capture unchanged; no shipped experiment or
    vehicle file changed; the import guard holds; no resource warning from the server.
12. Dependencies: Pillow in the dev extra, justified; nothing else new. The app, the scene
    and the exported page make no request off the machine (a template scan, the page's
    Content-Security-Policy, and the browser's network list).
13. Documents and public face current: CLAUDE.md, README (quick start, status), the manual
    (the app chapter and the pages survey 08 lists), physics.md, TODO.md, the board; the
    landing page, the deck and its PDF, the gallery with an exported scene and a video made
    from the recorded directories; the gallery's "nothing is re-simulated" sentence
    reworded; site built with no broken link; main pushed and Pages green; SP7's file
    fact-checked; handoff and prompt written; memory updated.
14. Demo recorded under docs/demos/SP2/: commands (the headless Edge ones included),
    screenshots in both themes, the QA table, the API record of one launch and one refusal
    with wall-clock times.
15. Export: `launchsim scene` writes a standalone page that plays with no server; the app
    exports an MP4 of a two-panel scene with the caveat footer.
16. Watchable, read through the state hook for pad beside silo_cold_s1 and pad beside
    silo_cold: the close-up vehicle is at least 120 px long at every time; the nose moves
    at least 4 px at each run's kick; staging, stage-2 ignition and the fairing drop each
    stay on screen at least 1.5 wall seconds under the default rate; separated bodies are
    drawn at least 4 px across.
17. Requests from another origin are refused: a page on another loopback port or another
    host cannot start a launch, post a frame or make the server build a scene (the guard
    table in the fast suite, and once with a real browser in the demo).

Changes against the brief's 14: 1 (+ second server); 2 (+ screening presets; a run that did
not fly); 3 (compared with SP1's recorded run instead of a scratch YAML); 4 (+ number
types, code change); 5 (attitude only where the model defines one; "thrust on or off
exactly outside a ramp" replaced by the event rule and a per-row plume tolerance, because a
lag startup has no ramp end; painted points added; events at 1e-6 s); 6 (1% tightened to
1e-4; tank checks added, because the mass rebuild alone is an identity); 7 (+ the mark on
every export; contrast); 8 (+ incomplete and unreadable); 10 (the allowed differences
named); 12 (Pillow); 15, 16 and 17 new.

## 9. Demo script

Output goes to `docs/demos/SP2/`. The browser pane renders a local file as a static snapshot
without JavaScript, so every page is opened through a server on 127.0.0.1; the app is such a
server.

    uv run python -m launchsim app

Then, at the printed URL:

1. Choose the preset for the 3 g / 100 m cold-start silo and press Launch. Look at: the
   progress line; the new directory under the results root; the scene starting by itself.
2. Watch the first 30 s at 1x. Look at: the pad held down with its engines lit while the
   silo's rocket rises unlit on the carriage; release; the ramp starting where the form put
   it; the plume growing over the ramp; the kick.
3. Let it run to orbit. Look at: the camera zooming out, the scale bar, staging with stage 1
   falling away (labelled display-only), the fairing halves, cutoff, the HUD.
4. Choose "solve the largest stage-1 offload" and launch again. Look at: the progress line
   over the minutes of the solve and the page staying usable; the stage-1 tank starting
   part-full; the earlier MECO; the results panel with the propellant saved, the max-Q
   against the pad's, and the caveats beside them; the pad not being run again. Compare
   the number with docs/findings/RQ1-fuel-offload-2d.md (it should equal SP1's
   `silo_cold_s1` within the tolerance of exit criterion 3, being the same configuration).
5. Add a structural penalty (+8.1 t) and launch. Look at: what is left of the offload.
6. Change the ramp start to a depth, then to a height by event. Look at: the ignition marker
   in the shaft and above the mouth; the requested and achieved values in the panel.
7. Enter a ramp-start depth larger than the stroke. Look at: the refusal message; no new
   directory.
8. Open `silo_offload_2d/20261003T112934Z` from the run browser and play `pad` beside
   `silo_cold_s1`, then `pad__offload_stage1` (the pad control). Look at: the two reaching
   the same orbit with the same payload, the offloaded tank, the pad control's label and
   its full tanks (its offload is 0 kg, so it flies the experiment's vehicle block).
9. Open `silo_screening_2d/20260930T175743Z` and play `silo_failed`. Look at: the fall-back
   and the impact.

If the standalone export is chosen in Q1 (the command name is fixed in A0):

    uv run python -m launchsim scene results/silo_screening_2d/20260930T175743Z --runs pad silo_cold --out docs/demos/SP2/pad_vs_silo_cold_scene.html

Recorded in `docs/demos/SP2/`: a README with the commit and the commands; screenshots of the
steps above in light and dark mode; the visual-QA table (sampled time, value from the CSV,
value read from the page, pass or fail); a text record of the API calls for one launch and
one refusal, with the launch's wall-clock time; the exported scene page if the export
exists. Check with `git status` that the exported page is not ignored (section 5.8 item 4).

**Added by the approved design (2026-10-05).** The steps above stay. The design adds:

10. In every scene, look at the close-up beside the true-scale view of each panel
    (D-SP2-35): the vehicle at a fixed scale with its attitude, plume and tank fills, and,
    at staging and at the fairing drop, the gap and the opening halves, each marked "drawn,
    not computed". In the true-scale view, look at the marker with a heading tick that
    replaces the rocket once its body is under 3 px wide, and at the path trace with its
    event markers.
11. Choose a screening preset (D-SP2-05), for example `silo_sled_22t` or `silo_hot_full`,
    and launch. Look at: the caveats, which are built from the run shown (D-SP2-36); those
    of the 22 t sled do not say that the carriage is massless.
12. Choose the failed-ignition preset (`silo_failed`) and launch. Look at: the status
    banner over the scene, the fall-back, the carriage and rails drawn as outlines, and
    the ticker saying that the planar model has no contact (D-SP2-20).
13. Export a video from the app (step A6v, D-SP2-30): an MP4 of `pad` beside
    `silo_cold_s1`. Look at: "frame n of N" and Cancel during the capture; the path of the
    written file on the page; the caveat footer on the frames, with the exploratory line
    when the directory is an app run.
14. Once, with a real browser: a page served from another loopback port tries to start a
    launch and is refused (exit criterion 17).

The standalone export was chosen (Q1, D-SP2-01) and its command is `launchsim scene`. The
demo page gets a hyphenated file name, because `.gitignore` gains the default output
patterns `*_scene.html` and `*_scene.mp4`, which would also ignore a demo file whose name
ends in `_scene.html`. Use this command instead of the one above:

    uv run python -m launchsim scene results/silo_screening_2d/20260930T175743Z --runs pad silo_cold --out docs/demos/SP2/pad-vs-silo-cold-scene.html

Where the launches go (D-SP2-37; protocol section 4, "App runs"):

- Demo launches are made from a clean tree, after the last code commit, so that their
  directories under `results/app/` record a clean git state. Their summaries are committed
  in their own commit (`SP2 step <k>: app summaries`).
- Review and gate launches start the app with `--results-root <a scratch folder>`, so
  nothing they launch is committed.
- Gallery, deck and manual material comes only from the two recorded directories of exit
  criterion 8, not from an app run.

Also recorded in `docs/demos/SP2/` (exit criterion 14): the headless Edge commands that
wrote the fixed-frame screenshots and the `#qa` state dump.

## 10. Risks and open questions

**Questions SP2's Plan mode puts to the user** (recommendation first, as the user prefers;
the user has often chosen the more ambitious option, so give it fairly with its cost)

| # | Question | Recommendation | Why |
|---|---|---|---|
| Q1 | Should a scene be exportable as a standalone HTML file, and as a video? | HTML export yes (a `launchsim scene` command, like `replay`); video no for now, as a backlog item | The app is the plan (D-SP1-02), and TODO.md (M13) records that a separate scene command is no longer planned, so the export is an addition the user has to choose. It reuses the renderer and the internal page writer that A3 needs anyway (A3's visual QA does not depend on this answer), gives a file to keep, and is the only way to show a scene on the public site: GitHub Pages is static, and the gallery refresh at the close (protocol section 7, item 6) needs a page or a recording. `site/build.py` frames only replay pages, so a scene page needs a frame rule (section 5.9). A video of a canvas needs either capture in the browser or a second renderer; neither is needed to see the launch |
| Q2 | Must the app and the scene work with no internet connection (fonts, any library)? | Yes: no request leaves the machine; the site's token values with system-font fallbacks (the existing `--font-*` stacks); no library for 2-D | A local tool should not depend on a network. The replay page and the site load the three brand fonts from Google Fonts today (TODO.md KI-019). The ambitious option is to vendor the three font families (SIL Open Font License) as woff2 files in the package, so the app matches the brand offline; cost: a few hundred KB, a licence file, and the package-data question. Whether to change the replay page too is part of the question. The three.js question (CDN or vendored) is SP4's |
| Q3 | How are app runs named and kept? | One results root entry for the app (for example `results/app/<UTC timestamp>/`), labelled exploratory, wholly ignored by git including `summary.md`, never deleted by the app; the run browser shows their size | `.gitignore` keeps every run directory's top-level `summary.md` tracked, so app runs would otherwise show up as untracked files and break the clean-tree rule for finding runs. Deleting results needs the user's OK (CLAUDE.md). A plain launch writes two runs of about 3.6 MB of CSV each; a solved stage-1 launch with a paired pad and a pad control writes five (the SP1 bridge directory is 17 MB) |
| Q4 | What are the form's presets? | The configurations of SP1's experiment: the pad alone; `silo_cold` (3 g, 100 m, cold start); `silo_hot_ramp_on_track`; `silo_cold_200m` (200 m at the same exit speed, 76.70717 m/s, about 1.5 g); `silo_cold` with the solved stage-1 offload (`silo_cold_s1`); the fixed 5% and 10% offloads; the penalty values 0, +2, +4, +8.1 t | They are the configurations the findings use, so the app and the notes show the same cases and a preset can be checked against SP1's recorded numbers |
| Q5 | Which vehicle can the form use? | The gate vehicle only (`generic_f9_class_2d.yaml`) | The user asked to stay on the Falcon 9 model. The ambitious option, the README-loads fork as a second choice, is cheap now: SP1 ran the bridge on it (`results/silo_offload_2d_readme/20261003T112956Z`) and `CALIBRATION_RECORDS` carries its record (+8.3%, inside the band); cost: a second energy block (that fork has no sourced fuel split, so its launches would have no energy comparison) and one more form switch |
| Q6 | Offload input: a fixed amount, a solve for the largest, or both; which modes? | Both; fixed is the default; stage-1 solve and fixed cases in the main form; stage-2 and both-stage solves behind an "advanced" switch with the pad control forced on and the vehicle-model label | A fixed offload is one payload search (seconds); a solve with its verification takes about 90-110 s more, plus about 30 s per pad control; stage-2 and both numbers are only honest net of their pad control (D-SP1-10) |
| Q7 | Look of the scene | A schematic cross-section in the brand's palette (section 5.10), with dark mode; the mock-up of A0 is approved before the renderer is built | A realistic rendering would imply detail the model does not have |

**Answers (2026-10-05, step A0).** The user answered all seven; the decisions are logged in
TODO.md.

| # | The user's answer | Decision |
|---|---|---|
| Q1 | A standalone HTML export (`launchsim scene`) and a video. More than the recommendation, which left the video to the backlog; D-SP2-30 fixes how the video is made (MP4 through ffmpeg, from the app) | D-SP2-01 |
| Q2 | Offline, with system fonts; the replay page stays as it is and keeps its font links (D-SP2-34). The recommendation; the fonts are not vendored | D-SP2-02 |
| Q3 | `results/app/<UTC timestamp>/`, with each summary.md tracked. Not the recommendation, which was to ignore them | D-SP2-03 |
| Q3, follow-up | Each app summary carries an exploratory banner; the summaries are committed at step boundaries and before any pre-registered run (D-SP2-37 fixes the commit they go in) | D-SP2-04 |
| Q4 | SP1's configurations plus the Phase 2 screening variants. More than the recommendation | D-SP2-05 |
| Q5 | The gate vehicle only. The recommendation | D-SP2-06 |
| Q6 | Fixed and solved; the stage-2 and both-stage forms under Advanced, with the pad control forced on. The recommendation | D-SP2-07 |
| Q7 | A schematic cross-section as in the mock-up, light and dark. The recommendation; the two mock-ups are saved in inputs/2026-10-05-SP2-mockups/ | D-SP2-08 |

**Open design points for A0 (no user decision needed unless they change scope)**

Each point is marked with the decision that settled it on 2026-10-05 (approved with the
design).

- What run a fixed-offload launch shows. SP1 records a fixed case's run as its own payload
  search at its own P* (SP1 step 7, deviation 2): its figure is P* - P_ref, and its
  decomposition at P_ref is computed in memory by `sim.matched_run` and not written.
  Recommended: show the recorded run with P* - P_ref beside it; a fly-out at P_ref would
  need new code and is not in scope. A solved case's recorded run already flies P_ref
  (0 <= m_res < 0.05 kg). **Settled: D-SP2-27** (as recommended; labelled "imposed
  offload", never "saved").
- Worker thread or child process (section 5.6). Recommended: thread, after measuring how
  responsive the server stays during a 90-110 s solve. **Settled: D-SP2-09** (a thread;
  measured in A0).
- How the cached baseline enters the run path. Recommended: the composition of SP1's
  in-memory path in `app.py`, leaving `results_io.py` unchanged (section 5.6).
  **Settled: D-SP2-10** (as recommended; each cache hit is re-wrapped).
- The git provenance of a long-running server (section 5.6). Recommended: record the git
  state at server start beside the launch-time state, key the baseline cache on it, and
  refuse a launch after a HEAD change. **Settled: D-SP2-11** (the refusal is on a change
  under src, configs, experiments, pyproject.toml or uv.lock, not on any HEAD change).
- A1's compatibility policy (section 5.2). Recommended: re-exports of the old names, the
  two caveat sentences left in their modules, existing tests unchanged.
  **Settled: D-SP2-13.**
- Whether the pad controls (and the paired pad) are cached across launches: needs a hook in
  `planar_offload`. Recommended: no, unless the measured wait bothers the user.
  **Settled: D-SP2-25** (no; only the pad is cached).
- Progress granularity: a coarse stage line without touching the pipeline, or a callback
  in results_io.py or offload.py. Recommended: the coarse line. **Settled: D-SP2-25**
  (the five stages the app owns; no callback).
- Exploratory marking: a new `label` value (with a summary banner) or a provenance field.
  **Settled: D-SP2-12** (a label value, `exploratory`, with a banner).
- Default run selection for a directory with an offload block (proposed: the pad and the
  first solved stage-1 case). **Settled: D-SP2-28** (a rule for any directory).
- Where the display block lives and how it is validated; where the display-only formulas are
  documented. **Settled: D-SP2-18** (`configs/display/`, read by `display.py`); the
  formulas go into a new section of docs/physics.md, "Display-only reconstructions (not
  part of the model)" (design, sections 4.1 and 4.4).
- Whether plots are written for app launches. Recommended: yes by default if the time is
  small against the search, otherwise a form switch; measure first.
  **Settled: D-SP2-26** (no PNG plots; not the recommendation).
- Placement of the carriage's braking section in the drawing (section 5.5).
  **Settled: D-SP2-20.**
- Shared template fragment or deliberate copy between the replay and scene pages.
  **Settled: D-SP2-21** (a deliberate copy of seven helpers, pinned by a test).
- Brand assets in the package (section 5.10) and whether the replay page takes the site's
  contrast tokens. **Settled: D-SP2-33** (the marks are inlined) **and D-SP2-34** (it does
  not, in SP2).
- Whether SP2 takes the replay drive-caveat fix (section 5.8 item 5).
  **Settled: D-SP2-23** (yes, widened into step A1a).
- Port, and whether the command opens the browser itself. **Settled: D-SP2-29** (port
  8765; an `--open` option).

**Risks**

| # | Risk | Recommended resolution |
|---|---|---|
| R1 | SP1's last steps (9 and 10) change code this file relies on | The diff of the header at the start (`git diff --stat b3150c1 HEAD -- src tests configs experiments pyproject.toml .gitignore site/build.py`); re-check the files it lists |
| R2 | An app number is taken for a finding | The exploratory label in the directory, `metrics.json`, `summary.md`, the results panel and the scene; findings only from committed files run from a clean tree; the dirty flag is recorded as usual, with the git state at server start beside it (section 5.6) |
| R3 | The scene looks more certain than the model is: shapes, the spent stage, the carriage and the body axis are not simulated | Every display-only item labelled on the page (exit criterion 7); the display block never read by the run path; a schematic style |
| R4 | The headline shown in the app may not survive the structural-mass model (phase SP7, the phase after SP2 by D-SP1-18) | The structural caveat and the penalty field sit beside every offload number; the max-Q of the offloaded run is shown against the pad's (SP1's run has it above the pad's; see docs/findings/RQ1-fuel-offload-2d.md) |
| R5 | At orbital scale a 3.66 m wide rocket is smaller than a pixel | The enlarged icon with a "not to scale" note, and a scale bar in every panel |
| R6 | The side-by-side clock misleads: the pad's hold and the silo's push have different lengths before release | One stated clock (time after release) in the HUD; A0 may add a second alignment |
| R7 | A CPU-bound solve in a worker thread makes the page sluggish for minutes | Poll for status; measure in A4 with a real stage-1 solve; fall back to a child process |
| R8 | The run-data refactor changes `animate` or `replay` output | The byte-identical replay gate; existing tests; the one intended change (animate's output-path rule) is tested and logged |
| R9 | The replay and scene pages drift apart | A shared fragment, or a test that pins the shared helpers in both templates |
| R10 | App results pile up and untracked summaries break the clean-tree rule | Q3 |
| R11 | A local server is reachable by other software on the machine or by a web page | Loopback binding, Host check, POST for launches, no client-supplied paths (section 5.6); a reviewer checks it in A4 |
| R12 | Scene polish has no natural end | The exit criteria define done; further polish goes to the backlog in TODO.md |
| R13 | Recorded directories from before SP1 lack new metrics or have the mixed fairing convention | Fallbacks in the loader; the reader-side mass normalisation using the `fairing_drop` metric (section 5.8) |
| R14 | Mojibake and invalid JSON, both met before | `charset=utf-8` and `<meta charset>`, ASCII pages, NaN written as null, `allow_nan=False`; tests for each |
| R15 | The spent stage's vacuum coast is wrong in the atmosphere (no drag) | Labelled as display-only and drag-free; the path can be faded out below a stated altitude; not used for any number |
| R16 | An offload launch takes minutes and the user thinks the app hung | The background worker, the progress line with elapsed time and the expected range, one job at a time, the page never blocks (section 5.6) |
| R17 | The public site depends on replay's wording and marker (`site/build.py`: `REPLAY_MARKER`, `REPLAY_TEXT_FIXES`) | Keep the marker; run the site build after any replay text change and at the close; drop the text fix in the same change that fixes replay.py (section 5.8 item 5) |
| R18 | Brand assets live outside the package, so an installed app has no logo or favicon | Inline the mark in the template with a test against `assets/brand/favicon.svg` (section 5.10) |

**The five risks the approved design ranks (2026-10-05; design, section 8)**, in its
order, each with what the design does about it:

1. The session ends before the app exists: two checkpoints, a deferral order, an
   in-progress handoff at a checkpoint (protocol section 10).
2. Renderer rework after QA: the camera is in the first scene step; the page contract is
   fixed before A3.
3. Gates that pollute results/ or cannot run in agent time: a scratch results root, the dry
   run in the browser plus an API driver, the close reusing A5's record when the launch
   code is unchanged.
4. A flaky suite: the launch as a plain function, a faked-seam offload test, one slow
   launch (60-130 s), the server as a context manager, a leak test, Ctrl+Break handling.
5. A close that overruns: public-site material is built and reviewed in A7.

Also from the design's section 8:

- Launch times measured on this machine on 2026-10-05: the pad 18-46 s; a plain launch
  about 50 s; a stage-1 solve launch about 130 s without its pad control (about 30 s
  more). A stage-2 or both-stage pad control is budgeted at 90-110 s by SP1's
  pre-registration and is not yet measured.
- Accepted risk: other local processes and users of this machine can reach the server.
- config.py and summary.py change by a few lines (the label value and its banner), so
  SP7's inventory is re-checked at the close.
- Plan mode froze the background survey agents for 43 minutes; workflows run outside it
  (protocol section 11).

## 11. Session log

**2026-10-05 (session 1).**

- Start checklist (protocol section 3), run at b69ff0c:
  - The tree was clean.
  - Item 3 fails literally in two places, both for a known reason. HEAD's subject is "SP1:
    exit criterion 8 confirmed (pushed 03fe7a7, Pages run 37228086241)", not the
    bookkeeping subject: b69ff0c is one docs-only commit after "Close SP1: trackers,
    handoff, next phase file" (03fe7a7) and records SP1's exit criterion 8 in the SP1
    phase file. And `git diff --stat 5007515 HEAD` lists, beside docs/, TODO.md, CLAUDE.md
    and README.md, pages under site/ (the public-face refresh, d3dc509), which the
    protocol's list of bookkeeping paths does not name. It lists no code, tests, configs,
    experiments or results. The closing commit 5007515 is an ancestor of HEAD.
  - Fast suite: 1264 passed, 35 deselected in 98.55 s.
  - `gh` is authenticated and the last Pages run is green (37228154471).
  - Entry criteria 1 to 10 are met (node v24.11.1, ffmpeg 8.1, Edge installed).
  - The diff of the header lists site/build.py, src/launchsim/plots.py,
    src/launchsim/replay.py and tests/test_animate.py, as the handoff said. Section 6 was
    re-checked against the code (survey 01:
    inputs/2026-10-05-SP2-survey/01-inventory-recheck.md) and the corrections are at its
    top.
  - Open items owned by SP2 in TODO.md: KI-002, KI-016, KI-017, KI-018, KI-019 and KI-029.
    No backlog item targets SP2.
- Step A0 (planning):
  - The two mock-ups (one frame of the scene, one second before release, and the app
    page) were shown in the chat.
  - Q1 to Q7 and a follow-up to Q3 were put to the user and answered (D-SP2-01 to
    D-SP2-08).
  - A nine-part read-only code survey was made at b69ff0c.
  - The first draft of the design was read by six independent reviewers (numerics,
    honesty, compliance, security, delivery, interaction design): 2 blocker, 49 major and
    31 minor findings.
  - The second version, with the findings folded in, was approved by the user, and
    D-SP2-09 to D-SP2-38 with it. Step A0's gate (the user's approval) passed.
  - The inputs were saved under inputs/: 2026-10-05-SP2-design.md, 2026-10-05-SP2-survey/,
    2026-10-05-SP2-review/ and 2026-10-05-SP2-mockups/.
  - Bookkeeping for the start commit ("Start SP2: status in progress"): the status in the
    three places and the handoff line; D-SP2-01 to D-SP2-38 logged in TODO.md, milestone
    M13 corrected, KI-019 re-owned and KI-030 to KI-034 added; this file's sections 3 and
    6 to 13 brought to the approved design; the protocol amended (section 4, "App runs",
    D-SP2-37; section 11, the note below).
- Process note. Plan mode froze the background survey agents from 11:12 to 11:55 local
  time (43 minutes): an agent that writes scratch files cannot work while the session is
  in Plan mode. Workflows run outside Plan mode; enter it only to present a finished plan
  (now in protocol section 11).
- Step A1 (the shared run-data module). First action at the start commit a5b8133, before
  any edit: the reference page (results/silo_screening_2d/20260930T175743Z, runs pad,
  silo_cold, silo_hot_ramp_on_track, silo_failed) is 247,949 bytes, sha256
  3ca23dc5ce6532e6b9e3fd4656ab4846bcb4cdddfced7a077ce05c9411fd1eab (the b3150c1 value);
  seven more pages (the screening default and bound selections, two offload selections, the
  calibration cases, the README-loads offload, the bridge default) and the five gallery
  pages were hashed too, the gallery pages equal to the committed site/examples files.
  Implemented by a workflow (implementer; numerics skeptic and compliance auditor, two
  passes; one fix round; independent gate), then four minor findings fixed. Gate: all 13
  pages byte-identical after the refactor, existing tests unchanged, no `plots._` call in
  replay.py, the four fairing cases on planner rows, run_data loads no matplotlib; fast
  suite 1372 passed, 35 deselected; ruff clean; replay.html untouched. Two deliberate
  animate changes (D-SP2-14). Reviewers also checked 95 further replay selections over all
  56 planar run folders (byte-identical) and animate's loaded data on 76 selections
  (identical). Commit 9579f89. KI-002, KI-016 and KI-017 closed; KI-003 reworded.
- Next: step A1b (Pillow in the dev extra), then A1a (caveat wording at source).

## 12. Deviations from the plan

The changes the SP1 close-out fact-check made to this file on 2026-10-03 are corrections
of the brief to the code as SP1 left it, not deviations of SP2; they are listed in section
6, under "The inventory as checked at b3150c1".

Step A0 (2026-10-05): what the approved design changes against this brief. The user
approved these with the design (D-SP2-01 to D-SP2-38). They are listed because sections 1
to 5 still describe the brief's proposal.

1. **Step table.** Against the brief's A0 to A8: A1b (Pillow in the dev extra) and A1a
   (caveat wording at source) are added after A1. A3 is split into A3 and A3b, with the
   camera law and the close-up in A3 (the brief had a basic camera in A3 and the zoom out
   to Earth's curvature in A6). A4 is split into A4 (the launch function, with the form
   builder moved forward from A5) and A4b (the server). The brief's A6 (side by side and
   camera polish) is merged into A3b. A6v (the video) is added. The public-site material
   moves from the close (A8) into A7. Two checkpoints and a deferral order are new.
   Reasons, from the delivery review of the first draft
   (inputs/2026-10-05-SP2-review/05-delivery.md): a first renderer step gated on flights
   it has no camera to show, a server step that needs the form builder of the step after
   it, and no cut line if room runs out. The loop gains a security reviewer on A4b and
   A6v, the standing gate that replay.html's sha256 is unchanged, and the rule that tests
   run on synthetic directories or a short run in a temporary folder, never on results/.
2. **Exit criteria.** 17 instead of 14 (D-SP2-38). The changes are listed item by item at
   the end of section 8 ("Changes against the brief's 14"): criteria 15 (export), 16
   (watchable) and 17 (requests from another origin) are new, and criteria 1 to 8, 10 and
   12 changed. The reason D-SP2-38 gives: three of the brief's tolerances were
   unmeasurable or vacuous on recorded data. Two the design explains: the exact thrust-on
   test "outside a startup ramp" (a lag startup has no ramp end) and the stack-mass
   rebuild of criterion 6 (alone it is an identity). Not in the design's paragraph, found
   by comparing with the brief's text: criterion 11 also gains the import guard and "no
   resource warning from the server"; criterion 13 gains physics.md by name, the exported
   scene and the video in the gallery (made from the recorded directories) and the
   reworded "nothing is re-simulated" sentence; criterion 14 names what the demo records;
   criterion 9 is shortened (the counting test is in step A4's tests; the timing in the
   demo record is no longer asked for).
3. **Time grid** (D-SP2-16, against section 5.3). The scene's grid is a selection of CSV
   rows, never a resample. The brief proposed the replay's grid plus the event times, with
   linear interpolation; that grid misses the brief's own criterion on recorded data
   (pitch by 10.7 deg, plume by 0.98, mass by 29.8 t).
4. **No PNG plots for app launches** (D-SP2-26). A normal results directory has plots
   (CLAUDE.md, "Experiments and reporting"), and section 10 recommended writing them by
   default. An app launch writes none (`run_launch(..., plots=False)`): a PNG of an
   exploratory run would carry no mark, and the scene replaces it.
5. **App summaries are tracked** (D-SP2-03, the user's answer to Q3), against the brief's
   recommendation to ignore `results/app/` wholly. What follows from it: the exploratory
   banner and the commit points (D-SP2-04), a commit of their own, scratch results roots
   for reviews and gates (D-SP2-37), and the amendment of the session protocol.
6. **A wider A1a** (D-SP2-23). The brief's item (section 5.8 item 5) was one sentence of
   `replay.drive_caveat`, to be taken or left. A1a makes the drive caveat data-driven and
   also corrects, at source, the structure caveat, the paired-pad label and note, the
   comparison note, the rounding, the subtitle and one verb; the five gallery pages are
   regenerated. site/build.py keeps its three template canvas patches (replay.html is
   frozen in SP2; TODO.md KI-031) and its editorial additions.
7. **MP4 only** (D-SP2-30). The brief had video export out of scope unless the user asked
   for it; the user asked (Q1, D-SP2-01). The design delivers an MP4 through ffmpeg from
   the app, and no GIF from the app and no CLI video command.
8. **Display geometry in `display.py`, not in `config.py`** (D-SP2-18). The brief's step
   A2 listed `config.py` (display model) among its files. The display files are read by a
   new pure module; config.py changes in SP2 only by the `exploratory` label value.
9. **Player helpers** (D-SP2-21, against sections 5.4 and 5.9). The brief proposed reusing
   the replay page's clock, scrubber and rate select as they are, through a shared
   fragment or a guarded copy. Seven helpers are copied verbatim and pinned by a test
   (`readPalette`, `idxAt`, `valAt`, `phaseAt`, `setupCanvas`, `tick`, `setPlaying`), and
   the scene has its own rate law instead of the replay's Auto rate.

Correction to the design (a record, not edited): its section 4.6 says "the video routes of
4.9"; the video routes are in its section 4.8.

## 13. Prompt to start this phase

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

The prompt above started the session of 2026-10-05 and is kept unchanged (the handoff
holds the same text). It predates the approved design: where it says 14 exit criteria,
section 8 now has 17.

**Prompt to resume this phase** (protocol section 10; paste it into a fresh Claude Code
session opened in this folder if a session ends before SP2 is complete):

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP2-launch-app-2d-scene.md with its step table
> (section 7) and its session log (section 11), CLAUDE.md, TODO.md, README.md, and the
> memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links. Then read the approved design,
> docs/phases/inputs/2026-10-05-SP2-design.md, and the survey reports under
> docs/phases/inputs/2026-10-05-SP2-survey/ that the step in hand names.
>
> We are resuming phase SP2 of launch-assist-sim: the local app with the 2-D launch scene.
> SP2 is in progress. The approved design is
> docs/phases/inputs/2026-10-05-SP2-design.md; it supersedes sections 5, 7 and 8 of the
> brief where they differ, and its decisions are D-SP2-01 to D-SP2-38 in TODO.md. Resume
> at the first step of the table that is not marked [x], and never repeat a passed gate.
> Run the start checklist of protocol section 3 (for a phase in progress, item 3 is the
> check of section 10: every [x] row has its commit in `git log`, and the tree is clean or
> holds only tracker edits) and skip the status change of item 8. Add your own dated entry
> to the session log. Keep the step loop and the standing gates of section 7, and report
> anything that undercuts the hypothesis, and anything the scene would show that the model
> does not support, as plainly as the rest.
