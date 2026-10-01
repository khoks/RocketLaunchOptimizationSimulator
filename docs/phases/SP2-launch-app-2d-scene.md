# SP2: Local app and 2-D launch scene

Status: not started

Written 2026-09-30 in the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md), section
"SP2: local app and 2-D scene") and the code survey
([inputs/2026-09-30-survey-animate-replay-visuals.md](inputs/2026-09-30-survey-animate-replay-visuals.md)).
Line numbers in section 6 were checked at commit 2eebcae on 2026-09-30. SP1 edits several of
the files named here, so SP1's close-out (its step 10) re-checks this file against the code
as it then is, and finalises the prompt in section 13. How a session runs:
[../process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Program board:
[README.md](README.md).

This file is a brief, not the detailed design. The detailed design is made in SP2's own
Plan mode (step A0) and approved by the user before any code is written.

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
- sets where the stage-1 thrust ramp starts, in any of five ways: by time, by depth on the
  push, by speed on the push, by height above the mouth found by an event, by height above
  the mouth from the closed form;
- sets a stage-1 and a stage-2 propellant offload and an assumed structural penalty (extra
  stage-1 dry mass on the assisted run);
- presses Launch, and watches an animated 2-D scene of the pad launch and the silo launch
  side by side;
- browses the recorded run directories under `results/` and replays any planar one as a
  scene.

**What you can see at the end.**

- The app page at `http://127.0.0.1:<port>/`: a form, a Launch button, a progress line, a
  results panel with the caveats beside the numbers, and the scene.
- The scene: a silo cross-section with rings and a carriage, the rocket drawn to scale with
  its attitude, a plume that follows the thrust, tank fill levels (an offloaded stage starts
  visibly part-full), hold-down and release, the kick, staging with stage 1 falling away,
  the fairing halves, a camera that goes from the close-up to Earth's curvature, and a HUD.
- A normal results directory for every launch, labelled exploratory.
- A recorded demo under `docs/demos/SP2/`.

What SP2 does not show: anything in 3-D (SP4), and no new research number. A number seen in
the app is exploratory; findings come only from committed experiment files run from a clean
tree.

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
5. The app: a standard-library HTTP server bound to 127.0.0.1, a job runner that uses the
   same resolve and run path as the CLI, a cached pad baseline, the form, the launch flow,
   the run browser.
6. The fixes listed in section 5.8 (fairing event mass convention, output-path rule
   mismatch, private helpers).
7. Tests for the payload, the server API and the form-to-config mapping; visual QA against
   run data; the demo; the trackers, CLAUDE.md (commands, layout, the list of modules allowed
   to do I/O) and the README quick start, which today says there is no graphical interface.
8. Closing the phase per the session protocol: SP3's phase file fact-checked, handoff and
   prompt for SP3, memory.

**Out of scope**

- 3-D of any kind: the globe scene is SP4, the 3-D dynamics are SP3, SP5 and SP6.
- Any change to the equations of motion, frames, integrator settings, loss accounting,
  search or guidance. SP2 reads results; it does not change how they are produced. The one
  place where SP2 could touch event logging is the fairing event's mass convention; the
  recommended route (section 5.8) fixes it in the reader and leaves the validated planner
  alone.
- New assist models, a throttle, a structural-mass model (README Phase 3).
- New findings. No app run is cited in `docs/findings/`.
- Sweeps from the form. One Launch runs one configuration against the pad.
- Remote access, accounts, several users, a job queue. The server listens on 127.0.0.1 only
  and runs one job at a time.
- Editing a shipped experiment or vehicle file. The app builds its experiment in memory.
- Video export of the scene, unless the user asks for it in A0 (section 10, question Q1).

## 3. Decisions already taken

Decision ids are defined in TODO.md's decisions log; the text there is authoritative.

| Id | What it fixes for SP2 |
|---|---|
| D-SP1-02 | The visual tool is a local app first: form, Launch button, scenes inside it |
| D-SP1-07 | Order: SP2 comes after the settings, the offload solver and the planar headline (SP1), and before any 3-D work |
| D-SP1-08 | One fresh session for SP2; it is tested, refined and completed before SP3; it prepares SP3's documents, memory and prompt |
| D-SP1-05 | Form: `stroke_m` with exactly one of `net_accel_g` or `exit_speed_mps` |
| D-SP1-06 | Form: the ramp start by time; by depth or speed on the push; by height above the mouth by event; by height by closed form |
| D-SP1-03 | Form: offload of stage 1, stage 2, or both; tanks partly filled, dry mass unchanged; fixed payload = the full-load pad's payload capacity on the same vehicle and 200 km orbit |
| D-SP1-04 | Form: the structural penalty is an assumed extra stage-1 dry mass on the assisted run (+2, +4, +8.1 t are the rows SP1 reports) |
| D-SP1-09 | The offload is an `offload:` block and a post-pass, so the app passes it in the experiment dict; no `search.figure_of_merit` value changes |
| D-SP1-10 | Every offload mode is also solved on the pad; stage-2 and both-stage numbers are shown net of the pad control; stage 1 is the only headline |
| D-SP1-01 | 3-D is true dynamics in later phases; SP2 builds the run-data module and the payload so that a later model's time series (a superset of the planar columns) can be added without a rewrite |

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

Standing rules that bind the design (CLAUDE.md): the calibrated vehicle file is never edited;
a results directory is never overwritten and nothing in `results/` is deleted without asking;
no magic numbers outside `constants.py` and configs; I/O lives only in the listed modules;
every new dependency is justified in one line; caveats are reported as plainly as results.

## 4. Entry criteria

All of these are true before the SP2 session writes code. The session checks them at its
start and records the check in section 11.

1. SP1 is closed: `docs/phases/README.md` shows SP1 done with its closing commit, and each
   SP1 exit criterion passed its gate or carries a user-accepted, logged miss.
2. The settings exist and their tests pass:
   - `assist.exit_speed_mps` as the alternative to `assist.net_accel_g`;
   - the stage-1 ramp-start triggers `at_depth_m`, `at_speed_mps`, and `at_height_m` with
     `height_method: event | closed_form`, beside the existing `t_ign_s` with `reference`;
   - the `offload:` experiment block with solved and fixed cases, the stage-2 pre-offload and
     the assumed added stage-1 dry mass;
   - the preflight check that refuses a bad configuration before a results directory is made.
3. An entry point runs an experiment given as an in-memory dict (no YAML file on disk for
   the experiment), and SP1 has a test for it.
4. `launchsim replay` accepts a results directory that holds offload runs.
5. The planar metrics the form and HUD read exist: `net_accel_g`, `net_accel_mps2`,
   `stroke_m`, and the requested and achieved ramp-start values.
6. Run data is on disk (CSV files are not tracked in git):
   - `results/silo_screening_2d/20260930T175743Z` (12 runs with `timeseries.csv`), or a
     re-run of it;
   - at least one results directory of `experiments/silo_offload_2d.yaml` from SP1.
7. The tree is clean; `uv run pytest -q -m "not slow"` is green; ruff is clean; the golden
   1-D tests and SP1's planar digest pin pass.
8. Section 6 of this file has been re-checked against the code at SP1's closing commit, and
   the prompt in section 13 has been finalised by the SP1 session.
9. Tools: a browser reachable through 127.0.0.1. Optional: node (for `node --check` of the
   page scripts; the test is skipped without it) and ffmpeg (only if video export is chosen).

## 5. Design

The brief below is what the plan approved plus the constraints the survey found. Full text:
the plan's section "SP2: local app and 2-D scene" and the survey's sections 1-10 and its
"Recommendation". Items marked "proposed" are this file's suggestions for A0 to confirm.

### 5.1 Shape of the system

    browser page (form, scene)                         127.0.0.1 only
        |  GET page, GET run list, GET scene payload, POST launch, GET job status
    app server (standard library)
        |-- job runner (one worker)
        |       form values -> experiment dict (in memory)
        |       -> config.resolve_experiment -> preflight -> run path of the CLI
        |       -> results/<experiment>/<UTC timestamp>/   (a normal results directory)
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
  and `check_output`, with one rule for `animate`, `replay` and the scene export
  (section 5.8);
- the planar-directory check with a configurable error type (today `check_planar_run_dir`
  and `check_replay_run_dir` do the same work);
- run discovery and selection (`animation_run_names`, `select_runs`), `run_source` (the role
  of each run folder: run, bound, paired baseline, case, and SP1's offload role),
  `read_series`, and `read_events` returning every row with the mass before and after a drop;
- the resampling helpers (`replay_grid`, `defined_mask`, `series_values`), taking the field
  list as an argument so the scene can add fields;
- `CALIBRATION_RECORDS` and the calibration caveat's data.

`plots.py` and `replay.py` switch to the public names. None of today's loaders carries
`pitch_rad`, `thrust_N`, `thrust_vac_N`, `stage`, the track columns, the assist geometry or
the vehicle masses; the scene payload adds them.

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
| attitude | `pitch_rad` (thrust direction above local horizontal; pi/2 in HOLD; the track angle in ASSIST; along v_rel when unpowered; unwrapped) | rocket rotation; wrapped for display |
| thrust state and size | `thrust_vac_N`, `thrust_N` | plume on or off and its length |
| stage | `stage` | which bodies are attached |
| track | `s_m`, `drive_force_N`, `interface_force_N`, `drive_power_W` (NaN outside ASSIST) | carriage position, HUD |
| mass | `m_kg` with the run's vehicle masses and searched payload | tank fill levels |
| events | every row of `events.csv`, with pre- and post-drop mass | markers, staging, fairing, hold-down release |
| assist geometry | `stroke_m`, `exit_altitude_m`, `track.angle_deg`, `carriage_mass_t`, `brake_decel_g`, `braking_distance_m`, `facility_length_m` | silo drawing |
| separated objects | rebuilt from the `staging` and `fairing` event rows (section 5.5) | spent stage and fairing paths |
| display geometry | the display block (section 5.5) | shapes |

Design constraints from the survey:

- **Time grid.** The replay samples every 0.1 s until 40 s after release, then every 1 s,
  and interpolates linearly. A scene has steps that must not be smeared: the mass drop at
  staging, thrust off at MECO, the stage label. Proposed: the grid also contains every event
  time, and step-like fields (`phase`, `stage`, thrust on or off) take the last row at or
  before the sample instead of an interpolated value. Phase boundaries are written twice in
  the CSV; the loader keeps the last of the duplicates, as replay does.
- **Tank levels.** The time series holds one stack mass. Propellant left in a stage is that
  mass minus everything else still attached, using the run's own vehicle block from
  `resolved_config.yaml` (an offloaded run carries its own) and the searched payload from
  `metrics.json` (`payload_kg`), not the vehicle file's nominal payload. The fill fraction is
  taken against the full-load tank, so an offloaded stage starts below full. The payload
  builder checks that the rebuilt stack mass equals `m_kg`.
- **Clock.** Runs are aligned on time after release (`t_rel_release_s`), as in the replay.
  The pad's hold and the silo's push both lie before zero. The HUD says which clock is shown.
- **Frame.** `downrange_m` is an Earth-fixed arc and the scene is drawn in the Earth-fixed
  frame: a point sits at angle downrange/R_E on a circle of radius R_E + altitude
  (docs/handoff/archive/2026-09-30-phases-0-2.md, section 4.6). The drawn attitude is the
  pitch measured from the local horizontal at that point. R_E comes from `constants.py`.
- **Size.** The replay page for four runs is 300,810 bytes, of which 268,817 bytes are JSON
  (measured). The scene adds about five series per run; the payload should stay well under
  1 MB for four runs (estimate, to measure in A2).
- **Old directories.** Runs recorded before SP1 lack SP1's new metrics; the loader falls
  back to the config keys, as SP1's replay change does.
- **Failed runs.** `silo_failed` (371 rows, 372 lines with the header; ends in `impact`)
  must load and play. Its `gamma_rel_rad` is unwrapped past pi on the fall-back (TODO.md
  KI-001); angles are wrapped for display.

### 5.4 Scene content

Everything below is drawn from the payload. Items that the simulator does not model are
display-only and are labelled as such on the page (section 5.5).

- **Silo cross-section:** the shaft from the mouth down to the launch depth (`stroke_m`), the
  mouth at `exit_altitude_m`, rings along the shaft, the carriage moving with `s_m` during
  ASSIST, the floor label with the depth.
- **Pad:** a mount and hold-down clamps, released at the `release` event.
- **Rocket:** drawn to scale, both stages and the fairing, rotated by the attitude.
- **Plume:** on when the stage's thrust is on; length from `thrust_vac_N` relative to the
  stage's full vacuum thrust, so the startup ramp is visible.
- **Tank fill levels:** per stage, so the offload is visible from the first frame.
- **Events:** push start, ignition, ramp end, release, liftoff, kick start and end, MECO
  (`propellant`), staging, fairing, cutoff, apex, impact, failed ignition; plus the
  ramp-start trigger event SP1 adds for `height_method: event`.
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
  recorded directories (proposed: two panels by default, toggles for the others).
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
| Spent stage 1 after staging | A ballistic coast from the staging event state. The state is rebuilt from the event rows: r = R_E + alt, v_r = V_rel sin(gamma), u = V_rel cos(gamma), v_theta = u + omega_p r, theta = downrange/R_E + omega_p (t - t_fs), with omega_p = omega_E cos(lat) sin(az). Check: hypot(v_r, v_theta) equals the row's `speed_inertial_mps` (about 3049 against 3049.68 m/s on the pad's staging row). Proposed: a vacuum coast under mu/r^2 with no drag and no attitude, as a pure function with an energy and angular-momentum test |
| Dropped stage-1 mass | `propellant` row mass minus `staging` row mass (22,200 kg on the pad run, equal to the stage-1 dry mass). When the fairing leaves at staging (rule `staging`, or the heating criterion already met there) the staging row is logged after both drops, so the difference also contains the fairing mass; subtract it using the run's vehicle block |
| Fairing halves after the drop | The same coast from the `fairing` event state; the sideways separation is a drawing choice |
| Carriage after release | Not recorded; only `braking_distance_m` is known (60 m at 5 g on the shipped silo) and where the braking section sits is not modelled. Proposed: draw the carriage slowing at `brake_decel_g` over that distance, with the placement stated as a display choice; A0 decides |
| A carriage of 0 t | The shipped silo runs use a massless carriage; it is drawn anyway and the caveat list says so |
| Body attitude | `pitch_rad` is the thrust direction; a point mass has no body axis. The rocket is drawn along it, and the page says so |
| Plume shape | Length follows thrust; the shape and its growth with altitude are a drawing choice |

The scene's caveat list names every display-only item. It also carries the model caveats the
replay already generates (calibration +14.3%, sweep-optimized and unthrottled guidance, no
structural mass for the push, prescribed-acceleration drive, vented shaft).

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
  job status. A0 fixes the names.
- **Safety of a local server:** requests whose Host is not the loopback address are refused;
  launches are POST only; the client never sends a file path. A results directory is
  addressed by experiment name and timestamp and looked up in the results root's own listing,
  so a request cannot reach outside it.
- **Job runner:** one job at a time; a second Launch while one runs is refused with a clear
  message. Proposed: a worker thread in the server process, so the cached baseline lives in
  memory, with status polled by the page. The alternative is a child process running the CLI,
  which can be cancelled and isolates a crash but cannot share the cache. A0 decides after
  measuring how responsive the server stays during a search.
- **Run path:** the form's values become an experiment dict whose shared blocks (guidance,
  search, checks, integrator, target orbit, site) are copied from a committed experiment
  file, so app runs share the guidance parametrisation, sweep grid and optimizer budget with
  the committed experiments (CLAUDE.md, Experiments). Then `config.resolve_experiment`, SP1's
  preflight, the runs, the offload post-pass, and the usual writers. The form cannot change a
  shared block or the vehicle file.
- **Pad baseline cache:** at 2eebcae, `results_io.run_experiment` always runs the baseline.
  The app needs either an optional pre-computed baseline argument there or its own
  composition of the same pieces (`sim.run_resolved`, `planar_experiment_result`,
  `write_run`). Proposed: the cache is keyed by a digest of the resolved baseline run dict
  and vehicle dict, lives only in the server process, and the cached baseline is written into
  every launch's directory, so each directory is complete and `replay`, `animate` and the
  scene can read it alone.
- **Results directories:** one normal directory per launch (resolved config, git hash,
  metrics, time series, summary). `run_experiment` creates the directory before the runs and
  leaves `FAILED.txt` on an exception; the run browser shows such a directory as failed and
  does not offer it for replay.
- **Exploratory label:** shown in the app, in the scene's caveats, in `summary.md` and in
  `metrics.json`. The experiment `label` field already exists with the values `calibration`
  and `guidance_study` and has validators tied to it (`config.py` 1430-1460); A0 chooses
  between a new label value and a separate provenance field.
- **Time per launch (estimates from the inputs):** a searched planar run takes 7 to 25 s; a
  solved offload case about 33 s; a stage-2 or both-stage solve also needs its pad control;
  the first launch also runs the pad. Machine speed varies about 3x under load. The page
  shows the stage of the job and never blocks.

### 5.7 The form

| Group | Fields | Config keys (after SP1) | Decision |
|---|---|---|---|
| Launch site | pad only, or silo | `assist.model` | - |
| Depth | depth; exit speed or net acceleration (one of the two) | `assist.stroke_m`; `assist.exit_speed_mps` or `assist.net_accel_g` | D-SP1-05 |
| Ramp start | one of: time and its reference; depth below the mouth; speed on the push; height above the mouth by event; height by closed form. Startup kind as in the vehicle default | `ignition.stage1.*` | D-SP1-06 |
| Propellant | stage-1 offload, stage-2 offload (tonnes or percent), or "solve the largest stage-1 offload" | `offload.cases` (`fixed` or `solve`) | D-SP1-03, D-SP1-09, D-SP1-10 |
| Structural penalty | assumed extra stage-1 dry mass on the assisted run | `stage1_dry_mass_added_t` in the offload case | D-SP1-04 |
| Presets | named starting points (section 10, Q4) | - | open |

- Validation is the simulator's own. The form sends the values; `resolve_experiment` and the
  preflight accept or refuse them; the refusal's message is shown beside the form. The page
  may grey out impossible combinations, but the server is the judge.
- Refusals that must work: both exit speed and acceleration given; ramp-start depth beyond
  the stroke; ramp-start speed above the exit speed; a height above the drag-free apex; a
  push-relative trigger on a pad run; an offload larger than the stage's load; a missing or
  non-numeric value. A refused launch writes nothing under `results/`.
- The results panel shows what `summary.md` reports: payload capacity against the pad, or
  with an offload the propellant saved (tonnes, percent of stage 1 and of the total), the
  energy comparison labelled "not an efficiency claim", max-Q against the pad's, felt g on
  the track, facility length, flags. The caveats sit beside the numbers: calibration +14.3%,
  no structural mass for the 4 g push, sweep-optimized and unthrottled guidance, and that the
  max-Q of an offloaded run can exceed the pad's.

### 5.8 Things to fix on the way

1. **Fairing event mass convention (TODO.md KI-016).** At 2eebcae the `fairing` row of
   `events.csv` carries the mass before the drop when the fairing leaves in LTG_BURN (at
   stage-2 ignition, `phases/planar.py` L1253, or during the burn, logged by `_integrate`
   L1305-1311 before the map at L1271), and the mass after both drops when it leaves at
   staging because the heating criterion is already met (L1583, phase COAST_STAGING).
   There is a fourth case: under the rule `fairing_drop: staging` the fairing leaves in
   the staging map and no `fairing` row is written at all (L1575-1583 writes the row only
   when the heating criterion is met); the drop has to be read from the staging row and
   the vehicle's fairing rule. No shipped planar vehicle uses that rule, but the schema
   allows it and the 1-D reference vehicle has it. Recommended: `read_events` in the
   run-data module reports the mass before and after for every drop, telling the cases
   apart by the row's phase and the vehicle's fairing rule. Recorded directories
   already on disk have the mixed convention, so the reader has to handle it in any case.
   Changing what the planner logs touches events in validated code (Plan mode, physics.md in
   the same change, digest pins); do that only if A0 finds a reason the reader cannot cover.
2. **Output-path rule mismatch (TODO.md KI-017).** `plots._results_tree` matches the folder name "results"
   case-sensitively and `plots.check_animation_out` refuses output only inside the run's own
   tree; `replay.results_ancestors` matches case-insensitively and `replay.check_replay_out`
   refuses output inside any folder named results. Recommended: one rule, the stricter one
   (replay's), for `animate`, `replay` and the scene export. This changes `animate`'s
   behaviour in one corner; it is recorded as a deliberate change and tested.
3. **Private helpers and copies (TODO.md KI-002).** `replay.py` calls `plots._results_tree`
   and `plots._is_inside` and copies the JSON/YAML readers; `run_events` duplicates
   `plots._events`; `calibration_caveat` exists twice with different wording. All move to
   public names in the run-data module. The refactor must leave the replay page of a fixed
   directory byte-identical, so the wording is not unified in the same step.
   `CALIBRATION_RECORDS` moves with them (KI-003: it is updated whenever the calibration
   is re-run).
4. **Housekeeping.**
   - `.gitignore` gains the scene's default output pattern (today it has
     `*_animation.mp4`, `*_animation.gif`, `*_replay.html`). These patterns match at any
     depth, so a pattern such as `*_scene.html` would also ignore the demo file
     `docs/demos/SP2/pad_vs_silo_cold_scene.html` of section 9. Add `!docs/demos/**` after
     the patterns (unless SP1's close-out already did), or give demo files names that do
     not match; check with `git status` that the demo files show up.
   - `test_template_ships_as_package_data` covers only the editable install; a second
     template should not make that weaker.
   - KI-018: Pillow is imported by tests/test_animate.py but is not declared in
     pyproject.toml (it arrives through matplotlib). Declare it with the one-line
     justification CLAUDE.md asks for, or re-own the issue in TODO.md; A0 decides, A1 does
     it. Declaring a package that is already installed is not a new dependency in the
     sense of exit criterion 12, but it is logged the same way.
   - KI-019: the replay page's Google Fonts links; decided with question Q2.

### 5.9 Code organisation (recommended by the survey)

| Module | Kind | Content |
|---|---|---|
| `src/launchsim/run_data.py` (new) | I/O, read-only | section 5.2 |
| `src/launchsim/scene.py` (new) | I/O plus pure helpers | payload, display-geometry loading, rebuilt separation states, the display-only coast, page rendering and export |
| `src/launchsim/templates/scene.html` (new) | template | the scene; shares the replay's clock and helpers through a common fragment or a deliberate copy guarded by a test, so the two pages do not drift |
| `src/launchsim/app.py` (new) | I/O | server, job runner, baseline cache, form-to-experiment mapping |
| `src/launchsim/templates/app.html` (new) | template | the form, progress, results panel, run browser, and the scene inside it |
| `src/launchsim/cli.py` | I/O | the `app` command, and `scene` if the export is chosen (Q1) |
| `src/launchsim/plots.py`, `replay.py` | I/O | switch to the run-data module's public names |
| `configs/display/` (new) | config | display geometry, sourced or assumed |
| `tests/test_run_data.py`, `test_scene.py`, `test_app.py` (new) | tests | section 7 |

`replay.py` is already 1,161 lines, most of it caveat and results-table text; the scene gets
its own module instead of growing it. CLAUDE.md lists the modules allowed to do I/O and the
layout; both are updated in SP2's close-out. No JavaScript tooling exists in the project (no
`package.json`, no bundler) and the 2-D scene needs none.

## 6. Inventory of the code this phase touches

Line numbers checked at commit 2eebcae on 2026-09-30 (the survey's numbers, re-checked by
grep for the symbols below). SP1 edits `replay.py`, `metrics_planar.py`, `results_io.py`,
`cli.py`, `config.py`, `sim.py` and `phases/planar.py`; treat every number in those files as
stale until SP1's close-out re-checks this section.

**CLI: `src/launchsim/cli.py` (419 lines)**

| Symbol | Lines | Note for SP2 |
|---|---|---|
| `build_parser` | 56-147 | `add_subparsers` at 63; `animate` parser 81-124; `replay` parser 126-146. A new command adds a parser here and a usage line in the module docstring (11-17) |
| `load_yaml` | 177 | third YAML reader; raises `CliError` |
| `load_experiment` | 240 | reads the experiment and vehicle files, calls `resolve_experiment` and `check_result_names`; the app does the same from a dict |
| `results_root` | 267 | `--results-root`, else `<repo root>/results` |
| `command_run` | 291 | the CLI run path the app must match |
| `command_animate` | 349-381 | catches `plots.AnimationError` |
| `command_replay` | 384-397 | `check_replay_run_dir`, `default_replay_path`, `write_replay_page` |
| `main` | 400-419 | dispatch dict at 406-411; exit 0, 1 (`CliError`, `OSError`, one ASCII `error:` line), 2 (usage) |

**Run path (read by the app, changed by SP1)**

| Symbol | File and lines | Note |
|---|---|---|
| `resolve_experiment(exp_dict, vehicle_dict, load_vehicle=None)` | `config.py` 1858-1918 | takes dicts; the app's entry |
| `ResolvedRun`, `ResolvedExperiment` | `config.py` 1639, 1701 | |
| `ConstantAccelConfig`, `TrackConfig`, `IgnitionConfig` | `config.py` 537, 508, 624 | form fields map to these; SP1 adds keys |
| experiment `label` rules | `config.py` 1347, 1430-1460 | `calibration`, `guidance_study` today |
| `run_experiment(resolved, out_root, plots, only_variant, repo_root, sensitivity)` | `results_io.py` 703 | always runs the baseline; makes the directory before the runs; `FAILED.txt` on an exception |
| `make_run_dir` | `results_io.py` 284 | never reuses a directory; adds `-2`, `-3` on a collision |
| `planar_experiment_result` | `results_io.py` 945 | pure; SP1 adds the offload post-pass here |
| `write_run` | `results_io.py` 597 | the writer of a run directory |
| `git_info` | `results_io.py` 319 | provenance, including the dirty flag |
| `run_resolved` | `sim.py` 841 | one resolved run |

**Replay: `src/launchsim/replay.py` (1,161 lines)**

| Symbol | Lines | Note |
|---|---|---|
| `REPLAY_TEMPLATE`, `REPLAY_DATA_TOKEN` | 59, 61 | `("templates", "replay.html")`, `__REPLAY_DATA__` |
| grid constants | 65-74 | early end 40 s, 0.1 s, then 1 s |
| `REPLAY_COLUMNS`, `SERIES_FIELDS` | 99, 116-125 | eight fields; no pitch, thrust, stage or track columns |
| `_read_json`, `_read_yaml` | 145, 154 | copies of `plots._read_json` (550), `_read_yaml` (559) |
| `check_replay_run_dir` | 163 | needs `metrics.json`, a `runs` dict, `model == "planar_2d"`; rejects 1-D and sweep points |
| `select_runs` | 195 | reuses `plots.animation_run_names`; at most `ANIMATION_MAX_RUNS` (4) |
| `run_source` | 241 | roles: run, bound, paired_baseline, case; SP1 adds an offload role |
| `read_series` | 306 | sorts on `t_rel_release_s`, drops duplicate times keeping the last |
| `_finite`, `replay_grid`, `defined_mask`, `series_values` | 324, 335, 346, 356 | null and resampling logic to share |
| `run_events` | 386 | every event row; duplicates `plots._events` (606) |
| `calibration_caveat` | 593 | second copy at `plots.py` 927, different wording |
| `caveats` | 761 | generated caveat list to reuse |
| `run_record` | 897-977 | per-run metrics for the page |
| `source_text`, `protected_tree` | 980, 1114 | call `plots._results_tree` (984, 1120) and `plots._is_inside` (1121) |
| `replay_data` | 1022 | payload builder |
| `embed_json`, `load_template`, `render_page` | 1083, 1091, 1097 | injection pattern to keep |
| `results_ancestors`, `default_replay_path`, `check_replay_out` | 1105, 1126, 1139 | the stricter output-path rule |
| `write_replay_page` | 1154 | |

**Replay template: `src/launchsim/templates/replay.html` (588 lines)**

| Item | Lines | Note |
|---|---|---|
| Google Fonts links | 7-9 | the page is not offline today (Q2; TODO.md KI-019) |
| data script tag | 197 | `<script type="application/json" id="replay-data">` |
| script (one strict IIFE, canvas 2D, no library) | 198-585 | |
| `MARK_EVENTS` | 213 | propellant, fairing, cutoff, impact |
| `valAt`, `setupCanvas` | 242, 263 | reusable |
| `drawTraj` | 348 | altitude against downrange on a flat axis |
| `drawCloseup` | 370-411 | altitude against time; the shaft is a filled band; no walls, rings, carriage or vehicle |
| `tick`, `setPlaying`, `init` | 516, 526, 539 | playback and wiring; Auto rate at 509-515 |

**Animate: `src/launchsim/plots.py` (1,664 lines)**

| Symbol | Lines | Note |
|---|---|---|
| `AnimationError`, `ANIMATION_MAX_RUNS`, `RESULTS_TREE_NAME` | 309, 321, 344 | |
| `CALIBRATION_RECORDS` | 474-482 | feeds the calibration caveat; update when the calibration is re-run (TODO.md KI-003) |
| `AnimationRun`, `ANIMATION_COLUMNS` | 499, 536 | animate's loader type; no pitch, thrust or track columns |
| `animation_run_names`, `check_planar_run_dir` | 568, 584 | run discovery; the planar check |
| `_events`, `read_animation_run`, `load_animation_runs` | 606, 633, 665 | |
| `ascent_time_map` | 719 | animate's piecewise timeline (not used by the replay page) |
| `_results_tree`, `_is_inside` | 780, 793 | private helpers used by `replay.py` |
| `default_animation_path`, `check_animation_out` | 798, 814 | the looser output-path rule |
| `frame_geometry`, `write_ascent_animation` | 838, 1602-1664 | FFMpegWriter (h264) or PillowWriter; no blitting, about 4 minutes for 600 frames at 1280 px |

Figures in `plots.py` are built from `matplotlib.figure.Figure` and saved through the Agg
canvas (module docstring), not through pyplot's global state.

**Recorded data**

| Item | Where | Note |
|---|---|---|
| `PLANAR_TIMESERIES_COLUMNS` | `metrics_planar.py` 329 | sampled every 0.05 s (`sample_dt_s`, `config.py` 665); about 10.8k rows and 3.6 MB per run |
| `PLANAR_EVENT_COLUMNS` | `metrics_planar.py` 369 | `t_s` (absolute), `event`, `phase`, `stage`, `alt_m`, `downrange_m`, `speed_rel_mps`, `speed_inertial_mps`, `gamma_rel_rad`, `m_kg` |
| `TRACK_COLUMNS` | `metrics.py` 60 | `s_m`, `drive_force_N`, `interface_force_N`, `drive_power_W`, track-normal g; NaN outside ASSIST |
| `planar_track_metrics` | `metrics_planar.py` 922 | `track_start_altitude_m`, `exit_speed_mps`, `push_time_s`, `facility_length_m`, `braking_distance_m`, `carriage_mass_kg` |
| `PlanarView.row` | `phases/planar.py` 229 | how theta maps to `downrange_m` |
| `map_staging_planar`, `map_fairing_planar` | `phases/planar.py` 446, 470 | subtract mass only; r, theta and velocity unchanged |
| fairing event logging | `phases/planar.py` 1253, 1305-1311 (before the map at 1271), 1583 | the mixed mass convention of section 5.8 |
| staging event logging | `phases/planar.py` 1563-1583 | logged after the drop |
| metrics times | `metrics.json` | after release, except `t_release_s` (absolute) |
| resolved config | `resolved_config.yaml` | `runs.<name>.run`; bounds under `bound_runs`, cases under `cases`; a run with a different vehicle carries its own `vehicle` block; where SP1 puts offload runs is fixed at SP1's close-out |

**Tests to keep green and to copy from**

| File | Lines | Note |
|---|---|---|
| `tests/test_replay.py` | 575 | synthetic `results/<exp>/<ts>` under `tmp_path` (44-253), no simulation; strict JSON; ASCII page; L306 asserts `pitch_deg` is not embedded; template string checks 521-526; `node --check` 558-561 (skipped without node) |
| `tests/test_animate.py` | 447 | fixture 36-134; output-path refusals; `CALIBRATION_RECORDS` against the findings note (271) |

No test in either file is marked slow. There is no test file for `plots.py` itself.

**Packaging and tools: `pyproject.toml`**

- Dependencies: numpy, scipy, pandas, matplotlib, pydantic, pyyaml, ambiance. Pillow arrives
  through matplotlib and is not declared (TODO.md KI-018; section 5.8 item 4). Build backend `uv_build`, no package-data setting;
  the whole `src/launchsim` folder ships, `templates/` included (it has no `__init__.py`).
- ruff: line length 100, `docs/findings/probes` excluded. pytest: `filterwarnings = error`,
  so library code never calls `warnings.warn`.
- On this machine: ffmpeg 8.1, and node at `/c/nvm4w/nodejs/node`.
- `.gitignore` 9-19: `results/**` ignored except each run directory's top-level
  `summary.md`; the default outputs of `animate` and `replay` ignored.

**Data on disk for development (2026-09-30; CSV files are not in git)**

| Directory | Runs with `timeseries.csv` |
|---|---|
| `results/silo_screening_2d/20260930T175743Z` | 12: pad, pad__aero_bound, pad_instant, silo_cold, silo_cold__aero_bound, silo_cold_lag, silo_failed, silo_hot_full, silo_hot_full_impinged, silo_hot_ramp_on_track, silo_instant, silo_sled_22t (45 MB) |
| `results/calibration_f9_2d/20260930T173928Z` | 8 |
| `results/silo_bridge_2d_readme/20260930T185034Z` | 4 |
| SP1's `results/silo_offload_2d/<timestamp>` | to be listed at SP1's close-out |

Earlier work to look at: `docs/findings/probes/handoff-2026-09-30/template.html` and
`prep_data.py` (the prototype of the replay page; `prep_data.py` emits `pitch_deg`), and
`docs/media/ascent_pad_vs_silo_cold_2d.mp4` and `.gif`.

## 7. Steps

Proposed, to confirm in SP2's Plan mode (step A0). Each step runs the protocol's loop:
implementer, adversarial reviewers (a CLAUDE.md compliance auditor on every step; a
visual-QA reviewer on anything drawn; an honesty auditor on labels and caveats), up to two
fix rounds, an independent gate, commit, tracker update. Standing gate on every code step:
fast suite green, ruff clean, golden 1-D and the planar digest pin unchanged, no shipped
experiment or vehicle file changed.

Status marks: `[ ]` not started, `[~]` in progress, `[x]` done, `[!]` blocked or needs a
decision.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| A0 | Plan mode: check the entry criteria; re-check section 6; put the questions of section 10 to the user; detailed design; one static mock-up frame of the scene and of the app page, shown inline in the chat (a widget or an SVG) or written to the scratchpad, not to the repository (Plan mode cannot write repository files); confirm steps, tolerances and exit criteria | this file | - | User approval of the plan and the mock-up | [ ] | |
| A1 | Shared run-data module: readers, directory checks, run discovery, roles, series and event readers (pre- and post-drop mass), resampling, one output-path rule; `plots.py` and `replay.py` switched to it. First action, before any edit: generate the reference replay page at the SP2 start commit (the note below the table) | `run_data.py` (new), `plots.py`, `replay.py`, `cli.py`, `.gitignore`, `pyproject.toml` (if KI-018 is taken) | `tests/test_run_data.py` (new); `test_animate.py`, `test_replay.py` | Replay page of the reference directory byte-identical to the reference page (same sha256); animate tests pass; no `plots._` call left in `replay.py`; the four fairing drop cases of section 5.8 item 1 tested | [ ] | |
| A2 | Scene data payload and display geometry: display block with sources or `assumed`; payload with attitude, thrust, stage, track columns, tank levels, event-aligned grid, rebuilt separation states, display-only coast, caveats | `scene.py` (new), `configs/display/` (new), `config.py` (display model), `docs/physics.md` (display-only section) | `tests/test_scene.py` (new): strict JSON, nulls in the shaft, mass closure of the tank levels, staging state against `speed_inertial_mps`, energy and angular momentum of the coast, 1-D and sweep-point refusal, an offloaded run's starting fill | An independent agent compares the payload of the reference directory with its CSV at sampled times; every display number sourced or `assumed`; vehicle files untouched | [ ] | |
| A3 | 2-D scene renderer, one panel: silo, pad, rocket to scale, attitude, plume, tanks, hold-down, release, kick, staging, fairing, basic camera, HUD, caveats; a page-state hook for QA; the standalone export if chosen (Q1) | `templates/scene.html` (new), `scene.py`, `cli.py` | template string checks, ASCII page, `node --check`, export path refusals | Visual QA round 1 through a 127.0.0.1 server on pad, silo_cold, silo_hot_ramp_on_track and silo_failed | [ ] | |
| A4 | App server and job runner: `app` command, endpoints, loopback binding and Host check, one job at a time, the CLI's run path from a dict, baseline cache, exploratory label, results location and ignore rule | `app.py` (new), `cli.py`, `results_io.py` (only if the cached baseline needs an argument), `.gitignore` | `tests/test_app.py` (new): server on a free port with a stub runner; status codes; refusals write nothing; busy refusal; no path outside the results root; charset header; the baseline runs once for two launches; one slow end-to-end launch on a small grid | Fast and slow suites; a reviewer confirms nothing but 127.0.0.1 is bound and no client path is opened; app result equals the CLI's for the same configuration | [ ] | |
| A5 | Form and launch flow: fields, presets, refusal messages, progress, results panel with caveats, run browser, the scene inside the page | `templates/app.html` (new), `app.py` | form-to-experiment mapping, one test per field and per refusal; template checks | Each preset launched from the browser through 127.0.0.1: a results directory appears, its resolved config equals the form's values, its scene plays | [ ] | |
| A6 | Side by side and camera polish: two panels on one clock and one zoom, scale bars, the not-to-scale icon label, zoom out to Earth's curvature, event ticker, reduced motion, dark mode | `templates/scene.html`, `templates/app.html` | template checks; camera transform checks through the page-state hook | Visual QA round 2 | [ ] | |
| A7 | Visual QA, full: the checklist of sampled times and runs against the CSV; screenshots in both themes; audit of display-only labels, the exploratory label and the caveats | `docs/demos/SP2/` | the QA table itself | Independent visual-QA reviewer and honesty auditor; every row of the table passes or is logged as a deviation | [ ] | |
| A8 | Close SP2: exit-criteria gate; full suite; demo recorded; CLAUDE.md (commands, layout, I/O modules), README quick start, TODO.md; SP3's phase file fact-checked; handoff and prompt for SP3; memory | docs, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit | [ ] | |

The reference page of A1 and of exit criterion 10. "The reference directory" is
`results/silo_screening_2d/20260930T175743Z` with the runs `pad`, `silo_cold`,
`silo_hot_ramp_on_track` and `silo_failed` (four is the page's limit). SP1 edits
`replay.py`, so the page made "before the refactor" is generated at the SP2 start commit,
as the first action of A1 and before any file is edited:

    uv run python -m launchsim replay results/silo_screening_2d/20260930T175743Z --runs pad silo_cold silo_hot_ramp_on_track silo_failed --out <scratchpad>/reference_replay.html

Record its sha256 and the commit in the session log and keep the file in the scratchpad
for the session. On a fresh clone the CSVs are missing: re-run the experiment first (entry
criterion 6) and use the new directory, naming it in the session log.

Notes on the order. A1 comes first because the scene, the app and the two existing commands
all stand on it, and its gate (a byte-identical replay page) is cheap. The scene (A2, A3) is
built and checked on recorded directories before the server exists, so a drawing fault is
never mixed up with a server fault. The app (A4, A5) then only has to produce a directory
and hand it to a scene that already works.

## 8. Exit criteria

Each is checked by an independent gate at the end of the phase. Tolerances marked "proposed"
are confirmed or changed in A0 and then fixed. The phase closes with an open criterion only
if the user accepts the miss, and the miss is logged.

1. **The app starts.** `uv run python -m launchsim app` serves the app page on 127.0.0.1 and
   on no other interface, and prints the URL.
2. **Launch works for every setting.** From the form, a launch with each of the following
   produces a normal results directory (resolved config, git hash, `metrics.json`, time
   series and events per run, `summary.md`) whose resolved config holds the form's values:
   exit speed; net acceleration; each of the five ramp-start ways; a stage-1 offload; a
   stage-2 offload; a structural penalty. The scene of that directory then plays in the app.
3. **Same numbers as the CLI.** For one configuration, the app's payload capacity and offload
   result equal those of `launchsim run` on the equivalent YAML within 0.002 kg (proposed;
   the paths are meant to be the same code).
4. **Refusals.** Each bad input of section 5.7 gives a one-line message in the form and
   writes nothing under the results root. A second Launch during a running job is refused.
5. **The scene matches the run data.** For pad, silo_cold, one hot start, one offloaded run
   and silo_failed, at sampled times that include push start, mid-push, release, ignition,
   ramp end, the kick, MECO, staging, the fairing drop, cutoff or impact, and at least five
   times between them, the page state read from the running page equals the run's CSV within
   (proposed): altitude within the larger of 0.5% and 1 m; downrange within the larger of
   0.5% and 10 m; attitude within 0.5 deg; thrust on or off exactly outside a startup ramp,
   and the plume fraction within 0.02 of `thrust_vac_N` over the stage's full value; the
   stage shown; each event shown within one grid step of its time.
6. **The offload is visible and right.** An offloaded run's stage tank starts at one minus
   its offload fraction within 1% (proposed) and reads empty at its `propellant` event; the
   rebuilt stack mass equals `m_kg` at every sampled time within 1 kg (proposed).
7. **Honest labels.** The page names every display-only item (shapes, spent stage and
   fairing paths, carriage after release, the enlarged icon, the body axis), marks app runs
   as exploratory, and shows the model caveats (calibration +14.3%, no structural mass for
   the push, sweep-optimized and unthrottled guidance, the drive model) beside the numbers.
8. **Browse and replay.** The app lists the recorded planar run directories and plays
   `results/silo_screening_2d/20260930T175743Z` and one SP1 offload directory. A 1-D
   directory, a sweep point and a failed directory are refused with a clear message.
9. **The pad baseline is cached.** A second launch with an unchanged baseline does not run
   the pad again (a test with a counting stub, and the timing in the demo record).
10. **Loader and fixes.** `animate` and `replay` pass their tests on the shared module; the
    replay page of the reference directory (named in section 7, below the step table) is
    byte-identical to the reference page generated at the SP2 start commit (same sha256 as
    recorded in the session log); one output-path rule serves `animate`, `replay` and the
    scene export; no private cross-module helper call remains; the event reader gives pre-
    and post-drop mass for all four fairing cases of section 5.8 item 1.
11. **Tests and guards.** New tests for the payload, the server API and the form mapping run
    in the fast tier (one end-to-end launch may be slow-marked); the full suite is green;
    ruff is clean; golden 1-D and the planar digest pin are unchanged; no shipped experiment
    or vehicle file is changed.
12. **No new Python dependency**, or each one is justified in one line and logged as a
    decision. No request leaves the machine unless the user chose that in Q2.
13. **Documents.** CLAUDE.md (commands, layout, I/O modules, status line), README (quick
    start), the display-only section, TODO.md and the program board are current; SP3's phase
    file has been fact-checked against the code; the handoff and the prompt for SP3 are
    written; memory is updated.
14. **Demo recorded** under `docs/demos/SP2/`.

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
4. Set a stage-1 offload (the value SP1's findings note reports, or a fixed 10%) and launch
   again. Look at: the stage-1 tank starting part-full; the earlier MECO; the results panel
   with the propellant saved, the max-Q against the pad's, and the caveats beside them; the
   pad not being run again.
5. Add a structural penalty (+8.1 t) and launch. Look at: what is left of the offload.
6. Change the ramp start to a depth, then to a height by event. Look at: the ignition marker
   in the shaft and above the mouth; the requested and achieved values in the panel.
7. Enter a ramp-start depth larger than the stroke. Look at: the refusal message; no new
   directory.
8. Open `silo_screening_2d/20260930T175743Z` from the run browser and play `silo_failed`.
   Look at: the fall-back and the impact.

If the standalone export is chosen in Q1 (the command name is fixed in A0):

    uv run python -m launchsim scene results/silo_screening_2d/20260930T175743Z --runs pad silo_cold --out docs/demos/SP2/pad_vs_silo_cold_scene.html

Recorded in `docs/demos/SP2/`: a README with the commit and the commands; screenshots of the
steps above in light and dark mode; the visual-QA table (sampled time, value from the CSV,
value read from the page, pass or fail); a text record of the API calls for one launch and
one refusal; the exported scene page if the export exists. Check with `git status` that
the exported page is not ignored (section 5.8 item 4).

## 10. Risks and open questions

**Questions SP2's Plan mode puts to the user** (recommendation first, as the user prefers)

| # | Question | Recommendation | Why |
|---|---|---|---|
| Q1 | Should a scene be exportable as a standalone HTML file, and as a video? | HTML export yes (a `launchsim scene` command, like `replay`); video no for now, as a backlog item | The app is the plan (D-SP1-02), and TODO.md records that a separate scene command is no longer planned, so the export is an addition the user has to choose. It reuses the renderer, gives a file to keep and a way to test the scene without the server. A video of a canvas needs either capture in the browser or a second renderer; neither is needed to see the launch |
| Q2 | Must the app and the scene work with no internet connection (fonts, any library)? | Yes: no request leaves the machine; system fonts with the current fallbacks; no library for 2-D | A local tool should not depend on a network. The replay page loads three fonts from Google Fonts today (TODO.md KI-019); whether to change that page too is part of the question. The three.js question (CDN or vendored) is SP4's |
| Q3 | How are app runs named and kept? | One results root entry for the app (for example `results/app/<UTC timestamp>/`), labelled exploratory, wholly ignored by git including `summary.md`, never deleted by the app; the run browser shows their size | `.gitignore` keeps every run directory's top-level `summary.md` tracked, so app runs would otherwise show up as untracked files and break the clean-tree rule for finding runs. Deleting results needs the user's OK (CLAUDE.md). A launch writes two runs of about 3.6 MB of CSV each (estimate) |
| Q4 | What are the form's presets? | The pad alone; the silo variants of SP1's experiment (`silo_cold`, `silo_hot_ramp_on_track`, `silo_cold_200m`); silo_cold with the solved stage-1 offload; the penalty values 0, +2, +4, +8.1 t | They are the configurations the findings use, so the app and the notes show the same cases |
| Q5 | Which vehicle can the form use? | The gate vehicle only (`generic_f9_class_2d.yaml`) | The user asked to stay on the Falcon 9 model. The README-loads fork (inside the calibration band) could be a second choice later |
| Q6 | Offload input: a fixed amount, a solve for the largest, or both? | Both; fixed is the default | A fixed offload is one searched run; a solve takes about 33 s more per case (estimate) and stage 2 needs its pad control |
| Q7 | Look of the scene | A schematic cross-section in the replay page's style and palette, with dark mode; the mock-up of A0 is approved before the renderer is built | A realistic rendering would imply detail the model does not have |

**Open design points for A0 (no user decision needed unless they change scope)**

- What run a fixed-offload launch shows: the fly-out at the reference payload (the user's
  question: same payload, less propellant) with its residual or shortfall, or the offloaded
  vehicle's own payload-capacity run. Recommended: the reference-payload run. It depends on
  what SP1's step 7 records for a fixed case; check at SP1's close-out.
- Worker thread or child process (section 5.6). Recommended: thread, after measuring.
- How the cached baseline enters the run path: an optional argument on `run_experiment` or a
  composition in `app.py`. Recommended: whichever leaves `results_io.py` smallest; decide
  with SP1's entry point in hand.
- Exploratory marking: a new `label` value or a provenance field.
- Where the display block lives and how it is validated; where the display-only formulas are
  documented.
- Whether plots are written for app launches. Recommended: yes by default if the time is
  small against the search, otherwise a form switch; measure first.
- Placement of the carriage's braking section in the drawing (section 5.5).
- Shared template fragment or deliberate copy between the replay and scene pages.
- Port, and whether the command opens the browser itself.

**Risks**

| # | Risk | Recommended resolution |
|---|---|---|
| R1 | SP1's interfaces differ from the design this file assumes (entry point, offload run folders, metric names) | SP1's close-out re-checks this file; A0 re-checks section 6 before designing |
| R2 | An app number is taken for a finding | The exploratory label in the directory, `metrics.json`, `summary.md`, the results panel and the scene; findings only from committed files run from a clean tree; the dirty flag is recorded as usual |
| R3 | The scene looks more certain than the model is: shapes, the spent stage, the carriage and the body axis are not simulated | Every display-only item labelled on the page (exit criterion 7); the display block never read by the run path; a schematic style |
| R4 | The headline shown in the app may not survive the structural-mass model (README Phase 3, which comes after the 3-D phases by the chosen order) | The structural caveat and the penalty field sit beside every offload number; the max-Q of the offloaded run is shown against the pad's (38.4 against 37.2 kPa in the probe, a probe value, not a finding) |
| R5 | At orbital scale a 3.66 m wide rocket is smaller than a pixel | The enlarged icon with a "not to scale" note, and a scale bar in every panel |
| R6 | The side-by-side clock misleads: the pad's hold and the silo's push have different lengths before release | One stated clock (time after release) in the HUD; A0 may add a second alignment |
| R7 | A CPU-bound search in a worker thread makes the page sluggish | Poll for status; measure in A4; fall back to a child process |
| R8 | The run-data refactor changes `animate` or `replay` output | The byte-identical replay gate; existing tests; the one intended change (animate's output-path rule) is tested and logged |
| R9 | The replay and scene pages drift apart | A shared fragment, or a test that pins the shared helpers in both templates |
| R10 | App results pile up and untracked summaries break the clean-tree rule | Q3 |
| R11 | A local server is reachable by other software on the machine or by a web page | Loopback binding, Host check, POST for launches, no client-supplied paths (section 5.6); a reviewer checks it in A4 |
| R12 | Scene polish has no natural end | The exit criteria define done; further polish goes to the backlog in TODO.md |
| R13 | Recorded directories from before SP1 lack new metrics or have the mixed fairing convention | Fallbacks in the loader; the reader-side mass normalisation (section 5.8) |
| R14 | Mojibake and invalid JSON, both met before | `charset=utf-8` and `<meta charset>`, ASCII pages, NaN written as null, `allow_nan=False`; tests for each |
| R15 | The spent stage's vacuum coast is wrong in the atmosphere (no drag) | Labelled as display-only and drag-free; the path can be faded out below a stated altitude; not used for any number |

## 11. Session log

Empty: the phase has not started.

## 12. Deviations from the plan

None.

## 13. Prompt to start this phase

Draft; the SP1 session finalises it at its close-out (SP1 step 10).

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP2-launch-app-2d-scene.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links. We are continuing the
> launch-assist-sim project; this session is phase SP2:
> the local app with the 2-D launch scene. I want to open `launchsim app`, set the silo
> depth, the exit speed or acceleration, where the thrust ramp starts, the stage-1 and
> stage-2 propellant offload and an assumed structural penalty, press Launch, and watch the
> pad launch and the silo launch side by side; and I want to browse and replay recorded
> runs.
>
> Follow the session protocol. First confirm the entry criteria in the phase file's
> section 4 (SP1 closed, clean tree, fast tests green) and re-check its section 6 against
> the code as it is now. Then start in Plan mode (step A0): put the questions in section 10
> to me with your recommendation first, show me a mock-up frame of the scene and of the app
> page, and show me the detailed design, the step table and the exit criteria before
> writing any code.
>
> Keep the build, review and gate loop for every step, commit at each gate, and keep the
> phase file's step table, session log and TODO.md current. Anything drawn is checked
> against the run data through a server on 127.0.0.1, not by eye alone. App runs are
> exploratory: no finding comes from them. Do not change the equations of motion, events,
> search or loss accounting, and do not edit a shipped experiment or vehicle file. At the
> end, check the exit criteria with an independent gate, record the demo under
> docs/demos/SP2/, and prepare SP3: fact-check its phase file against the code, write the
> handoff and the prompt, and update the memory.
