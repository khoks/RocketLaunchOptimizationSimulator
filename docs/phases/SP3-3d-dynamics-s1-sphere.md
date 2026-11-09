# SP3: 3-D dynamics S1, a 3-DOF point mass over a rotating sphere

Status: not started

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-09-30 in
the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md)) and the
3-D design ([inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md)).
Nothing in this file has been built or run in the repository; the numbers marked as a
review's replica (Q7, section 5.10, section 7's Tolerances) come from probes outside it
(KI-102). Sections 4, 6 and 13 were re-checked against the code by SP7's close-out
(protocol section 7, item 8): line by line at commit 6cf0fd2 on 2026-11-04, then
re-validated at commit d03367b on 2026-11-05, the commit this file now cites. At d03367b
git shows 3a07f07 (SP7 step S8) as the last commit that changed code and
9fe125c (SP7 step S7c) as the last that changed src/. It is the first re-check since the
file was written: the inventory had drifted through SP1, SP2 and SP7. Section 6 is
corrected in place, the entry criteria carry their state, and the prompt of section 13 is
final.

## 1. Goal and what you can see at the end

Build stage S1 of true 3-D dynamics: a 3-DOF point mass in Earth-centred inertial
Cartesian coordinates over a rotating spherical Earth, with the same atmosphere, drag,
thrust, staging, guidance family and payload search as the planar model, at any latitude
and azimuth. Validate it by closed forms and by reduction to the planar model, then record
how far its payload capacity sits from the planar gate.

At the end you can see:

- the new tests green, with the 1-D golden tier and the planar pin unchanged;
- a 3-D run from the CLI (`launchsim run` on an experiment with `dynamics: spatial_3d`)
  that writes a normal results directory with the spatial time series;
- the model-to-model record `docs/findings/M2M-3d-vs-planar.md`: the 3-D payload capacity
  against the planar gate's 26,054.4 kg at 28.5 deg, azimuth 90 deg, with the expectation
  that was written down before the run (difference under 5 kg) and the loss rows side by
  side.

This phase produces no new claim about the assist. It produces a second model that must
agree with the first where the first is exact, and a measured difference where it is not.

## 2. Scope and out of scope

In scope:

- New modules `frames.py`, `orbit3d.py`, `dynamics3d.py`, `guidance3d.py`,
  `phases/spatial.py`, `search_spatial.py`, `metrics_spatial.py`, `sim_spatial.py`.
- Config: `dynamics: spatial_3d` with `earth: {model: spherical}`; `site.longitude_deg`
  for display only.
- The generalised loss identity with the gravity row split into an along-up part and a
  lateral part.
- The release map at any latitude and azimuth; the track and the hold stay 1-DOF.
- Reporting generalisation in `compare.py`, `results_io.py`, `summary.py`, `plots.py` so
  a spatial run goes through the same pipeline (new writers; planar writers untouched).
- The planar pin test (S1.0), written and committed before any shared module is edited.
- The model-to-model record and its pre-registration (the expectation is committed with
  S1.0, before any file under src/ is edited; section 5.10 says what came before it).
- TODO.md KI-001, which this phase owns: a read-only audit that no loss integral or check
  reads the unwrapped `gamma_rel_rad` (step S1.6). The issue is then closed or re-owned.
- `docs/physics.md` updated in every step that touches equations, frames, events or loss
  accounting.

Out of scope (each has a home):

- Oblate Earth, J2, geodetic altitude: SP5.
- 6-DOF, attitude, gimbal: SP6.
- The 3-D scene and the offload re-check on S1: SP4.
- Inclination or plane targeting with yaw (S1b): deferred; see section 5.12.
- Tilted or curved tracks: README Phase 3 (TODO.md B-006, B-008). The force- and
  power-limited linear motor and the sealed shaft were built in SP7 on the 1-DOF track
  (B-005, D-SP7-24, D-SP7-26); SP3 adds no drive. The general tilted release form is
  written down in section 5.6 as the seam for it and is not built.
- Porting `PlanarPlanner` onto the shared model kit: deferred.
- Any change to a planar or 1-D number. None is allowed (section 5.1).
- Optimal control (README Phase 5); wind.

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-01: 3-D means true 3-D dynamics in three validated stages; this phase is S1. It
  also answers CLAUDE.md's "ask before expanding scope (6-DOF, 3-D Earth)".
- D-SP1-07: order of the program (settings and offload, planar findings, app, then 3-D),
  amended by D-SP1-18 (2026-10-04: SP7, the structural mass of the push load and a
  force-limited drive, runs after SP2 and before SP3) and confirmed at SP2's close by
  D-SP2-40 (SP7 next, then SP3 to SP6).
- D-SP1-08: one fresh session per phase; this file is the starting document.
- D-SP1-09: the offload is an `offload:` block and a post-pass, so no pre-registered file
  or budget id changes. The reuse requirement is not a numbered decision: it is step 5 of
  the approved plan and section 5.4 of the SP1 phase file (`OffloadProblem` is built from
  a problem factory against `RecordingProblem`), so the 3-D search context inherits the
  solver without change. It is used in SP4, but it constrains what `SpatialSearchContext`
  must satisfy here. SP7 added an optional vehicle transform to the solver (D-SP7-20) and
  left `RecordingProblem` as it was. Its structural transform reads a planar pad flight and
  flies a linear-motor push through a planar `SearchContext`, so it is not part of what
  `SpatialSearchContext` must satisfy (SP4's question).
- D-SP1-11 and D-SP1-12 concern S2 and S3 and are not acted on here.
- D-SP1-14 to D-SP1-16: the public repository; push after every step's tracker commit and
  at the close; the public face kept current at the close.
- D-SP7-27 (SP7's approved design): no field is added to any dataclass the 1-D golden dump
  reaches; tests/test_golden_dump_fields.py pins their field lists. The 1-D golden tier
  cannot be recaptured, so the pin binds SP3's edits too (the rule in section 5, risk 8 in
  section 10).
- From Phase 2 (legacy ids are assigned in TODO.md): the calibration miss of +14.3% is
  accepted and carries over unchanged; the planar flight step cap is 2 s and is kept for
  the 3-DOF model.

## 4. Entry criteria

1. SP7 is "done" on the program board. The planned order is SP1, SP2, SP7, then SP3
   (D-SP1-07, amended by D-SP1-18 and confirmed at SP2's close by D-SP2-40). SP3 needs only
   SP1 (board, "Dependency order"): it uses nothing from SP2's app or SP7's structure
   model, but its copy of `phases/planar.py` includes the edits of SP1 and SP7, and its
   inventory those of SP1, SP2 and SP7. Starting SP3 before a phase that is not done is a
   user decision logged in TODO.md.
   State at this check (d03367b, 2026-11-05): SP1 done (5007515) and SP2 done (3a1b243) on
   the board; SP7 in progress, steps 0 to S8 done, C1 and C2 open (SP7 phase file, section
   7). SP7's close sets the board, the SP7 phase file and TODO.md to "done (<date>, commit
   <hash>)" and writes the new handoff naming that commit, all before the Close SP7
   commit. The start checklist confirms the three, and this criterion fails if any is
   missing.
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3), subject "Close SP7: trackers, handoff,
   next phase file"; the closing commit is an ancestor of HEAD, and `git diff --stat
   <closing commit> HEAD` touches only docs/, TODO.md, CLAUDE.md, README.md, .gitignore and
   site/.
   State: at this check the tree was clean at d03367b; the demo runs' four summaries are
   committed (6940273). The start checklist confirms a clean tree, the subject and the
   ancestry.
3. Fast suite green (`uv run pytest -q -m "not slow"`); ruff clean; these pins pass: the
   exact 1-D golden tier (tests/test_golden_1d.py with tests/golden_1d_support.py), SP1's
   planar digest pin
   (`tests/test_config_planar.py::test_shipped_planar_resolved_dicts_match_the_pinned_digests`,
   the four Phase 2 planar experiments in tests/data/planar_pins/resolved_digests.json),
   the planar output capture
   (`tests/test_planar_pipeline.py::test_written_outputs_keep_the_captured_structure`,
   tests/data/planar_pins/output_capture.json) and the field lists of the dataclasses the
   1-D golden dump reaches (tests/test_golden_dump_fields.py, D-SP7-27). The pad and
   silo_cold payload capacities reproduce their recorded values within 0.002 kg (SP1 step 5
   gate; the slow `tests/test_silo_screening_record.py::test_recorded_payload_capacity_reproduces`,
   `PAYLOAD_TOL_KG` = 0.002): 26,054.3962 kg for the pad and 27,553.2271 kg for silo_cold,
   pinned at full precision in tests/data/silo_screening_2d_record.json
   (26054.396243494975 and 27553.227114190096 kg; git 7ad381f,
   results/silo_screening_2d/20260930T175743Z, copied from its metrics.json by SP1 step 1;
   the pad value equals tests/data/calibration_record.json, `amended_rerun`). The
   one-decimal figures 26,054.4 and 27,553.2 kg are not the reference.
   State at this check (d03367b): the last recorded counts are 2,217 fast and 2,271 full (54
   slow), all passing (SP7 step S7d's gate, cd14968; S8's gate ran the fast suite again,
   2,217); SP7's close records its full-suite count in the handoff (section 7). S7d's gate
   passed the fast tier under 32 burners and a disk writer (KI-090 and KI-091 closed; the
   SP7 file's S7d entry says what that does not show, and KI-051 stays open). A test that
   starts a subprocess can still fail beside heavy jobs (protocol section 11); re-run it
   alone before reading a failure as real.
4. SP1's offload solver exists and is written against `RecordingProblem` with a problem
   factory, not against `SearchContext` (design requirement on SP1). If it is not, that
   is logged as a known issue for SP4, not fixed here.
   State: confirmed at d03367b: `offload.ProblemFactory` (vehicle -> RecordingProblem,
   offload.py 97), `OffloadProblem` (168) with `from_factory` (193), and the planar factory
   `planar_problem_factory` (282; `sim.offload_problem_factory`, sim.py 2071). SP7 added
   an optional vehicle transform (`OffloadProblem.transform`, 184; D-SP7-20) and left
   `RecordingProblem` unchanged (in search.py it changed only the `PreludeFailure`
   docstring). The structural transform it carries is planar-bound: a linear-motor push is
   flown through a planar `SearchContext` (`sim.flown_push_trace`, 2388), and the envelope
   reads a planar pad Result (`sim.structure_pad_cases`, 2171, refuses any other at 2193).
   Whether S1 carries it is SP4's question (board, SP4 row).
5. Section 6 of this file has been re-checked at the current HEAD and its commit and date
   updated.
   State: done 2026-11-04 at 6cf0fd2 and re-validated 2026-11-05 at d03367b by SP7's close-out
   (the check line at the top of section 6), the first re-check since the file was written
   at 2eebcae. Since 2eebcae, SP1
   edited `assist/constant_accel.py`, `cli.py`, `compare.py`, `config.py`, `guidance.py`,
   `metrics_planar.py`, `phases/engine.py`, `phases/planar.py`, `phases/prelude.py`,
   `phases/vertical.py`, `plots.py`, `replay.py`, `results_io.py`, `search.py`, `sim.py`,
   `summary.py`, `units.py` and `vehicle.py` and added `offload.py`. SP2 edited `cli.py`,
   `config.py`, `plots.py`, `replay.py` and `summary.py` and added `app.py`, `appform.py`,
   `display.py`, `run_data.py`, `scene.py`, `video.py` and the templates `app.html` and
   `scene.html`. SP7 edited `phases/engine.py`, `phases/planar.py`, `phases/prelude.py`,
   `phases/trace.py`, `phases/vertical.py`, `dynamics.py`, `losses.py`, `metrics.py`,
   `metrics_planar.py`, `sim.py`, `offload.py`, `config.py`, `compare.py`, `results_io.py`,
   `summary.py`, `plots.py`, `replay.py`, `cli.py`, `vehicle.py`, `units.py`,
   `constants.py`, `atmosphere.py`, the assist package, `run_data.py`, `scene.py`, `app.py`,
   `appform.py`, `video.py`, the templates `app.html` and `scene.html` and one docstring in
   `search.py`, and added `structure.py` and `assist/linear_motor.py`. `guidance.py` and
   `orbit.py` are as SP1 left them. No file under src/ changed after 9fe125c (S7c). Section
   6 lists the corrected line numbers.

## 5. Design

The full design is in
[inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md)
(sections 0, S1, 5, 6, 7). This section keeps its content for S1. Plan mode confirms or
refines it against the code.

Three rules from CLAUDE.md govern the whole phase:

- Plan mode is required for anything touching equations of motion, frames, events,
  integrator settings or loss accounting, and `docs/physics.md` is updated in the same
  change. Every step of this phase does that.
- No planar or 1-D number may change. The pin test comes first (S1.0) and edits to shared
  modules are additive, with one limit (D-SP7-27): no field is added to a dataclass the
  1-D golden dump reaches, because that golden can never be recaptured.
  tests/test_golden_dump_fields.py pins their field lists: `losses.LossBudget`,
  `losses.AssistEnergyBudget`, `sim.Result`, `sim.RunResult`, `config.ResolvedRun`,
  `config.SweepPoint`, `compare.SensitivityRow`, `results_io.ExperimentResult` and
  `results_io.SweepResult`. So the lateral gravity part rides in a class built only on the
  spatial path, or in the spatial metrics, never as a `LossBudget` field.
  `losses.loss_budget` sums only the 1-D and planar J names and is reused for those rows.
- No physics feature is used in an experiment until its closed-form test passes. The
  model-to-model run (S1.8) is the first searched 3-D run used for a record and comes
  last. Searched 3-D runs also happen inside tests before it (S1.5 to S1.7), so the
  pre-registered expectation of section 5.10 is committed earlier, with S1.0, before any
  file under src/ is edited.

### 5.1 Approach

`search.py` and the two inner solves in `guidance.py` see only protocols and are reused
unchanged. The planner, the steering laws, five events, the metrics and the run assembly
are written new, as copies, so no planar number can move. The five events are the four of
section 6 (apex, turnaround, kick start, kick aligned) and the upward altitude crossing:
`engine.ev_altitude_up` finds the altitude rate by `_altitude_rate_index`, which knows only
`v_r_mps` and `v_mps` and raises ValueError on any other layout. The planar planner uses
it for SP1's ignition height and SP7's `shaft_exit`. SP7's `shaft_apex` and
`shaft_turnaround` are the apex and turnaround events renamed, so they come with them. The
coupling table with line numbers is in section 6.

The new `SpatialPlanner` is written against a small model kit (layout, rhs, kinematics,
law and event factories) so that S2 and S3 reuse it. The copy is taken from
`phases/planar.py` as it stands when SP3 starts. That file includes SP1's altitude ignition
event and ignition resolver and SP7's edits: the linear motor's release-referenced ignition
lit at the flown release (D-SP7-25) and the flight inside the shaft after a release below
the mouth, with the `shaft_exit`, `shaft_apex` and `shaft_turnaround` events, the shaft
floor (`FlightStart.shaft_floor_m`) and the `shaft_fallback` impact flag (D-SP7-51). Which
of SP7's additions the spatial planner carries is decided in Plan mode. `planar_prelude`
also sets `PreludeLayout.aerodynamic`, which words the early-release assumption line for a
flight model that evaluates the atmosphere, and the spatial model is one. The copy is not
taken from the file as it stood at 2eebcae (1,624 lines) or at SP7's start 22c62e9 (1,733
lines; 2,028 at d03367b).

Edits that touch validated code, all behaviour-preserving for 1-D and planar and guarded
by S1.0, the 1-D golden tier, SP1's planar pins (tests/data/planar_pins/), SP7's vented
pins (tests/data/vented_pins.json) and the golden-dump field pins
(tests/test_golden_dump_fields.py): the `sim.run` dispatch and the preflight's
`sim.run_ignition_specs` (`check_resolved` calls it for every run, and a spatial run would
take its 1-D branch), the `DynamicsKind` literal and its rules in `config.py` (today the
`offload:` and `structure:` blocks refuse every model but planar_2d, config.py 2533 and
2600), the model branches in `compare.py`, `results_io.py`, `summary.py` and `plots.py`,
and a `run_data.MODEL_COLUMNS` entry if a reader is to accept spatial runs. No new
dependency.

### 5.2 Module layout and config

| New file | Content |
|---|---|
| `src/launchsim/frames.py` | ECI/ECEF/local-frame transforms, site position, v_rel |
| `src/launchsim/orbit3d.py` | h vector, inclination, node, argument of latitude; a, e, r_p, r_a through the existing `orbit_elements` |
| `src/launchsim/dynamics3d.py` | state layout, scalar-float RHS, kinematics, observables |
| `src/launchsim/guidance3d.py` | rise, kick, gravity turn and stage-2 linear-tangent laws as 3-vectors |
| `src/launchsim/phases/spatial.py` | `SpatialPlanner`, release map, prelude layout; the five spatial events (here or in `phases/engine.py` beside the planar ones, decided in Plan mode) |
| `src/launchsim/search_spatial.py` | `SpatialSearchContext` (satisfies `RecordingProblem`) |
| `src/launchsim/metrics_spatial.py` | sampling, rows, felt loads, time-series and event columns |
| `src/launchsim/sim_spatial.py` | run assembly for a spatial run |

Config: `dynamics: spatial_3d` with `earth: {model: spherical | wgs84_j2}` (only
`spherical` is accepted in SP3; `wgs84_j2` arrives in SP5). The existing `guidance`,
`search`, `target_orbit` and `checks` blocks are reused as they are. `site.longitude_deg`
is added for display only. `dynamics: rigid_6dof` is SP6.

### 5.3 Frames and state

- Frame: ECI Cartesian, Z on the spin axis, coincident with ECEF at run clock t = 0.
  Cartesian has no pole or V = 0 singularity, takes J2 as one extra term, is what 6-DOF
  needs, and makes the reduction to the polar planar model an independent check.
- State: `[rx_m, ry_m, rz_m, vx_mps, vy_mps, vz_mps, m_kg, J_vac, J_grav, J_grav_lat,
  J_alt, J_drag, J_steer, J_bp]`. The J names need the `_mps` suffix in code:
  `engine.atol_for` rejects a state name without a known unit suffix.
- Local frame at r: u = r_hat (up), e_E = z x u / |z x u| (east), n = u x e_E (north).

### 5.4 Equations of motion

    r' = v
    v' = -mu r/|r|^3 + (T e - D v_rel_hat)/m
    m' = -T_vac/c

    v_rel = v - omega_E z x r          h = |r| - R_E          (p, rho, a) = atm(h)
    D = 0.5 rho V^2 C_D(M) A_ref       T = max(0, T_vac - p A_e)

e is the unit thrust direction from the steering law; V = |v_rel|. The RHS uses scalar
floats (no numpy cross products) for speed.

### 5.5 Generalised loss identity (also valid for S2 and S3)

Since v_rel . (omega x v_rel) = 0:

    dV/dt = v_rel_hat . (a_thrust + a_aero) + v_rel_hat . g_eff
    g_eff = g(r) - omega x (omega x r)          (holds for any g, including J2)

Rates:

    J_vac'   = T_vac/m
    J_drag'  = D/m
    J_steer' = (T/m)(1 - e . v_rel_hat)
    J_bp'    = (T_vac - T)/m
    J_grav'  = -g_eff . v_rel_hat

Split of the gravity row, with g_up = -g_eff . u (in S1: mu/r^2 - omega_E^2 r cos^2(lat))
and sin(gamma_rel) = v_rel_hat . u:

    J_grav'     = g_up sin(gamma_rel) + J_grav_lat'
    J_grav_lat' = -g_eff,horizontal . v_rel_hat
    J_alt'      = (g_up - g_ref) sin(gamma_rel)

- For V < 1e-9 m/s, v_rel_hat := u (the existing pad-start rule).
- Comparison rows against planar: planar gravity maps to J_grav total, with the lateral
  part shown beside it; the other rows map one to one.
- Expected row differences at 28.5 deg east: V_f differs by
  omega^2 r^2 (cos^2(lat_f) - cos^2(i))/(2V), about 0.2-0.4 m/s (design estimate), and
  the gravity + steering term absorbs it (the two rows trade against each other as
  gamma* moves; the findings read only the sum). That assumes i = lat. Under section
  5.7's full-vector law i is not lat, and about +1.9 m/s enters (omega h d(cos i) / V,
  by hand, at the replica's inclination; Q7, section 10).

### 5.6 Release map and track

- Site position: r_site(t) = (R_E + z) [cos(lat) cos(lon + omega_E t),
  cos(lat) sin(lon + omega_E t), sin(lat)].
- Vertical exit: v = s' u + omega x r, so v_rel = s' u exactly.
- General tilted form, written down as the seam for README Phase 3 and not built here:
  r = r_site + x_e d_az + z_e u, v = s' (cos(phi_t) d_az + sin(phi_t) u) + omega x r.
- The track and the hold stay 1-DOF, with g_track = mu/R_E^2 - omega_E^2 R_E cos^2(lat),
  independent of azimuth. Computing it as `g_eff_track(omega_E cos(lat))` makes it
  bit-equal to the planar value at azimuth 90 deg (9.7720917 m/s^2 at 28.5 deg).
- Neglected on the track and listed in the assumptions: Coriolis 2 omega_E s' cos(lat)
  (0.0098 m/s^2 at 77 m/s); the horizontal centrifugal term
  omega_E^2 R_E sin(lat) cos(lat) (0.0142 m/s^2 at 28.5 deg, a rail side load of
  0.0014 g); gravity variation over the stroke.

### 5.7 Guidance

- Launch plane: n_p = r_fs_hat x d_az at the flight start, fixed inertially;
  theta_hat = n_p x u, normalised. Pitch is the thrust elevation above local horizontal;
  yaw is the angle out of that plane.
- Rise: e = u. Kick: e = cos(delta) u + sin(delta) theta_hat.
- Kick end: (u_h cos(delta) - w sin(delta))/V crosses zero upward, with w = v_rel . u and
  u_h = v_rel . theta_hat.
- Gravity turn: e = v_rel_hat as a full vector. Open: Q7 (section 10) asks whether this
  stays, since on a review's replica this law leaves the launch plane (section 5.10).
- gamma_rel for the inner solve: atan2(w, s |v_rel,h|) with s = sign(v_rel . theta_hat).
  This keeps the planar range (-pi, pi], so the timeout and impact sentinels in
  `guidance.py` still work.
- Stage 2: plane normal frozen from r x v at stage-2 ignition;
  e = (s r_hat + theta_2)/sqrt(1 + s^2), s = a - b tau, zero yaw.
- Target: r = r_t, v_r = 0, E = -mu/(2 r_t); inclination is free and reported.
- `Handover.gamma_meco_rad` and `Stage2Result.{r_cut_m, v_r_cut_mps, tau_cut_s}` satisfy
  the existing protocols, so both inner solves and `run_search` run unchanged.

### 5.8 Orbit elements (`orbit3d.py`)

h = r x v; i = acos(h_z/|h|); node angle in the epoch frame (`raan_epoch_rad`, since the
run has no sidereal epoch); argument of latitude. a, e, r_p and r_a come from the existing
`orbit_elements(|r|, r_hat . v, |h|/|r|, mu)`.

### 5.9 Outputs

- New writers; the planar writers are untouched.
- Time-series columns are a superset of the planar names, so the 2-D scene of SP2 can read
  3-D runs once `run_data.MODEL_COLUMNS` gains a spatial entry and the scene's
  `check_run_dir` call accepts the model (at d03367b both take planar_2d only: run_data.py
  191-200 and 289-330, scene.py 497; the app gives other models no results panel, app.py
  3242 and 4813). Whether SP3 or SP4 adds the entry is decided in Plan mode.
  Added: ECI and ECEF position and velocity; lat, lon, alt; crossrange; heading;
  yaw; thrust unit vector (ECI); `J_grav_lat`; osculating a, e, i, `raan_epoch`, argument
  of latitude. Events carry the same columns.
- Summary rows add inclination, the gravity split and the model-to-model deltas.
- None of the new metric keys, summary rows or assumption lines may appear on 1-D or
  planar runs. The 1-D golden tier guards the 1-D outputs. For planar runs the guard is
  SP1's output capture (tests/data/planar_pins/output_capture.json and output_summary.md,
  compared by tests/test_planar_pipeline.py; captured in SP1 step 1, e2fb6ab, last
  recaptured in SP1 step 3, 83d66dd, unchanged by SP7): the files written, every
  metrics.json key path, the top-level keys of resolved_config.yaml and every CSV header
  of the fixed-guidance fast experiment (pad, silo_cold and silo_failed of
  silo_screening_2d) in every environment, and the sha256 of the normalised summary.md in
  the capture environment only. S1.0 checks it on the untouched tree (step table, S1.0).
  SP1's digest pin covers the resolved config dicts; SP7's vented pins
  (tests/data/vented_pins.json) cover a planar flown push and its track metrics.

### 5.10 Model-to-model record (S1.8)

- No tuning and no new fitted parameter, so no new calibration. The +14.3% miss of the
  gate vehicle carries over.
- Reference: the planar gate, pad baseline on `configs/vehicles/generic_f9_class_2d.yaml`,
  28.5 deg, azimuth 90 deg, 200 km circular, P* = 26,054.4 kg.
- Why a small difference is expected: at azimuth 90 deg the planar inertial dynamics are
  exact. The only difference is the air's out-of-plane velocity
  omega_E sin(lat) r sin(theta), about 5.7 m/s at MECO on the recorded pad, which enters
  at second order.
- Dated note, 2026-11-05 (SP7 step C1, physics review pass 2): that reason does not hold
  under section 5.7's law as written. The difference is second order in the crosswind, but
  the ratio that matters is crosswind / u_h at kick end, not crosswind / V at MECO.
  Section 5.6's horizontal centrifugal term (0.0142 m/s^2, in g_eff in flight) gives 0.25
  m/s of crosswind by the recorded pad's kick end (17.77 s), where u_h is only 3.69 m/s,
  so the heading of v_rel's horizontal part is already 3.92 deg off the plane (v_rel
  itself 0.19 deg). A gravity turn near vertical keeps that heading, and it reaches 6.1
  deg at MECO. A review's replica gives dP* = -20.2 kg on the pad, about four times the
  bound, and -0.001 kg with a zero-yaw gravity turn. These are a review's replica numbers,
  not a run and not a finding (no spatial_3d code exists); Q7 in section 10 holds them,
  their controls and the choice. The bound and its number stay: it is an expectation to
  test, on record since SP1 step T. But any later change to the law or to the bound
  follows this probe, so neither is a blind pre-registration; if neither changes, the
  expectation is still written after the replica's number. S1.0's entry in TODO.md must
  say which.
- **Pre-registered expectation: |dP*| < 5 kg.** It is written into TODO.md (and this
  file's session log) and committed in step S1.0, in the same commit as the planar pin and
  before any file under src/ is edited. That is before every searched run of the shipped
  3-D code, including those inside the tests of S1.5 to S1.7; Q7's replicas came first and
  are not that code. The expectation has also been on record in this file since the SP1
  step-T commit. A larger gap is treated as a bug until the loss rows explain it.
- The record goes to `docs/findings/M2M-3d-vs-planar.md`: both payloads, delta, (a, b),
  the loss rows side by side with the lateral gravity part, inclination, run times.
  Gravity and steering are read as their sum (section 5.5): on a review's replica, not a
  run, each row moves by more than 5 m/s inside the search's 0.5 kg payload tolerance with
  no physics behind it, and the sum by 0.17 m/s.
- The 5 kg bound is an expectation to test, not a target to tune toward. If the measured
  difference is outside it and the loss rows explain it, the note says so plainly and the
  bound is reported as missed.

### 5.11 Runtime (estimates from the design, to be measured at S1.2)

- Planar today, with the 2 s cap: about 12 microseconds per RHS call (build step 25; the
  cap adds RHS calls, not cost per call), 12.1-24.7 s per searched run (build step 26a: pad
  12.1 s, silo_cold 14.1 s, silo_cold_lag 24.7 s, 26.5 s on the reviewer's run; scaled to
  build step 25's machine speed silo_cold_lag takes about 33 s, already over the 30 s
  budget). The budget is the "One searched run" row of docs/physics.md, "Performance
  (measured)"; no test asserts it.
- S1: about 15 microseconds per RHS call, 12-18 s per searched run typical. The
  lag-startup case may reach 30-35 s against the 30 s budget the design refers to (recorded
  in docs/physics.md "Performance (measured)", not asserted; decide before S1.5 whether a
  test should hold it).
- The existing 2 s flight step cap is kept.

### 5.12 Deferred

- Inclination and plane targeting with yaw (S1b). It needs a 3x3 shooting or an azimuth
  outer solve, and the headline case (28.5 deg, due east) does not need it.
- Mean-element targets, wind, porting `PlanarPlanner` onto the shared kit.

Size estimate from the design: about 4,500 source lines, 3,000 test lines and 700 lines
of physics.md.

## 6. Inventory of the code this phase touches

Checked at commit d03367b on 2026-11-05 by SP7's close (SESSION_PROTOCOL.md section 7,
item 8), against the tree as SP1, SP2 and SP7 left it. The line-by-line check was made at
6cf0fd2 on 2026-11-04; no file under src/ changed between the two commits. First written
at 2eebcae on 2026-09-30 from the design's numbers. SP3's step 0 re-checks it at its start
commit. Paths are relative to the repository root.

### Coupling to the planar layout

| Module | Reusable as is | Bound to the planar layout |
|---|---|---|
| `src/launchsim/search.py` | `SearchProblem` (470) and `RecordingProblem` (499) protocols; `payload_root` (864), `optimise_gamma` (1394), `final_verify` (1627), `run_search` (1781): they see only the protocols | `SearchContext` (512-770); test-only `joint_root_crosscheck` (1881); `Stage2Result` and `KickPoint` appear only as annotations |
| `src/launchsim/offload.py` | `ProblemFactory` (97), `OffloadProblem` (168; its SP7 `transform` is optional), `solve_offload` (499): they see only `RecordingProblem` | `planar_problem_factory` (282) wraps a `SearchContext`; the spatial twin is SP4's |
| `src/launchsim/guidance.py` | `solve_delta_for_gamma` (370), `solve_ltg` (656), `GuidanceSpec` (253), `LtgSettings` (520), the guess ladder (`ltg_physics_guess` 605, `ltg_guess_ladder` 619), `GuidanceFailure` (96), the sentinels (65-83) | All steering laws (`Radial` 120, `FixedTilt` 139, `AlongVrel` 166, `LinearTangent` 184, `LinearTangentEps` 217): they return `(e_r, e_theta)` from `PlanarKinematics` |
| `src/launchsim/phases/engine.py` | `integrate_phase` (436), `ev_ground(model, z_ground_m)` (809), `ev_propellant(m_dry_stack_kg, layout)` (622), `ev_time` (959) | `ev_radial_apex` (887) and `ev_radial_turnaround` (903) need `v_r_mps`; `ev_kick_start` (914), `ev_kick_aligned` (938); `ev_altitude_up` (843; SP1's ignition height and SP7's shaft exit) takes its rate from `_altitude_rate_index` (834), which accepts only `v_r_mps` or `v_mps`; `atol_for` (294, suffix table 91-97) rejects unknown suffixes |
| `src/launchsim/phases/prelude.py` | Hold (`hold_until_liftoff` 733) and `fly_track` (1154) through `PreludeLayout` (846) and the `g_eff_mps2` and `p_amb_pa` arguments; every drive goes through them, SP7's linear motor and sealed shaft included. `PreludeLayout.aerodynamic` (862, SP7) defaults to False, the 1-D wording; `planar_prelude` sets it True | Nothing in the code (whether the hold rows and the logged track events are reused is Q5); the text of `ramp_start_assumption` (511) names planar_2d |
| `src/launchsim/phases/planar.py` | The state-machine structure only (`PlanarPlanner` 795-2028) | No hooks: module-level `PLANAR_LAYOUT` indices (215-220), `rhs_planar`, `PlanarEnvironment` (302) throughout; `PlanarView` (227), `map_release_planar` (428), `planar_prelude` (459), `map_staging_planar` (484), `map_fairing_planar` (508), `ev_energy_cutoff` (526), `ev_fmh` (547), `ev_mass_floor` (566), `FlightStart` (587), `KickPoint` (630), `Handover` (649), `Stage2Result` (683); SP7's shaft events `SHAFT_EXIT_EVENT`, `SHAFT_APEX_EVENT` and `SHAFT_TURNAROUND_EVENT` (140-168), listed by `PlanarPlanner._burn` (1655) for a burn that starts below the ground |
| `src/launchsim/dynamics.py` | `StateLayout` (148), `DynamicsModel` protocol (189), `thrust_terms` (124), `g_eff_track` (114) | `PLANAR_STATE_NAMES` (551), `PlanarKinematics` (625), `SteeringLaw` (664), `PlanarParams` (688), `planar_forces` (760), `rhs_planar` (809), `PlanarDynamics2D` (904) |
| `src/launchsim/losses.py` | `loss_budget(phases, layout, speed)` (375), `rocket_equation_closure(trace, vehicle, layout)` (489) | `pointwise_dVdt` (424) |
| `src/launchsim/metrics_planar.py` | `scan_peak` (189), `max_q` (268), `unwrap_rad` (369), `loss_items` (849), `search_metrics` (1197), `closure_metrics` (1395): about a third of the file | Sampling, rows, felt loads; the column sets `PLANAR_TIMESERIES_COLUMNS` (350) and `PLANAR_EVENT_COLUMNS` (390); `planar_track_metrics` (980) |
| `src/launchsim/orbit.py` | `TargetOrbit` (20), `orbit_elements` (95) | Nothing (takes scalars) |
| `sim.py`, `compare.py`, `results_io.py`, `summary.py`, `plots.py`, `cli.py`, `run_data.py` | Structure | Branches on `== PLANAR_2D` (listed below); `compare.MatchedRun` (595) carries `omega_p_rads` (613); `PlanarDynamics2D` is built at 639, 829 and 1470 (SP1's `_screening_offload`); 958 passes `view.omega_p_rads` |

### Branch sites on the dynamics kind (to become a model set in S1.6 and S1.7)

- `src/launchsim/config.py`: `DynamicsKind = Literal["vertical_1d", "planar_2d"]` (217);
  `RunConfig._dynamics_rules` (1618) with checks at 1610, 1619, 1663; `ExperimentConfig`
  checks at 2380, 2400, 2418, 2444, 2451, and at 2469 (SP2: the exploratory label), 2533
  (SP1: `offload:` is a planar_2d block) and 2600 (SP7: `structure:` is a planar_2d block);
  `resolve_run` (3126) at 3141, 3146; `PlanarSiteConfig` (620-637), which requires every
  site field explicitly.
- `src/launchsim/sim.py`: `run` (1043), dispatch at 1054; `run_ignition_specs` (1079),
  dispatch at 1085 (SP1; `check_resolved` and `structure_block_needs_hold` call it);
  `run_planar` (1852); `planar_setup` (1375); `search_context` (1401); `simulate_planar`
  (1529); `matched_run` (1939). SP7's structure path stays planar: `structure_pad_cases`
  (2171, refusal at 2193) and `structure_flight_cases` (3545, refusal at 3569) refuse a
  non-planar Result, and `StructureTransform` (2771) is built only from a `structure:`
  block.
- `src/launchsim/compare.py`: 403, 456, 518-524.
- `src/launchsim/results_io.py`: 639, 704, 730, 788, 1006, 2521, 2589, 2679, 2778.
- `src/launchsim/summary.py`: 821. `src/launchsim/plots.py`: 168.
  `src/launchsim/cli.py`: 466. `src/launchsim/run_data.py` (SP2): `check_run_dir` (289,
  refusal at 324) defaults to `models=(PLANAR_2D,)` and is called that way by the animation
  (plots.py 2029), the replay (replay.py 290) and the scene (scene.py 497); `MODEL_COLUMNS`
  (191) has only the planar entry; `read_series_frame` (652) and `read_series` (677)
  default to `model=PLANAR_2D`. So the animation, the replay and the scene refuse anything
  but planar; whether they accept spatial runs is decided in SP4. The app's run browser
  lists a run of another model as "not planar" and gives it no results panel (app.py 3242,
  4813).

### Tests that guard or serve as models

- `tests/test_golden_1d.py` with `tests/golden_1d_support.py`: every 1-D output pinned.
- `tests/test_golden_planar.py` does not exist at d03367b; S1.0 creates it. SP1 step 1
  added two planar pins (`tests/planar_pin_support.py`, data in `tests/data/planar_pins/`):
  the resolved-dict digests (tests/test_config_planar.py) and an output capture of a
  fixed-guidance fast experiment (files written, metrics.json key paths, CSV headers and
  the normalised summary.md digest; tests/test_planar_pipeline.py), last recaptured by SP1
  step 3. SP1 step 5 reproduces the two payload capacities
  (`tests/test_silo_screening_record.py`, `tests/data/silo_screening_2d_record.json`). SP7
  step S5 added byte pins of vented pushes, one planar flown push among them
  (`tests/vented_pins_support.py`, `tests/test_sealed_shaft.py`). S1.0 extends these, it
  does not duplicate them.
- `tests/test_config_planar.py`: `PLANAR_EXPERIMENTS` (78) and
  `test_every_shipped_planar_experiment_is_checked` (911). The test collects only
  `dynamics: planar_2d` files, so it does not see a spatial experiment file; a new spatial
  file needs a parallel spatial list with its own check (section 10).
- Models for the new tests: `tests/test_planar_dynamics.py`, `test_planar_reductions.py`,
  `test_orbit.py`, `test_release_planar.py`, `test_loss_identity_2d.py`,
  `test_closure.py`, `test_convergence_2d.py`, `test_planar_events.py`,
  `test_payload_search.py`, `test_search.py`, `test_planar_pipeline.py`.
- `tests/test_calibration.py` (slow): P* regression against
  `tests/data/calibration_record.json`.

### Critical files (read in full before planning)

`src/launchsim/phases/planar.py`, `src/launchsim/dynamics.py`, `src/launchsim/search.py`,
`src/launchsim/guidance.py`, `src/launchsim/sim.py`.

### docs/physics.md sections to extend (heading lines at d03367b)

Frames and datum (337), Planar ascent state and equations of motion (498), 2-D loss
identity (652), Planar reductions (754), Orbital elements and the circular target (817),
Planar release map (844), Stage-1 guidance and events (951), Stage 2 and insertion
(1464), Event rules (4095), Experiment schema (7482), Assumptions (10587),
Test-to-equation map (11604). The 3-D material goes in new sections beside these; the
planar text is not rewritten.

## 7. Steps

Each step runs the loop of SESSION_PROTOCOL.md section 4: implementer, adversarial
reviewers (physics or numerics skeptic, CLAUDE.md compliance; an honesty auditor on S1.7's
summary rows and S1.8's note), up to two fix rounds, independent gate, commit, tracker
update, push and the Pages check. Standing gate on every code step: fast suite green, ruff
clean, the exact 1-D golden tier (LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1, 0 skipped), SP1's
planar digest pin and output capture, the golden-dumped field lists
(tests/test_golden_dump_fields.py), templates/replay.html's sha256, the structure files'
and the vented byte pins, no shipped experiment, vehicle or structure file edited, and the
S1.0 pin passing; the full suite (which also runs the slow pins: the two P* and SP1's
headline 41,262.908 kg within 0.002 kg) after every step from S1.2 to S1.7 (all are
physics-core).
The payload-capacity part of the S1.0 pin runs full searches and is slow-marked, so the
fast suite does not run it: run it by name
(`uv run pytest -q tests/test_golden_planar.py`) at every step's gate.
`docs/physics.md` is updated in every step. Test file names are proposals.

Tolerances. Those in the table that the design input does not give are proposals of this
file, confirmed or changed in step 0: 1e-12 for the algebraic reductions (the steering
laws and the kick event of S1.3); 1e-8 relative for the
vacuum-coast energy (the test is on CLAUDE.md's validation list, which gives no number for
it; tests/test_coast.py holds the 1-D coast to 1e-10 relative); 1e-12 relative for g_up
against g_ref
in the hold-consistency test; `checks.closure_tol_mps` (1e-5 m/s) for the rocket-equation
closure; rtol 1e-12 for S1.2's orbit gate (CLAUDE.md's upper limit of 1e-9 does not pass it
with no step cap: on a review's replica, not a run, the eccentricity vector drifts 7.5e-8
at rtol 1e-9 and 1.1e-10 at 1e-12, and a 2 s cap passes at every rtol, at 32,000 steps),
and that gate's reading: each component of h against |h| and of the eccentricity vector
against e. Read against its own value a component can be zero (the probe's state, perigee
and node on x, has h_x = 0 and e_y = e_z = 0), and on a generic orientation (Omega 0.7,
omega 1.1 rad) e_x drifts 4.4e-10 of itself against 1.1e-10 of e at rtol 1e-12 on the same
replica. A 1e-12 comparison of quantities that can cancel (the rows and the pointwise
dV/dt of S1.2, the kick event of S1.3) reads against the quantity's scale, for a row its
largest magnitude over the seeded states, not against its value at that state; the design
input gives S1.2's 1e-12 and this file the kick event's; neither gives this reading, which
step 0 confirms too. Read against the value, a
review's replica of the 500 states (the probes: KI-102) reaches 2.25e-12 on dv_theta/dt at
a row value of 0.065 m/s^2 (1.5e-13 absolute), on rounding alone, so a fixed seed could
pass or fail on the draw; against each row's scale the same states reach 1.0e-13.
S1.4's 28.5 deg vacuum line keeps the design input's 1e-9 and says what it compares; that
reading is also a proposal step 0 confirms. In-plane laws fix the steering, not the
events: a kick started on V = |v_rel| (section 5.4, the copied `ev_kick_start`) counts the
crosswind even on an exactly in-plane flight, so on a review's replica, not a run, the
kick starts 3.7e-5 s early, the velocity moves by 4.8e-6 relative at MECO and the cutoff
mass by 2.2e-6, quadratic in the crosswind and zero at the equator; a kick on the in-plane
speed leaves r, v_r, v_theta and m within 1.1e-13 relative on the same replica. The J rows
are not compared, because they carry the sideslip (J_steer at MECO 0.0353 against 0.0263
m/s). Plan mode decides whether the shipped spatial trigger is |v_rel| or the in-plane
speed; a kick at a fixed time in the test is the alternative.
S1.4's equatorial line keeps the design input's 1e-9 and 1e-8 s, but flies them at a
tightened setting on a smooth test air, not at the design's rtol 1e-12 on the shipped
air, and both S1.4 lines read v_r against the inertial speed |v|; step 0 confirms all
three. The figures below are reviews' replicas, not runs (the probes: KI-102). With the
air on, on a Cartesian replica flown against the shipped `PlanarPlanner`, rtol 1e-12 at
`atol_for`'s values leaves the worst J row (J_drag) at 3.4e-9 to 2.1e-8 relative and the
fairing time at 5.7e-8 to 2.1e-7 s over five draws of first step and step cap on the pad.
No model difference is behind it: the shipped planner alone moves 2.2e-8 on J_drag
between rtol 1e-12 and 3e-14, and in vacuum the same settings stay near 1e-13. rtol alone
does not clear it, and atol alone, at rtol 1e-12 on one draw, passes at three of the four
scales tried and fails at the fourth. rtol 1e-13 with `atol_scale` 1e-3 (the
`IntegratorSettings` factor on `atol_for`'s values, with no YAML key) reaches 8.0e-11 and
3.0e-10 s on those five draws, but no setting tried clears the shipped air and drag with
margin: the gap enters in one accepted step across a kink of the right-hand side (an ICAO
layer base at 47, 51 or 71 km, a C_D knot near Mach 1, or, in silo_cold's startup ramp,
KI-049's unsplit thrust clamp), where that step falls is the draw, and docs/physics.md
("Noise floor", "Planar step cap") calls what is left a heavy-tailed jitter. At that
setting about one pad draw in twelve still fails (16 of 200 on the J rows and 14 of 200 on
the fairing time, worst 4.9e-8 and 4.3e-8 s over 360 draws; 124 and 120 of 1,500 at the
shipped 2 s cap, worst 6.6e-8 and 1.2e-7 s); silo_cold fails two of the same five draws
(J_drag 2.5e-9 and 2.8e-9), 8 of 200, and 142 of 1,500 on the J rows and 145 on the
fairing time; and the shipped planner, varying only its own first step against a tight
reference, misses 1e-9 in 5 of 60 pad flights and 7 of 60 of silo_cold's. rtol 3e-14 with
`atol_scale` 1e-5, near scipy's floor, passes the pad's 300 draws over two seeds and
silo_cold's 200 on the second (worst 5.2e-10 on the J rows and 4.8e-9 s on the fairing
time, a margin of about 2) but fails silo_cold 2 of 100 on the first. At rtol 1e-13 with
`atol_scale` 1e-3, a 0.25 s step cap passes 100 draws of each (a margin of 1.7 on the
pad's J rows), and a 0.05 s cap passes the pad's 100 and fails silo_cold's fairing time
once in 100 (2.1e-8 s).
The smooth test air, given to both models (`PlanarEnvironment`'s atmosphere and the
vehicle's `DragModel` are arguments), is the one the replicas flew: an exponential
pressure and density with a 7.5 km scale height (101,325 Pa and 1.225 kg/m^3 at the
datum), a constant speed of sound (320 m/s) and a constant C_D (0.4). Its pressure is part
of it. With the same density and speed of sound, the ICAO pressure, C1 at the layer bases,
fails the pad 1 of 400 draws on the J rows and 8 of 400 on the fairing time (worst 1.2e-9
and 2.3e-8 s). tests/conftest.py's `exp_atmosphere` has no pressure (p = 0), which zeroes
J_bp on both models and removes KI-049's clamp; no replica flew that air. Step 0 chooses.
On the replicas' smooth air, at that setting, the pad fails 0 of 200 draws (J rows within
7.3e-11, the fairing time within 1.4e-10 s by linearisation; with the replica's own event
detection 0 of 40, J rows within 4.3e-11 and every event time within 9.3e-11 s) and 0 of
1,500 at the shipped cap (states 3.7e-13, J rows 8.4e-11, fairing time 1.4e-10 s).
silo_hot_full, at full thrust through the push and so with no clamp crossing after
release, fails 0 of 1,500 (states 1.3e-13, J rows 2.7e-11, fairing time 6.4e-11 s; flown
on its recorded payload, delta and (a, b) from results/silo_screening_2d/20260930T175743Z,
whose metrics.json is not in git, so step 0 decides whether the test carries those values
or S1.0's pin adds silo_hot_full). So the 1e-9 and 1e-8 s line flies the pad and
silo_hot_full there, the release map included. silo_cold, lit after release, fails it on
that air: 0 of pass 5's 200 (worst 4.2e-9 s), but 10 of 1,500 over 1e-8 s on the fairing
time (worst 1.5e-6 s), 4 on the J rows and 2 on the states. Its startup ramp keeps
KI-049's clamp: pass 5 traced two of its three worst draws on that air (3.8e-9 and
2.4e-9 s) to the one step across it, and saw the worst's gap grow near MECO without
tracing where it entered; the 1,500-draw tail was not traced.
The same setting then flies the pad and silo_cold on the shipped air and drag, read at
1e-8 on the states, 1e-6 on the J rows and 1e-5 s on the event times, which keeps the
altitude and Mach wiring, silo_cold's release map and its lit-after-release ramp under
test. Over 1,500 draws at the shipped cap the worst are 5.1e-10, 6.6e-8 and 1.2e-7 s on
the pad, and 4.0e-9, 7.1e-8 and 1.2e-6 s on silo_cold. The event time binds: the fairing
event is the log of 0.5 rho V^3 over its limit crossing zero near 110 km, so on silo_cold
it moves 1.2e-6 s per mm of altitude and 7.6e-6 s per mm/s of speed, and 1e-6 s asks for
0.8 mm (1.3e-10 of r) where the state reading allows 65 mm. On silo_cold's worst draw one
accepted 2.9 ms step across KI-049's clamp, 0.15 s after ignition, puts 3.6e-7 m/s into
v_r (every other step of the ramp under 5e-11 m/s), the near-vertical gravity turn carries
it about 35 times larger to MECO, and the fairing time moves 1.2e-6 s (1 of 1,500 draws
over 1e-6 s, 3 over 1e-7 s); hence 1e-5 s. The same draw gives silo_cold's worst state,
4.0e-9, a margin of 2.5. Those event times are the fairing time alone, by linearisation
about the planner's events: no event detection was flown on silo_cold, and on the pad,
where it was (65 draws on the shipped air, 40 on the smooth), the fairing time was the
worst event in every draw but one. Step 0 sizes silo_cold's event-time reading with every
event detected. The 28.5 deg line, in vacuum, holds at the same setting. v_r reads against
|v| because on a converged (a, b) it is the shooting's residual at cutoff: on that replica
1.9e-6 m/s with a gap of 1.35e-6 m/s, 0.72 of the value and 1.7e-10 of |v|, and still
0.12 of the value at rtol 1e-12 with `atol_scale` 1e-3 and 3.7e-3 at S1.4's setting, so no
integrator setting passes a reading against the value.
The S1.0 pin compares the two payload capacities within 0.002 kg of their recorded values
(the tolerance SP1 uses for the same two numbers), delta, (a, b), the loss rows and the
cutoff state within 1e-9 relative, and the key lists, column lists and the summary digest
exactly. Its v_r needs no such reading: the pin compares the planar code with itself, and
the pad's `insertion_v_r_mps`, about -1.1e-4 m/s, is the same double in the five recorded
directories from 2026-09-30 to 2026-11-03 (silo_cold's in four), and in the demo re-runs
and the app's exploratory runs, which no finding cites. So 1e-9 of that value,
about 1.1e-13 m/s, holds while the planar arithmetic is unchanged, and that number trips
first if it moves.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| 0 | Session start: entry criteria, inventory re-check, Plan mode, open questions of section 10 put to the user | this file, TODO.md | fast suite | User approves the plan | [ ] | |
| S1.0 | Planar pin, test only: gate pad and silo_cold P*, delta, (a, b), loss rows, cutoff state; and the planar written outputs captured on the untouched tree for pad and silo_cold of a small planar experiment (metrics.json key list, time-series and event column lists, sha256 of summary.md without the lines that change from run to run). SP1 step 1 added such a capture: tests/data/planar_pins/output_capture.json and output_summary.md, for pad, silo_cold and silo_failed of the fast experiment of tests/test_planar_pipeline.py, checked there. It was last recaptured at SP1 step 3 (83d66dd) and is unchanged since. S1.0 checks that it passes on the untouched tree; whether S1.0 reuses it or adds its own capture beside it is decided in Plan mode. The model-to-model expectation (section 5.10) is written into TODO.md in the same commit, with the gravity-turn law Q7 settled and a line that Q7's replicas came first (section 5.10's dated note) | `tests/test_golden_planar.py`, TODO.md | the pin itself | Passes on the untouched tree; pin and expectation committed before any file under src/ is edited | [ ] | |
| S1.1 | Frames and orbit elements | `frames.py`, `orbit3d.py` | Element round trip at 1e-12; v_rel against a finite-differenced ECEF position; pad release speed 465.10 m/s at the equator and 465.10 cos(lat) at latitude (408.74 m/s at 28.5 deg), due east; vacuum inclination closed form cos i = cos(lat) sin(beta_inertial) | All listed tests | [ ] | |
| S1.2 | Equations of motion (scalar-float RHS); measure the RHS cost | `dynamics3d.py` | Inclined e = 0.3 orbit, 10 revs, rtol 1e-12: energy, each component of h against abs(h) and of the eccentricity vector against e drift < 1e-8, period 2 pi sqrt(a^3/mu); 500 seeded states: rows equal `rhs_planar` after transformation on the equator at 1e-12 of each row's scale, and pointwise dV/dt closes at 1e-12 of its scale; vacuum coast energy conserved to 1e-8 relative | All listed tests; RHS time per call recorded in the session log | [ ] | |
| S1.3 | Steering laws and the five events (apex, turnaround, kick start, kick aligned, altitude up) | `guidance3d.py`, `phases/spatial.py` (events) | Laws reduce to the planar tuples at 1e-12; the kick event equals the planar function at 1e-12 of its scale | All listed tests | [ ] | |
| S1.4 | Planner, release map, prelude layout | `phases/spatial.py` | Hold consistency: a point released at rest accelerates at g_eff, whose up-component equals the prelude's g_ref to 1e-12 relative. Equatorial east, the pad and silo_hot_full, each at fixed (delta, a, b), rtol 1e-13 and `atol_scale` 1e-3 on both models, on section 7's smooth test air (its pressure included) and constant C_D: same event sequence as `PlanarPlanner`; r, v_r, v_theta, m and all J within 1e-9 relative at MECO and cutoff (v_r against abs(v)); event times within 1e-8 s; abs(z) < 1e-6 m. The same settings on the shipped air and drag, the pad and silo_cold, each at fixed (delta, a, b): same event sequence; r, v_r, v_theta and m within 1e-8 relative (v_r against abs(v)) and all J within 1e-6 relative at MECO and cutoff; event times within 1e-5 s (silo_cold's sized on its fairing time alone; step 0 sizes it with every event detected); abs(z) < 1e-6 m. 28.5 deg, azimuth 90 deg, vacuum, in-plane laws only, the kick started on the in-plane speed sqrt(w^2 + u_h^2), the same settings: r, v_r, v_theta and m equal planar at 1e-9 at MECO and cutoff (v_r against abs(v)), and i = 28.5 deg at 1e-12 | All listed tests | [ ] | |
| S1.5 | Search context | `search_spatial.py` | Slow: equatorial-east P* within 1 kg of planar; gamma_MECO(delta) monotone scan | All listed tests; `search.py` and the inner solves unchanged (diff check) | [ ] | |
| S1.6 | Metrics, run assembly, dispatch in `sim.run` and in `sim.run_ignition_specs` (the preflight), config literal and `earth` block, `site.longitude_deg` | `metrics_spatial.py`, `sim_spatial.py`, `sim.py`, `config.py` | Loss identity < 1e-5 m/s at 28.5/90 and at 45/45 (lat/az, deg); rocket-equation closure within `checks.closure_tol_mps` (1e-5 m/s); convergence < 0.1% under 10x tighter tolerances; schema refusals (`wgs84_j2` and `rigid_6dof` not yet available). KI-001: read-only audit that no loss integral or check, planar or spatial, reads the unwrapped `gamma_rel_rad`; close the issue in TODO.md or re-own it | All listed tests; resolved dicts of the shipped planar and 1-D experiments unchanged (SP1's digest pin covers four of the nine planar files, SP7's offload-start digests cover the starts of SP1's two offload files, and the 1-D golden covers the 1-D file; how the rest are checked is settled in Plan mode); KI-001 closed or re-owned | [ ] | |
| S1.7 | Reporting generalisation: a model set instead of `== PLANAR_2D`; `MatchedRun` takes layout and speed; new writers | `compare.py`, `results_io.py`, `summary.py`, `plots.py`, `cli.py` | Pipeline test on a small spatial run: required metrics present, summary rows (inclination, gravity split) | The S1.0 pin passes, its written-output part exactly (planar metrics.json keys, time-series and event columns and the summary digest byte-identical), and the 1-D golden is byte-identical; a spatial run from the CLI writes a complete results directory | [ ] | |
| S1.8 | Model-to-model record: experiment file committed, run from the clean commit, findings note with honesty review. The expectation was committed in S1.0 | `experiments/` (new spatial file), `docs/findings/M2M-3d-vs-planar.md`, TODO.md | `tests/test_config_planar.py` or its spatial twin lists the new file | The expectation commit (S1.0) precedes the first commit that adds `search_spatial.py`, and so every searched 3-D run (git log); no `bug_suspect`; difference under 5 kg, or explained by the loss rows and reported as a miss | [ ] | |
| C | Close SP3: exit-criteria gate, demo recorded, close-out question (which phase runs next), CLAUDE.md layout and conventions (spatial frame), README status, TODO.md, the public face (landing page, deck and PDF, manual; the gallery where a page can show the phase's runs: `animate`, `replay` and `scene` take planar_2d runs only), the next phase file fact-checked (SP4 in the planned order), handoff and prompt, memory, cold read, push and Pages | docs/, site/, docs/manual/, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit; push and the Pages deployment green | [ ] | |

## 8. Exit criteria

1. `tests/test_golden_planar.py` was committed before the first commit that edits a file
   under src/ in this phase (checked in git log) and passes at the closing commit, with
   the exact 1-D golden tier, SP1's planar digest pin and output capture, the golden-dumped
   field lists, replay.html's sha256 and SP1's and SP7's slow pins (the two P* and the
   headline 41,262.908 kg, each within 0.002 kg) unchanged. The pin covers the solver
   numbers (pad and silo_cold P*, delta, (a, b), loss rows, cutoff state) and the planar
   written outputs (metrics.json key lists, time-series and event column lists, the
   summary digest); the written outputs are byte-identical at the closing commit.
2. Frames and elements: the S1.1 tests pass, including 465.10 m/s at the equator and
   408.74 m/s at 28.5 deg.
3. Dynamics: the inclined e = 0.3 orbit holds energy, each component of h against |h| and
   of the eccentricity vector against e to < 1e-8 relative over 10 revolutions at rtol
   1e-12; the 500-state comparison with `rhs_planar` passes at 1e-12 of each row's scale
   (section 7, Tolerances); the vacuum coast conserves energy.
4. Guidance and events reduce to the planar tuples and the planar kick event (section 7,
   Tolerances).
5. Planner: at S1.4's integrator settings, the equatorial-east pad and silo_hot_full runs
   on S1.4's smooth test air match `PlanarPlanner` (same event sequence, states and J rows
   within 1e-9 relative at MECO and cutoff with v_r against |v|, event times within
   1e-8 s, |z| < 1e-6 m), and the equatorial-east pad and silo_cold runs on the shipped
   air and drag match it at S1.4's readings (same event sequence, states within 1e-8
   relative with v_r against |v| and J rows within 1e-6 relative at MECO and cutoff, event
   times within 1e-5 s, |z| < 1e-6 m); the 28.5 deg vacuum in-plane run, the kick started
   on the in-plane speed, matches planar's r, v_r, v_theta and m at 1e-9 at MECO and
   cutoff with v_r against |v|, and i = 28.5 deg at 1e-12 (section 7, Tolerances); the
   hold-consistency test passes.
6. Search: equatorial-east P* is within 1 kg of the planar value; the gamma_MECO(delta)
   scan is monotone. `search.py`'s public search functions and the two inner solves in
   `guidance.py` are unchanged (diff against the SP3 start commit).
7. The loss identity closes to < 1e-5 m/s at 28.5/90 and at 45/45; the rocket-equation
   closure passes; tightening tolerances 10x moves payload and margins by < 0.1%.
8. `uv run python -m launchsim run <spatial experiment>` writes a results directory with
   the column set of section 5.9.
9. Model-to-model record: the expectation |dP*| < 5 kg is in TODO.md in a commit that
   precedes the first commit adding `search_spatial.py` (git log), and so every searched
   3-D run; `docs/findings/M2M-3d-vs-planar.md` exists and passed the honesty
   review; the run has no `bug_suspect`; the difference is under 5 kg, or is explained by
   the loss rows and the miss is accepted by the user and logged as a decision.
10. The measured RHS cost and searched-run time are recorded (session log and
    docs/physics.md), next to the estimates of section 5.11.
11. Full suite green, ruff clean; docs/physics.md has the 3-D frames, equations, loss
    identity, release map, guidance, events and assumptions; no new dependency.
12. Demo recorded under docs/demos/SP3/; the close-out question put to the user and
    logged; the public face refreshed (landing page, deck and PDF, manual, and the gallery
    where it can show the phase's runs), the site built with no broken link, main pushed
    and the Pages deployment green; the next phase file (SP4 in the planned order)
    fact-checked; handoff, prompt and memory written; cold read done.

## 9. Demo script

Output goes to docs/demos/SP3/ (text captures and a short README with the commit).

    uv run pytest -q -m "not slow"
    LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1 uv run pytest -q tests/test_golden_planar.py tests/test_golden_1d.py
    uv run pytest -q <the new 3-D test files, by path>
    uv run python -m launchsim run experiments/<model-to-model spatial file>.yaml

Look at:

- the test counts, and the pin and golden tests passing;
- the results directory of the 3-D run: `summary.md` (payload capacity, inclination, the
  gravity row with its lateral part, the identity line), `timeseries.csv` with the ECI,
  ECEF, lat/lon/alt and thrust-direction columns;
- `docs/findings/M2M-3d-vs-planar.md`: 3-D against 26,054.4 kg, the expectation written
  before the run, the loss rows side by side.

The exact file and test names are filled in by the session. Select the 3-D tests by path:
a `-k` expression with "frames" also selects tests of test_animate.py and test_video.py.
The golden line is Git Bash syntax; in PowerShell set
`$env:LAUNCHSIM_REQUIRE_EXACT_GOLDEN = "1"` first.

## 10. Risks and open questions

Risks (from the design, with mitigations):

1. Shared-module edits move planar numbers. Mitigation: S1.0 first; additive edits only;
   the standing gate on every step.
2. The Cartesian RHS is slow. Mitigation: scalar floats; measure at S1.2 before building
   the planner.
3. Sign and monotonicity of gamma_MECO(delta). Mitigation: the signed definition of
   section 5.7 plus the scan test of S1.5.
4. A thrust-direction step of about 3.4e-3 rad at kick end, from the crosswind. It is
   documented in the assumptions; in S3 it becomes a small step command. Dated note,
   2026-11-05 (SP7 step C1, physics review pass 2; a review's replica, not a run): the
   step is the small part. The same crosswind sets a heading the gravity turn keeps, so
   under section 5.7's law the vehicle leaves the launch plane (-255.6 m/s out of the
   plane and -10.2 km at the pad's MECO, inclination 28.95 deg) and the payload gap
   exceeds section 5.10's bound. Q7 puts the choice to the user; its recommended law has
   no step and, at azimuth 90 deg, stays in the plane.
5. Schema edits change resolved dicts. Adding a field to `PlanarSiteConfig`, or an
   `earth` block that appears in a planar run dict, would break the digest pin on its four
   files and change the dicts of the planar files it does not pin.
   Mitigation: the spatial site and the `earth` block live on the spatial path only (for
   example a `SpatialSiteConfig`); S1.6's gate checks the resolved dicts of every shipped
   file.
6. The lag-startup case may exceed the run-time budget (section 5.11). Mitigation:
   measure; if it does, report it and log a known issue rather than loosen a tolerance.
7. The spatial planner is a copy, so a later fix to `phases/planar.py` does not reach it.
   Mitigation: log it in TODO.md (backlog: port planar onto the shared kit) and state the
   copy date in the module docstring. The fairing-event mass convention (TODO.md KI-016,
   closed in SP2 step A1, 9579f89, by the reader `run_data.with_drop_masses`; the planner's
   logging unchanged, and SP7 did not change it) is copied as phases/planar.py stands at
   SP3's start commit.
8. The dataclasses the 1-D golden dump reaches have frozen field lists (D-SP7-27;
   tests/test_golden_dump_fields.py). The dump writes losses.LossBudget and
   losses.AssistEnergyBudget field by field. It reads sim.Result, sim.RunResult,
   config.ResolvedRun, config.SweepPoint, compare.SensitivityRow,
   results_io.ExperimentResult and results_io.SweepResult by attribute. A field added to
   the first two changes the dump and fails the 1-D golden for good (it is never
   recaptured). A field added to any of the nine fails the field-list test. Mitigation:
   the spatial data, the lateral gravity row J_grav_lat included, ride in new classes on
   the spatial path; where the lateral row lives is settled in Plan mode.

Open questions for Plan mode:

- Name and content of the model-to-model experiment file. Recommended: pad baseline plus
  `silo_cold` on the gate vehicle, the shared blocks verbatim from
  `experiments/silo_screening_2d.yaml`, `dynamics: spatial_3d`, `earth: spherical`,
  28.5 deg, azimuth 90 deg.
- Whether the |dP*| < 5 kg expectation is also pre-registered for `silo_cold` against
  27,553.2 kg. Recommended: yes, the same second-order argument applies and the track g
  is bit-equal (the argument holds under Q7's recommended law; under section 5.7's as
  written a review's replica gives -11.1 kg here, Q7). **Needs the user** only if the
  session wants a different bound.
- How spatial experiments are classified by
  `test_every_shipped_planar_experiment_is_checked`. Recommended: a parallel
  `SPATIAL_EXPERIMENTS` list whose files match the planar ones on PLANAR_SHARED_KEYS
  (guidance, search, target_orbit, checks). `dynamics` and `site` differ by design, so the
  planar check over SHARED_KEYS cannot take them. Two tests load every file in experiments/
  the CLI's way, preflight included, and so load the new one too:
  tests/test_config.py::test_ki030_shipped_files_resolve_with_every_value_as_written and
  tests/test_results_io.py::test_preflight_visits_every_resolved_run_and_passes_the_shipped_experiments.
- The value of `site.longitude_deg` for the Cape Canaveral case. The first handoff
  suggested about -80.6 deg as a display choice; it must be labelled display-only and
  carry `assumed` or a source.
- Settled: SP2 closed on 2026-10-07 and SP7 closes before SP3 (D-SP1-18, D-SP2-40); the
  user's request of 2026-10-19 sets SP3 next, and a different order is the user's call at
  SP3's start (handoff section 6).

**Questions SP3's Plan mode puts to the user** (from SP7's close-out, none answered here;
each gives the recommendation first. The fact-check of 2026-11-04 recommended on Q1 and on
Q3's planar-only blocks; the recommendations on Q2, Q4, Q5 and Q6 and Q3's clause on the
`planar` key were drafted at SP7's close from this file's text and have not been tried
against a design, and `integrator.planar_max_step_s` has none yet. Q7 came later, from
that close-out's physics review (pass 2, 2026-11-05), and its recommendation is the
review's. Plan mode confirms or changes them.)

- **Q1: the altitude-up event and SP7's shaft flight.** Recommended: refuse a release below
  the mouth on spatial_3d in SP3 with a one-line message, since the model-to-model pair
  releases at the mouth; the phase that first needs it ports it. The question: where the
  spatial altitude-up event is built (`phases/spatial.py` or `phases/engine.py`, the choice
  5.2 already leaves open): `engine.ev_altitude_up` (843) takes its rate from
  `_altitude_rate_index` (834), which accepts only a layout with `v_r_mps` or `v_mps`. And
  whether the spatial planner copies SP7's shaft sub-phases with their tests (a release
  below the mouth, the shaft floor, `SHAFT_EXIT_EVENT`, `SHAFT_APEX_EVENT`,
  `SHAFT_TURNAROUND_EVENT`; D-SP7-51; `phases/planar.py` 140-168 and `_burn`, 1655), or
  refuses a release below the mouth on spatial_3d and logs it.
- **Q2: SP7's drives on a spatial run.** Recommended: refuse the linear motor and the sealed
  shaft on spatial_3d in SP3 with a one-line message, as Q1 does for a release below the
  mouth: the record needs neither, and a refusal adds no metric key or assumption line; the
  cost is that a later phase wires them. The question: the prelude is shared, so a spatial
  run could fly every drive the planar one does, including SP7's linear motor, its sealed
  shaft and its release at a target speed below the mouth. Does SP3 accept them
  (`metrics_spatial` then writes SP7's linear-motor and sealed-shaft keys and lines, as
  `metrics_planar.planar_track_metrics` and `sim.planar_assumptions` do), or refuse them on
  spatial_3d until a later phase? The model-to-model record (5.10) is the pad baseline and
  needs no drive; the recommended second run, `silo_cold`, flies constant_accel and releases
  at the mouth.
- **Q3: the shared blocks, and the planar-only blocks.** Recommended: `offload:` and
  `structure:` stay planar-only in SP3 and only the shared-block rule is widened, with the
  shared blocks carried under the `planar` key, since renaming it would change every planar
  resolved dict. The question: today the `guidance`, `search`, `target_orbit` and `checks`
  blocks are injected into each run under the run-dict key `planar` (`RunConfig.planar`, a
  `PlanarShared`) and refused on any dynamics but planar_2d (config.py 2399-2405), and
  `offload:` and `structure:` refuse every model but planar_2d (config.py 2533, 2600; the
  offload re-check is SP4). Does a spatial run carry the shared blocks under the `planar`
  key and reuse `integrator.planar_max_step_s`? Renaming either would change every planar
  resolved dict, and SP1's digests are never recaptured. Does S1.6 widen the offload and
  structure rules to spatial_3d or leave them planar-only for SP4?
- **Q4: reused assumption lines that name the planar model.** Recommended: edit no reused
  line, and give the spatial path its own wording that names omega_E cos(lat); with Q3's
  recommendation no structural wording reaches a spatial summary in SP3. The cost is a
  spatial copy of those lines. The question: how a spatial run words the reused assumption
  lines that name the planar model: the drives' `track_gravity_assumption` ('the planar
  rotation rate of the site', constant_accel.py 205, linear_motor.py 810) and
  `prelude.ramp_start_assumption` ('on planar_2d drag and rotation', 511). Section 5.6 folds
  omega_E cos(lat), which equals omega_p only at azimuth 90 deg. No planar or 1-D line may
  change. Also how D-SP7-22's three-way structural wording reaches a spatial summary.
- **Q5: the ECI epoch and the hold rows.** Recommended: keep the epoch 5.3 writes (ECI and
  ECEF coincide at run clock t = 0) and write the spatial hold rows and the logged track
  events so that the state turns with the ground, because the ECEF, longitude and
  `raan_epoch` columns depend on it; the cost is a spatial hold function beside the shared
  one, and `from_track` for the logged track events. The question: the planar datum puts
  theta = 0 at the flight start (release or the liftoff root), not at t = 0, and the shared
  prelude's `hold_state(z_m, m_kg)` takes no time while `hold_rhs_for` holds every row but
  the mass (prelude.py 659-680, 846-862). So an ECI hold state stays inertially fixed while
  the ground turns. `from_track(y_track, params)` takes no time either (prelude.py 861,
  called at 1331, 1375, 1409, 1442, 1445, 1455 and 1839), so every track event logged
  through the shared prelude has the same gap. The spherical dynamics do not depend on it;
  the ECEF, longitude and `raan_epoch` columns do. Plan mode decides the epoch (run clock
  t = 0, as 5.3 now says, or the flight start as in the planar datum) and how the spatial
  hold rows and logged track events are written.
- **Q6: what `SpatialSearchContext` offers beyond `RecordingProblem`.** Recommended: nothing
  beyond it in SP3, with the file saying what the context leaves out; the cost is that SP4
  adds it if the S1 re-check carries SP7's structure. The question: `RecordingProblem` with a
  `ProblemFactory` built as `offload.planar_problem_factory` builds the planar one is all
  SP1's offload solver needs. SP7's structural transform also flies a linear-motor push
  through a `SearchContext` (`StructureTransform.push_context`, `sim.flown_push_trace`,
  sim.py 2388-2414). Whether the S1 re-check carries it is SP4's decision (board, "Dependency
  order", the SP4 row), so SP3 only has to say what its context leaves out.
- **Q7: the gravity turn's law, on which the bound |dP*| < 5 kg rests.** Recommended: a
  zero-yaw gravity turn, e the projection of v_rel on the launch plane, in place of
  section 5.7's full vector. At azimuth 90 deg it keeps the launch plane and, in the
  review's judgement, with no source, is closer to what a closed-loop vehicle holds; it
  keeps section 5.10's second-order argument true and has no step at kick end (risk 4).
  The cost is a steering row from the sideslip, 0.0095 m/s over stage 1 on the recorded
  pad, which the payload does not feel, since the thrust stays along the planar direction
  (stage 2 adds about 0.15 m/s of sideslip row under either law). The alternative is to
  keep the full vector and accept a bound that does not hold on this replica (about -20
  kg). The question: which law S1.3 builds, and with it which speed starts the kick
  (section 7, Tolerances). Section 5.10's dated note gives the mechanism. No test before
  S1.8 measures its payload cost (S1.6 and S1.7 report the inclination, which on the
  replica would read 28.95 deg against 28.5, but no test holds it): S1.4 and S1.5 are
  equatorial or vacuum in-plane, and S1.6's 28.5/90 case tests the identity, not the
  payload. So on the full vector the phase's last step would meet a gap about four times
  the bound, with no row named for it: it would show as +2.5 m/s of V_f from the
  inclination (about 1.9 m/s of it section 5.5's term), -1.09 m/s on the lateral row and
  +0.84 m/s of steering, and J_vac would pay 2.07 m/s. A review's replica (the shipped
  vehicle, drag and atmosphere, stage 2 by planar LTG shooting, delta re-solved per model,
  payload at zero residual; it reproduces the recorded pad: kick 12.4937 and 17.7740 s,
  MECO 151.3284 s, cutoff mass within 0.41 kg) gives:

  | Law | dP* pad | dP* silo_cold | Inclination, pad and silo_cold |
  |---|---|---|---|
  | Section 5.7 as written, e = v_rel_hat | -20.2 kg | -11.1 kg | 28.95 and 28.74 deg |
  | Zero yaw, e the in-plane projection of v_rel | -0.001 kg | -0.001 kg | 28.50 deg |

  Controls: at the equator 3-D equals planar; the crosswind scaled by 0, 0.5 and 1 gives
  -0.00, -4.80 and -20.07 kg (residuals at the recorded delta; quadratic, ratio 4.18); by
  hand, v_rot (1 - cos 6.1 deg) = 2.31 m/s at RQ2's 9.4 kg per m/s is about 22 kg; rtol
  1e-10 and 1e-11 agree. On the full vector the pad-to-silo delta moves by about +9.1 kg.
  The -0.001 kg is at each law's exact delta optimum; S1.8's searched difference is
  limited to a few tenths of a kg by the search's tolerance. A second replica, by pass 3
  of the same review (Cartesian to cutoff, drag throughout, stage 2 in a plane frozen at
  its ignition; pad residual +0.0002 kg at the record's payload, every loss row to 3
  decimals), gives -20.21, -11.06 and -0.001 kg and the rows in the paragraph above. The
  cause is the rotating sphere's unbalanced centrifugal term, since radial "up" is not the
  plumb line, so S2's geodetic vertical should remove most of it (not measured). SP4's
  file, lines 214-217, rests on the same bound; re-check it at SP3's close. These are a
  review's replica numbers, not a run and not a finding: no spatial_3d code exists. The
  reports and the probes are outside the repository (KI-102):
  C:/Users/rahul/.claude/projects/D--DEV-ClaudeProjects-SpaceRocketOptimization/sp7work/c1/review-p2-physics.md
  with p2-probes/ beside it, and review-p3-physics.md with p3-probes/. Any later change to
  the law or to the bound followed this probe, so it is not a blind pre-registration; if
  neither changes, S1.0's expectation is still written after this probe's number (section
  5.10).

## 11. Session log

(empty: phase not started)

## 12. Deviations from the plan

(none)

## 13. Prompt to start this phase

Final (2026-11-05, SP7's close-out, checked at d03367b). SP7's handoff,
docs/handoff/NEXT_SESSION.md section 10, holds the same text; if the two differ, this one
wins (protocol section 8, item 10).

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP3-3d-dynamics-s1-sphere.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links, then the inputs the phase file links
> (docs/phases/inputs/2026-09-30-design-3d-dynamics.md first), and sections 11 and 12 of
> docs/phases/SP7-structural-mass-push-load.md for what SP7 changed in the shared modules.
>
> We are continuing launch-assist-sim. SP7 is closed: a first-order structural sizing
> model (structure.py, configs/structures/) charged into SP1's offload solve through an
> optional vehicle transform; the force- and power-limited linear motor
> (assist/linear_motor.py) with release at a target speed, the shaft floor and the sealed
> shaft; and the findings note docs/findings/RQ1-structural-2d.md (a first-order station
> sizing at central coefficients, with an assumed 0.5 s rise time, zero margin, the pad's
> unthrottled flight as the envelope and the instant release flagged, not sized; planar,
> sweep-optimized and unthrottled, on the gate vehicle with its +14.3% calibration miss:
> the modelled structure cancels most of SP1's offload, and 11.42 t of 41.26 t is left).
> This session is phase SP3: stage S1 of true 3-D dynamics, a 3-DOF point mass in ECI
> Cartesian coordinates over a rotating sphere, built beside the planar model without
> changing any planar or 1-D number. SP3 uses nothing from SP2's app or SP7's structure
> model, but its copy of phases/planar.py and its inventory include SP7's edits.
>
> Follow the session protocol. Run its start checklist: a clean tree; HEAD's subject
> "Close SP7: trackers, handoff, next phase file", SP7's closing commit (named in the
> handoff) an ancestor, and `git diff --stat <that commit> HEAD` touching only bookkeeping
> files; the fast suite green with the count recorded; the entry criteria of the phase
> file's section 4 (the pins, the two recorded payload capacities 26,054.3962 and
> 27,553.2271 kg within 0.002 kg, SP1's solver built from a problem factory); the
> inventory of section 6 re-checked against HEAD (last checked at d03367b); the open KI and
> B items owned by SP3 listed (KI-001). If the session starts in Plan mode, do the
> read-only checks first and run the suite right after approval, as the protocol's section
> 3 says.
>
> Then work in Plan mode (step 0). Confirm or refine steps S1.0 to S1.8 against the code,
> put the open questions of section 10 to me, each with your recommendation first and the
> trade-off in one line, show me the plan with the step table, the gates and the
> tolerances, and wait for my approval before writing any code. My request of 2026-10-19
> to keep working through SP3-SP6 does not replace that approval. After approval, log the
> decisions as D-SP3-nn in TODO.md, save the design under docs/phases/inputs/, and make the
> start commit ("Start SP3: status in progress").
>
> Rules for the whole session. Plan mode, and docs/physics.md in the same change, for
> anything touching the equations of motion, frames, events, integrator settings or loss
> accounting; every step of this phase does. The planar pin test (S1.0) is committed before
> any file under src/ is edited, and every new physics feature passes its closed-form test
> before any experiment uses it. Write the expectation |dP*| < 5 kg against 26,054.4 kg
> into TODO.md and commit it with the planar pin (S1.0), before any file under src/ is
> edited and so before any searched 3-D run; write docs/findings/M2M-3d-vs-planar.md at the
> end (S1.8). The bound is an expectation to test, not a target to tune toward: a
> difference outside it is reported as a miss, as plainly as one inside it. The experiment
> file is committed before it is run, the run starts from a clean commit, and no results
> directory is ever overwritten or deleted.
>
> Run every step through the loop: implementer; adversarial reviewers (a physics or
> numerics skeptic and a CLAUDE.md compliance auditor on every code step, an honesty
> auditor on S1.7's summary rows and S1.8's note); up to two fix rounds, and an extra
> round (a fixer and verification reviewers) before the gate when a step's third review
> pass still has majors (SP7 deviation 31); an independent gate that runs every command in
> the foreground, in chunks under ten minutes, never ends its turn on a running command
> and has docs/physics.md in its file list; one commit per gate; the tracker commit at
> once ("SP3 step <k>: trackers (<hash>)"); then `git push origin main` and a check that
> the Pages deployment succeeded. Standing gates on every code step (the phase file's
> section 7): fast suite green, ruff clean, the exact 1-D golden tier, SP1's planar digest
> pin, the planar output capture, the golden-dump field lists, templates/replay.html's
> sha256, the structure files' and the vented byte pins, no shipped experiment, vehicle or
> structure file edited, and from S1.0 on the S1.0 pin (its slow part run by name); the
> full suite after every step from S1.2 to S1.7.
>
> At the end, run the end checklist of the protocol's section 7: an independent gate on
> each exit criterion (a criterion stays open only with my explicit acceptance, logged as a
> decision); the full suite and ruff with the counts recorded; the demo under
> docs/demos/SP3/; the phase file closed, the board, TODO.md, CLAUDE.md (status, layout,
> the spatial frame) and README.md updated, and the public face refreshed (landing page,
> deck and its PDF, gallery, manual) with the site built locally and no broken link; the
> close-out questions to me with the recommendation first (which phase runs next: SP4 in
> the planned order); the fact-check of the next phase's file against the code; the
> handoff archived and the new one written with the next prompt; the next prompt printed
> to me; the memory updated; the cold-read check by an agent that did not write the
> documents; the closing commit; the push and the Pages deployment confirmed.
