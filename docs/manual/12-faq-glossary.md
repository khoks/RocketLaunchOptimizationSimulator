# 12. FAQ and glossary

[Manual contents](README.md) · Previous: [11. Troubleshooting](11-troubleshooting.md)

## FAQ

**Is this open source?**
No. All rights reserved: the repository is public to read, and no license is granted. You
may not copy, modify, share or use it, commercially or otherwise, without written permission
([LICENSE](../../LICENSE)). Publishing the research ideas does not grant any right to
implement or commercialise them.

**How much propellant does the silo push save?**
On this model, preliminary: at the pad's payload and orbit the 3 g, 100 m cold-start silo
lets the gate vehicle leave out **41.26 t of stage-1 propellant, 10.04% of the stage-1 load
and 7.96% of the total** ([RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md),
pre-registered SP1 runs). It is a difference between runs of a vehicle model, not a Falcon 9
figure, and these caveats travel with it:

- the gate vehicle calibrates +14.3% high; on the README-loads fork, which calibrates inside
  the band, the same case removes 36.01 t (9.10% of stage 1);
- guidance is sweep-optimized and nothing is throttled;
- no structural mass is charged for the 4 g full-stack push: an assumed +8.1 t of stage-1
  dry mass leaves 1.98 t, and about 8.5 t (extrapolated) cancels it;
- read as the pre-registration worded it, most of the offload is the lighter stack's
  thrust-to-weight (the pad flown with the same offload falls only 1.4 t short of the
  payload), while a delta-v reading chosen after the run gives the lighter stack 28 to 29%;
- the offloaded run's max-Q is 3.4% above the pad's (the full-load silo's was 16% below);
- the stage-2 case failed its independent verification, and stage-2 figures are a property
  of the vehicle model, not the headline;
- the heat-to-electricity ratio of about 128 is not an efficiency claim.

[9. Reading results](09-reading-results.md#what-the-shipped-offload-run-says) has the rest.

**Does this show that electricity can replace a share of a rocket's fuel?**
No such claim follows. The figure is propellant left out of a partly filled tank of one
vehicle model at one payload, before any structure is charged for the push, and the energy
ratio beside it sets unlike quantities side by side: it leaves out producing the oxidiser,
supplying the fuel, grid losses and the facility, and says nothing about cost.

**So what has been found?**
Preliminary results for the vertical silo only, in [docs/findings/](../findings/README.md).
On the 2-D gate vehicle the cold-start silo (3 g net over 100 m, 76.7 m/s at the mouth)
carries +1,498.8 kg (+5.75%) more to a 200 km orbit than the pad, or, read the other way,
leaves out 41.26 t of stage-1 propellant at the pad's payload (above). That comes with
caveats that could cancel it: no structural mass is charged for the 4 g full-stack push
(about 8.1 t of strengthening would cancel the payload gain, about 8.5 t the offload), the
vehicle calibrates +14.3% high, and the guidance is sweep-optimized and unthrottled
([9. Reading results](09-reading-results.md#the-caveats-and-why-each-matters)).

**Does every m/s of assist help, as the hypothesis says?**
In the ideal rocket equation, yes: about 9 kg of payload per m/s on the README vehicle. In the
simulations so far the answer is mixed. The 77 m/s silo gains about twice the ideal estimate
before structural mass; but a full hot start ties the cold start, a slow startup after
release gives back a large part of the gain, and at the slowest swept push (0.5 g over 50 m)
the trajectory term is negative and a third of the small gain is the pad's own hold-down
burn. In the offload runs the max-Q benefit is spent, the offload per m/s falls with depth,
each second of ignition delay after release costs 4.8 to 5.3 t, and assumed structure takes
4.5 to 5.1 t of offload per tonne
([9. Reading results](09-reading-results.md#results-that-go-against-the-hypothesis)).

**Why is the 2-D gain about twice the README's hand estimate? Is that a bug?**
The hand estimate holds every loss constant. A vertical release is not constant-loss: in
silo_cold the gravity, steering, back-pressure, drag and fairing terms together fall, and the
pad pays for burning 2.7 t while clamped. The simulator requires such a beat to be explained
by its loss breakdown, and it is (README; [RQ3-2d](../findings/RQ3-silo-screening-2d.md)).

**Why does the Falcon 9 model carry 26 t instead of 22.8 t?**
The gate vehicle misses the published payload high by +14.3%, outside the planned +/-10%
band. The cause is not established. The user accepted the miss as documented, and every 2-D
number inherits it ([CAL-f9-leo-2d](../findings/CAL-f9-leo-2d.md)).

**Is the silo idea new?**
The simulator does not claim so. NASA studied magnetic launch assist (MagLifter), the Navy's
EMALS launches aircraft electromagnetically, Long March 11 is cold-launched from a tube, and
launch coasters pull cars up towers with cables. The README's
[Prior art](../../README.md#prior-art) table lists them. The project measures what such an
assist is worth on a specific rocket, with the penalties counted.

**Can I simulate the cable-pulled ramp, a linear motor, or a tilted exit?**
Not yet. Curved tracks, the cable winch, the force- and power-limited linear motor, the
silo air column, modelled braking and a tilted-exit abort are README roadmap Phase 3. The
config refuses them with a message that says so.

**Is there a 3-D model or a graphical app?**
Not yet. A local app with an animated 2-D launch scene is phase SP2; true 3-D dynamics (a
point mass on a rotating sphere, then an oblate Earth, then a 6-DOF fly-out) are SP3 to SP6,
with a 3-D scene in SP4 ([docs/phases/README.md](../phases/README.md)). Today you get files,
an MP4 or GIF from `animate`, and an interactive page from `replay`.

**Why does the 1-D model report "payload equivalents" that are not payload?**
The 1-D model stops at stage-1 burnout, with no orbit. It converts a burnout-speed difference
to kilograms with the ideal rocket equation for comparison with the README table, and labels
the result "not a payload result". Use the 2-D model for payload.

**Why are the hot starts not better than the cold start?**
Under a prescribed acceleration the drive supplies whatever force the push needs, so thrust on
the track buys no exit speed; it only trades propellant for drive energy and peak power. The
hot-start question waits for a force-limited drive (Phase 3). In the offload runs every hot
start beats lighting at the mouth, and lighting 75 m deep removes the most (46.96 t), but
lighting at the shaft floor removes 2.6 t less than that: the extra propellant burned on the
track buys nothing under this drive.

**How do I run the offload experiment myself?**
`uv run python -m launchsim run experiments/silo_offload_2d.yaml` (long; see
[5b](05b-offload.md)). Its summary gains the section "Propellant saved at fixed payload";
replay an offloaded run beside the pad with `replay ... --runs pad silo_cold_s1`.

**Can I change a vehicle file?**
Not a calibrated one: copy it to a new file and change the copy
([6. Vehicle files](06-vehicles.md#never-edit-a-calibrated-file-fork-it)).

**Why did my run write a directory with `FAILED.txt`?**
It raised after the directory was created. See
[11. Troubleshooting](11-troubleshooting.md#problems-during-or-after-a-run).

## Glossary

| Term | Meaning |
|---|---|
| **assist** | The ground-powered push. Configured in a run's `assist` block |
| **attribution** | The split of a variant's delta-v margin difference against the pad, at the pad's payload, into release-speed, final-speed, gravity, drag, steering, back-pressure, pre-flight and fairing terms (`attr_*`) |
| **back-pressure loss** | Thrust lost to ambient pressure on the nozzle exit, integrated as (T_vac - T)/m |
| **baseline** | The pad run every other run is compared with |
| **bound** | A named re-run of variants with overrides, compared with the baseline re-run under the same overrides (2-D) |
| **bug_suspect** | A run or comparison that failed a blocking check. It blocks findings until investigated |
| **calibration** | Comparing the model vehicle with the real one's published performance. Labelled, and kept apart from validation |
| **carriage** | What the drive pushes and the rocket stands on. It stays on the track at release |
| **case** | An independent run of a calibration experiment with another vehicle, site or orbit; never compared |
| **closure** | The rocket-equation bookkeeping of a 2-D run: the ideal rocket-equation delta-v at the payload must equal the flown vacuum delta-v plus the pre-flight burn and fairing-carry terms plus the delta-v margin, to a tolerance |
| **cold start** | Engines lit after release (silo_cold: 0.5 s after, with a 2 s ramp) |
| **constant_accel** | The screening drive: a prescribed constant net acceleration along a straight track |
| **dP\*** | A run's payload capacity minus the baseline's |
| **drive efficiency** | Mechanical drive work over electrical energy (assumed 0.5 in the shipped files) |
| **dv margin** | The delta-v the residual propellant at insertion is worth, at the vehicle payload |
| **exit speed** | The speed at the track exit; sqrt(2 a L) for the prescribed push |
| **facility length** | Stroke plus carriage braking distance |
| **felt g** | Proper acceleration, the acceleration the vehicle feels, in g0. A full stack pushed at 3 g net feels about 4 g |
| **flight start** | Release, or liftoff after an extended hold; the loss quadratures start here |
| **g0** | 9.80665 m/s^2: the unit "g" and the Isp conversion, never a gravity model |
| **g_eff** | Effective gravity, mu/r^2 - omega_p^2 r (centrifugal folded in). The track uses its constant surface value |
| **gamma\*** | The flight-path angle at stage-1 burnout (MECO), solved per run by the search |
| **gate vehicle** | `configs/vehicles/generic_f9_class_2d.yaml`, mass set C: the pre-registered calibration vehicle every 2-D finding uses |
| **gravity loss** | The integral of g_eff sin(gamma_rel); time spent climbing against gravity |
| **hold, hold-down** | The vehicle clamped while its engines start. The pad baseline lights 2 s before release and burns about 2.7 t while clamped |
| **hot start** | Engines lit on the track (or before the push starts) |
| **kick** | The pitch-over that starts the turn, held at angle delta until the velocity lines up with the thrust |
| **lag** | A first-order startup: thrust fraction 1 - exp(-t/tau). A lag of tau costs as much as a linear ramp of 2 tau |
| **loss identity** | Speed change = vacuum delta-v minus gravity, drag, steering and back-pressure losses; must close for every run |
| **LTG** | Linear-tangent guidance on stage 2: tan(pitch) = a - b t |
| **M2 to M5** | Mechanism checks of the screening-beat rule (gravity, back-pressure, drag and steering, anchor). M2 is diagnostic only |
| **matched payload (P_ref)** | The baseline's P\*, at which every variant is re-flown for the attribution |
| **max-Q** | The largest dynamic pressure of the flight. Unthrottled here, so an upper bound |
| **MECO** | Main engine cutoff: stage-1 burnout |
| **mouth** | The top of the silo, the track exit |
| **no_ignition** | A ramp start by event height that the coast after release never reaches (its apex lies below the height); the run ends `guidance_failed` or `search_failed` |
| **no_offload** | The status of an offload solve whose vehicle cannot carry P_ref even with full tanks (x\* = 0) |
| **offload** | Propellant removed from a full load at a fixed payload and orbit, with the tanks partly filled and every dry mass unchanged; set up with the experiment's `offload:` block ([5b](05b-offload.md)) |
| **offload decomposition (cross-vehicle)** | The split of the ideal delta-v an offloaded vehicle does without, D_id(pad) - D_id(case), into the release speed and the differences in the losses, the pre-flight burn, the fairing term and the margin; `explained` when it closes, else `bug_suspect` |
| **omega_p** | The Earth rotation rate in the plane of the launch, omega_E cos(lat) sin(az) |
| **P0** | The payload in the vehicle file (22.8 t on the Falcon 9-class files) |
| **P\*** | Payload capacity: the largest payload that reaches the target orbit with zero residual propellant |
| **P_ref** | The reference payload of an offload: the full-load pad's P\* on the same vehicle and orbit |
| **pad control** | The offload solve run on the pad itself: for stage 1 a consistency test of the solver; for stage 2 and both the amount those cases are quoted net of |
| **paired pad** | The pad flown with an offload case's propellant change and no push (`<case>__<baseline>`); it separates the head start from the lighter stack |
| **paired sweep** | A sweep that re-runs the baseline at every point with the same overrides (2-D) |
| **penalty row** | An offload case with `stage1_dry_mass_added_t`: an assumed stage-1 dry mass added to the assisted run, a parametric stand-in for structure, not a sized one |
| **pre-registration** | Fixing inputs and rules in a commit before a run, so they cannot drift toward a wanted answer |
| **probe** | A labelled one-off calculation outside the shipped experiments. Never a finding |
| **q-alpha** | Dynamic pressure times the angle between thrust and air-relative velocity, an aerodynamic load indicator |
| **ramp** | A linear thrust startup over `t_ramp_s` |
| **ramp start** | When a stage's thrust ramp begins: by time, or (stage 1 on a silo run) by depth, speed or height (by a closed form or by an altitude event in flight) |
| **release** | The moment the vehicle leaves the track or the hold-down opens |
| **residual propellant** | Stage-2 propellant left at insertion, at the vehicle payload. Negative means a virtual shortfall |
| **resolution effect** | A stage-1 pad control that ends `no_offload` because the full-load pad misses P_ref by grams of residual propellant (between -0.05 and 0 kg); it passes the consistency test |
| **screening, screening yardstick** | The ideal rocket-equation payload gain of a release speed, with all losses held constant. The yardstick a run's dP\* is checked against |
| **sensitivity case** | A run with one parameter moved by plus or minus a fraction |
| **silo** | Concept A: a vertical shaft whose drive pushes the rocket out |
| **stage-1 burnout speed** | The 1-D figure of merit |
| **steering loss** | Thrust not along the velocity, integrated as (T/m)(1 - cos psi) |
| **step** | Instant full thrust at ignition. A yardstick: no engine does it |
| **stroke** | Track length L (`stroke_m`) |
| **sweep** | A full grid of runs over dotted paths |
| **sweep-optimized** | Guidance whose free parameters are solved per run over a grid shared by every run of an experiment. Not optimal control |
| **track-normal load** | The load across the track, per body, in g0. Zero on a vertical straight track |
| **v_k** | The kick trigger speed (50 m/s in the shipped files) |
| **v_rel** | Velocity relative to the co-rotating air (Earth-relative). Drag, Mach, q and the loss accounting use it |
| **validation** | Checking that the code solves its equations, against closed forms in the tests |
| **variant** | A named partial run merged over the baseline |
| **x\*** | The solved offload: the largest evaluated x at which the assisted run still carries P_ref with residual propellant >= 0 |
