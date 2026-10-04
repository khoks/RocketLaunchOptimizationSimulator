# SP1 demo: propellant saved at fixed payload (planar model)

The recorded demo of phase SP1 (docs/phases/SP1-fuel-offload-planar.md, section 9). It
shows the `offload:` block at work: the same rocket model flown from the pad with full
tanks, and flown out of a vertical silo with less stage-1 propellant. Both carry the same
payload to the same orbit, and the question is how much stage-1 propellant the silo run
can leave out. The finding these runs feed is
[docs/findings/RQ1-fuel-offload-2d.md](../../findings/RQ1-fuel-offload-2d.md). Read its
caveats before quoting any number here.

## What it shows

- **The offload block** ([offload-block.md](offload-block.md)). At the pad's payload
  (P_ref = 26,054.4 kg to a 200 km circular orbit, 28.5 deg, due east), the cold-start
  silo (100 m stroke at 3 g net, exit at 76.7 m/s, stage 1 lit 0.5 s after release with
  a 2 s ramp) lets the vehicle model leave out **41.26 t of stage-1 propellant: 10.04%
  of the stage-1 load, 7.96% of the total** (case `silo_cold_s1`, sweep-optimized,
  unthrottled). The pad's own stage-1 control finds nothing to remove, and an
  independent payload search on the offloaded vehicle returns P_ref within 0.01 kg.
  These caveats go with that number:
  - It comes from the gate vehicle model, which calibrates +14.3% high against the
    published 22,800 kg (docs/findings/CAL-f9-leo-2d.md). It is a difference between two
    runs of a model, not a figure for a real Falcon 9. On the README-loads fork, which
    calibrates inside the band (+8.3%), the same case gives 36.01 t (9.10% of its stage-1 load)
    ([console-bridge.txt](console-bridge.txt)).
  - It charges no structural mass for the 4 g push of the fully fuelled stack. Adding an
    assumed +2, +4 and +8.1 t of stage-1 dry mass leaves 32.29, 22.88 and 1.98 t. About
    8.5 t (extrapolated) leaves nothing. These rows are assumptions, not a sized
    structure.
  - Part of it is the lighter stack, not the push. Flown from the pad with the same
    41.26 t removed, the vehicle falls only 1.40 t short of P_ref (the paired pad
    `silo_cold_s1__pad`). Read as the pre-registration worded it, that shortfall, 3.4%
    of the 41.26 t offload, means most of the offload is the lighter stack's
    thrust-to-weight. The findings note reports that verdict and points out that it
    compares payload kilograms with propellant kilograms. A delta-v reading, chosen
    after the run, gives the lighter stack 28-29% of the saved ideal delta-v. Both
    readings are in the note.
  - The offloaded run's max-Q is 3.4% above the pad's (38,438.5 against 37,191.4 Pa,
    unthrottled upper bounds). The full-load silo run flew 16% below it.
  - The stage-2 case (`silo_cold_s2`) failed its independent verification: its search
    returned P* 15.36 kg above P_ref against a 2.6 kg tolerance, and the case carries 4
    flags. Its figure is a flagged lower bound and a property of the vehicle model.
    Stage 1 is the only headline.
  - The heat / electricity column (about 128 for the headline) compares unlike
    quantities. The block says so: it is not an efficiency claim, and it leaves out LOX
    production, fuel supply, grid losses and the facility.
- **The replay page** ([pad_vs_offloaded_silo.html](pad_vs_offloaded_silo.html), with a
  screenshot in [pad_vs_offloaded_silo.png](pad_vs_offloaded_silo.png)). The full-load
  pad (`pad`) and the offloaded silo run (`silo_cold_s1`, the headline case's recorded
  run) fly side by side. Both reach the same 200 km circular orbit with the same
  26,054 kg payload. The offloaded run lifts off 41.26 t lighter (531.1 against
  572.4 t) and reaches MECO 12.8 s sooner. The page carries the caveats of the run in its
  "Read before quoting these numbers" box, with one stale sentence: the drive caveat ends
  "Each of these favours the assisted runs." Under the prescribed drive the massless
  carriage and the missing shaft drag do not raise the payload or the offload; they bias
  only the drive energy, peak power and interface force low (README, "What can eat the
  gain", Silo air; [RQ3-silo-screening-2d](../../findings/RQ3-silo-screening-2d.md)), while
  the free pitch kick does favour the silo run. The page also rounds the offload to 41.3 t,
  10.0% and 8.0% (41.26 t, 10.04% and 7.96% in the summary). The file here is kept as
  `replay` wrote it; the site's copy (site/examples/pad-vs-silo-offload.html, through the
  text fixes in site/build.py) corrects both. The screenshot shows the stale sentence.

## Files

| file | what it is |
|---|---|
| [console-run.txt](console-run.txt) | Console output of the `run` command (step 9) |
| [console-sweep.txt](console-sweep.txt) | Console output of the `sweep` command (step 9) |
| [console-bridge.txt](console-bridge.txt) | Console output of the bridge `run` on the README-loads fork (step 9): the robustness row against the calibration miss |
| [offload-block.md](offload-block.md) | Lines 98 to 226 of results/silo_offload_2d/20261003T112934Z/summary.md: the section "Propellant saved at fixed payload" with its Decomposition, Pad controls and Sensitivity subsections, copied unchanged under a one-line source comment |
| [pad_vs_offloaded_silo.html](pad_vs_offloaded_silo.html) | The interactive replay page of `pad` and `silo_cold_s1`. It is self-contained apart from Google Fonts |
| [pad_vs_offloaded_silo.png](pad_vs_offloaded_silo.png) | Full-page screenshot of the replay page, served on 127.0.0.1 (see "The screenshot") |

The console files are the console logs of the step-9 runs as written. Two things were
changed: each first line's absolute local path now reads as a repository-relative path
with forward slashes, and line endings are LF. Nothing else was changed or removed.

Reading the console lines:

- `silo_cold_s2: ok, ...` reports the status of the solve. The case's independent
  verification failed (offload-block.md: "passed False", and the Flags section of the
  run's summary.md), so its figure is a flagged lower bound.
- `silo_cold_s1_s2pre2t: ok, 42.7685 t removed` is the total, including the 2 t taken
  from stage 2 first. Its stage-1 offload is 40.7685 t (offload-block.md, "quoted
  offload").
- `pad control stage1: no_offload, x_pad 0 kg, consistency pass` is the expected result.
  The full-load pad misses P_ref by grams of residual propellant (-0.0016 kg), a
  resolution effect within the solver's tolerance, so the solver's consistency test
  passes.
- `silo_cold_fix5pct` and `silo_cold_fix10pct` are fixed cases. Their figure is the extra
  payload at an imposed offload (+783.2 and +6.8 kg), not a solved offload.

## Commits

| commit | what |
|---|---|
| c2a4cf0 | Pre-registration: experiments/silo_offload_2d.yaml, experiments/silo_offload_2d_readme.yaml and docs/phases/inputs/2026-10-03-sp1-preregistration.md, committed before any run |
| d336933 | Amendment 1, before any run: reporting code only. No case, budget, criterion or reading changed |
| b3150c1 (b3150c1754ee) | The run commit. All three results directories record `git b3150c1754ee` with `dirty: false` |
| fd664a5 | The findings note docs/findings/RQ1-fuel-offload-2d.md, written from these runs |

The run, the sweep and the bridge were run in step 9 (2026-10-03) and were not re-run for
this demo. The replay page was written on 2026-10-04 at cfd9059, from the run directory
above. Nothing under src/, experiments/ or configs/, and neither pyproject.toml nor
uv.lock, changed between b3150c1 and cfd9059, so it is the page b3150c1 writes.

## Results directories

| command | results directory |
|---|---|
| `run experiments/silo_offload_2d.yaml` | results/silo_offload_2d/20261003T112934Z |
| `sweep experiments/silo_offload_2d.yaml` | results/silo_offload_2d/20261003T112949Z |
| `run experiments/silo_offload_2d_readme.yaml` (bridge) | results/silo_offload_2d_readme/20261003T112956Z |

Only each directory's top-level summary.md is tracked in git. The metrics, time series and
plots stay on the machine that ran them (results/ is gitignored apart from those
summaries).

## Exact commands

From the repository root at b3150c1, clean tree (step 9, 2026-10-03):

    uv run python -m launchsim run experiments/silo_offload_2d.yaml
    uv run python -m launchsim sweep experiments/silo_offload_2d.yaml
    uv run python -m launchsim run experiments/silo_offload_2d_readme.yaml

The three started within 22 s of each other (11:29:34, 11:29:49 and 11:29:56 UTC, the
directory names) and ran at the same time, not one after the other. Wall times under that
load: `run` 14.1 min, `sweep` 20.9 min, the bridge 2.1 min. The pre-registration's serial
estimates were 30-50, 39-64 and 3-6 min. No number depends on the order: each command
re-solves its own pad (docs/physics.md, "SP1 research notes").

The replay (2026-10-04):

    uv run python -m launchsim replay results/silo_offload_2d/20261003T112934Z --runs pad silo_cold_s1 --out docs/demos/SP1/pad_vs_offloaded_silo.html

It printed `replay: docs\demos\SP1\pad_vs_offloaded_silo.html (163 KiB)`.

The default replay file name ends in `_replay.html`, and `.gitignore` ignores that
pattern (with `*_animation.mp4` and `*_animation.gif`) at any depth. That is why the page
here has another name. `git check-ignore` reports none of the files in this folder as
ignored.

## The screenshot

The screenshot was taken from the page served on localhost, from this folder:

    uv run python -m http.server 8761 --bind 127.0.0.1

with the page at http://127.0.0.1:8761/pad_vs_offloaded_silo.html. It was taken in a
browser driven by Playwright, with a 1440 px wide viewport and the light colour scheme,
over the full page height. Playback was paused and the time slider moved to its end
(T+536.3 s after release). At that point both telemetry panels read "In orbit, 200 km
circular" (200.0 km, 7,363 m/s, 30.1 t), and the "What each run carries to orbit" table
shows 26,054 kg for both runs. The page follows the system colour scheme, so it also
opens in dark mode.

## Reproduce on a fresh clone

The results are not tracked, so the replay has no time series until you re-run the
experiments.

1. `git clone https://github.com/khoks/RocketLaunchOptimizationSimulator.git` and
   `git checkout b3150c1` (or any later commit that leaves src/, experiments/, configs/,
   pyproject.toml and uv.lock as they are at b3150c1).
2. `uv sync`
3. Re-run the two demo commands. Add the bridge if you want the robustness row:

       uv run python -m launchsim run experiments/silo_offload_2d.yaml
       uv run python -m launchsim sweep experiments/silo_offload_2d.yaml
       uv run python -m launchsim run experiments/silo_offload_2d_readme.yaml

   Each writes a new timestamped directory under results/ and never overwrites one.
   Compare its console output with the files here, and its summary.md with the tracked
   summaries above.
4. Replay the new run directory:

       uv run python -m launchsim replay results/silo_offload_2d/<new timestamp> --runs pad silo_cold_s1 --out pad_vs_offloaded_silo.html

Nobody has checked whether these runs reproduce on another machine or with other library
versions. uv.lock pins the Python dependencies.
