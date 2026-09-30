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
- [x] M6 Phase 2 plan (2-D ascent, rotation, drag, guidance, payload search, calibration): written 2026-09-29 from 3 designs, 9 reviews and a critique; defaults below apply unless the user objects
- [!] M7 Phase 2 gate: validation tests pass; the pre-registered gate vehicle (set C) MISSES HIGH: P* 26,054 kg, +14.3%, 974 kg above the 25,080 kg band edge (set A 24,700 kg +8.3% inside; set B 25,416 kg +11.5% outside). Stopped for your decision (2026-09-30); docs/findings/CAL-f9-leo-2d.md
- [ ] M8 2-D concept-A results: silo_screening_2d (with ignition sweeps), bridge and trigger studies; RQ2-2d, RQ3-2d, RQ6 preliminary
- [ ] M9 Phase 2 closed: physics.md, CLAUDE.md layout and status, README status, TODO

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

## Phase 2 build steps (plan section 10 and section 14 amendments)

| # | Step | Status | Gate / notes |
|---|---|---|---|
| 14 | Pre-registration of decisions (no code); tracker rows | [x] | decisions logged below with defaults |
| 15 | Golden capture of every 1-D output + test_golden_1d | [x] | 121 golden tests (silo_screening_1d plus a paths set covering staging, apex, no-liftoff, drive-limit, fall-back ignition) |
| 16 | Split sim.py into sim, metrics, compare, summary, results_io, plots | [x] | 1-D CLI outputs byte-identical (23/23 experiment, 129/129 sweep digests) |
| 17 | phases/ package (engine, trace, prelude, vertical); y_events, nfev, dense-off setting | [x] | full suite + golden |
| 18 | Aero data layer: ambient_scalar, C_D PCHIP, drag, fairing rule; three 2-D vehicle forks | [x] | full suite + golden |
| 19 | Config schema: dynamics, shared blocks, target orbit, search/ltg/checks, bounds, cases; four experiment YAMLs | [x] | 1-D resolved dicts identical; all four YAMLs resolve |
| 20 | Planar EOM, orbit.py, H0 gravity; orbit/coast/rocket-eq/pointwise-identity/reduction tests | [x] | elliptical orbit (DOP853 and RK45) drift < 1e-8 |
| 21 | Stage-1 planner and guidance: hold, release map, rise, kick, gravity turn, staging, gamma* solve | [x] | 465.1 m/s release test; Culler-Fried gravity turn |
| 22 | Stage 2: LTG law and shooting, energy cutoff, fairing, insertion, max-Q, loads | [x] | full-ascent loss budget closes < 1e-5 m/s (pad, silo, clamped thrust, fall-back) |
| 23 | search.py: residual, payload capacity, gamma* sweep, final verify | [x] | searched pad run 7-10 s; lag variants 25-28 s |
| 24 | Pipeline: dispatch, planar metrics, compare with closure/attribution/checks, summary, plots | [x] | full suite + golden |
| 25 | Convergence and performance gate; slow marks | [x] | every CLAUDE.md Phase 2 required test green; fast tier 43 s, full 230 s |
| 26 | Calibration (labelled): three mass sets, checklist, CAL-f9-leo-2d.md | [x] | frozen at c2849b7; run 20260930T100100Z; gate C misses high (M7 [!]); every numerical check passes; slow regression test without a band |
| 26a | Step cap (2 s, planar) and M2 as diagnostic; pre-registration amendment; calibration re-run | [~] | implemented and gated (908 tests, golden byte-identical); amendment committed; calibration re-run next |
| 27 | Research experiments: trigger study, silo_screening_2d, bridge; RQ2/RQ3-2d, RQ6 | [ ] | unblocked by the user's decisions; after 26a |
| 28 | Close Phase 2 | [ ] | |

## Priorities

1. P0 Physics correctness and honest tests (validation first; closed forms computed in the tests).
2. P1 Phase 0 and Phase 1 gates with the CLAUDE.md commands working on Windows.
3. P2 Concept-A numbers and the two preliminary findings notes.
4. P3 Polish: plots, docs completeness, slow-test hygiene.

## Todo (near term)

- [x] Plan Phase 2 in Plan mode (equations of motion, frames, events): PlanarDynamics2D, rotation and the 465.1 m/s release test, atmosphere in the RHS, drag and back-pressure, guidance, payload bisection, elliptical-orbit test, calibration fork of the F9 file.
- [x] Won't fix: track-normal g of 6e-17 on vertical tracks is cos(pi/2) roundoff; the summary prints 0 and a clamp would need a magic tolerance.
- [x] config.SweepPoint.sweep_index is now 1-based like the sweep_<n> directories (test added).
- [ ] Results retention: three run+sweep pairs from 2026-09-29 have tracked summaries (cited pair 103623Z/103634Z, reviewer pair 104503Z/104510Z, gate pair 105657Z/105707Z); decide whether to keep only cited pairs (deleting results needs your OK per CLAUDE.md).
- [ ] Phase 2 prep: re-source the F9 propellant loads and stage-2 dry mass in the calibration fork (FT spec sheet values differ from the README generics).

## Future items (deferred, with hooks in place)

- Phase 2: PlanarDynamics2D, Earth rotation (omega_p r release mapping, 465.1 m/s test, h0 gravity form), atmosphere in dynamics, drag, back-pressure, guidance (pitch kick, gravity turn, linear-tangent), payload bisection, max-Q, insertion, elliptical-orbit test, calibration fork of the F9 file, throttling.
- Phase 3: linear_motor, curved TrackGeometry and the frictionless-arc test, cable_winch, air-column piston, friction, modelled carriage braking, release at a target speed, tilted-exit abort with Coriolis, interface-hardware mass penalty, engine shutdown transients.
- Later: parquet, multiprocessing sweeps, notebooks, optimize.py, RocketPy comparison, findings for RQ1-RQ8.

## Decisions log

Phase 2 pre-registration (2026-09-29; defaults from the plan, each open to objection until the pre-registration commit before step 26):

- Calibration mass sets A (README), B (recorded re-sourcing scope) and C (full FT table with Block 5 thrust, version mix disclosed) are all run and reported with equal prominence; default gate C on provenance (546.3 t of 549 t launch-mass closure). Prototype disclosure: A about 25,082 kg (+10.01%, 2 kg above the band edge), C roughly +10 to +14%, B not prototyped; indicative only.
- Reference orbit 200 km circular (r_t = 6,578,137 m), 28.5 deg, due east, expendable; never moved.
- Fitted or solved in calibration: guidance outputs only (gamma*_MECO, delta, LTG a and b). Fixed inputs: A_ref 10.52 m^2 (21.24 m^2 as a bound case), Braeunig C_D(M) with PCHIP, fairing jettison at 1,135 W/m^2, 11 s staging coast, stage-2 A_e 8.6 m^2 (assumed), no throttle, no reserves. On a miss: report, checklist, stop, ask.
- Shared across runs: guidance parametrisation, gamma* grid 8-36 deg step 2, tolerances, LTG settings; gamma* sweep-optimized per run. v_k = 50 m/s and the hold-to-alignment kick were chosen with prototype knowledge; the trigger study reports best-vs-best dP*, and headlines are quoted against the pad's best v_k if it beats v_k = 50 by more than 5 kg.
- Deferred: throttling (max-Q reported unthrottled), --jobs parallelism (unless an experiment exceeds 30 min serial).
- Layout: phases/ package; sim.py split into sim, metrics, compare, summary, results_io, plots; new guidance.py, orbit.py, search.py; optimize.py stays for Phase 5.
- Output angles in _rad; degrees only in summary cells and plot labels. Nothing in results/ is deleted.

User decisions, 2026-09-30 (answers to the step-26 questions):

- Calibration miss accepted as documented: the research experiments run on the gate vehicle (set C) as is, and every finding carries the miss (+14.3%).
- Mechanism check M2 becomes diagnostic only: still computed and reported, no longer sets bug_suspect; the rocket-equation closure, the loss identity and M3-M5 still block findings. Recorded as checks.m2_role: diagnostic in the planar experiments.
- Planar max_step cap of 2 s adopted (planar flight phases only; 1-D untouched); the inner-solve acceptance tightens accordingly. Recorded as an explicit shared setting; the calibration is re-run from the amended commit so its record matches.
- These change pre-registered experiment blocks, so they are committed as a pre-registration amendment before any research run; the original freeze (c2849b7) and its calibration run stay on record.

Phase 2 build (2026-09-30), deviations from the plan recorded as built (none changes a figure of merit beyond search noise; details in docs/physics.md):

- gamma* inner-solve acceptance: 3e-6 rad as first built (uncapped noise floor from the transonic C_D knots), tightened to 3e-7 rad with the 2 s planar step cap the user approved on 2026-09-30 (capped floor about 1e-7 rad; the plan's 1e-9 rad is below any floor). The cap moved the gate pad's P* by -0.0001 kg.
- A kick that times out inside the delta inner solve maps to a sentinel instead of failing the grid point (with rotation, the bracket's 0.1 deg low end never aligns).
- refine_capped is reported as a flag, not a search failure.
- The lag startup's step cap holds for the whole lag-lit burn (silo_cold_lag costs about 2.5x the pad's RHS calls); a cap over the first few tau only is left open.
- First-step carry-over across planar phase boundaries was measured and not adopted.
- The gamma*-sensitivity diagnostic step moved into the pre-registered checks block (gamma_sensitivity_step_deg: 0.5).
- Calibration runs record the frozen-input state (last commit touching configs/ and experiments/, dirty paths); a dirty or unknown state is marked in summary.md and the CLI as not a valid calibration record.

Phase 0-1:

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

- Stage-1 measurement, not a finding (physics.md, Time-shift mechanism): at equal gamma* at MECO, a 77 m/s vertical silo release saves about a quarter of the gravity loss the plan's time-shift estimate predicted when both runs light at release, and about none for the cold start (0.5 s + 2 s ramp in the air); the silo leaves about 9% heavier than the pad at the same speed.

## Open questions for you (Phase 2)

- None open. Answered 2026-09-30 (see the decisions log).

## Known issues and observations

- silo_cold_lag's searched run takes about 25 s at normal machine speed, close to the 30 s per-run budget, because the lag's step cap holds for the whole lag-lit burn; options (a planar lag cap over the first few tau) are open, not needed for correctness.
- Planar convergence tests now run in the slow tier only (with the cap each takes just over 5 s).

- summary.md labels +/-10% vehicle-perturbation sensitivity cases of a pad baseline as 'Unexplained beats'; the screening rule should not apply when the baseline is a pad without an assist (cosmetic).
- Literature sizing of flight-performance reserve, unusable residuals and payload adapter mass is not in the calibration note (it uses the run's own conversions and says so); add it with citations if the calibration is revisited.

- README says one EMALS launch is 122 MJ; 45 t at 67 m/s is about 101 MJ (122 MJ is the rated maximum). Note in findings, do not edit silently.
- README ignition-loss band (5-25 m/s) covers the linear ramp; a first-order lag with tau = 1-3 s gives 10-39 m/s.
- The Bash tool failed to parse one very long multi-heredoc script; keep file-writing calls to ~150 lines.
