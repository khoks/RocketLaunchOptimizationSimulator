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
The current phase, SP1, adds launch settings (silo depth with exit speed, where the thrust
ramp starts) and a solver for the headline question: what share of the rocket's propellant
the silo push replaces at a fixed payload. **That question is not answered yet.** A
labelled probe found about 10% of stage-1 propellant (41.1 t, 7.9% of the total propellant
load) before any structural mass is charged; it is a probe, not a finding, and the answer is
being computed in SP1. The probe's other caveats: at that offload the silo run's max-Q
(38.4 kPa) is above the full pad's (37.2 kPa), and the gate vehicle calibrates +14.3% high
([handoff, section 3](../handoff/archive/2026-09-30-phases-0-2.md#3-the-headline-question-and-a-first-answer-probe-not-a-finding)). The program board is [docs/phases/README.md](../phases/README.md).

## Contents

| Chapter | What it covers |
|---|---|
| [1. Install](01-install.md) | Python, uv, the virtual environment, ffmpeg, checking the install |
| [2. Quick start](02-quick-start.md) | Run a shipped experiment, open the summary, replay a 2-D run |
| [3. Concepts](03-concepts.md) | The phases of a run, pad baseline against silo, payload capacity, residual propellant, the loss budget |
| [4. Experiment files](04-experiments.md) | Every block of an experiment YAML: shared blocks, baseline, variants, sweeps, sensitivity, bounds, cases, the merge rules |
| [5. Assist and ignition](05-assist-and-ignition.md) | The `none` and `constant_accel` assist models, the carriage, braking, efficiency, impingement; ignition timing, startup shapes, failed ignition, ramp-start triggers |
| [6. Vehicle files](06-vehicles.md) | Stages, engines, sourced quantities, aerodynamics, fairing, screening; why calibrated files are forked, never edited |
| [7. Commands](07-commands.md) | `run`, `sweep`, `animate`, `replay`: every flag, default and output location |
| [8. Outputs](08-outputs.md) | The results directory, `summary.md`, `metrics.json`, `timeseries.csv` and `events.csv` columns with units, plots |
| [9. Reading results](09-reading-results.md) | The loss identity, payload capacity, the screening yardstick and the screening-beat rule, statuses and flags, the caveats |
| [10. Validation](10-validation.md) | Validation first: the analytic tests, calibration against validation, running the tests |
| [11. Troubleshooting](11-troubleshooting.md) | Windows notes, common errors and what they mean |
| [12. FAQ and glossary](12-faq-glossary.md) | Short answers and the terms used everywhere else |

## How to read it

- **You want to see something run:** chapters 1 and 2, then chapter 7 for the flags.
- **You want to set up your own study:** chapters 3, 4 and 5, then 6 if you need another
  vehicle.
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

Every command, flag, configuration key, default, metric and column named here was checked
against the code at commit `e4f36ee` (branch `main`, 2026-10-02): `src/launchsim/cli.py`,
`config.py`, `metrics.py`, `metrics_planar.py`, `results_io.py`, `plots.py`, `replay.py`,
and the shipped files under `experiments/` and `configs/vehicles/`. Where the code and the
docs move on, the code wins; [docs/physics.md](../physics.md) is the source of truth for the
equations.

Features that are planned but not in that code are marked **coming in SP1** (or with the
phase that brings them).
