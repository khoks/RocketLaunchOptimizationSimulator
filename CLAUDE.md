# CLAUDE.md

## Project

launch-assist-sim is a research simulator for ground-powered launch assist. A rocket gets its first ~10–300 m/s from electrically powered ground hardware (a vertical maglev silo, a cable-pulled curved ramp, a straight track), and we measure the effect on payload, propellant, losses, loads, energy and peak power. Every result is a delta against the same rocket launched from a pad.

- Background, prior art, first-order numbers and research questions: README.md. Read it before planning experiments.
- Report findings plainly, including ones that undercut the hypothesis that every m/s of assist helps.
- Status: Phases 0 and 1 done (scaffold, atmosphere, configs, CLI, results I/O; 1-D vertical model with staging; constant-acceleration vertical silo push pulled forward from Phase 3; 346 tests; first concept-A numbers in docs/findings/). Phase 2 done (2-D rotating-Earth ascent with drag, guidance and payload search; calibration missed high by +14.3% and the user accepted the documented miss; first 2-D concept-A findings in docs/findings/). Work now runs as one session per phase (program board: docs/phases/README.md). SP1 done (2026-10-04: launch settings, the fuel-offload solver and the RQ1 finding in docs/findings/RQ1-fuel-offload-2d.md, the tracking system, the public repository). SP2 (local app with the 2-D launch scene) is next, then SP7 (structural mass of the push load and a force-limited drive), then the 3-D phases SP3-SP6 (D-SP1-18). The next session starts from docs/handoff/NEXT_SESSION.md; see TODO.md. Update this line when a phase's exit criteria pass (docs/phases/README.md, README roadmap).

## Commands

Create these in Phase 0 and keep this list accurate.

- Setup: `uv sync` (fallback: `python -m venv .venv && pip install -e ".[dev]"`)
- Fast tests: `uv run pytest -q -m "not slow"`
- All tests: `uv run pytest -q`
- Lint and format: `uv run ruff check . && uv run ruff format .` (Windows PowerShell 5.1 has no `&&`: run the two commands separately, or use Git Bash)
- One run: `uv run python -m launchsim run experiments/<name>.yaml [--variant NAME] [--no-plots] [--no-sensitivity] [--no-offload]` (`--no-offload` skips an experiment's offload block; `--no-sensitivity` also skips its sensitivity arms)
- Sweep: `uv run python -m launchsim sweep experiments/<name>.yaml [--no-plots] [--no-offload]`
- Animate a 2-D run (MP4/GIF): `uv run python -m launchsim animate results/<experiment>/<timestamp> [--runs NAME ...] [--out PATH]`
- Interactive replay page (HTML): `uv run python -m launchsim replay results/<experiment>/<timestamp> [--runs NAME ...] [--out PATH]`
- Local app (127.0.0.1 only, Ctrl+C stops it): `uv run python -m launchsim app [--port N] [--results-root PATH] [--open]`
- 2-D launch scene page (standalone HTML): `uv run python -m launchsim scene results/<experiment>/<timestamp> [--runs NAME ...] [--out PATH] [--display PATH]`

## Layout

```text
src/launchsim/
  constants.py   Earth and physical constants; the only place μ, R_E, ω_E and g0 are defined
  units.py       unit conversions at the YAML/plot boundary (deg, km, kN, t, g, kWh); the only place those factors appear
  atmosphere.py  ICAO standard atmosphere: layer closed forms evaluated from `ambiance`'s constant table (ambiance.Atmosphere is the test oracle; valid to ~81 km) plus a documented isothermal extension above
  vehicle.py     stages, engines, drag vs Mach, mass bookkeeping, thrust schedules, ideal-rocket-equation screening
  config.py      pydantic models that validate vehicle and experiment YAML and convert units; no file I/O
  assist/        swappable assist models: base (interfaces), none, constant_accel, linear_motor, track (geometry), cable_winch
  dynamics.py    equations of motion: 1-DOF track phase, 2-D planar ascent
  phases/        phase sequencing and events (ignition, release, staging, insertion, impact): engine (generic integrator, event rules), trace (StateView, event records), prelude (hold and track), vertical (1-D planner), planar (2-D planner)
  guidance.py    steering laws (vertical rise, kick, gravity turn, linear-tangent), gamma* inner solve, LTG shooting
  orbit.py       circular target orbit and orbital elements
  search.py      figure-of-merit searches (residual, payload capacity, gamma* sweep, final verification); "sweep-optimized" until Phase 5
  offload.py     fixed-payload propellant offload solver; pure
  losses.py      loss integrals, the budget check and the planar rocket-equation closure
  sim.py         run one configuration (vertical_1d or planar_2d dispatch) and return a Result; re-exports the split modules
  metrics.py     1-D metrics and time series
  metrics_planar.py  planar metrics, max-Q, q-alpha and felt loads
  compare.py     comparison against the baseline, closure, attribution, screening checks, sensitivity
  summary.py     summary.md text
  results_io.py  run directories, provenance (git, pre-registration state), writers, experiment and sweep entry points
  plots.py       plot writers (Agg) and the `animate` MP4/GIF replay
  replay.py      the `replay` command: a self-contained interactive HTML replay page (template in templates/replay.html)
  run_data.py    shared read-only reader of a results directory: file readers, directory check, run selection and roles, series and event readers (mass before and after each drop), calibration records, the output-path rule; no matplotlib
  display.py     display-only reconstructions of the 2-D scene, pure: the display-file models, tank levels and their load-time checks, separation state and vacuum coast, screen transform and camera law, row selection, held attitude; never model output
  scene.py       the 2-D scene: the data payload of a planar results directory (reads through run_data and configs/display/), its strict-JSON encoding, and the standalone page (render_page fills templates/scene.html; write_scene_page writes only the page, never inside a results tree)
  appform.py     the local app's form, pure: the basis of the two committed experiments, the request parser (whitelisted keys, enumerated choices, finite bounded numbers), the presets, build_experiment (experiment app, label exploratory, committed names only for committed configurations), the derived values and the one-line refusals
  app.py         the local app's launch function: load_basis, the server-start git state and the code-change check, the in-memory pad cache, run_launch (results_io's pieces in run_experiment's order, FAILED.txt on any exception, no PNG plots) and the outcome of a written directory; the server (AppServer and AppHandler: 127.0.0.1-only bind, the request guard, the routes, one launch worker, the run browser and results-panel data, the Ctrl+C and Ctrl+Break stop)
  optimize.py    ascent optimization (Phase 5)
  cli.py
  templates/     package-data page templates: replay.html (the replay page; frozen in SP2), scene.html (the standalone 2-D scene page that scene.py renders and writes; no request, state hook window.launchsimScene) and app.html (the app page; a placeholder until step A5)
configs/vehicles/  one YAML per vehicle; every number has `source:` or `assumed: true`
configs/display/   display-only geometry of the 2-D scene (one YAML per vehicle family, applies_to names the vehicles; scene.yaml for the camera, pixel thresholds and the generic shape); every number has `source:` or `assumed: true`; nothing here enters the model
experiments/       one YAML per experiment: baseline, variants, sweep axes
results/           generated, never hand-edited; gitignored except */summary.md
docs/physics.md    equations and assumptions; the source of truth for the math
docs/findings/     one write-up per research question
docs/process/      SESSION_PROTOCOL.md: how every session runs (start checklist, step loop, end checklist, ID conventions)
docs/phases/       program board (README.md), one file per phase (SP<n>-<slug>.md: brief, step table, exit criteria, session log), inputs/ (dated plans, designs and code surveys)
docs/handoff/      NEXT_SESSION.md (the live handoff, read first by a new session) and archive/ (earlier handoffs)
docs/demos/        recorded demo of each finished phase (SP<n>/; created when a phase closes; SP1 so far)
notebooks/         exploration only; nothing experiments depend on
tests/
```

## Conventions

- SI units everywhere in code. Degrees, km, kN and tonnes appear only in YAML and plot labels, converted at the boundary. Names carry units when not obvious: `alt_m`, `thrust_N`, `isp_s`, `pitch_deg`.
- Angles are radians internally. Never pass a `_deg` value to a trig function.
- `g0 = 9.80665` converts Isp and defines the unit "g" for `_g` inputs and load reports (units.py); it is never a gravity model. Gravity in the ascent is μ/r²; the track phase uses the constant g_eff defined below; any other constant g appears only in named analytic tests.
- Constants live in constants.py: μ = 3.986004418e14 m³/s², R_E = 6 378 137 m, ω_E = 7.2921150e-5 rad/s.
- Track frame: origin at track start, x downrange along the launch azimuth (default east), z up. Geometry is a function of arc length s: track angle φ(s) above horizontal, t̂ = (cos φ, sin φ), n̂ = (−sin φ, cos φ) (t̂ rotated +90°), signed curvature κ = dφ/ds (positive when curving up). The track phase uses a flat local frame with constant g_eff = μ/R_E² − ω_p² R_E; Coriolis (~0.01 m/s² at 77 m/s) is neglected. List both in assumptions.
- Ascent frame: planar, Earth-centred inertial, containing the launch site and azimuth. State [r, θ, v_r, v_θ, m], with θ increasing downrange. Planar Earth rotation rate ω_p = ω_E cos(lat) sin(az): exact for an equatorial east launch, an approximation otherwise.
- Flight-path angle γ is the velocity's angle above local horizontal; pitch is the thrust direction's angle above local horizontal. Always say which velocity (inertial or Earth-relative) an angle refers to.
- The atmosphere co-rotates with Earth, so drag uses v_rel = v − ω × r.
- Every physics function's docstring states inputs, outputs, units and frame.

## Physics model

docs/physics.md holds the full derivations; keep it in sync with the code. A run is a sequence of phases joined by events:

1. Hold (optional): vehicle restrained on the pad or carriage; engines may start.
2. Assist: 1-DOF along the track, s from 0 to L:
   (m_v + m_c) s̈ = F_drive·t̂ + T_axial − (m_v + m_c) g_eff (t̂·ẑ) − D_air − F_friction − F_piston
   - Report the track normal load for vehicle and carriage separately: N = m (κ ṡ² + g_eff n̂·ẑ) − F_other·n̂, where F_other is any applied force with a normal component (e.g., a cable pulled from a fixed point). Report it in g's.
   - Report the felt axial acceleration of the vehicle (a full stack pushed up at 3 g net feels 4 g) and the interface force between vehicle and carriage.
   - Drives: `constant_accel` (screening); `linear_motor` with F = min(F_max, P_max/ṡ) and efficiency η; `cable_winch` = drum (inertia J, torque and power limits) plus cable as a spring-damper (k = EA/ℓ, damping c), pulley ratio n, cable mass included. Tension acts along t̂ unless the config sets a fixed pull point.
   - Silo runs either model the air column (piston force) or state that the shaft is vented.
   - Report carriage braking distance v²/(2 a_brake) and include it in facility length.
3. Release at s = L (or ṡ = v_target). The carriage stays. Map the vehicle state into the ascent frame, adding ω_p r to the downrange component.
4. Ignition at t_ign relative to release (negative means lit on the track). Thrust builds as a ramp or first-order lag with time constant τ; mass flow follows thrust.
5. Ascent:
   ṙ = v_r;  θ̇ = v_θ/r;  v̇_r = v_θ²/r − μ/r² + (T_r + D_r)/m;  v̇_θ = −v_r v_θ/r + (T_θ + D_θ)/m;  ṁ = −T_vac/(g0 Isp_vac)
   Thrust T = max(0, T_vac(t) − p_amb A_e) while an engine runs, 0 when off; T_vac(t) includes the startup ramp and ṁ follows T_vac(t). Drag D = ½ ρ |v_rel|² C_D(M) A_ref, acting along −v_rel.
   Guidance: vertical rise, pitch kick, then gravity turn (thrust along v_rel) on stage 1; linear-tangent steering (tan pitch = a − b t) on stage 2, solved by shooting for target altitude and γ = 0.
6. Staging: drop dry mass (and the fairing when scheduled), coast, ignite the next stage.
7. Insertion: stop at the target orbit. Figures of merit, in increasing fidelity: ideal rocket-equation screening; residual propellant and Δv margin at a fixed payload; payload capacity by bisection (zero residual propellant at insertion).

Loss accounting uses the Earth-relative velocity v_rel. Drag acts exactly along −v_rel, Coriolis does no work, and centrifugal folds into effective gravity g_eff = μ/r² − ω_p² r, so this identity must close:

|v_rel,f| − |v_rel,0| = Δv_vac − gravity − drag − steering − back-pressure

where Δv_vac = ∫ T_vac/m dt, gravity = ∫ g_eff sin γ_rel dt, drag = ∫ D/m dt, steering = ∫ (T/m)(1 − cos ψ) dt (ψ is the angle between thrust and v_rel), and back-pressure = ∫ (T_vac − T)/m dt (this keeps the identity exact when thrust is clamped at zero). Accumulate from release onward; the assist phase has its own energy budget. Use γ_rel = atan2(v_r, v_θ − ω_p r) everywhere, including through apex in fall-back runs; fall back to local vertical only when |v_rel| < 1e-9 m/s (a pad start).

Integrator: scipy `solve_ivp` (DOP853 or RK45) with an event at every phase boundary; rtol ≤ 1e-9 in tests.

## Validation first

No physics feature is used in an experiment until its test passes. Required tests:

- Rocket equation, vacuum, no gravity: Δv = c ln(m0/mf), relative error < 1e-6.
- Vertical burn, constant g, no drag: v_f = v_0 + c ln(m0/mf) − g t_b, for several v_0.
- Elliptical orbit (e ≈ 0.3) for 10 revolutions: specific energy and angular momentum drift < 1e-8 relative; period = 2π√(a³/μ). Don't use a circular orbit: in polar coordinates it is an equilibrium and passes even with a wrong v̇_θ term.
- Vacuum coast: apex = v_0²/(2g) with constant g; energy conserved with μ/r².
- Straight track, constant force: v = √(2aL), t = v/a.
- Frictionless, unpowered circular-arc ramp of radius R starting horizontal: v² = v_0² − 2gR(1 − cos φ) and N/m = v_0²/R − 2g + 3g cos φ (closed form, not the code's own formula).
- Release mapping: an equatorial east pad launch starts at 465.1 m/s inertial.
- Loss budget closes to < 0.01 m/s over a full ascent.
- Assist energy, including hot starts with changing mass M: ∫ (F_drive·t̂ + T_axial) ṡ dt = Δ(½ M ṡ² + M g z) − ∫ Ṁ (½ ṡ² + g z) dt + dissipated, relative error < 1e-6.
- Cable: small-oscillation frequency = √(k/m).
- Convergence: tightening tolerances 10× changes payload and margins by < 0.1%.

Calibration is separate from validation; label it as such:

- configs/vehicles/generic_f9_class.yaml reaches ~22,800 kg to low Earth orbit (28.5°, expendable) within ±10% after a guidance sweep. SpaceX doesn't publish the reference altitude, so fix one (e.g., 200 km circular) and state it. Record every fitted parameter.
  - Phase 2 result: the pre-registered 2-D gate fork generic_f9_class_2d.yaml reached 26,054 kg to 200 km circular (+14.3%, a miss high); the user accepted the documented miss on 2026-09-30 (docs/findings/CAL-f9-leo-2d.md).
- Published claims (e.g., NASA's "over 20%" propellant saving) are benchmarks to explain, never targets to tune toward.
- The hobby-scale case matches RocketPy apogee within ±5% (Phase 6).

## Experiments and reporting

- Each experiment YAML defines a pad baseline with the same vehicle, plus variants. All of them share the guidance parametrisation, sweep grid and optimizer budget; free guidance parameters are sweep-optimized per run. Until Phase 5, call results "sweep-optimized".
- Write each run to results/<experiment>/<UTC timestamp>/: resolved config, git hash, metrics.json, time series (parquet or CSV), plots, summary.md. Never overwrite a results directory.
- Every summary reports, against baseline: payload or residual propellant; the gravity, drag, steering and back-pressure losses; max-Q; peak felt axial g and the peak interface force; peak track-normal g; assist energy (J and kWh); peak drive power; facility length including braking; and the list of assumptions.
- Headline numbers get a sensitivity check: ±10% on stage-1 dry mass, Isp, C_D and drive efficiency.
- If an assisted run beats the README's ideal screening estimate for its release speed, the loss breakdown must explain why (for example, lower gravity loss). If it doesn't, treat it as a bug.
- Conclusions go in docs/findings/RQ<n>-<slug>.md, next to the plots they rest on.

## Code style

- Python 3.12, type hints everywhere, frozen dataclasses for parameters, pydantic to validate YAML.
- Physics functions are pure: no globals, I/O or printing. I/O lives in cli.py, sim.py, results_io.py, plots.py, replay.py, run_data.py, scene.py and app.py.
- Small functions with docstrings. No magic numbers outside constants.py and configs.
- ruff for lint and format. Mark tests slower than 5 s with `@pytest.mark.slow`.

## Working rules

- Use Plan mode for anything touching equations of motion, frames, events, integrator settings or loss accounting, and update docs/physics.md in the same change.
- Run the fast tests before calling a task done; run all tests after any physics-core change.
- Never tune parameters to make an assist look better. Never change baseline settings without re-running every variant compared against it.
- Don't edit a calibrated vehicle config; copy it to a new file.
- Justify every new dependency in one line in the change summary.
- Ask before expanding scope (6-DOF, 3-D Earth, structural FEM), deleting results, or replacing a validated model.
- Follow docs/process/SESSION_PROTOCOL.md: its start checklist, step loop and end checklist. One phase per session. Update the phase file's step table (docs/phases/SP<n>-<slug>.md) at every gate.
- TODO.md is the program-level tracker: milestones, current phase, priorities, backlog, decisions log and known issues. Per-phase step tables live in docs/phases/. Update TODO.md when a step's gate passes.
- The repository is public on GitHub (https://github.com/khoks/RocketLaunchOptimizationSimulator), all rights reserved (LICENSE). Push main after every step's tracker commit and at every phase close; never force-push. Commits use the GitHub noreply email set in this repo's git config. Keep the public face current at each phase close: the GitHub Pages site (site/, built by site/build.py and deployed by .github/workflows/pages.yml), the slide deck, the animation gallery and the user manual (docs/manual/). Public text follows the same honesty rules as the findings: no number without its source and caveats, no probe presented as a finding, never call the project open source.
