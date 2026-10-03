# 3. Concepts

[Manual contents](README.md) · Previous: [2. Quick start](02-quick-start.md) · Next: [4. Experiment files](04-experiments.md)

This chapter explains what a run is, how a silo run is compared with a pad run, and what
the figures of merit and the loss budget mean. The equations are in
[docs/physics.md](../physics.md); this is the reader's version.

## The comparison

Every result is a difference against the same rocket launched from a normal pad, flown with
the same guidance parametrisation, the same search budget and the same integrator settings.
The README calls the concepts:

| Concept | What it is | In the simulator |
|---|---|---|
| A. Vertical maglev silo | The rocket stands in a shaft lined with electromagnetic rings that push a carriage (or supports on its body) upward. Engines light in the shaft (hot) or just after the mouth (cold) | Built, as the `constant_accel` assist on a vertical straight track |
| B. Cable-pulled ramp | A cable drive pulls a carriage along a track that curves from horizontal toward vertical | Not built. Curved tracks and the cable winch are README roadmap Phase 3 |
| C. Baseline | The same rocket from a pad | The `baseline` run of every experiment, with assist model `none` |

The prior art (NASA's MagLifter studies, the Navy's EMALS catapult, Long March 11's cold
launch from a tube, launch coasters and others) is in the README's
[Prior art](../../README.md#prior-art) table. The simulator measures an old idea on a
specific vehicle; it does not claim the idea is new.

## The phases of a run

A run is a sequence of phases joined by events. The phase name appears in the `phase`
column of the time series ([8. Outputs](08-outputs.md#timeseriescsv)).

| # | Phase | What happens | Phase kinds in the time series |
|---|---|---|---|
| 1 | Hold (optional) | The vehicle is clamped on the pad or on the carriage; engines may start. On the pad the clamp opens at t = 0, or later if thrust has not yet passed weight (an extended hold) | `HOLD` |
| 2 | Assist | The carriage pushes the vehicle along the track from s = 0 to the track length L (1-DOF) | `ASSIST` |
| 3 | Release | At s = L, the track exit (the silo mouth). The carriage stays behind. The state is mapped into the ascent frame; in 2-D the ground speed of the site is added | an event, `release` |
| 4 | Ignition | The stage-1 thrust ramp starts at a time relative to release (negative: lit on the track or the pad), as a step, a linear ramp or a first-order lag | an event, `ignition` |
| 5 | Ascent | 1-D: straight up. 2-D: a vertical rise, a pitch kick, then a gravity turn along the air-relative velocity on stage 1 | 1-D: `BURN`, `COAST`, `FALL` (and `_PRE_IGN` coasts). 2-D: `COAST_PRE_IGN`, `VERTICAL_RISE`, `KICK`, `GRAVITY_TURN` |
| 6 | Staging | Stage 1's dry mass is dropped, the vehicle coasts (11 s on the 2-D vehicles), stage 2 lights. The fairing goes at staging or, on the 2-D vehicles, when free-molecular heating falls below a limit | `COAST_STAGING` (and `FALL_STAGING` in 1-D); event `staging`, `fairing` |
| 7 | Insertion | 2-D only: stage 2 flies linear-tangent steering and cuts off when the orbital energy reaches the target orbit's | `LTG_BURN`; event `cutoff` |

A run whose engines never light (`fails: true`) coasts up, falls back and ends at `impact`
(phase `COAST` in 2-D; `COAST` then `FALL` in 1-D).

Where a run stops is set by its `end` key: `stage1_burnout` (the default, and what the 1-D
experiment uses), `all_burnout`, `apex` or `impact` in 1-D; `stage1_burnout`, `insertion`,
`apex` or `impact` in 2-D. A 2-D run with a payload search must end at `insertion`.

**The clock.** t = 0 is the push start on a track and the hold-down release on a pad. Most
metrics and the `t_rel_release_s` column count from release instead, so a silo run's push
has negative times (the reference silo pushes for 2.6 s, so it starts at about -2.6 s).

## Pad baseline against silo variants

The shipped 2-D experiment (`experiments/silo_screening_2d.yaml`) and its 1-D mirror use
these runs. The silo settings are the same in every silo variant (3 g net over a 100 m
stroke, released at 76.7 m/s) unless the table says otherwise.

| Run | Stage-1 start | Role |
|---|---|---|
| `pad` (baseline) | Lit 2 s before release with a 2 s ramp, held down | The comparison basis |
| `pad_instant` | Step to full thrust at release | A yardstick, unphysical (no engine starts instantly) |
| `silo_instant` | Step to full thrust at release | A yardstick, unphysical: the release speed alone |
| `silo_cold` | Lit 0.5 s after release, 2 s ramp | The reference cold start |
| `silo_cold_lag` | Lit 0.5 s after release, first-order lag with tau = 1 s | Startup shape |
| `silo_hot_ramp_on_track` | Lit on the carriage 2 s before release, full thrust at release | Hot start |
| `silo_hot_full` | Full thrust for the whole push | Hot start |
| `silo_hot_full_impinged` | As `silo_hot_full`, with all the exhaust hitting the carriage | Hot start with impingement |
| `silo_failed` | Never lights | Failed ignition: the fall-back |
| `silo_sled_22t` | As `silo_cold`, with a 22 t carriage | Carriage mass (moves only energy and power under this drive) |

Two conventions matter when you read a difference:

- **The pad pays for its hold-down.** The pad burns about 2.7 t while clamped during its
  2 s ramp. On the 2-D gate vehicle that accounts for 130.7 kg gross (83.1 kg net) of the
  silo_cold gain; against a pad lit at release the gain is +1,415.8 kg instead of
  +1,498.8 kg (README, "Against the hypothesis").
- **Under a prescribed acceleration, thrust on the track buys no exit speed.** The drive
  supplies whatever force the prescribed acceleration needs, so a hot start only trades
  propellant for drive energy and peak power. The hot-start question waits for a
  force-limited drive (README roadmap Phase 3).

## Figures of merit

In increasing fidelity:

1. **Ideal rocket-equation screening.** The README's hand estimate: the payload an
   assist velocity buys if every loss stays the same, from the rocket equation with
   effective per-stage Isp values (the vehicle file's `screening` block). About 9 kg of
   payload per m/s on the README vehicle. In the simulator it is the **screening
   yardstick** a run is checked against ([9. Reading results](09-reading-results.md#the-screening-yardstick-and-the-screening-beat-rule)).
2. **Residual propellant and delta-v margin at a fixed payload.** Fly the vehicle with its
   file payload P0 (`payload_mass_t`, 22.8 t on the Falcon 9-class files) and report how
   much stage-2 propellant is left at insertion, and the delta-v it is worth. Negative
   means the vehicle cannot carry P0 (a "virtual", massless shortfall).
3. **Payload capacity P\*.** The largest payload that reaches the target orbit with zero
   residual propellant, found by a root search, with each run's guidance parameters
   (gamma\*, the kick angle and the stage-2 steering pair) solved for that run. This is
   the headline figure of the 2-D notes.

The 1-D model has no orbit. Its figure of merit is the speed at stage-1 burnout, and its
"payload equivalents" are screening conversions, not payload results.

**Coming in SP1: propellant offload at fixed payload.** The headline question of SP1 is how
much propellant the silo push replaces while the payload stays fixed. The solver core
exists (`src/launchsim/offload.py`, SP1 step 5): it removes propellant x from stage 1 (or
stage 2, or both at the same fraction) and finds the largest x for which the vehicle still
inserts the reference payload, the full-load pad's P\* on the same vehicle and orbit. It is
not reachable from experiment files yet; the `offload:` block arrives in SP1 step 7. The
only number so far is a labelled probe: about 10% of stage-1 propellant (41.1 t, 7.9% of the
total propellant load) on the 3 g, 100 m cold-start silo, before any structural mass is
charged. It is a probe, not a finding. At that offload the silo run's max-Q (38.4 kPa) is
above the full pad's (37.2 kPa), and the gate vehicle calibrates +14.3% high
([handoff, section 3](../handoff/archive/2026-09-30-phases-0-2.md#3-the-headline-question-and-a-first-answer-probe-not-a-finding)).

## Guidance, and what "sweep-optimized" means

The 2-D guidance is the same law for every run:

- stage 1: rise vertically until the air-relative speed reaches the kick trigger v_k
  (50 m/s in the shipped files), tilt by a kick angle delta until the velocity lines up,
  then follow the air-relative velocity (a gravity turn) to burnout (MECO);
- stage 2: linear-tangent steering, tan(pitch) = a - b t, to the target orbit.

The free parameters are solved per run, never set by hand: gamma\* (the flight-path angle
at MECO) is the best point of a shared grid refined by a bounded search; delta is solved to
reach it; a and b are found by shooting for the target radius and zero radial speed. Every
run of an experiment shares the grid and the search budget. That is "sweep-optimized": a
fair, shared search, not an optimal-control solution (README roadmap Phase 5).

A silo run already faster than v_k when stage 1 lights kicks at its first lit instant;
the summary reports this as the kick regime.

## The loss budget

The rocket's engines deliver a vacuum delta-v; gravity, drag, steering and back-pressure
take some of it away. The simulator books each term along the flight and checks that the
books close:

    |v_rel,f| - |v_rel,0| = dv_vac - gravity - drag - steering - back-pressure

| Term | Definition (all from the flight start, in m/s) |
|---|---|
| `dv_vac` | integral of T_vac / m dt: what the engines would give in vacuum |
| gravity | integral of g_eff sin(gamma_rel) dt, with g_eff = mu/r^2 - omega_p^2 r (centrifugal folded in) |
| drag | integral of D / m dt |
| steering | integral of (T/m)(1 - cos psi) dt, psi the angle between thrust and the air-relative velocity |
| back-pressure | integral of (T_vac - T) / m dt, the thrust lost to ambient pressure on the nozzle exit |

The velocity is Earth-relative (`v_rel`, relative to the co-rotating air). The identity
starts at the flight start (release, or liftoff after an extended hold); the push has its
own energy budget (drive work against kinetic and potential energy gained). A run whose
books do not close to the configured tolerance is marked `bug_suspect`
([9. Reading results](09-reading-results.md#the-loss-identity)).

The 1-D model splits gravity into a duration part and an altitude part, and has no drag,
steering or back-pressure (vacuum thrust, no atmosphere).

## Loads, energy and power

Every summary reports, against the pad:

- **peak felt axial g**: the acceleration the vehicle feels along its axis. A full stack
  pushed up at 3 g net feels about 4 g (3 g plus the 1 g that holds its weight). Measured:
  3.996 g on the 573.9 t 2-D stack (README);
- **interface force** between vehicle and carriage (22.49 MN on that stack);
- **track-normal load** for vehicle and carriage separately (zero on a vertical straight
  track);
- **drive energy** in J and kWh, the electricity at the assumed drive efficiency, and the
  **peak drive power** (2.249 GJ and a 1.725 GW peak for the reference silo in 2-D);
- **facility length** including carriage braking: 100 m stroke plus 60 m of braking at
  5 g gives 160 m.

Rockets normally see 4 g only near burnout, with nearly empty tanks. No structural mass is
charged for that load in any result so far; it is the caveat that could cancel the gain
(README roadmap Phase 3, backlog B-004).

Next: [4. Experiment files](04-experiments.md)
