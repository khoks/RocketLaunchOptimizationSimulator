# 9. Reading results

[Manual contents](README.md) · Previous: [8. Outputs](08-outputs.md) · Next: [10. Validation](10-validation.md)

A summary is full of numbers. This chapter says which to look at first, what the checks
mean, and which caveats travel with every result. The worked numbers come from the shipped
2-D records `results/silo_screening_2d/20260930T175743Z` and
`results/silo_offload_2d/20261003T112934Z` and from the findings notes; all of them are
preliminary.

## Read in this order

1. **The summary lines at the end of the Checks section.** They say whether any run or
   comparison is `bug_suspect`, which runs had no screening check, which verdicts change
   within gamma\* +/- h, and which beats of the screening estimate no loss breakdown
   explains. In the shipped 2-D record the first of them reads "No run and no comparison is
   bug_suspect." A `bug_suspect` blocks findings until it is investigated. With an offload
   block, the "Offload checks" lines above them give the stage-1 pad control's verdict and
   each case's decomposition status ([below](#reading-an-offload-result)).
2. **The Flags section.** Anything the run wants you to know (a tensile interface, a
   braking drive, an ignored setting, a search flag). "(none)" is the normal case.
3. **The status rows** of the variant table: run status, search status, run checks,
   screening status.
4. **The figure of merit**: P\* and dP\* in 2-D, burnout speed in 1-D, with the yardstick
   rows beneath it.
5. **The losses, loads, energy and power**, and the sensitivity table before quoting any
   number.
6. **The Assumptions section.** Each line names the runs it applies to.
7. **With an offload block, the section "Propellant saved at fixed payload"**: its caveats
   first, then each case as described in [Reading an offload result](#reading-an-offload-result).

## Run statuses

| Status | Model | Meaning |
|---|---|---|
| `nominal` | 1-D | The run completed to its `end` |
| `inserted` | 2-D | Stage 2 reached the energy cutoff inside the targeting acceptance |
| `off_target` | 2-D | It reached the cutoff outside the acceptance (flagged with the misses) |
| `short_of_orbit` | 2-D | Stage 2 burned out before the cutoff |
| `impact` | both | The run ended on the ground (expected for a failed ignition) |
| `no_liftoff` | both | Thrust never passed weight on the pad |
| `drive_limit` | both | The prescribed push would need a negative drive force; the run stopped on the track ([5](05-assist-and-ignition.md#what-the-drive-does-and-what-it-does-not-model)) |
| `search_failed` | 2-D | The payload search failed; no recorded run (see `search_failure_kind`) |
| `guidance_failed` | 2-D | A fixed-guidance run whose guidance failed (for example a kick timeout, or `no_ignition`: a ramp start by event height that the coast never reaches) |
| `bug_suspect` | 2-D | A per-run check failed (closure, loss identity or insertion eccentricity). The trajectory's own status is in `trace_status` |

The search status is `ok`, `no_orbit`, `search_failed`, `none (fixed guidance)` or a skip
reason such as `skipped (end: impact (ignition stage1 fails))`. An offload solve has its own
statuses (`ok`, `no_offload`, `search_failed`; [5b](05b-offload.md#what-it-computes)), and
an offload pass or arm whose pad has no P\* is `reference_failed`.

## The loss identity

Every run must balance its books ([3. Concepts](03-concepts.md#the-loss-budget)):

    |v_rel,f| - |v_rel,0| = dv_vac - gravity - drag - steering - back-pressure

- **2-D, per run:** the identity residual must be below `checks.identity_tol_mps`
  (1e-5 m/s), the rocket-equation closure below `checks.closure_tol_mps` (1e-5 m/s), and an
  inserted run's eccentricity below `checks.insertion_e_max` (1e-6). The Checks section
  prints all three for every run. A failure makes the run `bug_suspect`.
- **1-D, per comparison:** the Checks section writes the change in burnout speed against the
  pad as a sum of terms (speed at release, delta-v, the two gravity parts, drag, steering,
  back-pressure) and its residual, which must be below 0.01 m/s. In the shipped 1-D runs the
  residuals are at the 1e-12 m/s level.

CLAUDE.md asks for the identity to close to better than 0.01 m/s over a full ascent; the test
suite checks it ([10. Validation](10-validation.md)).

## Payload capacity, the vehicle payload and residual propellant

- **P\*** is the largest payload that reaches the target orbit with zero residual
  propellant, each run with its own sweep-optimized guidance. dP\* is the run's P\* minus
  the baseline's.
- **P0** is the payload in the vehicle file (22.8 t on the Falcon 9-class files). The
  residual propellant and delta-v margin are taken at P0, with the guidance that is optimal
  for P\* (`residual_propellant_basis`), which the assumptions note is a few kg low, against
  the assist.
- **Payload excess** P0 - P\* is negative when the vehicle can carry more than P0. On the
  gate vehicle every inserted run in the shipped record has a negative excess, because the
  vehicle calibrates high.

Example (shipped record): pad P\* 26,054.4 kg, silo_cold 27,553.2 kg, dP\* +1,498.8 kg
(+5.75%).

## The screening yardstick and the screening-beat rule

CLAUDE.md sets a rule: if an assisted run beats the README's ideal screening estimate for its
release speed, its loss breakdown must explain why, or it is treated as a bug.

**The yardstick** is the ideal rocket-equation payload gain of the run's release speed,
computed two ways: on the vehicle at P0 and on the vehicle at the baseline's P\*. The verdict
uses the stricter (smaller) of the two (`screening_yardstick_kg`, basis `P0` or `P*_base`).
For silo_cold at 76.7 m/s the shipped summary gives 765.4 kg at the pad's P\* and 675.3 kg at
P0, so the yardstick used is 675.3 kg. silo_cold's +1,498.8 kg beats it (about 2.0 times the
765.4 kg figure the README quotes).

**The explanation** is a matched-payload attribution. Each variant is flown once more at the
baseline's P\*, and the difference in delta-v margin against the pad is split, exactly up to
the two runs' residuals, into terms in the variant's favour: release speed, final speed,
gravity, drag, steering, back-pressure, pre-flight burn and fairing (`attr_*` in
`metrics.json`, in m/s and kg). Only the sum of gravity and steering is interpreted: the
two trade against each other as gamma\* moves, so their split depends on where the search
landed. For silo_cold, README and [RQ3-2d](../findings/RQ3-silo-screening-2d.md) give, in the
matched basis: 46% release speed at face value, 34% lower gravity and steering loss, 9% the
pad's hold-down burn, 8% back-pressure, 2% drag. The breakdown explains the beat, so it is
not treated as a bug.

**The mechanism checks** (thresholds in the `checks` block):

| Check | What it requires | Blocks findings |
|---|---|---|
| closure | The variant's and the baseline's rocket-equation closures close | yes |
| attribution | The attribution closes; a beat with no attribution where one is required is an unexplained beat | yes |
| M2 (gravity) | The matched gravity gain is within [0.33, 3] of a time-shift estimate | **no**: diagnostic since the user's decision of 2026-09-30 (`m2_role: diagnostic`); reported, marked "(diagnostic)" |
| M3 (back-pressure) | The same for back-pressure, when it exceeds 1 m/s | yes |
| M4 (drag and steering) | Drag plus steering carry at most half of the gain beyond the release speed | yes |
| M5 (anchor) | When both yardstick runs exist, a variant released at silo_instant's speed gains no more than silo_instant over pad_instant, plus the payload equivalent of the pad's pre-flight burn, plus 1.5 kg | yes |

With M2 diagnostic, no blocking check bounds the gravity term of a beat; the closing
attribution and the printed M2 ratio are the evidence for it
([docs/physics.md](../physics.md), "Screening-beat rule (2-D)").

**Screening status** is `ok`, `bug_suspect` (a blocking check failed) or `not_checked` (no
attribution, by design: for example a comparison across two vehicles, such as a vehicle
sensitivity case against the unchanged baseline). A `not_checked` gain is not explained by a
loss breakdown, so no finding about a beat may rest on it; the Checks section lists those
under "Unexplained beats". In the shipped record they are the vehicle-parameter sensitivity
cases compared with the unchanged pad; the same cases compared with the same-perturbation
pad are attributed and `ok`.

**In 1-D** the rule is a bound: a variant's burnout-speed gain may not exceed its release
speed plus the hold-down credit plus an altitude term (`unexplained_gain_mps <= 0`). The
1-D "payload equivalents" are rocket-equation conversions of speed, not payload results.

## Upper-bound and kick flags

The row "dP\* is an unthrottled/unconstrained upper bound" is True when the run's max-Q or
q-alpha is above the pad's, or its kick is faster than `checks.unconstrained_kick_mps`. For
the silo runs it is True because of q-alpha: the kick happens at a higher speed and the
model charges nothing for it (there is no angle-of-attack aerodynamics). Max-Q itself falls
16.0% for the cold silo (31.24 against 37.19 kPa, unthrottled;
[RQ6](../findings/RQ6-aero-2d-preliminary.md)).

## Sensitivity cases

Each case is compared with the unchanged baseline and, for a vehicle parameter, with the
baseline under the same perturbation. Read the second column for vehicle parameters: it
compares one vehicle with itself. In the shipped record silo_cold's gain stays between
+1,345 and +1,667 kg under every +/-10% case (README). The screening-Isp and
drive-efficiency cases leave P\* unchanged by construction (they move only the yardstick,
and only energy and power, respectively).

## Reading an offload result

An offload row ([5b](05b-offload.md)) compares **different vehicles carrying the same
payload to the same orbit**: the full-load pad, and the assisted vehicle with less
propellant in its tanks. It is a different kind of comparison from the payload rows above,
and it has checks of its own. Read a case in this order: the Checks section's "Offload
checks" lines, the pad controls, the case's status, verification and flags rows, the quoted
offload with its basis, then the decomposition, the paired pad, the loads beside it, and
the energy rows last.

### Quoted and gross figures

Each case quotes one offload, and the cases table prints it first with its basis:

- **A stage-1 solve** quotes its x\*, gross: "x\* at P_ref, gross: stage 1, the headline".
- **A `stage2` or `both` solve** quotes x\* net of the pad control's x_pad, labelled "a
  property of the vehicle model, not of the assist". The gross rows beside it are not a
  saving of the assist. Stage 1 is the only headline.
- **A fixed case** quotes its imposed offload; its figure is its own P\* against P_ref
  (`payload_delta_kg`).
- **"not quoted"** means the case's own solve did not end `ok` or `no_offload`, or (for
  stage 2 and both) the pad control has no offload to net it against.

### Verification and flags

An `ok` solve is re-checked by an independent payload search of the offloaded vehicle,
which must return P_ref within the printed tolerance (`checks.search_final_flag_rel` x
P_ref). When it does not, the case carries `offload_verify_mismatch` and its x\* is a lower
bound (the solve left gamma\* short of its best). In an offload flag, the inner search's
words "payload" and "P" name the offload x, not a payload; such flags carry the marker
`(P = offload x)`. In the shipped run the stage-1-only cases verified within 0.009 kg of
P_ref against a 2.6 kg tolerance (the case with 2 t taken from stage 2 first within
0.37 kg), and the stage-2 case failed (+15.36 kg), so its gross removal is a flagged lower
bound ([RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md), "Stage 2 and both
stages").

### The cross-vehicle decomposition

The matched-payload attribution above compares two runs on one vehicle, where the ideal
rocket-equation delta-v of the vehicle at P_ref, D_id, is the same on both sides and
cancels. An offloaded vehicle and the full-load pad differ in D_id by the whole delta-v
the removed propellant was worth, so the attribution would leave that as its residual and
call the pair `bug_suspect`. The decomposition keeps each vehicle's own D_id instead
([docs/physics.md](../physics.md), "Cross-vehicle decomposition"):

    D_id(pad) - D_id(case) = release speed + final speed + gravity + drag + steering
                             + back-pressure + pre-flight + fairing + margin   (+ residual)

Each term is in m/s, positive when it lets the case fly P_ref on less ideal delta-v: the
release speed is the head start, the loss terms are the pad's loss minus the case's, the
pre-flight term is the propellant the pad burns on its hold-down, and the margin term is
about 0 for two runs at their boundaries. The summary prints each term in m/s and, in
brackets, in kg of the offload (a proportional split). As with the attribution, **only the
sum of gravity and steering is read as physics**: the two trade against each other as
gamma\* moves.

The residual is exactly the difference of the two runs' own closure and loss-identity
residuals. It must stay below `checks.closure_tol_mps` (1e-5 m/s as shipped), together with
both runs' own residuals and a check that each trace starts at its vehicle's liftoff mass;
the status is then `explained`, else `bug_suspect`, which blocks findings. A pass certifies
the bookkeeping (the masses, each vehicle's D_id and the loss integrals booked
consistently), not the physics of either run.

The shipped headline case, silo_cold_s1 against the pad, both at P_ref (run summary.md):

| Term | m/s | kg of the 41,262.9 kg | share |
|---|---|---|---|
| release speed | +76.707 | +13,869.9 | 33.6% |
| gravity + steering | +124.710 | +22,549.5 | 54.6% |
| pre-flight (the pad's 2.7 t burned on the hold-down) | +14.408 | +2,605.2 | 6.3% |
| back-pressure | +13.280 | +2,401.2 | 5.8% |
| drag | -0.877 | -158.5 | -0.4% |
| fairing, final speed, margin | about 0 | about -4 | 0.0% |
| D_id(pad) - D_id(case) | 228.204 | 41,262.9 | 100% |

Residual 4.5e-12 m/s: `explained`. The pre-flight term is a baseline convention (the pad is
clamped from ignition at -2 s), not the push.

### The screening rule for offload rows

CLAUDE.md's rule (a result that beats the README's ideal screening estimate must be
explained by its loss breakdown, or it is treated as a bug) applies to offload rows in this
form:

- **The yardstick** is the ideal-screening offload: the stage-1 propellant the case's
  release speed is worth at fixed losses, on the pad's vehicle at P_ref, with the
  screening's loss-averaged stage-1 Isp. The table prints it, the ratio "stage-1 offload /
  screening offload" and whether the offload beats it.
- **It applies to a stage-1 offload with a head start only.** The ratio and the beat flag
  are `n/a` for a case that also removes stage-2 propellant (a stage-2 kilogram frees about
  twice the ideal delta-v of a stage-1 one) and for a run released from rest. For a fixed
  case the beat flag only compares the imposed x with the yardstick.
- **An offload beyond the yardstick is explained when, and only when, its decomposition
  closes.** One that does not is `bug_suspect` and blocks the finding. Offload rows never
  enter the "Unexplained beats" list; their explanation is the decomposition.

The shipped headline removes 41.26 t against a 14.98 t yardstick (ratio 2.755), and the
decomposition above explains it: more than half of it is lower gravity and steering loss
(the lighter stack reaches MECO 12.8 s sooner), a third the release speed, and 6% the pad's
hold-down convention.

### The pad control

The pad control runs the same solve on the pad itself, at its own P\*.

- **For stage 1 it is a consistency test of the solver.** The pad should find nothing to
  remove. An `ok` control passes when 0 <= x_pad <= bound, with bound =
  `search.final_payload_xtol_kg` / abs(dm_res/dx), the residual slope taken from the
  control's own logged evaluations.
- **`no_offload` by grams is a resolution effect, not a failure.** The full-load pad's P\*
  is found on the feasible side to within 0.05 kg of residual propellant, so flying exactly
  P_ref it can miss by grams. A `no_offload` control with -`final_payload_xtol_kg` <
  m_res(0) < 0 passes and is printed as "a resolution effect: the full-load pad misses
  P_ref by grams of residual propellant at the feasible-side convention's resolution,
  within final_payload_xtol_kg; not a failure". The shipped control reads x_pad = 0,
  m_res(0) = -0.0016 kg, bound 1.62 kg: consistency test pass.
- **A failing stage-1 control blocks findings.** The Checks section then gets its own line:
  "Findings are blocked until these are investigated (a stage-1 pad control failed its
  consistency test of the solver, ...)".
- **For stage 2 and both there is no test.** The control is the amount the pad itself can
  leave out, and those cases are quoted net of it. In the shipped run the stage-2 control
  removed 513.6 kg and carries a flag of its own (`search_vs_final_payload`), which the
  note reads as an uncertainty of about 0.07 to 0.21 t in the net stage-2 figure.

### The paired pad

The cross-vehicle gravity term mixes two effects: the head start, and a lighter stack whose
higher thrust-to-weight spends less time against gravity. A case with `paired_pad: true`
also flies the pad with the same propellant change and no push (`<case>__<baseline>`). The
table prints its P\*, its shortfall against P_ref, and the assisted vehicle's P\* (its
verification search) minus the paired pad's: a comparison on one vehicle, attributed by the
matched-payload attribution at the paired pad's P\* and checked like a variant (a
`bug_suspect` blocks findings).

In the shipped run the pad offloaded by the same 41.26 t carries 24,652.4 kg, **1,402.0 kg
short of P_ref**: without the push the same tanks carry 1.4 t less, so the push is needed to
carry this offload. How much of the offload the lighter stack accounts for depends on the
reading, and the note gives both:

- **Read as the pre-registration worded it**, the shortfall is set against the offload:
  1,402 kg against 41.26 t is 3.4%, small, so its branch fires and reads that **most of the
  offload is the lighter stack's thrust-to-weight**, not the head start. The note reports
  that verdict and argues that it compares kilograms of payload with kilograms of
  propellant.
- **In ideal delta-v, a reading chosen after the run**, 28 to 29% of the 228.2 m/s the
  offload removes is the lighter stack's own thrust-to-weight gain and 71 to 72% the push at
  equal stack mass (the pad's hold-down convention included). The range is bracketed by the
  two orders of the two-step split.

### Loads beside an offload

- **Max-Q** of each offloaded run is printed beside the pad's, unthrottled (an upper bound,
  and no max-Q limit constrains the solve). A lighter stack climbs faster through the dense
  air: the shipped headline flies 38,438.5 Pa, **3.35% above the pad's** 37,191.4 Pa, where
  the full-load silo flew 16.0% below it. The max-Q benefit of the full-load silo is spent
  once the push is cashed in as propellant.
- **q-alpha** is not in the offload table; it is in `metrics.json` (`offload.runs`). The
  headline's is 226.9 Pa rad at the kick, 3.04 times the pad's 74.7 (no angle-of-attack
  aerodynamics; the kick costs nothing it would in flight).
- **On the track** the stack still feels 4.0 g (20.81 MN at the interface for the headline),
  and no structural mass is charged for it except in the assumed penalty rows.

### The energy rows

The ratio of the combustion heat of the removed fuel to the push's electricity is labelled
"not an efficiency claim", and it is not one: it sets unlike quantities side by side. It
leaves out producing the removed LOX, extracting, refining and delivering the fuel,
generation, transmission and storage losses, and the facility beyond the drive; the
electricity is metered at the drive, at an assumed 50% drive efficiency. The shipped
headline reads about 128 (12.4 t of RP-1 removed with 28.9 t of LOX, against 1.16 MWh), and
5.65 with the assumed +8.1 t of stage-1 strengthening. It says nothing about cost, and
nothing about what share of a rocket's fuel energy a ground drive could replace.

### What the shipped offload run says

From [RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md) (preliminary, pre-registered;
README, "Fuel replaced at fixed payload (SP1)"). At the pad's payload (26,054.4 kg to
200 km, 28.5 degrees) the 3 g, 100 m cold-start silo lets the gate vehicle leave out
**41.26 t of stage-1 propellant: 10.04% of the stage-1 load, 7.96% of the total**, 2.76
times the ideal-screening offload, the beat explained by the decomposition. The numbers
that sit beside it:

- **The vehicle model.** The gate vehicle calibrates +14.3% high. On the README-loads fork,
  which calibrates inside the band, the same case removes 36.01 t (9.10% of stage 1). Read
  it as 9 to 10% of stage 1 across the two vehicle forks of this model, not as a Falcon 9
  figure.
- **Structure.** No structural mass is charged for the 4 g full-stack push. An assumed +2,
  +4 and +8.1 t of stage-1 dry mass leave 32.29, 22.88 and 1.98 t; about 8.5 t
  (extrapolated) leaves nothing.
- **What the push itself does.** The pad flown with the same offload falls 1.4 t short of
  the payload; read as the pre-registration worded it, most of the offload is the lighter
  stack's thrust-to-weight, while the delta-v reading chosen after the run gives the lighter
  stack 28 to 29% ([The paired pad](#the-paired-pad)). 6% is the pad's hold-down convention.
- **Loads.** Max-Q 3.4% above the pad's; q-alpha 3.0 times the pad's.
- **Stage 2.** The stage-2 case failed its independent verification; stage-2 and
  both-stage figures are a property of the vehicle model, never the headline.
- **Energy.** The heat-to-electricity ratio of about 128 is not an efficiency claim.
- **Method.** Sweep-optimized guidance (not optimal control), no throttle, a free kick, a
  prescribed drive with no force or power limit, partly filled tanks of an unchanged
  vehicle. Under the ±10% sensitivity arms the offload stays between 38.67 and 44.46 t.

## The caveats, and why each matters

These apply to every 2-D number so far (README, "Caveats that apply to every 2-D number").

| Caveat | Why it matters |
|---|---|
| No structural mass is charged for the 4 g full-stack push | At about 184 kg of payload per tonne of stage-1 dry mass, about 8.1 t of silo-only strengthening would cancel the whole silo_cold gain (a linear extrapolation, not a sized structure). In offload terms each assumed tonne takes 4.5 to 5.1 t off the 41.26 t, and about 8.5 t (extrapolated) takes all of it. This decides whether the headline survives (README roadmap Phase 3, backlog B-004) |
| The gate vehicle calibrates +14.3% high (accepted, documented) | Every 2-D number inherits the miss. On a vehicle calibrated to 22.8 t the gain would be expected near 1.3 t (derived by proportion, not run); the offload's README-loads bridge gives 9.10% of stage 1 against 10.04% |
| Guidance is sweep-optimized, not optimal control | The trajectory part of the gain (34% of silo_cold's) is the part a better pad ascent could change, in either direction (README roadmap Phase 5) |
| Nothing is throttled; the kick is free | Max-Q and q-alpha are upper bounds; q-alpha at the kick is above the pad's in every silo variant |
| Prescribed acceleration, unbounded drive force | A hot start cannot add exit speed; carriage mass and drive efficiency move only energy and power |
| Massless carriage (except `silo_sled_22t`), no air drag in the vented shaft | Energy, power and interface force are slightly low |
| Planar point mass with a generic C_D(Mach) table | Not Falcon 9 aerodynamics; 3-D dynamics come in phases SP3 to SP6 |
| The pad's hold-down burn is part of the baseline | 130.7 kg gross (83.1 kg net) of the gain; against a pad lit at release the gain is +1,415.8 kg |

## Results that go against the hypothesis

The hypothesis is that any ground-supplied velocity, however small, cuts propellant or
raises payload. The findings so far include results that undercut it, and the summaries
show them as plainly as the others (README, "Against the hypothesis"):

- A full hot start does not pay: silo_hot_full is 10.2 kg behind the cold start (a tie).
- The startup after release is expensive: the cold start gives back 327.1 kg (34.74 m/s)
  against an instant start, 2.37 times the 1-D formula.
- Small pushes gain little from the push itself: at 0.5 g over 50 m (22 m/s) the trajectory
  term is negative, and about 83 kg net (35%) of that point's +240 kg is the pad's hold-down
  burn.
- q-alpha at the kick gets worse in every silo variant.
- A failed ignition has no abort: the stack falls back to the mouth at 76.6 m/s.
- The facility is sized by power: a 1.725 GW peak for a 2.6 s push.

The fuel-offload note adds these ([RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md),
"What goes against the hypothesis"):

- Structural mass can cancel the offload: each assumed tonne of stage-1 strengthening takes
  4.5 to 5.1 t off, and about 8.5 t (extrapolated) takes all of it.
- Part of the headline is not the push: 6% is the pad's hold-down convention. Read as the
  pre-registration worded it, most of the offload is the lighter stack's thrust-to-weight
  (the pad with the same offload falls only 1.4 t short); in the delta-v reading chosen
  after the run, 28 to 29% is the lighter stack's own thrust-to-weight gain, which the push
  makes usable but does not produce.
- The max-Q benefit disappears: 16% below the pad's at full load becomes 3.35% above it at
  the offload, and up to 12.5% above at a 300 m stroke.
- Diminishing returns with depth: the offload per m/s falls from 622 to 429 kg from 25 to
  300 m; at a fixed exit speed a deeper silo gives the same offload (by construction in
  this model) for up to 71% more electricity and a longer facility.
- The earliest hot start loses: lighting at the shaft floor removes 2.6 t less than
  lighting 75 m deep, under a prescribed drive where thrust on the track buys no speed; a
  force-limited drive (Phase 3) may change that ordering.
- A late start is expensive: each second of delay after release costs 4.8 to 5.3 t.
- The figure depends on the vehicle masses (9.10% of stage 1 on the README-loads fork).

Next: [10. Validation](10-validation.md)
