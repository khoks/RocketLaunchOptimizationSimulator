<!-- Record of SP7 step 0: read-only survey 01-assist-track-events (the drive seam, the track phase and its events), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0 survey 01: the drive seam, the track phase and its events (HEAD 22c62e9)

The assist seam is generic enough for a `linear_motor` to plug in without touching the planners: `AssistModel.state_rate` returns sddot, the drive force, the interface force and extra-state rates; `rhs_track` integrates whatever the model returns; both the 1-D and the planar planners run the same `fly_track` prelude; and the closed forms of the brief (section 5.7) are correct, which I checked by my own algebra and by DOP853 integrations to better than 5e-12 relative. Five things in the code do not fit a mass-dependent, force-limited drive and must change. (1) `push_time_estimate(track)` takes no mass, yet the first stage's ignition time for `reference: release` is fixed from it before the push. That holds even for t_ign_s >= 0, so under a drive whose push time depends on mass and thrust the ignition would land at the wrong time relative to the real release. (2) `fly_track` returns a `TrackExit` only on `track_end` (or s >= L) and computes the exit altitude at s = L, so a release at a target speed needs a new event and the release position carried through. (3) `AssistForces.dissipated_W` is never integrated, and the energy budget hard-codes `dissipated = 0`. (4) The felt-g observable assumes that no force other than the interface and the thrust acts on the vehicle. (5) Nothing integrates the carriage after release, and the RunTrace is a sequence of phases in time, so a carriage braking phase that runs alongside the flight does not fit it. The binding constraint on all of this is the 1-D golden tier: it can never be recaptured. So every new state, column, metric key, assumption line or summary row must appear only on runs of the new drive. Two findings matter for the experiment design. First, any force-then-power profile that reaches the same exit speed over the same stroke has a peak acceleration at or above the constant-acceleration value. At 76.7072 m/s over 100 m it needs 4.23 g0 felt at a 60 m/s corner speed and 7.21 g0 at 30 m/s, against 4.00 g0. Second, with fixed limits a lighter offloaded stack is pushed harder and faster, so the offload solve couples to the push under the linear motor in a way it does not under `constant_accel`.

## 1. Method and status of each claim

- I read the brief (docs/phases/SP7-structural-mass-push-load.md, sections 2, 5, 6 and 10) and the code at HEAD 22c62e9 (clean tree, checked with `git rev-parse`/`git status`). Every line reference below is at that commit.
- Facts carry file:line. "(inferred)" marks a conclusion drawn from the code and not read directly. Recommendations are labelled **Recommendation**.
- No repository file was edited or written. I ran no launchsim run, sweep or app, and no test suite.
- **REPORT.md was not written.** The task asked for a copy of this report at `.../scratchpad/a0/01-assist-track-events/REPORT.md`, but the harness refused the write ("Subagents should return findings as text"). This message is the only copy.
- Scratch scripts and their outputs are in `C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/01-assist-track-events/`:
  - `verify_closed_forms.py`, output in `verify_output.txt`: the linear-motor closed forms, the F_max needed for 76.7072 m/s at 100 m, the hot-start interface force, the trapped-column work, and the ramp dynamic-load factor;
  - `rise_time_probe.py`, output in `rise_time_output.txt`: the force needed to reach the same exit speed with a finite force rise time.

## 2. The assist package (facts)

### 2.1 `AssistModel` interface (src/launchsim/assist/base.py)

- `TrackGeometry` protocol, base.py:36-65: `length_m`, `start_altitude_m`, `phi(s)`, `kappa(s)`, `z(s)`. There is no `x(s)` (the exit's downrange offset is known only for a `StraightTrack`; prelude.py:760-771).
- `AssistForces`, frozen dataclass, base.py:68-86: `sddot_mps2`, `drive_force_N`, `drive_normal_N` (the drive's force along n_hat, which enters the carriage's normal load), `interface_force_N` (carriage on vehicle; negative means tension), `dissipated_W`, and `extra_rate` (d/dt of the model's extra states).
- `AssistModel` protocol, base.py:89-172:
  - `name`;
  - `extra_state_names` (111-114: "names (with unit suffixes for `phases.atol_for`) of the states the model integrates beside [s, sdot, m]");
  - `f_imp`, `efficiency`, `carriage_mass_kg` and `allow_negative_drive`;
  - `initial_extra()`;
  - `state_rate(t, s, sdot, extra, m_vehicle, m_carriage, thrust_axial, g_eff, track)` (140-155; `t` is absolute, with t = 0 at push start);
  - `push_time_estimate(track)` (157-160: "exact for a prescribed acceleration; an estimate for a force-limited drive"). It takes **only the track**: no vehicle mass and no thrust.
  - `braking_distance_m(v)` and `facility_length_m(track, v_exit)` (162-168), and `assumptions()` (170-172).
- `AssistBuilder` (175-189): a class-level `name` and `from_config(config, g_eff) -> (model, track | None)`.
- `normal_load_N`, base.py:192-215: N = m (kappa sdot^2 + g_eff cos phi) - F_other.n_hat.

### 2.2 `constant_accel` (src/launchsim/assist/constant_accel.py)

- `ConstantAccelAssist` is at 31. Fields at 61-69: `net_accel_mps2`, `carriage_mass_kg`, `brake_decel_mps2`, `efficiency`, `f_imp`, `allow_negative_drive`, `g_eff_mps2` (used for assumptions only), `omega_p_rads` (assumptions only) and `exit_speed_input_mps` (assumptions only). `name` and `extra_state_names = ()` are class constants (58-59).
- `from_config`, 71-98. The track starts at exit_altitude - L sin phi (86). `omega_p_rads` is not set here: the planar setup replaces it only for this class (sim.py:1064-1066).
- `state_rate`, 121-146: `a_up = a + g_eff sin phi(s)` (137); `F_drive = M a_up - (1 - f_imp) T` (141); `F_int = m_v a_up - T` (143); `drive_normal = 0` (142); `dissipated = 0` (144); `extra_rate` empty (145). The acceleration is prescribed, so the drive force is solved, not limited.
- Closed-form helpers: `exit_speed_mps` sqrt(2aL) (148-150), `push_time_s` sqrt(2L/a) (152-154), `time_to_speed_s` v/a (156-160), and `push_time_estimate`, which is exact (162-164).
- Carriage after release, in closed form only: `braking_distance_m` = v^2/(2 a_brake) (166-168) and `facility_length_m` = L + braking distance (170-172).
- Assumptions, 206-226. Among them: "drive force unconstrained, solved from the track equation" (213-214), "shaft vented (no air column), no friction" (222) and "infinite jerk at push start and release" (224).
- Exhaust impingement: the system keeps (1 - f_imp) T, while the vehicle feels its full T (base.py:15-20; physics.md 4545-4554).

### 2.3 `none`, `track`, the registry

- `NoAssist` (none.py:17): `state_rate` raises (41-54); a zero push time and zero facility.
- `StraightTrack` (track.py:18-52): phi constant; `__post_init__` accepts phi in [0, pi/2] (30-35). `TrackConfig` admits 90 degrees only (config.py:589-605, refusal at 597-603).
- `ASSIST_MODELS = {none, constant_accel}` (assist/__init__.py:27-30); `build_assist` dispatches through it (36-52).
- config.py: `PlannedModel = Literal["linear_motor", "cable_winch"]` (78); `PLANNED_MODELS` (79); `PlannedAssistConfig` refuses with "planned for Phase 3" (713-723); `AssistConfig` is the union (726-728).

### 2.4 The track equation as implemented, against CLAUDE.md "Physics model" item 2

Implemented (base.py:11-20, physics.md 4541-4554):

    M sddot = F_drive + T_sys - M g_eff sin phi - F_other,     T_sys = (1 - f_imp) T,  M = m_v + m_c
    F_int   = m_v (sddot + g_eff sin phi) - T

CLAUDE.md: (m_v + m_c) s̈ = F_drive·t̂ + T_axial − (m_v + m_c) g_eff (t̂·ẑ) − D_air − F_friction − F_piston.

The differences (facts):

- **Impingement.** T_axial is replaced by (1 - f_imp) T, an amendment stated in physics.md 4545-4551.
- **Lumped forces.** D_air, F_friction and F_piston are folded into one `F_other`, which no model supplies today: constant_accel has zero friction and zero piston force, and the vented shaft has no drag (sim.py:973-978 states the bias).
- **Direction of the solve.** constant_accel inverts the equation: sddot is given and F_drive is solved from it.
- **Where F_other acts.** The interface formula assumes F_other acts on the carriage, never on the vehicle (inferred from F_int = m_v(sddot + g sin phi) - T, which holds only if the vehicle's free body has no other force).
- **Normal load.** It matches CLAUDE.md (base.py:200-215; n_hat.z_hat = cos phi).

## 3. The track phase: integration, events and the carriage after release

### 3.1 dynamics.py

- `g_eff_track(omega_p)` = mu/R_E^2 - omega_p^2 R_E (114-121).
- Track state: `TRACK_BASE_STATE_NAMES = (s_m, sdot_mps, m_kg)` (352), then the model's extra states, then `TRACK_QUADRATURE_NAMES = (E_drive_J, W_thrust_J, J_mass_J)` (354, 360-363).
- `TrackParams` (371-435) holds the track, the assist, `carriage_mass_kg`, `g_eff`, the schedule, `p_amb_pa` and `lit`. Its `extra()` slices the model's extra states (416-419), and `forces()` calls `assist.state_rate` (421-435).
- `rhs_track` (438-472) integrates `ds = sdot` and `dsdot = f.sddot`, `dm = -T_vac/c`, the extra states from `f.extra_rate` (467-468), `dE_drive = F_drive sdot` (469), `dW_thrust = (1 - f_imp) T sdot` (470) and `dJ_mass = Mdot (sdot^2/2 + g_eff z)` (471). **`f.dissipated_W` is not integrated anywhere**: the field is set only at constant_accel.py:144 and read nowhere (grep over src/).
- `track_observables` (475-508) reports F_drive, F_int, P = F_drive sdot, the normal loads and `felt_g = (F_int + T)/m_v` (505). The same function feeds the 1-D time series (metrics.py:161-186) and the planar one (metrics_planar.py:488-518, `felt_axial_g` from `accel_felt_g`).

### 3.2 `fly_track` (phases/prelude.py:774-922)

The function runs in this order:

1. `t_push_est = assist.push_time_estimate(track)` (823). A value <= 0 raises (824-825).
2. The ignition time: `t_ign = spec.t_ign_abs_s(t_push_est, 0)` (831), that is t_push_est + t_ign_s for `reference: release` and t_ign_s for `push_start`. It is written to `tr.t_ign_abs_s` before the push (832-833) and the schedule is built from it (838). A pending height-event ignition flies the push unlit (826-829).
3. A hot start with t_ign < 0 gets a closed-form HOLD (841-858) carrying m g_eff sin phi. The vehicle is clamped to the carriage, and there is no liftoff extension.
4. The track layout is the model's layout (862), with the extra states set from `initial_extra()` (865-868).
5. The step cap is `push_cap = t_push_est / settings.push_steps` (871).
6. The sub-phase boundaries are the schedule's kink times only (872-873).
7. In each sub-phase (877-910) the events are `ev_track_end`, `ev_propellant` and, unless `allow_negative_drive`, `ev_drive_limit` (881-883). Every non-`track_end` event is logged (887-890), terminal or not, so a non-terminal event is logged automatically. `drive_limit` stops the run (892-899); `propellant` raises (900-903); `ramp_end` is logged (906-910).
8. The exit is returned only when `res.ended_by == "track_end" or s_end >= L - ATOL_M` (912). The `TrackExit` fields are evaluated **at s = L**: `phi_rad=track.phi(length)`, `x_exit_m=_exit_x_m(track)` and `z_exit_m=start + track.z(length)` (913-921). Otherwise the code raises `RuntimeError` (922).

Consequence (inferred): a sub-phase ended by any other terminal event moves the loop on to the next fixed boundary. If that boundary was `None` (the last), it falls through to the RuntimeError. The loop cannot re-enter after a split event.

### 3.3 Events and the engine (phases/engine.py)

- `ev_track_end(L)`: s - L crossing upward, terminal, `zero_tol = ATOL_M` (674-685).
- `ev_drive_limit(params)`: F_drive crossing zero downward, terminal, `zero_tol = ATOL_KG * g_eff` (688-704).
- `ev_time` (852-863) is the time-event pattern.
- `EventSpec` (175-197) has name, fn, terminal, direction and zero_tol. `integrate_phase` (400-531) applies the pre-solve rules: already past means the phase ends at t0; at zero means a Heun prediction decides whether to disarm.
- Per-state atol comes from the name suffix (`_ATOL_BY_SUFFIX`, 90-96): `_m`, `_mps`, `_kg`, `_J`, `_rad`. **An unknown suffix raises** (`atol_for`, 291-307). A force state (`_N`), a pressure state (`_Pa`) or a power state (`_W`) therefore needs a new entry.

How the new pieces would enter (facts about the mechanism; the choice is a recommendation in section 7):

- **A target-speed release.** A factory `sdot - v_target` with direction +1, terminal and zero_tol `ATOL_MPS`, listed in fly_track's event list (881-883). The exit condition (912) and the event-log exclusion (888) must name it, and the `TrackExit` must carry the release s (913-921).
- **Extra drive states.** These are already supported generically: `extra_state_names`, `initial_extra`, `AssistForces.extra_rate`, `TrackParams.extra` and `rhs_track` 467-468. No model uses them today.
- **A time-based force ramp.** It needs no state. Its kink at t_r should be a sub-phase boundary, but fly_track builds boundaries from `schedule.kink_times()` only (872); a model-supplied kink list is needed.
- **The power-limit corner (sdot = P/F).** It is a C1 kink in the velocity, so only the jerk jumps. It can be crossed without splitting (section 9: error 4e-12 without a split against 2e-13 with one) and logged with a non-terminal event.

### 3.4 Ignition timing depends on `push_time_estimate` (fact plus consequence)

- The release-referenced ignition of stage 1 is resolved against the estimate before the push (prelude.py:831), even for t_ign_s >= 0. The 1-D ascent uses `tr.t_ign_abs_s` when fly_track set it (vertical.py:383-387). The planar start passes `tr.t_ign_abs_s.get(stage0)` (planar.py:938), and a `None` there with no altitude means "stage 1 does not light" (planar.py:573-584).
- The depth, speed and closed-form height conversions are refused for any drive other than `constant_accel` (`resolve_ignition`, prelude.py:282-288; pinned by tests/test_silo.py:1003-1022, "needs the constant_accel drive"). `_ramp_start_time` also calls `push_time_estimate` (336).
- The planar ramp-start metrics compare the converted time with `push_time_estimate` (sim.py:1341) and compute the depth from z at s = L (sim.py:1340).
- Consequence (inferred): for a mass- and thrust-dependent drive, a `release`-referenced ignition lands at t_push_est + t_ign_s, not at t_release + t_ign_s, unless the estimate is exact for that vehicle. With thrust on the track the estimate cannot be exact in general, because the push time depends on t_ign, which is circular.

### 3.5 The carriage after release (fact)

Nothing integrates the carriage after release. Braking exists as the closed form v^2/(2 a_brake) only:

- `constant_accel.py:166-172`;
- facility length and braking distance in metrics.py:509-510 and metrics_planar.py:1014-1015;
- the parked-carriage altitude for the failed-ignition geometry, which puts the carriage d_brake beyond the exit along the tangent: metrics.py:601-614, with z at s = L at 612;
- the scene's carriage animation (templates/scene.html 1532, 1831), which reads `braking_distance_m`;
- the app's derived values (appform.py:1493-1502).

The run assumption says so: "carriage braking is not modelled as a phase (its distance v^2/(2 a_brake) is added to the facility length)" (sim.py:683-686). The RunTrace holds the vehicle's phases in time order (`TraceBuilder.add_phase`, trace.py:364-375; `finish`, 409-428). A carriage phase that runs at the same time as the ascent has no place in it (inferred).

## 4. One prelude for both models: what a new drive must support (facts)

- The 1-D model: `VerticalPlanner.run_track` (vertical.py:296-339) calls the same `fly_track` with `VERTICAL_PRELUDE` (315) and then `map_release` (328). `map_release` refuses a non-vertical exit (vertical.py:144-148). `sim.run` (1-D) builds any registered drive (sim.py:861), and `sim.simulate` accepts an injected one (sim.py:732-835). The energy tests inject `ConstantAccelAssist` this way (tests/test_assist_energy.py:57-92).
- The planar model: `PlanarPlanner.start_track` (planar.py:907-944) calls `fly_track` with the planar prelude, uses the exit pressure p(z at s = L) for the whole push (919-930), and then `map_release_planar`, which requires a vertical exit and x = 0 (planar.py:397-427). `SearchContext.from_run` builds the drive per run context (search.py:559-560).
- No code under src/ besides config, appform, app, scene, replay, metrics_planar and sim names `constant_accel`. Specifically: `sim.planar_setup`'s omega_p replace (sim.py:1065-1066), `prescribed_accel_mps2` (metrics_planar.py:939-946), the `ConstantAccelConfig` depth check (config.py:1433-1438), `resolve_ignition` (prelude.py:282), and `ENERGY_ONLY_ASSIST_KEYS` (compare.py:1744-1749, whose docstring already says "a linear motor with an electrical power limit would fly differently with another efficiency").
- **What a new drive must support** (inferred from the above): the `AssistModel` protocol on both planners. The 1-D model needs nothing more. The 1-D golden runs only `constant_accel` and the pad (golden_1d_support.py; tests/test_golden_1d.py:1-31), so a linear motor in 1-D is free to exist. 1-D is also the cheapest home for closed-form tests (`sim.simulate` with constant g_eff and a track model).

## 5. Push metrics: what exists and what assumes a constant acceleration (facts)

1-D, `metrics.track_metrics` (441-522), and planar, `planar_track_metrics` (metrics_planar.py:963-1060), write the same keys. The planar one adds `PUSH_SETTING_METRICS` (933, 948-960). Pad zeros are at metrics.py:425-436 and `PAD_ASSIST_ZEROS` (metrics_planar.py:850-864). Time-series columns are `TRACK_COLUMNS` (metrics.py:60-67), and they are part of both models' column lists (metrics.py:68-85; metrics_planar.py:340-348).

| Metric | Source | Assumes constant acceleration? |
|---|---|---|
| `exit_speed_mps` | release state (metrics.py:478; planar `_state_row` speed_rel, 970-972) | no |
| `push_time_s` | `trace.t_release_s` (493; 996), absolute with t = 0 at push start | no |
| `stroke_m` | `track.length_m` (planar only, 955-956) | no, but it is the track length, not the push length under a target-speed release |
| `net_accel_mps2`, `net_accel_g` | `prescribed_accel_mps2` (939-946): None for any other drive | yes (None for a linear motor; the key set stays the same) |
| `felt_g_track_peak` (+ time, mass) | sampled ASSIST rows (488; planar 990-1001) | no, but the docstring claims exactness from "the forces of the prescribed-acceleration drive, which are monotone within a lit sub-phase" (453-454); with kinks as boundaries that stays true (inferred) |
| `interface_force_peak_N`, `_min_N`, `drive_force_peak_N` | sampled rows (497-499; 997-999) | same as above |
| `drive_power_peak_W`, `_t_s`, `drive_power_min_W` | dense-output scan (`losses.drive_power_extrema`, 240-292; 486; 989) | no; under a power limit P = P_max on a plateau: the value is exact, the time is arbitrary within the plateau (inferred). KI-032: `_t_s` is on the absolute clock (507; 1012) |
| `drive_energy_J`/kWh, `drive_work_in/out_J`, `electrical_energy_J`/kWh | quadrature E_drive; electrical = work_in / efficiency (485; 988) | no |
| `braking_distance_m`, `facility_length_m` | `assist.braking_distance_m(v_exit)`, `facility_length_m(track, v_exit)` = L + d (509-510; 1014-1015) | constant deceleration; facility assumes release at L |
| `carriage_park_altitude_m` / failed-ignition carriage items | metrics.py:601-614 (z at s = L) | release at L |
| `ramp_start_*` (planar) | the converted time against `push_time_estimate`, depth from z(L) (sim.py:1332-1345) | yes (exact only for a prescribed push) |
| `assist_energy_residual_rel`, `carriage_mass_kg`, `track_start_altitude_m`, `propellant_burned_on_track_kg`, normal loads | budget, model, track | no |

The readers that infer a constant acceleration: `replay.push_accel_g` (replay.py:699-706) uses the metric else the config's `net_accel_g`. `scene.py:513-528` derives `net_accel_mps2 = v^2/(2L)` from the exit speed and labels it "derived", so for a linear-motor run it would draw the equivalent constant acceleration (inferred), as the brief anticipates in 5.7.

## 6. The assist energy identity (docs/physics.md 4536-4589; tests/test_assist_energy.py)

- What is integrated: `E_drive = ∫ F_drive sdot`, `W_thrust = ∫ (1 - f_imp) T sdot` and `J_mass = ∫ Mdot (sdot^2/2 + g_eff z)` (dynamics.py:448-456, 469-471). `AssistEnergyBudget(work_drive, work_thrust, delta_mech, massflow_term, dissipated)` (losses.py:98-127) checks work_drive + work_thrust = delta_mech + massflow_term + dissipated.
- **`dissipated` is hard-coded 0.0** (losses.py:168). The docstring says "a dissipative drive of Phase 3 must add its own quadrature" (142-144). `residual_rel` uses a 1 J floor (122-127).
- **Efficiency does not enter the identity.** It enters only as electrical = work_in / eta (metrics.py:485; metrics_planar.py:988; no regeneration, sim.py:690-691). The energy test builds the drive with `efficiency=0.5` (test_assist_energy.py:63) and never checks electricity. Tests: cold closed form E = M (a + g) L for m_c in {0, 20 t} and omega_p in {0, site} (114-134); hot full thrust for f_imp in {0, 0.5, 1} (167-178); the planar prelude with rotation (181-204); a ramp straddling the push, closure only (207-240). Required residual 1e-6, asserted 1e-9 (48).
- What the new pieces add (algebra; recommendations in section 7):
  - **Linear motor with eta.** The mechanical identity is unchanged: F_drive sdot is still the drive's work. If P_max is the mechanical limit at the carriage, eta stays energy-only, as for constant_accel. If P_max is the electrical supply limit, then F = min(F_max, eta P_el / sdot): eta enters the trajectory, `ENERGY_ONLY_ASSIST_KEYS` must not list it, and the drive-efficiency sensitivity becomes a full searched run. Either way the motor loss (1/eta - 1) W_in lives in a second, electrical ledger, not in `dissipated`.
  - **Piston.** It adds W_p = ∫ F_p sdot dt as a stated term on the right. For an adiabatic trapped column it is reversible (it goes into p_atm ΔV of the atmosphere and the gas's internal energy), so it is not "dissipated". Because F_p depends on s alone, W_p(s0, s1) has a closed form (section 9). A model quadrature would test the integration.
  - **Braking.** It lies after release, outside the push identity. delta_mech already counts the carriage's kinetic energy at release, ½ m_c v^2. The carriage alone obeys ½ m_c v^2 = W_brake + m_c g_eff d sin phi, so W_brake = ½ m_c v^2 (1 - g_eff sin phi / a) for a constant net deceleration a.

## 7. Per-feature change map

Facts are the current lines. Each **Recommendation** is mine, for Plan mode to settle.

### 7.1 `linear_motor`: F = min(F_max, P_max / sdot), eta, carriage mass

- **Lines to change.**
  - New `assist/linear_motor.py` (`LinearMotorAssist`, frozen, `name = "linear_motor"`), registered in `ASSIST_MODELS` (assist/__init__.py:27-30).
  - `LinearMotorConfig` replaces `PlannedAssistConfig` for that key (config.py:78-79, 713-728), with the depth check extended (1433-1438).
  - `ENERGY_ONLY_ASSIST_KEYS` (compare.py:1744), depending on the P_max semantics.
  - The omega_p replace (sim.py:1065-1066) if the model quotes it.
  - `push_time_estimate` is called at prelude.py:823 and 336 and at sim.py:1341. `units.py` has `kn_to_n` but no MW (44-100): a YAML power in MW needs a new conversion there (CLAUDE.md: unit factors only in units.py).
- **Tests that change with it.**
  - tests/test_config.py:219-220 and 283-289 (the planned-model pins).
  - tests/test_silo.py:506-535 (`set(ASSIST_MODELS) == {"none", "constant_accel"}` at 518).
  - tests/test_silo.py:1003-1022, if the drive learns the depth and speed triggers.
  - `PHYSICS_MODULES` in tests/test_scaffold.py and `RUN_PATH_MODULES` in tests/test_scene.py.
- **State and events.** No new state is needed. `state_rate` returns sddot = (F + (1 - f_imp) T - M g sin phi - F_other)/M, F_drive = F and F_int = m_v (sddot + g sin phi) - T. `ev_drive_limit` cannot fire, since F >= 0 by construction. **Recommendation:** add a non-terminal `power_limit` event at sdot = P_max/F_max, which fly_track logs automatically (887-890).
- **The protocol gap.** `push_time_estimate(track)` has no mass (base.py:157-160). **Recommendation:** give it the vehicle mass at push start (and optionally T), computed from the cold closed forms. The constant_accel and none implementations ignore it, so their outputs do not move. Also refuse a `release`-referenced ignition with t_ign_s < 0 on this drive, or resolve it by a root solve on the push. Treat t_ign_s >= 0 as pending through the unlit push and resolve it at the real t_release. The 1-D `ascend` already falls back to `spec.t_ign_abs_s(tr.t_release_s)` when nothing was written (vertical.py:385-387); the planar `start_track` would need the same (planar.py:938). Depth and speed triggers are cold until they fire, so the cold closed forms with the liftoff mass give them exactly (inferred). `resolve_stage_ignitions` has the vehicle (prelude.py:201-228); `resolve_ignition` does not.
- **Starting from rest.** If F(0) + T_sys < M g sin phi, sddot(0) < 0 and nothing stops s < 0 (fact: no stop constraint in rhs_track). **Recommendation:** refuse or flag a stall at push start (status `drive_stall`). The force rise time below must also start from the holding force (7.2).
- **Coupling to the offload** (inferred, from recorded numbers). With fixed F_max and P_max the force-phase felt g is F_max/(g0 M). The headline offloaded stack is about 531 t (20.81 MN at 39.19 m/s^2, brief 5.1), against 573.9 t for silo_cold. The same limits that give silo_cold 3.9965 g0 would push the offloaded stack at about 4.32 g0, and faster. Under constant_accel the acceleration is prescribed and this coupling is absent. Plan mode must decide whether the SP7 cases state the drive by its limits (a fixed facility, so the coupling is real) or by a target exit speed (7.3).
- **Pin risk.** None, if the drive lives in new classes only. A new default field on `ConstantAccelConfig` would break the digest pin (brief 5.10; the dump rule at config.py:679-690 is the model for leaving keys out).

### 7.2 Finite force rise time

- **Facts.** fly_track's boundaries are the thrust kinks only (prelude.py:872-873). `state_rate` receives the absolute t (base.py:140-155), with t = 0 at push start (prelude.py:17-18).
- **Recommendation: a time-based ramp, no state.** F_lim(t) = F_0 + (F_max - F_0) min(1, t/t_r), with F_0 the holding force M_0 g sin phi - T_sys(0) fixed at push start. It needs a hook through which fly_track hands the model m_push and T(0), and a model kink list merged into `boundaries` at prelude.py:873. A ramp from F = 0 would give sddot(0) = -9.77 m/s^2 (rise_time_probe.py). The other options:
  - a first-order lag state named `F_drive_N`, which needs a `_N` atol entry (engine.py:90-96);
  - a ramp from 0 against a bottom stop, a hold-like sub-phase ended at the root F + T_sys = M g sin phi, mirroring `hold_until_liftoff` (prelude.py:581-672).
- **Closed form for the test.** During the ramp from the holding force (cold, constant M), the jerk j = (F_max - F_0)/(M t_r) is constant: sddot = j t, v = j t^2/2, s = j t^3/6. After t_r the 5.7 forms apply, from the state at t_r.
- **Cost of finite jerk** (rise_time_probe.py; cold, vertical, 76.7072 m/s at 100 m, M = 573,853 kg):

  | t_r | F_max | Felt g0 | vs step |
  |---|---|---|---|
  | 0.25 s | 22.5034 MN | 3.9988 | +0.06% |
  | 0.5 s | 22.5426 MN | 4.0057 | +0.23% |
  | 1.0 s | 22.7027 MN | 4.0342 | +0.94% |

  A step needs 22.4905 MN (3.9965 g0).
- **Pin risk.** If the boundary merge produces the same sequence of `integrate_phase` calls for constant_accel (an empty model kink list), there is none (inferred). Any reordering of the boundary list for existing runs would break the bit-exact 1-D tier.

### 7.3 Release at a target speed

- **Lines to change.**
  - A new event factory in engine.py: `sdot - v_target`, direction +1, terminal, `ATOL_MPS`.
  - fly_track's event list (prelude.py:881-883), the logging exclusion (888) and the exit test (912).
  - `TrackExit` (714-734) gains the release position and the trigger. Its `z_exit_m`, `phi_rad` and `x_exit_m` must be evaluated at s_release (913-921).
  - The consumers: `map_release` (vertical.py:328), `map_release_planar` (planar.py:933 via 397-427), the carriage park altitude (metrics.py:612), the ramp-start depth (sim.py:1340) and the facility length (constant_accel.py:170-172 analogue).
- **Recommendation.** Use it only on `linear_motor`. Keep z(L) bit-for-bit when the trigger is `track_end`: recomputing z(s_end) for constant_accel would move the release altitude by up to ATOL_M and break the bit-exact tiers. If v_target > v_inf or is not reached by L, `track_end` fires first and the run reports it. The unused stroke becomes braking track: facility = max(L, s_rel + d_brake) (inferred). Add a release-position metric for these runs only.
- **Note** (inferred). A release below the mouth leaves the vehicle inside the shaft. The planar ascent lists `ev_ground` only in falling phases (planar.py:1423), so a rising start below z = 0 is not refused. The track's constant ambient pressure is taken at s = L (planar.py:919).
- **Tests.** At the event, sdot = v_target within ATOL_MPS and s = s(v) of the closed form; the release state maps at z(s_rel).

### 7.4 Modelled carriage braking

- **Facts.** Section 3.5 lists where braking lives today. The TRACK_ASSUMPTIONS line (sim.py:683-686) is in every 1-D track run's summary.
- **Recommendation.** Make it pure functions on the drive: distance v^2/(2a), time v/a, brake force m_c (a - g sin phi), brake energy ½ m_c v^2 (1 - g sin phi / a), and optionally a power-limited regenerative brake integrated alone with its own closed form. Do not make it a RunTrace phase, which is sequential (inferred). Use it on linear_motor only, so the constant_accel assumption line and metric keys stay as they are; that line cannot change for 1-D runs (section 8). With a constant deceleration the "modelled" braking reproduces the closed form exactly. It adds new information only with a force- or power-limited brake, or with a release before L.
- **Tests.** The three closed forms; zero for m_c = 0.

### 7.5 Sealed-shaft air column

- **Physics** (my algebra). The trapped air below the carriage has a gap h_0 (assumed) and bore area A: p(s) = p_0 (h_0/(h_0 + s))^gamma and F_p = (p_top - p(s)) A. Since p >= 0, F_p <= p_top A by construction. The work is W_p = p_atm A s - p_0 V_0 [1 - (V_0/V)^(gamma-1)]/(gamma - 1). The pressure is a function of s, so **no state is needed** for the adiabatic case. A partly vented shaft would need a pressure state `_Pa`, which has no atol entry (engine.py:90-96).
- **Where it acts** (verified, section 9). The deficit acts on the carriage deck when the vehicle sits in air at p_atm above it (inferred geometry). Then:
  - under constant_accel, F_drive rises by F_p and F_int is unchanged;
  - under a force-limited drive, sddot falls and F_int = (m_v (F - F_p) - T (m_c + f_imp m_v))/M, that is **lower by (m_v/M) F_p**.

  If it acted on the vehicle, F_int would be higher by (m_c/M) F_p, and the felt-g observable (dynamics.py:505) would be wrong by F_p/m_v (1.91 m/s^2 for 1.09 MN on 570 t). The current `AssistForces` has no "other force on the vehicle" field (base.py:81-86).
- **Recommendation.** The force acts on the carriage, inside `F_other` of the drive's `state_rate`. Its work goes into a model extra state `W_other_J` (the `_J` suffix exists), so the constant_accel layout is untouched. `AssistEnergyBudget` gains a `work_other` field read from that state, defaulting to 0 (losses.py:98-169; x - 0.0 is exact, so the constant_accel residual is bit-identical, inferred). Add `shaft: Literal["vented", "sealed"]` with `bore_m`, `gap_m` and `gamma` on `LinearMotorConfig` only. constant_accel's `shaft: Literal["vented"]` (config.py:646) and its assumption (constant_accel.py:222) stay.
- **Tests.** The work closed form against the identity quadrature; F_p <= p_atm A at every sample; F_int lower by (m_v/M) F_p under a force-limited push.

### 7.6 Pin risk, by kind of change

- **The 1-D golden tier** (tests/test_golden_1d.py) re-runs experiments/silo_screening_1d.yaml and the vertical_1d paths. It compares every output file (rel 1e-12, and exactly in the capture environment) and the set of files. **It can never be recaptured**: capture refuses unless src/, configs/, experiments/, pyproject.toml and uv.lock equal 104ea07 (golden_1d_support.py:47-49, 146-147, 755-772). The following therefore break it:
  - any change to constant_accel's push integration (state vector length, boundary order, RHS arithmetic);
  - `TRACK_COLUMNS` and `TIMESERIES_COLUMNS` (metrics.py:60-85);
  - `track_metrics` keys;
  - `TRACK_ASSUMPTIONS` or `ConstantAccelAssist.assumptions` text;
  - summary rows.

  New items must be conditional on the new drive. The precedent is the conditional ramp-start rows (`summary.RAMP_START_ROWS`, cited at metrics_planar.py:1047-1050).
- **The planar digest pin** (tests/test_config_planar.py:323-342) hashes the resolved run and vehicle dicts of the four pinned experiments and is never recaptured (planar_pin_support.py:18-19). It is at risk only from new dumped fields on the existing config models.
- **The planar output capture** (tests/test_planar_pipeline.py:1146-1162) compares metric key paths, CSV headers and files in every environment, and the summary sha256 in the capture environment. It **can be recaptured deliberately**, as SP1 steps 2 and 3 did (planar_pin_support.py:31-38). A new metric key on constant_accel runs would break it; a new column would break it and the 1-D tier together.

## 8. Tests to copy and what pins what

- Closed forms to copy from: tests/test_silo.py:159-275 (cold kinematics, interface and felt g), 302-370 (hot interface, the tension flag, drive limit), 541-629 (energy, power and facility), 732-860 (exit-speed form); tests/test_assist_energy.py (above).
- tests/test_planar_pipeline.py:1165-1186 pins that `PUSH_SETTING_METRICS` came in one block after `carriage_mass_kg` (`keys[first - 1] == "carriage_mass_kg"`). New push metrics placed after that block on linear-motor runs only would not disturb it (inferred).
- tests/test_planar_pipeline.py:1102 pins `PUSH_SETTING_METRICS == ("stroke_m", "net_accel_mps2", "net_accel_g")`. Adding a key to the tuple changes the tuple pin and the capture.

## 9. Independent verification of the brief's closed forms (section 5.7 and the interface force)

**Algebra (vertical, constant M, cold, g = g_eff).**

- The force phase gives a = F_max/M - g, v = a t, s = a t^2/2, up to v_c = P_max/F_max.
- In the power phase, dv/dt = g (v_inf - v)/v with v_inf = P_max/(M g). Using v/(v_inf - v) = -1 + v_inf/(v_inf - v): t - t_c = (1/g)[(v_c - v) + v_inf ln((v_inf - v_c)/(v_inf - v))].
- Using v^2/(v_inf - v) = -(v + v_inf) + v_inf^2/(v_inf - v): s - s_c = (1/g)[(v_c^2 - v^2)/2 + v_inf (v_c - v) + v_inf^2 ln((v_inf - v_c)/(v_inf - v))].
- Horizontal: M v dv/dt = P gives v^2 = v_c^2 + 2P(t - t_c)/M, and M v^2 dv = P ds gives v^3 = v_c^3 + 3P(s - s_c)/M.

**All four agree with the brief exactly.** Their preconditions are not written beside them in the brief: F_max > M g sin phi (else no lift), v_c < v_inf and v < v_inf, constant M (cold), F at F_max from t = 0 (no rise time), M including m_c, and g replaced by g_eff sin phi on an inclined track.

**Numerical results** (verify_output.txt; DOP853, rtol 1e-12; M = 573,853 + 22,000 kg; F_max = M (3 g0 + g_eff); v_c in {30, 50, 70} m/s; to 76.7072 m/s):

| Case | Relative error, t | Relative error, s | E_drive vs ΔKE + ΔPE |
|---|---|---|---|
| Vertical, g_eff = 9.7720917 m/s^2 | <= 3.8e-12 | <= 4.9e-12 | <= 1.7e-13 |
| Vertical, split at the corner | <= 5.1e-13 | <= 1.0e-12 | |
| Horizontal | <= 4.1e-13 | <= 7.9e-13 | |

**Hot-start interface force.** From base.py:13 and 19, F_int = m_v (F + (1 - f) T)/M - T = (m_v/M) F - T (m_c + f m_v)/M, which in the force-limited phase is the brief's (m_v/M) F_max - T (m_c + f_imp m_v)/M. **Correct.** It equals F_max - f_imp T for a massless carriage: exactly F_max only when f_imp = 0, which is what the brief says. Over 1,000 random cases the code formula and the brief's agree to 1.5e-15, and the carriage free body m_c sddot = F - F_int - f T - m_c g closes. The felt g is (F + (1 - f) T)/M.

**Trapped column.** p_atm A = 1.0895 MN for a 3.7 m bore, matching the README's 1.1 MN.

| Gap h_0 | F_p(L) / (p_atm A) | Work over 100 m | Closed form vs quadrature |
|---|---|---|---|
| 0.5 m | 0.9994 | 107.7 MJ (29.9 kWh) | 1.5e-16 |
| 5 m | 0.986 | 99.4 MJ (27.6 kWh) | 1.5e-16 |
| 20 m | 0.919 | 81.1 MJ (22.5 kWh) | 1.5e-16 |

**Ramp dynamic-load factor** (brief 5.2). The numerical undamped SDOF equals 1 + |sin(pi t_r/T)|/(pi t_r/T) to 6 decimals for t_r/T in {0, 0.25, 0.5, 1, 1.5, 2, 3.3} (2.000, 1.900, 1.637, 1.000, 1.212, 1.000, 1.078). **Correct.**

**The F_max needed for 76.7072 m/s at L = 100 m** (cold, m_c = 0, M = 573,853 kg, no rise time; closed forms):

| Corner speed v_c | F_max | Force-phase felt g | P_max |
|---|---|---|---|
| none (constant_accel) | 22.490 MN | 3.9965 g0 | 1.725 GW at release |
| 70 m/s | 22.68 MN | 4.030 g0 | 1.587 GW |
| 60 m/s | 23.81 MN | 4.231 g0 | 1.429 GW |
| 50 m/s | 26.41 MN | 4.692 g0 | 1.320 GW |
| 40 m/s | 31.34 MN | 5.568 g0 | 1.253 GW |
| 30 m/s | 40.56 MN | 7.207 g0 | 1.217 GW |

## 10. Corrections and precisions to the brief

1. **appform.py:187.** `ASSIST_UNION_TAGS = frozenset({"none", "constant_accel", *PLANNED_MODELS})`. Removing `linear_motor` from `PLANNED_MODELS` **drops** "linear_motor" from the tag set. It does not "follow automatically" (brief section 2, item 5; section 5.11). The impact is low, since the form submits `constant_accel` only (appform.py:100-105, inferred), but the set should be derived from the union or name the tag.
2. **Brief 5.7, "the assist energy identity holds with eta ... as stated terms".** Eta does not enter the mechanical identity (section 6). It enters a separate electrical ledger, and enters the trajectory only if P_max is an electrical limit. The piston work is a stated term, but it is not "dissipated".
3. **Brief 5.7, air-column row**, "decides whether it reaches the interface force at all". That is true only under the prescribed drive. Under a force-limited drive a carriage-side piston force lowers F_int by (m_v/M) F_p; a vehicle-side one raises it by (m_c/M) F_p and breaks the felt-g observable (section 9; dynamics.py:505).
4. **Brief 5.2, the step load "peaks at twice the static load".** The factor 2 applies to the load increment. The stack already rests on the carriage at about 1 g (cold, vertical), so a step to n of about 4.0 peaks near 1 + 2 (n - 1), about 7.0 g0, not 2n = 8 g0 (inferred, undamped SDOF). The release is a step too: under constant_accel it is "infinite jerk at push start and release" (constant_accel.py:224). A cold release drops the load from about 4 g to 0, and an undamped structure then swings to about -4 g, an axial tension (inferred). A ramp-down before release is the mitigation; the target-speed release (7.3) could carry it.
5. **Brief 5.8, item 3** ("linear_motor against constant_accel at the same exit speed and stroke"). v^2 = 2 ∫ sddot ds <= 2 a_max L, so any profile reaching v_e in L has a_max >= v_e^2/(2L). Constant acceleration is the minimum-peak profile, and a power limit can only raise the force-phase felt g (table in section 9: 4.23 g0 at v_c = 60 m/s). The linear motor's structural relief comes only from a longer stroke or a lower exit speed, never from the power limit at the same (v, L). It buys lower peak power (1.43 against 1.73 GW).
6. **Brief 5.10 and section 6.** The 1-D golden cannot be recaptured, which is stricter than the planar capture (section 7.6). The `TrackExit` altitude, angle and offset are taken at s = L (prelude.py:913-921), so the target-speed release needs more than an event. `push_time_estimate` has no mass argument (base.py:157-160), and a `release`-referenced ignition depends on it even after release (prelude.py:831).
7. **`AssistForces.dissipated_W`** exists but is never integrated (dynamics.py:438-472; losses.py:168). A model that needs dissipation booked must carry it as its own extra quadrature, and the budget must read it.

## 11. Recommendations in one place (for Plan mode)

1. **Put every new behaviour behind `LinearMotorConfig` and `LinearMotorAssist`:** power-limited force, rise time, target-speed release, modelled braking, sealed shaft. Leave `constant_accel`'s config, layout, assumptions, metrics keys and columns unchanged. Make new metrics, summary rows and flags conditional on the drive.
2. **Extend the protocol** with backward-compatible members: a mass-aware `push_time_estimate`, a `kink_times()` list (empty for the existing models), a release-speed accessor (None for the existing models), and a work-other quadrature name. Merge these into fly_track so that the existing models produce the same calls.
3. **P_max is mechanical at the carriage** (eta energy-only, the sensitivity stays cheap), or electrical if the user prefers the physical supply limit; state which.
4. **The rise time is a linear ramp from the holding force, with no state.** A force lag would need an `_N` atol entry.
5. **Refuse release-referenced on-track ignition (t_ign_s < 0)** on the linear motor in SP7, or root-solve it. Treat t_ign_s >= 0 as pending until the real release. Implement the depth and speed triggers from the cold closed forms with the liftoff mass.
6. **Braking is closed-form functions of the drive**, not a trace phase. The facility length is max(L, s_release + d_brake).
7. **The sealed-shaft force acts on the carriage, inside F_other**, with a `W_other_J` extra state, a `work_other` budget field and the adiabatic closed-form test.
8. **Validation tests** (brief 5.9, extended):
   - the 5.7 forms vertical and horizontal, and the ramp form s = j t^3/6;
   - F <= F_max and F sdot <= P_max at every sample;
   - the energy identity < 1e-9 with rise time, hot start and piston;
   - the hot interface formula for f_imp in {0, 0.5, 1};
   - the target-speed event at s(v);
   - the braking distance, time and energy;
   - the piston work and the p_atm A bound;
   - F_int lowered by (m_v/M) F_p;
   - the planner refuses (or flags) a stall at push start.
