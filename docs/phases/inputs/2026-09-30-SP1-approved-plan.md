# Plan: fuel replacement at fixed payload (this session), and the program of one-session phases after it

## Context

Phases 0-2 of launch-assist-sim are done (1-D model, vertical constant-acceleration silo
push, planar 2-D ascent to orbit with payload search, calibration accepted at +14.3%).
The handoff (docs/handoff/NEXT_SESSION.md) set three goals: answer the headline question
(how much rocket propellant a maglev silo push replaces at a fixed payload and orbit on
the Falcon 9-class gate vehicle), make silo depth and the thrust-ramp start configurable,
and show the launch in 2-D and then 3-D. A probe found about 10% of stage-1 propellant
(41.1 t, 7.9% of total); it is not yet a finding.

During planning you chose true 3-D dynamics up to 6-DOF and a local app as the visual
tool, and asked for the work to be split into self-contained, demonstrable phases, one
fresh Claude session each, with each session preparing the next one's documents, memory
and prompt, and for work tracking to mature to support that. This plan therefore covers
(a) the program split, (b) the tracking system, (c) the full step plan for this session
(SP1), and (d) the designs already made for later phases, which SP1 writes into their
phase files so nothing is lost.

## Decisions taken with you (2026-09-30)

| # | Decision | Answer |
|---|---|---|
| 1 | 3-D: picture or physics | True 3-D dynamics in three validated stages: S1 3-DOF point mass on a rotating sphere; S2 oblate Earth (J2, ellipsoid); S3 6-DOF rigid body |
| 2 | Visual tool | A local app is the main tool (form, Launch button, scenes inside it) |
| 3a | Offload | Stage 1 (headline), stage 2, and both stages |
| 3b | Structural penalty | Parametric rows: offload re-solved with assumed extra stage-1 dry mass |
| 4 | Depth | `stroke_m` with exactly one of `net_accel_g` or `exit_speed_mps` |
| 5 | Ramp start | All of: time; depth or speed on the push; height above the mouth by event; height by closed form |
| 6 | Order | Settings and offload solver, headline findings on the planar model, the app with the 2-D scene, then 3-D |
| 7 | Way of working | One fresh session per phase; each phase tested, refined and completed before the next; handoff documents, memory and a prompt prepared by the previous session |

Decisions 1 and 2 go beyond the handoff's recommendation. CLAUDE.md's "ask before
expanding scope (6-DOF, 3-D Earth)" is satisfied by these answers; they go into the
decisions log.

## Program: one session per phase

| Phase | Goal | What you can see at the end |
|---|---|---|
| SP1 (this session) | Tracking system; launch settings (depth, ramp start); fuel-offload solver; the headline finding on the planar model | Findings note with the % of propellant replaced; `launchsim run experiments/silo_offload_2d.yaml` reproducing it; a replay page of the full pad against the offloaded silo |
| SP2 | Local app with the 2-D launch scene | `launchsim app`: set depth, ramp start and offload, press Launch, watch pad and silo side by side |
| SP3 | 3-D dynamics S1 (3-DOF, rotating sphere) | Tests green; model-to-model record against the planar gate; a 3-D run from the CLI |
| SP4 | 3-D scene in the app; headline re-checked on S1 | The launch on a globe; offload % on planar and 3-D |
| SP5 | 3-D dynamics S2 (oblate Earth) | Offload % on the oblate model; effect of flattening and J2 separated |
| SP6 | 3-D dynamics S3 (6-DOF fly-out) | Attitude, gimbal and cold-start controllability results; attitude shown in the 3-D scene |
| later | README Phase 3 (force-limited motor, ramp, cable, structural mass for the 4 g push), Phase 5 (optimal control), Phase 6 (hobby scale) | per the README roadmap |

The structural-mass model (README Phase 3) decides whether the headline survives. It
sits after the 3-D work only because of the order chosen; it can be moved up at any
session boundary.

## Work tracking (built first, step T)

| File | Role |
|---|---|
| `docs/process/SESSION_PROTOCOL.md` (new) | How every session runs: start checklist, step loop, end checklist, ID conventions. CLAUDE.md "Working rules" points to it |
| `docs/phases/README.md` (new) | Program board: each phase's goal, status, entry and exit criteria, demo, session dates, commits, link to its phase file |
| `docs/phases/SP<n>-<slug>.md` (new, one per phase) | Starting document and live record: brief (goal, scope, out of scope, decisions, design, fact-checked inventory with file:line), step table with gates, exit criteria, demo script, risks, session log, deviations |
| `docs/handoff/NEXT_SESSION.md` | Entry point for the next session: what was finished, state of the tree, which phase file to open, gotchas, the prompt to paste. The previous one moves to `docs/handoff/archive/<date>-<phase>.md` |
| `TODO.md` | Program-level tracker: milestones, current phase, priorities, backlog, decisions log, known issues, findings index. Step tables of new phases live in the phase files; the Phase 0-2 tables stay as history |
| `docs/demos/SP<n>/` (new) | Recorded demo output or screenshots of each finished phase |
| `CLAUDE.md`, `README.md`, memory directory | Status lines, layout, commands; the protocol rule; project status and way-of-working memories updated at every session end |

Conventions: decisions `D-nnn` (date, phase), known issues `KI-nnn` (severity, status,
owner phase), backlog `B-nnn` (priority, target phase); existing TODO.md entries get IDs
in place, nothing is deleted. Exit criteria are written before a phase starts and checked
by an independent gate at its end; a phase closes with an open criterion only if you
accept the miss (logged). Session start: read handoff, phase file, CLAUDE.md, TODO.md,
memory; confirm a clean tree and a green fast suite; Plan mode to confirm or refine the
steps. Session end: exit criteria checked, full suite, demo recorded, trackers and status
lines updated, next phase file fact-checked against the code as it then is, handoff and
prompt rewritten, memory updated, final commit.

## SP1 steps (this session)

Each step: implementer, adversarial reviewers (physics or numerics skeptic, CLAUDE.md
compliance; honesty auditor for findings), up to two fix rounds, independent gate,
commit, tracker update. Steps run as multi-agent workflows. Standing gate on every code
step: fast suite green, ruff clean, golden 1-D byte-identical; the full suite after
physics-core steps (4, 5, 6).

| # | Step | Main files | Gate |
|---|---|---|---|
| T | Tracking system: protocol, program board, phase files SP1-SP6 (SP2-SP6 from the designs in this plan), TODO.md restructure with IDs, decisions D-nnn for this session, handoff archived, memory updated | docs/process, docs/phases, TODO.md, CLAUDE.md, memory | Compliance review; commit |
| 1 | Guard and merge rule: pin digests of every resolved run and vehicle dict of the four shipped planar experiments (captured before any change); exclusive key families in `merge_run_dicts` and `_set_path` so a variant or sweep axis that sets one parameterisation drops the base's others | src/launchsim/config.py; tests/test_config*.py | Digests and golden unchanged |
| 2 | Exit-speed option: `ConstantAccelConfig` takes exactly one of `net_accel_g` / `exit_speed_mps` (a = v^2/(2L)); planar metrics `net_accel_g`, `net_accel_mps2`, `stroke_m`; replay reads the metric | config.py, assist/constant_accel.py, metrics_planar.py, replay.py | Exit speed and push time vs closed form at 1e-9; trajectory equals the equivalent `net_accel_g` run |
| 3 | Ramp start by depth, speed and closed-form height: `at_depth_m`, `at_speed_mps`, `at_height_m` + `height_method`; one resolver `prelude.resolve_ignition` used by both spec build sites (sim.ignition_specs, SearchContext.from_run), converting to the existing (t_ign_s, reference); refusals (pad, later stages, depth > stroke, speed > exit speed, height above the drag-free apex); preflight check before a results directory is made; planar metrics for requested and achieved ramp-start time, depth, height, speed | config.py, phases/prelude.py, assist/constant_accel.py, sim.py, search.py, metrics_planar.py, summary.py | Ignition-event depth and speed vs closed forms (1-D and planar); handoff table rows reproduced |
| 4 | Altitude event for `height_method: event`: `ev_altitude_up` in the engine; `_coast` takes extra events (planar and 1-D); `FlightStart` distinguishes "lights at a height" from "fails"; apex before the height is a typed failure (`no_ignition`); physics.md updated in the same change | phases/engine.py, planar.py, vertical.py, prelude.py, guidance.py, docs/physics.md | Event altitude = mouth + h (with drag and rotation); event time = closed form in constant-g vacuum; default runs have identical event tuples; full suite |
| 5 | Offload solver core: `vehicle.with_offload`; new `offload.py` with `OffloadProblem` (a `RecordingProblem` whose abscissa is the offload, built from a problem factory so the 3-D models can reuse it) and `solve_offload`: `optimise_gamma` then `final_verify` unchanged, recorded run at P_ref with 0 <= m_res < 0.05 kg, then an independent full payload search at the solved load that must reproduce P_ref | offload.py (new), vehicle.py, search.py (extract the body of `SearchContext.evaluate`), tests/test_offload.py | Toy closed forms (vacuum two-stage with a head start; equals `stage1_propellant_saved_kg` when Isp matches); pad control ~ 0 for stage 1; pad and silo_cold P* reproduce 26,054.4 and 27,553.2 kg within 0.002 kg; 10x tighter budget moves the offload < 0.1%; full suite |
| 6 | Cross-vehicle decomposition: for two runs at the same payload and orbit, the reduction in ideal delta-v = release-speed term + differences in gravity, drag, steering, back-pressure, pre-release and fairing terms, from the existing loss budget and rocket-equation closure (no change to loss accounting) | compare.py, tests/test_closure.py | Residual below `closure_tol_mps` on the gate vehicle; toy with zero losses |
| 7 | `offload:` experiment block, pipeline and reporting: cases (`solve: stage1 | stage2 | both`, or `fixed:` offload = the plain "reduce propellant by X" knob), optional stage-2 pre-offload and assumed added stage-1 dry mass, pad control, sensitivity, sourced RP-1 fractions and heating value; sweeps can solve the offload per point; summary block "Propellant saved at fixed payload"; `metrics.json` key; replay accepts offload runs; entry point callable with an in-memory experiment dict (for the SP2 app) | config.py, results_io.py, summary.py, compare.py, replay.py, cli.py | Schema refusals; energy arithmetic; small-grid end-to-end; existing planar outputs unchanged when no block is declared |
| 8 | Experiments, pre-registered: `experiments/silo_offload_2d.yaml` (shared blocks verbatim) and a one-case bridge on the README-loads vehicle (inside the calibration band); committed before any run | experiments/, tests/test_config_planar.py | Resolves; committed; clean tree |
| 9 | Runs and findings: run and sweep from the clean commit; `docs/findings/RQ1-fuel-offload-2d.md`; physics.md, README results, findings index | results/ (summaries), docs/findings | No `bug_suspect`; decomposition explains the beat over the ideal screening estimate; honesty review |
| 10 | Close SP1: exit criteria gate; demo recorded; SP2 phase file fact-checked; handoff and prompt for SP2; memory; status lines | docs/, TODO.md, CLAUDE.md, README.md, memory | Independent gate; final commit |

### Design points behind the steps (checked against the code)

- **Why an `offload:` block and not a new figure of merit.** `search.figure_of_merit` is
  a shared, pre-registered block; tests require it identical across shipped experiments
  and every field written in each YAML. A separate block and a post-pass in
  `results_io.planar_experiment_result` leaves every shipped file and budget id untouched.
- **Offload definition.** x >= 0 removed along a mode (stage 1, stage 2, or both at an
  equal fraction), dry mass unchanged. F(x) = residual propellant at P_ref with gamma*
  optimised; the reported x* is the largest evaluated offload with F >= 0 at final
  tolerance (the same feasible-side convention as payload capacity). A single sign change
  on the bracket is required and checked afterwards (`offload_nonmonotone` flag).
- **Stage 2 needs a pad control.** physics.md ("Virtual propellant") records that adding
  975 kg of stage-2 propellant moved the gate pad's residual from -975.0 to -990.3 kg:
  stage-2 propellant is worth about nothing at the margin on this vehicle and guidance.
  So the pad itself may fly the reference payload with less stage-2 propellant. Every
  mode is therefore also solved on the pad; stage 1 must return ~0 (a consistency test),
  and stage-2 and both-stage numbers are reported net of the pad's, labelled as a
  property of the vehicle model. Stage 1 stays the only headline. "Both" = the
  equal-fraction solve plus the largest stage-1 offload at a fixed stage-2 offload.
- **Structural penalty rows.** Stage-1 offload re-solved with +2, +4 and +8.1 t of
  assumed stage-1 dry mass on the assisted run only.
- **Energy comparison.** RP-1 removed (from the sourced LOX/RP-1 split, kept in the
  experiment's offload block because the gate vehicle file is never edited), its
  combustion heat at a sourced or `assumed` heating value, the push's electricity, and
  the ratio, labelled "not an efficiency claim"; LOX production and generation losses
  are excluded and said so.
- **Screening rule.** The offload is expected to be about 3x the ideal screening
  estimate (README: 14 t at 77 m/s). The decomposition of step 6 must explain it; if its
  residual fails the checks the row is `bug_suspect` and blocks the finding.
- **Ramp start.** Depth, speed and closed-form height convert to a time before the run
  (exact for the constant-acceleration drive), so only the altitude event changes the
  planners. Requested and achieved values are both reported from the event record.
- **Nothing validated moves.** No shipped experiment or vehicle file changes. Touched
  validated code keeps neutral defaults and is guarded by the golden 1-D tier, the new
  planar digest pin and the two reproduced payload capacities. No new 1-D metric,
  summary row or assumption text.

### The experiment (step 8)

- Baseline pad; variants `silo_cold` (3 g, 100 m, cold start), `silo_hot_ramp_on_track`,
  `silo_cold_200m` (200 m at the same 76.71 m/s exit speed: lower felt g).
- Cases on `silo_cold`: stage 1 (headline, with sensitivity +/-10% on stage-1 dry mass,
  Isp, C_D, drive efficiency); stage 2; both; stage 1 with a 2 t stage-2 offload; stage 1
  with +2, +4, +8.1 t; fixed 5% and 10%; pad controls. Stage 1 on the hot ramp.
- Sweeps, each solving the stage-1 offload: depth 25-300 m at 3 g; depth 50-300 m at a
  fixed 76.71 m/s exit speed (same offload expected, lower g and power, longer facility);
  ramp start by depth (100 to 0 m below the mouth); ramp start by height (10-200 m, by
  event, plus two closed-form points).
- Estimated serial time: about 15 min for the run and 17 min for the sweeps (a solved
  case is about 33 s). No parallel option needed.

### Findings note (step 9): docs/findings/RQ1-fuel-offload-2d.md

Definition; headline with caveats beside it; why it exceeds the screening estimate
(decomposition); penalty rows and break-even; stage 2 and both with the pad control;
depth; ramp start; energy; sensitivity; limits; reproduction. Caveats that travel with
the number: calibration +14.3% (bridge row on the README-loads vehicle), sweep-optimized
and unthrottled guidance, no structural mass for the 4 g push, prescribed-acceleration
drive with a massless carriage and no shaft drag, max-Q of the offloaded run against the
pad's, tanks partly filled with mixture ratio kept and no ullage or centre-of-gravity
effects.

### SP1 exit criteria

1. Tracking system in place; phase files SP1-SP6 exist; handoff and prompt for SP2 written.
2. Exit-speed option and all four ramp-start parameterisations pass their closed-form tests.
3. Offload solver passes its toy closed forms; pad control ~ 0 for stage 1; the
   independent payload search reproduces P_ref at each solved case (or the case is flagged).
4. `silo_offload_2d` run and sweeps come from a clean committed tree with no `bug_suspect`.
5. Findings note passes the honesty review; headline stated with penalty rows and sensitivity.
6. Full suite green; golden 1-D and planar digests unchanged; ruff clean.
7. Demo recorded under docs/demos/SP1/.

### SP1 demo

    uv run python -m launchsim run experiments/silo_offload_2d.yaml
    uv run python -m launchsim sweep experiments/silo_offload_2d.yaml
    uv run python -m launchsim replay results/silo_offload_2d/<timestamp> --runs pad <offloaded silo run>

Look at: the "Propellant saved at fixed payload" block of summary.md, and the replay page
showing the full pad and the offloaded silo reaching the same orbit with the same payload.

## Designs for later phases (written into their phase files in step T)

### SP2: local app and 2-D scene (detailed design in SP2's Plan mode)

- Shared read-only run-directory loader (one JSON/YAML reader pair instead of four
  copies, directory checks, output-path rules); `plots.py` and `replay.py` switch to its
  public names. None of today's loaders carries pitch, thrust, stage, track columns,
  assist geometry or vehicle masses; the scene payload adds them.
- `launchsim app` on 127.0.0.1 with Python's standard-library HTTP server (no new
  dependency). Form: depth, exit speed or acceleration, ramp start (all five ways),
  stage-1 and stage-2 offload, structural penalty. Launch runs the same resolve and run
  path as the CLI in a worker and writes a normal results directory; the pad baseline is
  cached. App runs are labelled exploratory; findings come only from committed files.
- 2-D scene on canvas, reusing the replay page's clock, scrubber, run toggles, telemetry
  and caveats: silo cross-section with rings and carriage, rocket to scale with attitude
  from `pitch_rad`, plume from `thrust_vac_N`, tank fill levels (the offload is visible),
  hold-down, staging and fairing, camera from close-up to Earth curvature, pad and silo
  side by side. Shapes are a display-only block with sources or `assumed`. The spent
  stage's path is a display-only ballistic coast from the staging event state.
- To fix on the way: the fairing event's mass convention differs between drop cases;
  animate and replay disagree on output-path rules.
- Data for development: results/silo_screening_2d/20260930T175743Z (12 runs) plus SP1's
  offload runs.

### SP3-SP6: 3-D dynamics (design verified against the code)

`search.py` and the two inner solves in `guidance.py` see only protocols and are reused
unchanged; the planner, steering laws, four events, metrics and run assembly are written
new as copies so no planar number can move. Config: `dynamics: spatial_3d` with
`earth: {model: spherical | wgs84_j2}`; `rigid_6dof` as a fly-out. No new dependency.

- **S1 (SP3).** ECI Cartesian state. v' = -mu r/|r|^3 + (T e - D v_rel_hat)/m with
  v_rel = v - omega x r. Loss identity generalised (Coriolis does no work; the gravity row
  gains a lateral part reported beside it). Release map v = s' u + omega x r at any
  latitude and azimuth; the track stays 1-DOF. Guidance: rise, kick toward the azimuth,
  gravity turn along the v_rel vector, in-plane linear tangent on stage 2; inclination
  free and reported. Gates: planar pin test first; release 465.10 m/s at the equator and
  408.74 m/s at 28.5 deg; inclined e = 0.3 orbit for 10 revs with energy and
  angular-momentum-vector drift < 1e-8; equatorial-east run equals the planar planner at
  1e-9 and its payload capacity within 1 kg; loss identity < 1e-5 m/s; model-to-model
  record against 26,054.4 kg with a pre-registered expectation of |difference| < 5 kg.
- **S2 (SP5).** `EarthModel` with spherical and ellipsoid-J2 forms; geodetic altitude and
  local up. Target under J2 (default, stated): osculating circular at geocentric
  R_E + 200 km at cutoff. Gates: geodetic round trip; a = -grad U; energy with the J2
  potential and h_z conserved; nodal and apsidal rates within 1% of first-order closed
  forms; zero-J2, zero-flattening limit equals S1.
- **S3 (SP6).** Quaternion attitude, body rates, gimbal with actuator lag, normal force
  and moment, jet damping, PD attitude controller. Used as a fly-out of the
  3-DOF-optimised payload and guidance, not a new search. Vehicle data in a new fork;
  dimensions sourced from the Falcon User's Guide, mass-property and aero-moment data
  `assumed`; results presented as sensitivities. Research output: a cold start coasts
  without control authority until ignition. Gates: inertia closed forms; torque-free
  precession; angular momentum and rotational energy; fixed-q oscillation or divergence
  rate; trim angle; prescribed-attitude mode reproduces S1/S2.
- **SP4.** three.js globe scene in the app from the spatial time series; the offload
  experiment copied to `spatial_3d` with the same budget, offload % reported per model.

Size estimate for the 3-D work: about 8,200 source and 6,400 test lines over SP3, SP5, SP6.

## Verification (SP1)

- Per step: the gate in the step table, run by an independent agent, plus
  `uv run pytest -q -m "not slow"` and ruff; `uv run pytest -q` after steps 4, 5, 6 and
  before closing.
- Regression guards: golden 1-D tests; the planar digest pin of step 1; pad and
  silo_cold payload capacities within 0.002 kg of 26,054.4 and 27,553.2 kg.
- End to end: the two experiment commands from a clean commit; summary.md checked for the
  offload block, the decomposition residual, the pad controls and flags; the probe's
  10% / 41.1 t figure is compared with the solved value as a sanity check, not a target.
- Demo: the three commands above, output saved under docs/demos/SP1/; the replay page
  opened in the browser pane.

## Things to know before approving

- Stage-2 and both-stage offload numbers will be reported net of a pad control and may
  be small or ill-conditioned; the headline is stage 1.
- The max-Q of the offloaded silo run can exceed the pad's (38.4 against 37.2 kPa in the
  probe); it is reported beside the number, not constrained (no throttle model).
- The 3-D and app phases are several sessions of work; SP1 does not start them beyond
  writing their phase files.
