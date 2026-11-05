# SP7 demo: the offload with the push's structure charged, and the linear motor (planar model)

The recorded demo of phase SP7 (docs/phases/SP7-structural-mass-push-load.md, section 9). It
shows the structural model at work: the same 100 m silo as SP1, with a first-order structure
sized for the push and charged to the assisted run at every offload the solve tries, and
the force- and power-limited linear motor on that silo. The demo repeats the phase's four
recorded commands from one clean commit and compares every metrics.json leaf, and the
sweep's indexes and baseline series, with the recorded directories. The finding the
recorded runs feed is
[docs/findings/RQ1-structural-2d.md](../../findings/RQ1-structural-2d.md). Read its caveats
before quoting any number here. Every result number below is quoted from that note and
rests on the recorded directories it cites, not on the demo runs (see
[What the demo is not](#what-the-demo-is-not)); the timings, test counts and leaf counts are
the demo's own.

## What it shows

- **The structural headline** ([console-run-structure.txt](console-run-structure.txt)). At
  the pad's payload (P_ref = 26,054.4 kg to a 200 km circular orbit, 28.5 deg, due east), with
  a first-order structure sized for the offloaded stack at central coefficients, the
  cold-start silo (100 m stroke at 3 g net, exit at 76.7 m/s, stage 1 lit 0.5 s after release
  with a 2 s ramp) leaves out **11.42 t of stage-1 propellant: 27.7% of SP1's uncharged
  41.26 t, 2.78% of the stage-1 load** (case `silo_cold_s1_st`, sweep-optimized,
  unthrottled). The pre-registered reading "cancels most" fired (the sizing-only estimate
  before the run was 11.1 t). The modelled 6,305.2 kg of structure costs 29.84 t of offload. These caveats go with that number:
  - It is a first-order station sizing, not a structural design: closed forms per station,
    no FEM, no joints beyond the non-optimum factors, no lateral loads, no fatigue.
  - It uses the structure file's central coefficients, an assumed real-drive rise time of
    0.5 s that the constant-acceleration trajectory does not fly (it flies an instant step),
    zero existing margin and the pad's own unthrottled flight as the envelope. The instant
    release is flagged, not sized: the model's single-mode treatment puts the stage-1 LOX
    column's bottom at -896 kPa absolute, and takes stage 2's LOX column through the same
    separation at the pad's own MECO. Nothing models propellant settling for the ignition
    0.5 s after that release, a risk no number here measures.
  - The physics band runs from no offload (243.7 m/s of delta-v short of P_ref at x = 0,
    payload deficit -2,080 kg) to 28.57 t (23.68 t before its plausibility scaling), the
    outer envelope from no offload (1,021.5 m/s short, -7,804 kg) to 31.12 t, and the step
    push the constant-acceleration drive actually flies leaves no offload (125.2 m/s short,
    -1,087 kg). The -2,080 and -1,087 kg are upper bounds on the payload change. Band ends are the extremes a
    screened search found, not bounds. Under the ±10% arms the headline stays between 8.55
    and 15.07 t.
  - It comes from the gate vehicle model, which calibrates +14.3% high against the published
    22,800 kg (docs/findings/CAL-f9-leo-2d.md): a difference between two runs of a model, not
    a figure for a real Falcon 9. On the README-loads fork, which calibrates inside the band
    (+8.33%), the central structure sized for the fork leaves 9.16 t of that fork's 36.01 t,
    25.5% ([console-run-readme.txt](console-run-readme.txt)).
  - Guidance is sweep-optimized, not optimal control; nothing is throttled; the kick is free
    (q-alpha at the kick 140.9 against the pad's 74.7 Pa rad); the tanks are partly filled.
- **The axes** ([console-sweep-structure.txt](console-sweep-structure.txt)). With the central
  structure charged, strokes of 25 and 50 m at 3 g (38.35 and 54.24 m/s) leave no offload
  (60.2 and 18.3 m/s short; payload deficit not flown), and 200 and 300 m (108.48 and
  132.86 m/s) leave 31.62 and 44.73 t, the 300 m value an upper bound, with full-load runs
  kicking at 7.7 and 17.3 times the pad's q-alpha. At a fixed 76.71 m/s exit, 50 m ends at no
  offload (190.0 m/s short; payload deficit not flown) and 200 and 300 m keep 26.69 and
  32.03 t. A sweep point has no flown band and no ±10% arm.
- **The drive cases** ([console-run-drive.txt](console-run-drive.txt)). At the central
  structure only, with no physics band and no ±10% arm, all nine linear-motor drives cancel
  most of the offload: 2.48 t (a stop taper, whose benefit the model credits only in its
  flags) to 18.27 t (an acceleration-law hot start, which repeats run A's
  `silo_hot_ramp_s1_st` by construction, favoured by the unmodelled exhaust in the shaft and
  with its release flag, a risk no number here measures). On the same 100 m silo the two
  drives that exit faster than silo_cold at the solved offload keep less: the force-limited
  hot start 4.07 t less at 12.53 m/s faster (the rise formula overcharges its n_peak, which
  costs of order 1 t of offload on a rough estimate, not measured), the force sized for the
  full load 82 kg less at 0.44 m/s faster. The motor is capped by force and power only, with an assumed efficiency
  of 0.5.
- **The pages.** [pad-vs-structural-offload.html](pad-vs-structural-offload.html) replays
  the pad beside `silo_cold_s1_st`: both reach the same 200 km orbit with the same
  26,054.4 kg, and the offloaded run starts at 567,239 kg against the pad's 572,354 kg (the
  pad then burns 2.7 t on the clamp).
  [pad-vs-structural-offload-scene-page.html](pad-vs-structural-offload-scene-page.html) draws
  the same pair as the 2-D launch scene, with the display-only reconstructions it names on
  the page. [constant-accel-vs-linear-motor.html](constant-accel-vs-linear-motor.html)
  replays `silo_cold` beside `lm_cmd`, two full-load variants at their own payload capacity,
  no structure charged: a linear motor flying the ramped plateau reaches the same 76.7 m/s
  and the same P\* to within the search's resolution, by construction: the command is set to
  reach that speed at the track end, and a cold start's flight after release does not see
  the push, so the match is not evidence that a real drive behaves so. Each page carries the
  caveats of its runs in its own "Read before quoting" list. All three are made from the demo
  directories (their Data and meta lines read git 6cf0fd2d05f7, clean), so that the record
  stays one set of runs; the gallery's copies are made from the recorded run A. They are the
  commands' own output, without the site's frame and its three drawing patches of the replay
  template (site/build.py), so they keep the template's known defects: on
  constant-accel-vs-linear-motor.html "silo floor, 100 m down" overprints the time axis, and
  pad-vs-structural-offload.html scrolls 7 px sideways on a 375 px phone.

## What the demo is not

- It is no finding and it adds no number. The demo runs repeat recorded commands, they are
  never cited in a finding, and they replace none of the directories the note cites. The
  comparison below is a check.
- It is not a reproduction on another machine or with other library versions.
- It does not show a physical result about a Falcon 9, a structural design or a facility
  design. Its pages are model replays.
- It does not close the phase: SP7's closing gate comes after this record.

## The demo runs against the recorded directories

The demo ran the note's four commands from the clean commit 6cf0fd2 (`dirty=false` before each
command, in [times.txt](times.txt); each run's git record reads `dirty: false`). The
comparison is [deep-compare.txt](deep-compare.txt), every leaf of metrics.json, and
[compare-with-recorded.txt](compare-with-recorded.txt), the offload cases, the payload cases
and the sweep's files. The tolerance is 0.002 kg; no number differs at all.

| command | recorded directory | demo directory | what was compared | result |
|---|---|---|---|---|
| `run` silo_structure_2d (run A) | results/silo_structure_2d/20261016T171513Z | results/silo_structure_2d/20261104T095619Z | 16,391 numeric leaves of metrics.json | none differs; 24 offload cases and 4 payload cases, same statuses |
| `sweep` silo_structure_2d | results/silo_structure_2d/20261019T172327Z | results/silo_structure_2d/20261104T095624Z | both sweep_index.csv files and the baseline's series | largest numeric difference 0, no text cell differs |
| `run` silo_structure_2d_readme (run C) | results/silo_structure_2d_readme/20261016T171529Z | results/silo_structure_2d_readme/20261104T095630Z | 2,161 numeric leaves | none differs |
| `run` silo_drive_2d (run B) | results/silo_drive_2d/20261103T231946Z | results/silo_drive_2d/20261104T095635Z | 14,967 numeric leaves | none differs; 20 offload cases, same statuses |

The only text leaves that differ are `/git/hash` and `/timestamp_utc`, no key is added or
missing, and every x\*, status and verification of each case is therefore the recorded
directory's. The demo ran the code of 6cf0fd2, so the code added after each recorded
commit (the linear motor after runs A and C, the wording steps after all three) moved no
number of these runs. It shows nothing about a change made after 6cf0fd2.

## The fast suite: three results, in order

The demo's first command is the fast suite. It did not pass, and it is reported here as it
ran.

| when | commit | command | result | capture |
|---|---|---|---|---|
| before the runs, 2026-11-04 09:50:27Z to 09:56:10Z | 6cf0fd2 | `uv run pytest -q -m "not slow"` | exit 1: 1 failed, 2,216 passed, 53 deselected, 338.26 s (`test_wrapper_encoder_is_killed_with_its_child_and_the_session_fails`) | [console-fast-suite.txt](console-fast-suite.txt) |
| after the runs, 10:33:22Z to 10:40:23Z | 6cf0fd2 | the same | exit 1: 2 failed, 2,215 passed, 53 deselected, 415.03 s (that test and `test_one_connection_carries_an_exports_requests`) | [console-fast-suite-rerun.txt](console-fast-suite-rerun.txt) |
| after step S7d, 2026-11-05 07:45:19Z to 07:49:49Z | cf6d1db, clean | the same | exit 0: 2,217 passed, 54 deselected, 267.05 s | [console-fast-suite-after-s7d.txt](console-fast-suite-after-s7d.txt) |

All three failures are in tests/test_video.py, with other projects' processes loading the
machine: the tests' short wall-clock limits fired before a fake encoder had started (KI-091,
TODO.md). Those processes were not this session's to stop, so step S7d (cd14968, trackers
cf6d1db; deviation 57) made the fast tier hold under that load. It changed tests and test-map
rows of docs/physics.md only: nothing under src/, configs/ or experiments/, and neither
pyproject.toml nor uv.lock, changed between 6cf0fd2 and cf6d1db. So the runs' numbers are
unaffected, and the three runs were not repeated after it. The suite's count after S7d is
2,271: 2,217 fast and 54 slow. Two known issues stay open, and neither touches a model
number: KI-092, a real defect on the video routes of src/launchsim/app.py, and KI-093, two
test coverage gaps S7d disclosed.

`uv run pytest -q tests/test_structure.py`, the demo's second command, passed: 44 tests
([console-structure-tests.txt](console-structure-tests.txt)).

## Files

| file | what it is |
|---|---|
| [console-fast-suite.txt](console-fast-suite.txt) | The fast suite at 6cf0fd2, before the runs (exit 1) |
| [console-structure-tests.txt](console-structure-tests.txt) | tests/test_structure.py |
| [console-run-structure.txt](console-run-structure.txt) | `run experiments/silo_structure_2d.yaml` |
| [console-sweep-structure.txt](console-sweep-structure.txt) | `sweep experiments/silo_structure_2d.yaml` |
| [console-run-readme.txt](console-run-readme.txt) | `run experiments/silo_structure_2d_readme.yaml` |
| [console-run-drive.txt](console-run-drive.txt) | `run experiments/silo_drive_2d.yaml` |
| [console-fast-suite-rerun.txt](console-fast-suite-rerun.txt) | The fast suite at 6cf0fd2, after the runs (exit 1) |
| [console-fast-suite-after-s7d.txt](console-fast-suite-after-s7d.txt) | The fast suite at cf6d1db, after S7d (exit 0) |
| [times.txt](times.txt), [times-after-s7d.txt](times-after-s7d.txt) | Start and end stamps (UTC), HEAD and the dirty state of each command |
| [compare-with-recorded.txt](compare-with-recorded.txt), [deep-compare.txt](deep-compare.txt) | The comparison with the recorded directories |
| [pad-vs-structural-offload.html](pad-vs-structural-offload.html) | The replay page of `pad` and `silo_cold_s1_st` from the demo's run A |
| [pad-vs-structural-offload-scene-page.html](pad-vs-structural-offload-scene-page.html) | The 2-D scene page of the same pair |
| [constant-accel-vs-linear-motor.html](constant-accel-vs-linear-motor.html) | The replay page of `silo_cold` and `lm_cmd` from the demo's run B |

The console files are the captures as written. Three things were changed: each `results:`
line's absolute local path now reads as a repository-relative path with forward slashes,
local paths in the pytest failure reports read `<home>` and `<user>`, and line endings are LF.
Nothing else was changed or removed.

Reading the console lines:

- `silo_cold_s1_st_phys_hi: no_offload, ...` is a result, not a failure: the vehicle carrying
  its dm cannot carry P_ref even with full tanks.
- `structure payload case ...: ok, P* ... (P* - P_ref ...)` is a payload change at full load,
  never propellant saved; `structure_payload_unconverged` says its two passes had not
  settled, and the note quotes the residual estimate beside the number.
- `pad control stage1: no_offload, x_pad 0 kg, consistency pass` is the expected result.
- `lm_fixed_target: ... flags: release_speed_not_reached` is the variant's own run, a stack
  heavier than the full load that reaches the track end below its release speed. The part 2
  pre-registration expected it there, and it fires on neither of the variant's two cases.

## Commits

| commit | what |
|---|---|
| cbbd7bc | Pre-registration, part 1: experiments/silo_structure_2d.yaml, experiments/silo_structure_2d_readme.yaml and docs/phases/inputs/2026-10-15-SP7-preregistration.md, committed before any run |
| 74eb3c8 | Amendment 1: the sweep's no-offload record and the sweep's re-run |
| 1b5f9d4 (1b5f9d46d31c) | The clean commit of the recorded run A and run C |
| 2b343d7 | The commit of the sweep's re-run; its git record reads dirty (by the session's account from 13 untracked draft documents; deviation 45, the note's Provenance) |
| 331891d | Pre-registration, part 2: experiments/silo_drive_2d.yaml and docs/phases/inputs/2026-11-03-SP7-preregistration-part2.md |
| 642e11e (642e11e3851d) | The clean commit of the recorded run B |
| e5f64b3 | The findings note completed (step S7b) |
| 9fe125c | Step S7c: the program-level wording, the last code commit before the demo |
| 6cf0fd2 (6cf0fd2d05f7) | S7c's tracker commit: every demo command ran from it, clean |
| 6940273 | The four demo summaries committed |
| cd14968, cf6d1db | Step S7d and its trackers: the fast tier under load (tests and test-map rows only) |

The three pages were written in step S8 from the demo directories, after KI-082's rewording of
the display file's shaft note (the scene page embeds that note in its data block, which the
page does not show); nothing else about them depends on the working tree.

## Results directories

Only each directory's top-level summary.md is tracked in git. The metrics, time series and
plots stay on the machine that ran them.

| run | demo directory, its summary tracked | recorded directory the note cites |
|---|---|---|
| A | [results/silo_structure_2d/20261104T095619Z](../../../results/silo_structure_2d/20261104T095619Z/summary.md) | [results/silo_structure_2d/20261016T171513Z](../../../results/silo_structure_2d/20261016T171513Z/summary.md) |
| sweep | [results/silo_structure_2d/20261104T095624Z](../../../results/silo_structure_2d/20261104T095624Z/summary.md) | [results/silo_structure_2d/20261019T172327Z](../../../results/silo_structure_2d/20261019T172327Z/summary.md) |
| C | [results/silo_structure_2d_readme/20261104T095630Z](../../../results/silo_structure_2d_readme/20261104T095630Z/summary.md) | [results/silo_structure_2d_readme/20261016T171529Z](../../../results/silo_structure_2d_readme/20261016T171529Z/summary.md) |
| B | [results/silo_drive_2d/20261104T095635Z](../../../results/silo_drive_2d/20261104T095635Z/summary.md) | [results/silo_drive_2d/20261103T231946Z](../../../results/silo_drive_2d/20261103T231946Z/summary.md) |

## Exact commands

From the repository root at 6cf0fd2, clean tree (2026-11-04, UTC):

| command | start | end |
|---|---|---|
| `uv run pytest -q -m "not slow"` | 09:50:27Z | 09:56:10Z |
| `uv run pytest -q tests/test_structure.py` | 09:56:10Z | 09:56:15Z |
| `uv run python -m launchsim run experiments/silo_structure_2d.yaml` | 09:56:15Z | 10:32:27Z |
| `uv run python -m launchsim sweep experiments/silo_structure_2d.yaml` | 09:56:20Z | 10:18:25Z |
| `uv run python -m launchsim run experiments/silo_structure_2d_readme.yaml` | 09:56:25Z | 09:59:53Z |
| `uv run python -m launchsim run experiments/silo_drive_2d.yaml` | 09:56:30Z | 10:25:40Z |

The four commands started 5 s apart and ran at the same time, as step S7a started its three.
No number depends on the order: each command re-solves its own pad. Other projects'
processes were running on the machine, and from about 10:22Z several of their pytest runs.

The pages, in step S8:

    uv run python -m launchsim replay results/silo_structure_2d/20261104T095619Z --runs pad silo_cold_s1_st --out docs/demos/SP7/pad-vs-structural-offload.html
    uv run python -m launchsim scene results/silo_structure_2d/20261104T095619Z --runs pad silo_cold_s1_st --out docs/demos/SP7/pad-vs-structural-offload-scene-page.html
    uv run python -m launchsim replay results/silo_drive_2d/20261104T095635Z --runs silo_cold lm_cmd --out docs/demos/SP7/constant-accel-vs-linear-motor.html

They printed 166 KiB, 595 KiB and 167 KiB. The default page names end in `_replay.html` and
`_scene.html`, and `.gitignore` ignores those patterns at any depth, which is why the pages
here have hyphens.

## Look at

- The Structure subsection of the demo's run A summary: the central case, the physics band,
  the outer envelope, the penalty rows beside, the element split, the plausibility table, the
  flags, and the design-axis rows with their break-even note.
- The thickness figure of the central case, pad envelope against the push:
  [RQ1-structural-2d-silo_cold_s1_st_structure.png](../../findings/RQ1-structural-2d-silo_cold_s1_st_structure.png)
  (copied from the recorded run A).
- The exit-speed and depth sweeps with the structure charged:
  [the sweep summary](../../../results/silo_structure_2d/20261104T095624Z/summary.md) and
  [RQ1-structural-2d-derived_sweep1_exit_speed.png](../../findings/RQ1-structural-2d-derived_sweep1_exit_speed.png).
- The linear-motor runs: force against speed, the interface force, the release position and
  speed, the taper's cost: the Variants table of the demo's run B summary, and
  [RQ1-structural-2d-derived_drive_force_power.png](../../findings/RQ1-structural-2d-derived_drive_force_power.png).
- The note's headline sentence and its Caveats section.

The app (`launchsim app`) can show the same pair from the run browser. No launch was made
for this demo, and the app's form charges no modelled structure.

## Reproduce on a fresh clone

The results are not tracked, so the pages have no time series until you re-run the
experiments. Cloning and running need the copyright holder's written permission: see
[LICENSE](../../../LICENSE).

1. `git clone https://github.com/khoks/RocketLaunchOptimizationSimulator.git` and
   `git checkout 6cf0fd2` (or any later commit that leaves src/, experiments/, configs/,
   pyproject.toml and uv.lock as they are at 6cf0fd2 apart from configs/display's note).
2. `uv sync`
3. Run the four commands above. Each writes a new timestamped directory under results/ and
   never overwrites one. Compare its console output with the files here, and its summary.md
   with the tracked summaries above.
4. Point the page commands at the new directories.

Nobody has checked whether these runs reproduce on another machine or with other library
versions. uv.lock pins the Python dependencies.
