# RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push

Status: preliminary. Phase 1 model, first experiment. Numbers will change in Phase 2
(drag, back-pressure, rotation, 2-D ascent) and Phase 3 (force-limited drives).

## Caveats (read first)

Everything below is computed under the Phase 1 model:

- 1-D vertical motion only; no pitch, no gravity turn, no orbit. The figure of merit is
  the stage-1 burnout speed and its decomposition, not payload to orbit.
- Vacuum thrust from sea level (8.227 MN, TWR 1.55 at liftoff instead of the real 1.43);
  no atmosphere, so no drag, no back-pressure, no max-Q.
- No Earth rotation (omega_p = 0); Coriolis neglected.
- Fixed payload (22.8 t), unthrottled engines, instantaneous cutoff at depletion.
- The drive is a prescribed net acceleration (`constant_accel`, 3 g0 net, 100 m stroke):
  the drive force is whatever the track equation needs each instant, unbounded. A
  force-limited or power-limited drive (`linear_motor`, Phase 3) would behave differently
  under a hot start; see "Open question".
- Carriage mass 0 unless stated; shaft vented; no friction; infinite jerk at push start
  and release; vehicle clamped to the carriage during any hold before the push.
- Gravity in flight is mu/r^2; on the track and as the loss-split reference it is
  g_eff = mu/R_E^2 = 9.798285 m/s^2 (the README's hand numbers used g0 = 9.80665).
- Vehicle: configs/vehicles/generic_f9_class.yaml, 542,570 kg at liftoff (the README
  used 549 t), stage-1 startup a 2 s linear ramp (assumed).

## Provenance

- Experiment: experiments/silo_screening_1d.yaml (baseline `pad`, nine variants, three
  sweeps, sixteen sensitivity cases).
- Results: results/silo_screening_1d/20260929T103623Z/ (run) and
  results/silo_screening_1d/20260929T103634Z/ (sweeps). Both summaries carry the same
  git label, 98c752d58f52-dirty: commit 98c752d (Phase 1 engine) plus the uncommitted
  silo, failed-ignition, metrics and summary work of build steps 7-12. A second pair,
  20260929T104503Z (run) and 20260929T104510Z (sweeps), is the reviewer's independent
  reproduction: the summaries are identical to the cited pair apart from the timestamp.
- Every identity line closes to < 2.4e-12 m/s and no variant exceeds its release speed
  + hold-down credit + altitude term by more than 1e-6 m/s (summary.md, "Checks").
- The numbers are reproduced in-process by tests/test_readme_numbers.py; the closed
  forms behind them are validated in tests/test_ignition_loss.py and tests/test_silo.py.

## The question

Engines lit on the carriage versus lit after release: how much does the delay and the
thrust build-up cost, and what does lighting them before release buy?

## Cold start: the loss is exact, and it is the gravity term

Reference: full thrust from the instant of release (`silo_instant`, a step startup at
t = 0, unphysical; it is the yardstick, not a design). A delayed variant burns the
same propellant with the same c, so its dv_vac = c ln(m_release/m_burnout) is
identical; every metre per second it loses is gravity loss over the extra time it
spends under thrust deficit. Under constant g the loss is a closed form
(docs/physics.md, "Ignition-after-release loss"):

- delay t_d then a linear ramp of t_r: loss = g (t_d + t_r/2), exactly;
- delay t_d then a first-order lag of tau: loss = g [t_d + tau (1 - e^(-u))] with
  u = 1 + t_b/tau + W0(-e^(-1 - t_b/tau)); g (t_d + tau) is the asymptote and is
  exact to 1e-63 m/s for the 147 s F9 burn;
- a ramp straddling release (-t_r < t_ign < 0): Phi_pre = t_ign^2/(2 t_r) full-thrust
  seconds burn on the track; loss vs instant = c ln(m0/(m0 - mdot Phi_pre)) - g Phi_pre
  + g (t_r + t_ign)^2/(2 t_r).

Under mu/r^2 the delayed vehicle flies lower for the whole burn and the loss integrates
about 3 % higher than the constant-g formula; the runs print both.

Shipped variants, stage-1 burnout (all silo variants exit at 76.7072 m/s):

| variant | t_ign vs release [s] | startup | burned before release [kg] | burnout speed [m/s] | delta vs pad [m/s] | loss vs silo_instant, integrated [m/s] | constant-g formula [m/s] |
|---|---|---|---|---|---|---|---|
| pad (baseline) | -2.0 | ramp 2 s | 2,697 (held down) | 2557.65 | 0 | n/a | 5.40 (hold-down cost) |
| pad_instant | 0 | step | 0 | 2563.22 | +5.58 | n/a | 0 |
| silo_instant | 0 | step | 0 | 2642.41 | +84.77 | 0 | 0 |
| silo_cold | +0.5 | ramp 2 s | 0 | 2627.29 | +69.64 | 15.12 | 14.70 |
| silo_cold_lag | +0.5 | lag tau 1 s | 0 | 2627.29 | +69.64 | 15.12 | 14.70 |
| silo_hot_ramp_on_track | -2.0 | ramp 2 s | 2,697 (on the track) | 2636.80 | +79.16 | 5.61 | 5.40 |
| silo_hot_full | -4.61 (push start - 2 s) | ramp 2 s | 9,731 (2,697 in a hold, 7,033 on the track) | 2621.82 | +64.17 | 20.60 | 19.85 |
| silo_hot_full_impinged | -4.61 | ramp 2 s | 9,731 | 2621.82 | +64.17 | 20.60 | 19.85 |

Ignition sweep on `silo_cold` (sweeps/sweep_2, 3 g0, 100 m; loss = silo_instant
burnout speed 2642.41 minus the point's):

| delay [s] | ramp [s] | integrated loss [m/s] | g_eff (t_d + t_r/2) [m/s] | delta vs pad [m/s] |
|---|---|---|---|---|
| 0 | 1 | 5.04 | 4.90 | +79.73 |
| 0 | 2 | 10.08 | 9.80 | +74.69 |
| 0 | 3 | 15.12 | 14.70 | +69.64 |
| 0.5 | 1 | 10.08 | 9.80 | +74.68 |
| 0.5 | 2 | 15.12 | 14.70 | +69.64 |
| 0.5 | 3 | 20.17 | 19.60 | +64.60 |
| 1 | 1 | 15.13 | 14.70 | +69.64 |
| 1 | 2 | 20.17 | 19.60 | +64.60 |
| 1 | 3 | 25.21 | 24.50 | +59.55 |

The README's band (5-25 m/s for a 0-1 s delay and a 1-3 s ramp) is reproduced: 4.90 to
24.50 m/s by the formula, 5.04 to 25.21 m/s integrated. For a 77 m/s assist that is
6-33 % of the exit speed, gone before the engines reach full thrust.

## Lag versus ramp: the README band understates the lag case

Lag sweep on `silo_cold_lag` (sweeps/sweep_3, 0.5 s delay):

| tau [s] | integrated loss [m/s] | g_eff (t_d + tau) [m/s] | delta vs pad [m/s] |
|---|---|---|---|
| 1 | 15.12 | 14.70 | +69.64 |
| 2 | 25.20 | 24.50 | +59.57 |
| 3 | 35.28 | 34.29 | +49.49 |

A first-order lag of time constant tau costs g tau, twice what a linear ramp of the same
duration costs (g tau/2): the lag reaches only 63 % of full thrust after one time
constant (an average of 37 % over that first tau) and never quite reaches full thrust,
so the deficit integrates to a full tau.
The README quotes both formulas but gives one band, 5-25 m/s, which is the ramp band. For
the lag case with the same 0-1 s delay and 1-3 s time constant the band is 9.8-39.2 m/s
(formula) or about 10-40 m/s integrated. Observation for the README, not an edit: the
band should either be labelled "linear ramp" or widened to cover the lag.

## Hot start under a prescribed acceleration: no speed, less drive energy

Under `constant_accel` the carriage acceleration is fixed at 3 g0 net whether or not the
engines are running, so a hot start changes the forces and the energy, not the exit
speed (76.7072 m/s in every silo variant) and not the felt acceleration (3.999 g0 on the
full stack in every silo variant). What it does:

| variant | thrust during the push | F_int peak / min [MN] | drive energy [GJ] | peak drive power [GW] | electrical at 50 % [kWh] | propellant before release [t] |
|---|---|---|---|---|---|---|
| silo_cold | none | 21.28 / 21.28 | 2.128 | 1.632 | 1,182 | 0 |
| silo_hot_ramp_on_track | ramp starts 0.607 s after push start, full at release | 21.28 / 12.95 | 1.654 | 0.993 | 919 | 2.70 |
| silo_hot_full (f_imp = 0) | full for the whole push | 12.95 / 12.67 | 1.276 | 0.972 | 709 | 9.73 |
| silo_hot_full_impinged (f_imp = 1) | full, exhaust pushes on the carriage | 12.95 / 12.67 | 2.099 | 1.603 | 1,166 | 9.73 |

- Propellant burned before release is a straight loss at burnout: `silo_hot_full` is
  20.6 m/s (integrated; 19.85 by the constant-g arithmetic: 55.19 m/s of dv_vac spent for
  35.35 m/s of gravity loss avoided) behind `silo_instant`, and 5.5 m/s behind the cold
  variant it is meant to improve on. `silo_hot_ramp_on_track` (the README's "lit on the
  carriage") is 5.6 m/s behind `silo_instant` and 9.5 m/s ahead of `silo_cold`: it
  removes the post-release ramp loss (14.70 m/s) at the price of the 2.7 t burned on the
  track (5.40 m/s), the same trade the pad baseline makes while clamped.
- Drive energy falls by the thrust work on the track: 0.85 GJ (40 %) for the full hot
  start at f_imp = 0, 0.47 GJ for the ramp-on-track case. Peak drive power falls by 40 %
  (1.632 -> 0.972 GW), because at release the drive carries M (a + g) - T instead of
  M (a + g).
- The exhaust-impingement fraction bounds this: with f_imp = 1 (all of the exhaust
  momentum returned to the carriage) the drive energy and peak power are back to the cold
  values (2.099 GJ, 1.603 GW, lower only by the 9.7 t of mass no longer aboard), while
  the interface force and the propellant cost are unchanged. The true f_imp for a
  carriage that sits under nine engines is not known; both bounds are reported.
- Drive-limit threshold: F_drive = M (a + g_eff) - (1 - f_imp) T goes negative when the
  engines alone would exceed the prescribed acceleration, i.e. below a net acceleration
  of about 0.55 g0 for this vehicle at f_imp = 0 (T/M0 - g_eff = 5.44 m/s^2 with
  M0 = 539,873 kg, the stack at push start after the 2 s hold ramp of `silo_hot_full`;
  5.36 m/s^2 = 0.547 g0 with the 542,570 kg liftoff mass). Below that a
  prescribed-acceleration drive would have to brake the engines; the model ends such a
  run with status `drive_limit` (tests/test_silo.py) unless `allow_negative_drive_force`
  is set. None of the shipped variants reaches it (3 g0 net).
- The hold before the push (`silo_hot_full`): 2.0 s clamped to the carriage at the shaft
  bottom, hold-down force at least 2.94 MN in tension at the end of the ramp, 2,697 kg
  burned there, then 7,033 kg more on the track.

The interface force is lower with a hot start (12.7-12.9 MN instead of 21.3 MN) because
the engines carry part of the stack's weight-plus-inertia; that is the one structural
benefit, and it is bought with propellant.

## The hold-down credit, stated so it is not mistaken for a silo gain

The pad baseline lights its engines 2 s before release and burns 2,697 kg while clamped;
that costs it 5.40 m/s at burnout against an (unphysical) instant-thrust pad. Every silo
variant lit after release does not pay that cost, so its delta against the pad includes
+5.40 m/s that has nothing to do with the push. The summary prints this credit on its own
line; the decomposition of `silo_cold`'s +69.64 m/s is 76.71 (exit speed) + 5.40 (credit)
- 14.70 (post-release ignition loss, constant-g part) + 2.23 (altitude term: the assisted
vehicle flies the whole burn higher, where mu/r^2 is weaker); the last three together
(-7.07 m/s) are delta dv_vac (15.20 m/s) minus the gravity-loss difference against the
pad (24.50 - 2.23 = 22.27 m/s, printed as the duration and altitude parts). The concept's own contribution is exit speed less
ignition loss: 62.0 m/s here, 81 % of the exit speed.

## Findings that undercut the hypothesis

- Nothing lit on the carriage buys exit speed under a prescribed acceleration; it buys a
  lower drive-energy and peak-power bill and a lower interface force, and pays in
  propellant: 2.7 to 9.7 t, 5.6 to 20.6 m/s at burnout against the instant yardstick.
- The best variant that could exist (`silo_instant`) is unphysical; the best physical one
  in this set is `silo_hot_ramp_on_track` at +79.2 m/s over the pad, and the plain cold
  start at +69.6 m/s gives up 19 % of the exit speed to the 0.5 s + 2 s startup.
- A lag-type startup is twice as expensive as a ramp of the same duration; the README's
  5-25 m/s band covers only the ramp.
- A 10 % perturbation of stage-1 dry mass or Isp moves the silo_cold delta against the
  nominal pad by 40 to 260 m/s (the vehicle changed), but the delta against the pad with
  the same perturbation by less than 0.5 m/s (69.23 to 70.09 m/s): the concept's benefit
  is insensitive to the vehicle at fixed exit speed, in 1-D. The screening Isp moves only
  the payload equivalent (613 to 629 kg); the drive efficiency moves only the electrical
  energy (1,075 to 1,314 kWh).

## Open question (needs the force-limited `linear_motor`, Phase 3)

With a force- or power-limited drive the on-track thrust is not cancelled by the drive:
F_drive = min(F_max, P_max/v) and the engines add to the acceleration, so a hot start
would raise the exit speed for a given stroke, or shorten the stroke for a given exit
speed, and the hold-down and interface loads would follow the drive's force curve rather
than the prescribed acceleration. Whether the propellant burned on the track then pays
for itself cannot be answered by this model; it is the first thing to run once
`linear_motor` exists. The drive-limit threshold above (0.55 g0) also becomes the
natural operating point rather than a failure.

## README observations (not edits)

- The 5-25 m/s ignition-loss band is the linear-ramp band; the lag case with the same
  delay and duration is 10-40 m/s (see above).
- "One EMALS launch (122 MJ)": 122 MJ is roughly the rated energy of one flywheel
  alternator (the README's own prior-art row says 121 MJ each); a 45 t aircraft at
  67 m/s carries 0.5 x 45,000 x 67^2 = 101 MJ of kinetic energy. The comparison for a
  13 t launcher's 38 MJ stands either way.

## Figures

Copied from results/silo_screening_1d/20260929T103623Z/plots/:

- RQ2-silo_cold_speed.png: speed vs time from release for the cold start; the coast
  and the ramp are visible in the first 2.5 s.
- RQ2-silo_cold_mass_thrust.png: mass and thrust; the ramp starts 0.5 s after release.
- RQ2-silo_hot_ramp_on_track_track_forces.png: drive and interface force during the push
  when the ramp completes exactly at release (F_int falls from 21.3 to 12.9 MN). F_drive
  and F_int coincide (massless carriage, f_imp = 0), so one line shows under the
  two-entry legend.
- RQ2-silo_hot_full_track_forces.png: the same with full thrust for the whole push;
  F_drive and F_int coincide here too.
- RQ2-silo_hot_full_drive_power.png and RQ2-silo_cold_drive_power.png: drive power,
  0.97 GW peak hot versus 1.63 GW cold.
