# launch-assist-sim user manual

launch-assist-sim is a research simulator for ground-powered launch assist. A rocket gets
its first tens of metres per second from electrically powered ground hardware (so far, a
vertical maglev silo), and the simulator measures what that is worth in payload,
propellant, losses, loads, energy and peak power. Every result is a difference against the
same rocket launched from a pad.

This manual explains how to install it, run the shipped experiments, write your own
experiment and vehicle files, and read what comes out. The research itself (the question,
the prior art, the hand numbers and the results so far) is in the top-level
[README](../../README.md). The findings are in [docs/findings/](../findings/README.md).

> **License.** All rights reserved. The repository is public so that it can be read; no
> license is granted. You may not copy, modify, share or use any part of it, commercially
> or otherwise, without written permission. It is not open source. See
> [LICENSE](../../LICENSE).

## Status in one paragraph

Phases 0 to 2 are done: a 1-D vertical model, the constant-acceleration vertical silo push,
and a 2-D ascent to orbit over a rotating Earth with drag, guidance and a payload search.
Phase SP1 added launch settings (silo depth with exit speed; where the thrust ramp starts,
by time, depth, speed or height, the height by a closed form or by an altitude event in
flight), a solver for propellant offload at fixed payload with its `offload:` experiment
block, and a pre-registered finding:
[RQ1-fuel-offload-2d](../findings/RQ1-fuel-offload-2d.md) (preliminary). At the pad's payload
and orbit, the 3 g, 100 m cold-start silo lets the gate vehicle leave out **41.26 t of
stage-1 propellant, 10.04% of the stage-1 load and 7.96% of the total**. That is a
difference between runs of a vehicle model that calibrates +14.3% high, not a Falcon 9
figure (on the README-loads fork, which calibrates inside the band, it is 36.01 t, 9.10%),
sweep-optimized and unthrottled, and before any structural mass is charged for the 4 g push
(an assumed +8.1 t of stage-1 dry mass leaves 1.98 t; about 8.5 t, extrapolated, cancels
it). Just as important: read as the pre-registration worded it, most of the offload is the
lighter stack's thrust-to-weight (the pad flown with the same offload falls only 1.4 t short
of the payload), while a delta-v reading chosen after the run gives the lighter stack 28 to
29%; the offloaded run's max-Q is 3.4% above the pad's; the stage-2 case failed its
verification; and the heat-to-electricity ratio of about 128 is not an efficiency claim
([9. Reading results](09-reading-results.md#what-the-shipped-offload-run-says)). Phase SP2
(closed 2026-10-07) added the local app, `launchsim app`: a launch form built from the
committed experiments, a results panel, a run browser and the 2-D launch scene, which draws
the pad and the silo side by side from a run's recorded time series, with an MP4 export;
and `launchsim scene`, the same scene as a standalone page
([7b. The local app and the launch scene](07b-app.md)). Every run launched from the app is
exploratory and never a finding; the app's launch of the `silo_cold_s1` preset reproduces
SP1's 41.26 t within 0.002 kg (the same configuration on the same model: a reproduction,
not new evidence). The program board is [docs/phases/README.md](../phases/README.md).

## Contents

| Chapter | What it covers |
|---|---|
| [1. Install](01-install.md) | Python, uv, the virtual environment, ffmpeg, checking the install |
| [2. Quick start](02-quick-start.md) | Run a shipped experiment, open the summary, replay a 2-D run, watch it as a launch scene, open the app |
| [3. Concepts](03-concepts.md) | The phases of a run, pad baseline against silo, payload capacity, residual propellant, the loss budget |
| [4. Experiment files](04-experiments.md) | Every block of an experiment YAML: shared blocks, baseline, variants, sweeps, sensitivity, bounds, cases, the merge rules |
| [5. Assist and ignition](05-assist-and-ignition.md) | The `none` and `constant_accel` assist models, the carriage, braking, efficiency, impingement; ignition timing, startup shapes, failed ignition, ramp start by depth, speed or height (closed form or altitude event) |
| [5b. Propellant offload at fixed payload](05b-offload.md) | The `offload:` block: every key, the runs it writes, pad controls, paired pads, sensitivity arms, sweeps that solve an offload at every point, the summary section, replaying an offloaded run, `--no-offload` and `--no-sensitivity` |
| [6. Vehicle files](06-vehicles.md) | Stages, engines, sourced quantities, aerodynamics, fairing, screening; why calibrated files are forked, never edited |
| [7. Commands](07-commands.md) | `run`, `sweep`, `animate`, `replay`, `scene`, `app`: every flag, default and output location; the one output-path rule |
| [7b. The local app and the launch scene](07b-app.md) | `launchsim app`: starting and stopping it, the form group by group, the presets, the checks and refusals, Launch, the progress card, the results panel, the run browser, the scene and its keys, the MP4 export, the exploratory regime, the security notes; `launchsim scene`, the standalone page |
| [8. Outputs](08-outputs.md) | The results directory, `summary.md`, `metrics.json` (with the offload record), `resolved_config.yaml`, `sweep_index.csv` (with the offload columns), `timeseries.csv` and `events.csv` columns with units, plots; an app launch's directory, the scene page and the MP4 |
| [9. Reading results](09-reading-results.md) | The loss identity, payload capacity, the screening yardstick and the screening-beat rule, statuses and flags; reading an offload result (the cross-vehicle decomposition, the pad control, the paired pad); the caveats |
| [10. Validation](10-validation.md) | Validation first: the analytic tests, calibration against validation, running the tests |
| [11. Troubleshooting](11-troubleshooting.md) | Windows notes, common errors and what they mean |
| [12. FAQ and glossary](12-faq-glossary.md) | Short answers and the terms used everywhere else |

## How to read it

- **You want to see something run:** chapters 1 and 2, then chapter 7 for the flags and
  7b for the app and the launch scene.
- **You want to set up your own study:** chapters 3, 4 and 5, then 5b for a
  propellant-offload study and 6 if you need another vehicle.
- **You have a results directory and want to know what it says:** chapters 8 and 9.
- **You want to know whether to trust the numbers:** chapters 9 and 10, and the
  "Caveats (read first)" section of each note in [docs/findings/](../findings/README.md).

Chapters link to each other where a term is defined elsewhere. The
[glossary](12-faq-glossary.md#glossary) collects the terms in one place.

## Conventions in this manual

- Commands are written for `uv run` from the repository root, as in
  [CLAUDE.md](../../CLAUDE.md). `uv run launchsim ...` works too: the package installs a
  `launchsim` command.
- Code is SI throughout. Degrees, kilometres, kilonewtons, tonnes and g appear only in YAML
  files and plot labels, and the key name says which (`_deg`, `_km`, `_kN`, `_t`, `_g`).
- Every example says which shipped file it comes from. Snippets that are not in a shipped
  file are marked as written for this manual; each of them was resolved (or refused, where
  the text says so) by the simulator's own config loader before it was put here.
- Numbers about results come from the README, the findings notes or a results summary, with
  their caveats beside them.

## What this manual was checked against

The manual was first checked against the code at commit `e4f36ee` (branch `main`,
2026-10-02). It was brought up to date for what SP1 delivered after that (the ramp start by
an altitude event and the `offload:` block, with its outputs, sweep columns, replay role and
command-line switches) at commit `cfd9059` (2026-10-04): every command, flag,
configuration key, default, metric and column named in those additions was checked there
against `src/launchsim/cli.py`, `config.py`, `results_io.py`, `summary.py`, `compare.py`,
`offload.py`, `metrics_planar.py`, `plots.py` and `replay.py`, the shipped files under
`experiments/` and `configs/vehicles/`, and the recorded results of the pre-registered SP1
runs. It was brought up to date for what SP2 delivered (the app, the scene, the MP4 export,
the one output-path rule and the display files) at commit `705025f` (2026-10-07): every
command, option, field, preset, refusal and output named in those additions was checked
against `src/launchsim/cli.py`, `app.py`, `appform.py`, `scene.py`, `display.py`,
`video.py`, `run_data.py`, the templates under `src/launchsim/templates/`, the files under
`configs/display/` and the recorded demo in `docs/demos/SP2/`. Where the code and the docs
move on, the code wins; [docs/physics.md](../physics.md) is the source of truth for the
equations.

Features that are planned but not in that code are marked with the phase that brings them
(for example README roadmap Phase 3 for the force-limited drives).
