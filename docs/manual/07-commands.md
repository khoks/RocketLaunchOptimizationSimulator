# 7. Commands

[Manual contents](README.md) · Previous: [6. Vehicle files](06-vehicles.md) · Next: [8. Outputs](08-outputs.md)

`launchsim` has four commands. Run them from the repository root as
`uv run python -m launchsim <command> ...` (or `uv run launchsim <command> ...`).

```text
launchsim run     <experiment.yaml> [--results-root DIR] [--variant NAME] [--no-plots] [--no-sensitivity]
launchsim sweep   <experiment.yaml> [--results-root DIR] [--no-plots]
launchsim animate <run_dir> [--runs NAME [NAME ...]] [--out PATH] [--fps N] [--seconds S] [--width PX]
launchsim replay  <run_dir> [--runs NAME [NAME ...]] [--out PATH]
launchsim --version
```

`-h` or `--help` after any command prints its help.

## `run`

Flies the baseline and every variant of an experiment, the sensitivity cases of the runs
that flew, the bounds whose variants flew and (for a calibration file) the cases, then
writes one results directory.

| Argument | Default | Meaning |
|---|---|---|
| `experiment` | required | Path to an experiment YAML file |
| `--results-root DIR` | `<repo root>/results` | Root of the results tree. The repo root is the nearest folder above the experiment file with a `pyproject.toml`; without one, `./results` |
| `--variant NAME` | all variants | Fly only this variant, plus the baseline. Sensitivity cases run only for these two runs, a bound runs only if it names this variant, and calibration cases are skipped. An unknown name is an error that lists the variants |
| `--no-plots` | plots on | Skip the PNG plots |
| `--no-sensitivity` | sensitivity on | Skip the sensitivity cases |

Output: a new directory `<results root>/<experiment>/<UTC timestamp>/`
([8. Outputs](08-outputs.md#a-run-directory)). The console prints its path and one line per
run: the status and any flags; a 2-D run adds P\* [kg], gamma\* [deg] and max-Q [Pa]. A
calibration run also prints whether its inputs were committed, and a run with sensitivity
cases prints how many ran.

```text
results: <repo>\results\silo_screening_2d\<timestamp>
  pad (baseline): inserted (P* 26054.4 kg, gamma* 22.9891 deg, max-Q 37191.4 Pa)
  silo_cold: inserted (P* 27553.2 kg, gamma* 21.6465 deg, max-Q 31237.6 Pa)
```

(From `run experiments/silo_screening_2d.yaml --variant silo_cold --no-sensitivity`; the
numbers match the shipped record. Caveats: [2. Quick start](02-quick-start.md#step-3-a-2-d-run-to-orbit-minutes).)

How long: the whole 1-D file, with its sensitivity cases, takes seconds. A searched 2-D run
takes about 7-10 s for the pad and 25-28 s for the lag variants (README), and each
comparison adds matched-payload evaluations, so a full 2-D file with its sensitivity cases
takes many minutes.

## `sweep`

Flies the baseline once and every point of every sweep the file declares.

| Argument | Default | Meaning |
|---|---|---|
| `experiment` | required | Path to an experiment YAML file |
| `--results-root DIR` | `<repo root>/results` | As for `run` |
| `--no-plots` | plots on | Skip the PNG plots (a sweep writes plots for every point, so this saves time and disk) |

`sweep` has no `--variant` and no `--no-sensitivity`: sweep points never run sensitivity
cases. Output: a new directory with `baseline/`, `sweep_<n>/run_<nnnn>/` per point,
`sweep_<n>/sweep_index.csv` per sweep and a top-level `summary.md`
([8. Outputs](08-outputs.md#a-sweep-directory)). The console prints one line per sweep, for
example `sweep_1: silo_cold x 12 points over assist.net_accel_g, assist.stroke_m: inserted`
(the last part lists the statuses that occurred). A file without sweeps prints
`no sweeps declared`.

## `animate`

Replays the 2-D runs of one results directory as a video. It only reads the directory and
never writes into it.

| Argument | Default | Meaning |
|---|---|---|
| `run_dir` | required | One results directory of a `planar_2d` `run`: `results/<experiment>/<timestamp>` |
| `--runs NAME [NAME ...]` | the baseline plus up to three variants, in summary order | Runs to show, at most four. Bound re-runs can be named too |
| `--out PATH` | `./<experiment>_<timestamp>_animation.mp4`, or `.gif` when ffmpeg is missing | Output file. The extension picks the format: `.mp4` (ffmpeg) or `.gif` (Pillow) |
| `--fps N` | 30 | Frames per second. A `.gif` stores frame delays in whole 10 ms steps, so it plays at 1000 / delay fps (12 fps plays at 12.5) and at most 50 fps; the command prints the real rate |
| `--seconds S` | 20.0 | Length of the video [s] |
| `--width PX` | 1280 | Frame width in pixels: even, at least 320. The frame is 16:9 |

The default output goes to the current directory; if the current directory is inside the
run's results tree, the file goes next to that tree instead. An explicit `--out` inside the
results tree is refused, and its folder must exist.

The video shows the first 30 s of flight slowly, so the push and liftoff are visible, and
the rest of the ascent much faster, with the current playback speed in the corner
(README). Rendering takes a while: about 4 minutes for the 600-frame 1280 px MP4 and under a
minute for the 640 px GIF on a laptop (README). The console prints
`rendering <runs>: <n> frames at <fps>, <w>x<h> px ...` and then `animation: <path>`.

`vertical_1d` runs are refused: they have no downrange or flight-path angle to draw.

## `replay`

Writes one self-contained interactive HTML page of the 2-D runs of a results directory:
the trajectory, a launch close-up with the shaft below ground, live telemetry, strip charts
of speed, felt g and dynamic pressure, the headline metrics against the baseline, and the
caveats that apply to the selected runs. The page replays the recorded time series; nothing
is re-simulated.

| Argument | Default | Meaning |
|---|---|---|
| `run_dir` | required | One results directory of a `planar_2d` `run` |
| `--runs NAME [NAME ...]` | the baseline plus up to three variants, in summary order | At most four. Experiment runs, bound re-runs (compared with their paired baseline) and calibration cases (compared with nothing) can be named |
| `--out PATH` | `./<experiment>_<timestamp>_replay.html` | Output `.html` file |

The output may not lie inside the run's results tree or inside any folder named `results`;
if the current directory is inside one, the default goes next to the outermost such folder.
The console prints `replay: <path> (<size> KiB)`.

## Exit codes and messages

| Code | When |
|---|---|
| 0 | Success (and `--version`) |
| 1 | A configuration or file-system error: one `error: ...` line, no traceback, and no results directory |
| 2 | A usage error (no command, an unknown option): argparse's usage text |

Anything else (a bug in the simulator) keeps its Python traceback. If a run fails after its
results directory was created, the directory gets a `FAILED.txt` with the traceback and no
`summary.md`, so a partial directory is never mistaken for a good one.

Console output is ASCII only, so it prints on a cp1252 Windows console; characters outside
ASCII (in a path, say) are shown as backslash escapes. The files themselves are UTF-8.

## The commands in CLAUDE.md

These are the project's own command list, kept in [CLAUDE.md](../../CLAUDE.md):

| Task | Command |
|---|---|
| Set up | `uv sync` (fallback: `python -m venv .venv && pip install -e ".[dev]"`) |
| Fast tests | `uv run pytest -q -m "not slow"` |
| All tests | `uv run pytest -q` |
| Lint and format | `uv run ruff check .` then `uv run ruff format .` |
| One run | `uv run python -m launchsim run experiments/<name>.yaml` |
| Sweep | `uv run python -m launchsim sweep experiments/<name>.yaml` |
| Animate a 2-D run | `uv run python -m launchsim animate results/<experiment>/<timestamp> [--runs NAME ...] [--out PATH]` |
| Replay page | `uv run python -m launchsim replay results/<experiment>/<timestamp> [--runs NAME ...] [--out PATH]` |

The `&&` in the pip fallback does not work in Windows PowerShell 5.1; run the two parts
separately ([11. Troubleshooting](11-troubleshooting.md#windows)).

Next: [8. Outputs](08-outputs.md)
