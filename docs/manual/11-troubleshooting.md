# 11. Troubleshooting

[Manual contents](README.md) · Previous: [10. Validation](10-validation.md) · Next: [12. FAQ and glossary](12-faq-glossary.md)

A configuration or file problem prints one line starting with `error:` and exits with code
1, without a traceback and without writing a results directory. A traceback means a bug in
the simulator. This chapter lists the common messages and the Windows notes.

## Windows

**PowerShell 5.1 has no `&&`.** Run chained commands one at a time, or separate them with
`;` (which runs the second even if the first fails), or use Git Bash. This affects the pip
fallback in CLAUDE.md (`python -m venv .venv && pip install -e ".[dev]"`) and the lint line
(`uv run ruff check . && uv run ruff format .`).

**The console is cp1252.** `launchsim` prints ASCII only, so it never fails on a Windows
console; a character outside ASCII (in a path, say) is printed as a backslash escape. Every
file it writes is UTF-8. Windows PowerShell 5.1's `Get-Content` assumes the ANSI code page,
so read a summary with `Get-Content -Encoding UTF8 summary.md`, or open it in an editor that
reads UTF-8.

**Save your YAML files as UTF-8.** A file saved as ANSI (cp1252) with a degree sign or an
accented character in a comment is refused:
`error: <path> is not UTF-8 (byte N: ...); save the file as UTF-8`.

**Keep the repository path short.** Run and experiment names are capped at 64 characters so
that `results/<name>/<timestamp>/sweep_<n>/run_<nnnn>/plots/<png>` stays under Windows'
260-character path limit from a repository at a normal depth. A repository buried deep in
the folder tree can still hit it.

**No activation needed.** If PowerShell refuses to run `.venv\Scripts\Activate.ps1`, use
`uv run ...`, which runs inside the environment without activating it.

**`uv run --directory DIR` changes the working directory to DIR.** The default outputs of
`animate` and `replay` go to the working directory, so they land in DIR. Pass `--out` to put
them somewhere else.

**Drive-relative paths are refused.** A vehicle path like `C:configs\x.yaml` (a drive with
no backslash after the colon) depends on a hidden per-drive current directory, so it is
refused: `vehicle path 'C:...' is drive-relative and ambiguous; use an absolute path`.

## ffmpeg

`.mp4` needs ffmpeg on `PATH`. Without it the default `animate` output becomes a `.gif`, and
an explicit `.mp4` stops with
`error: writing .mp4 needs ffmpeg on PATH (or matplotlib's animation.ffmpeg_path); install ffmpeg or ask for a .gif`.
[1. Install](01-install.md#optional-ffmpeg) shows how to check.

## Configuration errors

The message is followed by pydantic's description of the field, which names the run and the
key path.

| Message (shortened) | Cause | Fix |
|---|---|---|
| `file not found: <path>` | Wrong experiment path | Check the path; it is relative to the current directory |
| `vehicle file '<name>' not found; tried ...` | The `vehicle:` path matches neither the experiment's folder nor the repository root | Fix the path; the message lists both places it looked |
| `Extra inputs are not permitted` | A misspelt or unknown key | Unknown keys are always errors; check the spelling against chapters [4](04-experiments.md) to [6](06-vehicles.md) |
| `Field required` (for example `brake_decel_g`) | A required key is missing | `constant_accel` needs `stroke_m` and `brake_decel_g` |
| `bare value; vehicle files need {value, source} or {value, assumed: true}` | A plain number in a vehicle file | Write `{value: ..., source: "..."}` or `{value: ..., assumed: true}` |
| `constant_accel needs exactly one of net_accel_g or exit_speed_mps beside stroke_m` | Neither, or both | State the push one way ([5](05-assist-and-ignition.md#stating-the-push-two-ways)) |
| `keys [...] of two exclusive families are given together` | Two ways of stating one setting in one dict, often through a YAML anchor merge | Remove one; write the dict out instead of `<<: *anchor` |
| `ignition height_method: event ... arrives in SP1 step 4` | The altitude-event ramp start is not built yet | Use `height_method: closed_form` |
| `ignition at_height_m and height_method come together` | One without the other | Give both |
| `at_depth_m ... is deeper than the track` | Depth larger than `stroke_m` | Reduce the depth |
| `at_speed_mps ... exceeds the exit speed ...: the push never reaches it` | Speed above the exit speed | Reduce it, or raise the exit speed |
| `at_height_m ... is at or above the drag-free apex ...` | The coast never reaches that height | Lower the height |
| `a ramp start by at_depth_m needs an assist model` | A depth, speed or height trigger on a pad | Use it on a silo run only |
| `reference push_start needs an assist model (a pad run has no push)` | `push_start` on a pad | Use `reference: release` |
| `ignition fails: true requires end: impact` | A failed ignition must end on the ground | Add `end: impact` |
| `assist model 'linear_motor' is planned for Phase 3` | Not built yet | Use `constant_accel` |
| `track angle_deg other than 90 is a Phase 3 feature` | Tilted or curved tracks are not built yet | Use 90 |
| `include_rotation: true is a Phase 2 feature: it needs dynamics: planar_2d` | Earth rotation on a 1-D run | Set it false, or use `planar_2d` |
| `a planar_2d site needs latitude_deg, azimuth_deg and include_rotation, each given explicitly` | A 2-D site with a missing key | Give all three |
| `... is an experiment-level shared block ...` | A variant, sweep, sensitivity case or bound touches `site`, `guidance`, `search`, `target_orbit`, `checks` or `dynamics` (or the baseline declares one) | Declare shared blocks once at the top; only a paired sweep of a `guidance_study` may vary `guidance.*` |
| `on planar_2d no integrator setting may differ between runs` | A variant or path changes the integrator | Keep the integrator in the baseline only |
| `planar_2d: integrator.rtol (...) must equal search.final_rtol (...)` | The two tolerances differ | Make them equal |
| `on planar_2d a sweep of vehicle.* paths needs paired: true` | A vehicle sweep on the 2-D model | Add `paired: true` |
| `paired sweeps need label: guidance_study to vary guidance.*` | A paired guidance sweep without the label | Add the label |
| `cases need label: calibration` | `cases` in a normal experiment | Use variants or bounds |
| `... is not a valid results directory name`, `... is reserved by the results layout`, `... is longer than 64 characters` | A name that cannot be a folder | Rename ([4](04-experiments.md#top-level-keys)) |
| `variant 'x' not in experiment 'y': [...]` | `--variant` with an unknown name | Use one of the listed names |

## Problems during or after a run

- **`FAILED.txt` in a results directory.** The run raised after its directory was created;
  the file holds the traceback and the directory has no `summary.md`. That is a bug or an
  unexpected input; the next run creates a new directory.
- **Status `search_failed`.** The payload search could not bracket or converge; see
  `search_failure_kind` and `search_failure_message` in `metrics.json`. The run has no
  recorded trajectory, so its plots and time series are empty.
- **Status `drive_limit`.** The thrust on the track exceeded what the prescribed
  acceleration needs; see [5](05-assist-and-ignition.md#what-the-drive-does-and-what-it-does-not-model).
- **Status `bug_suspect` or a `bug_suspect` comparison.** A per-run check or a blocking
  screening check failed. Do not quote the number; read the Checks section
  ([9](09-reading-results.md)).
- **`-dirty` after the git hash.** The working tree had uncommitted changes when the run
  started. A calibration run with uncommitted inputs prints `PREREGISTRATION DIRTY` and is
  not a valid calibration record.
- **It is slow.** A 2-D run searches each run's payload capacity, and every comparison adds
  matched-payload evaluations. While you iterate, use `--variant NAME`, `--no-sensitivity`
  and `--no-plots`. Sweeps fly every point one after another (there is no parallel option
  yet; backlog B-011).

## animate and replay

| Message (shortened) | Cause | Fix |
|---|---|---|
| `run directory not found` | Wrong path | Pass `results/<experiment>/<timestamp>` |
| `... has no metrics.json; pass one results directory` | You passed a sweep directory (it has no top-level `metrics.json`) or a run's subfolder | Pass the directory of a `run` |
| `... is not an experiment results directory (its metrics.json lists no runs ...)` (replay) | You passed a sweep point folder | Use `run` on the experiment, then replay that directory |
| `... is a vertical_1d run; animate draws planar_2d runs only` | A 1-D run. animate also says this for a sweep point folder of a 2-D sweep, because a point's `metrics.json` does not record the model | Use a 2-D `run` directory |
| `unknown run(s) ...; available: ...` | A name not in the directory | Use one of the listed names |
| `N runs requested; at most 4 fit one animation` (or replay) | More than four runs | Pick four |
| `output ... is inside the results tree` | `--out` points into the results root (replay also refuses any folder named `results`) | Write elsewhere |
| `output folder does not exist` | The `--out` folder is missing | Create it first |
| `--width must be an even number of pixels >= 320` | Odd or too small | Use an even width of 320 or more |
| `a .gif plays at most 50 fps ...` | `--fps` above 50 for a GIF | Lower it, or write `.mp4` |
| `... is empty (a failed search writes no trajectory)` | The run's search failed | Pick another run |

On a fresh clone the CSVs are not in git, so the shipped results directories cannot be
replayed or animated; run the experiment first and use the new directory.

Next: [12. FAQ and glossary](12-faq-glossary.md)
