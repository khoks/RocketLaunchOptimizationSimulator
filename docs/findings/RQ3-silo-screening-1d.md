# RQ3 (preliminary, 1-D): vertical silo screening, concept A

Status: preliminary. Phase 1 model, first experiment. Numbers will change in Phase 2
(drag, back-pressure, rotation, 2-D ascent, an air column if the shaft is not vented)
and Phase 3 (force-limited drives, carriage braking as a modelled phase, tilted-exit
abort).

## Caveats (read first)

Everything below is computed under the Phase 1 model:

- 1-D vertical motion only; no pitch, no gravity turn, no orbit. The figure of merit is
  the stage-1 burnout speed and its decomposition, not payload to orbit; the "payload
  equivalent" quoted is the ideal rocket equation at fixed losses, not a payload result.
- Vacuum thrust from sea level (8.227 MN, TWR 1.55 at liftoff instead of the real 1.43);
  no atmosphere, so no drag, no back-pressure, no max-Q, and a drag-free fall-back coast.
- No Earth rotation (omega_p = 0); Coriolis neglected.
- Fixed payload (22.8 t), unthrottled engines, instantaneous cutoff at depletion.
- The drive is a prescribed net acceleration (`constant_accel`): the drive force is
  whatever the track equation needs each instant, unbounded; infinite jerk at push start
  and release. No force, power or jerk limit is modelled.
- Carriage mass 0 unless stated (the 22 t variant is the exception); shaft vented (no air
  column); no friction; carriage braking not modelled as a phase (its distance
  v^2/(2 a_brake) at 5 g0 is added to the facility length).
- Gravity in flight is mu/r^2; on the track g_eff = mu/R_E^2 = 9.798285 m/s^2 (the README
  used g0 = 9.80665).
- Vehicle: configs/vehicles/generic_f9_class.yaml, 542,570 kg at liftoff (README: 549 t),
  stage-1 startup a 2 s linear ramp (assumed).

## Provenance

- Experiment: experiments/silo_screening_1d.yaml (baseline `pad`, nine variants, three
  sweeps, sixteen sensitivity cases).
- Results: results/silo_screening_1d/20260929T103623Z/ (run) and
  results/silo_screening_1d/20260929T103634Z/ (sweeps), git 98c752d58f52-dirty
  (commit 98c752d plus the uncommitted silo, failed-ignition, metrics and summary work
  of build steps 7-12). The pair 20260929T104503Z / 20260929T104510Z is the reviewer's
  independent reproduction with summaries identical apart from the timestamp.
- Every identity line closes to < 2.4e-12 m/s; no variant exceeds its release speed +
  hold-down credit + altitude term by more than 1e-6 m/s (summary.md, "Checks").
- Reproduced in-process by tests/test_readme_numbers.py; closed forms validated in
  tests/test_silo.py, tests/test_assist_energy.py, tests/test_failed_ignition.py.

## The reference silo (3 g0 net, 100 m stroke, cold start 0.5 s + 2 s ramp)

| quantity | value | README hand number |
|---|---|---|
| exit speed, push time | 76.71 m/s, 2.607 s | 77 m/s, 2.6 s |
| felt axial acceleration on the full stack (542.57 t) | 3.999 g0 (a + g_eff = 39.22 m/s^2) | 4 g |
| peak felt g in flight | 5.71 g0 at stage-1 burnout (146.87 t), every variant | (rockets see such g only near burnout) |
| track-normal load | 0 (vertical track) | - |
| interface force (cold) | 21.28 MN, constant over the push | 21.5 MN at 549 t |
| drive force (cold, m_c = 0) | 21.28 MN | - |
| drive energy | 2.128 GJ = 591 kWh (= M (a + g_eff) L = delta KE + delta PE) | ~2.2 GJ |
| peak drive power | 1.632 GW, at release | ~1.65 GW |
| electrical energy at 50 % efficiency | 4.256 GJ = 1,182 kWh | ~1.2 MWh |
| braking distance at 5 g0, facility length | 60.0 m, 160 m | - |
| stage-1 burnout speed delta vs pad | +69.64 m/s (76.71 exit + 5.40 hold-down credit - 14.70 ignition loss + 2.23 altitude term) | - |
| ideal-screening payload equivalent of that delta | 621 kg (README yardstick at 76.71 m/s: 685 kg) | - |

The README hand numbers are reproduced within their rounding; the residual differences
are the 542.57 t vs 549 t liftoff mass and g_eff vs g0.

## Stroke versus g: the sweep over a and L (`silo_cold`, sweeps/sweep_1)

| net a [g0] | L [m] | exit speed [m/s] | felt g [g0] | drive energy [GJ] | peak power [GW] | facility [m] | delta vs pad [m/s] |
|---|---|---|---|---|---|---|---|
| 0.5 | 50 | 22.1 | 1.50 | 0.40 | 0.18 | 55 | +13.3 |
| 0.5 | 100 | 31.3 | 1.50 | 0.80 | 0.25 | 110 | +22.8 |
| 0.5 | 300 | 54.2 | 1.50 | 2.39 | 0.43 | 330 | +46.4 |
| 1 | 50 | 31.3 | 2.00 | 0.53 | 0.33 | 60 | +22.8 |
| 1 | 100 | 44.3 | 2.00 | 1.06 | 0.47 | 120 | +36.2 |
| 1 | 300 | 76.7 | 2.00 | 3.19 | 0.82 | 360 | +69.6 |
| 3 | 50 | 54.2 | 4.00 | 1.06 | 1.15 | 80 | +46.4 |
| 3 | 100 | 76.7 | 4.00 | 2.13 | 1.63 | 160 | +69.6 |
| 3 | 300 | 132.9 | 4.00 | 6.38 | 2.83 | 480 | +127.6 |
| 5 | 50 | 70.0 | 6.00 | 1.60 | 2.24 | 100 | +62.7 |
| 5 | 100 | 99.0 | 6.00 | 3.19 | 3.16 | 200 | +92.7 |
| 5 | 300 | 171.5 | 6.00 | 9.58 | 5.48 | 600 | +167.6 |

Reading it:

- Exit speed follows sqrt(2 a L) exactly (the README table: 31/44/77/99/133/172 m/s).
  The felt acceleration is a + g_eff regardless of L. Pushing gently means a long shaft:
  at 0.5 g0 net (1.5 g0 felt) 100 m gives 31.3 m/s, and 76.7 m/s needs 600 m; at 1 g0 net
  it needs 300 m.
- The ignition loss after release is the same 14.70 m/s (constant-g; 15.1 integrated)
  at every point, because it depends only on the delay and the ramp, not on the exit
  speed. So the slow points are eaten by it: at 0.5 g0 and 50 m the exit speed is
  22.1 m/s and the delta against the pad is +13.3 m/s, of which 5.4 m/s is the
  hold-down credit (the pad burns 2.7 t while clamped, the silo does not; see RQ2) and
  0.4 m/s the altitude term, leaving 7.4 m/s for the push itself. Break-even for the
  push alone against its own ignition loss is at about 15 m/s of exit speed.
- Drive energy is M (a + g_eff) L: the 1 g0 of weight support costs as much as the
  first 1 g0 of net acceleration, so at 0.5 g0 net two thirds of the energy goes into
  holding the rocket up. Peak power is M (a + g_eff) v_exit at release.
- Facility length is L (1 + a/a_brake) with the 5 g0 brake: 1.6 L at 3 g0 net, 2 L at
  5 g0.
- The ideal-screening payload equivalent scales with the delta: 621 kg at +69.6 m/s,
  about 9 kg per m/s in this range (ideal rocket equation, fixed losses, not a payload
  result).

## The sled-mass variant (`silo_sled_22t`, MagLifter's ~4 % of liftoff mass)

A 22 t carriage changes nothing for the vehicle (same exit speed, felt g, interface
force 21.28 MN, burnout speed) and raises the drive force to 22.14 MN, the drive energy
to 2.214 GJ (+4.1 %), the peak power to 1.698 GW and the electrical energy to
1,230 kWh. The braking distance and facility length are unchanged (60 m, 160 m at the
same 5 g0). The carriage's own braking energy is not modelled.

## Failed ignition: the fall-back coast (`silo_failed`)

The engines never light after the 76.71 m/s exit. Drag-free coast under mu/r^2:

| event | time after release [s] | altitude [m] | speed [m/s] |
|---|---|---|---|
| apex | 7.829 | 300.27 | 0 |
| meets the parked carriage (60 m above the mouth, its braking distance) | 14.83 | 60.0 | 68.6 down |
| back at the mouth (release altitude) | 15.658 | 0 | 76.71 down |
| shaft bottom (derived: v^2 = v_mouth^2 + 2 g_eff L) | - | -100 | 88.56 down |

- README: ~300 m and ~7.8 s. Under g0 the closed forms give 300.00 m and 7.822 s; the
  0.27 m and 0.007 s more here are g_eff < g0 at the surface (0.256 m) plus the mu/r^2
  weakening with altitude (0.014 m).
- The full 542.57 t stack comes back to the mouth 15.7 s after release at its exit speed
  and would reach the shaft bottom at 88.6 m/s. Unless the carriage is withdrawn within
  about 14.8 s, the first thing the stack hits on the way down is its own carriage,
  parked 60 m above the mouth after braking at 5 g0, at 68.6 m/s. Nothing in the model
  stops the fall; no abort is modelled.
- Drag at 77 m/s is about 0.4 % of the stack's weight (q = 3.6 kPa on ~10.5 m^2 at
  C_D ~ 0.5 against 5.3 MN), so the drag-free numbers are good to about that.
- A slightly tilted exit (the README's suggestion) is a planar question for Phase 2/3;
  with a 76.7 m/s exit and 15.7 s in the air, the sideways drift needed to clear a
  ~4 m bore is a few tenths of a degree of exit angle, but the same tilt is a sideways
  load on the interface during the push and an azimuth error at ignition. Not
  quantified here.

## Loads: 4 g on a full stack versus 5.7 g at burnout

The silo's distinctive load is not its peak g: the unthrottled stage 1 reaches 5.71 g0 at
burnout in every variant, pad included. It is that the 4.0 g0 (a + g_eff at 3 g0 net) is
felt by a full stack of 542.57 t, when the rocket is at its heaviest:

- interface force 21.28 MN, which is 2.6x the vacuum thrust (2.8x the sea-level thrust
  the README compared against); for comparison, the pad hold-down load m g_eff - T
  runs from +5.3 MN (weight at ignition) to -2.9 MN (tension at the end of the 2 s ramp);
- felt acceleration 2.6x the vacuum-thrust liftoff value of 1.55 g0 (the README quotes
  2.8x over the real 1.4 g0), so tank-bottom hydrostatic pressure and the thrust-structure
  compression rise by the same factor with full tanks;
- at burnout the 5.71 g0 act on 146.87 t of nearly empty stage, a load the stage is
  built for. The full-stack 4 g0 is a new load case, and the sweep shows the only way
  around it is a longer, slower shaft (1.5 g0 felt needs 600 m for 77 m/s) or a lower
  exit speed.

A hot start lowers the interface force to 12.7-12.9 MN (the engines carry part of the
load) at a propellant cost (RQ2); the felt acceleration on the stack is unchanged.

## Findings stated plainly, including the ones against the concept

- The reference silo delivers +69.6 m/s at stage-1 burnout over the pad, of which
  76.7 m/s is the exit speed, -14.7 m/s the post-release ignition loss, +5.4 m/s the
  hold-down credit that the pad convention gives every after-release-lit variant, and
  +2.2 m/s the altitude term. Its ideal-screening payload equivalent is 621 kg, below
  the README's 685 kg yardstick at the same exit speed, because the yardstick has no
  ignition loss.
- 19 % of the exit speed is lost to a 0.5 s delay and a 2 s ramp; a lag-type startup
  loses twice as much (RQ2). The ignition loss is a fixed cost, so the concept pays off
  only for exit speeds well above ~15 m/s, and the low-g, short-stroke corner of the
  sweep (22 m/s) is worth 7 m/s net.
- The facility is sized by peak power, not energy: 1.6 GW for 2.6 s. Energy is 2.1 GJ
  (0.6 MWh mechanical, 1.2 MWh electrical at 50 %), and a 22 t sled adds 4 %.
- The load case is the 4 g0 on a full stack and the 21 MN interface force, 2.6x the
  vehicle's own liftoff values. The model neither strengthens the stage nor counts the
  mass that would take (RQ1/RQ7).
- A failed ignition brings the full stack back to the mouth at 77 m/s in 15.7 s, onto
  its own carriage first; there is no abort in a vertical shaft without a tilt, and a
  tilt is a Phase 2/3 question.
- Hot starts do not raise the exit speed under this drive model; they trade propellant
  for drive energy (RQ2).
- Sensitivity: the delta against a pad with the same perturbation moves by < 0.5 m/s for
  +/-10 % of stage-1 dry mass or Isp, so the 1-D result is robust to the vehicle at
  fixed exit speed; the C_D sensitivity is n/a (no drag in Phase 1); the drive efficiency
  moves only the electrical energy (1,075-1,314 kWh).

## README observations (not edits)

- "122 MJ per EMALS launch": that figure is about one flywheel alternator's rated store
  (the README's prior-art row says 121 MJ each); a 45 t aircraft at 67 m/s carries
  0.5 x 45,000 x 67^2 = 101 MJ of kinetic energy. Either number keeps a 13 t launcher's
  38 MJ below one EMALS shot.
- The 5-25 m/s ignition-loss band is the linear-ramp band; a first-order lag of the
  same duration costs 10-40 m/s (RQ2).
- The README's 21.5 MN and 2.2 GJ / 1.65 GW use 549 t and g0; the simulator's vehicle
  file totals 542.57 t (as the README notes) and uses g_eff, hence 21.28 MN and
  2.13 GJ / 1.63 GW.

## Figures

Copied from results/silo_screening_1d/20260929T103623Z/plots/:

- RQ3-silo_cold_track_forces.png: drive and interface force during the cold push
  (constant 21.28 MN).
- RQ3-silo_cold_felt_g.png: felt axial acceleration, 4.0 g0 on the track, 0 during the
  0.5 s coast, 1.55 g0 at the end of the 2 s ramp, 5.71 g0 at burnout.
- RQ3-silo_cold_drive_power.png: drive power, linear to 1.63 GW at release.
- RQ3-silo_cold_altitude.png: altitude from release to stage-1 burnout at 134.8 km.
- RQ3-silo_failed_altitude.png and RQ3-silo_failed_speed.png: the fall-back coast,
  apex 300.27 m at 7.83 s, back at the mouth at 15.66 s at 76.7 m/s.
- RQ3-silo_sled_22t_track_forces.png: the 22 t carriage raises the drive force to
  22.14 MN while the interface force stays at 21.28 MN.

## Superseded by 2-D

The payload questions of this note are superseded by RQ3-silo-screening-2d.md (planar
2-D model, payload capacity to a 200 km orbit; runs results/silo_screening_2d/
20260930T175743Z and 20260930T182453Z, results/silo_bridge_2d_readme/20260930T185034Z
and results/guidance_trigger_2d/20260930T174950Z, git 7ad381f) and, for max-Q and
q-alpha, RQ6-aero-2d-preliminary.md. The text above is kept unchanged as the record of
the 1-D model. In short (preliminary: sweep-optimized, unthrottled, free kick with no
alpha aerodynamics, no structural mass charged for the 4 g0 track load): the reference
cold-start silo gains +1,498.8 kg on the gate vehicle (+1,345 to +1,667 kg under the
+/-10 % cases; the vehicle calibrates +14.3 % high; 83.1 kg net, 130.7 kg gross, of it
is the pad's clamped-ramp convention) and +1,394.4 kg on these README masses (bridge
experiment), against this note's 621 kg ideal-screening equivalent of the burnout
delta. The difference is partly a change of figure of merit and of the fork's inputs,
and partly lower gravity and steering loss after release, back-pressure, drag and the
pad's hold-down burn (RQ3-silo-screening-2d.md, Bridge). Exit speed, track loads,
drive energy and power, facility length and the failed-ignition coast carry over,
scaled by the heavier 2-D stack.
