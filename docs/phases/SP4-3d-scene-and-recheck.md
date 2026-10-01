# SP4: 3-D scene in the app, and the headline re-checked on S1

Status: not started

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-09-30 in
the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md)), the
3-D design ([inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md),
sections 5 and 6) and the visuals survey
([survey-animate-replay-visuals](inputs/2026-09-30-survey-animate-replay-visuals.md)).
Nothing in this file has been built or run. The plan gives SP4 two lines; the detail below
is a proposal for SP4's Plan mode, and it depends on what SP2 and SP3 actually build. The
session before SP4 re-checks sections 4, 5, 6 and 13.

## 1. Goal and what you can see at the end

Two deliverables:

1. **The launch on a globe.** A 3-D scene inside the SP2 app, drawn with three.js from
   the spatial time series that SP3 writes: the Earth, the launch site, the trajectory,
   the rocket with its attitude taken from the thrust direction, and three camera modes
   (chase, ground, orbit).
2. **The headline re-checked on the 3-D model.** SP1's offload experiment copied to
   `dynamics: spatial_3d` with the same budget, run from a committed file, and the offload
   percentage reported on the planar model and on S1 side by side.

At the end you can see: `launchsim app` showing a pad and a silo launch on a globe, with
the same clock, scrubber and telemetry as the 2-D scene; and a findings note with the
offload % on both models.

The re-check can come out different from the planar number. Both are then reported, with
the loss rows that explain the gap; neither replaces the other.

## 2. Scope and out of scope

In scope:

- A scene payload for spatial runs (Python, read-only on results directories): position,
  attitude, thrust, stage, events, site, orbit elements.
- The three.js scene in the app: globe with a graticule, launch site marker, silo mouth,
  ground track and trajectory, rocket model oriented along the thrust direction, plume
  scaled with `thrust_vac_N`, staging and fairing markers, the three camera modes.
- Reuse of the SP2 page parts: playback clock, scrubber, run toggles, telemetry, results
  table, caveats.
- A way to get a spatial run into the app (section 10, open question 2).
- Visual QA of the scene against the run data.
- The offload experiment on S1: experiment file, pre-registration, run, findings note,
  honesty review.
- docs/physics.md only if the offload post-pass needs a statement for the spatial model
  (for example which pad is the reference); no equation changes are planned in this phase.

Out of scope:

- Oblate Earth and its offload re-check: SP5. True attitude from a rigid body: SP6 (SP4
  draws the thrust direction; a point mass has no attitude).
- MP4 or GIF export of the 3-D scene; a 3-D view of planar runs placed on the globe by
  great-circle arc (possible, exact for the planar model, display only). Both go to the
  backlog unless Plan mode adds them.
- A separated spent stage and fairing in 3-D beyond what SP2's display-only ballistic
  path provides.
- Any change to dynamics, guidance, search or loss accounting. If the re-check exposes a
  defect in S1, it is fixed under the SP3 rules (Plan mode, closed-form test first,
  physics.md in the same change) and logged as a deviation.
- Changing the planar offload experiment or its findings. A planar or 1-D number may not
  change in this phase; the pins of SP1 and SP3 stay green.

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-01: 3-D means true 3-D dynamics, so the scene is fed by the spatial time series,
  not by a planar run mapped onto a globe.
- D-SP1-02: the visual tool is a local app; the scene lives inside it.
- D-SP1-03 and D-SP1-10: the offload semantics and the pad control. Stage 1 is the only
  headline; stage-2 and both-stage numbers are reported net of the pad control.
- D-SP1-04: structural penalty rows (+2, +4, +8.1 t) travel with the headline.
- D-SP1-09: the offload is an `offload:` block and a post-pass, so the spatial copy of the
  experiment changes no pre-registered file or budget id.
- D-SP1-07 and D-SP1-08: order and way of working.

## 4. Entry criteria

1. SP2 and SP3 are "done" on the program board (and SP1, which both need).
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3).
3. Fast suite green; ruff clean; the 1-D golden tier, SP1's planar digest pin and SP3's
   `tests/test_golden_planar.py` pass.
4. SP3's model-to-model record exists (`docs/findings/M2M-3d-vs-planar.md`) with no open
   `bug_suspect`. If SP3 closed with an accepted miss of its 5 kg expectation, the handoff
   says so and section 5.6 is re-read with that in mind.
5. `launchsim run` on a `spatial_3d` experiment writes the spatial time series of section
   5.1, and one such results directory is on disk for development (re-run it on a fresh
   clone; CSVs are not tracked).
6. SP1's offload solver takes its search problem from a factory (written against
   `RecordingProblem`), so `SpatialSearchContext` can be passed in. If SP1 did not deliver
   that, making it so is the first step here and is recorded as a deviation.
7. `launchsim app` starts, launches a planar run and shows the 2-D scene (SP2's demo).
8. Sections 5 and 6 of this file have been rewritten against the code SP2 and SP3 left.

## 5. Design

Summarised from the inputs; details to be settled in Plan mode against SP2's app.

Rules that apply to the whole phase:

- CLAUDE.md requires Plan mode for anything touching equations of motion, frames, events,
  integrator settings or loss accounting, with docs/physics.md updated in the same
  change. This phase plans none of those; the rule applies the moment one is needed.
- No planar or 1-D number may change. Pin tests come first: the existing pins must pass
  before and after every step.
- Every new physics feature needs its closed-form test before any experiment uses it.
  The S1 offload run uses only features SP1 and SP3 have already tested; the entry
  criteria check that.
- App runs are exploratory. Findings come only from committed experiment files run from a
  clean tree (SP2 design).

### 5.1 Scene data: the spatial time series

From the design's "Outputs" section. The exact column names are fixed by SP3
(`metrics_spatial.py`); the SP3 close-out writes them into this section.

- The spatial columns are a superset of the planar names, so SP2's 2-D scene reads a 3-D
  run unchanged: `t_s`, `t_rel_release_s`, `phase`, `stage`, `alt_m`, `downrange_m`,
  `speed_rel_mps`, `speed_inertial_mps`, `gamma_rel_rad`, `pitch_rad`, `psi_rad`, `m_kg`,
  `thrust_N`, `thrust_vac_N`, `drag_N`, `q_pa`, `mach`, felt loads, the loss integrals
  and the track columns.
- Added by S1: ECI and ECEF position and velocity; lat, lon, alt; crossrange; heading;
  yaw; thrust unit vector (ECI); `J_grav_lat`; osculating a, e, i, `raan_epoch`, argument
  of latitude.
- Events carry the same columns.
- Site: latitude and azimuth from the resolved config, and `site.longitude_deg`, which
  SP3 adds for display only.
- S3 later adds q0..q3, body rates, alpha, gimbal angles, attitude error, x_cg, I_t
  (SP6); the scene payload should take extra fields without a redesign.

### 5.2 Scene content

- Globe: a sphere of radius R_E with a latitude/longitude graticule, drawn Earth-fixed
  (ECEF positions), so the site stays put and the trajectory is the one seen from the
  ground. An inertial view (globe turning at omega_E) is optional.
- Launch site marker at (lat, lon); the silo as a shaft below the mouth for assisted
  runs, using SP2's display geometry block (shapes are display-only, sourced or
  `assumed`).
- Trajectory: the flown path up to the clock time as a bold trail over a faint full path,
  the ground track under it, event markers (release, MECO, staging, fairing, cutoff).
- Rocket: SP2's shape, placed at the ECEF position. Body axis along the thrust unit
  vector while an engine runs; along v_rel when unpowered; along the track while on it;
  vertical in the hold. This mirrors the planar `pitch_rad` convention and is labelled a
  display convention: a 3-DOF point mass has no attitude.
- Plume scaled with `thrust_vac_N`; tank fill levels as in SP2, so the offload is visible.
- Several runs at once (pad and silo), with SP2's run toggles.
- HUD and caveats: reuse SP2's telemetry cards and generated caveats, plus inclination and
  the model name (`spatial_3d`, spherical).

### 5.3 Camera modes

- Chase: follows the rocket at a distance that grows with altitude.
- Ground: from a point near the launch site, looking at the rocket.
- Orbit: a free camera around the globe, showing the whole ascent and the orbit plane.

### 5.4 three.js delivery (open question for Plan mode)

There is no JavaScript tooling in the project (no package.json, no bundler). Two routes:

- CDN: a module import from a public CDN. No file in the repository, but the scene does
  not work offline. The replay page already loads fonts from Google Fonts, so it is not
  fully offline today either.
- Vendored: one pinned `three.module.min.js` under `src/launchsim/templates/`, which
  uv_build's default packaging ships and the app's local server can serve. Works offline;
  adds a third-party file to the repository.

Either way three.js is a new dependency, and CLAUDE.md requires a one-line justification
in the change summary; a vendored file also needs its version and licence (MIT) recorded.
Recommendation and the user's decision: section 10, open question 1.

### 5.5 Visual QA against run data

A visual-QA reviewer (SESSION_PROTOCOL.md section 4) checks the picture against the
numbers. Proposed checks:

- At t = 0 the rocket sits at the site (at -stroke for a silo run); the marker's lat/lon
  equal the resolved config's.
- At release, max-Q, MECO, fairing drop and cutoff, the scene's rocket position (read
  through a small debug hook that returns the drawn state at a time) equals the ECEF
  columns of the time series within the resampling tolerance, and the HUD numbers equal
  the row.
- The ground track follows the lat/lon columns; the initial heading is due east for the
  28.5 deg, azimuth 90 deg case; the drawn orbit plane's inclination equals the reported
  one.
- The body axis equals the thrust unit vector at sampled lit times.
- Screenshots at those times in each camera mode go to docs/demos/SP4/.
- Python tests on the payload: strict JSON (no NaN), nulls where q and Mach are undefined
  in the shaft, required fields present, 1-D runs rejected; `node --check` of the inline
  script, as in `tests/test_replay.py`.

### 5.6 The offload re-check on S1

- Experiment: a copy of `experiments/silo_offload_2d.yaml` (SP1 step 8) with
  `dynamics: spatial_3d`, `earth: {model: spherical}`, the same vehicle, the same shared
  blocks verbatim and therefore the same budget id. It is committed before any run.
- Reference payload: per D-SP1-03 the fixed payload is the full-load pad's payload
  capacity on the same vehicle and orbit. Each model uses its own pad: the S1 offload is
  solved at the S1 pad's P*, not at the planar 26,054.4 kg.
- Solver: SP1's `solve_offload` unchanged, given a factory that builds
  `SpatialSearchContext`. Its checks apply as on planar: pad control about 0 for stage 1;
  the independent payload search reproduces the reference payload at the solved load, or
  the case is flagged.
- Reported, planar beside S1: stage-1 offload in tonnes, % of stage-1 and % of total
  propellant; the pad controls; the penalty rows; the cross-vehicle decomposition residual
  (SP1 step 6) on the spatial loss rows, including the lateral gravity part.
- Which cases to copy: recommended, the whole run block (headline, stage 2, both, penalty
  rows, pad controls) and the sweeps only if time allows; decided in Plan mode.
- Expectation, to be pre-registered by the session before the run: SP3 expects the 3-D
  payload capacity within 5 kg of planar. At the probe's marginal rate of 34-37 kg of
  payload per tonne of stage-1 propellant, a 5 to 10 kg shift corresponds to roughly 0.1
  to 0.3 t of offload, under 0.1 percentage point of the 410.9 t stage-1 load. This is an
  estimate made here from probe numbers; the session replaces it with one built from
  SP1's solved rate and SP3's measured differences, and commits it before running. A
  larger gap is a bug until the decomposition explains it.
- Run time: SP1 estimates about 15 min for the planar run and 17 min for its sweeps; the
  design puts the S1 RHS at about 15 against 12 microseconds per call, so about a quarter
  longer (estimate; SP3 measures the real ratio).
- Findings: a note beside SP1's `docs/findings/RQ1-fuel-offload-2d.md` (name proposed:
  `RQ1-fuel-offload-3d.md`, extended by SP5), with every caveat that travels with the
  planar number: calibration +14.3%, sweep-optimized and unthrottled guidance, no
  structural mass for the 4 g push, prescribed-acceleration drive, max-Q of the offloaded
  run against the pad's, tanks partly filled.

## 6. Inventory of the code this phase touches

Checked at commit 2eebcae on 2026-09-30, to be re-checked by the session before SP4. Most
of what SP4 builds on does not exist at that commit: SP1, SP2 and SP3 create it. This
section therefore has two parts, and the SP3 close-out (or the SP2 close-out, whichever
is later) rewrites the second.

### Exists at 2eebcae (line numbers from the visuals survey, spot-checked)

- `src/launchsim/replay.py` (1,161 lines): `REPLAY_DATA_TOKEN` (61), `REPLAY_COLUMNS`
  (99), `SERIES_FIELDS` (116), `check_replay_run_dir` (163; refuses any model other than
  `planar_2d` at 186), `select_runs` (195), `run_source` (241), `read_series` (306),
  `_finite` (324), `replay_grid` (335), `defined_mask` (346), `series_values` (356),
  `run_events` (386), `run_record` (897), `replay_data` (1022), `embed_json` (1083),
  `load_template` (1091), `render_page` (1097), `check_replay_out` (1139).
- `src/launchsim/templates/replay.html` (588 lines): JSON payload tag (197), one strict
  script (198-585), canvas 2D only, no modules, no libraries; fonts from Google Fonts
  (7-9).
- `src/launchsim/cli.py`: `build_parser` (56), commands dispatched from `main` (400;
  dict at 406-411).
- `pyproject.toml`: no JavaScript tooling; uv_build ships the whole `src/launchsim`
  folder; no package-data setting. `.gitignore` (16-19) ignores the default animate and
  replay outputs.
- `tests/test_replay.py`: the synthetic results-directory fixture (44-253) and the
  `node --check` of the inline script, the model for scene payload tests.
- The time series at 2eebcae is planar only (`metrics_planar.py`:
  `PLANAR_FLIGHT_COLUMNS` 287, `PLANAR_QUADRATURE_COLUMNS` 320,
  `PLANAR_TIMESERIES_COLUMNS` 329) and records no site longitude and no out-of-plane
  state.

### Created by earlier phases (names as planned; confirm at the fact-check)

| From | Item | SP4 uses it for |
|---|---|---|
| SP1 | `src/launchsim/offload.py` (`OffloadProblem`, `solve_offload`, problem factory); the `offload:` block and post-pass in `results_io.py`; `experiments/silo_offload_2d.yaml`; `docs/findings/RQ1-fuel-offload-2d.md` | The re-check |
| SP1 | Cross-vehicle decomposition in `compare.py` (step 6) | Explaining the offload on spatial loss rows |
| SP2 | `launchsim app` (local server, form, worker, results directory per launch); the shared run-directory loader; the 2-D scene page and payload; the display geometry block | Host for the 3-D scene; shapes; clock, HUD, caveats |
| SP3 | `metrics_spatial.py` (column names), `sim_spatial.py`, `search_spatial.py` (`SpatialSearchContext`), `frames.py`, `orbit3d.py`; `dynamics: spatial_3d`, `earth`, `site.longitude_deg` in `config.py`; the model set in `compare.py`, `results_io.py`, `summary.py`, `plots.py` | Scene data; the spatial offload run |
| SP3 | `tests/test_golden_planar.py`; `docs/findings/M2M-3d-vs-planar.md` | Pins; the expectation of section 5.6 |

The visuals survey recommends `scene.py`, a read-only `run_data.py` and
`templates/scene.html` for SP2; the real names are whatever SP2 chose.

## 7. Steps

Each step runs the loop of SESSION_PROTOCOL.md section 4. Reviewers: a CLAUDE.md
compliance auditor on every step; a visual-QA reviewer on steps 2 to 5; a physics or
numerics skeptic on steps 6 and 7; an honesty auditor on step 7. Standing gate on every
code step: fast suite green, ruff clean, 1-D golden byte-identical, the planar pins of
SP1 and SP3 passing. Step numbers and file names are proposals for Plan mode.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| 0 | Session start: entry criteria, sections 5 and 6 re-checked, Plan mode, open questions of section 10 put to the user | this file, TODO.md | fast suite | User approves the plan | [ ] | |
| 1 | Scene payload for spatial runs: ECEF position, lat/lon/alt, thrust direction, stage, events, site, orbit elements; resampled as the 2-D payload | SP2's loader and scene modules | Strict JSON; nulls in the shaft; required fields; a planar or 1-D run is refused or routed to the 2-D scene | Listed tests; the 2-D scene still loads a spatial run | [ ] | |
| 2 | three.js delivered as decided (question 1); page skeleton in the app; globe, graticule, site marker | SP2's app and templates | Template ships as package data; `node --check` | Scene opens in the app; site marker at the configured lat/lon | [ ] | |
| 3 | Trajectory, ground track, event markers, rocket with attitude from the thrust direction, plume, tank levels, several runs | scene template | Payload-to-scene unit checks where they can run without a browser | Visual QA of positions and attitude at sampled times (section 5.5) | [ ] | |
| 4 | Camera modes (chase, ground, orbit); clock, scrubber, HUD and caveats reused from SP2 | scene template | `node --check` | Visual QA in each mode, at the silo mouth and at orbit scale | [ ] | |
| 5 | Getting a spatial run into the app (question 2); full visual QA pass against run data | app, scene | App test as SP2 defines it | Visual-QA review passes; screenshots saved | [ ] | |
| 6 | Offload on S1: spatial context through SP1's problem factory; experiment file copied and committed; expectation written and committed | `experiments/` (new file), `search_spatial.py` or `offload.py` glue, tests | Small-grid end-to-end offload on a spatial experiment; pad control about 0 for stage 1; experiment listed in the config test | Resolves; committed; clean tree; planar outputs unchanged | [ ] | |
| 7 | Runs and findings: run from the clean commit; findings note with planar and S1 side by side; README results, findings index | results/ (summaries), `docs/findings/` | none new | No `bug_suspect`; decomposition residual within tolerance; honesty review | [ ] | |
| C | Close SP4: exit-criteria gate, demo recorded, status lines, SP5 phase file fact-checked, handoff and prompt, memory | docs/, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit | [ ] | |

## 8. Exit criteria

1. The app shows a spatial run on a globe: site marker, trajectory and ground track,
   rocket oriented along the thrust direction, event markers, and the chase, ground and
   orbit cameras, with the clock, scrubber and telemetry working.
2. Visual QA passed: at release, max-Q, MECO, fairing drop and cutoff the drawn position
   equals the time-series ECEF position within the stated resampling tolerance, the HUD
   equals the row, and the body axis equals the thrust unit vector; screenshots are in
   docs/demos/SP4/.
3. The scene payload tests pass (strict JSON, nulls, required fields, refusals), and
   SP2's 2-D scene still loads planar runs and loads a spatial run.
4. The three.js decision is logged in TODO.md with its one-line justification; if
   vendored, the file's version and licence are recorded.
5. The spatial offload experiment file and the session's expectation were committed
   before the run (git log), and the run came from a clean tree.
6. The offload on S1 is solved with the pad control about 0 for stage 1, the independent
   payload search reproducing the reference payload (or the case flagged), and no
   `bug_suspect`.
7. The findings note states the stage-1 offload % on the planar model and on S1 with the
   caveats beside the numbers, explains any difference from the loss rows, and passed the
   honesty review.
8. Full suite green; ruff clean; 1-D golden and both planar pins unchanged.
9. Demo recorded under docs/demos/SP4/; SP5's phase file fact-checked; handoff, prompt
   and memory written.

## 9. Demo script

Output goes to docs/demos/SP4/ (screenshots, text captures, a short README with the
commit). Commands are placeholders until SP2 and SP3 fix the names.

    uv run python -m launchsim app
    uv run python -m launchsim run experiments/<spatial offload file>.yaml

Look at:

- in the app: a pad and a silo launch on the globe; switch between the chase, ground and
  orbit cameras; scrub to release, MECO and cutoff and compare the HUD with the time
  series; switch to the 2-D scene for the same run;
- in `summary.md` of the spatial offload run: the "Propellant saved at fixed payload"
  block, the pad controls, the decomposition residual, the flags;
- in the findings note: the table of offload % on planar and on S1.

## 10. Risks and open questions

Open questions for Plan mode:

1. **three.js from a CDN or vendored. Needs the user.** Recommended: vendored, one pinned
   file under `templates/`. The app is a local tool on 127.0.0.1 and should work offline;
   a pinned file also keeps the scene reproducible. Cost: a third-party file of the order
   of 1 MB in the repository (estimate; check the pinned release) and a licence note. The
   CDN route costs nothing in the repository but fails offline. Either way the dependency
   gets its one-line justification (CLAUDE.md).
2. How a spatial run reaches the app. Recommended: a model selector in the form (planar
   or spatial), since the app already runs the CLI's resolve and run path; opening an
   existing results directory is the fallback. Depends on SP2's design.
3. Globe appearance. Recommended: a shaded sphere with a graticule and no bitmap texture,
   so no image asset or licence is needed. A coastline layer from a public-domain source
   is a backlog item with its source and licence stated.
4. Whether `launchsim replay` accepts spatial runs (it refuses any model but `planar_2d`
   at 2eebcae). Recommended: yes if SP3's reporting step has not already done it, since
   the columns are a superset; otherwise backlog.
5. Which offload cases and sweeps are copied to S1 (section 5.6).
6. Name and place of the 3-D findings note.

Risks:

1. SP4's design rests on code that does not exist yet. Mitigation: entry criterion 8; the
   plan is re-made in Plan mode against SP2's app.
2. Scale and precision in WebGL: a 70 m rocket next to a 6,378 km globe, and positions of
   6.4e6 m in 32-bit floats, give jitter and depth fighting. Mitigation: render relative
   to a moving origin (the rocket or the site), a logarithmic depth buffer or split
   scenes, a rocket drawn larger than scale in the orbit camera and labelled so; test at
   the silo mouth and at orbit altitude.
3. WebGL in the review tooling: the browser pane used for visual QA may not render WebGL
   or may show local files as static snapshots. Mitigation: serve from the app on
   127.0.0.1; fall back to Chrome; keep the debug hook so positions can be checked
   without reading pixels.
4. The drawn attitude can be read as a result. It is the thrust direction of a point
   mass. Mitigation: a caveat on the page; SP6 replaces it with the 6-DOF attitude.
5. The offload on S1 differs from planar by more than expected. Mitigation: treat as a
   bug until the decomposition explains it; report both numbers; do not adjust either
   model toward the other.
6. Stage-2 and both-stage offloads are ill-conditioned on the planar model (D-SP1-10) and
   may differ between models for that reason alone. Mitigation: stage 1 stays the only
   headline; the others are reported net of the pad control with that label.
7. Payload size: more columns per run than the 2-D payload (about 270 kB of JSON for four
   runs at 2eebcae). Mitigation: send only what the scene draws; keep the resampling
   grid.

## 11. Session log

(empty: phase not started)

## 12. Deviations from the plan

(none)

## 13. Prompt to start this phase

Draft, the previous session finalises it.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP4-3d-scene-and-recheck.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links. Follow the session
> protocol. This session does phase SP4: (1) a 3-D scene
> in the local app, drawn with three.js from the spatial time series: globe, launch site,
> trajectory, the rocket oriented along the thrust direction, and chase, ground and orbit
> cameras, checked against the run data; (2) the headline fuel offload re-checked on the
> 3-D model S1: the offload experiment copied to dynamics: spatial_3d with the same
> budget, committed before it is run, and the offload % reported on planar and 3-D side
> by side. Check the entry criteria (SP2 and SP3 closed, pins green) and re-check
> sections 5 and 6 against the code, then start in Plan mode. Ask me first whether
> three.js comes from a CDN or is vendored (your recommendation first), then show me the
> plan before writing code. No planar or 1-D number may change; any change to equations,
> frames, events or loss accounting needs Plan mode and docs/physics.md in the same
> change. Keep the build-review-gate loop with a visual-QA reviewer for the scene and an
> honesty auditor for the findings, commit at each gate, keep the trackers current, and
> close the phase with the demo, the SP5 phase file fact-checked, the handoff and the
> prompt for SP5.
