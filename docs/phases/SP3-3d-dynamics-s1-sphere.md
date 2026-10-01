# SP3: 3-D dynamics S1, a 3-DOF point mass over a rotating sphere

Status: not started

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-09-30 in
the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md)) and the
3-D design ([inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md)).
Nothing in this file has been built or run. The session before SP3 re-checks sections 4, 6
and 13 against the code as it then is.

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
  S1.0, before any 3-D code exists).
- TODO.md KI-001, which this phase owns: a read-only audit that no loss integral or check
  reads the unwrapped `gamma_rel_rad` (step S1.6). The issue is then closed or re-owned.
- `docs/physics.md` updated in every step that touches equations, frames, events or loss
  accounting.

Out of scope (each has a home):

- Oblate Earth, J2, geodetic altitude: SP5.
- 6-DOF, attitude, gimbal: SP6.
- The 3-D scene and the offload re-check on S1: SP4.
- Inclination or plane targeting with yaw (S1b): deferred; see section 5.12.
- Tilted or curved tracks, force-limited drives: README Phase 3. The general tilted
  release form is written down in section 5.6 as the seam for it and is not built.
- Porting `PlanarPlanner` onto the shared model kit: deferred.
- Any change to a planar or 1-D number. None is allowed (section 5.1).
- Optimal control (README Phase 5); wind.

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-01: 3-D means true 3-D dynamics in three validated stages; this phase is S1. It
  also answers CLAUDE.md's "ask before expanding scope (6-DOF, 3-D Earth)".
- D-SP1-07: order of the program (settings and offload, planar findings, app, then 3-D).
- D-SP1-08: one fresh session per phase; this file is the starting document.
- D-SP1-09: the offload is an `offload:` block and a post-pass, so no pre-registered file
  or budget id changes. The reuse requirement is not a numbered decision: it is step 5 of
  the approved plan and section 5.4 of the SP1 phase file (`OffloadProblem` is built from
  a problem factory against `RecordingProblem`), so the 3-D search context inherits the
  solver without change. It is used in SP4, but it constrains what `SpatialSearchContext`
  must satisfy here.
- D-SP1-11 and D-SP1-12 concern S2 and S3 and are not acted on here.
- From Phase 2 (legacy ids are assigned in TODO.md): the calibration miss of +14.3% is
  accepted and carries over unchanged; the planar flight step cap is 2 s and is kept for
  the 3-DOF model.

## 4. Entry criteria

1. SP1 is "done" on the program board. In the planned order (D-SP1-07) SP2 is also done,
   but SP3 uses nothing from SP2; starting SP3 before SP2 is a user decision logged in
   TODO.md.
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3).
3. Fast suite green (`uv run pytest -q -m "not slow"`); ruff clean; the 1-D golden tier
   byte-identical; SP1's planar digest pin passes; the pad and silo_cold payload
   capacities reproduce their recorded values within 0.002 kg (SP1 step 5 gate):
   26,054.3962 kg for the pad (tests/data/calibration_record.json, `amended_rerun` block)
   and 27,553.2271 kg for silo_cold (metrics.json of
   results/silo_screening_2d/20260930T175743Z, git 7ad381f; copied into test data by SP1
   step 1). The one-decimal figures 26,054.4 and 27,553.2 kg are not the reference.
4. SP1's offload solver exists and is written against `RecordingProblem` with a problem
   factory, not against `SearchContext` (design requirement on SP1). If it is not, that
   is logged as a known issue for SP4, not fixed here.
5. Section 6 of this file has been re-checked at the current HEAD and its commit and date
   updated. SP1 edits `phases/engine.py`, `phases/planar.py`, `phases/prelude.py`,
   `phases/vertical.py`, `guidance.py`, `search.py`, `sim.py`, `config.py`, `vehicle.py`,
   `compare.py`, `results_io.py`, `summary.py`, `metrics_planar.py`, `replay.py` and
   `cli.py`, and SP2 edits `plots.py`, `replay.py` and `cli.py` if it has run. Every line
   number below will have moved.

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
  modules are additive.
- No physics feature is used in an experiment until its closed-form test passes. The
  model-to-model run (S1.8) is the first searched 3-D run used for a record and comes
  last. Searched 3-D runs also happen inside tests before it (S1.5 to S1.7), so the
  pre-registered expectation of section 5.10 is committed earlier, with S1.0, before any
  file under src/ is edited.

### 5.1 Approach

`search.py` and the two inner solves in `guidance.py` see only protocols and are reused
unchanged. The planner, the steering laws, four events, the metrics and the run assembly
are written new, as copies, so no planar number can move. The coupling table with line
numbers is in section 6.

The new `SpatialPlanner` is written against a small model kit (layout, rhs, kinematics,
law and event factories) so that S2 and S3 reuse it. The copy is taken from
`phases/planar.py` as it stands when SP3 starts, which includes SP1's altitude ignition
event and ignition resolver, not as it stood at 2eebcae.

Edits that touch validated code, all behaviour-preserving for 1-D and planar and guarded
by S1.0 and the 1-D golden tier: the `sim.run` dispatch, the `DynamicsKind` literal and
its rules in `config.py`, the model branches in `compare.py`, `results_io.py`,
`summary.py` and `plots.py`. No new dependency.

### 5.2 Module layout and config

| New file | Content |
|---|---|
| `src/launchsim/frames.py` | ECI/ECEF/local-frame transforms, site position, v_rel |
| `src/launchsim/orbit3d.py` | h vector, inclination, node, argument of latitude; a, e, r_p, r_a through the existing `orbit_elements` |
| `src/launchsim/dynamics3d.py` | state layout, scalar-float RHS, kinematics, observables |
| `src/launchsim/guidance3d.py` | rise, kick, gravity turn and stage-2 linear-tangent laws as 3-vectors |
| `src/launchsim/phases/spatial.py` | `SpatialPlanner`, release map, prelude layout; the four spatial events (here or in `phases/engine.py` beside the planar ones, decided in Plan mode) |
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
  the gravity row absorbs it.

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
- Gravity turn: e = v_rel_hat as a full vector.
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
- Time-series columns are a superset of the planar names, so the 2-D scene of SP2 reads
  3-D runs. Added: ECI and ECEF position and velocity; lat, lon, alt; crossrange; heading;
  yaw; thrust unit vector (ECI); `J_grav_lat`; osculating a, e, i, `raan_epoch`, argument
  of latitude. Events carry the same columns.
- Summary rows add inclination, the gravity split and the model-to-model deltas.
- None of the new metric keys, summary rows or assumption lines may appear on 1-D or
  planar runs. The 1-D golden tier guards the 1-D outputs. For planar runs the guard is the
  written-output part of the S1.0 pin: the metrics.json key lists, the time-series and
  event column lists and a digest of summary.md (step table, S1.0). At 2eebcae no planar
  output golden exists; SP1's digest pin covers resolved config dicts only.

### 5.10 Model-to-model record (S1.8)

- No tuning and no new fitted parameter, so no new calibration. The +14.3% miss of the
  gate vehicle carries over.
- Reference: the planar gate, pad baseline on `configs/vehicles/generic_f9_class_2d.yaml`,
  28.5 deg, azimuth 90 deg, 200 km circular, P* = 26,054.4 kg.
- Why a small difference is expected: at azimuth 90 deg the planar inertial dynamics are
  exact. The only difference is the air's out-of-plane velocity
  omega_E sin(lat) r sin(theta), about 3 m/s at MECO, which enters at second order.
- **Pre-registered expectation: |dP*| < 5 kg.** It is written into TODO.md (and this
  file's session log) and committed in step S1.0, in the same commit as the planar pin and
  before any file under src/ is edited. That is before every searched 3-D run, including
  those inside the tests of S1.5 to S1.7. The expectation has also been on record in this
  file since the SP1 step-T commit. A larger gap is treated as a bug until the loss rows
  explain it.
- The record goes to `docs/findings/M2M-3d-vs-planar.md`: both payloads, delta, (a, b),
  the loss rows side by side with the lateral gravity part, inclination, run times.
- The 5 kg bound is an expectation to test, not a target to tune toward. If the measured
  difference is outside it and the loss rows explain it, the note says so plainly and the
  bound is reported as missed.

### 5.11 Runtime (estimates from the design, to be measured at S1.2)

- Planar today: about 12 microseconds per RHS call, 9-24 s per searched run.
- S1: about 15 microseconds per RHS call, 12-18 s per searched run typical. The
  lag-startup case may reach 30-35 s against the 30 s budget the design refers to (find
  where that budget is asserted before S1.5; docs/physics.md "Performance (measured)").
- The existing 2 s flight step cap is kept.

### 5.12 Deferred

- Inclination and plane targeting with yaw (S1b). It needs a 3x3 shooting or an azimuth
  outer solve, and the headline case (28.5 deg, due east) does not need it.
- Mean-element targets, wind, porting `PlanarPlanner` onto the shared kit.

Size estimate from the design: about 4,500 source lines, 3,000 test lines and 700 lines
of physics.md.

## 6. Inventory of the code this phase touches

Checked at commit 2eebcae on 2026-09-30 (the design's numbers, spot-checked against the
tree when this file was written). To be re-checked by the session before SP3: SP1 and SP2
edit most of these files. Paths are relative to the repository root.

### Coupling to the planar layout

| Module | Reusable as is | Bound to the planar layout |
|---|---|---|
| `src/launchsim/search.py` | `SearchProblem` (460) and `RecordingProblem` (489) protocols; `payload_root` (805), `optimise_gamma` (1335), `final_verify` (1568), `run_search` (1722): they see only the protocols | `SearchContext` (502-711); test-only `joint_root_crosscheck` (1822); `Stage2Result` and `KickPoint` appear only as annotations |
| `src/launchsim/guidance.py` | `solve_delta_for_gamma` (367), `solve_ltg` (653), `GuidanceSpec` (250), `LtgSettings` (517), the guess ladder (`ltg_physics_guess` 602, `ltg_guess_ladder` 616), `GuidanceFailure` (93), the sentinels (62-80) | All steering laws (`Radial` 117, `FixedTilt` 136, `AlongVrel` 163, `LinearTangent` 181, `LinearTangentEps` 214): they return `(e_r, e_theta)` from `PlanarKinematics` |
| `src/launchsim/phases/engine.py` | `integrate_phase` (390), `ev_ground(model)` (700), `ev_propellant(layout)` (579), `ev_time` (797) | `ev_radial_apex` (725) and `ev_radial_turnaround` (741) need `v_r_mps`; `ev_kick_start` (752), `ev_kick_aligned` (776); `atol_for` (281, suffix table 80-86) rejects unknown suffixes |
| `src/launchsim/phases/prelude.py` | Hold and `fly_track` (483) through `PreludeLayout` (403) and a `g_eff_mps2` argument | Nothing |
| `src/launchsim/phases/planar.py` | The state-machine structure only (`PlanarPlanner` 733-1624) | No hooks: module-level `PLANAR_LAYOUT` indices (179-184), `rhs_planar`, `PlanarEnvironment` (266) throughout; `map_release_planar` (392), `planar_prelude` (423), `map_staging_planar` (446), `map_fairing_planar` (470), `ev_energy_cutoff` (488), `ev_fmh` (509), `FlightStart` (549), `KickPoint` (568), `Handover` (587), `Stage2Result` (621) |
| `src/launchsim/dynamics.py` | `StateLayout` (148), `DynamicsModel` protocol (189), `thrust_terms` (124), `g_eff_track` (114) | `PLANAR_STATE_NAMES` (530), `PlanarKinematics` (604), `SteeringLaw` (643), `PlanarParams` (667), `planar_forces` (739), `rhs_planar` (788), `PlanarDynamics2D` (883) |
| `src/launchsim/losses.py` | `loss_budget(phases, layout, speed)` (294), `rocket_equation_closure(trace, vehicle, layout)` (408) | `pointwise_dVdt` (343) |
| `src/launchsim/metrics_planar.py` | `scan_peak` (169), `max_q` (248), `unwrap_rad` (348), `loss_items` (824), `search_metrics` (1025), `closure_metrics` (1153): about a third of the file | Sampling, rows, felt loads |
| `src/launchsim/orbit.py` | `TargetOrbit` (20), `orbit_elements` (95) | Nothing (takes scalars) |
| `sim.py`, `compare.py`, `results_io.py`, `summary.py`, `plots.py`, `cli.py` | Structure | Branches on `== PLANAR_2D` (listed below); `compare.MatchedRun` (571) carries `omega_p_rads` (589) and builds `PlanarDynamics2D` (613, 802; 931 passes `view.omega_p_rads`) |

### Branch sites on the dynamics kind (to become a model set in S1.6 and S1.7)

- `src/launchsim/config.py`: `DynamicsKind = Literal["vertical_1d", "planar_2d"]` (78);
  `RunConfig._dynamics_rules` (1110) with checks at 1102, 1111, 1155; `ExperimentConfig`
  checks at 1370, 1390, 1408, 1434, 1441; `resolve_run` at 1754, 1759;
  `PlanarSiteConfig` (476-493), which requires every site field explicitly.
- `src/launchsim/sim.py`: `run` (812), dispatch at 823; `run_planar` (1393);
  `planar_setup` (955); `search_context` (981); `simulate_planar` (1109);
  `matched_run` (1480).
- `src/launchsim/compare.py`: 379, 432, 494-500.
- `src/launchsim/results_io.py`: 528, 586, 610, 642, 854, 968, 988, 1046, 1126.
- `src/launchsim/summary.py`: 572. `src/launchsim/plots.py`: 129, 597.
  `src/launchsim/cli.py`: 279. `src/launchsim/replay.py`: 186 (replay refuses anything
  but planar; whether it accepts spatial runs is decided in SP4).

### Tests that guard or serve as models

- `tests/test_golden_1d.py` with `tests/golden_1d_support.py`: every 1-D output pinned.
- `tests/test_golden_planar.py` does not exist at 2eebcae; S1.0 creates it. SP1 step 1
  adds a digest pin of the resolved planar experiments and SP1 step 5 reproduces the two
  payload capacities; S1.0 extends those, it does not duplicate them.
- `tests/test_config_planar.py`: `PLANAR_EXPERIMENTS` (52) and
  `test_every_shipped_planar_experiment_is_checked` (805). A new experiment file must be
  classified there or in a parallel spatial list.
- Models for the new tests: `tests/test_planar_dynamics.py`, `test_planar_reductions.py`,
  `test_orbit.py`, `test_release_planar.py`, `test_loss_identity_2d.py`,
  `test_closure.py`, `test_convergence_2d.py`, `test_planar_events.py`,
  `test_payload_search.py`, `test_search.py`, `test_planar_pipeline.py`.
- `tests/test_calibration.py` (slow): P* regression against
  `tests/data/calibration_record.json`.

### Critical files (read in full before planning)

`src/launchsim/phases/planar.py`, `src/launchsim/dynamics.py`, `src/launchsim/search.py`,
`src/launchsim/guidance.py`, `src/launchsim/sim.py`.

### docs/physics.md sections to extend (heading lines at 2eebcae)

Frames and datum (333), Planar ascent state and equations of motion (494), 2-D loss
identity (648), Planar reductions (750), Orbital elements and the circular target (813),
Planar release map (840), Stage-1 guidance and events (947), Stage 2 and insertion
(1418), Event rules (3258), Experiment schema (4374), Assumptions (4533),
Test-to-equation map (4796). The 3-D material goes in new sections beside these; the
planar text is not rewritten.

## 7. Steps

Each step runs the loop of SESSION_PROTOCOL.md section 4: implementer, adversarial
reviewers (physics or numerics skeptic, CLAUDE.md compliance), up to two fix rounds,
independent gate, commit, tracker update. Standing gate on every code step: fast suite
green, ruff clean, 1-D golden byte-identical, SP1's planar digest pin and the S1.0 pin
passing; the full suite after every step from S1.2 to S1.7 (all are physics-core).
The payload-capacity part of the S1.0 pin runs full searches and is slow-marked, so the
fast suite does not run it: run it by name
(`uv run pytest -q tests/test_golden_planar.py`) at every step's gate.
`docs/physics.md` is updated in every step. Test file names are proposals.

Tolerances. Those in the table that the design input does not give are proposals of this
file, confirmed or changed in step 0: 1e-12 for the algebraic reductions (the steering
laws and the kick event of S1.3, the pointwise dV/dt of S1.2); 1e-8 relative for the
vacuum-coast energy (CLAUDE.md's validation list); 1e-12 relative for g_up against g_ref
in the hold-consistency test; `checks.closure_tol_mps` (1e-5 m/s) for the rocket-equation
closure. The S1.0 pin compares the two payload capacities within 0.002 kg of their
recorded values (the tolerance SP1 uses for the same two numbers), delta, (a, b), the loss
rows and the cutoff state within 1e-9 relative, and the key lists, column lists and the
summary digest exactly.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| 0 | Session start: entry criteria, inventory re-check, Plan mode, open questions of section 10 put to the user | this file, TODO.md | fast suite | User approves the plan | [ ] | |
| S1.0 | Planar pin, test only: gate pad and silo_cold P*, delta, (a, b), loss rows, cutoff state; and the planar written outputs captured on the untouched tree for pad and silo_cold of a small planar experiment (metrics.json key list, time-series and event column lists, sha256 of summary.md without the lines that change from run to run). SP1 step 1 adds such a capture; S1.0 re-captures it at SP3's start commit. The model-to-model expectation (section 5.10) is written into TODO.md in the same commit | `tests/test_golden_planar.py`, TODO.md | the pin itself | Passes on the untouched tree; pin and expectation committed before any file under src/ is edited | [ ] | |
| S1.1 | Frames and orbit elements | `frames.py`, `orbit3d.py` | Element round trip at 1e-12; v_rel against a finite-differenced ECEF position; pad release speed 465.10 m/s at the equator and 465.10 cos(lat) at latitude (408.74 m/s at 28.5 deg), due east; vacuum inclination closed form cos i = cos(lat) sin(beta_inertial) | All listed tests | [ ] | |
| S1.2 | Equations of motion (scalar-float RHS); measure the RHS cost | `dynamics3d.py` | Inclined e = 0.3 orbit, 10 revs: energy, each component of h and the eccentricity vector drift < 1e-8, period 2 pi sqrt(a^3/mu); 500 seeded states: rows equal `rhs_planar` after transformation on the equator at 1e-12, and pointwise dV/dt closes at 1e-12; vacuum coast energy conserved to 1e-8 relative | All listed tests; RHS time per call recorded in the session log | [ ] | |
| S1.3 | Steering laws and the four events (apex, turnaround, kick start, kick aligned) | `guidance3d.py`, `phases/spatial.py` (events) | Laws reduce to the planar tuples at 1e-12; the kick event equals the planar function at 1e-12 | All listed tests | [ ] | |
| S1.4 | Planner, release map, prelude layout | `phases/spatial.py` | Hold consistency: a point released at rest accelerates at g_eff, whose up-component equals the prelude's g_ref to 1e-12 relative. Equatorial east, fixed (delta, a, b), rtol 1e-12: same event sequence as `PlanarPlanner`; r, v_r, v_theta, m and all J within 1e-9 relative at MECO and cutoff; event times within 1e-8 s; abs(z) < 1e-6 m. 28.5 deg, azimuth 90 deg, vacuum, in-plane laws only: equals planar at 1e-9 and i = 28.5 deg at 1e-12 | All listed tests | [ ] | |
| S1.5 | Search context | `search_spatial.py` | Slow: equatorial-east P* within 1 kg of planar; gamma_MECO(delta) monotone scan | All listed tests; `search.py` and the inner solves unchanged (diff check) | [ ] | |
| S1.6 | Metrics, run assembly, dispatch in `sim.run`, config literal and `earth` block, `site.longitude_deg` | `metrics_spatial.py`, `sim_spatial.py`, `sim.py`, `config.py` | Loss identity < 1e-5 m/s at 28.5/90 and at 45/45 (lat/az, deg); rocket-equation closure within `checks.closure_tol_mps` (1e-5 m/s); convergence < 0.1% under 10x tighter tolerances; schema refusals (`wgs84_j2` and `rigid_6dof` not yet available). KI-001: read-only audit that no loss integral or check, planar or spatial, reads the unwrapped `gamma_rel_rad`; close the issue in TODO.md or re-own it | All listed tests; resolved dicts of the shipped planar and 1-D experiments unchanged; KI-001 closed or re-owned | [ ] | |
| S1.7 | Reporting generalisation: a model set instead of `== PLANAR_2D`; `MatchedRun` takes layout and speed; new writers | `compare.py`, `results_io.py`, `summary.py`, `plots.py`, `cli.py` | Pipeline test on a small spatial run: required metrics present, summary rows (inclination, gravity split) | The S1.0 pin passes, its written-output part exactly (planar metrics.json keys, time-series and event columns and the summary digest byte-identical), and the 1-D golden is byte-identical; a spatial run from the CLI writes a complete results directory | [ ] | |
| S1.8 | Model-to-model record: experiment file committed, run from the clean commit, findings note with honesty review. The expectation was committed in S1.0 | `experiments/` (new spatial file), `docs/findings/M2M-3d-vs-planar.md`, TODO.md | `tests/test_config_planar.py` or its spatial twin lists the new file | The expectation commit (S1.0) precedes the first commit that adds `search_spatial.py`, and so every searched 3-D run (git log); no `bug_suspect`; difference under 5 kg, or explained by the loss rows and reported as a miss | [ ] | |
| C | Close SP3: exit-criteria gate, demo recorded, CLAUDE.md layout and conventions (spatial frame), README status, TODO.md, SP4 phase file fact-checked, handoff and prompt, memory | docs/, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit | [ ] | |

## 8. Exit criteria

1. `tests/test_golden_planar.py` was committed before the first commit that edits a file
   under src/ in this phase (checked in git log) and passes at the closing commit, with
   the 1-D golden tier and SP1's planar digest pin unchanged. The pin covers the solver
   numbers (pad and silo_cold P*, delta, (a, b), loss rows, cutoff state) and the planar
   written outputs (metrics.json key lists, time-series and event column lists, the
   summary digest); the written outputs are byte-identical at the closing commit.
2. Frames and elements: the S1.1 tests pass, including 465.10 m/s at the equator and
   408.74 m/s at 28.5 deg.
3. Dynamics: the inclined e = 0.3 orbit holds energy, each component of h and the
   eccentricity vector to < 1e-8 relative over 10 revolutions; the 500-state comparison
   with `rhs_planar` passes at 1e-12; the vacuum coast conserves energy.
4. Guidance and events reduce to the planar tuples and the planar kick event.
5. Planner: the equatorial-east run matches `PlanarPlanner` (same event sequence, states
   within 1e-9 relative at MECO and cutoff, event times within 1e-8 s, |z| < 1e-6 m); the
   28.5 deg vacuum in-plane run matches planar at 1e-9 with i = 28.5 deg at 1e-12; the
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
12. Demo recorded under docs/demos/SP3/; SP4's phase file fact-checked; handoff, prompt
    and memory written.

## 9. Demo script

Output goes to docs/demos/SP3/ (text captures and a short README with the commit).

    uv run pytest -q -m "not slow"
    uv run pytest -q tests/test_golden_planar.py tests/test_golden_1d.py
    uv run pytest -q -k "frames or orbit3d or dynamics3d or guidance3d or spatial"
    uv run python -m launchsim run experiments/<model-to-model spatial file>.yaml

Look at:

- the test counts, and the pin and golden tests passing;
- the results directory of the 3-D run: `summary.md` (payload capacity, inclination, the
  gravity row with its lateral part, the identity line), `timeseries.csv` with the ECI,
  ECEF, lat/lon/alt and thrust-direction columns;
- `docs/findings/M2M-3d-vs-planar.md`: 3-D against 26,054.4 kg, the expectation written
  before the run, the loss rows side by side.

The exact file and test names are filled in by the session.

## 10. Risks and open questions

Risks (from the design, with mitigations):

1. Shared-module edits move planar numbers. Mitigation: S1.0 first; additive edits only;
   the standing gate on every step.
2. The Cartesian RHS is slow. Mitigation: scalar floats; measure at S1.2 before building
   the planner.
3. Sign and monotonicity of gamma_MECO(delta). Mitigation: the signed definition of
   section 5.7 plus the scan test of S1.5.
4. A thrust-direction step of about 1e-3 rad at kick end, from the crosswind. It is
   documented in the assumptions; in S3 it becomes a small step command.
5. Schema edits change resolved dicts. Adding a field to `PlanarSiteConfig`, or an
   `earth` block that appears in a planar run dict, would break the digest pin.
   Mitigation: the spatial site and the `earth` block live on the spatial path only (for
   example a `SpatialSiteConfig`); S1.6's gate checks the resolved dicts.
6. The lag-startup case may exceed the run-time budget (section 5.11). Mitigation:
   measure; if it does, report it and log a known issue rather than loosen a tolerance.
7. The spatial planner is a copy, so a later fix to `phases/planar.py` does not reach it.
   Mitigation: log it in TODO.md (backlog: port planar onto the shared kit) and state the
   copy date in the module docstring. The fairing-event mass convention (TODO.md KI-016)
   is copied as SP2 leaves it.

Open questions for Plan mode:

- Name and content of the model-to-model experiment file. Recommended: pad baseline plus
  `silo_cold` on the gate vehicle, the shared blocks verbatim from
  `experiments/silo_screening_2d.yaml`, `dynamics: spatial_3d`, `earth: spherical`,
  28.5 deg, azimuth 90 deg.
- Whether the |dP*| < 5 kg expectation is also pre-registered for `silo_cold` against
  27,553.2 kg. Recommended: yes, the same second-order argument applies and the track g
  is bit-equal. **Needs the user** only if the session wants a different bound.
- How spatial experiments are classified by
  `test_every_shipped_planar_experiment_is_checked`. Recommended: a parallel
  `SPATIAL_EXPERIMENTS` list with the same shared-block identity check.
- The value of `site.longitude_deg` for the Cape Canaveral case. The first handoff
  suggested about -80.6 deg as a display choice; it must be labelled display-only and
  carry `assumed` or a source.
- Whether SP3 runs before SP2 (the board allows the swap). **Needs the user** if raised.

## 11. Session log

(empty: phase not started)

## 12. Deviations from the plan

(none)

## 13. Prompt to start this phase

Draft, the previous session finalises it.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP3-3d-dynamics-s1-sphere.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links
> (docs/phases/inputs/2026-09-30-design-3d-dynamics.md first). Follow the session
> protocol. This session does phase SP3: stage S1 of true 3-D
> dynamics, a 3-DOF point mass in ECI Cartesian coordinates over a rotating sphere, built
> beside the planar model without changing any planar or 1-D number. Check the entry
> criteria and re-check the inventory in section 6, then start in Plan mode: confirm or
> refine steps S1.0 to S1.8, put the open questions of section 10 to me with your
> recommendation first, and show me the plan before writing code. The planar pin test
> (S1.0) is committed before any shared module is edited; every new physics feature gets
> its closed-form test before any experiment uses it; docs/physics.md is updated in the
> same change as the equations. Write the expectation |dP*| < 5 kg against 26,054.4 kg
> into TODO.md and commit it with the planar pin (S1.0), before any file under src/ is
> edited and so before any searched 3-D run; write docs/findings/M2M-3d-vs-planar.md at
> the end (S1.8). Keep the build-review-gate loop, commit at each
> gate, keep the trackers current, and close the phase with the demo, the SP4 phase file
> fact-checked, the handoff and the prompt for SP4.
