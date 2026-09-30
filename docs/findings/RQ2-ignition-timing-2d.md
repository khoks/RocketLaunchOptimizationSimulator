# RQ2 (preliminary, 2-D): ignition timing on a vertical silo push

Status: preliminary. Phase 2 planar model, sweep-optimized guidance (not an
optimal-control solution; Phase 5). Supersedes the 1-D numbers of
RQ2-ignition-timing-1d.md for payload questions. The screening-beat investigation, the
v_k fairness rule and the full list of caveats are in RQ3-silo-screening-2d.md; they
apply here unchanged.

## Caveats (read first)

- Planar 2-D ascent, rotating spherical Earth (28.5 N, due east), ICAO atmosphere,
  generic C_D(M), back-pressure, unthrottled, a kick without angle-of-attack
  aerodynamics, sweep-optimized guidance (v_k = 50 m/s; the pre-registered fairness
  rule did not fire, RQ3-silo-screening-2d.md).
- Gate vehicle (mass set C), which calibrates +14.3 % high (CAL-f9-leo-2d.md; the user
  accepted the miss on 2026-09-30); every number inherits it.
- Drive: `constant_accel`, 3 g0 net, 100 m stroke, exit 76.707 m/s; a prescribed
  acceleration, so a hot start buys no exit speed. Carriage mass 0, drive efficiency
  0.5 (assumed), vented shaft, no drag in the shaft, infinite jerk.
- Startups (vehicle file, assumed): stage-1 linear 2 s ramp; the lag variants use a
  first-order lag with time constant tau; mass flow follows the vacuum thrust, and the
  net thrust is max(0, T_vac - p A_e), so partly lit engines at sea level pay
  back-pressure. The power-on C_D table is used in the unlit coast (a small bias toward
  cold starts; under 0.4 kg for the 0.5 s coast: 0.015 m/s of release-time speed at the
  anchor's 22.7 kg per m/s, RQ3-2d).
- The exhaust-impingement fraction f_imp on the carriage is an assumed amendment to the
  track equation; both bounds (0 and 1) are reported.
- No structural mass is charged for the 4.0 g0 full-stack load on the track
  (RQ3-silo-screening-2d.md, Caveats: about 184 kg of P* per tonne of stage-1 dry
  mass). The hot starts cut the interface force (14.5 to 14.8 MN against 22.5 MN) but
  not the felt g (3.996 g0 in every variant), so the penalty applies to all of them.

## Provenance

- results/silo_screening_2d/20260930T175743Z (run: the named variants) and
  results/silo_screening_2d/20260930T182453Z (sweeps: sweep_2 t_ign x t_ramp, sweep_3
  lag tau), both git 7ad381f227a9, clean, search budget a17a0160...a7df; summaries
  committed in 63b45c8. The sweeps are unpaired: every point is compared with the pad
  (P* 26,054.4 kg, identical in both directories).
- Every run passes its blocking checks; no `bug_suspect`. M2 is diagnostic (fails
  listed below).
- The like-for-like 2-D cold-start loss on the README masses is from
  results/silo_bridge_2d_readme/20260930T185034Z (git 7ad381f227a9, clean; derived:
  silo_instant minus silo_cold, 187.212 - 154.914 = 32.298 m/s of matched margin,
  26,395.7 - 26,094.4 = 301.3 kg).
- The 1-D values quoted are from RQ2-ignition-timing-1d.md
  (results/silo_screening_1d/20260929T103623Z and 20260929T103634Z).

## The measure

The yardstick is `silo_instant` (full thrust by a step at the instant of release;
unphysical). The 2-D ignition loss of a variant is measured two ways, both against
silo_instant: in kg, silo_instant's P* (27,880.4 kg) minus the variant's; and in m/s,
silo_instant's matched delta-v margin at the pad's P* minus the variant's (derived: the
difference of two matched attributions against the same pad at the same P_ref, so
every term is comparable). It is compared with the 1-D constant-g formula
g (t_d + t_r/2) for a ramp and g (t_d + tau) for a lag, evaluated with the 2-D g_ref =
9.7721 m/s^2, and with the 1-D integrated values.

## Ramp sweep (sweep_2: delay t_d x ramp t_r, silo_cold)

| t_d [s] | t_r [s] | P* [kg] | dP* vs pad [kg] | loss vs silo_instant [kg] | [m/s] | 1-D formula [m/s] | 2-D / formula | 1-D integrated [m/s] | of which g + s / back-pressure [m/s] | kick speed [m/s] | q-alpha [Pa rad] | M2 (diag.) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 27,768.3 | +1,713.9 | 112.1 | 11.850 | 4.886 | 2.43 | 5.04 | 10.60 / 1.18 | 76.7 | 196.0 | pass (0.635) |
| 0 | 2 | 27,655.7 | +1,601.3 | 224.7 | 23.808 | 9.772 | 2.44 | 10.08 | 21.27 / 2.39 | 76.7 | 170.9 | pass (0.541) |
| 0 | 3 | 27,542.5 | +1,488.2 | 337.8 | 35.887 | 14.658 | 2.45 | 15.12 | 32.01 / 3.64 | 76.7 | 147.2 | pass (0.444) |
| 0.5 | 1 | 27,666.5 | +1,612.1 | 213.8 | 22.654 | 9.772 | 2.32 | 10.08 | 20.71 / 1.81 | 71.8 | 150.8 | pass (0.545) |
| **0.5** | **2** | **27,553.2** | **+1,498.8** | **327.1** | **34.742** | **14.658** | **2.37** | **15.12** | **31.45 / 3.06** | 71.8 | 129.9 | pass (0.449) |
| 0.5 | 3 | 27,439.4 | +1,385.0 | 441.0 | 46.937 | 19.544 | 2.40 | 20.17 | 42.24 / 4.34 | 71.8 | 110.3 | pass (0.353) |
| 1 | 1 | 27,564.0 | +1,509.6 | 316.3 | 33.585 | 14.658 | 2.29 | 15.13 | 30.89 / 2.48 | 66.9 | 113.7 | pass (0.454) |
| 1 | 2 | 27,450.1 | +1,395.7 | 430.3 | 45.790 | 19.544 | 2.34 | 20.17 | 41.69 / 3.77 | 66.9 | 96.6 | pass (0.358) |
| 1 | 3 | 27,335.5 | +1,281.1 | 544.8 | 58.108 | 24.430 | 2.38 | 25.21 | 52.54 / 5.08 | 66.9 | 80.7 | fail (0.262) |

(bold: the shipped silo_cold.) The t_d = 0 rows are lit exactly at release with a ramp;
their "first lit instant" is the release, so they kick at 76.7 m/s. The "1-D integrated"
column is on the README masses (RQ2-1d); the like-for-like 2-D value on those masses
exists only for the shipped point (silo_bridge_2d_readme; RQ3-2d, Bridge).

**Caveat on the "dP* vs pad" column (pre-registered, experiments/silo_screening_2d.yaml):**
the pad keeps its 2 s ramp at every point, so at t_r = 1 s and 3 s the dP* vs pad also
contains an engine-startup change the pad does not get (the pad's hold-down burn,
mdot t_r / 2, would be 1,349 / 2,697 / 4,046 kg for t_r = 1 / 2 / 3 s). It favours the
silo at 1 s and penalises it at 3 s, by roughly 40 kg either way (derived, a linear
estimate from the pad_instant pair: removing the whole 2 s clamped ramp is worth
+83.1 kg net). Only t_r = 2 s is like for like. The loss columns (against silo_instant)
compare silo with silo and are unaffected.

## Lag sweep (sweep_3: 0.5 s delay, first-order lag tau, silo_cold_lag)

| tau [s] | P* [kg] | dP* vs pad [kg] | loss vs silo_instant [kg] | [m/s] | 1-D formula g (t_d + tau) [m/s] | 2-D / formula | 1-D integrated [m/s] | of which g + s / back-pressure [m/s] | q-alpha [Pa rad] | M2 (diag.) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 27,553.2 | +1,498.8 | 327.2 | 34.747 | 14.658 | 2.37 | 15.12 | 31.45 / 3.08 | 129.9 | pass (0.449) |
| 2 | 27,326.6 | +1,272.2 | 553.7 | 59.068 | 24.430 | 2.42 | 25.20 | 52.99 / 5.63 | 92.2 | fail (0.258) |
| 3 | 27,099.6 | +1,045.2 | 780.8 | 83.694 | 34.202 | 2.45 | 35.28 | 74.72 / 8.26 | 61.2 | fail (0.063) |

The lag axis likewise differs from the pad's 2 s ramp in startup shape (pre-registered
caveat); its dP* vs pad is not like for like. The loss columns against silo_instant are.

## What the sweeps show

- **The 2-D ignition loss is 2.29 to 2.45 times the 1-D formula** on the gate vehicle.
  For the model change alone, compare like with like: on the same README masses the
  bridge gives 32.30 m/s (301.3 kg) for the shipped 0.5 s + 2 s, 2.14 times the 1-D
  integrated 15.12 m/s; on the gate vehicle it is 34.742 m/s (327.1 kg). In payload,
  every second of full-thrust deficit after release (g_ref x 1 s = 9.77 m/s of
  formula) costs 211 to 225 kg on this vehicle (derived: loss in kg / formula x
  9.7721). The shipped cold start gives back 327.1 kg of the instant start's
  +1,826.0 kg; a 1 s delay with a 3 s ramp gives back 544.8 kg, a 3 s lag 780.8 kg.
- **The 1-D structure survives.** The loss depends on the startup through t_d + t_r/2
  (ramp) or t_d + tau (lag) to within 7 %: at a formula value of 14.66 m/s the
  combinations (0, 3 s), (0.5, 2 s), (1, 1 s) and the 1 s lag cost 35.89, 34.74, 33.59
  and 34.75 m/s. The 1-D rule that a lag of tau costs as much as a ramp of 2 tau holds:
  tau 1 s against the 2 s ramp, both after 0.5 s, 34.747 against 34.742 m/s (327.2
  against 327.1 kg).
- **At equal formula value, ramp time costs slightly more than delay time** (35.89
  against 33.59 m/s at 14.66 m/s of formula), 1-D had them equal (15.12 and 15.13).
  Two candidate reasons, not separated: partly lit engines pay back-pressure at sea
  level (T = max(0, T_vac - p A_e); p A_e is about 620 kN against 8,227 kN at full
  vacuum thrust, so the first 7.5 % of a ramp gives no net thrust; derived), which
  matches the back-pressure column (3.64 against 2.48 m/s); and the kick starts at the
  first lit instant, so a longer delay kicks at a lower speed (66.9 against 76.7 m/s)
  on a different trajectory.
- **Why 2-D costs more than 1-D.** In 1-D the delayed vehicle loses g x (deficit time)
  of speed and arrives at burnout that much slower (plus a small altitude term). In 2-D
  the lost early speed also leaves the vehicle lower and slower through the whole
  gravity turn: for the shipped cold start the 34.74 m/s are 29.54 m/s of gravity loss
  (23.12 before MECO, 6.42 after), 1.91 m/s of steering, 3.06 m/s of back-pressure and
  0.23 m/s of drag and fairing (derived from the matched attributions). It is the mirror
  image of the release-speed amplification in RQ3-2d, where 76.7 m/s of release speed
  is worth 190.6 m/s of margin (2.48 times); here 14.66 m/s of formula loss costs 34.74
  m/s (2.37 times).
- **At equal gamma* the stage-1 part is larger than the matched split shows** (labelled
  launchsim probe, RQ3-silo-screening-2d.md, Provenance). With silo_cold and
  silo_instant both flown to the pad's gamma* (22.99 deg) at P_ref, the cold start's
  0.5 s coast and in-air ramp add 19.43 m/s of gravity loss before MECO (1,093.63
  against 1,074.20 m/s; 19.63 m/s at 21.65 deg). The instant pair (silo_instant against
  pad_instant, both lit at release) shows what the release saves before MECO at equal
  gamma*: 25.46 m/s at 22.99 deg (docs/physics.md, "Time-shift mechanism": 32.1 / 27.7
  / 23.8 m/s at 15 / 20 / 25 deg). So the cold start gives back most of the release's
  stage-1 gravity saving; the 23.12 m/s before MECO in the matched split above is
  measured at the two runs' own gamma*.
- **Loads.** A later or slower startup lowers the kick's q-alpha (196 to 61 Pa rad) but
  every point stays above the pad's 74.7 Pa rad except the 3 s lag (61.2). Max-Q rises
  slightly with the startup length (31.0 to 31.9 kPa), all below the pad's 37.2 kPa.
- **Screening.** Every ramp and lag point beats its screening yardstick: by 369.8 to
  1,038.5 kg against the stricter 675.3 kg (at P0), or 279.8 to 948.5 kg against
  765.4 kg (at the pad's payload; derived from sweeps summary.md and metrics.json). Each
  is attributed (screening status ok) with the same kind of gravity + steering,
  back-pressure and pre-flight terms as silo_cold, reduced by the startup loss in the
  columns above; none is a suspected bug.
- **Drive energy is unaffected** by the timing of a cold start (2.247 to 2.250 GJ; the
  small spread is the P* carried on the track).
- **M2 (diagnostic)** fails at the three slowest startups (1 s + 3 s ramp: 0.262; lag 2
  and 3 s: 0.258 and 0.063): the time-shift estimator does not model the in-air
  startup. No blocking check fails.

## Hot versus cold (named variants, same 3 g0, 100 m push)

| variant | stage-1 ignition vs release | propellant burned before release [kg] | P* [kg] | dP* vs pad [kg] | vs silo_instant [kg] | vs silo_cold [kg] | drive energy [GJ] | electrical at 50 % [kWh] | peak drive power [GW] | interface force max / min [MN] |
|---|---|---|---|---|---|---|---|---|---|---|
| silo_instant (yardstick) | 0, step | 0 | 27,880.4 | +1,826.0 | 0 | +327.1 | 2.250 | 1,250.2 | 1.726 | 22.50 / 22.50 |
| silo_cold | +0.5 s, 2 s ramp | 0 | 27,553.2 | +1,498.8 | -327.1 | 0 | 2.249 | 1,249.5 | 1.725 | 22.49 / 22.49 |
| silo_cold_lag | +0.5 s, lag 1 s | 0 | 27,553.2 | +1,498.8 | -327.2 | -0.04 | 2.249 | 1,249.5 | 1.725 | 22.49 / 22.49 |
| silo_hot_ramp_on_track | -2 s, 2 s ramp ending at release | 2,697.5 (on the track) | 27,788.2 | +1,733.8 | -92.2 | +235.0 | 1.834 | 1,018.7 | 1.134 | 22.50 / 14.79 |
| silo_hot_full (f_imp 0) | -4.607 s (2 s hold, then the push at full thrust) | 9,730.6 (2,697.5 in the hold, 7,033.1 on the track) | 27,543.0 | +1,488.6 | -337.4 | -10.2 | 1.459 | 810.8 | 1.112 | 14.78 / 14.50 |
| silo_hot_full_impinged (f_imp 1) | as silo_hot_full | 9,730.6 | 27,543.0 | +1,488.6 | -337.4 | -10.2 | 2.220 | 1,233.4 | 1.696 | 14.78 / 14.50 |

Matched attribution against silo_instant (derived, m/s at P_ref):

- silo_hot_ramp_on_track: -9.839 = pre-flight -14.408 (2,697.5 kg burned on the track)
  + gravity + steering +4.888 + drag, back-pressure and fairing -0.320.
- silo_hot_full: -36.153 = pre-flight -52.297 (9,730.6 kg) + gravity + steering
  +17.318 + drag -0.967 + back-pressure -0.062 + fairing -0.145.

Reading:

- **Propellant burned before release is partly recovered in 2-D.** The vehicle leaves
  the track lighter, with a higher thrust-to-weight, and flies a lower-loss trajectory:
  about a third of the burned delta-v comes back (4.9 of 14.4 m/s for 2.7 t, 17.3 of
  52.3 m/s for 9.7 t). In 1-D the same variants were 5.6 and 20.6 m/s behind the
  instant yardstick at burnout.
- **Lit on the carriage, ramp ending at release (silo_hot_ramp_on_track) is the best
  physical variant: +235.0 kg over the cold start** (24.9 m/s of margin, derived: it
  pays 14.4 m/s of pre-flight propellant to avoid a 2-D in-air startup that costs 36.3
  m/s of gravity + steering and 3.0 m/s of back-pressure). In 1-D the same comparison
  was +9.5 m/s at burnout. The trade favours the hot ramp more in 2-D because the
  in-air startup is amplified and the burned propellant is partly recovered.
- **A full hot start does not pay: silo_hot_full is 10.2 kg behind the cold start**
  (1-D: 5.5 m/s behind). Its 9.7 t burned in the hold and on the track costs slightly
  more than the startup it avoids. Under the +/-10 % cases the gap runs from -18.5 to
  +0.1 kg (Sensitivity, below): "no gain" is robust, the 10 kg deficit is not; the two
  are a tie within the sensitivity.
- **What a hot start buys under a prescribed acceleration is drive energy, power and
  interface force, not speed.** silo_hot_full at f_imp = 0 uses 35 % less drive energy
  (1.459 against 2.249 GJ) and 36 % less peak power (1.112 against 1.725 GW) and cuts
  the interface force to 14.5 to 14.8 MN; silo_hot_ramp_on_track saves 18 % energy and
  34 % peak power (the thrust is full at release, where the power peaks).
- **The impingement bound removes the saving**: with f_imp = 1 the drive energy and peak
  power return to 2.220 GJ and 1.696 GW, 1.3 % and 1.7 % below the cold start, lower
  only by the 9.7 t no longer aboard; payload, interface force and propellant cost are
  unchanged. The true f_imp for a carriage under nine engines is unknown.
- **Hold loads**: silo_hot_full is clamped for 2 s at the shaft bottom; the hold-down
  force reaches 2.03 MN in tension at the end of the ramp (the pad's is 2.04 MN).

## Sensitivity

The +/-10 % cases were pre-registered for silo_cold and silo_hot_full only. From the
recorded pairs (each against the pad re-run under the same perturbation; derived as
the difference of the two P*), silo_hot_full minus silo_cold is -10.2 kg nominal and
ranges from -18.5 kg (stage-1 Isp -10 %) to +0.1 kg (stage-1 Isp +10 %): stage-1 dry
mass -13.9 / -6.6 kg (-10 / +10 %), stage-2 Isp -18.2 / -1.2 kg, C_D -8.9 / -11.6 kg,
drive efficiency -10.2 kg. The full hot start never gains more than 0.1 kg over the
cold start, but its deficit is not robust in size. Drive efficiency -10 / +10 % moves
only the electrical energy (silo_hot_full 900.9 / 737.1 kWh, silo_cold 1,388.3 /
1,135.9 kWh). silo_instant, silo_hot_ramp_on_track and the sweep points
were not perturbed, so the 327 kg ignition loss, the +235 kg hot-ramp advantage and the
sweep numbers carry no sensitivity (open issue).

## What changes from 1-D, and why

| quantity | 1-D (RQ2-1d) | 2-D (this note) | why |
|---|---|---|---|
| cold-start loss, 0.5 s + 2 s ramp | 15.12 m/s at burnout (14.70 formula), README masses | 32.30 m/s, 301.3 kg on the same README masses (bridge; 2.14 times); 34.74 m/s, 327.1 kg on the gate vehicle | lost early speed also costs altitude and trajectory (gravity after MECO, back-pressure) |
| README band, 0-1 s delay, 1-3 s ramp | 5.04 to 25.21 m/s | 11.85 to 58.11 m/s, 112 to 545 kg | the same amplification, 2.29 to 2.45 times the formula |
| lag, tau 1-3 s, 0.5 s delay | 15.12 to 35.28 m/s | 34.75 to 83.69 m/s, 327 to 781 kg | same; a lag of tau still costs a ramp of 2 tau |
| hot_ramp_on_track vs cold | +9.5 m/s | +235.0 kg (+24.9 m/s) | in-air startup amplified; burned propellant partly recovered |
| hot_full vs cold | -5.5 m/s | -10.2 kg (-18.5 to +0.1 kg under +/-10 %) | lighter vehicle at release recovers a third of the burned delta-v |
| hot-start drive energy saving (f_imp 0) | 0.85 GJ (40 %) | 0.79 GJ (35 %) | same mechanism; heavier 2-D stack: gate masses and P* on the track |

The README observation of RQ2-1d stands and grows: its 5-25 m/s ignition-loss band is
the 1-D ramp band; in payload terms on this vehicle the ramp band is 112-545 kg and the
lag case (1-3 s after a 0.5 s delay) is 327-781 kg.

## Findings stated plainly

- The engines' startup after release is expensive in 2-D: the shipped 0.5 s delay and
  2 s ramp cost 327 kg of the instant yardstick's 1,826 kg (18 %); a 3 s lag after the
  same delay costs 781 kg (43 %) (no +/-10 % run: silo_instant and the sweep points
  were not perturbed; see Sensitivity). Every second of thrust deficit after release
  costs about 210-225 kg of payload on this vehicle, 2.29-2.45 times what the 1-D
  formula suggested (2.14 times the 1-D integrated value on the same masses, bridge).
  Only the t_r = 2 s ramp points are like for like in dP* vs pad; the losses against
  silo_instant are unaffected by the pad's startup.
- Lighting on the carriage so that full thrust arrives at release is the best physical
  option in this set (+235 kg over the cold start; no sensitivity run), paid for with
  2.7 t burned on the track; lighting for the whole push is not worth it (-10 kg
  nominal, -18.5 to +0.1 kg under the +/-10 % cases: no gain, a tie within the
  sensitivity).
- Under a prescribed-acceleration drive a hot start buys drive energy and peak power
  (up to 35 % and 36 %), not speed, and only if the exhaust does not push on the
  carriage. A force- or power-limited drive (Phase 3 `linear_motor`) is still needed
  before the hot-start question can be answered: there the on-track thrust would add
  exit speed.
- Preliminary: unthrottled, free kick, sweep-optimized guidance, calibration miss
  +14.3 %.

## Figures

Copied next to this note from results/silo_screening_2d/20260930T175743Z/plots/ (and
one lag point from results/silo_screening_2d/20260930T182453Z/sweep_3/run_0003/plots/):

- RQ2-2d-silo_cold_speed.png and RQ2-2d-silo_cold_mass_thrust.png: the 0.5 s coast and
  the 2 s ramp after release.
- RQ2-2d-silo_cold_lag_mass_thrust.png: the 1 s lag startup.
- RQ2-2d-sweep3_run_0003_mass_thrust.png: the 3 s lag (the slowest startup swept).
- RQ2-2d-silo_hot_ramp_on_track_track_forces.png and
  RQ2-2d-silo_hot_ramp_on_track_drive_power.png: the ramp on the track; the interface
  force falls from 22.50 to 14.79 MN, peak drive power 1.134 GW.
- RQ2-2d-silo_hot_full_track_forces.png, RQ2-2d-silo_hot_full_drive_power.png and
  RQ2-2d-silo_hot_full_mass_thrust.png: full thrust for the whole push after the 2 s
  hold; 1.112 GW peak.
- RQ2-2d-silo_cold_drive_power.png: the cold push, 1.725 GW at release.
