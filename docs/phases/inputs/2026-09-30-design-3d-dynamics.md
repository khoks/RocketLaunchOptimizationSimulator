# Design input: true 3-D dynamics in three stages (SP3, SP5, SP6; 3-D scene in SP4)

Produced in the SP1 planning session on 2026-09-30 by a read-only design agent and checked
against the code at commit 2eebcae. Nothing was edited or run for it. Line numbers refer
to that commit; re-check before relying on one. Input to the phase files SP3, SP4, SP5 and
SP6 under docs/phases/.

User decisions behind it (2026-09-30): true 3-D dynamics, "full fledged", built in three
validated stages: S1 3-DOF point mass over a rotating sphere; S2 oblate Earth (J2,
ellipsoid); S3 6-DOF rigid body. Order: after the planar fuel-offload findings (SP1) and
the local app with the 2-D scene (SP2).

## 0. Coupling to the planar layout (verified in code)

| Module | Reusable as is | Bound to the planar layout |
|---|---|---|
| `src\launchsim\search.py` | `optimise_gamma`, `payload_root`, `final_verify`, `run_search`: they see only the `SearchProblem`/`RecordingProblem` protocols (460-495) | `SearchContext` (502-711) and test-only `joint_root_crosscheck`; `Stage2Result`/`KickPoint` appear only as annotations |
| `src\launchsim\guidance.py` | `solve_delta_for_gamma`, `solve_ltg`, `GuidanceSpec`, `LtgSettings`, guess ladder, `GuidanceFailure` | All steering laws: they return `(e_r, e_theta)` from `PlanarKinematics` |
| `src\launchsim\phases\engine.py` | `integrate_phase`, `ev_ground(model)`, `ev_propellant(layout)`, `ev_time` | `ev_radial_apex/turnaround` (need `v_r_mps`), `ev_kick_start`, `ev_kick_aligned`; `atol_for` rejects unknown suffixes |
| `src\launchsim\phases\prelude.py` | Hold and `fly_track` via `PreludeLayout` and a `g_eff_mps2` argument | Nothing |
| `src\launchsim\phases\planar.py` | The state-machine structure only | No hooks: module-level `PLANAR_LAYOUT` indices, `rhs_planar`, `PlanarEnvironment` throughout |
| `src\launchsim\losses.py` | `loss_budget(phases, layout, speed)`, `rocket_equation_closure(trace, vehicle, layout)` | `pointwise_dVdt` |
| `src\launchsim\metrics_planar.py` | `scan_peak`, `max_q`, `search_metrics`, `closure_metrics`, `loss_items`, `unwrap_rad` (about a third) | Sampling, rows, felt loads |
| `sim.py`, `compare.py`, `results_io.py`, `summary.py`, `plots.py`, `cli.py` | Structure | About 12 branches on `== PLANAR_2D`; `compare.MatchedRun` carries `omega_p_rads` and builds `PlanarDynamics2D` (589, 613, 802, 931) |

Search and both inner solves are reused unchanged. The planner, laws, four events, metrics
and run assembly are written new. Recommendation: copy the planner rather than refactor
`planar.py`, so planar numbers cannot move. Write the new `SpatialPlanner` against a small
model kit (layout, rhs, kinematics, law and event factories) so S2 and S3 reuse it.
Porting planar onto that kit is deferred.

**Module layout (new files):** `frames.py`, `dynamics3d.py`, `guidance3d.py`, `orbit3d.py`,
`phases\spatial.py`, `search_spatial.py`, `metrics_spatial.py`, `sim_spatial.py`; S2 adds
`geodesy.py`, `earth.py`; S3 adds `rigidbody.py`, `aero6.py`, `control.py`, `dynamics6.py`,
`phases\rigid.py`.

**Config:** `dynamics: spatial_3d` with `earth: {model: spherical | wgs84_j2}`, and
`dynamics: rigid_6dof` as a fly-out only. The existing `guidance`, `search`,
`target_orbit`, `checks` blocks are reused. `site.longitude_deg` is added for display
only. No new dependency.

## S1. 3-DOF over a rotating sphere (SP3)

**Frames and state.** ECI Cartesian, Z on the spin axis, coincident with ECEF at run clock
t = 0. Cartesian has no pole or V = 0 singularity, takes J2 as one extra term, is what
6-DOF needs, and makes the reduction to the polar planar model an independent check.

- State: `[rx_m, ry_m, rz_m, vx_mps, vy_mps, vz_mps, m_kg, J_vac, J_grav, J_grav_lat,
  J_alt, J_drag, J_steer, J_bp]`.
- Local frame: u = r_hat, e_E = z x u / |z x u|, n = u x e_E.

**Equations of motion.**

- r' = v; v' = -mu r/|r|^3 + (T e - D v_rel_hat)/m; m' = -T_vac/c.
- v_rel = v - omega_E z x r; h = |r| - R_E; (p, rho, a) = atm(h);
  D = 0.5 rho V^2 C_D(M) A_ref; T = max(0, T_vac - p A_e).

**Loss identity (also valid for S2 and S3).** Since v_rel . (omega x v_rel) = 0:

- dV/dt = v_rel_hat . (a_thrust + a_aero) + v_rel_hat . g_eff, with
  g_eff = g(r) - omega x (omega x r). This holds for any g, including J2.
- Rates: J_vac' = T_vac/m; J_drag' = D/m; J_steer' = (T/m)(1 - e . v_rel_hat);
  J_bp' = (T_vac - T)/m; J_grav' = -g_eff . v_rel_hat.
- Split of gravity: g_up = -g_eff . u (in S1, mu/r^2 - omega_E^2 r cos^2(lat)).
  J_grav' = g_up sin(gamma_rel) + J_grav_lat', where sin(gamma_rel) = v_rel_hat . u and
  J_grav_lat' = -g_eff,horizontal . v_rel_hat. J_alt' = (g_up - g_ref) sin(gamma_rel).
- V < 1e-9 m/s: v_rel_hat := u.
- Comparison rows: planar gravity <-> J_grav total, with the lateral part shown beside it;
  the other rows map one to one.
- Expected row differences at 28.5 deg east: V_f differs by
  omega^2 r^2 (cos^2(lat_f) - cos^2(i))/(2V), about 0.2-0.4 m/s, and the gravity row
  absorbs it.

**Release map and track.**

- Site position: r_site(t) = (R_E + z)[cos(lat) cos(lon + omega_E t),
  cos(lat) sin(lon + omega_E t), sin(lat)].
- Vertical exit: v = s' u + omega x r, so v_rel = s' u exactly. The general tilted form is
  r = r_site + x_e d_az + z_e u, v = s'(cos(phi_t) d_az + sin(phi_t) u) + omega x r
  (Phase 3 seam).
- Track and hold stay 1-DOF with g_track = mu/R_E^2 - omega_E^2 R_E cos^2(lat),
  independent of azimuth. Computing it as `g_eff_track(omega_E cos(lat))` makes it
  bit-equal to the planar value at az 90 deg (9.7720917 m/s^2 at 28.5 deg).
- Neglected on the track and listed in assumptions: Coriolis 2 omega_E s' cos(lat)
  (0.0098 m/s^2 at 77 m/s), the horizontal centrifugal omega_E^2 R_E sin(lat) cos(lat)
  (0.0142 m/s^2 at 28.5 deg, a rail side load of 0.0014 g), and gravity variation over the
  stroke.

**Guidance.**

- Launch plane: n_p = r_fs_hat x d_az at the flight start, fixed inertially;
  theta_hat = n_p x u normalised. Pitch is the thrust elevation above local horizontal;
  yaw is the angle out of that plane.
- Rise: e = u. Kick: e = cos(delta) u + sin(delta) theta_hat.
- Kick end: (u_h cos(delta) - w sin(delta))/V crosses zero upward, with w = v_rel . u and
  u_h = v_rel . theta_hat.
- Gravity turn: e = v_rel_hat as a full vector.
- gamma_rel for the inner solve: atan2(w, s |v_rel,h|) with s = sign(v_rel . theta_hat).
  This keeps the planar range (-pi, pi], so the timeout and impact sentinels still work.
- Stage 2: plane normal frozen from r x v at stage-2 ignition;
  e = (s r_hat + theta_2)/sqrt(1 + s^2), s = a - b tau, zero yaw.
- Target: r = r_t, v_r = 0, E = -mu/(2 r_t), inclination free and reported.
  `Handover.gamma_meco_rad` and `Stage2Result.{r_cut_m, v_r_cut_mps, tau_cut_s}` satisfy
  the existing protocols, so both solves and `run_search` run unchanged.
- Inclination targeting with yaw is deferred (S1b): it needs a 3x3 shooting or an azimuth
  outer solve, and the headline case does not need it.

**Orbit (`orbit3d.py`).** h = r x v, i = acos(h_z/|h|), node angle in the epoch frame
(`raan_epoch_rad`, since there is no sidereal epoch), argument of latitude. a, e, r_p, r_a
come from the existing `orbit_elements(|r|, r_hat . v, |h|/|r|, mu)`.

**Steps.**

1. **S1.0 Planar pin (test only).** `tests\test_golden_planar.py` pins the gate pad and
   silo_cold P*, delta, (a, b), loss rows and cutoff state. Gate: passes on the untouched
   tree.
2. **S1.1 `frames.py` and `orbit3d.py`.** Tests: element round trip at 1e-12; v_rel
   against a finite-differenced ECEF position; pad release speed 465.10 m/s at the equator
   and 465.10 cos(lat) at latitude (408.74 at 28.5 deg), due east; vacuum inclination
   closed form cos i = cos(lat) sin(beta_inertial).
3. **S1.2 `dynamics3d.py`** (scalar-float RHS, no numpy cross products). Tests:
   - Inclined e = 0.3 orbit, 10 revs: energy, each component of h, and the eccentricity
     vector drift < 1e-8; period matches 2 pi sqrt(a^3/mu).
   - 500 seeded states at 1e-12: rows equal `rhs_planar` after transformation on the
     equator, and pointwise dV/dt closes.
   - Vacuum coast energy.
4. **S1.3 `guidance3d.py` and the four events.** Tests: laws reduce to the planar tuples;
   the kick event equals the planar function.
5. **S1.4 `phases\spatial.py`** (planner, release map, prelude layout). Tests:
   - Hold consistency: a point released at rest accelerates at g_eff, whose up-component
     equals the prelude's g_ref.
   - Equatorial east, fixed (delta, a, b), rtol 1e-12: same event sequence as
     `PlanarPlanner`; r, v_r, v_theta, m and all J within 1e-9 relative at MECO and
     cutoff; event times within 1e-8 s; |z| < 1e-6 m.
   - 28.5 deg az 90 deg in vacuum with in-plane laws only: equals planar at 1e-9 and
     i = 28.5 deg at 1e-12.
6. **S1.5 `search_spatial.py`** (`SpatialSearchContext`). Slow tests: equatorial-east P*
   within 1 kg of planar; gamma_MECO(delta) monotone scan.
7. **S1.6 `metrics_spatial.py`, `sim_spatial.py`, dispatch in `sim.run`, config literal.**
   Tests: loss identity < 1e-5 m/s at 28.5/90 and at 45/45; rocket-equation closure;
   convergence < 0.1%.
8. **S1.7 Reporting generalisation** in `compare.py`, `results_io.py`, `summary.py`,
   `plots.py`: a model set instead of `== PLANAR_2D`; `MatchedRun` takes layout and speed.
   Gate: S1.0 pin and the 1-D golden are byte-identical.
9. **S1.8 Model-to-model record** (section 5). `docs\physics.md` is updated in every step.

## S2. Oblate Earth (SP5)

**Model.** `earth.py` holds an `EarthModel` protocol with `SphericalEarth` (S1 runs stay
bit-identical) and `EllipsoidJ2Earth`. `constants.py` gains J2 = 1.08262668e-3 and
1/f = 298.257223563; the existing mu, R_E and omega_E are already the WGS-84 values.

- Gravity: a_x,y = -mu (x,y)/r^3 [1 + 1.5 J2 (R/r)^2 (1 - 5 z^2/r^2)];
  a_z = -mu z/r^3 [1 + 1.5 J2 (R/r)^2 (3 - 5 z^2/r^2)].
- `geodesy.py`: geodetic <-> ECEF with a smooth fixed-iteration or closed-form inverse.
  Altitude for the atmosphere, ground and fairing rule is geodetic h.
- u is the ellipsoid normal for the rise, kick and gamma_rel, so dh/dt = v_rel . u
  exactly. Stage 2 and the target keep geocentric r_hat.
- Site latitude is geodetic. The same number therefore means a different point than in
  S1; this is stated in assumptions.
- g_track = -(g_J2(r_site) - omega x (omega x r_site)) . u, about 9.792 m/s^2 at 28.5 deg.
- Target: osculating two-body a = r_t and e = 0 at cutoff, with r_t = R_E + h_t geocentric
  (recommended for comparability; approved as the default in the SP1 plan). Geodetic
  altitude at insertion is reported. The orbit then oscillates at order J2; mean-element
  targets are deferred.

**Steps.**

1. **S2.1 `geodesy.py`.** Tests: round trip < 1e-7 m and 1e-14 rad over -5 km to 1,000 km
   at all latitudes; grad h equals the normal by finite differences.
2. **S2.2 Gravity.** Tests:
   - a = -grad U by finite differences against a potential typed in the test.
   - E = v^2/2 + U and h_z drift < 1e-8 over 10 revs (a = 10,000 km, e = 0.3, i = 50 deg).
   - Nodal rate -1.5 J2 n (R/p)^2 cos i and apsidal rate 0.75 J2 n (R/p)^2 (5 cos^2 i - 1)
     within 1%.
   - A polar orbit's node is fixed to 1e-10 rad; the apsidal rate is about 0 at
     63.435 deg.
3. **S2.3 Surface consistency.** Tests: gravity along the normal against Somigliana within
   2e-4 m/s^2 at 0, 28.5, 45, 90 deg (the gap is the missing J4; estimated 4e-5 at the
   equator and 1.2e-4 at the pole); horizontal residual < 2e-4 m/s^2; the released-at-rest
   test of S1.4 with g_ref.
4. **S2.4 Planner and metrics on `EarthModel`.** Tests: `EllipsoidJ2Earth(0, 0)` matches
   S1 at 1e-9 relative at fixed guidance and within 1 kg in P*; a new S1 pin stays
   bit-identical; identity < 1e-5 m/s; convergence.
5. **S2.5 Decomposition runs** (f only, J2 only, both) for the record in section 5.

## S3. 6-DOF verification fly-out (SP6)

**State.** r, v (ECI); q (body -> ECI, scalar first, Hamilton); omega_b (body axes); m;
two gimbal angles with a first-order actuator lag; the seven quadratures. Body frame: x_b
to the nose, stations measured from the nozzle plane, axisymmetric
I = diag(I_xx, I_t, I_t).

**Dynamics.**

- q' = 0.5 q (x) (0, omega_b).
- I omega' = M_aero + M_tvc - omega x I omega - I' omega - m_e' r_e x (omega x r_e) (the
  last term is jet damping).
- Thrust T t_b(delta) acts at the gimbal station, magnitude and m' as before.
- Aero: axial -q S C_A(M) x_b with C_A equal to the existing C_D table, so alpha = 0
  reproduces 3-DOF; normal q S C_N_alpha(M) alpha in the cross-flow direction at x_cp(M).
- Loss rows: drag is -F_aero . v_rel_hat/m, steering uses the gimballed thrust direction;
  the identity still closes.
- CG-shift acceleration terms are neglected (stated).

**Data** (in a fork `configs\vehicles\generic_f9_class_6dof.yaml`; the gate file is never
edited).

- Sourced: 3.66 m diameter, 70 m height, 5.2 m x 13.1 m fairing (Falcon User's Guide
  2021); LOX/RP-1 split from the gate file's own source; propellant densities.
- Stage lengths: recalled as roughly 41 m and 14 m; confirm against the source at
  implementation before marking them sourced.
- `assumed: true`: tank stations, dry-mass distribution, CG and inertia (computed from a
  cylinder-tank model with settled propellant), C_N_alpha(M) and x_cp(M) (Barrowman from
  the geometry), gimbal limit and rate, actuator lag, gains.

**Controller.** PD on the attitude error x_b x e_cmd, with e_cmd from the same S1/S2 laws
evaluated on the 6-DOF state.

- K_p = (I_t omega_n^2 + M_alpha)/(T l_g), K_d = 2 zeta omega_n I_t/(T l_g), scheduled on
  I, T, q.
- omega_n about 2 rad/s, zeta = 0.7, both assumed, with a +/-50% sensitivity.
- Smooth saturation delta_max tanh(.) keeps the RHS smooth.

**Silo and coast phases.** Attitude is rail-constrained on the track: x_b = u, omega =
Earth rate, zero tip-off, with optional `tipoff_rate` and `alpha0` sensitivity inputs. A
cold start coasts with no control authority until ignition, and with reduced authority
during the ramp. Reported: tau_div = sqrt(I_t/(q S C_N_alpha l)) at release, attitude
error at ignition, peak gimbal and time in saturation. A rough estimate is tau_div of
about 9-14 s at 77 m/s at sea level, which the mass model must confirm. The staging coast
has no reaction control; drift is reported.

**Payload at 6-DOF.** No 6-DOF search. Fly the 3-DOF-optimised (P*, delta, a, b). Report
insertion miss (dr, dv_r, di, e), gimbal peaks, true q-alpha and attitude error. An
optional re-solve of delta and (a, b) through the same two protocols gives the
residual-propellant difference, quoted as an estimated dP.

**Out of scope (assumptions list):** slosh, flex, wind, roll torque and roll control,
engine-out, per-engine gimbal geometry, thrust misalignment, separation dynamics,
nonlinear aero (flag when |alpha| > 10 deg).

**Steps.**

1. **S3.1 `rigidbody.py` mass properties.** Tests: cylinder I_t = m(3 r^2 + L^2)/12,
   parallel axis, full and empty limits, smooth CG travel.
2. **S3.2 Rotational core; `atol_for` gains quaternion and `_radps` suffixes.** Tests:
   torque-free precession rate (I_xx - I_t) omega_x/I_t at 1e-9 over 100 periods; inertial
   L and rotational energy < 1e-10; |q| - 1 < 1e-12; constant torque
   theta = 0.5 (M/I) t^2; jet-damping decay closed form.
3. **S3.3 `aero6.py`.** Tests in a fixed-q rig: oscillation or divergence rate
   sqrt(q S C_N_alpha |x_cp - x_cg|/I_t) at 1e-6; alpha = 0 force equals the 3-DOF drag.
4. **S3.4 `control.py`.** Tests: trim delta = q S C_N_alpha alpha (x_cp - x_cg)/(T l_g);
   step response omega_n and zeta.
5. **S3.5 `dynamics6.py` and `phases\rigid.py`** (reuses the `SpatialPlanner` kit). Tests:
   - Prescribed-attitude mode (x_b = e_cmd, delta = 0, C_N_alpha = 0) reproduces S1/S2 at
     1e-9.
   - Controlled limit (omega_n = 10 rad/s, C_N_alpha = 0): |dr| < 5 m, |dv| < 0.05 m/s,
     |dm_res| < 2 kg at MECO, shrinking at least 2x per doubling of omega_n.
   - Identity < 1e-5 m/s.
6. **S3.6 Fly-out pipeline, metrics, vehicle fork.**
7. **S3.7 Pad and silo fly-outs with sensitivities; findings with an honesty review.**

## 5. Calibration and comparability

- No tuning and no new fitted parameter, so no new calibration. The +14.3% miss carries
  over.
- Pre-register in the trackers before the first searched 3-D run, then write
  `docs\findings\M2M-3d-vs-planar.md` against the 26,054.4 kg gate.
- **S1 at 28.5 deg east:** the planar inertial dynamics are exact there. The only
  difference is the air's out-of-plane velocity omega_E sin(lat) r sin(theta), about 3 m/s
  at MECO, which enters at second order. Pre-registered |dP*| < 5 kg; a larger gap is
  treated as a bug until the loss rows explain it.
- **S2:** expect roughly -50 to -100 kg (-0.2 to -0.4%). The site sits about 4.8 km deeper
  for a geocentric target radius and surface gravity is about 0.2% higher. This is a hand
  estimate, to be decomposed by S2.5, not tuned.
- **Headline offload:** copy the planar offload experiment to `spatial_3d` (spherical,
  then `wgs84_j2`) with the same budget; report the offload percentage on all three
  models. Then fly pad and offloaded silo through S3 and compare their dm_res.
- **Requirement on SP1:** write the offload figure of merit against `RecordingProblem`,
  not `SearchContext`, so the 3-D context inherits it.

## 6. Outputs

- New writers; the planar writers are untouched.
- Time-series columns are a superset of the planar names, so the 2-D scene reads 3-D runs.
  Added: ECI and ECEF position and velocity; lat, lon, alt; crossrange; heading; yaw;
  thrust unit vector (ECI); `J_grav_lat`; osculating a, e, i, `raan_epoch`, argument of
  latitude.
- S3 adds q0..q3, omega_b, alpha, gimbal angles, attitude error, x_cg, I_t.
- Events carry the same columns. Summary rows add inclination, the gravity split,
  model-to-model deltas and the 6-DOF verification block.

## 7. Runtime, risks, deferrals, size

**Runtime (estimates, to be measured at S1.2).** Planar is about 12 microseconds per RHS
call and 9-24 s per searched run.

- S1: about 15 microseconds, 12-18 s typical. The lag-startup case may reach 30-35 s
  against today's 30 s budget.
- S2: about 20 microseconds, 15-25 s.
- S3: step cap 0.1 s; fly-out 3-10 s; with re-solve 1-2 min.
- The existing 2 s flight step cap is kept for 3-DOF.

**Risks and mitigations.**

1. Shared-module edits moving planar numbers: S1.0 pin first, additive edits only.
2. Slow Cartesian RHS: scalar floats; measure before building the planner.
3. Sign and monotonicity of gamma_MECO(delta): the signed definition above plus a scan
   test.
4. A thrust-direction step of about 1e-3 rad at kick end from the crosswind: documented;
   a small step command in S3.
5. Ambiguity of "200 km" under S2: geocentric R_E + 200 km chosen as the default (stated).
6. S3 data is mostly assumed: results are presented as sensitivities, not predictions.
7. Gimbal saturation non-smoothness: tanh saturation and the step cap.

**Deferred.** Inclination and plane targeting, mean-element targets, wind, integral
control, porting `PlanarPlanner` onto the shared kit.

**Size (new lines, source / tests).**

| Stage | Source | Tests | physics.md |
|---|---|---|---|
| S1 | about 4,500 | about 3,000 | +700 |
| S2 | about 900 | about 1,200 | +300 |
| S3 | about 2,800 | about 2,200 | +500 |

**Edits that touch validated code (all behaviour-preserving for 1-D and planar, guarded by
S1.0 and the 1-D golden):** `sim.run` dispatch, the `DynamicsKind` literal and rules in
`config.py`, `engine.atol_for` suffixes, the model branches in
`compare.py`/`results_io.py`/`summary.py`/`plots.py`, and constant additions. No existing
validated number changes. S2 produces new, different numbers by design; they are reported
as model-to-model deltas and never replace the planar gate.

## Critical files

- src\launchsim\phases\planar.py
- src\launchsim\dynamics.py
- src\launchsim\search.py
- src\launchsim\guidance.py
- src\launchsim\sim.py
