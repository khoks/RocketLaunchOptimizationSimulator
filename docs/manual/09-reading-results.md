# 9. Reading results

[Manual contents](README.md) · Previous: [8. Outputs](08-outputs.md) · Next: [10. Validation](10-validation.md)

A summary is full of numbers. This chapter says which to look at first, what the checks
mean, and which caveats travel with every result. The worked numbers come from the shipped
2-D record `results/silo_screening_2d/20260930T175743Z` and the findings notes; all of them
are preliminary.

## Read in this order

1. **The summary lines at the end of the Checks section.** They say whether any run or
   comparison is `bug_suspect`, which runs had no screening check, which verdicts change
   within gamma\* +/- h, and which beats of the screening estimate no loss breakdown
   explains. In the shipped 2-D record the first of them reads "No run and no comparison is
   bug_suspect." A `bug_suspect` blocks findings until it is investigated.
2. **The Flags section.** Anything the run wants you to know (a tensile interface, a
   braking drive, an ignored setting, a search flag). "(none)" is the normal case.
3. **The status rows** of the variant table: run status, search status, run checks,
   screening status.
4. **The figure of merit**: P\* and dP\* in 2-D, burnout speed in 1-D, with the yardstick
   rows beneath it.
5. **The losses, loads, energy and power**, and the sensitivity table before quoting any
   number.
6. **The Assumptions section.** Each line names the runs it applies to.

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
| `guidance_failed` | 2-D | A fixed-guidance run whose guidance failed (for example a kick timeout) |
| `bug_suspect` | 2-D | A per-run check failed (closure, loss identity or insertion eccentricity). The trajectory's own status is in `trace_status` |

The search status is `ok`, `no_orbit`, `search_failed`, `none (fixed guidance)` or a skip
reason such as `skipped (end: impact (ignition stage1 fails))`.

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

## The caveats, and why each matters

These apply to every 2-D number so far (README, "Caveats that apply to every 2-D number").

| Caveat | Why it matters |
|---|---|
| No structural mass is charged for the 4 g full-stack push | At about 184 kg of payload per tonne of stage-1 dry mass, about 8.1 t of silo-only strengthening would cancel the whole silo_cold gain (a linear extrapolation, not a sized structure). This decides whether the headline survives (README roadmap Phase 3, backlog B-004) |
| The gate vehicle calibrates +14.3% high (accepted, documented) | Every 2-D number inherits the miss. On a vehicle calibrated to 22.8 t the gain would be expected near 1.3 t (derived by proportion, not run) |
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

The question SP1 is answering, the share of propellant replaced at a fixed payload, has no
finding yet. A labelled probe found about 10% of stage-1 propellant (41.1 t, 7.9% of the total
propellant load) before any structural mass is charged; it is a probe, not a finding. At that
offload the silo run's max-Q (38.4 kPa) is above the full pad's (37.2 kPa), and the gate
vehicle calibrates +14.3% high ([handoff, section 3](../handoff/archive/2026-09-30-phases-0-2.md#3-the-headline-question-and-a-first-answer-probe-not-a-finding)).

Next: [10. Validation](10-validation.md)
