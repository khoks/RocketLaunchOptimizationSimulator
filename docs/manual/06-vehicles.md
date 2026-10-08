# 6. Vehicle files

[Manual contents](README.md) · Previous: [5b. Propellant offload at fixed payload](05b-offload.md) · Next: [7. Commands](07-commands.md)

A vehicle file under `configs/vehicles/` describes one rocket: its stages and engines, the
fairing and payload, the screening Isp values and, for the 2-D model, its aerodynamics.
Unlike experiment files, **every number in a vehicle file carries its provenance.**

## Sourced quantities

Every number is a quantity: a mapping with a `value` and exactly one of `source` or
`assumed: true`, plus an optional `note`.

```yaml
dry_mass_t: {value: 22.2, source: "Espace & Exploration No.39 via Wikipedia Falcon 9 Full Thrust (en.wikipedia.org/wiki/Falcon_9_Full_Thrust, first-stage empty mass)"}
t_ramp_s: {value: 2.0, assumed: true, note: "linear ramp; F9 ignites at T-3 s and holds down"}
```

(Both lines are from `configs/vehicles/generic_f9_class_2d.yaml`.)

The loader refuses a bare number (`bare value; vehicle files need {value, source} or
{value, assumed: true}`), both or neither of `source` and `assumed`
(`give exactly one of source or assumed: true`), a blank source, and NaN or infinity. A
table such as the drag curve carries one provenance for all its lists.

When a sweep, sensitivity case or bound changes a vehicle number through a `vehicle.` path,
the new value is recorded as `{value, assumed: true, note: override}`, so a perturbed
vehicle never looks sourced.

## Keys

(The display files under `configs/display/`, which the launch scene draws from and the
run path never reads, are described at the end of this chapter.)

### Top level

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | Vehicle name (printed in summaries) |
| `description` | no | Free text |
| `stages` | yes | Stages in firing order (at least one; names unique). The 2-D model needs exactly two |
| `fairing_mass_t` | yes | Fairing mass [t] |
| `payload_mass_t` | yes | The vehicle payload P0 [t], used by the fixed-payload figures of merit |
| `fairing_drop` | no (default `staging`) | `staging`, `never`, or a block (below) |
| `screening` | no | Effective per-stage Isp for the ideal rocket-equation screening |
| `aero` | 2-D: yes | Reference area, drag-scale knob and the C_D(Mach) table |

### A stage

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | The stage name; experiment files key `ignition` by it (`stage1`, `stage2`) |
| `dry_mass_t` | yes | Dry mass [t] (>= 0) |
| `propellant_mass_t` | yes | Propellant load [t] (> 0) |
| `engine.count` | yes | Number of engines (a positive integer) |
| `engine.thrust_vac_kN` | yes | Vacuum thrust per engine [kN] |
| `engine.isp_vac_s` | yes | Vacuum Isp [s]; exhaust velocity c = g0 Isp |
| `engine.thrust_sl_kN` | no | Sea-level thrust per engine [kN], used only to derive the nozzle exit area, (T_vac - T_sl) / p_sea_level |
| `engine.exit_area_m2` | no | Exit area per engine [m^2], instead of `thrust_sl_kN` (not both). With neither, the exit area is 0: no back-pressure |
| `startup` | no (default `step`) | `{kind: step}`, `{kind: ramp, t_ramp_s: ...}` or `{kind: lag, tau_s: ...}` (durations are quantities) |
| `coast_before_ignition_s` | no (default 0) | Coast between the previous stage's separation and this stage's ignition [s] |

Delivered thrust is T = max(0, T_vac - p_ambient A_exit); mass flow follows the vacuum
thrust.

### Fairing drop

| Form | Meaning |
|---|---|
| `staging` | Dropped with stage 1 |
| `never` | Carried to the end |
| `{trigger: free_molecular_heating, limit_W_m2: <quantity>}` | Dropped when 0.5 rho V^3 falls below the limit (2-D only; refused on `vertical_1d`) |

The 2-D Falcon 9-class files use the heating rule with 1,135 W/m^2, sourced to the Falcon
User's Guide.

### Screening

```yaml
screening:
  stage_isp_eff_s:
    - {value: 295, assumed: true, note: "README stage-1 average Isp between sea level and vacuum"}
    - {value: 348, source: "en.wikipedia.org/wiki/Falcon_9 specification table, second-stage Isp 348 s (vacuum stage)"}
```

One entry per stage. These loss-averaged Isp values feed only the ideal rocket-equation
screening (the README's hand estimate and the screening yardstick of
[9. Reading results](09-reading-results.md#the-screening-yardstick-and-the-screening-beat-rule)),
never the flight. A sensitivity case on `vehicle.screening.stage_isp_eff_s.0` therefore
moves the yardstick and leaves the flown payload unchanged.

### Aerodynamics (2-D)

| Key | Meaning |
|---|---|
| `reference_area_m2` | Drag reference area [m^2] (10.52 m^2, the 3.66 m body, on the 2-D files) |
| `cd_scale` | A multiplier on C_D, 1.0 nominal. Required, so a `vehicle.aero.cd_scale` sensitivity case always finds its nominal value |
| `interpolation` | `pchip` (the only choice) |
| `cd_mach` | `{mach: [...], cd: [...], source or assumed: true, note}`: equal lengths, Mach strictly increasing from >= 0, C_D >= 0. Held at the end values outside the table |

The shipped table is a generic launcher curve (Braeunig 2020, marked `assumed: true`), not
Falcon 9 data. Drag acts along the velocity relative to the co-rotating air.

## The shipped vehicles

| File | Used by | Masses (stage 1 dry / propellant, stage 2 dry / propellant, fairing) |
|---|---|---|
| `generic_f9_class.yaml` | `silo_screening_1d.yaml` | README masses: 25.6 / 395.7, 3.9 / 92.67, 1.9 t; no aero block |
| `generic_f9_class_2d.yaml` | Every 2-D experiment except the two README-loads bridges: the **gate vehicle**, mass set C | Full Thrust table: 22.2 / 410.9, 4.0 / 107.5, 1.7 t |
| `generic_f9_class_2d_readme_loads.yaml` | `silo_bridge_2d_readme.yaml`, `silo_offload_2d_readme.yaml`, calibration case `readme_loads`: mass set A | README masses with the 2-D additions |
| `generic_f9_class_2d_recorded_scope.yaml` | Calibration case `recorded_scope`: mass set B | 25.6 / 410.9, 4.0 / 107.5, 1.9 t |

All four share the engines (nine 914.1 kN Merlin-class engines at 311 s vacuum Isp with a
2 s ramp; one 981 kN upper-stage engine at 348 s with a step start) and a 22.8 t payload.
The three 2-D forks add an 11 s staging coast, an 8.6 m^2 upper-stage exit area (assumed),
the heating-rule fairing and the aero block. Each file's header lists its sources and its
differences from the 1-D file.

**Calibration** (labelled calibration, not validation;
[CAL-f9-leo-2d](../findings/CAL-f9-leo-2d.md)): to 200 km circular at 28.5 degrees, due
east, expendable, against SpaceX's published 22,800 kg, the gate vehicle reaches 26,054.4 kg
(+14.3%, outside the +/-10% band: a miss high, accepted by the user and documented). Set A
reaches 24,700.0 kg (+8.33%), set B 25,416.3 kg (+11.48%). Every 2-D finding rests on the
gate vehicle and inherits the miss; the fuel-offload note
([RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md)) repeats its headline case on
set A as a robustness row (9.10% of stage 1 there, against 10.04% on the gate vehicle).

## Display files (configs/display/)

`configs/display/` holds the shapes the 2-D launch scene draws ([7b](07b-app.md#the-scene)):
`f9_class.yaml`, the Falcon 9-class geometry (body diameter from the reference area, the
stage, interstage and fairing lengths that sum to the published 70 m, the fairing diameter,
the drawn shaft, rings, carriage, rails, mount and clamps), with an `applies_to` list naming
the four shipped vehicles; and `scene.yaml`, the camera law, the pixel thresholds and the
proportions of the generic shape drawn for a vehicle no display file lists. Every number is
written like a vehicle-file quantity, `{value, source}` or `{value, assumed: true, note}`,
and a bare number or an unknown key is refused. **Nothing in these files enters the model:
the run path never reads them** (an import guard keeps the display and scene modules out of
it), and no result changes if they change. `launchsim scene --display PATH` points the
scene at another folder; the app reads the repository's.

## Never edit a calibrated file; fork it

Results and the calibration record depend on these files as they are. CLAUDE.md forbids
editing a calibrated vehicle file; copy it to a new file instead, and say in its header what
changed and why (the 2-D forks show how). Then point a new experiment at the copy, or use
`vehicle.` overrides in sweeps, sensitivity cases and bounds.

To make your own vehicle:

1. Copy the closest shipped file to a new name.
2. Change `name` and `description`, and every number you change: give it a `source`, or mark
   it `assumed: true` with a note.
3. For the 2-D model keep exactly two stages and an `aero` block.
4. Create an experiment that names the new file and re-run its pad baseline: results on two
   vehicles are never compared directly.

Next: [7. Commands](07-commands.md)
