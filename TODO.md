# Work tracker

Living tracker for launch-assist-sim. Milestones follow the README roadmap; build steps
follow the approved plan (Phase 0 + Phase 1 + vertical constant-acceleration silo push).
Status marks: [x] done, [~] in progress, [ ] not started, [!] blocked or needs a decision.
Last updated: 2026-09-29.

## Milestones

- [x] M0 Plan approved: Phase 0 scaffold, Phase 1 1-D vertical rocket, concept-A silo push (2026-09-28)
- [x] M1 Phase 0 gate: 200 tests pass, all CLAUDE.md commands and the pip fallback work; first commit (2026-09-28)
- [x] M2 Phase 1 gate: rocket-equation, vertical-burn, coast-apex and staging tests pass; 269 tests green (2026-09-29)
- [ ] M3 Silo push validated: straight-track, loads, assist-energy identity, failed-ignition tests pass
- [ ] M4 First concept-A numbers: silo_screening_1d run + sweep, identity lines close, README-number smoke test passes
- [ ] M5 Findings RQ2 and RQ3 (preliminary), status lines updated, commit
- [ ] M6 Phase 2 plan (2-D ascent, rotation, drag, guidance, payload search, calibration)

## Build steps (plan, "Build sequence")

| # | Step | Status | Gate / notes |
|---|---|---|---|
| 1 | git init, pyproject, constants, units, cli stub, scaffold tests | [x] | 10 tests pass, ruff clean, ambiance runs warning-free on NumPy 2.5.3 |
| 2 | atmosphere.py + ICAO/extension tests + docs/physics.md start | [x] | ICAO layer closed forms from ambiance's constant table (ambiance.Atmosphere is the 1e-12 oracle); 2 review rounds |
| 3 | config.py, vehicle.py, F9 YAML, experiment YAML, toy data, fixtures, tests | [x] | 542,570 kg; README screening table reproduced; 2 review rounds |
| 4 | cli.py + sim.py results I/O (placeholder run), tests -> Phase 0 gate | [x] | run/sweep write results dirs; independent gate passed |
| 5 | dynamics.py (gravity, 1-D RHS), phases.py engine, rocket-eq/vertical-burn/coast/events tests | [x] | event rules verified against scipy; 2 review rounds |
| 6 | VerticalPlanner, simulate/run, losses.py, staging/hold/ignition-loss/identity tests -> Phase 1 gate | [x] | exact ignition-loss forms and identity closure tested; 2 review rounds |
| 7 | assist/* (constant_accel, track, none), track RHS, release map, energy budget, silo tests | [~] | code written by an interrupted agent (OAuth expiry); tests and docs pending; workflow resumed |
| 8 | failed-ignition coast + test | [ ] | |
| 9 | full metrics, comparison, sensitivity, summary.md with identity line, plots | [ ] | |
| 10 | convergence test, slow marks | [ ] | |
| 11 | docs/physics.md complete (assumptions, test-to-equation map, Phase 2 note); ruff clean | [ ] | |
| 12 | run + sweep silo_screening_1d; verify identity lines; test_readme_numbers | [ ] | |
| 13 | findings RQ2/RQ3 (preliminary); CLAUDE.md + README status lines; commit | [ ] | |

## Priorities

1. P0 Physics correctness and honest tests (validation first; closed forms computed in the tests).
2. P1 Phase 0 and Phase 1 gates with the CLAUDE.md commands working on Windows.
3. P2 Concept-A numbers and the two preliminary findings notes.
4. P3 Polish: plots, docs completeness, slow-test hygiene.

## Todo (near term)

- [ ] Launch the physics-core workflow (steps 5-13) with adversarial review per step.
- [ ] Step 9: make config.SweepPoint.sweep_index 1-based and drop the +1 in sim (carried from the CLI review).
- [ ] Phase 2 prep: re-source the F9 propellant loads and stage-2 dry mass in the calibration fork (FT spec sheet values differ from the README generics).

## Future items (deferred, with hooks in place)

- Phase 2: PlanarDynamics2D, Earth rotation (omega_p r release mapping, 465.1 m/s test, h0 gravity form), atmosphere in dynamics, drag, back-pressure, guidance (pitch kick, gravity turn, linear-tangent), payload bisection, max-Q, insertion, elliptical-orbit test, calibration fork of the F9 file, throttling.
- Phase 3: linear_motor, curved TrackGeometry and the frictionless-arc test, cable_winch, air-column piston, friction, modelled carriage braking, release at a target speed, tilted-exit abort with Coriolis, interface-hardware mass penalty, engine shutdown transients.
- Later: parquet, multiprocessing sweeps, notebooks, optimize.py, RocketPy comparison, findings for RQ1-RQ8.

## Decisions log

- 2026-09-28 constant_accel means prescribed net acceleration (drive force solved each instant); hot start therefore buys no exit speed and trades propellant for drive energy; report plainly.
- 2026-09-28 Earth rotation off in Phase 1 (omega_p = 0 on the track and in the ascent).
- 2026-09-28 Pad baseline: engines lit at t = -2 s under hold-down, full thrust at release; pad_instant and silo_instant are unphysical yardsticks.
- 2026-09-28 1-D figure of merit: stage-1 burnout speed and altitude deltas vs pad, decomposed by the loss identity; no residual-propellant metric in 1-D.
- 2026-09-28 Vehicle YAML all-Quantity (source/assumed); experiment YAML bare numbers.
- 2026-09-28 CSV time series, argparse CLI, uv_build backend, ambiance without a numpy pin.
- 2026-09-28 atmosphere.py evaluates the ICAO layer closed forms directly from ambiance's constant table (450x faster in the ODE RHS); ambiance.Atmosphere stays the test oracle at 1e-12 relative.
- 2026-09-28 results/: only the top-level summary.md of each run directory is tracked (nested sweep-point summaries are ignored).

## Known issues and observations

- README says one EMALS launch is 122 MJ; 45 t at 67 m/s is about 101 MJ (122 MJ is the rated maximum). Note in findings, do not edit silently.
- README ignition-loss band (5-25 m/s) covers the linear ramp; a first-order lag with tau = 1-3 s gives 10-39 m/s.
- The Bash tool failed to parse one very long multi-heredoc script; keep file-writing calls to ~150 lines.
