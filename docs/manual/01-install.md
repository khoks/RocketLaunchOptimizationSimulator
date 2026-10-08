# 1. Install

[Manual contents](README.md) · Next: [2. Quick start](02-quick-start.md)

> **Before you install.** The repository is public to read, but no license is granted
> ([LICENSE](../../LICENSE)). Cloning it and running the simulator on your own machine is a
> use the license does not cover, so ask the copyright holder for permission first (through
> GitHub, `@khoks`). This chapter is for the author and for anyone who has that permission.

## What you need

| Item | Version | Why |
|---|---|---|
| Python | 3.12 (`requires-python = ">=3.12"`; `.python-version` pins 3.12) | The simulator is pure Python |
| [uv](https://docs.astral.sh/uv/) | recent; the build backend is `uv_build` 0.12 | Creates the environment and runs every command. Optional: pip works too |
| Git | any | To get the repository, and because every results directory records the git hash |
| ffmpeg | any, on `PATH` | Optional. Only `launchsim animate` with an `.mp4` output and the app's Save-video export ([7b](07b-app.md#save-video-mp4)) need it; `.gif` works without it, and the app runs without it with the export switched off |
| Node.js | any, on `PATH` | Optional, for the tests only: the tests that check the inline scripts of the replay, scene and app pages run them through `node`; without it those tests are skipped and say so |

The package depends on numpy, scipy, pandas, matplotlib, pydantic, PyYAML and `ambiance`
(the ICAO standard atmosphere, used as the reference in the tests). The dev extra adds
pytest, ruff and Pillow (declared since SP2 because the tests import it directly; it arrives
with matplotlib in any case). The exact versions are in `pyproject.toml` and `uv.lock`.

## Get the repository

```text
git clone https://github.com/khoks/RocketLaunchOptimizationSimulator.git
cd RocketLaunchOptimizationSimulator
```

## Set up with uv (recommended)

```text
uv sync
```

That creates `.venv/` and installs the package in editable mode with its dev tools. You do
not need to activate the environment: prefix every command with `uv run`.

## Set up with pip (fallback)

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

The second line is for Windows PowerShell. In Git Bash use `source .venv/Scripts/activate`;
on Linux or macOS use `source .venv/bin/activate`. With an activated environment you can
drop `uv run` from the commands in this manual. If PowerShell refuses to run the activation
script, use the uv route above instead; it needs no activation.

## Check the install

```text
uv run python -m launchsim --version
```

prints `launchsim 0.1.0`. Then run the fast tests:

```text
uv run pytest -q -m "not slow"
```

They should all pass. The full suite, including the slow tier, is `uv run pytest -q`; see
[10. Validation](10-validation.md) for what the tests check.

## Optional: ffmpeg

`launchsim animate` writes `.mp4` through ffmpeg and `.gif` through Pillow (which comes
with matplotlib). Without ffmpeg the default output switches to `.gif` by itself, and an
explicit `--out something.mp4` stops with a one-line error. The app's Save-video control
([7b](07b-app.md#save-video-mp4)) needs ffmpeg too: the app resolves it once at start and
prints the executable it found, or `video: MP4 export off (<why>)`, and the rest of the app
works without it. To check whether matplotlib can see ffmpeg:

```text
uv run python -c "from matplotlib.animation import FFMpegWriter; print(FFMpegWriter.isAvailable())"
```

## Lint and format (for contributors with permission)

```text
uv run ruff check .
uv run ruff format .
```

Windows PowerShell 5.1 has no `&&`, so run the two commands one after the other (or chain
them in Git Bash). More Windows notes are in [11. Troubleshooting](11-troubleshooting.md).

Next: [2. Quick start](02-quick-start.md)
