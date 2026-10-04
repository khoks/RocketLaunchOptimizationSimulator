# 5. Assist and ignition

[Manual contents](README.md) · Previous: [4. Experiment files](04-experiments.md) · Next: [5b. Propellant offload at fixed payload](05b-offload.md)

Two blocks of a run decide what makes a silo run different from the pad: `assist` (the
ground push) and `ignition` (when and how each stage's engines start). This chapter lists
every key of both, with the rules the config enforces.

## Assist models

| `model` | Status | What it is |
|---|---|---|
| `none` | built | The pad: no track phase. The baseline of every shipped experiment |
| `constant_accel` | built | A prescribed constant net acceleration along a straight track: the screening drive used for the vertical silo |
| `linear_motor` | planned, README roadmap Phase 3 | A force- and power-limited drive. Refused today: `assist model 'linear_motor' is planned for Phase 3` |
| `cable_winch` | planned, README roadmap Phase 3 | Drum, cable as a spring-damper, pulleys. Refused the same way |

### `constant_accel` keys

| Key | Default | Rule | Meaning |
|---|---|---|---|
| `model` | required | `constant_accel` | |
| `stroke_m` | required | > 0 | Track length L [m] |
| `net_accel_g` | one of the two | > 0 | Net acceleration along the track, in g0 |
| `exit_speed_mps` | one of the two | > 0, finite | Speed at the track exit [m/s]; the acceleration is derived, a = v^2 / (2 L) |
| `carriage_mass_t` | 0 | >= 0 | Carriage mass [t]. It stays on the track at release |
| `brake_decel_g` | required | > 0 | Carriage braking deceleration, in g0 |
| `drive_efficiency` | 1.0 | 0 < eta <= 1 | Electrical energy = positive drive work / eta. The shipped files use 0.5 (assumed) |
| `exhaust_impingement_fraction` | 0 | 0 to 1 | Fraction of the on-track thrust lost to exhaust hitting the carriage: the system keeps (1 - f) T (an assumed amendment to the track equation) |
| `shaft` | `vented` | `vented` only | No air column and no air drag in the shaft |
| `allow_negative_drive_force` | false | | Let the drive pull back on the vehicle (see `drive_limit` below) |
| `track.angle_deg` | 90 | 90 only | Track angle above horizontal. Anything else: `track angle_deg other than 90 is a Phase 3 feature` |
| `track.exit_altitude_m` | 0 | | Altitude of the track exit (the silo mouth) above the pad datum [m]. The track starts L below it |

The shipped silo, from `experiments/silo_screening_2d.yaml` (the same in the 1-D file):

```yaml
assist: {model: constant_accel, net_accel_g: 3.0, stroke_m: 100,
         carriage_mass_t: 0, brake_decel_g: 5, drive_efficiency: 0.5,
         exhaust_impingement_fraction: 0.0, shaft: vented,
         track: {angle_deg: 90, exit_altitude_m: 0}}
```

That is a 100 m shaft whose mouth is at ground level, pushing at 3 g net. The exit speed is
76.7 m/s after a 2.6 s push, the carriage brakes at 5 g over 60 m, and the facility is
160 m long (README).

### What the drive does, and what it does not model

- **The acceleration is prescribed.** The drive supplies whatever force keeps the net
  acceleration at a: F_drive = M (a + g_eff sin phi) - (1 - f) T, with M the vehicle plus
  carriage mass. The force is unbounded. That is why a hot start cannot add exit speed in
  this model, and why carriage mass and drive efficiency change only energy and power,
  never the trajectory.
- **The push from rest:** exit speed sqrt(2 a L), push time sqrt(2 L / a), and a felt axial
  acceleration of a + g_eff on a vertical track (the full stack at 3 g net feels about 4 g).
- **Braking is a length, not a phase.** The braking distance v^2 / (2 a_brake) is added to
  the stroke to give the facility length.
- **The shaft is vented.** No air column (no piston force) and no air drag on the vehicle
  in the shaft. The README estimates this biases drive energy, peak power and interface
  force low by about 0.04%, 0.08% and 0.08%, and leaves payload unchanged.
- **The track phase is flat and 1-DOF**, with a constant g_eff = mu/R_E^2 - omega_p^2 R_E;
  Coriolis is neglected. The jerk at push start and release is infinite.
- **No regeneration.** If the drive brakes, the braking work is reported but no
  electricity is credited back.

**`drive_limit`.** If the thrust on the track ever exceeds what the prescribed acceleration
needs, the drive force would have to turn negative. The run then stops on the track at that
point with status `drive_limit` and never releases. With
`allow_negative_drive_force: true` the drive pulls back instead, the run continues, and the
`drive_braking` flag says how much negative work the drive did. A negative interface force
anywhere on the push raises the `interface_tensile` flag (the vehicle would have to be held
down on its carriage).

### Stating the push two ways

`constant_accel` takes exactly one of `net_accel_g` or `exit_speed_mps` beside `stroke_m`.
With the exit speed v and the stroke L the model uses a = v^2 / (2 L), so depth and exit
speed can be set independently: a deeper silo reaches the same speed at a lower
acceleration.

| Quantity | In v and L |
|---|---|
| net acceleration | a = v^2 / (2 L) |
| push time | 2 L / v |
| felt axial acceleration on a vertical track | v^2 / (2 L) + g_eff |
| cold drive energy, vertical | M (v^2 / 2 + g_eff L) |
| cold peak drive power, vertical (at release) | M (v^2 / (2 L) + g_eff) v |
| braking distance | v^2 / (2 a_brake), independent of L |

At a fixed exit speed, doubling the stroke halves the acceleration, doubles the push time
and lowers the felt g, the forces and the peak power; the drive energy rises only by the
extra potential energy M g_eff L.

Written for this manual (not in a shipped file): a 200 m silo that releases at the same
76.7 m/s as the shipped one, at a gentler acceleration.

```yaml
variants:
  silo_deep_cold:
    assist: {model: constant_accel, exit_speed_mps: 76.7, stroke_m: 200,
             carriage_mass_t: 0, brake_decel_g: 5, drive_efficiency: 0.5,
             exhaust_impingement_fraction: 0.0, shaft: vented,
             track: {angle_deg: 90, exit_altitude_m: 0}}
    ignition: {stage1: {t_ign_s: 0.5}}
```

Write the assist dict out like this. `{<<: *silo, exit_speed_mps: 76.7}` is refused,
because the anchor brings `net_accel_g` into the same dict and the two keys belong to
exclusive families ([4. Experiment files](04-experiments.md#merge-rules)).

A sweep can vary exit speed and depth together. Written for this manual, over the shipped
silo_cold (the axis replaces its `net_accel_g` at every point):

```yaml
sweeps:
  - {of: silo_cold, axes: {assist.exit_speed_mps: [50, 77, 100], assist.stroke_m: [100, 300]}}
```

A 2-D run records the push it flew in `metrics.json` (`stroke_m`, `net_accel_mps2`,
`net_accel_g`), whichever way it was stated, and a push stated by its exit speed adds an
assumption line to the summary.

## Ignition

`ignition` is a dict keyed by the vehicle's stage names (`stage1`, `stage2` in the shipped
vehicles). A stage that is not listed ignites at its defaults.

| Key | Default | Meaning |
|---|---|---|
| `t_ign_s` | 0.0 | When the thrust ramp starts, relative to `reference` [s]. Negative means before |
| `reference` | `release` | `release` or `push_start` |
| `at_depth_m`, `at_speed_mps`, `at_height_m` with `height_method` | none | Other ways to state the stage-1 ramp start (below) |
| `startup` | the vehicle's | Override of the startup shape: `{kind, t_ramp_s, tau_s}` |
| `fails` | false | The stage never produces thrust. Requires `end: impact` |

### Timing by time: `t_ign_s` and `reference`

- `reference: release`, stage 1: relative to the track exit on a silo run, or to the
  hold-down release (t = 0) on a pad. A negative time lights the engines on the track or
  while clamped on the pad.
- `reference: release`, later stages: relative to the end of the stage's staging coast.
  A later stage must have `t_ign_s >= 0`.
- `reference: push_start`: relative to the start of the push. First stage only, and only on
  a run with an assist (a pad has no push). With a negative `t_ign_s` the vehicle is clamped
  on the carriage until the push starts.

From `experiments/silo_screening_2d.yaml`:

| Run | `ignition.stage1` | Effect |
|---|---|---|
| `pad` | `{t_ign_s: -2.0, reference: release}` | Lit 2 s before release, held down through its 2 s ramp |
| `silo_cold` | `{t_ign_s: 0.5}` (reference inherited: `release`) | Lit 0.5 s after the mouth |
| `silo_hot_ramp_on_track` | `{t_ign_s: -2.0, reference: release}` | Lit on the carriage, full thrust at release |
| `silo_hot_full` | `{t_ign_s: -2.0, reference: push_start}` | Lit 2 s before the push starts, so full thrust for the whole push (the summary shows -4.607 s relative to release) |
| `pad_instant`, `silo_instant` | `{t_ign_s: 0.0, startup: {kind: step}}` | Full thrust at release: a yardstick, unphysical |

### Startup shapes

The vehicle file sets each stage's startup; an ignition's `startup` overrides it. With f the
thrust fraction and dt the time since ignition:

| `kind` | Shape | Duration key |
|---|---|---|
| `step` | f = 1 from ignition: instant full thrust (no real engine does this) | none |
| `ramp` | f = dt / t_ramp, capped at 1 | `t_ramp_s` |
| `lag` | f = 1 - exp(-dt / tau) | `tau_s` |

A ramp or lag with a zero duration is a step. Mass flow follows the vacuum thrust. An
override keeps the vehicle's values for what it does not set; switching to `ramp` or `lag`
needs its duration (from the override or the vehicle), and a duration given for another
shape is refused. From `experiments/silo_screening_2d.yaml`:

```yaml
silo_cold_lag:    {assist: *silo, ignition: {stage1: {t_ign_s: 0.5, startup: {kind: lag, tau_s: 1.0}}}}
```

**What a late start costs.** In 1-D the loss is exact: g (t_d + t_r / 2) for a delay t_d
and a linear ramp t_r, and g (t_d + tau) for a lag, so a lag costs as much as a ramp twice as
long ([RQ2-1d](../findings/RQ2-ignition-timing-1d.md)). In 2-D it is larger: on the gate
vehicle the 0.5 s delay and 2 s ramp of silo_cold give back 327.1 kg (34.74 m/s) against an
instant start, 2.37 times the 1-D formula ([RQ2-2d](../findings/RQ2-ignition-timing-2d.md);
preliminary, sweep-optimized, unthrottled).

### Failed ignition: `fails: true`

The stage's thrust is zero for the whole run. The run must end at `impact`, and in 2-D the
search is skipped (there is nothing to optimise). From `experiments/silo_screening_2d.yaml`:

```yaml
silo_failed:      {assist: *silo, ignition: {stage1: {fails: true, t_ign_s: 0.0}}, end: impact}  # no search
```

The vehicle coasts up from the mouth, falls back and hits the ground; no abort is modelled.
In 2-D the apex is 300.65 m at 7.843 s and the stack is back at the mouth at 15.689 s at
76.60 m/s, 0.4 m from the axis (README; [RQ3-2d](../findings/RQ3-silo-screening-2d.md)).
The braked carriage parks 60 m above the mouth, in the fall-back path.

### Ramp start by depth, speed or height

The stage-1 ramp start can also be stated by where it happens on the push or above the
mouth (SP1 steps 3 and 4). A depth, a speed or a closed-form height is converted to a time
before the run, so the rest of the simulator sees a `(t_ign_s, reference)` pair. A height
by event is not converted: stage 1 lights when the flown coast after release crosses that
height.

| Setting | Converts to | Closed form | Refused when |
|---|---|---|---|
| `at_depth_m: d` (d >= 0) | time from push start | t = sqrt(2 (L - d) / a) | d > L (deeper than the track) |
| `at_speed_mps: v` (v >= 0) | time from push start | t = v / a | v above the exit speed (the push never reaches it) |
| `at_height_m: h` (h > 0), `height_method: closed_form` | time after release | the smaller root of v_e t - g_eff t^2 / 2 = h (a drag-free coast at constant g_eff) | h at or above the drag-free apex v_e^2 / (2 g_eff) |
| `at_height_m: h` (h > 0), `height_method: event` | nothing: an altitude event in flight, at the mouth's altitude + h on the coast after release | none (the crossing is found in flight) | h at or above the drag-free apex v_e^2 / (2 g_eff), as for the closed form; in flight, a coast that peaks below the height (below) |

Rules:

- First stage only, and only on a run with a `constant_accel` assist. On a pad:
  `a ramp start by at_depth_m needs an assist model (a pad run has no push and no track exit)`.
- One way only: the four forms are one exclusive family group
  ([4. Experiment files](04-experiments.md#merge-rules)). A variant that sets `at_depth_m`
  over the baseline's `t_ign_s` and `reference` replaces them; giving both together is
  refused.
- `at_height_m` and `height_method` come together.
- Depth and speed are exact: the ignition event lies at the requested depth and speed. They
  always fall inside the push, so they never start a hold; full thrust at the push start
  still needs `t_ign_s < 0` with `reference: push_start`.
- The closed-form height is exact only for a drag-free coast at constant gravity. The flown
  coast has drag, 1/r^2 gravity and rotation, so it reaches a slightly different height
  (on the gate vehicle the closed form lights 3.8 mm below 40 m and 0.11 m below 200 m;
  [docs/physics.md](../physics.md), "Silo model"); both the requested and the achieved
  height are reported.
- The event height is exact to the event tolerance: stage 1 lights at the crossing, and
  the thrust schedule, its ramp and the kick deadline count from there as for a time-lit
  stage. events.csv records an `ignition_height` event right before the `ignition` it
  triggers. Since nothing is converted, `ramp_start_requested_t_s` is empty for it.
- **The `no_ignition` band (event only).** The preflight refuses a height at or above the
  drag-free apex v_e^2 / (2 g_eff), but on `planar_2d` drag makes the flown coast peak
  lower. For the shipped 3 g, 100 m silo on the gate vehicle the flown apex is about
  300.65 m against the drag-free 301.06 m, and it moves with payload and C_D (300.61 to
  300.69 m over the values measured; [docs/physics.md](../physics.md), "Silo model"). A
  height inside that band of about 0.4 m resolves but never lights: a fixed-guidance run
  ends `guidance_failed` (kind `no_ignition`), and a searched run ends `search_failed`
  (kind `grid`, naming no_ignition). Such runs are reported, never hidden. Keep event
  heights well below the apex; the shipped sweep stops at 200 m.
- A request only the conversion or the apex check can refuse (a speed above the exit
  speed, a height at or above the drag-free apex) is caught before any results directory
  is made, as one `error:` line.
- With `fails: true` the conversion (or the apex check) still runs, and the request is
  flagged as ignored; a failed stage stated by a height event is a failed-ignition run with
  no altitude event.

Written for this manual, four ramp starts on the shipped silo (each is a variant over the
pad baseline, so the full assist dict is given through the shipped anchor):

```yaml
variants:
  silo_ramp_at_50m_depth:   {assist: *silo, ignition: {stage1: {at_depth_m: 50}}}
  silo_ramp_at_30mps:       {assist: *silo, ignition: {stage1: {at_speed_mps: 30}}}
  silo_ramp_40m_above_exit: {assist: *silo, ignition: {stage1: {at_height_m: 40, height_method: closed_form}}}
  silo_ramp_40m_by_event:   {assist: *silo, ignition: {stage1: {at_height_m: 40, height_method: event}}}
```

To sweep the event height, give its two keys as two axes, so the rest of the ignition dict
is kept. From `experiments/silo_offload_2d.yaml` (its fourth sweep, which also solves an
offload case at every point; [5b](05b-offload.md#sweeps-that-name-offload-cases)):

```yaml
  - {of: silo_cold, axes: {ignition.stage1.at_height_m: [10, 40, 100, 200],
                           ignition.stage1.height_method: [event]}, offload: [silo_cold_s1]}
```

A 2-D run reports the achieved ramp start from the stage-1 ignition event
(`ramp_start_t_rel_release_s`, `ramp_start_alt_m`, `ramp_start_depth_m` or
`ramp_start_height_m`, `ramp_start_speed_mps`, `ramp_start_phase`) and, for a ramp start
stated by depth, speed or height, the request (`ramp_start_trigger`: `depth`, `speed`,
`height_closed_form` or `height_event`; `ramp_start_requested_t_s`, empty for
`height_event`; and the requested value). The summary shows ramp-start rows only when some
run uses one of these forms, and the run gets an assumption line that names the request
and its closed form (for the event, that nothing is converted).

## The `offload:` block

The SP1 question, how much propellant the push replaces at a fixed payload, is set up with
an `offload:` block in the experiment file. Its keys, the runs it writes and the switches
that skip it are in [5b. Propellant offload at fixed payload](05b-offload.md).

Next: [5b. Propellant offload at fixed payload](05b-offload.md)
