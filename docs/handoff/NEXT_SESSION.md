# Next session: visual launch simulator and fuel-replacement experiments

Read this file first, then CLAUDE.md, TODO.md and README.md. It hands over everything a
new Claude Code session needs to continue without the previous conversation. Written
2026-09-30 at the end of the session that built Phases 0-2 (commits 5963515 to the
handoff commit). The memory directory also points here.

## 1. The request (the user's words, lightly cleaned)

> Add the replay page as a command. Now enhance the simulator so that it can show the
> rocket actually getting launched in different configurations, in 2-D and then in a 3-D
> world. It will be intriguing to see it happen instead of seeing graphs only. I want to
> configure the depth from which the rocket is launched inside the silo. I want to
> configure when the rocket's thrust ramp-up starts: between the cold start and
> thereafter, where do the thrusters start ramping up? Also, if the rocket is lifted by a
> maglev ring setup inside the silo and given an initial speed just above the launch pad,
> we can try taking away some of the rocket's fuel, because less fuel should be needed to
> take the same payload to the same altitude and the same orbit. That should be
> configurable too: the system should let me reduce the amount of rocket fuel. Let's stick
> with the Falcon 9 rocket model. If this is too much for the current session, start a new
> one: save the memory, update the documents and trackers, and store this prompt so the
> new session can pick up with no progress or relevant context lost.

And the follow-up, which sets the headline research question:

> My idea is to find out whether, if we don't change the payload size and just add this
> extra lift using renewable electricity through a maglev ring setup inside the silo, we
> can reduce the amount of rocket fuel at every launch. I want to see what percentage of
> rocket fuel can be replaced with renewable energy, in case that is something companies
> are interested in, instead of increasing the payload.

## 2. Requirements and status

| # | Requirement | Status at handoff |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done: `launchsim replay` (section 4.5) |
| R2 | An animated scene of the launch itself (rocket, silo, exhaust, staging, flight), not only graphs, for different configurations; 2-D first | Not started; data available (section 4.6) |
| R3 | The same in a 3-D world | Not started; see decision 1 |
| R4 | Configure the launch depth in the silo | Exists indirectly (`assist.stroke_m`); a depth/exit-speed parameterisation is missing |
| R5 | Configure where the thrust ramp-up starts, from during the push to after release | Exists by time (`ignition.stage1.t_ign_s` with `reference`); by depth, height or speed is missing |
| R6 | Reduce the rocket's propellant at fixed payload and report the fraction replaced by the silo's electrical push (the headline question) | Possible by hand (sensitivity cases, probe in section 3); a proper figure of merit and experiment are missing |
| R7 | Stay on the Falcon 9-class model | Standing: use configs/vehicles/generic_f9_class_2d.yaml (planar gate fork); never edit it, copy or override |
| R8 | Lose nothing between sessions | This file, TODO.md, the memory directory, CLAUDE.md status line |

## 3. The headline question and a first answer (probe, not a finding)

**Question:** keep the payload and the orbit fixed. How much rocket propellant can be
removed when the silo pushes the rocket out at 76.7 m/s, and what fraction of the
propellant does the silo's electricity replace?

**Probe** (docs/findings/probes/handoff-2026-09-30/probe_offload.py and .out; gate vehicle
generic_f9_class_2d.yaml, the shipped shared blocks of experiments/silo_screening_2d.yaml,
payload search, 3 g / 100 m cold start lit 0.5 s after release with the 2 s ramp; about
20 s per run; nothing written to results/):

| Run | Stage-1 propellant | Payload capacity P* | Liftoff mass | MECO | Max-Q |
|---|---|---|---|---|---|
| Pad, full load | 410.9 t | 26,054.4 kg | 572.4 t | 151.3 s | 37.2 kPa |
| Silo cold start, full load | 410.9 t | 27,553.2 kg | 573.9 t | 153.8 s | 31.2 kPa |
| Silo, 2% less stage-1 propellant | 402.7 t | 27,274.2 kg | 565.4 t | 150.8 s | 32.5 kPa |
| Silo, 5% less | 390.4 t | 26,837.6 kg | 552.6 t | 146.2 s | 34.6 kPa |
| Silo, 10% less | 369.8 t | 26,061.2 kg | 531.3 t | 138.6 s | 38.4 kPa |
| Pad, 10% less (for reference) | 369.8 t | 24,658.8 kg | 529.9 t | 136.1 s | 44.5 kPa |

- With **10% less stage-1 propellant (41.1 t)** the silo-launched rocket still carries the
  full-load pad's payload to the same 200 km circular orbit (26,061 vs 26,054 kg). That
  is **7.9% of the total propellant load** (410.9 + 107.5 t). The marginal rate is about
  34-37 kg of payload per tonne of stage-1 propellant, so the exact break-even is slightly
  above 10%.
- Energy, derived and rough: the removed propellant holds about 12.4 t of RP-1 (the FT
  table's 123.5 t RP-1 in 410.9 t), roughly 530 GJ of combustion heat at about 43 MJ/kg.
  The push of the lighter stack takes about 2.1 GJ of mechanical work, about 4.2 GJ
  (1.2 MWh) of electricity at the assumed 50% drive efficiency: roughly a 100:1 ratio.
  This is not an efficiency claim. The saving comes from the head start avoiding the
  slowest, most gravity-costly part of the ascent, not from the push's energy itself.
- Caveats that travel with these numbers: the gate vehicle calibrates +14.3% high;
  guidance is sweep-optimized and unthrottled; **no structural mass is charged for the
  4 g full-stack push** (about 8.1 t of stage-1 strengthening would cancel the payload
  gain, and would cut the offload too); tank dry mass is not reduced with the offload
  (that favours the offload); max-Q of the offloaded silo run (38.4 kPa) exceeds the
  full pad's (37.2 kPa); the drive is a prescribed 3 g push with no force or power limit,
  a massless carriage and no shaft drag.

## 4. What already exists (fact-checked at handoff)

### 4.1 Silo depth (R4)

- There is no `depth` key. The silo is `assist: {model: constant_accel, net_accel_g,
  stroke_m, carriage_mass_t, brake_decel_g, drive_efficiency,
  exhaust_impingement_fraction, shaft: vented, track: {angle_deg: 90, exit_altitude_m}}`
  (config.py ConstantAccelConfig). Depth of the launch point below the silo mouth =
  `stroke_m`; the mouth sits at `exit_altitude_m` (0 = ground). Only vertical tracks are
  allowed (`angle_deg` 90; tilted is Phase 3).
- Depth changes: exit speed v = sqrt(2 a L), push time sqrt(2 L / a), braking distance
  v^2 / (2 a_brake), facility length, drive energy and peak power. Felt g on the track is
  a + g_eff, independent of depth. In the shipped sweep, payload capacity depends only on
  the exit speed (100 m at 0.5 g and 50 m at 1 g both give 31.3 m/s and 26,510.5 kg; 300 m
  at 1 g and 100 m at 3 g both give 76.7 m/s and 27,553.2 kg), while energy, peak power
  and facility length differ.
- Depth and exit speed can be set independently today only by computing
  `net_accel_g = v^2 / (2 g0 L)` by hand (200 m at 1.5 g gives 76.7 m/s).

### 4.2 Where the thrust ramp starts (R5)

- `ignition: {stage1: {t_ign_s, reference: release | push_start, startup: {kind: step |
  ramp | lag, t_ramp_s, tau_s}, fails}}`. Negative `t_ign_s` with `reference: release`
  means lit on the track; `push_start` measures from the start of the push (assist runs
  only). A stage lit before the push is clamped at the shaft bottom until the push starts.
  The vehicle default is a 2.0 s linear ramp.
- Under the prescribed-acceleration drive, lighting on the track does not change the exit
  speed; it changes the propellant burned on the track, the drive force, energy and power.
- Ramp start position for the shipped 3 g / 100 m silo (closed forms; t_push 2.607 s):

| t_ign_s | reference | Ramp starts at (z, speed) | Where |
|---|---|---|---|
| -2.0 | push_start | -100 m, 0 m/s | clamped at the bottom, full thrust exactly at push start (silo_hot_full) |
| 0.0 | push_start | -100 m, 0 m/s | ramp starts with the push |
| +1.0 | push_start | -85.3 m, 29.4 m/s | in the shaft |
| -2.0 | release | -94.6 m, 17.9 m/s | in the shaft; ramp ends at release (silo_hot_ramp_on_track) |
| -1.0 | release | -62.0 m, 47.3 m/s | in the shaft |
| 0.0 | release | 0 m, 76.7 m/s | at the mouth |
| +0.5 | release | +37.1 m, 71.8 m/s | coasting (silo_cold) |
| +2.0 | release | +133.9 m, 57.2 m/s | coasting |

  Inverse: to start the ramp at depth d below the mouth,
  `t_ign_s (push_start) = sqrt(2 (L - d) / a)`, or that minus t_push for `reference:
  release` (d = 50 m gives 1.844 s from push start, -0.764 s from release, at 54.2 m/s).
  Probe: docs/findings/probes/handoff-2026-09-30/probe_ign_table.py.

### 4.3 Reducing propellant (R6)

- Variants cannot change the vehicle (`vehicle:` in a variant is refused). On planar
  experiments, vehicle-path sweeps must be `paired: true` and bounds pair the pad the same
  way, so both compare an offloaded silo with an equally offloaded pad. Only the
  `sensitivity` block compares a vehicle change against the unchanged pad (symmetric +/-
  fraction, one per parameter). Example that resolves today:
  `sensitivity: {of: [silo_cold], params: {vehicle.stages.stage1.propellant_mass_t: 0.10}}`.
  Probe: docs/findings/probes/handoff-2026-09-30/probe_resolve.py.
- Physically: dry mass unchanged (tanks partly filled), liftoff mass falls one to one,
  stage 1 burns to depletion earlier (41.1 t less is 15.2 s earlier MECO), guidance is
  re-solved per run.
- Missing: a per-variant vehicle override compared against the unchanged pad; a figure of
  merit "minimum propellant at fixed payload and orbit" (bisection on the stage-1, or
  stage-2, load until P* equals the reference payload); summary rows named "propellant
  saved" with % of stage-1 and of total and the energy ratio; tank-mass scaling.

### 4.4 Vehicle files (R7)

- configs/vehicles/generic_f9_class_2d.yaml: the planar calibration gate (mass set C).
  Stage 1 22.2 t dry, 410.9 t propellant, 9 x 914.1 kN vac / 845.2 kN SL, Isp 311 s, 2 s
  ramp; stage 2 4.0 / 107.5 t, 981 kN, 348 s, 11 s staging coast; fairing 1.7 t on the
  heating rule; A_ref 10.52 m^2; Braeunig C_D(M). P* 26,054.4 kg (+14.3% vs 22.8 t).
  Used by calibration_f9_2d, silo_screening_2d, guidance_trigger_2d. Never edit it.
- generic_f9_class_2d_readme_loads.yaml (set A, README masses), ..._recorded_scope.yaml
  (set B), and the 1-D reference generic_f9_class.yaml.

### 4.5 Visual outputs today

- PNG plots per run (results/<exp>/<ts>/plots/).
- `uv run python -m launchsim animate <run_dir> [--runs ...] [--out x.mp4|x.gif] [--fps]
  [--seconds] [--width]`: chart-style replay (altitude vs downrange, launch close-up with
  the shaft, speed, felt g, q, readouts, caveat footnote). Captures in docs/media/.
- `uv run python -m launchsim replay <run_dir> [--runs ...] [--out page.html]`: a
  self-contained interactive HTML page (play/pause, scrub, run toggles, trajectory,
  launch close-up, telemetry, strip charts, results table, caveats). The prototype it was
  ported from is kept in docs/findings/probes/handoff-2026-09-30/ (template.html,
  prep_data.py); a published copy is the private claude.ai artifact "Ascent Replay"
  (https://claude.ai/artifact/BkkFxnZEuqqXvrvtXtYeas).
- There is no scene: nothing draws the rocket, silo, carriage, plume or Earth.

### 4.6 Data a 2-D/3-D launch scene can use

- timeseries.csv (every 0.05 s): t_s, t_rel_release_s, phase (HOLD, ASSIST,
  COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN, COAST),
  stage, alt_m (negative inside the silo), downrange_m, speed_rel_mps,
  speed_inertial_mps, gamma_rel_rad, pitch_rad (thrust/body axis above local horizontal),
  psi_rad, m_kg, thrust_N, thrust_vac_N (plume size), drag_N, q_pa, mach, felt g, losses,
  and on the track s_m, drive_force_N, interface_force_N, drive_power_W.
- events.csv: push_start, ignition, ramp_end, release, kick_start, kick_end, liftoff,
  propellant (MECO), staging, fairing, cutoff, apex, impact, end, with states.
- metrics.json and resolved_config.yaml: site latitude 28.5 deg and azimuth 90 deg,
  stroke, acceleration, exit altitude, carriage mass, vehicle masses, A_ref.
- 2-D scene: x = downrange, z = altitude; for Earth curvature place each point at angle
  downrange/R_E on a circle of radius R_E + alt. Attitude = pitch.
- 3-D view of a planar run: move along the great circle from the site at azimuth 90 deg
  through downrange/R_E (exact for the planar model); the site longitude is not recorded
  (use about -80.6 deg for Cape Canaveral, labelled as a display choice).
- Not recorded: vehicle and silo geometry (length, diameters, rings, carriage), the spent
  stage and fairing after separation, carriage motion after release, out-of-plane state.

## 5. Decisions to put to the user first (Plan mode)

CLAUDE.md requires Plan mode for anything touching events, search or loss accounting, and
says to ask before expanding scope to 3-D Earth. Ask these (with the recommendation first)
before designing:

1. **3-D: picture or physics?** Recommended: a 3-D *view* of the existing planar physics
   on a globe (exact for this launch geometry). True 3-D dynamics is a scope expansion.
2. **What kind of visual tool?** Recommended: CLI-generated self-contained scenes first (a
   2-D canvas scene, then a three.js 3-D scene from a CDN, plus MP4/GIF through the
   existing ffmpeg path), built from recorded runs; later, if wanted, an interactive local
   app with a form (depth, ramp start, fuel offload) and a Launch button (needs a small
   local server, a new dependency, and 10-30 s per searched run).
3. **Fuel offload semantics** (the headline). Recommended: stage-1 offload first, tanks
   partly filled (dry mass unchanged), fixed payload = the full-load pad's payload
   capacity on the same vehicle and the same 200 km orbit; report the largest offload in
   tonnes, % of stage-1 and % of total propellant, the RP-1 removed, and the energy ratio
   (combustion heat removed vs electricity used); stage-2 and both-stage offload as
   options. Also ask whether to show a "with structural penalty" row (for example the
   8.1 t break-even) beside it.
4. **Depth parameterisation.** Recommended: allow either `stroke_m` with `net_accel_g`
   (today) or `stroke_m` with `exit_speed_mps` (acceleration derived), never both.
5. **Ramp-start parameterisation.** Recommended: keep time-based `t_ign_s`, add
   `at_depth_m` (below the mouth) and `at_speed_mps` for the push, converted by closed
   form for constant_accel and recorded as metrics.

## 6. Proposed plan (to refine in Plan mode)

| Step | Deliverable | Gate |
|---|---|---|
| V0 | Plan mode: answers to section 5; design; physics.md sections listed | User approval |
| V1 | Configuration: exit-speed option for depth; ignition by depth/speed; variant-level vehicle overrides compared against the unchanged pad (with the comparison basis stated); a `propellant_offload` figure of merit (bisection on the stage-1 load to P* = reference payload) with closed-form tests; summary rows "propellant saved" and the energy ratio; experiments/silo_offload_2d.yaml (offload at the pad's payload, a depth sweep and a ramp-start sweep) | Full suite; golden 1-D unchanged |
| V2 | 2-D animated launch scene (`launchsim scene`): silo cross-section with rings and carriage, the rocket, exhaust scaled with thrust, the pad's hold-down, release, kick, staging with stage 1 falling away, fairing halves, a camera that follows and zooms out to Earth's curvature, a HUD; several configurations side by side; HTML and MP4/GIF | Visual QA of extracted frames against the run data |
| V3 | 3-D scene: globe with the launch site, the trajectory plane, rocket and silo models, camera modes (chase, ground, orbit), same data | Visual QA |
| V4 | Experiments and findings: the fuel-replacement answer (offload at fixed payload, the energy ratio, with and without a structural penalty), depth and ramp-start sweeps; a findings note with caveats | Honesty review |

Phase 3 of the README roadmap (force-limited linear motor, curved ramp, cable winch,
structural mass for the 4 g load) is still open; the structural-mass cost decides whether
the gain survives, so keep it beside every fuel-offload number.

## 7. State of the project at handoff

- Commits on main, newest first: the handoff commit (the replay command, this file, the probes, the trackers), e0d6bc7
  (README refresh, animate, Experiments rule), a8c8f88 (Phase 2 closed, findings),
  63b45c8 (2-D experiment runs), 7ad381f (pre-registration amendment: 2 s planar step cap,
  M2 diagnostic), d20a05f (calibration record), c2849b7 (Phase 2 build and freeze),
  d8d6951, 104ea07, 5d6c6c5, 98c752d, 5963515.
- Tests: 928 fast plus 23 slow; ruff clean; the golden 1-D test pins every 1-D output.
- Key results directories (top-level summaries tracked, CSVs on disk only):
  results/calibration_f9_2d/20260930T173928Z (amended re-run),
  results/silo_screening_2d/20260930T175743Z (run) and 20260930T182453Z (sweeps),
  results/guidance_trigger_2d/20260930T174950Z, results/silo_bridge_2d_readme/20260930T185034Z.
- Findings: docs/findings/README.md indexes CAL-f9-leo-2d, RQ2/RQ3 (1-D and 2-D) and RQ6.
- The Phase 2 plan (historical) is at C:\Users\rahul\.claude\plans\read-readme-md-and-claude-md-mutable-honey.md.
- User decisions so far are in TODO.md's decisions log (calibration miss accepted; M2
  diagnostic only; 2 s planar step cap; the Experiments rule rewording).

## 8. How work was done (keep doing it)

- Plan first. The user asked to see plans before code; physics, event, search and
  loss-accounting changes go through Plan mode, with docs/physics.md updated in the same
  change.
- Build in steps, each with an implementer, then adversarial reviewers (a physics or
  numerics skeptic and a CLAUDE.md compliance auditor; an honesty auditor for findings; a
  visual-QA reviewer for anything drawn), up to two fix rounds, then an independent gate.
  Multi-agent workflows ran these; a workflow that loses agents (an expired login) can be
  resumed from its run id and replays cached steps.
- Commit at each gate (the user expects it) and update TODO.md: milestones, step rows,
  decisions log, findings, known issues.
- Runs that produce findings start from a clean committed tree; calibration runs record
  the pre-registration state. Never tune toward a target; state results against the
  hypothesis plainly; keep caveats next to every headline number.
- The user answers decision questions quickly and has chosen the recommended option every
  time; put the recommendation first and explain the trade-off in one line.

## 9. Gotchas learned

- The Bash tool can reject a long command containing a quoted heredoc ("unexpected EOF
  while looking for matching `'`") before anything runs. Write longer scripts to the
  scratchpad with the Write tool and run them with `python <file>`.
- `cd` inside a Bash command persists and moves the session's working directory; use
  absolute paths, and never write into results/.
- Windows PowerShell 5.1 has no `&&`; the console is cp1252, so every file open passes
  `encoding="utf-8"` and console output stays ASCII.
- Python's json writes NaN; JavaScript rejects it. q and Mach are NaN during the
  vented-shaft push; emit null.
- A standalone HTML file needs `<meta charset="utf-8">`; a local server sends no charset
  and the minus and degree signs turn into mojibake. The Write tool turns `\uXXXX` escapes
  into real characters.
- The browser pane renders files outside the project folder as static snapshots (no
  JavaScript); to test a page, serve its folder with `python -m http.server` on
  127.0.0.1 and open that URL.
- pytest runs with filterwarnings=error: never call warnings.warn in library code.
- Machine speed varies about 3x under load (full suite 4-20 min). A searched planar run
  takes 7-25 s; silo_screening_2d took about 27 min for the run and 26 min for the
  sweeps. Background Bash commands are not killed at the 10-minute tool timeout; a
  Monitor expires after 30 minutes and must be re-armed.
- Results: only each run's top-level summary.md is tracked; a fresh clone must re-run
  experiments before animate or replay can read their CSVs.

## 10. Prompt to start the next session

Paste this into a new Claude Code session opened in this folder:

> Read docs/handoff/NEXT_SESSION.md first, then CLAUDE.md, TODO.md and README.md, and the
> memory index. We are continuing the launch-assist-sim project from that handoff. The
> goal of this session: (1) answer the headline question in section 3 properly: at a fixed
> payload and the same 200 km orbit on the Falcon 9-class gate vehicle, how much rocket
> propellant can a maglev silo push replace, as a percentage of stage-1 and total
> propellant, with the energy comparison and the structural-mass caveat; (2) make silo
> depth and the thrust-ramp start point configurable in the ways section 5 proposes;
> (3) build an animated 2-D launch scene that shows the rocket actually launching from
> the pad and from the silo, then a 3-D view. Start in Plan mode: put the five decisions
> in section 5 to me with your recommendation first, then show me the plan before writing
> any code. Keep the build-review-gate workflow, commit at each gate and keep TODO.md
> current.
