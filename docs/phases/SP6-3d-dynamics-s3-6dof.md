# SP6: 3-D dynamics S3, the 6-DOF verification fly-out

Status: not started

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-09-30 in
the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md)) and the
3-D design ([inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md),
sections S3, 5, 6 and 7). Nothing in this file has been built or run. The session before
SP6 re-checks sections 4, 6 and 13 against the code as it then is.

This phase is not README Phase 6 (the hobby-scale RocketPy comparison); that stays under
"later" on the program board.

## 1. Goal and what you can see at the end

Build stage S3 of true 3-D dynamics: a 6-DOF rigid body with quaternion attitude, body
rates, a gimballed engine with actuator lag, aerodynamic normal force and moment, jet
damping and a PD attitude controller. Use it to fly the payload and guidance that the
3-DOF models optimised, and report what the point-mass models cannot: attitude, gimbal
demand, true angle of attack, and whether a cold start, which leaves the silo with no
control authority until its engines light, stays pointed.

At the end you can see:

- the new tests green (inertia closed forms, torque-free precession, momentum and
  rotational energy, the fixed-q oscillation or divergence rate, the trim angle, and a
  prescribed-attitude mode that reproduces S1/S2), with every earlier pin unchanged;
- fly-outs of the pad and of the silo runs (full and offloaded): insertion miss, gimbal
  peaks and time in saturation, true q-alpha, attitude error, and for the cold start the
  attitude error at ignition against the divergence time at release;
- the attitude of the rocket in the app's 3-D scene, taken from the quaternion.

Most of the vehicle data this model needs is not published and is marked assumed. The
results are therefore presented as sensitivities, not predictions. If the cold start
turns out hard to control within the assumed ranges, that is reported as plainly as the
payload gain it was credited with.

## 2. Scope and out of scope

In scope:

- New modules `rigidbody.py`, `aero6.py`, `control.py`, `dynamics6.py`, `phases/rigid.py`;
  `engine.atol_for` gains quaternion and `_radps` suffixes.
- Config: `dynamics: rigid_6dof`, accepted as a fly-out only.
- A new vehicle fork `configs/vehicles/generic_f9_class_6dof.yaml` with geometry, mass
  properties, aerodynamic-moment data, gimbal and controller parameters, every number
  with `source:` or `assumed: true`. The gate file is never edited.
- The fly-out pipeline, metrics and a "6-DOF verification" block in the summary.
- Pad and silo fly-outs with sensitivities; a findings note with an honesty review.
- Attitude from the quaternion in the 3-D scene.
- docs/physics.md updated in the same change as each piece of dynamics.

Out of scope (each goes into the run's assumptions list):

- A payload or guidance search in 6-DOF (D-SP1-12). The optional re-solve of delta and
  (a, b) through the existing protocols is the only search-like step (section 5.9).
- Slosh, flex, wind, roll torque and roll control, engine-out, per-engine gimbal
  geometry, thrust misalignment, separation dynamics.
- Nonlinear aerodynamics: the model is linear in alpha and flags |alpha| > 10 deg.
- Reaction control in the staging coast: there is none; the drift is reported.
- CG-shift acceleration terms (neglected, stated).
- Integral control; inclination targeting; mean-element targets (deferred by the design).
- Structural loads from the bending moment (README Phase 3 owns the structural mass).
- Any change to a planar, 1-D, S1 or S2 number.

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-01: three validated stages; this phase is S3. It also answers CLAUDE.md's "ask
  before expanding scope (6-DOF, 3-D Earth)".
- D-SP1-12: the 6-DOF model is a verification fly-out of the 3-DOF-optimised payload and
  guidance, not a new search.
- D-SP1-03, D-SP1-10: the offload semantics; the offloaded silo run flown here is the
  stage-1 headline case.
- D-SP1-11: the target under J2, as SP5 confirmed or changed it.
- D-SP1-07, D-SP1-08: order and way of working.

## 4. Entry criteria

1. SP5 is "done" on the program board (the fly-out must reproduce S1 and S2 in
   prescribed-attitude mode). SP4 is done as well if the attitude display (step V) is to
   be built or the offloaded silo run is to be flown: criterion 4 needs that run's 3-DOF
   result on a spatial model, which comes only from SP4 or from SP5 step R (and step R
   itself needs SP4's experiment file). The dynamics, the pad fly-out and the full-load
   silo fly-outs do not need SP4. Without SP4, step V and the offloaded fly-out go to the
   user as open items (risk 10).
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3).
3. Fast suite green; ruff clean; the 1-D golden tier, the planar pins and the S1 pin
   pass; SP5's S2 tests pass.
4. The 3-DOF results to fly are on record with their results directories named in the
   handoff: P*, delta and (a, b) for the pad and the silo runs, full and offloaded, on
   the Earth model chosen for the fly-out.
5. The `SpatialPlanner` model kit of SP3 (layout, rhs, kinematics, law and event
   factories) exists as the design describes, so `phases/rigid.py` can reuse it. If SP3
   built it differently, section 5 is re-planned first.
6. Section 6 of this file has been re-checked at the current HEAD.

## 5. Design

The full design is in
[inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md). This
section keeps its content for S3.

Rules from CLAUDE.md that govern the phase:

- Plan mode is required for anything touching equations of motion, frames, events,
  integrator settings or loss accounting, with docs/physics.md updated in the same
  change. Steps S3.1 to S3.5 all do that; the 0.1 s step cap and the new tolerance
  suffixes are integrator settings.
- No planar, 1-D, S1 or S2 number may change. Pin tests come first: the existing pins
  pass before and after every step, and the `atol_for` edit is additive.
- Every new physics feature needs its closed-form test before any experiment uses it.
  The fly-outs (S3.7) come after S3.1 to S3.5 pass.
- Never edit a calibrated vehicle config; copy it to a new file.

### 5.1 Role of the model

`dynamics: rigid_6dof` runs a fly-out: it takes (P*, delta, a, b) from a 3-DOF run and
integrates the rigid body under a controller that tracks the same steering laws. It is a
check on the 3-DOF answer and a source of attitude results. It is not a figure-of-merit
search and does not produce a new payload capacity.

### 5.2 State and frames

- r, v in ECI; q (body to ECI, scalar first, Hamilton convention); omega_b in body axes;
  m; two gimbal angles, each with a first-order actuator lag; the seven loss quadratures.
- Body frame: x_b toward the nose; stations measured from the nozzle plane; axisymmetric
  inertia I = diag(I_xx, I_t, I_t).

### 5.3 Dynamics

    q' = 0.5 q (x) (0, omega_b)
    I omega' = M_aero + M_tvc - omega x (I omega) - I' omega - m_e' r_e x (omega x r_e)

- The last term is jet damping.
- Thrust T t_b(delta) acts at the gimbal station; its magnitude and the mass flow are as
  in the 3-DOF models.
- Translation is as in S1/S2 with the force directions taken from the body attitude.
- CG-shift acceleration terms are neglected (stated in the assumptions).

### 5.4 Aerodynamics

- Axial: -q S C_A(M) x_b, with C_A equal to the existing C_D table, so alpha = 0
  reproduces the 3-DOF drag.
- Normal: q S C_N_alpha(M) alpha in the cross-flow direction, applied at x_cp(M).
- Linear in alpha; a flag is raised when |alpha| > 10 deg.

### 5.5 Loss rows

Drag is -F_aero . v_rel_hat / m; steering uses the gimballed thrust direction; the other
rows are unchanged. The generalised identity of SP3 section 5.5 still closes; the gate is
< 1e-5 m/s.

### 5.6 Data: what is sourced and what is assumed

All in the fork `configs/vehicles/generic_f9_class_6dof.yaml`, copied from the gate
vehicle.

| Item | Status |
|---|---|
| 3.66 m diameter, 70 m height, 5.2 m x 13.1 m fairing | Sourced: Falcon User's Guide 2021 |
| LOX/RP-1 split per stage | Sourced: the gate file's own source (287.4 + 123.5 t and 75.2 + 32.3 t) |
| Propellant densities | Sourced (the session cites the source it uses) |
| Stage lengths | Recalled in the design as roughly 41 m and 14 m; to be confirmed against the source at implementation before they are marked sourced, otherwise `assumed: true` |
| Tank stations, dry-mass distribution | `assumed: true` |
| CG and inertia | Computed from a cylinder-tank model with settled propellant, on assumed stations: `assumed: true` |
| C_N_alpha(M), x_cp(M) | Barrowman from the geometry: `assumed: true` |
| Gimbal limit and rate, actuator lag | `assumed: true` |
| Controller gains (omega_n, zeta) | `assumed: true` |

Because the mass-property, aerodynamic-moment and actuator data are assumed, every
headline number of this phase is given with a sensitivity range.

### 5.7 Controller

- PD on the attitude error x_b x e_cmd, with e_cmd from the same S1/S2 steering laws
  evaluated on the 6-DOF state.
- Gains: K_p = (I_t omega_n^2 + M_alpha)/(T l_g), K_d = 2 zeta omega_n I_t/(T l_g),
  scheduled on I, T and q.
- omega_n about 2 rad/s and zeta = 0.7, both assumed, each with a +/-50% sensitivity.
- Saturation is smooth: delta_max tanh(.), so the right-hand side stays smooth.
- The 3-DOF thrust-direction step of about 1e-3 rad at kick end (SP3 risk 4) becomes a
  small step command here.

### 5.8 Silo and coast phases: the cold-start question

- On the track the attitude is rail-constrained: x_b = u, omega = Earth rate, zero
  tip-off. Optional sensitivity inputs: `tipoff_rate` and `alpha0`.
- A cold start coasts with no control authority from release until ignition, and with
  reduced authority during the thrust ramp. A hot start has authority at release.
- Reported for each silo run: the divergence time at release
  tau_div = sqrt(I_t/(q S C_N_alpha l)), the attitude error at ignition, the peak gimbal
  angle and the time in saturation.
- Rough estimate from the design: tau_div of about 9-14 s at 77 m/s at sea level, against
  a coast of 0.5 s and a 2 s ramp for the shipped cold start. The mass model must confirm
  it; it is not a result.
- The staging coast (11 s on the gate vehicle) has no reaction control; the attitude
  drift over it is reported.

### 5.9 Payload at 6-DOF (D-SP1-12)

- No 6-DOF search. Fly the 3-DOF-optimised (P*, delta, a, b).
- Report the insertion miss (dr, dv_r, di, e), gimbal peaks, true q-alpha and attitude
  error.
- Optional: re-solve delta and (a, b) through the same two inner-solve protocols and
  quote the residual-propellant difference as an estimated dP. It is labelled an estimate
  and is not a payload capacity.
- Headline comparison: fly the pad and the offloaded silo through S3 and compare their
  residual-propellant differences dm_res.

### 5.10 Outputs

The S1/S2 columns plus q0..q3, omega_b, alpha, gimbal angles, attitude error, x_cg and
I_t in the time series and events; a "6-DOF verification" block in the summary. New keys
and rows appear only on `rigid_6dof` runs.

### 5.11 Runtime (design estimates, to be measured)

Step cap 0.1 s; a fly-out takes 3-10 s; with the re-solve 1-2 min.

### 5.12 Attitude in the 3-D scene

SP4 draws the rocket along the thrust direction, a display convention. For a
`rigid_6dof` run the scene takes the body axis from the quaternion, shows the gimbal
angle on the plume, and adds alpha, attitude error and gimbal angle to the HUD. Visual QA
checks the drawn axis against q at sampled times.

Size estimate from the design: about 2,800 source lines, 2,200 test lines and 500 lines
of physics.md.

## 6. Inventory of the code this phase touches

Checked at commit 2eebcae on 2026-09-30, to be re-checked by the session before SP6.
Most of what SP6 builds on is created by SP3, SP4 and SP5; the second table lists it by
planned name.

### Exists at 2eebcae

- `src/launchsim/phases/engine.py`: `_ATOL_BY_SUFFIX` (80-86: `_m`, `_mps`, `_kg`, `_J`,
  `_rad`), `atol_for` (281; raises on an unknown suffix), `IntegratorSettings` (93),
  `EventSpec` (166), `PhaseSpec` (191), `integrate_phase` (390).
- `src/launchsim/vehicle.py` (673 lines): `Startup` (62), `Engine` (134), `Stage` (157),
  `ThrustSchedule` (223), `CdTable` (323), `DragModel` (395), `Vehicle` (475),
  `with_payload` (580), `with_stage_propellant` (595). It holds no lengths, diameters,
  stations, CG or inertia.
- `src/launchsim/config.py`: `Quantity` (160; the `source` or `assumed` rule),
  `AeroConfig` (245), `EngineConfig` (315), `StageConfig` (358), `VehicleConfig` (388),
  `DynamicsKind` (78). The 6-DOF data needs new, optional blocks that do not change how
  the existing vehicle files resolve.
- `configs/vehicles/generic_f9_class_2d.yaml` (the gate file, never edited): the LOX/RP-1
  split appears only inside source strings (lines 47 and 59); `reference_area_m2` 10.52
  from the 3.66 m body (84); stage-2 `coast_before_ignition_s` 11.0 (67).
- `src/launchsim/metrics_planar.py`: `q_alpha_pa_rad` (137) is q times psi, the angle
  between thrust and v_rel, not a true angle of attack; `felt_accel_g` (144).
- `src/launchsim/phases/prelude.py`: `fly_track` (483), `PreludeLayout` (403): the track
  stays 1-DOF; the 6-DOF layout adds the rail-constrained attitude at release.
- `src/launchsim/losses.py`: `loss_budget` (294), `rocket_equation_closure` (408).
- `src/launchsim/guidance.py`: `solve_delta_for_gamma` (367), `solve_ltg` (653) and the
  protocols `Stage1Flight` (304), `LtgShot` (495), used by the optional re-solve.

### Created by earlier phases (planned names; confirm at the fact-check)

| From | Item | SP6 use |
|---|---|---|
| SP3 | `phases/spatial.py` (`SpatialPlanner` and its model kit), `guidance3d.py`, `frames.py`, `dynamics3d.py` | `phases/rigid.py` reuses the kit; e_cmd comes from the same laws; prescribed-attitude mode is compared with them |
| SP3 | `metrics_spatial.py`, `sim_spatial.py`, the model set in `compare.py`, `results_io.py`, `summary.py`, `plots.py` | Fly-out metrics, the verification block, dispatch for `rigid_6dof` |
| SP5 | `earth.py` (`EarthModel`), `geodesy.py` | The fly-out runs on either Earth model |
| SP4 | The 3-D scene and its payload | Attitude from the quaternion (step V) |
| SP1, SP4, SP5 | The solved offload cases and their results directories | The offloaded silo fly-out |

### New in this phase

`src/launchsim/rigidbody.py`, `aero6.py`, `control.py`, `dynamics6.py`,
`phases/rigid.py`; `configs/vehicles/generic_f9_class_6dof.yaml`; an experiment file for
the fly-outs; tests; new docs/physics.md sections (rigid-body state and equations, mass
properties, aerodynamic moment, controller, the rail constraint and release, the 6-DOF
assumptions, the test-to-equation map).

## 7. Steps

Each step runs the loop of SESSION_PROTOCOL.md section 4: implementer, adversarial
reviewers (physics or numerics skeptic, CLAUDE.md compliance; honesty auditor for the
findings; visual-QA reviewer for step V), up to two fix rounds, independent gate, commit,
tracker update. Standing gate on every code step: fast suite green, ruff clean, 1-D
golden byte-identical, the planar, S1 and S2 pins passing; the full suite after every
step from S3.2 to S3.6. Test file names are left to the session.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| 0 | Session start: entry criteria, inventory re-check, Plan mode, open questions of section 10 put to the user | this file, TODO.md | fast suite | User approves the plan | [ ] | |
| S3.1 | Mass properties | `rigidbody.py` | Cylinder I_t = m (3 r^2 + L^2)/12; parallel axis; full and empty limits; smooth CG travel | All listed tests | [ ] | |
| S3.2 | Rotational core; `atol_for` gains quaternion and `_radps` suffixes | `dynamics6.py` (rotation), `phases/engine.py` | Torque-free precession rate (I_xx - I_t) omega_x/I_t at 1e-9 over 100 periods; inertial L and rotational energy drift < 1e-10; quaternion norm error < 1e-12; constant torque theta = 0.5 (M/I) t^2; jet-damping decay closed form | Listed tests; existing tolerances unchanged for every existing state name | [ ] | |
| S3.3 | Aerodynamic force and moment | `aero6.py` | Fixed-q rig: oscillation or divergence rate sqrt(q S C_N_alpha abs(x_cp - x_cg)/I_t) at 1e-6; alpha = 0 force equals the 3-DOF drag | All listed tests | [ ] | |
| S3.4 | Controller | `control.py` | Trim delta = q S C_N_alpha alpha (x_cp - x_cg)/(T l_g); step response omega_n and zeta | All listed tests | [ ] | |
| S3.5 | Full 6-DOF dynamics and planner (reuses the `SpatialPlanner` kit); rail constraint and release | `dynamics6.py`, `phases/rigid.py` | Prescribed-attitude mode (x_b = e_cmd, delta = 0, C_N_alpha = 0) reproduces S1/S2 at 1e-9; controlled limit (omega_n = 10 rad/s, C_N_alpha = 0): dr < 5 m, dv < 0.05 m/s, dm_res < 2 kg at MECO in magnitude, shrinking at least 2x per doubling of omega_n; loss identity < 1e-5 m/s | All listed tests | [ ] | |
| S3.6 | Fly-out pipeline, metrics, vehicle fork, config `rigid_6dof` | `sim_spatial.py` or a new run module, `metrics_spatial.py`, `config.py`, `results_io.py`, `summary.py`, `configs/vehicles/generic_f9_class_6dof.yaml` | Schema: every fork value has a source or `assumed`; `rigid_6dof` refused as a searched figure of merit; pipeline test on a short fly-out; existing vehicle files resolve unchanged | Listed tests; a fly-out from the CLI writes a complete results directory | [ ] | |
| S3.7 | Pad and silo fly-outs with sensitivities: experiment committed, run from the clean commit; findings note | `experiments/`, `docs/findings/`, README results | Experiment listed in the config test | No `bug_suspect`; every headline number has its sensitivity range; honesty review | [ ] | |
| V | Attitude in the 3-D scene from the quaternion; gimbal and alpha in the HUD | SP4's scene and payload | Payload tests (strict JSON, fields present); `node --check` | Visual QA: drawn axis equals q at sampled times | [ ] | |
| C | Close SP6: exit-criteria gate, demo recorded, status lines, CLAUDE.md layout, next phase chosen with the user and its file prepared, handoff and prompt, memory | docs/, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit | [ ] | |

## 8. Exit criteria

1. Mass properties pass their closed forms (cylinder inertia, parallel axis, full and
   empty limits) and the CG travel is smooth.
2. Rotational core: torque-free precession at 1e-9 over 100 periods; inertial angular
   momentum and rotational energy conserved to < 1e-10; quaternion norm error < 1e-12;
   the constant-torque and jet-damping closed forms pass.
3. Aerodynamics: the fixed-q oscillation or divergence rate matches its closed form at
   1e-6; the alpha = 0 force equals the 3-DOF drag.
4. Controller: the trim angle matches its closed form; the step response shows the set
   omega_n and zeta.
5. Prescribed-attitude mode reproduces S1 and S2 at 1e-9. The controlled limit converges
   toward the 3-DOF trajectory at least 2x per doubling of omega_n, with |dr| < 5 m,
   |dv| < 0.05 m/s and |dm_res| < 2 kg at MECO for omega_n = 10 rad/s, C_N_alpha = 0.
6. The loss identity closes to < 1e-5 m/s on a 6-DOF ascent.
7. The vehicle fork exists, every number in it has `source:` or `assumed: true`, the
   stage lengths are either confirmed against the source or marked assumed, and the gate
   vehicle file is unchanged (git diff).
8. `rigid_6dof` runs only as a fly-out: the config refuses it with a searched figure of
   merit.
9. Fly-outs of the pad and of the silo runs (full and offloaded) came from a committed
   experiment and a clean tree. For each: insertion miss (dr, dv_r, di, e), gimbal peak
   and time in saturation, true q-alpha, attitude error; for the silo runs also tau_div
   at release and the attitude error at ignition; the staging-coast drift.
10. The findings note presents the results as sensitivities (omega_n and zeta +/-50%,
    tip-off rate, alpha0, and the assumed aerodynamic and mass data), states what is
    assumed, says plainly whether the cold start stays controllable within those ranges,
    and passed the honesty review.
11. The 3-D scene shows the attitude from the quaternion for a `rigid_6dof` run, and
    visual QA passed.
12. Full suite green; ruff clean; all earlier pins unchanged; no new dependency;
    docs/physics.md updated.
13. Demo recorded under docs/demos/SP6/; the next phase agreed with the user (the board's
    "later" items) and its file, handoff, prompt and memory written.

## 9. Demo script

Output goes to docs/demos/SP6/ (text captures, screenshots, a short README with the
commit). File and test names are filled in by the session.

    uv run pytest -q -m "not slow"
    uv run pytest -q -k "rigidbody or aero6 or control or dynamics6 or rigid"
    uv run python -m launchsim run experiments/<6-DOF fly-out file>.yaml
    uv run python -m launchsim app

Look at:

- the test counts and the pins passing;
- `summary.md` of the fly-out run: the "6-DOF verification" block for the pad and for
  each silo run flown (insertion miss, gimbal peak, time in saturation, q-alpha, attitude
  error, tau_div, attitude error at ignition);
- the findings note: the cold-start controllability result with its sensitivity ranges
  and the list of assumed data;
- in the app: a `rigid_6dof` run in the 3-D scene, with the body axis and the gimballed
  plume during the coast before ignition, the kick and max-Q.

## 10. Risks and open questions

Open questions for Plan mode:

1. **How the results are published. Needs the user.** Recommended: as a findings note of
   sensitivities with ranges and an explicit list of assumed data, no single-number
   claims; D-SP1-12 already frames S3 as a verification. The alternative, holding the
   results back until better data exists, loses the cold-start answer the program asked
   for.
2. Which runs are flown. Recommended: pad, `silo_cold` full, `silo_cold` offloaded (the
   stage-1 headline), and `silo_hot_ramp_on_track` as the contrast with control authority
   at release.
3. Which Earth model the fly-outs use. Recommended: `wgs84_j2`, with the
   prescribed-attitude reproduction test on both S1 and S2.
4. Whether the optional re-solve of delta and (a, b) is run. Recommended: yes, for the
   pad and the offloaded silo only, quoted as an estimated dP.
5. Name and research question of the findings note. Proposed:
   `docs/findings/RQ2-cold-start-controllability-6dof.md`, with the verification block
   also summarised in `docs/findings/M2M-3d-vs-planar.md`.
6. The ranges for the assumed aerodynamic and mass data (C_N_alpha, x_cp, CG, I_t). The
   design fixes +/-50% only for omega_n and zeta; the session proposes the rest and marks
   them assumed.
7. What comes after SP6. **Needs the user.** The board lists README Phase 3 (which holds
   the structural-mass model that decides whether the headline survives), Phase 5 and
   Phase 6.

Risks:

1. The S3 data is mostly assumed. Mitigation: results as sensitivities, not predictions;
   every assumed value labelled in the fork and in the note.
2. Gimbal saturation makes the right-hand side non-smooth. Mitigation: tanh saturation
   and the 0.1 s step cap.
3. Stage lengths are recalled, not checked. Mitigation: confirm against the Falcon
   User's Guide at S3.6 or mark them assumed.
4. The vehicle is aerodynamically unstable when unpowered (the reason tau_div exists), so
   the cold-start coast and the staging coast diverge without control. That is the
   research output, not a defect; a large drift is reported, not tuned away with gains.
5. Controller gains chosen to make a run look good. Mitigation: gains are fixed by the
   stated omega_n and zeta before the fly-outs, committed with the experiment, and varied
   only in the declared sensitivity.
6. `atol_for` and the dispatch are shared, validated code. Mitigation: additive edits;
   the pins and the golden tier on every step.
7. A stiff controller with a 0.1 s step cap is slow or inaccurate at omega_n = 10 rad/s.
   Mitigation: the convergence test of S3.5 measures it; record the run time.
8. Linear aerodynamics outside its range. Mitigation: the |alpha| > 10 deg flag; a flagged
   run is reported as outside the model, not as a result.
9. The fly-out's insertion miss is read as a payload loss. Mitigation: the miss is
   reported as a miss; only the optional re-solve gives an estimated dP, labelled as an
   estimate.
10. Step V depends on SP4's scene, and the offloaded silo fly-out depends on a spatial
    offload run (SP4, or SP5 step R). Mitigation: if SP4 is not done, step V moves to the
    backlog and exit criterion 11 goes to the user as an open criterion; the offloaded
    case of exit criterion 9 goes to the user the same way.

## 11. Session log

(empty: phase not started)

## 12. Deviations from the plan

(none)

## 13. Prompt to start this phase

Draft, the previous session finalises it.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP6-3d-dynamics-s3-6dof.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links
> (docs/phases/inputs/2026-09-30-design-3d-dynamics.md first). Follow the session
> protocol. This session does phase SP6: stage S3 of true 3-D
> dynamics, a 6-DOF rigid body (quaternion attitude, body rates, gimbal with actuator
> lag, aerodynamic normal force and moment, jet damping, PD attitude controller) used as
> a verification fly-out of the payload and guidance the 3-DOF models optimised, not as a
> new search. Check the entry criteria and re-check the inventory in section 6, then
> start in Plan mode: confirm or refine steps S3.1 to S3.7 and the scene step, put the
> open questions of section 10 to me with your recommendation first, and show me the plan
> before writing code. Put the 6-DOF vehicle data in a new fork
> (configs/vehicles/generic_f9_class_6dof.yaml) with every number sourced or marked
> assumed; never edit the gate vehicle file. No planar, 1-D, S1 or S2 number may change;
> every new physics feature gets its closed-form test before any experiment uses it;
> docs/physics.md is updated in the same change as the equations. Fly the pad and the
> silo runs (full and offloaded), report insertion miss, gimbal peaks, true q-alpha and
> attitude error, and answer the cold-start question (no control authority between
> release and ignition) as sensitivities, stated plainly whichever way it comes out. Show
> the attitude in the 3-D scene. Keep the build-review-gate loop, commit at each gate,
> keep the trackers current, and close the phase with the demo, the handoff and the
> prompt for the phase we agree comes next.
