# 5b. Propellant offload at fixed payload

[Manual contents](README.md) · Previous: [5. Assist and ignition](05-assist-and-ignition.md) · Next: [6. Vehicle files](06-vehicles.md)

The `offload:` block of an experiment file asks the SP1 question: with the payload and
the orbit held fixed, how much propellant can the assisted rocket leave out? This chapter
lists every key of the block as `src/launchsim/config.py` defines it, the runs it writes,
how sweeps use it, what the summary reports, how to replay an offloaded run, and the two
command-line switches that skip parts of it. The worked example throughout is the shipped
`experiments/silo_offload_2d.yaml`. How to read what comes out is in
[9. Reading results](09-reading-results.md#reading-an-offload-result).

## What it computes

- **The offload x** [kg] is propellant removed from a full load along a mode: `stage1`
  (all from the first stage), `stage2` (all from the second) or `both` (the same fraction
  of each stage's load). The tanks are partly filled: every dry mass (tank structure
  included), engine, the payload, the fairing and the aerodynamics stay as they are, and
  each stage keeps its mixture ratio. It is an under-filled vehicle, not one redesigned
  around a smaller load.
- **The reference payload P_ref** is the payload capacity P\* of the full-load pad
  baseline, on the same vehicle and orbit with the shared search budget
  ([3. Concepts](03-concepts.md#figures-of-merit)).
- **A solved case** finds x\*, the largest evaluated offload whose residual propellant at
  insertion is still >= 0 when the assisted run flies P_ref, with gamma\* re-optimised
  (the same feasible-side convention as P\*). Its recorded run flies exactly P_ref and
  ends inserted with 0 <= m_res < `search.final_payload_xtol_kg` (0.05 kg in the shipped
  files). The solve ends `ok` (x\* found), `no_offload` (the vehicle cannot carry P_ref
  even with full tanks, so x\* = 0) or `search_failed`.
- **A fixed case** imposes an offload instead and reports its own P\* against P_ref.
- **Verification.** An `ok` solve is checked by an independent payload search of the
  vehicle offloaded by x\*. It must return P_ref within `checks.search_final_flag_rel` x
  P_ref (1e-4 x P_ref, 2.6 kg on the gate vehicle); otherwise the case carries the flag
  `offload_verify_mismatch` and x\* is a lower bound. A search in x whose residuals change
  sign more than once raises `offload_nonmonotone`. Every offload flag starts with
  `offload:`.

So an offload row compares **different vehicles carrying the same payload to the same
orbit**, not one vehicle carrying two payloads. The block changes no run of the
experiment: it is not a shared block, and the search budget id stays the same.

The block needs `dynamics: planar_2d` and `search.figure_of_merit: payload` (the solve and
its verification are payload searches).

## The worked example

From `experiments/silo_offload_2d.yaml` (an excerpt: most comments left out, five of its
eleven cases shown, and the three long `source:` strings of the energy block shortened here
to "..."; the file gives them in full):

```yaml
sensitivity:
  of: []
  params: {vehicle.stages.stage1.dry_mass_t: 0.10, vehicle.stages.stage1.engine.isp_vac_s: 0.10,
           vehicle.aero.cd_scale: 0.10, assist.drive_efficiency: 0.10}
offload:
  reference: pad                           # P_ref = the full-load pad's payload capacity P*
  pad_control: true                        # every solve mode (stage1, stage2, both) also solved on the pad
  sensitivity_of: [silo_cold_s1]           # the headline, re-solved at each +/-10% arm
  cases:
    - {name: silo_cold_s1, of: silo_cold, solve: stage1, paired_pad: true}
    - {name: silo_cold_s2, of: silo_cold, solve: stage2}
    - {name: silo_cold_s1_s2pre2t, of: silo_cold, solve: stage1, stage2_offload_t: 2}
    - {name: silo_cold_s1_dry+8.1t, of: silo_cold, solve: stage1, stage1_dry_mass_added_t: 8.1}
    - {name: silo_cold_fix5pct, of: silo_cold, fixed: {stage1_fraction: 0.05}}
  energy:
    fuel_mass_t:                           # RP-1 of each full load; the LOX is the rest of the stage's propellant
      stage1: {value: 123.5, source: "..."}
      stage2: {value: 32.3, source: "..."}
    heating_value_MJ_per_kg: {value: 43.03, source: "..."}
```

`silo_cold` is a variant of the file: the 3 g net, 100 m vertical silo of
`silo_screening_2d.yaml`, stage 1 lit 0.5 s after release. The file is pre-registered:
committed before any run, with what each case is for and how its result is read fixed in
`docs/phases/inputs/2026-10-03-sp1-preregistration.md`.

## The block's keys

| Key | Default | Rule | Meaning |
|---|---|---|---|
| `reference` | required | the baseline's name | Whose payload capacity is P_ref. Anything other than the baseline is refused |
| `cases` | required | at least one; names unique | The cases (next table) |
| `pad_control` | false | required by a `stage2` or `both` solve | Also solve every distinct solve mode of the cases once on the baseline at P_ref (the pad control) |
| <code>sensitivity_<wbr>of</code> | `[]` | case names, each once; stage-1 solves and fixed cases only; needs a sensitivity block | Re-solve these cases under every parameter in the sensitivity block's `params`, plus and minus |
| `energy` | none | optional | Inputs of the energy comparison (below) |

(In the code the YAML key `reference` is read into the field `reference_run`, because
`reference` is also a key of the ignition time family; you write `reference`.)

### A case

| Key | Default | Rule | Meaning |
|---|---|---|---|
| `name` | required | a run name (a directory name, [4](04-experiments.md#top-level-keys)); unique among the experiment's runs, bounds, cases and offload runs | The name of the case's recorded run |
| `of` | required | a variant; never the baseline | The assisted run the case starts from. The baseline's own offload is the pad control |
| `solve` | none | exactly one of `solve` and `fixed` | `stage1`, `stage2` or `both`: the mode solved for x\* |
| `fixed` | none | exactly one of `solve` and `fixed` | An imposed offload (next table) |
| `stage2_offload_t` | none | > 0 [t]; a stage-1 case only | Propellant taken from stage 2 before the case: the frontier point of a both-stage offload |
| `stage1_dry_mass_added_t` | none | > 0 [t] | An assumed structural penalty added to stage 1's dry mass, on the assisted run only: a penalty row, not a sized structure |
| `paired_pad` | false | refused together with `stage1_dry_mass_added_t` | Also fly the pad with the same propellant change and no push, and compare it with the case on one vehicle (the paired pad) |

### `fixed`

Exactly one key, holding a number. A key given as `null` counts as given and is refused.

| Key | Rule | Mode | Meaning |
|---|---|---|---|
| `stage1_t` | > 0 [t] | stage1 | Tonnes taken from stage 1 |
| `stage1_fraction` | in (0, 1) | stage1 | Fraction of stage 1's load |
| `stage2_t` | > 0 [t] | stage2 | Tonnes taken from stage 2 |
| `stage2_fraction` | in (0, 1) | stage2 | Fraction of stage 2's load |
| `both_fraction` | in (0, 1) | both | The same fraction of each stage's load |

A mass at or beyond a stage's load is refused when the experiment is resolved against its
vehicle (`... an offload beyond the load; a stage keeps some propellant`). Every changed
mass is written into the run's vehicle dict as `{value, assumed: true, note}`, the note
naming the change and the vehicle's own value, so an offloaded vehicle never looks
sourced.

### `energy`

| Key | Rule | Meaning |
|---|---|---|
| `fuel_mass_t` | one entry per stage of the vehicle, keyed by stage name, and no other key; each > 0 and no more than that stage's propellant | The fuel (RP-1) mass [t] of each stage's full load. The oxidiser (LOX) is the rest of the stage's propellant |
| `heating_value_MJ_per_kg` | > 0 | The fuel's lower heating value [MJ/kg] |

Both are sourced quantities, written like vehicle-file numbers: `{value, source}` or
`{value, assumed: true, note}` ([6. Vehicle files](06-vehicles.md#sourced-quantities)). They
live in the experiment because the vehicle file holds no fuel split and a calibrated
vehicle file is never edited. The removed propellant of each stage is split at that stage's
mixture ratio, and the combustion heat of the removed fuel is set beside the push's
electrical energy. The block is optional: `experiments/silo_offload_2d_readme.yaml` has
none, because its vehicle has no sourced fuel split.

### Rules that catch common mistakes

| Rule | Refusal you will see (shortened) |
|---|---|
| Planar only | `offload: a planar_2d block (declare dynamics: planar_2d)` |
| Payload search | `offload: the offload solve and its verification are payload searches, so the block needs search.figure_of_merit payload ...` |
| The reference is the baseline | `offload reference 'x' must be the baseline 'pad': the reference payload is the full-load pad's P*` |
| A case is built on a variant | `offload case 'x': of 'pad' is the baseline; the baseline's own offload is the pad control (pad_control: true)` |
| One way per case | `offload case 'x': give exactly one of solve (a mode to solve) or fixed (an imposed offload)` |
| Stage 2 and both are netted | `offload case 'x': a stage2 solve is quoted net of the pad control ..., so the block needs pad_control: true` |
| Arms need parameters | `offload sensitivity_of re-solves its cases under the experiment's sensitivity params: declare the sensitivity block` |
| No paired pad on a penalty row | `offload case 'x': paired_pad compares the case with the pad on one vehicle ...; give the penalty row without paired_pad` |
| Names stay unique | `run name 'x' is used twice (runs, bounds, cases and offload runs)` |

## The runs it writes

| Run (directory) name | What it is |
|---|---|
| `<case>` | The case's recorded run: the vehicle offloaded by x\* flying P_ref (a solved case), or the variant with the imposed offload at its own P\* (a fixed case) |
| `<case>__<baseline>` | The paired pad of a case with `paired_pad: true` |
| `<baseline>__offload_<mode>` | The pad control of a mode, with `pad_control: true` |

The shipped run writes, beside `pad` and its three variants, `pad__offload_stage1`,
`pad__offload_stage2`, `pad__offload_both`, the eleven case runs and `silo_cold_s1__pad`.
Each has the usual `timeseries.csv` and `events.csv`
([8. Outputs](08-outputs.md#a-run-directory)), and every offloaded run carries the
assumption line about partly filled tanks; a penalty row adds one saying its dry mass is
an assumed penalty.

**Pad controls.** A pad control runs the same solve on the pad. For `stage1` it is a
consistency test of the solver: the pad should find nothing to remove at its own P\*. For
`stage2` and `both` it is the amount the pad itself can leave out, and those cases are
quoted net of it, as a property of the vehicle model rather than of the assist. Only the
modes of cases that ran get a control. [9. Reading results](09-reading-results.md#the-pad-control)
explains the verdicts.

**Sensitivity arms.** Each case in `sensitivity_of` is rebuilt on its variant under each
parameter of `sensitivity.params` at plus and minus its fraction, and solved against the
pad under the same perturbation, whose P\* is the arm's P_ref. A `vehicle.` parameter
perturbs the pad and the assisted run alike; a run parameter (such as
`assist.drive_efficiency`) perturbs the assisted run only, since a pad has no drive. Arms
carry no independent verification search. An arm whose trajectory equals another run's
reuses that solve (a drive-efficiency arm moves only the electricity). Arms write no run
directory; they are named `<case>__<param>__+0.1` (or `-0.1`) in the summary and the
Checks section. `sensitivity.of` may be empty, as in the shipped file, when only the arms
are wanted: the payload Sensitivity section then says that its parameters perturb the
offload arms.

## Sweeps that name offload cases

A sweep may list cases of the block under its own `offload` key. At every point each case
is rebuilt on the point's run (in place of the case's `of`), solved at the point's
baseline P\* (the experiment's baseline, or a paired sweep's paired baseline) and
verified. From `experiments/silo_offload_2d.yaml`:

```yaml
sweeps:
  - {of: silo_cold, axes: {assist.stroke_m: [25, 50, 100, 200, 300]}, offload: [silo_cold_s1]}
  - {of: silo_cold, axes: {ignition.stage1.at_height_m: [10, 40, 100, 200],
                           ignition.stage1.height_method: [event]}, offload: [silo_cold_s1]}
```

The first solves the headline case at five silo depths, the second at four ramp-start
heights reached by the altitude event
([5](05-assist-and-ignition.md#ramp-start-by-depth-speed-or-height)).

- A sweep names stage-1 solves and fixed cases only: a `stage2` or `both` solve is quoted
  net of a pad control, which a sweep does not solve.
- A sweep of the baseline cannot name offload cases (the baseline's own offload is the
  pad control).
- A sweep point gets no paired pad, no pad control and no arms, and writes no offload run
  directory. Its results are columns of `sweep_index.csv`, written `<case>.<column>`
  ([8. Outputs](08-outputs.md#sweep_indexcsv)); those columns are the point's only record
  of its solve on disk. The sweep summary's Checks section lists each point's
  decomposition and its offload flags under `sweep_<n>/run_<nnnn>__<case>`.
- `launchsim run` never solves a sweep's offload cases, and `launchsim sweep` never solves
  the block's own cases.

## What the summary reports

`summary.md` of a `run` gains the section **"Propellant saved at fixed payload"**, right
after the variants table. In order:

1. **The basis line** with P_ref: different vehicles, the same payload and the same orbit.
   Then the sensitivity basis line when the block has arms.
2. **The caveats**, which travel with every number below: the vehicle's calibration (on
   the gate vehicle, +14.3% high: "read every offload as a difference between runs of the
   vehicle model, not as a Falcon 9 figure"), sweep-optimized and unthrottled guidance, no
   structural mass for the push except the assumed penalty rows, the prescribed drive,
   max-Q against the pad's, the partly filled tanks, and stage 1 as the only headline.
3. **The cases table**, one column per case. It leads with the **quoted offload** and its
   basis: a stage-1 solve's x\*, gross (the headline); a `stage2` or `both` solve's x\*
   net of the pad control, labelled a property of the vehicle model; a fixed case's
   imposed offload. Then the gross propellant removed per stage and its share of the
   stage-1, stage-2 and total loads, the assumed dry mass added, the payload flown and its
   difference from P_ref, the verification (P\* of the offloaded vehicle, P\* - P_ref, the
   tolerance, passed), the pad control's offload and the net value, liftoff mass, MECO,
   max-Q (unthrottled) and peak felt g in flight beside the pad's, the push (release speed,
   felt g on the track, interface force, facility length), the ideal-screening offload at
   the release speed and the ratio to it, the decomposition status and residual, the paired
   pad (its P\*, its shortfall against P_ref, the assisted P\* minus its P\* and the
   screening status of that comparison) and the number of flags. With an `energy` block
   the table adds RP-1 and LOX removed, the combustion heat of the removed RP-1 (MJ and
   kWh), the electrical energy of the push and their ratio, labelled "not an efficiency
   claim".
4. **The energy note**, saying what the ratio leaves out: producing the removed LOX,
   extracting, refining and delivering the fuel, generation, transmission and storage
   losses, and the facility beyond the drive.
5. **Decomposition**: the cross-vehicle decomposition of each case against the pad, term
   by term in m/s and kg ([9](09-reading-results.md#the-cross-vehicle-decomposition)).
6. **Pad controls**: a table (x_pad, m_res and the delta-v margin at x_pad, the residual
   slope, the stage-1 bound, the consistency verdict, the verification) and one line per
   control in words.
7. **Sensitivity**: one row per arm (parameter, change, whether the pad was perturbed,
   the arm's P_ref, status, offload and its change against the nominal case, the share of
   stage 1, decomposition, ratio, whether the solve was reused).

The offload runs also join the Flags, Assumptions and Checks sections. The Checks section
adds the heading "Offload checks" with the stage-1 pad control's verdict and one line per
case and arm (decomposition status, residual, ratio).

The console prints the block too. From the shipped run (first lines):

```text
  offload at P_ref 26054.4 kg:
    silo_cold_s1: ok, 41.2629 t removed (10.0421 % of stage 1, 7.95967 % of the total), decomposition explained
    silo_cold_s2: ok, 31.3907 t net of the pad control, a property of the vehicle model; gross 31.9043 t removed (0 % of stage 1, 6.15437 % of the total), decomposition explained
    silo_cold_fix5pct: ok, 20.545 t removed (5 % of stage 1, 3.96316 % of the total), P* - P_ref +783.163 kg, decomposition explained
    pad control stage1: no_offload, x_pad 0 kg, consistency pass
    pad control stage2: ok, x_pad 513.556 kg
    sensitivity: 8 arms
```

These lines carry none of the caveats; the summary section does. Read
[9](09-reading-results.md#reading-an-offload-result) before quoting any of them.

## Replaying an offloaded run

`launchsim replay` and `launchsim animate` choose the baseline and up to three variants by
default, so offload runs are never in the default selection. Name them with `--runs` (at
most four runs per page):

```text
uv run python -m launchsim replay results/silo_offload_2d/<timestamp> --runs pad silo_cold silo_cold_s1 silo_cold_s1__pad
```

The page labels each offload run "(offload)" and describes it from metrics.json: how much
propellant it carries less (solved or imposed, as a share of the stage-1 and total loads)
and the payload it flies against the pad's full load at P_ref, or that it is a paired pad
or a pad control. A caveat on the page says that what these runs measure is propellant
saved at the same payload and orbit, not a payload change, and points to the summary
section. That holds for a solved case's recorded run and for a pad control, which fly
P_ref. It does not hold for a paired pad or a fixed case, which fly their own payload
capacity, so their payload column is a payload change: the shipped paired pad
`silo_cold_s1__pad` carries 24,652.4 kg, 1,402.0 kg short of P_ref. The page also rounds
the offload to one decimal (41.3 t, 10.0% and 8.0% for the headline); the summary gives it
in full. The site's copies of the shipped pages correct both. `animate` draws the same runs
when named and labels them from the same offload record: its legend gives a solved case's
or pad control's payload as "flies P_ref" with the propellant it carries less, and a paired
pad's or fixed case's own P\* with its difference from P_ref. The stage-1 pad control,
whose recorded run ends grams of propellant short of orbit by construction, is labelled a
pad control (a resolution effect, not a failure) and its run table reads "~inserted". On a
fresh clone the CSVs are not in git: run the experiment first and point the command at the
new directory.

## Skipping parts of it

| Command and flag | Effect |
|---|---|
| `run --no-offload` | Skips the block. The summary section and metrics.json's `offload` record say `(offload block declared but skipped: --no-offload)`; no offload run is written |
| `run --no-sensitivity` | Skips the sensitivity cases and the block's arms; the section notes `(offload sensitivity arms skipped: --no-sensitivity)` |
| `run --variant NAME` | Runs only the cases built on that variant (and the pad controls of their modes, and their arms); every other case is listed as `not run: its variant did not run (launchsim run --variant)` |
| `sweep --no-offload` | Skips the offload cases the sweeps name; `sweep_index.csv` then has no offload columns |

A baseline without a payload capacity solves nothing: the record says
`reference_failed` and why. The offload pass is slow, because every case runs nested
payload searches: the pre-registered `run` of `silo_offload_2d.yaml` took 14.1 min and its
`sweep` 20.9 min on the author's machine, started together
([docs/physics.md](../physics.md), "SP1 research notes"). While you iterate, use
`--no-offload` or `--no-sensitivity`.

## What the shipped run found

The pre-registered runs of this file and its README-loads bridge are written up in
[RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md) (preliminary). On the gate
vehicle, at the pad's payload (26,054.4 kg to 200 km), the cold-start silo case
`silo_cold_s1` removes 41.26 t of stage-1 propellant, 10.04% of the stage-1 load (7.96% of
the total), sweep-optimized and unthrottled, before any structural mass is charged. It is a
difference between runs of a vehicle model that calibrates +14.3% high, not a Falcon 9
figure (the README-loads bridge, inside the band, gives 36.01 t, 9.10%). An assumed +8.1 t
of stage-1 dry mass leaves 1.98 t, and about 8.5 t (extrapolated) cancels it. Read as the
pre-registration worded it, most of the offload is the lighter stack's thrust-to-weight
(the pad flown with the same offload falls only 1.4 t short of the payload), while a
delta-v reading chosen after the run gives the lighter stack 28 to 29%. The offloaded run's
max-Q is 3.4% above the pad's, and the stage-2 case failed its independent verification.
[9. Reading results](09-reading-results.md#what-the-shipped-offload-run-says) gives the
rest of the caveats that sit beside it.

Next: [6. Vehicle files](06-vehicles.md)
