# RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload

Status: preliminary, 2026-10-03. Concept A only (a vertical silo whose drive imposes a
prescribed acceleration, `constant_accel`). Planar 2-D model, sweep-optimized guidance (not
an optimal-control solution; Phase 5), unthrottled. Pre-registered in commit c2a4cf0
(docs/phases/inputs/2026-10-03-sp1-preregistration.md), with Amendment 1 in d336933
(reporting code only; no case, budget, criterion or reading changed). Every new number
below comes from runs made from the clean commit b3150c1 (b3150c1754ee); comparison
numbers from earlier notes and from validation are cited where they appear.

## The question

README research question 1, "Net benefit", asks how payload or propellant changes with
exit speed after interface mass, extra structure and ignition losses, and where the
break-even is. This note answers the propellant form of that question for concept A: at
the pad's payload and orbit, how much stage-1 propellant can a silo-pushed rocket leave
out, and how much assumed extra stage-1 structure cancels the saving. It does not answer
the question for other vehicle classes (RQ8), for interface hardware carried on the
vehicle, or for a structure sized for the push load (no structural model exists yet).

## Caveats (read first)

- **Calibration.** The gate vehicle (configs/vehicles/generic_f9_class_2d.yaml) carries
  26,054.4 kg to the reference orbit, +14.3% against the published 22,800 kg, outside the
  +/-10% band (docs/findings/CAL-f9-leo-2d.md; the user accepted the miss on 2026-09-30).
  Every offload is a difference between runs of this vehicle model, not a Falcon 9
  figure. The bridge row (README-loads fork, +8.3%, inside the band) is the robustness
  check against the miss.
- **Sweep-optimized and unthrottled.** Both sides of every comparison fly the same
  restricted guidance family (vertical rise, kick, gravity turn, linear-tangent stage 2)
  with gamma*, the kick angle and the LTG pair solved per run. No throttle: max-Q and
  q-alpha are upper bounds, and no max-Q limit constrains the offloaded runs.
- **No structural mass for the push.** The fully fuelled stack rides the push at 4.0 g0
  felt (3 g0 net). The penalty rows add an assumed stage-1 dry mass; they are
  assumptions, not a sized structure.
- **Drive.** A prescribed constant acceleration with no force or power limit, a massless
  carriage and a vented shaft with no air drag. Under this drive a hot start cannot add
  exit speed, and drive efficiency moves only the electricity.
- **Partly filled tanks.** The offloaded vehicle keeps every dry mass (tank structure
  included), engine, the fairing and the aerodynamics, and keeps each stage's mixture
  ratio. It is an under-filled vehicle, not one redesigned around the smaller load
  (which would also shed tank mass; RQ7). No ullage, centre-of-gravity or residual
  effect is modelled.
- **Free kick.** No angle-of-attack aerodynamics. The run command's offloaded assisted
  runs kick at the first lit instant at 72 to 77 m/s (the pad at 50 m/s, after a vertical
  rise), and their q-alpha is 1.6 to 5.3 times the pad's. The sweep points kick at 50 to
  128 m/s: the full-load runs of the 200 and 300 m points of sweep 1 kick at 104 and
  128 m/s with q-alpha 7.7 and 17.3 times the pad's (574.1 and 1,293.3 against 74.7 Pa
  rad, derived ratios). Their offloaded runs are not written; at the headline the
  offloaded run's q-alpha is 1.75 times its full-load run's (derived: 226.9 / 129.9).
- **Stage 1 is the only headline.** Stage-2 and both-stage offloads are quoted net of the
  pad's own offload in that mode and labelled, as pre-registered, a property of the
  vehicle model's stage-2 sizing and guidance; why the stage-2 figure is so large is not
  established. The stage-2 case failed its independent verification, so its gross
  removal is a flagged lower bound; the net figure, which also subtracts a flagged pad
  control, is uncertain both ways ("Stage 2 and both stages").

## Definition

- **Offload x** [kg]: propellant removed from a full load, along a mode: stage 1 only,
  stage 2 only, or both (the same fraction of each load). The tanks are partly filled, so
  the liftoff mass falls by x; every dry mass is unchanged unless a penalty row adds an
  assumed one (docs/physics.md, "Propellant offload at fixed payload").
- **Reference payload P_ref** = 26,054.4 kg (26,054.396 kg): the full-load pad's payload
  capacity P* on the same vehicle, orbit (200 km circular, 28.5 deg, due east) and search
  budget (id a17a0160...a7df).
- **x\*** is the largest evaluated offload whose residual propellant m_res at insertion is
  >= 0 when the assisted run flies P_ref, with gamma* re-optimised (the feasible-side
  convention of P*). The recorded run flies exactly P_ref and ends inserted with
  0 <= m_res < 0.05 kg. So the comparison is between **different vehicles carrying the
  same payload to the same orbit** (`OFFLOAD_COMPARISON_BASIS`).
- **Pad control.** The same solve on the pad, in every mode. For stage 1 it is a
  consistency test of the solver (the pad should find nothing to remove); stage-2 and
  both-stage offloads are quoted net of it.
- **Verification.** An independent payload search on the vehicle offloaded by x* must
  return P_ref within 1e-4 x P_ref (2.6 kg); otherwise the case is flagged
  `offload_verify_mismatch` and x* is a lower bound.
- **Paired pad.** The pad flown with the same offload and no push. It separates the head
  start from the lighter, higher thrust-to-weight stack.

The pre-registration says plainly that the headline was not unknown: the step 5 and 6
validation tests had already solved it (41,262.908 kg; docs/physics.md, "Cross-vehicle
decomposition", Measured). What was fixed in advance is the design around it and how
each result is read.

## Provenance

| command | results directory | git | contents |
|---|---|---|---|
| `run experiments/silo_offload_2d.yaml` | results/silo_offload_2d/20261003T112934Z | b3150c1754ee, clean | pad, silo_cold, silo_hot_ramp_on_track, silo_cold_200m; 11 offload cases; pad controls in three modes; the headline's paired pad; 8 sensitivity arms |
| `sweep experiments/silo_offload_2d.yaml` | results/silo_offload_2d/20261003T112949Z | b3150c1754ee, clean | 5 sweeps, 20 points, a verified stage-1 offload solve at every point |
| `run experiments/silo_offload_2d_readme.yaml` | results/silo_offload_2d_readme/20261003T112956Z | b3150c1754ee, clean | the bridge: pad, silo_cold, the headline case, its paired pad and stage-1 pad control on the README-loads fork |

Numbers are copied from each directory's summary.md and metrics.json (the latter where
the summary does not print a value: the paired comparison's attribution terms, peak
q-alpha and peak drive power of the offloaded runs, sweep-point ignition times). Derived
numbers say "derived" and show the arithmetic. Sweep-point values come from each
sweep's sweep_index.csv. Every run and comparison passes its blocking checks: "No run
and no comparison is bug_suspect" in all three summaries.

## Headline

**At the pad's payload and orbit, the 3 g0, 100 m cold-start silo (exit 76.7 m/s, stage 1
lit 0.5 s after release with a 2 s ramp) lets the gate vehicle leave out 41.26 t of
stage-1 propellant: 10.04% of the 410.9 t stage-1 load and 7.96% of the 518.4 t total
(silo_cold_s1, sweep-optimized). That is 2.76 times the ideal-screening estimate at the
same release speed (14.98 t). It charges no structural mass for the 4 g0 push: an assumed
+2, +4 and +8.1 t of stage-1 dry mass leave 32.29, 22.88 and 1.98 t, and about 8.5 t
(extrapolated) leaves nothing. Under +/-10% of stage-1 dry mass, Isp, C_D and drive
efficiency the offload stays between 38.67 and 44.46 t.**

Caveats that sit beside this number:

- **The calibration miss and the bridge.** On the README-loads fork, a vehicle with other
  stage masses that calibrates inside the band (+8.3%), the same case removes 36.01 t,
  9.10% of its 395.7 t stage-1 load (2.53 times its 14.25 t screening offload). The
  fraction of stage 1 is 9.4% lower in relative terms than on the gate vehicle
  (derived: 9.09943 / 10.0421 - 1), inside
  the pre-registered agreement band of about 10%, near its edge. Read the headline as
  9 to 10% of stage 1 across the two forks, not as a Falcon 9 figure. The bridge's
  paired pad (the same offload, no push) falls 1,309.5 kg short of that fork's P_ref
  (bridge summary.md). By the same two-order split as below, the lighter stack is 26 to
  27% of the bridge's 208.67 m/s of ideal delta-v (derived: 208.670 - 152.014 = 56.66 m/s
  with the paired attribution, 208.670 - 154.914 = 53.76 m/s with silo_cold's matched
  attribution at P_ref; bridge metrics.json), against 28 to 29% on the gate vehicle.
- **Structure.** The penalty rows are the only stand-in for the structure a 4 g0
  full-stack push needs, and the needed mass is unknown (no structural model; TODO.md
  B-004, README Phase 3). See "Structural penalty rows".
- **Part of it is the lighter stack, not the push.** Flown without the push, the same
  41.26 t offload leaves the pad 1,402.0 kg short of P_ref, so the push is needed to
  carry it. But by a difference between runs, 63 to 67 m/s (28 to 29%) of the 228.2 m/s
  of ideal delta-v the offload removes is the lighter stack's own thrust-to-weight gain,
  which the push makes usable but does not produce; the release speed and the head
  start's trajectory effects carry 64 to 66%. The range is bracketed by the two orders
  of the two-step split ("Head start or lighter stack? The paired pad"). Read as the
  pre-registration worded it, the paired pad's 1,402.0 kg shortfall is small against the
  41.26 t offload (3.4%, derived), so the pre-registered reading says most of the offload
  is the lighter stack's thrust-to-weight; the delta-v split is a reading chosen after
  the run.
- **Part of it is a baseline convention.** 14.4 m/s of the 228.2 m/s the offloaded
  vehicle does without (6.3% of the decomposition; 15.6 m/s, 6.8%, on the paired-pad
  order of the split) is the pad's 2.7 t burned on the hold-down, which a silo lit after
  release does not pay.
- **Loads beside it.** The offloaded run flies a max-Q 3.35% above the pad's (38,438.5
  against 37,191.4 Pa), where the full-load silo flew 16.0% below it; its q-alpha is
  3.04 times the pad's (226.9 against 74.7 Pa rad); the stack feels 4.0 g0 on the
  track (20.81 MN at the interface).
- **Sweep-optimized, unthrottled, free kick, prescribed drive, partly filled tanks.**

| quantity (silo_cold_s1 against the full-load pad, both at P_ref) | value | source |
|---|---|---|
| stage-1 offload x* | 41,262.9 kg (41.2629 t) | run summary.md, offload table |
| % of the stage-1 / total load | 10.0421% / 7.95967% | same |
| status; recorded run | ok; inserted, m_res 3.4e-5 kg | same; metrics.json `offload.cases[0].solve` |
| difference from the validation measurement (41,262.908 kg) | +0.00004 kg (derived), against about 3.8 kg of resolution: reproduced | physics.md, "Cross-vehicle decomposition" |
| independent verification: P* of the offloaded vehicle | 26,054.4047 kg, +0.0085 kg from P_ref (tolerance 2.6 kg): passed | run summary.md |
| stage-1 pad control | x_pad = 0, m_res(0) = -0.0016 kg: a resolution effect, consistency test pass | run summary.md, "Pad controls" |
| ideal-screening offload at 76.7072 m/s | 14,976.6 kg; ratio 2.75516 | run summary.md |
| decomposition | explained, residual 4.5e-12 m/s | same |
| liftoff mass | 531,091.5 kg against the pad's 572,354.4 kg | same |
| MECO after release | 138.531 s against 151.328 s | same |
| max-Q (unthrottled) | 38,438.5 Pa, +3.35% above the pad's (at 53.5 s, Mach 1.56) | same; metrics.json `offload.runs.silo_cold_s1` |
| peak q-alpha (unconstrained) | 226.9 Pa rad at 0.5 s (the kick), pad 74.7 Pa rad | metrics.json `offload.runs.silo_cold_s1`; run summary.md variants table |
| peak felt axial g in flight | 5.19546 g0 (pad 5.19547) | run summary.md |
| peak felt g on the track; interface force | 3.996 g0; 20.81 MN | same |
| facility length incl. braking | 160 m (100 m stroke + 60 m at 5 g0) | same |
| electricity of the push; peak drive power | 1,156.36 kWh; 1.597 GW | same; metrics.json |
| flags | none | same |

The handoff probe read about 41.1 t off by hand; that comparison is a sanity check only,
never a target.

## Why about 2.76 times the ideal-screening estimate

The README's screening converts the release speed into propellant at fixed losses (14 t,
3.6%, at 77 m/s on README masses; 14.98 t, 3.6%, on the gate vehicle). CLAUDE.md requires
the loss breakdown to explain any beat over it, or it is treated as a bug. The
cross-vehicle decomposition (docs/physics.md, "Cross-vehicle decomposition") splits the
ideal delta-v that the offloaded vehicle can do without, D_id(pad) - D_id(case) = c1 ln(m0
/ (m0 - x*)) = 228.204 m/s, into the head start and the differences in the losses, the
pre-flight burn, the fairing term and the margin. It closes to 4.5e-12 m/s, so the beat is
explained, not a bug.

| term (silo_cold_s1 against the pad, both at P_ref) | m/s | kg of the 41,262.9 kg split | share (derived) |
|---|---|---|---|
| release speed | +76.707 | +13,869.9 | 33.6% |
| gravity + steering (the only split read as physics) | +124.710 | +22,549.5 | 54.6% |
| of which gravity / steering (not read separately) | +124.775 / -0.065 | +22,561.3 / -11.8 | |
| pre-flight (the pad's 2.7 t burned on the hold-down) | +14.408 | +2,605.2 | 6.3% |
| back-pressure | +13.280 | +2,401.2 | 5.8% |
| drag | -0.877 | -158.5 | -0.4% |
| fairing | -0.024 | -4.4 | 0.0% |
| final speed + margin | +7.6e-5 | +0.014 | 0.0% |
| **sum = D_id(pad) - D_id(case)** | **228.204** | **41,262.9** | 100% |
| residual | 4.5e-12 | | |

Figure: RQ1-2d-derived_decomposition.png (drawn from these metrics.json values). Of its
+124.71 m/s gravity + steering bar, 68 to 72 m/s is the lighter stack's own
thrust-to-weight gain and 53 to 56 m/s the head start at equal stack mass (derived by
difference; see the paired-pad section below).

The vehicle does without 2.98 times its release speed in ideal delta-v (derived: 228.204 /
76.707). Converted at the screening's loss-averaged stage-1 Isp (295 s) against the
closure's vacuum Isp (311 s), and less the curvature of the two exponentials, that is the
2.755 ratio (docs/physics.md, "Cross-vehicle decomposition"). The release speed itself is
a third of the saving. More than half is lower gravity and steering loss: the offloaded
vehicle reaches MECO 12.8 s sooner (138.5 against 151.3 s), losing 1,367.2 m/s to gravity
against the pad's 1,492.0 m/s (recorded runs at P_ref; RQ1-2d-pad_losses.png and
RQ1-2d-silo_cold_s1_losses.png). Back-pressure (the silo run is higher at every time) adds
13.3 m/s, and the pad's hold-down burn 14.4 m/s. Drag takes back 0.9 m/s: the lighter
stack is faster in the dense air.

The pre-flight term is a baseline convention, not the push: the pad is clamped from
ignition at -2 s to release, burning 2,697.5 kg it then does not carry. RQ3-2d's
pad_instant pair valued the same convention at 83.1 kg of payload net (5.5% of that
headline). No pad lit at release was run with an offload here, so the net share of the
convention in this offload is not measured.

### Head start or lighter stack? The paired pad

The gravity term of a single cross-vehicle pair mixes two effects: the head start, and a
stack 41.3 t lighter at liftoff whose higher thrust-to-weight spends less time against
gravity. The paired pad (silo_cold_s1__pad: the pad with the same 41,262.9 kg stage-1
offload and no push) separates them.

- The pad offloaded by 41.26 t carries **24,652.4 kg, 1,402.0 kg short of P_ref** (run
  summary.md). The assisted vehicle with the same offload carries P_ref (its
  verification search: 26,054.4 kg), **+1,402.04 kg** on one vehicle. So the lighter stack
  does not carry the offload by itself: without the push the same tanks carry 1.4 t less payload.
  At equal stack mass the head start is worth 1,402.0 kg, 93.5% of the 1,498.8 kg it is
  worth on the full-load stack (derived: 1,402.04 / 1,498.83).
- The lighter stack is still worth something on its own. Offloaded by 41.26 t, the pad
  loses only 0.0340 kg of payload per kg removed (derived: 1,402.03 / 41,262.9), against
  the ideal screening's fixed-loss rate of 0.0511 kg/kg at this release speed (derived:
  765.4 kg of payload for the 14,976.6 kg screening offload, both at the pad's payload).
  The thrust-to-weight gain recovers about a third of the ideal cost on its own (derived,
  approximate: the two rates are taken at different offload sizes). Recorded gravity
  losses show the same order: pad 1,492.0 m/s, the offloaded pad 1,406.2 m/s (at its own
  24,652 kg), the offloaded silo 1,367.2 m/s (at P_ref).
- The matched attribution of the assisted run against the paired pad, both at the paired
  pad's P* (metrics.json `offload.cases[0].paired_pad.comparison.attr_*`; not printed in
  summary.md), gives d dv_margin = +161.473 m/s = release speed 76.707 + gravity + steering
  53.044 (gravity 43.938, steering 9.107) + pre-flight 15.571 + back-pressure 12.054 + drag
  3.525 + fairing 0.572 m/s, residual 1.7e-11 m/s. In kg of the 1,402.04 kg: release
  666.0 (47.5%), gravity + steering 460.6 (32.9%), pre-flight 135.2 (9.6%),
  back-pressure 104.7 (7.5%), drag 30.6 (2.2%), fairing 5.0 (0.4%). This is RQ3-2d's
  split of the full-load gain (46 / 34 / 9 / 8 / 2%), almost unchanged on the lighter
  stack.
- **How the pre-registered reading is applied.** Section 7 of the pre-registration reads
  the paired pad's margin "against the offload": if it is small, most of the offload is
  the lighter stack. **Read as written, the branch fires**: the 1,402.0 kg margin is 3.4%
  of the 41,262.9 kg offload (derived), which is small, and the pre-registered reading is
  then that most of the offload comes from the lighter stack's thrust-to-weight, not from
  the head start. This note states that reading but does not adopt it, because the two
  quantities are not commensurate (kilograms of payload against kilograms of
  propellant). In equivalent ideal delta-v,
  an interpretation the pre-registration does not spell out, the push at equal stack
  mass, the pad's hold-down convention included, carries 161.5 of the 228.2 m/s (71%;
  165.2 m/s, 72%, in the other order below) and the lighter stack 28 to 29%. Both
  readings are stated here and in the readings table.

**What fraction is the push itself** (derived by difference). A two-step split depends on
the order of the steps, so it is taken both ways. Order A: the full-load pad, then the pad
offloaded by x* (the paired pad), then the offloaded silo; it uses the paired attribution
at the paired pad's 24,652 kg and the decomposition at P_ref, 1.4 t apart. Order B: the
full-load pad, then the full-load silo_cold, then the offloaded silo; it uses silo_cold's
matched attribution at P_ref (run summary.md, Checks: d dv_margin +165.248 m/s) and the
decomposition, both at P_ref. Of the 228.2 m/s of ideal delta-v the offload removes:

| part (derived) | order A | order B |
|---|---|---|
| release speed | 76.7 m/s (33.6%) | 76.7 m/s (33.6%) |
| the head start's trajectory effects at equal stack mass | 69.2 m/s (30.3%: gravity + steering 53.0, back-pressure 12.1, drag 3.5, fairing 0.6) | 74.1 m/s (32.5%: gravity + steering 56.4, back-pressure 13.6, drag 3.5, fairing 0.6) |
| the pad's hold-down convention | 15.6 m/s (6.8%) | 14.4 m/s (6.3%) |
| the lighter stack's own thrust-to-weight gain (the remainder) | 66.7 m/s (29.2%: 228.204 - 161.473) | 63.0 m/s (27.6%: 228.204 - 165.248) |

The order moves the lighter stack's share by 3.8 m/s (the interaction of the two steps).
The push and what it does to the trajectory carry 64 to 66% of the offload, the baseline
convention 6 to 7%, and the lighter stack, which the pad would get too if it could fly
with less propellant, 28 to 29%. The pad cannot: its stage-1 pad control removes nothing
at P_ref. Of the 124.7 m/s gravity + steering term alone, 53 to 56 m/s is the head start
at equal stack mass and 68 to 72 m/s the lighter stack (124.710 - 53.044 and 124.710 -
56.433); the lighter stack also loses about 4.4 m/s more to drag (3.525 + 0.877 and
3.507 + 0.877, derived), since it is faster in the dense air.

Figure: RQ1-2d-silo_cold_s1__pad_losses.png (the paired pad's cumulative losses).

## Structural penalty rows and break-even

The headline charges nothing for the 4 g0 full-stack push. The penalty rows re-solve the
stage-1 offload with an assumed stage-1 dry mass added to the assisted run only (the pad
keeps its dry mass). They are parametric assumptions, not a structure sized for the load.

| assumed stage-1 dry mass added | x* [t] | % of stage 1 | erosion per tonne (derived) | pre-registered linear estimate x*(0)(1 - dm/8.1 t) | offload / screening | liftoff mass vs pad | max-Q vs pad | electricity of the push | peak drive power | interface force |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 41.263 | 10.04% | | 41.263 | 2.755 | -41,262.9 kg | +3.35% | 1,156.4 kWh | 1.597 GW | 20.81 MN |
| +2 t | 32.285 | 7.86% | 4.49 t/t (0 to 2) | 31.075 | 2.156 | -30,285.2 kg | -2.18% | 1,180.3 kWh | 1.630 GW | 21.24 MN |
| +4 t | 22.876 | 5.57% | 4.70 t/t (2 to 4) | 20.886 | 1.527 | -18,876.0 kg | -7.57% | 1,205.1 kWh | 1.664 GW | 21.69 MN |
| +8.1 t | 1.980 | 0.48% | 5.10 t/t (4 to 8.1) | 0 | 0.132 | +6,119.5 kg | -18.19% | 1,259.5 kWh | 1.739 GW | 22.67 MN |

(The last three columns are the offloaded runs': run summary.md and metrics.json
`offload.runs`. Every row feels 3.996 g0 on the track and needs a 160 m facility.) Every
penalty row ends ok and verifies within 0.003 kg (the 0 t headline row within 0.0085 kg),
and every row has a closing decomposition (run summary.md). Figure:
RQ1-2d-derived_penalty_rows.png.

- **Each tonne of assumed stage-1 structure takes 4.5 to 5.1 t of propellant off the
  offload, and the erosion steepens.** Every row lies above the pre-registered linear
  estimate (by 1.21, 1.99 and 1.98 t), so the offload is not gone faster than estimated.
- **Break-even (extrapolated, not interpolated).** The +8.1 t row still carries 1.98 t,
  so the zero lies beyond the last row: a line through the +4 and +8.1 t rows reaches it
  at 8.49 t, and quadratic and cubic fits through the four rows at 8.47 t (derived; the
  steepening erosion suggests the true crossing is a little lower). **About 8.5 t of
  extra stage-1 dry mass, 38% of the 22.2 t stage-1 dry mass, removes almost all of the
  offload.** In payload space RQ3-2d put the break-even at 8.1 t by a linear extrapolation;
  in offload space it is slightly above.
- The offload falls to the ideal-screening estimate (14.98 t) at about 5.5 t of assumed
  penalty (derived: interpolated between the +4 and +8.1 t rows, 4 + (22.876 - 14.977) /
  5.0965). At +8.1 t the vehicle lifts off 6.1 t heavier than the pad and removes 0.48% of
  its stage-1 propellant: a silo that needs that much strengthening replaces almost no
  propellant.

## Depth and g-level: does only the exit speed matter?

**Sweep 1 (stroke at 3 g0).** The offload grows monotonically with the silo depth, at a
falling rate per m/s:

| stroke | exit speed | x* | % of stage 1 | screening offload / ratio | kick | max-Q vs pad | electricity (offloaded run) | peak drive power (full-load point run) | interface force (full-load point run) | facility |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 m | 38.35 m/s | 18,765.1 kg | 4.57% | 7.54 t / 2.489 | after a vertical rise to 50 m/s | +0.20% | 301.3 kWh | 0.861 GW | 22.46 MN | 40 m |
| 50 m | 54.24 m/s | 28,653.6 kg | 6.97% | 10.63 t / 2.695 | after a vertical rise to 50 m/s | +1.14% | 591.9 kWh | 1.219 GW | 22.47 MN | 80 m |
| 100 m | 76.71 m/s | 41,262.9 kg | 10.04% | 14.98 t / 2.755 | at ignition, 71.8 m/s | +3.35% | 1,156.4 kWh | 1.725 GW | 22.49 MN | 160 m |
| 200 m | 108.48 m/s | 56,827.2 kg | 13.83% | 21.06 t / 2.698 | at ignition, 103.6 m/s | +8.09% | 2,245.0 kWh | 2.443 GW | 22.52 MN | 320 m |
| 300 m | 132.86 m/s | 67,285.8 kg | 16.38% | 25.69 t / 2.619 | at ignition, 127.9 m/s: unconstrained kick, an upper bound | +12.51% | 3,299.1 kWh | 2.995 GW | 22.54 MN | 480 m |

(sweep_1/sweep_index.csv and the points' metrics.json; the screening offload is x* over
the recorded ratio; max-Q against the pad's 37,191.4 Pa. The offloaded runs of sweep
points are not written, so peak power and interface force are the full-load runs'; the
offloaded headline's are 1.597 GW and 20.81 MN. Every point feels 3.996 g0 on the
track.) Figure: RQ1-2d-derived_offload_vs_exit_speed.png.

- The marginal offload falls from 622 to 561, 490 and 429 kg per m/s of exit speed over
  the four steps (derived). The ratio to screening peaks at the 100 m point. No kink is
  visible where the kick regime changes between 50 and 100 m; five points cannot resolve
  one. The 100 m point equals the run command's headline to the printed digits
  (Amendment 1's first-branch reading beside the cap, "Other pairs": x* 3e-8 kg apart,
  the same recorded gamma*_ref, 22.98640 deg, so R_rec = 0.25 kg; equal on both
  readings, the sweep's P_ref being the run's to every printed digit).
- Max-Q of the offloaded run rises with the depth, to 12.5% above the pad's at 300 m.
  Peak q-alpha of the points' full-load runs is 58.9 and 49.4 Pa rad at 25 and 50 m (at
  the kick after the vertical rise, 8.78 and 4.67 s after release, below the pad's 74.7)
  and 129.9, 574.1 and 1,293.3 Pa rad at 100, 200 and 300 m (at the kick at ignition,
  0.5 s after release) (sweep_index.csv and the points' metrics.json; the offloaded runs
  of sweep points are not written).
- The 200 and 300 m points verify to +0.67 and +0.72 kg (about 17 and 18 kg of offload at
  the headline's slope, an estimate: their x* may be that much low, 0.03% of x*), 76 to
  140 times the other sweep points' gaps (0.005 to 0.009 kg) but below the 2.6 kg flag.
  docs/physics.md, "SP1 research notes", gives the likely cause.

**Sweep 2 (stroke 50 to 300 m at the fixed exit speed 76.7072 m/s).** The offload is flat:
41,262.97, 41,262.97, 41,262.97 and 41,262.91 kg, a spread of 0.066 kg (largest at
50 m, smallest at 300 m), within 0.25 kg, so flat to the solves' own resolution, the
pre-registered reading (R = 2.55 kg not approached). Beside it (Amendment 1): the two
points that set the spread record gamma*_ref 22.98982 and 22.98636 deg, a difference of
0.00346 deg, so R_rec = 0.25 + 65.7 x 0.00346 = 0.477 kg, and the spread is below that too.
The four x* fall in two gamma*_ref clusters (22.9864 and 22.9897 deg) about 0.065 kg apart.

What depth buys at a fixed exit speed is a gentler push at the price of energy and
length:

| stroke (net accel) | felt g on the track | peak drive power (full-load point run) | peak electrical power per kg (derived) | interface force (full-load point run) | electricity (offloaded run) | per kg of offloaded liftoff mass | facility |
|---|---|---|---|---|---|---|---|
| 50 m (6 g0) | 7.00 g0 | 3.02 GW | 10.53 kW/kg | 39.4 MN | 1,012.2 kWh | 6.86 kJ/kg | 110 m |
| 100 m (3 g0) | 4.00 g0 | 1.73 GW | 6.01 kW/kg | 22.5 MN | 1,156.4 kWh | 7.84 kJ/kg | 160 m |
| 200 m (1.5 g0) | 2.50 g0 | 1.08 GW | 3.76 kW/kg | 14.0 MN | 1,444.7 kWh | 9.79 kJ/kg | 260 m |
| 300 m (1 g0) | 2.00 g0 | 0.86 GW | 3.00 kW/kg | 11.2 MN | 1,733.0 kWh | 11.75 kJ/kg | 360 m |

(sweep_2/sweep_index.csv and the point metrics.json files; electricity per kg derived
with the offloaded liftoff mass, 572,354.4 kg - x*; peak electrical power per kg derived
as the full-load point run's peak drive power over its liftoff mass, 573,853.2 kg, and the
50% drive efficiency.) Every value matches the pre-registered closed forms (7.0, 4.0,
2.5, 2.0 g0; 10.5, 6.0, 3.8, 3.0 kW/kg; 6.9, 7.8, 9.8, 11.7 kJ/kg; 110 to 360 m). The
300 m push costs 1.71 times the electricity of the 50 m push (derived): the drive also
lifts the vehicle through the stroke.

**silo_cold_200m_s1** (run command, 200 m at 1.5 g0, the same release speed) removes
41,262.97 kg, +0.0625 kg against the headline; the two record gamma*_ref 0.003265 deg
apart, so R = 0.25 + min(65.7 x 0.003265, 2.30) = 0.46 kg (section 3, first branch), and
the difference lies within 0.25 kg: the two read as equal. Its decomposition matches the
headline's to 0.0025 m/s in the gravity + steering sum (124.7072 against 124.7096 m/s),
to 0.0013 m/s or better in drag, back-pressure and fairing, and to 0.0004 m/s in the
D_id change; gravity and steering separately differ by -0.048 and +0.046 m/s, trading
against each other with the 0.0033 deg gamma*_ref difference (the split between them is
not read as physics). Sweep 2's points against the two run-command solves (Amendment 1,
"Other pairs"): within 0.066 kg of the headline and of silo_cold_200m_s1, so equal on the
verdict and beside it (R_rec at most 0.475 kg); sweep 2's 200 m point reproduces
silo_cold_200m_s1 to the 12 digits written. It feels 2.50 g0 on the track instead of 4.00
(13.00 against 20.81 MN at the interface; peak drive power 0.997 against 1.597 GW), for a
260 m facility instead of 160 m and 1,444.7 kWh instead of 1,156.4 kWh (+24.9%, derived).

**Reading.** For a cold start lit a fixed time after release, the flight after release
does not depend on the stroke in this model: at a fixed exit speed the unlit vehicle
leaves the mouth in the same state whatever the drive, and the guidance clocks run from
the ignitions. So the offload at a fixed exit speed is the same by construction, as the
pre-registration stated (section 7). Sweep 2 and silo_cold_200m_s1 confirm that the code
honours this to 0.066 kg: they test the solver, not the physics of depth. Depth at a
fixed exit speed then trades felt g and peak power for electricity and facility length.
Its lower felt g (2.0 g0 at 300 m against 7.0 g0 at 50 m) would pay off only through a
lighter structure for the push, which no run here charges (the penalty rows are
assumptions). The exit speed alone does not set the offload: at the same 76.7 m/s, where
the thrust ramp starts moves it by up to 5.7 t above the headline (sweep 3) and 14.6 t
below it (sweep 4, lit 200 m up). Across exit speeds the rate per m/s falls.

## Ramp start: hot starts on the carriage, late starts in the air

Same silo (3 g0, 100 m, 76.7 m/s), with the 2 s ramp started at different points:

| ramp start | ignition relative to release | propellant burned before release | x* | % of stage 1 | electricity (offloaded run) | peak drive power (full-load run) | max-Q vs pad |
|---|---|---|---|---|---|---|---|
| 100 m deep (push start, sweep 3) | -2.607 s | 4,335.7 kg | 44,375.2 kg | 10.80% | 811.7 kWh | 1.129 GW | +6.78% |
| 94.6 m deep (silo_hot_ramp_s1, run command; full thrust at release) | -2.000 s | 2,697.5 kg | 46,013.4 kg | 11.20% | 914.7 kWh | 1.134 GW | +6.78% |
| 75 m deep (sweep 3) | -1.304 s | 1,146.1 kg | **46,958.5 kg** | 11.43% | 1,043.9 kWh | 1.359 GW | +6.47% |
| 50 m deep (sweep 3) | -0.764 s | 393.3 kg | 46,393.8 kg | 11.29% | 1,114.7 kWh | 1.531 GW | +5.81% |
| 25 m deep (sweep 3) | -0.349 s | 82.3 kg | 45,170.2 kg | 10.99% | 1,144.5 kWh | 1.663 GW | +5.08% |
| at the mouth (0 m, sweep 3) | 0 | 0 | 43,631.2 kg | 10.62% | 1,151.2 kWh | 1.725 GW | +4.36% |
| 10 m up (event, sweep 4) | +0.131 s | 0 | 43,014.8 kg | 10.47% | 1,152.6 kWh | 1.725 GW | +4.09% |
| silo_cold_s1 (headline, run command) | +0.5 s | 0 | 41,262.9 kg | 10.04% | 1,156.4 kWh | 1.725 GW | +3.35% |
| 40 m up (event, sweep 4 / closed form, sweep 5) | +0.540 s | 0 | 41,070.2 / 41,070.5 kg | 9.995% | 1,156.8 kWh | 1.725 GW | +3.27% |
| 100 m up (event, sweep 4) | +1.435 s | 0 | 36,655.6 kg | 8.92% | 1,166.4 kWh | 1.725 GW | +1.65% |
| 200 m up (event, sweep 4 / closed form, sweep 5) | +3.304 / +3.302 s | 0 | 26,664.4 / 26,679.3 kg | 6.49% | 1,188.2 / 1,188.1 kWh | 1.723 GW | -0.99% |

(sweep_index.csv of sweeps 3 to 5, the points' metrics.json for the ignition times, the
propellant burned before release and the interface force; the run summary and
metrics.json for silo_hot_ramp_s1 and silo_cold_s1, whose peak power is that of their
full-load runs silo_hot_ramp_on_track and silo_cold, the same basis as the sweep points';
the offloaded runs' are 0.991 and 1.597 GW. Every full-load run's peak interface force is
22.47 to 22.50 MN (offloaded: 20.63 MN for silo_hot_ramp_s1, 20.81 MN for the headline),
every row feels 3.996 g0 on the track, and the facility is 160 m throughout. Every point
solves at the same P_ref, ends ok with no flags and a closing decomposition.) Figure:
RQ1-2d-derived_offload_vs_ramp_start.png.

With impingement 0 the hot starts need less peak drive power (1.13 GW lit at the shaft
floor against 1.73 GW at the mouth) and less electricity: the on-track rocket thrust does
part of the drive's work. That favours them in energy and power, not in offload
("Impingement caveat" below).

- **Every hot start beats lighting at the mouth** (+744 to +3,327 kg), and the mouth
  start beats silo_cold by 2,368 kg. The pre-registered undercut test (a hot start that
  loses to the mouth start) did not fire.
- **The earliest start does not win, against the pre-registered expectation.** The
  expectation was the largest offload near 94.6 m (full thrust at release). Among the
  points the 75 m start gives the most, 945 kg more than silo_hot_ramp_s1 at 94.6 m; the
  start at the shaft floor (100 m) gives 2,583 kg less than the 75 m start and even less
  than the 25 m start. Under a prescribed acceleration, propellant burned on the track
  buys no exit speed. For the floor start against the 94.6 m start this is measured, not
  a reading: both reach release at full thrust with the same mass (523,643.50 kg, derived
  as the pad's liftoff mass less x* and the propellant burned before release) and fly the
  same flight afterwards (offloaded max-Q 39,712.56 and 39,712.58 Pa), and their offloads
  differ by 1,638.2 kg, the extra propellant the floor start burns on the track (4,335.7 -
  2,697.5 kg), to within 2 g. Why the 75 m start beats the 94.6 m start remains a reading
  (the sweep points' decompositions are written only as their status): a start too close
  to the mouth leaves more of the ramp to the air after release, one too deep burns more
  on the track for nothing but a lighter stack. The 75 m start is also best in payload
  (its full-load P* 27,814.1 kg against silo_hot_ramp_on_track's 27,788.2 kg), which
  refines RQ2-2d's "ramp ending at release is best" by 26 kg; no sensitivity run. Below
  it the payload and offload rankings differ: in payload the 94.6 m start beats the 50 m
  start by 7 kg (27,788.2 against 27,780.9 kg) and the floor start beats the 25 m start by
  8 kg (27,731.7 against 27,723.7 kg), the reverse of their offload order.
- **Late starts cost about 4.8 to 5.3 t of offload per second of delay** in the air
  (derived from sweep 4: 4.76, 4.93 and 5.35 t/s over the three steps). The headline at
  0.5 s lies on the same curve.
- **Event against closed form.** At 40 m the closed form removes 0.212 kg more than the
  event: within 2.55 kg, the two read as equal. At 200 m it removes 14.890 kg more,
  beyond R = 3.14 kg and inside the expected +3.14 to +30 kg (central estimate +12 to
  +17 kg): the sign is resolved, the 2.5 ms earlier ignition is worth more. Beside each
  pair (Amendment 1; they do not enter R), the recorded gamma*_ref: at 40 m 22.98942 deg
  (event) and 22.98602 deg (closed form), at 200 m 22.96791 and 22.97138 deg; none of the
  four points carries a flag.
- **Impingement caveat.** With an exhaust impingement fraction of 0 and no model of the
  plume in the shaft (back-pressure, heating, the carriage in the exhaust), all the
  on-track thrust offsets the drive force. That moves neither the trajectory nor the
  offload under the prescribed drive: the drive force is solved from the track equation,
  so it absorbs any force on the track, and the mass flow follows T_vac (pre-registration
  section 5). It does favour hot starts in electricity and power: their electricity and
  peak drive power are lower bounds. Their offload advantage rests on the prescribed
  drive instead. With a force- or power-limited drive (Phase 3) the on-track thrust would
  add exit speed and impingement and shaft pressure would take some of it back, so their
  offloads could move either way. silo_hot_ramp_s1's q-alpha is 393.0 Pa rad at t = 0,
  5.3 times the pad's.

## Stage 2 and both stages

Stated plainly: as pre-registered, these numbers are quoted net of the pad's own offload in
each mode and labelled a property of the gate vehicle model's stage-2 sizing and guidance,
not the silo's headline. Why the stage-2 figure is so large is not established by this
run, and the stage-2 case failed its independent verification.

| case | gross removal | pad control | quoted (net of the pad control) | verification | flags |
|---|---|---|---|---|---|
| silo_cold_s2 (stage 2 only) | 31,904.3 kg (29.68% of the 107.5 t stage-2 load) | 513.6 kg | 31,390.7 kg | **+15.36 kg against 2.6 kg: failed** | 4 |
| silo_cold_both (8.906% of each load) | 46,168.2 kg (36,594.3 + 9,573.8) | 0 | 46,168.2 kg | -0.0003 kg, passed | 0 |
| silo_cold_s1_s2pre2t (2 t from stage 2 first) | 42,768.5 kg (40,768.5 + 2,000) | 0 (stage 1) | 40,768.5 kg of stage 1 | +0.369 kg, passed | 0 |

- **The stage-2 result reverses the pre-registered expectation.** From the recorded
  marginal value of stage-2 propellant on the gate pad (about zero, measured at a fixed
  gamma* and in the adding direction), the pre-registration expected the stage-2 pad
  control to remove a large amount, leaving a small, ill-conditioned net figure. The pad
  control removed 513.6 kg (0.48% of the stage-2 load): m_res stays within +0.022 kg of
  zero over the first 0.5 t and then falls (-1.05 kg at 1,000 kg). So the net stage-2
  offload is large, 31.39 t (29.2% of the stage-2 load, derived), and in this model it is
  available only with the push: the pad alone can leave out 0.51 t. Why it is so large is
  unresolved: the pre-registered premise (near-free stage-2 propellant) held only over the
  first 0.5 t of the pad control, three quarters of the case's D_id change is the gravity
  + steering term of a reshaped ascent (303.0 of 404.1 m/s; steering loss 89.0 to
  5.9 m/s; below), and the case failed verification.
- **The pad control carries a flag and an uncertainty of its own.** Run summary.md,
  Flags: `search_vs_final_payload`, its search's x (513.443 kg) 0.114 kg from the final
  x_pad (513.556 kg), above the 1e-4 relative threshold of so small a number. Its
  verification passed (+0.2306 kg against 2.6 kg), but on the control's flat m_res curve
  that gap is about 73 kg of x_pad at the control's recorded slope (0.0031 kg/kg) and
  about 0.21 t at its final bracket's secant (0.0011 kg/kg; estimates, with the stage-1
  case's dm_res/dP of 0.993). So x_pad may be that much low and the net figure that much
  high, by 0.07 to 0.21 t (docs/physics.md, "SP1 research notes"); the case's own
  untaken offload (about 167 kg, below) points the other way.
- **Verification failed.** The payload search of the vehicle offloaded by 31,904.3 kg
  returned P* = 26,069.8 kg, +15.36 kg from P_ref (flag `offload_verify_mismatch`). By the
  pre-registration and docs/physics.md, x* is then a **flagged lower bound**: the solve
  left gamma* suboptimal. The untaken offload is about 167 kg (an estimate: 15.36 kg x
  0.993 / 0.0913, the stage-2 final bracket's secant, with the stage-1 case's dm_res/dP).
  The pre-registration blocks only the headline on this flag, so it blocks no finding; it
  meets exit criterion 3 only through its "or the case is flagged" branch.
- **The solve was hard.** Its four flags: the first search in x backed off 3 times (the
  counter counts halvings) from 2 failed evaluations at x = 32 t and 28 t, where the
  stage-2 linear-tangent shooting converged outside its direct-root window; the gamma*
  refine rejected 22.94 deg only by the direct-root rule; the refine's optimum sat at the
  lower edge of its 18 to 26 deg window, which was shifted once to 14 to 22 deg, where it
  ended at 17.49 deg (the pad: 22.99 deg); and the verification mismatch.
- **It reshapes the ascent.** Steering loss 5.9 against the pad's 89.0 m/s, LTG a 0.353
  against 0.610, gravity + steering term +303.0 m/s in the decomposition (D_id change
  404.1 m/s). With stage 1 full and the upper stack 31.9 t lighter, the peak felt axial g
  in flight is 6.475 g0 against 5.195 (+24.6%, at stage-1 burnout), and max-Q is 1.86%
  above the pad's. Figures: RQ1-2d-silo_cold_s2_angles.png and
  RQ1-2d-silo_cold_s2_felt_g.png.
- **Both stages remove more total tonnes than the headline**, 46.17 against 41.26 t
  (+4.91 t), with 4.67 t less from stage 1, as section 7 allowed, even though each
  stage-2 kilogram costs about twice the ideal delta-v of a stage-1 one (docs/physics.md,
  "Cross-vehicle decomposition"): the case's gravity + steering term is +215.1 m/s against
  the headline's +124.7 m/s (D_id change 316.3 against 228.2 m/s; steering loss 52.6 m/s
  against the pad's 89.0), a property of the vehicle model's stage-2 sizing and guidance.
  Its max-Q is 7.48% above the pad's and its in-flight peak 5.52 g0.
- **The frontier point** (2 t taken from stage 2 first) leaves the stage-1 offload close to
  the headline's: 40.77 t, 0.49 t less, with 1.51 t more in total. Its verification gap
  (+0.369 kg) is more than 40 times any stage-1-only case of the run command (at most
  0.009 kg) but inside tolerance; sweep 1's 200 and 300 m points (+0.67 and +0.72 kg) are
  larger.

Stage 1 stays the only headline.

## Energy

| case | RP-1 removed | LOX removed | combustion heat of the RP-1 (LHV) | electricity of the push | heat / electricity |
|---|---|---|---|---|---|
| silo_cold_s1 (headline) | 12,402.0 kg | 28,860.9 kg | 533,657 MJ (148,238 kWh) | 4,162.9 MJ (1,156.36 kWh) | **128.2** |
| silo_cold_200m_s1 | 12,402.0 kg | 28,861.0 kg | 533,658 MJ | 5,200.9 MJ (1,444.69 kWh) | 102.6 |
| silo_hot_ramp_s1 | 13,829.8 kg | 32,183.7 kg | 595,096 MJ | 3,293.0 MJ (914.72 kWh) | 180.7 (note a) |
| silo_cold_s1_dry+8.1t | 595.3 kg | 1,385.2 kg | 25,613.7 MJ | 4,534.3 MJ (1,259.53 kWh) | 5.65 |

(run summary.md, offload table; all eleven cases range from 5.65 to 180.7.)

Note a: impingement 0, so the electricity is a lower bound. The 2,697.5 kg the hot ramp
burns on the track (about 0.81 t of RP-1, about 34,900 MJ at the same heating value;
derived with the stage-1 fuel fraction 123.5 / 410.9) does part of the drive's work and is
counted on neither side of the ratio.

- **The ratio is not an efficiency claim.** It leaves out the energy to produce the
  removed oxidiser (air separation and liquefaction), to extract, refine and deliver the
  fuel, the losses of generation, transmission and storage (the electricity is metered at
  the drive: positive drive work over the assumed 50% efficiency), and the facility's
  energy beyond the drive (braking, the carriage's return).
- Inputs: RP-1 123.5 t in stage 1 and 32.3 t in stage 2 (Espace & Exploration No. 39 via
  Wikipedia, the gate vehicle file's own propellant source), mixture ratio kept; lower
  heating value 43.03 MJ/kg, the MIL-DTL-25576E specification minimum (18,500 Btu/lb by
  ASTM D240), written down to 0.01 MJ/kg. Delivered lots run slightly higher, so both
  choices lower the heat slightly; neither favours the assist.
- Drive efficiency +/-10% moves only the electricity (1,051.24 and 1,284.85 kWh), so the
  headline ratio would read 141.0 and 115.4 (derived).
- In plain terms: on this accounting the 12.4 t of RP-1 removed (with 28.9 t of LOX) has a
  combustion heat 128 times the push's 1.16 MWh of metered electricity. That is a ratio of
  unlike quantities, not an efficiency or a substitution rate, and it depends on the
  structure charged: with the assumed +8.1 t of stage-1 structure it falls to 5.65.

## Sensitivity

Each arm perturbs the assisted run and the pad alike (drive efficiency the assisted run
only) and solves at that perturbed pad's own P_ref. The arms carry no independent
verification search, by design (`OFFLOAD_SENSITIVITY_BASIS`).

| parameter | -10%: P_ref / x* | +10%: P_ref / x* | change of x* |
|---|---|---|---|
| nominal | 26,054.4 kg / 41.263 t | | |
| stage-1 dry mass | 26,456.3 kg / 40.892 t | 25,661.0 kg / 41.640 t | -0.37 / +0.38 t (-0.90 / +0.91%) |
| stage-1 Isp_vac | 22,478.3 kg / 44.465 t | 29,927.4 kg / 38.668 t | +3.20 / -2.59 t (+7.76 / -6.29%) |
| C_D scale | 26,093.5 kg / 41.304 t | 26,015.5 kg / 41.222 t | +0.04 / -0.04 t (+/-0.10%) |
| drive efficiency | 26,054.4 kg / 41.263 t | 26,054.4 kg / 41.263 t | 0 (electricity 1,284.85 / 1,051.24 kWh) |

(run summary.md, offload "Sensitivity"; all eight arms ok, decompositions explained,
residuals at most 3.5e-10 m/s; offload / screening 2.56 to 2.99.)

- **Range 38.67 to 44.46 t** (9.41 to 10.82% of stage 1), set by the stage-1 Isp (a reading:
  with a better engine each tonne of stage-1 propellant is worth more delta-v, so the same
  head start replaces fewer tonnes; that arm's pad also carries 3.9 t more payload, so its
  P_ref moves). Stage-1 dry mass and C_D move the
  offload by under 1%.
- Drive efficiency and carriage mass cannot change the offload under the prescribed drive,
  by construction; they are no evidence either way.

## Max-Q and loads

- **The max-Q reduction is spent.** The full-load silo_cold flies a max-Q 16.0% below the
  pad's (31,237.6 against 37,191.4 Pa; RQ6). Offloaded to P_ref it flies 38,438.5 Pa,
  3.35% above it: a lighter stack climbs faster through the dense air. Seven of the
  eleven cases fly above the pad's max-Q (+1.86% to +7.48%); only the three penalty rows
  and the 5% fixed case fly below it. The paired pad (the pad with the same offload)
  reaches 44,556.1 Pa (metrics.json), 19.8% above the nominal pad's (derived): offloading
  without a push raises max-Q far more. All values are unthrottled upper bounds; there is
  no max-Q-constrained offload (no throttle model). Figure: RQ1-2d-silo_cold_s1_q_mach.png.
- **q-alpha** (unconstrained, no angle-of-attack aerodynamics) of the offloaded runs is
  119.9 to 393.0 Pa rad against the pad's 74.7, 1.6 to 5.3 times (metrics.json
  `offload.runs`); the headline's is 226.9 Pa rad at the kick 0.5 s after release (kick
  angle 4.13 deg, against 2.36 deg for the full-load silo_cold). The offload table does
  not print it; it belongs beside every offload number.
- **Peak felt g in flight** is unchanged for the stage-1 offloads at P_ref with no
  dry-mass penalty or stage-2 pre-offload (the headline, 200 m and hot-ramp cases: 5.19545
  to 5.19546 against the pad's 5.19547 g0; both stacks reach MECO with the same mass).
  The penalty rows fall to 5.13, 5.07 and 4.95 g0 (heavier at MECO by the added dry
  mass), the frontier case rises to 5.26 g0 (2 t less stage-2 propellant), the fixed 5%
  case, flying 783 kg more payload, feels 5.17 g0, and the stage-2 and both-stage cases
  reach 6.475 and 5.52 g0 (run summary.md, offload table).
- **On the track** the stack feels 4.0 g0 at 3 g0 net (3.996 g0; interface force 20.81 MN
  for the offloaded headline, 22.49 MN for the full-load silo_cold), and 2.5 g0 at 1.5 g0
  net over 200 m (2.496 g0; 13.00 MN). No structural mass is charged for either.
- Facility: 160 m (100 m stroke + 60 m braking at 5 g0), 260 m for the 200 m stroke.

## What goes against the hypothesis

The hypothesis is that any ground-supplied velocity cuts the propellant the rocket needs.
These results limit or undercut it, stated as plainly as the headline:

- **Structural mass can cancel it.** Every tonne of assumed stage-1 strengthening takes
  4.5 to 5.1 t off the 41.26 t offload; about 8.5 t (extrapolated) takes all of it, and
  at +8.1 t only 1.98 t (0.48% of stage 1) remains. How much structure a 4 g0 full-stack
  push needs is unknown in this model.
- **Part of the headline is not the push.** 14.4 m/s of the 228.2 m/s (6.3%, about
  2.6 t of the offload by the proportional split) is the pad's clamped hold-down burn, a
  baseline convention. By a difference between runs, another 63 to 67 m/s (28 to 29%;
  the two orders of the split, with the hold-down at 14.4 and 15.6 m/s) is the lighter
  stack's own thrust-to-weight gain, which the push makes usable but does not produce.
  Of the 124.7 m/s gravity + steering term, 68 to 72 m/s is the lighter stack. Read as
  the pre-registration worded it, the paired pad's 1,402.0 kg shortfall is small against
  the 41.26 t offload (3.4%, derived), so the pre-registered reading says most of the
  offload is the lighter stack's thrust-to-weight; the delta-v split is a reading chosen
  after the run.
- **The max-Q benefit disappears.** The full-load silo's 16% lower max-Q becomes a max-Q
  3.35% above the pad's once the push is cashed in as propellant, and up to 12.5% above
  at a 300 m stroke; q-alpha at the kick is 3.0 times the pad's at the headline and 5.3
  times for the hot ramp, and the full-load runs of sweep 1's 200 and 300 m points reach
  7.7 and 17.3 times (their offloaded runs are not written). Nothing throttles or limits
  either.
- **Diminishing returns with depth.** The offload per m/s falls from 622 to 429 kg as the
  stroke grows from 25 to 300 m, and the 300 m point is an unconstrained-kick upper bound.
  At a fixed exit speed, a gentler push costs 71% more electricity and a 3.3 times longer
  facility (300 against 50 m strokes) for the same offload, which is the same by
  construction in this model.
- **The earliest hot start loses.** Lighting at the shaft floor removes 2.6 t less than
  lighting 75 m deep, against the pre-registered expectation; under the prescribed drive,
  propellant burned on the track buys no speed (measured against the 94.6 m start: the
  1,638.2 kg of extra on-track burn is the offload difference). That ordering belongs to
  the prescribed drive and may change with a force-limited drive (Phase 3). Under the
  prescribed drive the hot starts' offloads do not depend on impingement or the
  unmodelled plume; their lower electricity and peak power do (impingement 0 makes those
  lower bounds).
- **A late start is expensive.** Each second of delay after release costs 4.8 to 5.3 t of
  offload; a start 200 m up (3.3 s) keeps only 26.7 t of the 43.6 t a start at the mouth
  gives.
- **The figure depends on the vehicle masses.** On the README-loads fork (its masses
  against the gate vehicle's: stage-1 dry 25.6 against 22.2 t, stage-1 load 395.7
  against 410.9 t, stage-2 dry 3.9 against 4.0 t, stage-2 load 92.67 against 107.5 t,
  fairing 1.9 against 1.7 t; engines and aerodynamics the same; it calibrates inside the
  band), the offload is 9.10% of stage 1 rather than 10.04% (-9.4% relative).
  Whether the gate vehicle's calibration miss inflates its figure is not established.
- **The stage-2 and both-stage numbers are not the silo's headline.** As pre-registered
  they are quoted net of the pad control and labelled a property of the vehicle model's
  stage-2 sizing and guidance. Why the stage-2 figure is so large is unresolved: the
  pre-registered premise (near-free stage-2 propellant) held only over the first 0.5 t of
  the pad control, three quarters of its D_id change is the gravity + steering term of a
  reshaped ascent (steering loss 89.0 to 5.9 m/s), and the case failed verification.
- **Energy.** The 128 heat-to-electricity ratio leaves out LOX production, fuel supply,
  grid losses and the facility; it is no efficiency claim and says nothing about cost. It
  falls to 5.65 with the assumed +8.1 t of stage-1 structure.

## Limits

- No structural model: the penalty rows are assumptions. No interface hardware on the
  vehicle (README "What can eat the gain").
- No throttle and no max-Q or q-alpha limit; no angle-of-attack aerodynamics for the kick.
- `constant_accel` only: no force or power limit, massless carriage, no shaft air or
  plume, braking added to the length, not modelled. Phase 3's linear motor and cable winch
  may change the depth and hot-start readings.
- Partly filled tanks of a fixed vehicle; no resized vehicle (RQ7), no ullage or
  centre-of-gravity effect.
- Sweep-optimized guidance in one family; Phase 5 may move the trajectory terms either way.
- Planar point-mass model, generic C_D(Mach) table, ICAO atmosphere with an isothermal
  extension; the gate vehicle's +14.3% calibration miss.
- The sensitivity arms are not independently verified; the sweep points get no paired pad,
  pad control or arms, and their offloaded runs are not written (the load and power
  columns of the sweeps describe the points' full-load runs; only max-Q and electricity
  describe the offloaded run).
- One vehicle class (medium launcher); RQ8 is untouched.

## How each pre-registered reading came out

Readings of docs/phases/inputs/2026-10-03-sp1-preregistration.md, sections 2, 3, 7 and 8,
taken as written (Amendment 1 changed no verdict), except the paired-pad row: its
criterion compares payload kg with propellant kg, so the literal verdict and this note's
delta-v reading are both given there.

| criterion (pre-registered) | result | reading |
|---|---|---|
| Headline reproduces the validation measurement (41,262.908 kg) within about 3.8 kg | +0.00004 kg | reproduced |
| Headline supports if ok, every blocking check passes, verification within tolerance, decomposition closes | ok; no bug_suspect; +0.0085 kg; residual 4.5e-12 m/s | supports |
| Beats screening by about 2.75 times, explained by the decomposition | 2.755, explained (gravity + steering, hold-down burn, back-pressure) | supports (beat explained, not a bug) |
| Stage-1 pad control: x_pad in [0, bound] if ok; no_offload passes only for -0.05 < m_res(0) < 0 | no_offload, m_res(0) = -0.0016 kg, bound 1.62 kg | pass (resolution effect) |
| Paired pad falls short; if the margin is small against the offload, most of the offload is the lighter stack | 1,402.0 kg short; margin 1,402.04 kg, 93.5% of the full-load gain and 3.4% of the offload in kg (derived); the lighter stack 28 to 29% of the ideal delta-v (derived by difference, bracketed by the two orders of the split) | falls short, as expected. Read as written, the small-margin branch fires (3.4% is small): most of the offload is the lighter stack's thrust-to-weight. The note does not adopt that reading, because the branch compares payload kg with propellant kg, which are not commensurate; read in equivalent ideal delta-v (this note's interpretation, not spelled out in the pre-registration) it does not fire. The pre-registration defines no supports outcome here; both readings are reported |
| Penalty rows near 31, 21 and about 0 t (linear estimate); gone at +2 or +4 t undercuts further | 32.29, 22.88, 1.98 t; above the estimate at every row; zero at about 8.5 t (extrapolated) | undercuts in proportion to the unknown structure, no faster than estimated |
| Fixed cases: P* - P_ref about 650-810 kg (5%) and 5-7 kg (10%); the wrong side by more than 2.6 kg is an inconsistency | +783.2 and +6.80 kg | consistent |
| Stage 2: large pad control, small ill-conditioned net | gross x* 31.90 t, verification failed; pad control 0.51 t (its own flag: search_vs_final_payload, 0.07 to 0.21 t); net 31.39 t | expectation reversed; the gross x* is a flagged lower bound (about 0.17 t, an estimate), and the net figure is uncertain both ways by about 0.2 t; labelled a property of the vehicle model as pre-registered; why it is so large is unresolved |
| Both may remove more total tonnes than the headline | 46.17 against 41.26 t (gravity + steering term +215.1 against +124.7 m/s) | as allowed; labelled a property of the vehicle model |
| Frontier: stage-1 offload stays close to the headline's | 40.77 t (-0.49 t) | met |
| Sweep 1 grows monotonically; a fall undercuts | 18.8 to 67.3 t, monotonic; no kink resolved | supports (at a falling rate per m/s; 300 m an upper bound) |
| Sweep 2 flat: spread within 0.25 kg | 0.066 kg (R_rec 0.477 kg beside it) | flat to the solves' own resolution, as expected by construction (at a fixed exit speed a cold start's flight after release does not see the stroke, whatever the drive): a solver-consistency check, not a finding about depth |
| Sweep 2 closed forms of felt g, peak electrical power per kg, electricity per kg, facility | 7.0 / 4.0 / 2.5 / 2.0 g0; 10.53 / 6.01 / 3.76 / 3.00 kW/kg (derived); 6.86 / 7.84 / 9.79 / 11.75 kJ/kg; 110 to 360 m | met |
| silo_cold_200m_s1 against the headline (first branch, R = 0.46 kg) | +0.0625 kg | equal |
| Sweep 3: largest near 94.6 m, falling toward the mouth; 0 m above silo_cold; a hot start losing to the mouth undercuts | peak at 75 m (46.96 t), 94.6 m 0.95 t lower, 100 m below 25 m; every hot start above the mouth; 0 m +2.37 t over silo_cold | undercut test not triggered; the location expectation not met. The pre-registered "upper bound on their merit" (impingement 0) holds for the hot starts' electricity and power; impingement moves no offload under the prescribed drive (pre-registration section 5), so the offload ordering rests on the prescribed drive |
| Sweeps 4 and 5 fall as the start moves up: 10 m above silo_cold above 40, 100, 200 m | 43.01 > 41.26 > 41.07 > 36.66 > 26.66 t | met |
| 200 m, closed form minus event: +3.14 to +30 kg (central +12 to +17) | +14.890 kg (gamma*_ref 22.97138 and 22.96791 deg beside it; no flags) | met; sign resolved |
| 40 m, closed form minus event: within +/-2.55 kg | +0.212 kg (gamma*_ref 22.98602 and 22.98942 deg beside it; no flags) | equal |
| Bridge: x*/m_p1 within about 10% relative of the gate's | 9.10% against 10.04% (-9.4%); ideal delta-v change 208.67 against 228.20 m/s (-8.6%); its paired pad 1,309.5 kg short, the lighter stack 26 to 27% of its ideal delta-v (derived; 28 to 29% on the gate vehicle) | agrees, near the edge of the band |
| Sensitivity: report the range; an arm that fails is reported as such | all 8 ok and explained; 38.67 to 44.46 t | reported |
| Blocking checks of section 8 (bug_suspect, decomposition residuals, pad control) | none fires | findings not blocked |
| Headline-blocking flags (verify mismatch, nonmonotone, capped refine, reference_failed) | none on the headline | not blocked |
| KI-006: M4 and M2 over gamma* +/- 0.5 deg disclosed | next section | disclosed |

## KI-006: M2 and M4 over gamma* +/- 0.5 deg

- **In the run command**, the matched-attribution checks exist for the three variant
  comparisons (silo_cold, silo_hot_ramp_on_track, silo_cold_200m) and for the headline's
  paired comparison. All 24 check records (closure, attribution and M2 to M5 of each
  comparison) pass at gamma*_ref, M5 as n/a; the 12 that are evaluated at the +/-0.5 deg
  neighbours (M2, M3 and M4 of each comparison) pass at both. Paired comparison: M2
  (diagnostic) 0.536, range 0.447 to 0.626; M3 0.689
  (0.686 to 0.692); M4 (blocking) share 0.149 (0.066 to 0.222); M5 n/a; all robust
  (metrics.json).
- **The cross-vehicle offload cases and the sensitivity arms carry no M2 to M5**, by
  design: their decomposition is checked for closure only. KI-006 cannot be answered for
  them from these outputs.
- **In the bridge**, all 12 check records (silo_cold and the paired comparison) pass at
  gamma*_ref (M5 n/a); the 6 evaluated at the neighbours (M2, M3, M4) pass at both.
- **At the sweep points** the checks belong to each point's payload comparison against the
  pad, not to its offload solve. M2 (diagnostic) fails at sweep_1 run_0001 (25 m: 0.098,
  range -0.031 to 0.227, both neighbours fail), sweep_1 run_0002 (50 m: 0.294, 0.199 to
  0.390, not robust), sweep_4 run_0003 (100 m up: 0.278, 0.207 to 0.350, not robust),
  sweep_4 run_0004 (200 m up: -0.073, both neighbours fail) and sweep_5 run_0002 (200 m
  up, closed form: -0.072, both neighbours fail). M4 (blocking) passes at gamma*_ref
  everywhere but is not robust at sweep_4 run_0004 and sweep_5 run_0002: share 0.346,
  range 0.049 to 0.624 and 0.050 to 0.623, failing at one neighbour (above the 0.5
  limit). The verdict at gamma*_ref stands as pre-registered; these points' beats rest on
  a term split that moves with gamma*. As in RQ3-2d, M2 fails where the cold start's
  in-air startup is large against the head start (slow releases, late ignitions).

## Reproduction

From a clean checkout of b3150c1, in the repository root:

    uv run python -m launchsim run experiments/silo_offload_2d.yaml
    uv run python -m launchsim sweep experiments/silo_offload_2d.yaml
    uv run python -m launchsim run experiments/silo_offload_2d_readme.yaml

- Experiment files: experiments/silo_offload_2d.yaml and experiments/silo_offload_2d_readme.yaml,
  byte for byte as committed in c2a4cf0 (pre-registration); Amendment 1 (d336933) changed
  reporting code only. Results: the three directories of "Provenance"; only their
  top-level summary.md files are tracked.
- The three commands were started within 22 s of each other (11:29:34, 11:29:49 and
  11:29:56 UTC, the directory names) and ran concurrently, not one after the other as the
  pre-registration lists them. No number depends on the order: each command re-solves its
  own pad, and the sweep's P_ref equals the run's to every printed digit (26,054.396 kg),
  as does its 100 m point's x*. Wall times under that load: docs/physics.md, "SP1
  research notes".
- Replay the headline beside the pad: `uv run python -m launchsim replay
  results/silo_offload_2d/20261003T112934Z --runs pad silo_cold_s1`.
- The four derived figures were drawn by a throwaway matplotlib script from the files
  named under "Figures" (not kept in the repository); every plotted value is in the
  tables above.

## Figures

Copied unchanged from results/silo_offload_2d/20261003T112934Z/plots/:

- RQ1-2d-pad_losses.png and RQ1-2d-silo_cold_s1_losses.png: cumulative gravity, drag,
  steering and back-pressure losses from release, both at P_ref (gravity 1,492.0 against
  1,367.2 m/s, back-pressure 63.1 against 49.9 m/s).
- RQ1-2d-silo_cold_s1__pad_losses.png: the paired pad (the same offload, no push) at its
  own 24,652.4 kg (gravity 1,406.2 m/s).
- RQ1-2d-pad_trajectory.png and RQ1-2d-silo_cold_s1_trajectory.png: altitude against
  downrange to insertion (MECO at 69.5 and 69.3 km).
- RQ1-2d-silo_cold_s1_q_mach.png: dynamic pressure and Mach of the offloaded headline;
  max-Q 38.4 kPa at 53.5 s, above the pad's 37.2 kPa (unthrottled).
- RQ1-2d-silo_cold_s2_angles.png and RQ1-2d-silo_cold_s2_felt_g.png: the stage-2 case's
  shallower ascent (gamma* 17.5 deg at MECO) and its 6.5 g0 at stage-1 burnout (a flagged
  case: verification failed).

Derived (drawn from the run's metrics.json and the sweeps' sweep_index.csv and point
metrics.json; caveat lines are in each figure's footer):

- RQ1-2d-derived_penalty_rows.png: stage-1 offload against the assumed stage-1 dry mass
  (0, 2, 4, 8.1 t) with the zero line and the pre-registered linear estimate; the dotted
  segment past 8.1 t is an extrapolation.
- RQ1-2d-derived_offload_vs_exit_speed.png: sweep 1 against the exit speed with the
  ideal-screening offload at each speed, and sweep 2's four fixed-exit-speed points
  (coincident at 76.7 m/s, equal by construction for a cold start at a fixed exit
  speed). The 300 m point is an unconstrained-kick upper bound. The footer gives the
  drive as 3 g0 for sweep 1 and 6 to 1 g0 for sweep 2.
- RQ1-2d-derived_offload_vs_ramp_start.png: sweeps 3 to 5 and the run command's
  silo_hot_ramp_s1 and silo_cold_s1 against the ignition time relative to release. Under
  the prescribed drive the hot starts' offloads do not depend on impingement (0 here) or
  the unmodelled shaft plume; their ordering belongs to the prescribed drive (Phase 3 may
  change it). Sweep 5's and the run command's markers are hollow, so the sweep-4 points
  they nearly cover stay visible (40 and 200 m up; silo_cold at 0.5 s sits beside the
  40 m point).
- RQ1-2d-derived_decomposition.png: the headline's cross-vehicle decomposition in m/s
  (gravity and steering shown as their sum, the only split read as physics). Its footer
  notes that 68 to 72 m/s of the gravity + steering bar is the lighter stack's own
  thrust-to-weight gain (derived by difference, "Head start or lighter stack?").
