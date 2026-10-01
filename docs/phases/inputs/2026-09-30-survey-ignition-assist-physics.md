# Code survey: ignition timing, the silo assist and the phase engine

Read-only survey made in the SP1 planning session on 2026-09-30. Line numbers are for
commit 2eebcae and drift as SP1 edits the files; re-check before relying on one. Input to
docs/phases/SP1-fuel-offload-planar.md (steps 2-4).

Short answer: the exit-speed option and the push half of the ramp-start triggers can both
be done as a conversion before the run, and nothing downstream needs to change. Only
`at_height_m` by event (igniting at a height during the coast after release) needs a real
altitude-triggered event.

## 1. src/launchsim/assist/

**`base.py`**

- `TrackGeometry` (36-65): `length_m`, `start_altitude_m`, `phi(s)`, `kappa(s)`, `z(s)`.
  The exit altitude is `start_altitude_m + z(L)`.
- `AssistForces` (68-86): `sddot_mps2`, `drive_force_N`, `drive_normal_N`,
  `interface_force_N`, `dissipated_W`, `extra_rate`.
- `AssistModel` (89-172) has `push_time_estimate(track)` (157). Its docstring says it is
  "the push duration the planner uses to resolve ``push_start`` ignition times and to cap
  the step", and that it is "exact for a prescribed acceleration; an estimate for a
  force-limited drive". It also has `braking_distance_m(v)` (162) and
  `facility_length_m(track, v_exit)` (166).
- `AssistBuilder.from_config(config, g_eff) -> (model, track | None)` (175-189).
- `normal_load_N` (192).

**`constant_accel.py`**, `ConstantAccelAssist` (27-191):

- Fields: `net_accel_mps2, carriage_mass_kg, brake_decel_mps2, efficiency, f_imp,
  allow_negative_drive, g_eff_mps2, omega_p_rads`.
- `from_config` (64-88) builds `StraightTrack(length_m=config.stroke_m, phi,
  start_altitude_m=exit_altitude_m - stroke_m*sin(phi))` and reads
  `config.net_accel_mps2`. **This is the only place the acceleration enters the model.**
- `state_rate` (108-133): `sddot = a`, `F_drive = M (a + g_eff sin phi) - (1 - f_imp) T`,
  `F_int = m_v (a + g_eff sin phi) - T`.
- Closed forms: `exit_speed_mps(L)` (135) = sqrt(2aL); `push_time_s(L)` (139) =
  sqrt(2L/a), valid for any length, so `push_time_s(L - d)` is already the depth
  conversion; `push_time_estimate` (143); `braking_distance_m` (147) = v^2/(2 a_brake);
  `facility_length_m` (151) = L + braking distance.
- How the other parameters are used:
  - `drive_efficiency` only divides electrical energy (`metrics.track_metrics` 485).
  - `f_imp` enters `F_drive` and `dW_thrust/dt` (`dynamics.rhs_track` 470).
  - Carriage mass goes to `TrackParams.carriage_mass_kg`.
  - `shaft: vented` is `Literal["vented"]` (`config.py:551`) and only produces assumption
    text (`constant_accel.py:187`, "shaft vented (no air column), no friction") and replay
    text.
  - `allow_negative_drive_force` decides whether `ev_drive_limit` is listed.
- `assumptions()` (174-191) prints "prescribed net acceleration {a} g0 (assumed)".

**`track.py`**: `VERTICAL = pi/2` (13). `StraightTrack(length_m, phi_rad=VERTICAL,
start_altitude_m=0)` (17-52), with `exit_altitude_m` as a property (49-52).

**`none.py`**: `NoAssist` (16-70). Push time 0, facility 0; `state_rate` raises.

**`__init__.py`**: `ASSIST_MODELS` (27) and `build_assist(config, g_eff)` (36-52).

**Config side** (`config.py`): `TrackConfig` (508-528) accepts `angle_deg` 90 only
(515-523). `ConstantAccelConfig` (537-568): `net_accel_g: float = Field(gt=0.0)` is
required, `stroke_m` is required, and the properties `net_accel_mps2`, `carriage_mass_kg`,
`brake_decel_mps2` exist.

**Assist metrics** (`metrics.track_metrics` 441-522; planar copy
`metrics_planar.planar_track_metrics` 922-982):

- Speed and time: `exit_speed_mps`, `push_time_s` (= `trace.t_release_s`).
- Felt g: `felt_g_track_peak` with `_t_s` and `_mass_kg`.
- Forces: `interface_force_peak_N` and `_min_N`, `drive_force_peak_N`.
- Energy: `drive_energy_J` / `_kWh`, `drive_work_in_J` / `_out_J`, `electrical_energy_J` /
  `_kWh`.
- Power: `drive_power_peak_W`, `_peak_t_s`, `_min_W`.
- Facility: `braking_distance_m`, `facility_length_m`.
- Other: `propellant_burned_on_track_kg`, track normal-load peaks,
  `assist_energy_residual_rel`, `track_start_altitude_m`, `carriage_mass_kg`, plus the
  aliases in `TRACK_METRIC_ALIASES` (101-106).
- There is **no acceleration metric**.

## 2. Ignition resolution, startup, events

**Config** (`config.py`):

- `IgnitionConfig` (624-636): `t_ign_s: float = 0.0`,
  `reference: Literal["release","push_start"] = "release"`,
  `startup: StartupOverride | None`, `fails`. Extra keys are refused; the handoff probe
  confirms `at_depth_m` fails with `extra_forbidden`.
- `RunConfig._ignition_rules` (1172-1182): `fails` requires `end: impact`; `push_start`
  requires an assist model.
- `ignition_for(stage)` (1184-1186).
- `resolve_run` (1764-1779): a later stage may not use `push_start` or a negative
  `t_ign_s`.

**Spec and resolution** (`phases/prelude.py`):

- `IgnitionSpec(t_ign_s, reference, startup, fails)` (75-108).
- `t_ign_abs_s(t_release_s, t_push_start_s=0.0)` (104-108):
  `origin = t_release_s if self.reference == "release" else t_push_start_s`.
- There are only two construction sites, both through `run.ignition_for`:
  `sim.ignition_specs` (803-809, used by the 1-D path and `planar_setup` 972) and
  `search.SearchContext.from_run` (549-552).

**Track case** (`fly_track`, 483-615):

- 524-531: `t_push_est = assist.push_time_estimate(track)`, then
  `t_ign = spec.t_ign_abs_s(t_push_est, t_push_start)`, then
  `tr.t_ign_abs_s[stage0] = t_ign`, then
  `schedule = stage0.schedule(t_ign, spec.startup, spec.fails)`.
- In other words, a `release` reference is resolved against the model's closed form before
  anything is integrated. docs/physics.md 3489-3491 says exactly this: "so both resolve
  before anything is integrated".
- Clamp at the shaft bottom (534-551): if `t_ign < 0` and not `fails`,
  `HoldParams(schedule, g_eff*sin(phi), p_amb)`, an `ignition` event in HOLD at `y_hold`
  (start altitude, at rest), then `hold_closed_form` from `t_ign` to 0. There is no
  liftoff extension: the push starts at t = 0 whatever the thrust.
- The push is split at `schedule.kink_times()` (565-603). A sub-phase that ends at the
  ignition kink is unlit (`track_params` -> `is_lit`).
- Events logged on the track: `push_start` (569), `ignition` (572-573, at the first lit
  sub-phase start), `drive_limit`, `ramp_end` (599-603).

**Pad case** (hold-down):

- `VerticalPlanner.run_pad` (`vertical.py` 235-289) and `PlanarPlanner.start_pad`
  (`planar.py` 819-883) both refuse anything other than `reference: release`.
- The hold runs from `t_ign` to 0, then `hold_until_liftoff` (`prelude.py` 290-381) until
  T > m g.

**Thrust schedules** (`vehicle.py`):

- `Startup` (62-91), `thrust_fraction(startup, dt)` (94-106).
- `Stage.schedule(t_ign_abs_s, startup, fails)` (205-219).
- `ThrustSchedule` (223-268) uses `t - t_ign_abs_s`; `kink_times()` is
  `(t0, t0 + t_ramp)` for a ramp and `(t0,)` otherwise.
- `propellant_burned_kg` (271-295).
- Step caps come from `prelude.max_step_cap` (149-163). **Everything is a function of an
  absolute ignition time.**

**Events** (`engine.py`):

- `EventSpec(name, fn(t, y), terminal, direction, zero_tol)` (165-187).
- Factories: `ev_propellant` 579, `ev_apex` 594, `ev_turnaround` 608, `ev_impact` 622,
  `ev_liftoff` 636, `ev_track_end` 664, `ev_drive_limit` 678, `ev_ground` 700,
  `ev_radial_apex` 725, `ev_radial_turnaround` 741, `ev_kick_start` 752 (a state
  condition: `min(V - v_k, w)`), `ev_kick_aligned` 776, `ev_time` 797.
- `ignition`, `ramp_end`, `release`, `push_start`, `liftoff` and `staging` are **logged**
  by the planners with `tr.add_event`. Apart from `liftoff`, they are not root-finding
  events: they sit at kinks or maps.
- The engine fully supports state-triggered events: `ev_impact` and `ev_ground` are
  altitude crossings. A terminal `ev_altitude(h)` is straightforward.

**Planar sequence around release** (`planar.py`):

- `start_track` 908-914: `y_rel = map_release_planar(...)`, then
  `tr.add_event("release", t, ASSIST_KIND, 0, y_rel)`, then
  `t_ign = tr.t_ign_abs_s.get(stage0.name)`, then `_begin_flight(tr, t, y_rel, t_ign)`.
- `_fly_to_kick` 1461-1478:
  - `schedule = stage0.schedule(t_ign, ...)`
  - `if t_ign > t + ZERO_SPAN_S: t, y, how = self._coast(tr, COAST_PRE_IGN, 0, t, t_ign,
    y, hint=hint)`
  - Then `kick_now = trigger.fn(t, y) > trigger.zero_tol`
  - Then `tr.add_event("ignition", t, KICK if kick_now else VERTICAL_RISE, 0, y)`
  - Then VERTICAL_RISE through `_burn` (1394-1444; `ramp_end` at 1441-1442), with
    `kick_deadline = ev_time(t_ign + deadline)`.
- `_coast` (1344-1392) only takes `t_end` and lists the apex event (rising) or the ground
  event (falling). **It has no hook for extra events.**

**What igniting on "altitude >= h" in COAST_PRE_IGN takes:**

1. A trigger field on `IgnitionSpec` and its config.
2. `fly_track` has to build an unlit track schedule for the pending trigger and not set
   `tr.t_ign_abs_s`.
3. `FlightStart.t_ign1_s = None` currently means **failed ignition** (`run` 1039-1042,
   `to_kick` 946, `search._kick` 605-606; also `sim._solve_fixed_delta` 1345-1348). A
   separate "pending trigger" state is needed.
4. `_coast` needs an `extra` events argument plus an `ev_altitude` factory (+1 direction,
   `ATOL_M` tolerance). Altitude is monotone in a rising coast because the coast is split
   at the apex.
5. Set `t_ign` to the root time, then build the schedule and the deadline.
6. A rule for an apex reached before h, and for a release already above h (the planner
   should decide that itself, as it does for `kick_now`, so no engine flag fires).
7. The same for 1-D `ascend` (`vertical.py` 367-404), which writes `tr.t_ign_abs_s` before
   the coast, and for `_coast` (561-624).

## 3. Release mapping and the cold coast

- **1-D:** `map_release(sdot, m, phi, exit_alt)` (`vertical.py` 120-145) gives z = exit
  altitude, v = sdot, quadratures 0, and refuses a non-vertical track.
  - The coast `COAST_PRE_IGN` / `FALL_PRE_IGN` uses `rhs_vertical` with
    `InverseSquareGravity(mu)`: mu/r^2, no drag (Phase 1 has no atmosphere), omega_p = 0.
  - Events: apex (rising) or impact (falling).
- **Planar:** `map_release_planar` (`planar.py` 392-420) gives r = R_E + z_e, theta = 0,
  v_r = sdot, v_theta = omega_p r.
  - The coast uses `rhs_planar` with mu/r^2, omega_p of the site, ICAO atmosphere, and
    drag from the power-on C_D table (an assumption, `sim.py` 863-864).
  - The step cap is 2 s. `t_fs = t_release`, and the view is rebound so downrange counts
    from the mouth.
- **Track:** flat, with constant `g_eff = g_ref = mu/R_E^2 - omega_p^2 R_E`
  (`dynamics.g_eff_track` 114) and constant `p(z_exit)`.
- The handoff probe confirms a constant-g, drag-free coast matches the recorded
  `silo_cold` run to about 0.01 m at +0.5 s.

## 4. Time series and events.csv

**Time series columns:**

- 1-D (`metrics.py` 60-85): `t_s, z_m, v_mps, m_kg, t_rel_release_s, thrust_N,
  thrust_vac_N, accel_felt_g, phase, stage, J_*`, plus `s_m, drive_force_N,
  interface_force_N, drive_power_W, track_normal_g_*` (NaN outside ASSIST rows). The 1-D
  column is **`z_m`, not `alt_m`**.
- Planar (`metrics_planar.py` 287-337): `alt_m` (negative in the silo, from `_track_part`
  493), `downrange_m, speed_rel_mps, ..., thrust_vac_N, ...`, and the same track columns.
- Phase names: 1-D `HOLD, ASSIST, COAST_PRE_IGN, FALL_PRE_IGN, BURN, COAST_STAGING,
  FALL_STAGING, COAST, FALL`; planar `HOLD, ASSIST, COAST_PRE_IGN, VERTICAL_RISE, KICK,
  GRAVITY_TURN, COAST_STAGING, LTG_BURN, COAST`.

**events.csv:**

- 1-D: `t_s, event, phase, stage, z_m, v_mps, m_kg` (87).
- Planar: `t_s, event, phase, stage, alt_m, downrange_m, speed_rel_mps,
  speed_inertial_mps, gamma_rel_rad, m_kg` (369).

**Every relevant record carries the state:** `push_start` (s = 0); `ignition` on the track
(recorded through `prelude.from_track`: `track_to_vertical` in 1-D,
`planar_prelude.from_track` 432-441), exactly at the kink; `ignition` in a hold (altitude
-L, speed 0); `ramp_end`; `release` (the state after the release map). So depth below the
mouth = (mouth altitude - alt) and speed (`speed_rel_mps`, or `|v_mps|` in 1-D) can be
reported as metrics from `trace.first_event("ignition")`, filtered to stage 1.

**Caveat on the 1-D golden test:** `compare_tree` (`tests/golden_1d_support.py` 599-612)
requires the metric key lists to be identical. Any new key in 1-D `track_metrics` or
`ignition_timing_metrics` breaks it. Put new metrics in `metrics_planar` only.

## 5. docs/physics.md headings (line numbers)

1 title, 26 Atmosphere (subsections at 46, 101, 128), 137 Atmosphere, drag and
back-pressure in flight, 333 Frames and datum, 368 1-D ascent state and equations of
motion, 429 Gravity, 494 Planar ascent state and equations of motion, 648 2-D loss
identity, 750 Planar reductions, 813 Orbital elements and the circular target, **840
Planar release map**, **947 Stage-1 guidance and events (planar)**, 1169 gamma* inner
solve, 1350 Time-shift mechanism (2-D gravity loss), 1418 Stage 2 and insertion (planar),
1597 LTG shooting, 1732 Rocket-equation closure (planar), 1815 Max-Q and loads (planar),
**1877 Figures of merit (planar)**, 1948 Virtual propellant, **2005 Payload and gamma\*
search**, 2284 Shared budget, 2312 Convergence (planar), 2512 Performance (measured), 2687
Screening-beat rule (2-D), **2951 Reporting definitions (planar)**, **3106 Thrust
startup**, 3126 Integrator, **3258 Event rules**, **3436 Phases and events**, 3599 Loss
accounting, **3670 Ignition-after-release loss**, **3731 Assist energy identity**, **3786
Silo model (constant_accel, vertical)**, **3914 Hot start**, 4007 Failed-ignition coast,
**4164 Figures of merit in 1-D**, 4314 Convergence, **4374 Experiment schema (planar)**,
**4533 Assumptions**, 4748 Calibration notes, **4775 Phase 2 research notes**, **4796
Test-to-equation map**.

**Sections a change to the ignition parameterisation must update:**

- Phases and events: the "Clock and ignition times" paragraph (3485-3497) and the
  COAST_PRE_IGN row (3519).
- Hot start (3916-3922).
- Silo model: the closed forms (3798-3822) and the reported-quantities table.
- Stage-1 guidance and events (planar): the COAST_PRE_IGN row (995).
- Event rules table (3268-3276), for the state-triggered event.
- Experiment schema (planar), and Assumptions (4614-4625, the constant_accel lines).
- Test-to-equation map.
- For the exit-speed option, the derived a = v^2/(2L) goes in Silo model and Assumptions.

**Sections a new figure of merit must update:** Figures of merit (planar), Virtual
propellant, Payload and gamma\* search, Shared budget, Convergence (planar),
Screening-beat rule (2-D), Reporting definitions (planar), Experiment schema (planar),
Assumptions, Test-to-equation map.

## 6. Tests

- **tests/test_silo.py**
  - The closed forms at 1e-10: `test_cold_push_kinematics_and_drive_force` (125: exit
    speed, push time, s = a t^2/2, z = -L + s).
  - `test_drive_limit_when_a_ramp_crosses_zero_drive_force` (336:
    `IgnitionSpec(2.0, reference="push_start")`, quadratic root to 1e-9).
  - `test_drive_force_negative_at_push_start_ends_at_t0` (392: hot full start via
    `_hot_full` = `IgnitionSpec(-t_r, reference="push_start")`).
  - `test_ramp_ending_at_the_track_end_is_logged_once` (444: ignition at t_push - t_r;
    with `push_start` 0.5, `ramp_end` at 0.5 + t_r, 1e-12).
  - Energy and power tests at 507, 543 and 595.
- **tests/test_assist_energy.py**: 169 (hot full, `push_start`), 181 (planar prelude,
  `push_start`), 207 (ignition at sqrt(2L/A) - t_r, 1e-12).
- **tests/test_events.py**: 505 (release from the track;
  `events[:2] == ["push_start","release"]`).
- **tests/test_release_planar.py**: 101 (planar silo release), 129 (ignition 0.5 s after
  release, Coriolis drift).
- **tests/test_phases_package.py**: about 396 (dense output off gives the same
  `["push_start","ignition"]`) and 736 (tilted track).
- **tests/test_config.py**: 249 (`push_start` rules) and 520-540 (shipped resolution).
- Others: `test_failed_ignition.py` 352 (flags `reference = 'push_start'`),
  `test_ignition_loss.py` 211 (ramp straddling the release through the silo),
  `test_hold.py` (pad hold-down), `test_planar_events.py` 198/271/410/453,
  `test_closure.py` 263 and `test_loss_identity_2d.py` 61 (hot full `push_start`).
- Golden input `tests/data/golden/inputs/vertical_1d_paths.yaml` uses `silo_drive_limit`
  with `t_ign_s: 2.0, reference: push_start`.

**docs/findings/probes/handoff-2026-09-30/probe_ign_table.py:** pure closed forms:
a = 3 g0, L = 100 m, g_eff = 9.7720917, a 2 s ramp. `where(t)`: for t <= 0, clamped at
-L; on the track, z = -L + a t^2/2 and v = a t; after release, a drag-free constant-g
coast z = v_e dt - g dt^2/2. `t_abs = t_ign` for `push_start`, otherwise t_push + t_ign.
Inverse: t = sqrt(2(L - d)/a). A minor floating-point artefact mislabels rows at exactly
t = 0 ("on the track" while z = -100, v = 0).

## 7. What assumes time-based ignition

**With conversion before the run, nothing breaks**: every consumer reads
`t_ign_s`/`reference` or the trace's `t_ign_abs_s`. The direct readers of
`spec.t_ign_s`/`spec.reference` only need new refusals or cosmetic updates:

- `prelude.flag_ignored_ignition_settings` (115-134).
- The pad paths (`run_pad` 250, `start_pad` 832).
- `sim.planar_run_assumptions` (1056, pad only).
- The later-stage checks (`planar.py` 780, `vertical.py` 372, `config.py` 1766-1775).
- `replay.py` 478 and 675 read the raw `assist.net_accel_g` from `resolved_config` (the
  raw run dict). That would be missing for a run defined by exit speed.

**An existing time-based assumption:** the `release` reference already resolves against
`push_time_estimate`, which is only an estimate for a force-limited drive (Phase 3).

**A state-triggered ignition needs the items listed in section 2**: the unlit `fly_track`
schedule, `FlightStart.t_ign1_s` meaning "failed", `search._kick`, both `_coast` methods,
`ascend`, a new event factory.

**Merge pitfall (applies to every design):** `merge_run_dicts` (1519) merges by key. The
shipped baselines carry `ignition: {stage1: {t_ign_s: -2.0, reference: release}}`, so a
variant that writes `{at_depth_m: 50}` inherits `t_ign_s` and `reference`. Likewise the
`*silo` anchor carries `net_accel_g` into any variant that adds `exit_speed_mps`. The
approved design handles this with exclusive key families in the merge and in `_set_path`.

## Closed forms for the conversions (constant_accel)

- Depth d below the mouth: t (from push start) = sqrt(2 (L - d) / a).
- Speed v on the push: t (from push start) = v / a.
- Height h above the mouth, closed form: dt after release =
  (v_e - sqrt(v_e^2 - 2 g_eff h)) / g_eff, valid for h < v_e^2 / (2 g_eff). It is exact
  only for a drag-free constant-gravity coast; under drag, mu/r^2 and rotation it is off
  by centimetres to decimetres, growing with h. The achieved height is reported from the
  event record.
