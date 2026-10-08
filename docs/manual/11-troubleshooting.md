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
`animate`, `replay` and `scene` go to the working directory, so they land in DIR, and so
does the app's MP4 export. Pass `--out` to put a page or video elsewhere; start the app
from the folder its videos should go to.

**Drive-relative paths are refused.** A vehicle path like `C:configs\x.yaml` (a drive with
no backslash after the colon) depends on a hidden per-drive current directory, so it is
refused: `vehicle path 'C:...' is drive-relative and ambiguous; use an absolute path`.

## ffmpeg

`.mp4` needs ffmpeg on `PATH`. Without it the default `animate` output becomes a `.gif`, and
an explicit `.mp4` stops with
`error: writing .mp4 needs ffmpeg on PATH (or matplotlib's animation.ffmpeg_path); install ffmpeg or ask for a .gif`.
The app's Save-video control needs it too: without it the app starts with the line
`video: MP4 export off (<why>)` and the control says why it is off; everything else works.
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
| `ignition at_height_m and height_method come together` | One without the other | Give both |
| `at_depth_m ... is deeper than the track` | Depth larger than `stroke_m` | Reduce the depth |
| `at_speed_mps ... exceeds the exit speed ...: the push never reaches it` | Speed above the exit speed | Reduce it, or raise the exit speed |
| `at_height_m ... is at or above the drag-free apex ...` | The coast never reaches that height (either height method) | Lower the height |
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
| `offload: a planar_2d block ...`, `offload: ... needs search.figure_of_merit payload` | An `offload:` block on a 1-D file, or without a payload search | Use `planar_2d` with `figure_of_merit: payload` |
| `offload reference 'x' must be the baseline ...` | `reference` names another run | Name the baseline |
| `offload case 'x': of 'pad' is the baseline ...` | A case built on the baseline | Build it on a variant; the pad's own offload is the pad control |
| `offload case 'x': give exactly one of solve ... or fixed ...` | Both or neither | Give one |
| `a fixed offload states exactly one of stage1_t, stage1_fraction, ...` | No key, two keys, or a null in `fixed` | Give exactly one key with a number |
| `... a stage2 solve is quoted net of the pad control ...` (or `... solves stage2, which is quoted net of a pad control ...`) | A `stage2` or `both` solve without `pad_control: true`, or named in `sensitivity_of` or a sweep's `offload` | Set `pad_control: true`; name only stage-1 solves and fixed cases in arms and sweeps |
| `offload case 'x': stage2_offload_t is taken before a stage-1 case only ...` | A stage-2 pre-offload on a stage-2 or both case | Use it on a stage-1 case |
| `... takes N t of propellant from stage '...', which carries M t (an offload beyond the load ...)` | A fixed offload or pre-offload at or beyond a stage's load | Lower it |
| `offload sensitivity_of re-solves its cases ...: declare the sensitivity block` | `sensitivity_of` without a `sensitivity` block | Add one (its `of` may be `[]`) |
| `offload energy fuel_mass_t ...` | The energy block misses a stage, names an unknown one, or gives more fuel than the stage's propellant | One entry per stage, each no more than its propellant |
| `sweep N: offload names cases of the experiment's offload block, which this experiment does not declare` | A sweep's `offload` key without a block | Declare the block, or drop the key |

## Problems during or after a run

- **`FAILED.txt` in a results directory.** The run raised after its directory was created;
  the file holds the traceback and the directory has no `summary.md`. That is a bug or an
  unexpected input; the next run creates a new directory.
- **Status `search_failed`.** The payload search could not bracket or converge; see
  `search_failure_kind` and `search_failure_message` in `metrics.json`. The run has no
  recorded trajectory, so its plots and time series are empty. A searched run whose ramp
  start by event height lies just below the drag-free apex fails this way (kind `grid`,
  naming `no_ignition`): the flown coast, slowed by drag, peaks below the height
  ([5](05-assist-and-ignition.md#ramp-start-by-depth-speed-or-height)). Lower the height.
- **An offload case reads `offload_verify_mismatch`.** Its independent payload search did
  not return P_ref within the tolerance; its x\* is a lower bound. Report it as such
  ([9](09-reading-results.md#verification-and-flags)).
- **An offload case reads "not quoted".** Its own solve did not end `ok` or `no_offload`,
  or (stage 2 and both) its pad control has no offload to net it against.
- **The offload section says `reference_failed`.** The pad baseline (or, for an arm, the
  pad under that perturbation) found no payload capacity, so there is no P_ref to solve at.
- **"Findings are blocked ... a stage-1 pad control failed its consistency test".** The
  pad control found propellant to remove from the pad itself beyond the resolution bound,
  missed P_ref with full tanks by more than grams, or its solve failed. Do not quote any
  offload until it is investigated ([9](09-reading-results.md#the-pad-control)).
- **Status `drive_limit`.** The thrust on the track exceeded what the prescribed
  acceleration needs; see [5](05-assist-and-ignition.md#what-the-drive-does-and-what-it-does-not-model).
- **Status `bug_suspect` or a `bug_suspect` comparison.** A per-run check or a blocking
  screening check failed. Do not quote the number; read the Checks section
  ([9](09-reading-results.md)).
- **`-dirty` after the git hash.** The working tree had uncommitted changes when the run
  started. A calibration run with uncommitted inputs prints `PREREGISTRATION DIRTY` and is
  not a valid calibration record.
- **It is slow.** A 2-D run searches each run's payload capacity, and every comparison adds
  matched-payload evaluations, and an offload block runs nested payload searches per case.
  While you iterate, use `--variant NAME`, `--no-sensitivity`, `--no-offload` and
  `--no-plots`. Sweeps fly every point one after another (there is no parallel option
  yet; backlog B-011).

## animate, replay and scene

| Message (shortened) | Cause | Fix |
|---|---|---|
| `run directory not found` | Wrong path | Pass `results/<experiment>/<timestamp>` |
| `... has no metrics.json; pass one results directory` | You passed a sweep directory (it has no top-level `metrics.json`) or a run's subfolder | Pass the directory of a `run` |
| `... is not an experiment results directory (its metrics.json lists no runs ...)` | You passed a sweep point folder (all three commands say so since SP2) | Use `run` on the experiment, then replay that directory |
| `... is a vertical_1d run; ... draws planar_2d runs only` | A 1-D run | Use a 2-D `run` directory |
| `... has FAILED.txt: the run raised before it was written out` (scene) | The directory's run crashed | Pick another directory |
| `unknown run(s) ...; available: ...` | A name not in the directory | Use one of the listed names |
| `N runs requested; at most 4 fit ...` | More than four runs | Pick four |
| `output ... is inside the results tree` | `--out` points into the run's results tree or into any folder named `results`: the one rule of all three commands ([7](07-commands.md#where-the-default-output-goes)) | Write elsewhere |
| `output folder does not exist` | The `--out` folder is missing | Create it first |
| `--width must be an even number of pixels >= 320` | Odd or too small (animate) | Use an even width of 320 or more |
| `a .gif plays at most 50 fps ...` | `--fps` above 50 for a GIF | Lower it, or write `.mp4` |
| `... is empty (a failed search writes no trajectory)` | The run's search failed | Pick another run |

On a fresh clone the CSVs are not in git, so the shipped results directories cannot be
replayed, animated or drawn as a scene; run the experiment first and use the new directory.

## The app and the scene

Every answer of the app is one line, on the console at start or under the field or control
it concerns on the page ([7b](07b-app.md)).

| Where | Message (shortened) | Cause | Fix |
|---|---|---|---|
| console | `error: port 8765 on 127.0.0.1 is in use or reserved (another launchsim app or another program on that port?); stop it or pass --port N (0 picks a free one)` | The port is busy, or reserved by Windows | Stop the other app, or `--port 0` |
| console | `error: experiments/silo_offload_2d.yaml not found in a repository above the working directory or the installed package: start the app from a checkout of the repository` | Neither the working directory nor the installed package lies in a checkout | Start it inside the repository, or install the package from a checkout (`uv sync`) |
| console | `error: configs/display not found in <root>: the scene pages need it` | The checkout lacks the display files | Restore `configs/display/` |
| console | `video: MP4 export off (<why>)` | No usable ffmpeg (above) | Install ffmpeg; the rest of the app works |
| the form | one line under a marked field, Launch disabled with `The server refused this form (see the marked field).` | The dry run refused the form: a value outside its range or not a number, a depth deeper than the stroke, a speed above the exit speed, a height at or above the drag-free apex, an offload on a pad-only or failed-ignition launch, a stage-2 or both-stage form without Advanced, a paired pad with a penalty, an imposed mass at or beyond the load | Change the marked field; nothing was written |
| the form | `Use the form first: this page sends nothing until you do.` | The page was opened from a link on another site and has had no click yet | Click in the form |
| Launch | `A launch is running: one at a time, and it cannot be cancelled. ...` | A launch is in progress | Wait; the form, the run list and the scene stay usable |
| Launch | `the code under src, configs, experiments, pyproject.toml or uv.lock differs from the commit the app imported at its start, or git could not compare them: restart the app` | A commit changed one of those since the server started (committing documents or app summaries does not count) | Ctrl+C and start the app again |
| Launch | `the app server is stopping; no launch starts now` | Ctrl+C was pressed | Start the app again |
| the job card | `Crashed (FAILED.txt)` with the file's last line | The run raised after its directory was made (a bug, or the server was stopped during the launch) | The directory keeps `FAILED.txt` and no `summary.md`; launch again |
| the job card | `Complete: the run did not fly` with the kind | A failed search or guidance, for example a height-by-event ramp start just under the drag-free apex (`no_ignition`) | Change the setting; the pad alone is shown |
| Runs on disk | `no scene: sweep`, `no scene: 1-D`, `no scene: failed`, `no scene: incomplete`, `no scene: unreadable` | The directory holds no planar run with a time series: a sweep, a 1-D run, a crashed, half-written or unreadable directory, or a run whose CSVs are not on disk (a fresh clone) | Open a complete planar `run` directory, or run the experiment first |
| Save video | the control is off, with its reason | No ffmpeg; or a launch is running; or the directory has no scene | Install ffmpeg; wait for the launch |
| Save video | the file is named `..._scene-2.mp4` | A file of the default name already exists in the folder the app was started from; the app never overwrites | Nothing to fix; the "Saved:" line names the file written |
| the console, on Ctrl+Break under `uv run` | the shell reports a failure after `launchsim app: stopped` | `uv` exits with a console-interrupt code (3221225786) although the server stopped cleanly and marked a running launch FAILED (TODO.md KI-037) | Use Ctrl+C to stop the app |

A launch cannot be cancelled from the page; stopping the server with Ctrl+C marks it
FAILED. A launch into the repository's own `results/` is public once its `summary.md` is
committed: use `--results-root <a scratch folder>` for anything that is not meant to be
kept ([7b](07b-app.md#the-exploratory-regime)).

Next: [12. FAQ and glossary](12-faq-glossary.md)
