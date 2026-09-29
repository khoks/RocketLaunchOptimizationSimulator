# Work tracker

Living tracker for launch-assist-sim. Milestones follow the README roadmap; build steps
follow the approved plan (Phase 0 + Phase 1 + vertical constant-acceleration silo push).
Status marks: [x] done, [~] in progress, [ ] not started, [!] blocked or needs a decision.
Last updated: 2026-09-29 (steps 1-13 done; Phase 2 next).

## Milestones

- [x] M0 Plan approved: Phase 0 scaffold, Phase 1 1-D vertical rocket, concept-A silo push (2026-09-28)
- [x] M1 Phase 0 gate: 200 tests pass, all CLAUDE.md commands and the pip fallback work; first commit (2026-09-28)
- [x] M2 Phase 1 gate: rocket-equation, vertical-burn, coast-apex and staging tests pass; 269 tests green (2026-09-29)
- [x] M3 Silo push validated: straight-track, loads, assist-energy identity and failed-ignition tests pass (2026-09-29)
- [x] M4 First concept-A numbers: silo_screening_1d run + sweep, every identity line closes to ~1e-12 m/s, README-number smoke test passes (2026-09-29)
- [x] M5 Findings RQ2 and RQ3 (preliminary) in docs/findings/, status lines updated, commit (2026-09-29)
- [ ] M6 Phase 2 plan (2-D ascent, rotation, drag, guidance, payload search, calibration)
- [ ] M7 Phase 2 gate: orbit, loss-budget and convergence tests pass; generic F9-class within +/-10% of 22.8 t to LEO at a stated altitude

## Build steps (plan, "Build sequence")

| # | Step | Status | Gate / notes |
|---|---|---|---|
| 1 | git init, pyproject, constants, units, cli stub, scaffold tests | [x] | 10 tests pass, ruff clean, ambiance runs warning-free on NumPy 2.5.3 |
| 2 | atmosphere.py + ICAO/extension tests + docs/physics.md start | [x] | ICAO layer closed forms from ambiance's constant table (ambiance.Atmosphere is the 1e-12 oracle); 2 review rounds |
| 3 | config.py, vehicle.py, F9 YAML, experiment YAML, toy data, fixtures, tests | [x] | 542,570 kg; README screening table reproduced; 2 review rounds |
| 4 | cli.py + sim.py results I/O (placeholder run), tests -> Phase 0 gate | [x] | run/sweep write results dirs; independent gate passed |
| 5 | dynamics.py (gravity, 1-D RHS), phases.py engine, rocket-eq/vertical-burn/coast/events tests | [x] | event rules verified against scipy; 2 review rounds |
| 6 | VerticalPlanner, simulate/run, losses.py, staging/hold/ignition-loss/identity tests -> Phase 1 gate | [x] | exact ignition-loss forms and identity closure tested; 2 review rounds |
| 7 | assist/* (constant_accel, track, none), track RHS, release map, energy budget, silo tests | [x] | closed forms for exit speed, loads, energy identity (hot starts, f_imp 0/0.5/1) at 1e-10; 2 review rounds |
| 8 | failed-ignition coast + test | [x] | apex 300.27 m at 7.829 s, back at 15.658 s; also the parked carriage 60 m up the fall-back path at 14.83 s |
| 9 | full metrics, comparison, sensitivity, summary.md with identity line, plots | [x] | identity decomposition, screening payload equivalent (labelled), sensitivity vs both baselines |
| 10 | convergence test, slow marks | [x] | < 1e-6 relative under 10x tighter tolerances; no test exceeds 5 s |
| 11 | docs/physics.md complete (assumptions, test-to-equation map, Phase 2 note); ruff clean | [x] | 1,575 lines, checked against the code by a reviewer |
| 12 | run + sweep silo_screening_1d; verify identity lines; test_readme_numbers | [x] | results/silo_screening_1d/20260929T103623Z (run) and 103634Z (sweeps); two reproduction pairs |
| 13 | findings RQ2/RQ3 (preliminary); CLAUDE.md + README status lines; commit | [x] | 345 tests |

## Priorities

1. P0 Physics correctness and honest tests (validation first; closed forms computed in the tests).
2. P1 Phase 0 and Phase 1 gates with the CLAUDE.md commands working on Windows.
3. P2 Concept-A numbers and the two preliminary findings notes.
4. P3 Polish: plots, docs completeness, slow-test hygiene.

## Todo (near term)

- [~] Plan Phase 2 in Plan mode (equations of motion, frames, events): PlanarDynamics2D, rotation and the 465.1 m/s release test, atmosphere in the RHS, drag and back-pressure, guidance, payload bisection, elliptical-orbit test, calibration fork of the F9 file.
- [x] Won't fix: track-normal g of 6e-17 on vertical tracks is cos(pi/2) roundoff; the summary prints 0 and a clamp would need a magic tolerance.
- [x] config.SweepPoint.sweep_index is now 1-based like the sweep_<n> directories (test added).
- [ ] Results retention: three run+sweep pairs from 2026-09-29 have tracked summaries (cited pair 103623Z/103634Z, reviewer pair 104503Z/104510Z, gate pair 105657Z/105707Z); decide whether to keep only cited pairs (deleting results needs your OK per CLAUDE.md).
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

## Findings so far (details in docs/findings/)

- Cold start after a 3 g0 / 100 m push: +69.6 m/s at stage-1 burnout vs the pad = 76.7 exit + 5.4 hold-down credit - 14.7 ignition loss (0.5 s + 2 s ramp; exact constant-g form) + 2.2 altitude term. Ideal-screening equivalent 621 kg vs the README's 685 kg: the ignition loss outweighs the pad's hold-down waste.
- Hot starts under a prescribed-acceleration drive buy no exit speed: they trade 2.7-9.7 t of propellant (5.6-20.6 m/s at burnout vs the instant yardstick) for 0.47-0.85 GJ less drive energy and up to 40% less peak power, and only if the exhaust misses the carriage (f_imp = 1 removes the saving). A force-limited drive (Phase 3) is needed before the hot-start question can be answered.
- Loads: 4.0 g0 on the full 542.6 t stack during the push (21.3 MN interface force), against 5.7 g0 at stage-1 burnout in every variant (unthrottled).
- Lag startups cost more than the README's 5-25 m/s band: tau = 1/2/3 s gives 14.7/24.5/34.3 m/s with a 0.5 s delay.
- Failed ignition: apex 300.3 m at 7.83 s; the vehicle meets a carriage parked 60 m up the shaft at 14.8 s at 68.6 m/s, or the mouth at 15.66 s at 76.7 m/s.
- Sensitivity: the assist's benefit moves < 0.5 m/s under +/-10% stage-1 dry mass or Isp when compared against a baseline with the same perturbation.

## Known issues and observations

- README says one EMALS launch is 122 MJ; 45 t at 67 m/s is about 101 MJ (122 MJ is the rated maximum). Note in findings, do not edit silently.
- README ignition-loss band (5-25 m/s) covers the linear ramp; a first-order lag with tau = 1-3 s gives 10-39 m/s.
- The Bash tool failed to parse one very long multi-heredoc script; keep file-writing calls to ~150 lines.
