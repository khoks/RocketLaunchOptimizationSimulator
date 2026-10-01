# SP5: 3-D dynamics S2, oblate Earth (J2, ellipsoid)

Status: not started

Phase file of the program board ([README.md](README.md)). How a session runs:
[docs/process/SESSION_PROTOCOL.md](../process/SESSION_PROTOCOL.md). Written 2026-09-30 in
the SP1 session (step T) from the approved plan
([inputs/2026-09-30-SP1-approved-plan.md](inputs/2026-09-30-SP1-approved-plan.md)) and the
3-D design ([inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md),
sections S2, 5, 6 and 7). Nothing in this file has been built or run. The session before
SP5 re-checks sections 4, 6 and 13 against the code as it then is.

## 1. Goal and what you can see at the end

Build stage S2 of true 3-D dynamics: replace the spherical Earth of S1 by an Earth model
with the WGS-84 ellipsoid (geodetic altitude, ellipsoid normal as local up) and J2
gravity, keep the spherical model bit-identical, and measure what the oblate Earth does
to the payload capacity and to the headline offload.

At the end you can see:

- the new tests green (geodesy, gravity against its potential, orbit-rate closed forms,
  the zero-J2 and zero-flattening limit equal to S1), with every earlier pin unchanged;
- the model-to-model record extended with S2: payload capacity on the oblate model
  against S1 and planar, with the effect of flattening and of J2 separated (runs with
  flattening only, J2 only, and both);
- the stage-1 offload % on three models side by side: planar, S1 (sphere), S2 (oblate).

S2 gives new, different numbers by design. They are reported as model-to-model
differences. They never replace the planar gate, and a lower S2 payload is not a
re-calibration: nothing is tuned, and the accepted +14.3% miss is still stated against
the planar gate.

## 2. Scope and out of scope

In scope:

- `earth.py`: an `EarthModel` protocol with `SphericalEarth` (S1 runs stay bit-identical)
  and `EllipsoidJ2Earth`.
- `geodesy.py`: geodetic <-> ECEF conversion, geodetic altitude, ellipsoid normal.
- `constants.py`: J2 and the inverse flattening.
- The spatial planner, guidance, events and metrics moved onto `EarthModel`; config
  `earth: {model: wgs84_j2}` accepted.
- The target definition under J2 (D-SP1-11), stated in the assumptions.
- Decomposition runs (flattening only, J2 only, both) and the extended model-to-model
  record.
- The offload re-check on `wgs84_j2`, pre-registered, with an honesty review.
- docs/physics.md updated in the same change as each of the above.

Out of scope:

- Gravity terms beyond J2 (J3, J4, tesserals), third bodies, a latitude-dependent
  atmosphere, wind.
- Mean-element orbit targets; inclination or plane targeting (both deferred by the
  design).
- 6-DOF: SP6. New scene work beyond checking that the app's scenes read a `wgs84_j2`
  run (the globe stays a sphere on screen; the 21 km of flattening is not visible at
  that scale).
- Any change to a planar, 1-D or S1 number.

## 3. Decisions already taken

Cited by id; the text is in TODO.md's decisions log.

- D-SP1-01: three validated stages; this phase is S2.
- D-SP1-11: under J2 the default target is an osculating circular orbit at geocentric
  R_E + 200 km at cutoff; it is to be revisited in this phase (section 10, question 1).
- D-SP1-03, D-SP1-04, D-SP1-10: the offload semantics, the penalty rows and the pad
  control, as on the planar model.
- D-SP1-09: the offload is an `offload:` block and a post-pass; no budget id changes.
  That the solver is built from a problem factory against `RecordingProblem`, so a spatial
  search context can be passed in, is not a numbered decision: it is step 5 of the
  approved plan and section 5.4 of the SP1 phase file.
- D-SP1-07, D-SP1-08: order and way of working.
- From Phase 2 (legacy ids in TODO.md): the calibration miss is accepted and is not
  re-opened by S2.

## 4. Entry criteria

1. SP3 is "done" on the program board (the physics SP5 extends). In the planned order SP4
   is also done; SP5 uses SP4's spatial offload experiment file and 3-D findings note. If
   SP5 runs before SP4, the offload re-check (step R) moves to whichever of the two runs
   later, and that is logged as a decision.
2. Clean tree; HEAD is the bookkeeping commit that follows the closing commit the handoff
   names (SESSION_PROTOCOL.md section 3, item 3).
3. Fast suite green; ruff clean; the 1-D golden tier, SP1's planar digest pin and SP3's
   `tests/test_golden_planar.py` pass.
4. SP3's S1 tests pass, and `docs/findings/M2M-3d-vs-planar.md` exists with the S1 record
   and no open `bug_suspect`.
5. If SP4 is done: the offload on S1 (SP4) is on record, with its results directory named
   in the handoff. If SP4 is not done, this criterion does not apply and step R is
   deferred per criterion 1.
6. Section 6 of this file has been re-checked at the current HEAD: the spatial modules
   named there are created by SP3 and may differ from the design's names.

## 5. Design

The full design is in
[inputs/2026-09-30-design-3d-dynamics.md](inputs/2026-09-30-design-3d-dynamics.md). This
section keeps its content for S2.

Rules from CLAUDE.md that govern the phase:

- Plan mode is required for anything touching equations of motion, frames, events,
  integrator settings or loss accounting, with docs/physics.md updated in the same change.
  Every step from S2.1 to S2.4 does that.
- No planar or 1-D number may change, and here no S1 number either. Pin tests come first:
  an S1 pin is written and committed on the untouched S1 code before the planner is moved
  onto `EarthModel` (step S2.0).
- Every new physics feature needs its closed-form test before any experiment uses it. The
  decomposition runs (S2.5) and the offload run (R) come after S2.1 to S2.4 pass.

### 5.1 Earth model and constants

- `earth.py` holds the `EarthModel` protocol: gravity acceleration at an ECI or ECEF
  position, altitude above the surface, local up, site position and velocity, the track's
  effective gravity.
- `SphericalEarth` reproduces S1 exactly. `EllipsoidJ2Earth` takes J2 and the flattening;
  `EllipsoidJ2Earth(0, 0)` must reduce to S1.
- `constants.py` gains J2 = 1.08262668e-3 and 1/f = 298.257223563. The existing mu, R_E
  and omega_E are already the WGS-84 values. constants.py stays the only place Earth
  constants are defined.

### 5.2 Gravity with J2

With R = R_E, r = |r| and z along the spin axis:

    a_x = -mu x/r^3 [1 + 1.5 J2 (R/r)^2 (1 - 5 z^2/r^2)]
    a_y = -mu y/r^3 [1 + 1.5 J2 (R/r)^2 (1 - 5 z^2/r^2)]
    a_z = -mu z/r^3 [1 + 1.5 J2 (R/r)^2 (3 - 5 z^2/r^2)]

The test types the potential U independently and checks a = -grad U by finite
differences.

### 5.3 Geodesy, altitude and local up

- `geodesy.py`: geodetic <-> ECEF, with a smooth fixed-iteration or closed-form inverse.
  A data-dependent iteration count would put steps into the right-hand side and is not
  allowed.
- Altitude for the atmosphere, the ground event and the fairing rule is geodetic h.
- u is the ellipsoid normal for the rise, the kick and gamma_rel, so dh/dt = v_rel . u
  exactly. Stage 2 and the target keep geocentric r_hat.
- Site latitude is geodetic. The same number therefore means a different point than in
  S1; this is stated in the assumptions.
- Track gravity: g_track = -(g_J2(r_site) - omega x (omega x r_site)) . u, about
  9.792 m/s^2 at 28.5 deg (design estimate), against 9.7720917 m/s^2 in S1 and planar.

### 5.4 Target under J2 (D-SP1-11)

- Default: osculating two-body a = r_t and e = 0 at cutoff, with r_t = R_E + h_t
  geocentric. Chosen for comparability with planar and S1.
- The geodetic altitude at insertion is reported beside it.
- After cutoff the orbit oscillates at order J2. Mean-element targets are deferred.
- The assumptions list says which "200 km" is meant.

### 5.5 Loss identity

Unchanged in form (SP3 section 5.5): dV/dt = v_rel_hat . (a_thrust + a_aero)
+ v_rel_hat . g_eff with g_eff = g(r) - omega x (omega x r), valid for any g. In S2,
g_up = -g_eff . u with u the ellipsoid normal, and the lateral gravity row holds the
rest. The gate is the same: closure below 1e-5 m/s.

### 5.6 Model-to-model expectation and decomposition

- Hand estimate from the design: S2 payload capacity lower than S1 by roughly 50 to
  100 kg (-0.2 to -0.4%). Two reasons: for a geocentric target radius the site sits about
  4.8 km deeper, and surface gravity at the site is about 0.2% higher.
- This is an estimate to be decomposed, not a target. It is written into TODO.md and
  committed in step S2.0, with the S1 pin and before any spatial module is edited. That
  is before every searched S2 run, including those inside the tests of S2.4 (the zero
  limit within 1 kg in P*, the convergence test), which come before the decomposition
  runs. The estimate has also been on record in this file since the SP1 step-T commit.
  S2.5 then runs three cases against S1:
  flattening only, J2 only, both. The record states each difference, whether the two
  single effects add up to the combined one, and the loss rows that carry them.
- If the measured difference falls outside the estimate, the note says so and explains it
  from the rows. Nothing is adjusted to meet it.
- No tuning and no new fitted parameter, so no new calibration.

### 5.7 The offload re-check on `wgs84_j2`

- Experiment: SP4's spatial offload file copied with `earth: {model: wgs84_j2}`, the same
  vehicle and shared blocks, committed before any run.
- Reference payload: the `wgs84_j2` pad's own payload capacity (D-SP1-03: the full-load
  pad on the same vehicle and orbit, in the same model).
- Reported: stage-1 offload in tonnes, % of stage-1 and % of total propellant on planar,
  S1 and S2, with the pad controls, the penalty rows, the decomposition residual and the
  caveats that travel with the planar number.
- The session pre-registers its expectation for the offload difference before the run,
  built from the measured S2 payload difference and SP1's solved marginal rate.

### 5.8 Outputs

Geodetic lat, lon and alt in the time series and events; geodetic altitude at insertion,
the Earth model name, and the model-to-model deltas in the summary. New keys and rows
appear only on spatial runs.

### 5.9 Runtime (design estimates, to be measured)

About 20 microseconds per RHS call and 15-25 s per searched run, against about 15
microseconds and 12-18 s estimated for S1. The 2 s flight step cap is kept.

### 5.10 Deferred

Mean-element targets, inclination and plane targeting, higher gravity terms, wind.

Size estimate from the design: about 900 source lines, 1,200 test lines and 300 lines of
physics.md.

## 6. Inventory of the code this phase touches

Checked at commit 2eebcae on 2026-09-30, to be re-checked by the session before SP5.
Most of what SP5 edits is created by SP3; the second table lists it by planned name.

### Exists at 2eebcae

- `src/launchsim/constants.py` (42 lines): `MU_EARTH_M3S2` (7), `R_EARTH_M` (10),
  `OMEGA_EARTH_RADS` (13), `V_REL_EPS_MPS` (34), `ALT_AMBIANCE_MIN_M` = -5,004 m (37).
  `tests/test_constants.py` asserts the documented literals; the two new constants get
  the same treatment.
- `src/launchsim/dynamics.py`: `Gravity` protocol (50), `InverseSquareGravity` (63),
  `g_eff_track` (114), `planar_rotation_rate` (103; its docstring already calls the
  latitude geodetic).
- `src/launchsim/atmosphere.py`: `ambient_scalar(alt_m)` (303), the scalar entry the
  flight RHS uses; valid from -5,004 m, which bounds the geodesy round-trip range
  (-5 km to 1,000 km).
- `src/launchsim/phases/engine.py`: `ev_ground(model, z_ground_m)` (700), which takes
  altitude from the dynamics model.
- `src/launchsim/phases/planar.py`: the fairing heating rule `fmh_rate_W_m2` (462) and
  `ev_fmh` (509), which the spatial copy mirrors and which then read geodetic altitude.
- `src/launchsim/orbit.py`: `TargetOrbit` (20; a radius), `orbit_elements` (95).
- `src/launchsim/config.py`: `TargetOrbitConfig` (719; `altitude_km`, property
  `radius_m`), `PlanarSiteConfig` (476).

### Created by earlier phases (planned names; confirm at the fact-check)

| From | Item | SP5 change |
|---|---|---|
| SP3 | `frames.py` | Site position and local frames take an `EarthModel` |
| SP3 | `dynamics3d.py` | Gravity and altitude come from the `EarthModel`; the RHS stays scalar-float |
| SP3 | `guidance3d.py`, the four spatial events | u from the model (ellipsoid normal) for rise, kick, gamma_rel |
| SP3 | `phases/spatial.py` (`SpatialPlanner`, release map, prelude layout) | Built on the model kit; g_track from the model |
| SP3 | `metrics_spatial.py`, `sim_spatial.py`, `search_spatial.py` | Geodetic columns; model name; assumptions |
| SP3 | `config.py`: `earth: {model: spherical or wgs84_j2}` | `wgs84_j2` accepted; decomposition switches (question 2) |
| SP3 | `orbit3d.py` | Unchanged; osculating elements at cutoff |
| SP3 | `docs/findings/M2M-3d-vs-planar.md` | Extended with the S2 rows |
| SP4 | The spatial offload experiment and the 3-D offload findings note | Copied to `wgs84_j2`; note extended |

### docs/physics.md

New sections for the Earth model, geodesy, J2 gravity and its potential, the target under
J2, and the S2 assumptions, beside the 3-D sections SP3 adds; the test-to-equation map
(heading at line 4796 at 2eebcae) gains the S2 tests.

## 7. Steps

Each step runs the loop of SESSION_PROTOCOL.md section 4: implementer, adversarial
reviewers (physics or numerics skeptic, CLAUDE.md compliance; honesty auditor for the
record and the findings), up to two fix rounds, independent gate, commit, tracker update.
Standing gate on every code step: fast suite green, ruff clean, 1-D golden
byte-identical, the planar pins and the S1 pin passing; the full suite after every step
from S2.1 to S2.4. Step S2.0 is taken out of the design's S2.4 so that the pin exists
first. Test file names are left to the session.

| # | Step | Main files | Tests | Gate | Status | Commit |
|---|---|---|---|---|---|---|
| 0 | Session start: entry criteria, inventory re-check, Plan mode, open questions of section 10 put to the user | this file, TODO.md | fast suite | User approves the plan | [ ] | |
| S2.0 | S1 pin, test only: S1 payload capacity, guidance parameters, loss rows and cutoff state of the model-to-model cases. The S2 expectation (section 5.6) is written into TODO.md in the same commit | tests/, TODO.md | the pin itself | Passes on the untouched tree; pin and expectation committed before any spatial module is edited | [ ] | |
| S2.1 | Geodesy | `geodesy.py` | Round trip < 1e-7 m and 1e-14 rad over -5 km to 1,000 km at all latitudes; grad h equals the normal by finite differences | All listed tests | [ ] | |
| S2.2 | J2 gravity and constants | `earth.py`, `constants.py` | a = -grad U by finite differences against a potential typed in the test; E = v^2/2 + U and h_z drift < 1e-8 over 10 revs (a = 10,000 km, e = 0.3, i = 50 deg); nodal rate -1.5 J2 n (R/p)^2 cos i and apsidal rate 0.75 J2 n (R/p)^2 (5 cos^2 i - 1) within 1%; a polar orbit's node fixed to 1e-10 rad; apsidal rate about 0 at 63.435 deg | All listed tests | [ ] | |
| S2.3 | Surface consistency | `earth.py`, `frames.py` | Gravity along the normal against Somigliana within 2e-4 m/s^2 at 0, 28.5, 45 and 90 deg; horizontal residual < 2e-4 m/s^2; the released-at-rest test of S1.4 with g_ref | All listed tests | [ ] | |
| S2.4 | Planner and metrics on `EarthModel`; `wgs84_j2` accepted in config | `phases/spatial.py`, `dynamics3d.py`, `guidance3d.py`, `metrics_spatial.py`, `sim_spatial.py`, `config.py` | `EllipsoidJ2Earth(0, 0)` matches S1 at 1e-9 relative at fixed guidance and within 1 kg in P*; loss identity < 1e-5 m/s; convergence < 0.1% | Listed tests; the S1 pin of S2.0 bit-identical | [ ] | |
| S2.5 | Decomposition runs (flattening only, J2 only, both): experiment file committed, run from the clean commit, record extended. The expectation was committed in S2.0 | `experiments/`, `docs/findings/M2M-3d-vs-planar.md`, TODO.md | Experiment listed in the config test | The expectation commit (S2.0) precedes the commit that makes `wgs84_j2` runnable (S2.4), and so every searched S2 run (git log); no `bug_suspect`; each difference stated with its loss rows; honesty review | [ ] | |
| R | Offload re-check on `wgs84_j2`: experiment copied and committed with the session's expectation; run; findings note with planar, S1 and S2 side by side | `experiments/`, `docs/findings/`, README results | Small-grid end-to-end offload on a `wgs84_j2` experiment | No `bug_suspect`; pad control about 0 for stage 1; reference payload reproduced; honesty review | [ ] | |
| C | Close SP5: exit-criteria gate, demo recorded, status lines, CLAUDE.md layout and constants note, SP6 phase file fact-checked, handoff and prompt, memory | docs/, TODO.md, CLAUDE.md, README.md, memory | full suite | Independent gate; final commit | [ ] | |

The Somigliana tolerance of S2.3 is set by the missing J4 term: the design estimates the
gap at 4e-5 m/s^2 at the equator and 1.2e-4 m/s^2 at the pole. The Somigliana constants
are typed in the test with their source, not added to the library.

## 8. Exit criteria

1. An S1 pin was committed before the first commit that edits a spatial module in this
   phase (git log) and is bit-identical at the closing commit; the 1-D golden tier and
   the planar pins are unchanged.
2. Geodesy: round trip < 1e-7 m and 1e-14 rad over -5 km to 1,000 km at all latitudes;
   grad h equals the ellipsoid normal.
3. Gravity: a = -grad U; energy with the J2 potential and h_z conserved to < 1e-8 over 10
   revolutions; nodal and apsidal rates within 1% of the first-order closed forms; the
   polar-orbit node fixed to 1e-10 rad; the apsidal rate about 0 at 63.435 deg.
4. Surface gravity along the normal agrees with Somigliana within 2e-4 m/s^2 at 0, 28.5,
   45 and 90 deg; the horizontal residual is below 2e-4 m/s^2; the released-at-rest test
   passes.
5. The zero-J2, zero-flattening limit equals S1: 1e-9 relative at fixed guidance and
   within 1 kg in payload capacity.
6. The loss identity closes to < 1e-5 m/s on a `wgs84_j2` ascent; tightening tolerances
   10x moves payload and margins by < 0.1%.
7. The target definition (D-SP1-11, as confirmed or changed in Plan mode) and the meaning
   of the site latitude are in the run assumptions and in docs/physics.md; the geodetic
   altitude at insertion is reported.
8. The S2 expectation (-50 to -100 kg, hand estimate) is in TODO.md in a commit that
   precedes the first commit that makes `wgs84_j2` runnable (S2.4; checked in git log),
   and so every searched S2 run; the record states the measured differences for
   flattening only, J2 only and both, with their loss rows, and passed the honesty review.
9. The offload on `wgs84_j2` came from a committed file and a clean tree, with no
   `bug_suspect`; the findings note gives the stage-1 offload % on planar, S1 and S2 with
   the caveats beside the numbers.
10. Full suite green; ruff clean; no new dependency; docs/physics.md updated.
11. Demo recorded under docs/demos/SP5/; SP6's phase file fact-checked; handoff, prompt
    and memory written.

## 9. Demo script

Output goes to docs/demos/SP5/ (text captures and a short README with the commit). File
and test names are filled in by the session.

    uv run pytest -q -m "not slow"
    uv run pytest -q -k "geodesy or earth or j2"
    uv run python -m launchsim run experiments/<S2 decomposition file>.yaml
    uv run python -m launchsim run experiments/<wgs84_j2 offload file>.yaml

Look at:

- the test counts and the pins passing;
- `summary.md` of the decomposition run: payload capacity for flattening only, J2 only
  and both against S1; geodetic altitude at insertion; the gravity rows;
- `docs/findings/M2M-3d-vs-planar.md`: the S2 rows next to the estimate written before
  the run;
- the offload findings note: stage-1 offload % on planar, S1 and S2;
- optionally, the `wgs84_j2` run opened in the app's 3-D scene.

## 10. Risks and open questions

Open questions for Plan mode:

1. **The target under J2. Needs the user** (D-SP1-11 says to revisit it here).
   Recommended: keep the default, an osculating circular orbit at geocentric
   R_E + 200 km at cutoff, because it compares directly with planar and S1; report the
   geodetic altitude at insertion beside it. The alternative, a geodetic 200 km altitude
   at insertion, changes the target radius by a few km depending on the insertion
   latitude and makes the model-to-model difference harder to read.
2. How the decomposition cases are written in config. Recommended: two switches on the
   `wgs84_j2` model (J2 on or off, flattening on or off, both on by default), so no
   number is typed into an experiment file; used only by the decomposition experiment.
3. Whether the offload sweeps are re-run on S2 or only the run block. Recommended: the
   run block; sweeps go to the backlog unless the S2 difference is large.
4. Whether `wgs84_j2` becomes the default for later spatial experiments. Recommended: no
   default; every spatial experiment states its Earth model.

Risks:

1. Ambiguity of "200 km" under S2. Mitigation: D-SP1-11 and question 1; stated in the
   assumptions; geodetic altitude reported.
2. The site latitude means a different point than in S1. Mitigation: stated in the
   assumptions; the flattening-only run isolates it.
3. A non-smooth geodetic inverse disturbs the integrator and the convergence test.
   Mitigation: fixed-iteration or closed-form inverse; the round-trip and convergence
   gates.
4. Two different "up" directions: the ellipsoid normal on stage 1 and geocentric r_hat on
   stage 2 and at the target. They differ by about 0.003 rad at 28.5 deg (estimate,
   f sin(2 lat)). Mitigation: documented; the handover and the gamma* solve are tested;
   the gamma_MECO(delta) scan of SP3 is repeated on S2.
5. The decomposition is not exactly additive. Mitigation: report the interaction term
   instead of forcing a sum.
6. A lower S2 payload read as a better calibration. It is not one. Mitigation: the note
   keeps the +14.3% statement against the planar gate and labels the S2 number a
   model-to-model difference.
7. Shared-module edits move earlier numbers. Mitigation: S2.0; `SphericalEarth` as the
   default path; additive edits.
8. Run time grows (section 5.9). Mitigation: measure after S2.4 and record it.
9. The missing J4 limits the surface-gravity check to 2e-4 m/s^2. Mitigation: stated in
   the test and in the assumptions; higher terms are out of scope.

## 11. Session log

(empty: phase not started)

## 12. Deviations from the plan

(none)

## 13. Prompt to start this phase

Draft, the previous session finalises it.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP5-3d-dynamics-s2-oblate.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links
> (docs/phases/inputs/2026-09-30-design-3d-dynamics.md first). Follow the session
> protocol. This session does phase SP5: stage S2 of true 3-D
> dynamics, an oblate Earth (WGS-84 ellipsoid with J2 gravity, geodetic altitude and
> local up) behind an EarthModel protocol, with the spherical model kept bit-identical.
> Check the entry criteria and re-check the inventory in section 6, then start in Plan
> mode: confirm or refine steps S2.0 to S2.5 and the offload re-check, ask me to confirm
> the target definition under J2 (D-SP1-11; your recommendation first), and show me the
> plan before writing code. Pin S1 before editing any spatial module; no planar, 1-D or
> S1 number may change; every new physics feature gets its closed-form test before any
> experiment uses it; docs/physics.md is updated in the same change as the equations.
> Write the expected payload difference (-50 to -100 kg, a hand estimate to be
> decomposed, not tuned) into TODO.md and commit it with the S1 pin (S2.0), before any
> spatial module is edited and so before any searched S2 run. After S2.1 to S2.4 pass,
> run the flattening-only, J2-only and combined cases, extend
> docs/findings/M2M-3d-vs-planar.md, and re-check the fuel offload on wgs84_j2 so the
> offload % is reported on planar, S1 and S2. Keep the build-review-gate loop, commit at
> each gate, keep the trackers current, and close the phase with the demo, the SP6 phase
> file fact-checked, the handoff and the prompt for SP6.
