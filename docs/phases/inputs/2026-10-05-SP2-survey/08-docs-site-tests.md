Provenance: SP2 step A0 survey 08 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/08-docs-site-tests.md); a record, not edited (README.md).

# 08: Documents, site and test conventions SP2 must update or follow

Survey for SP2 step A0. Read-only, at HEAD b69ff0c (clean tree, checked before and after).
Scratch scripts: `s08_env_check.py`, `s08_pdf_meta.py`, `s08_guard_probe.py` (this folder).
Nothing in the repository was changed; pytest was not run.

What was verified by running something: the project environment's modules and tools
(`s08_env_check.py`), the deck PDF's metadata and all file sizes (`s08_pdf_meta.py`), the
two scaffold guards' regexes on candidate lines and the manual's chapter order
(`s08_guard_probe.py`), `git check-ignore --no-index` on hypothetical paths, and candidate
`.gitignore` lines in a throw-away repository outside the project. Everything else is read
from the files. Not verified: how pytest's `filterwarnings = ["error"]` treats an unclosed
server socket or a worker-thread exception (stated below as expected behaviour, to be
checked by the first server test).

## 1. Statements that become wrong once `launchsim app` (and maybe `scene`) exists

### README.md

| Line | Text | Why it changes |
|---|---|---|
| 19 | "**Status:** Phases 0-2 and SP1 done. ... Next: a local app with an animated 2-D launch scene (SP2), then SP7 ..." | status |
| 37 | "There is no graphical interface. `launchsim` is a command-line program: every output is a file (Markdown, JSON, CSV and PNG), the `animate` command turns a finished 2-D run into a video you can watch, and the `replay` command turns it into an interactive page you open in a browser." | the sentence the phase file names |
| 77-83 | the experiments table lists 5 files | already stale: `silo_offload_2d.yaml` and `silo_offload_2d_readme.yaml` are missing (they are in docs/manual/02-quick-start.md:20-21) |
| 90 | "Both take `--no-plots` and `--results-root DIR`. Only `run` takes `--variant NAME` ... and `--no-sensitivity`" | already stale: no `--no-offload` (CLAUDE.md:19-20 has it) |
| 111-115 | "### Look at the results" (summary.md, plots/, CSVs) | gains the app and the scene |
| 117-142 | "### Animate a 2-D run" ... 136: "For an interactive view, `replay` writes a single HTML page you open in a browser" ... 142: "The default output is `./<experiment>_<timestamp>_replay.html`, never inside `results/`." | the quick start needs an app section; 125 and 142 describe the two output-path rules that KI-017 unifies |
| 372 | "They come as `summary.md`, `metrics.json`, CSV time series and PNG plots, and `launchsim animate` turns a 2-D run into an MP4 or GIF" | no replay, no app |
| 390 | "Python 3.12 managed with uv; numpy, scipy, pandas and matplotlib; PyYAML and pydantic for configs; pytest and ruff; ..." | only if Pillow is declared (KI-018) |
| 414 | roadmap row 3: "... is now phase SP7, next after SP2 and before the 3-D phases" | wording after SP2 closes |
| 431 | "src/launchsim/            physics, models, simulation, CLI (run, sweep, animate)" | already omits replay; gains app |
| 444 | "docs/phases/ ... one file per phase (SP1 to SP6)" | already stale: SP7's file exists |
| 447-448 | "docs/demos/ recorded demo of each finished phase (created when the first phase closes; none yet)" | already false: docs/demos/SP1/ has 7 tracked files |
| 451-454 | "site/ ... the page templates (manual, replay frame)" | a scene frame, if Q1 |

The phase file (section 2 item 7, exit criterion 13) names only the README's quick start
and status. The layout block (423-459) and line 372 need the same pass.

### CLAUDE.md

| Line | Text | Change |
|---|---|---|
| 9 | "- Status: ... SP2 (local app with the 2-D launch scene) is next, then SP7 ..." | status line |
| 15-22 | the Commands list; 21: "Animate a 2-D run (MP4/GIF): ...", 22: "Interactive replay page (HTML): `uv run python -m launchsim replay ...`" | add `app` (and `scene`) |
| 46-50 | layout: `results_io.py`, `plots.py       plot writers (Agg) and the `animate` MP4/GIF replay`, `replay.py      the `replay` command: a self-contained interactive HTML replay page (template in templates/replay.html)`, `optimize.py`, `cli.py` | add `run_data.py`, `scene.py`, `app.py`, the templates; `templates/` has no line of its own today |
| 32 | "config.py      pydantic models that validate vehicle and experiment YAML and convert units; no file I/O" | binds where a display-block loader may live |
| 51 | "configs/vehicles/  one YAML per vehicle; every number has `source:` or `assumed: true`" | add `configs/display/` |
| 53 | "results/           generated, never hand-edited; gitignored except */summary.md" | inexact if `results/app/` is wholly ignored (Q3) |
| 59 | "docs/demos/        recorded demo of each finished phase (SP<n>/; created when a phase closes; SP1 so far)" | SP2 |
| 140 | "- Physics functions are pure: no globals, I/O or printing. I/O lives in cli.py, sim.py, results_io.py, plots.py and replay.py." | add the new I/O modules |

The layout block names no `site/`, `assets/`, `docs/manual/` or `docs/media/`; only
line 154 mentions the public face.

### docs/manual/

| File:line | Text | Change |
|---|---|---|
| README.md:19-40 | "## Status in one paragraph" (ends at SP1) | SP2 sentence |
| README.md:47 | "[2. Quick start] Run a shipped experiment, open the summary, replay a 2-D run" | app |
| README.md:53 | "[7. Commands] `run`, `sweep`, `animate`, `replay`: every flag, default and output location" | app, scene; a row for a new chapter |
| README.md:62 | "**You want to see something run:** chapters 1 and 2, then chapter 7 for the flags." | app chapter |
| README.md:87-96 | "What this manual was checked against ... at commit `cfd9059` (2026-10-04) ... `plots.py` and `replay.py`" | new commit and modules |
| 01-install.md:19-21 | "The package depends on numpy, scipy, pandas, matplotlib, pydantic, PyYAML and `ambiance` ... The dev extra adds pytest and ruff." | if Pillow is declared |
| 01-install.md:69 | "`launchsim animate` writes `.mp4` through ffmpeg and `.gif` through Pillow (which comes with matplotlib)." | if Pillow is declared |
| 02-quick-start.md:5-7 | "There is no graphical interface yet (a local app is planned for phase SP2). `launchsim` is a command-line program: every output is a file. This chapter runs two shipped experiments, shows where the results go, and turns a 2-D run into an interactive page." | the sentence the phase file names |
| 02-quick-start.md:93, 136-140, 142-147 | "## Step 4: replay it in a browser"; "On a fresh clone"; "Where to go next" | an app step and link |
| 05b-offload.md:274-276 | "`launchsim replay` and `launchsim animate` choose the baseline and up to three variants by default, so offload runs are never in the default selection." | the scene's default for an offload directory (pad and the first solved stage-1 case) differs |
| 07-commands.md:5 | "`launchsim` has four commands." | five or six |
| 07-commands.md:8-14 | the synopsis block (run, sweep, animate, replay, --version) | add lines |
| 07-commands.md:93-95 | "The default output goes to the current directory; if the current directory is inside the run's results tree, the file goes next to that tree instead. An explicit `--out` inside the results tree is refused, and its folder must exist." | animate's rule changes under KI-017 |
| 07-commands.md:119-120 | "The output may not lie inside the run's results tree or inside any folder named `results`; ..." | becomes the one rule |
| 07-commands.md:123-133 | "## Exit codes and messages" | the server's exit, Ctrl+C |
| 07-commands.md:138-151 | "## The commands in CLAUDE.md" (a copy of CLAUDE.md's list) | keep in step |
| 08-outputs.md:5 | "Every `run` and `sweep` writes a new directory under the results root" | a Launch does too |
| 08-outputs.md:15-16 | "Only each directory's top-level `summary.md` is tracked in git (see `.gitignore`)" | false for app runs if Q3 ignores them wholly |
| 08-outputs.md:58 | "so `animate` and `replay` cannot take one" (a sweep directory) | scene and run browser too |
| 08-outputs.md:142, 148, 271 | `git` = `{hash, dirty, error}`; "`model`, `label`, `search_budget_id` \| 2-D only"; resolved_config "adds `model`, `label`, ..." | an `exploratory` label value or provenance field; the git state at server start |
| 11-troubleshooting.md:130-147 | "## animate and replay"; 137: "animate also says this for a sweep point folder of a 2-D sweep, because a point's `metrics.json` does not record the model"; 140: "`--out` points into the results root (replay also refuses any folder named `results`)" | 137 and 140 change if the shared loader and the one path rule unify the two commands; app rows (port in use, job running, refusals) |
| 12-faq-glossary.md:85-89 | "**Is there a 3-D model or a graphical app?** Not yet. A local app with an animated 2-D launch scene is phase SP2; ... Today you get files, an MP4 or GIF from `animate`, and an interactive page from `replay`." | the second "no app" statement in the manual; the phase file does not name it |

### site/index.html

- 388: `<tr><td class="phase">SP2</td><td>A local app with an animated 2-D launch scene: set depth, ramp start and offload, press Launch, watch pad and silo side by side.</td><td><span class="label wip">Next</span></td></tr>`
- 389: SP7 row, "Runs after SP2 and before the 3-D work.", label "Planned".
- 122, 182, 284: "(phase SP7, after SP2)".
- 391: "SP4 | The launch shown on a globe in the app".
- 64-69 hero buttons and 405-407 "Explore" cards: "Animation examples: Replays, videos and GIFs of recorded runs, each with the command that made it." No card for the app.
- 420: the `<!-- stamp -->` marker the build requires on this page.
- No sentence on this page says there is no interface.

### site/deck/index.html (19 slides)

- Slide 1 (592-593): badges "Phases 0-2 and SP1 done · SP2 next", "Status as of 4 October 2026".
- Slide 8 "The simulator" (959): "Every run writes `summary.md`, `metrics.json`, CSV time series and plots. `animate` makes an MP4 or GIF; `replay` an interactive HTML page."
- Slide 15 (1176): "phase SP7, after SP2, decides whether the headline survives."
- Slide 16 "Roadmap" (1190): `<span class="when">Next</span><b>SP2</b><span>Local app with a 2-D launch scene</span>`; 1191 SP7 "Planned"; 1198 "now SP7, after SP2".
- Slide 17 "See it fly" (1223-1231): the "Animation examples" list, "Videos, GIFs and interactive replays: khoks.github.io/.../examples/", "A model replay, not a design result."
- Slide 18 "Read more" (1249): "docs/phases/: the program board, SP1 to SP6." (already stale); 1256-1257: "User manual: install, run, experiment and vehicle files, outputs." and "Animation examples: replays of the recorded 2-D runs."; 1262-1266 "How it is run": `uv sync`, `launchsim run experiments/silo_screening_2d.yaml`, `launchsim replay results/silo_screening_2d/<timestamp> --runs pad silo_cold`.
- Slides refer to each other by number ("slide 10" at 655, "slide 11" at 1070, "Prior art slide (7)" at 1296; CSS comments name slide 14). A new slide placed after 17 moves none of them.

### site/examples/index.html

- 6-7: title "Animation Examples", meta description "Interactive replays and a video of SP1's fuel offload ...".
- 233: "Replays of two recorded runs ... Every frame is drawn from the run's recorded time series; nothing is re-simulated in the browser or in the videos." A scene draws display-only reconstructions (spent stage, fairing halves), so this sentence needs a qualifier for a scene entry.
- 247: "The examples come from two shipped runs".
- 261-272: the table of contents (`<ul class="toc">`), one `<li>` per group and entry.
- 359: "Offload runs are not in the default selection of `replay` or `animate`".
- 626, 634: "Reproduce"; 634: "Output names ending in `_replay.html`, `_animation.mp4` or `_animation.gif` are ignored by git."
- 641: the footer's "Data:" paragraph (provenance of every page and video).

## 2. The manual

- Files: `docs/manual/README.md` (the contents page) and 13 chapters: 01-install, 02-quick-start, 03-concepts, 04-experiments, 05-assist-and-ignition, 05b-offload, 06-vehicles, 07-commands, 08-outputs, 09-reading-results, 10-validation, 11-troubleshooting, 12-faq-glossary.
- Build: `site/build.py::discover_chapters` (806-813) takes README.md first (it becomes `index.html`), then every other `*.md` sorted by file name; `build_manual` (816-848) renders each with `site/templates/manual.html` into `_site/manual/<stem>.html`. The sidebar (`nav_html`, 771) and the pager (`pager_html`, 788) are generated from that order.
- Per chapter (`ManualTreeprocessor.run`, 656-691): the first `h1` is the title (a chapter without one is a build error, 754-756); `h2`s become the sidebar's sub-entries; the chapter's own first-line navigation paragraph ("[Manual contents](README.md) · Previous: ... · Next: ...") is dropped (`find_nav_line`, 693-708: one of the first three blocks, a paragraph whose first link has href `README.md` and text "Manual contents"); the trailing "Next: [...]" line stays on the page.
- Links: another chapter's `.md` becomes `.html`; an image is copied to `_site/manual/files/<repository path>` (a missing image is a build error); any other repository path becomes a github.com blob or tree URL, and the link check then requires it to exist, not to be git-ignored, and (for `.md#anchor`) to have that heading (`check_repo_refs`, 1068-1084).
- Command blocks: a fenced block in which every line starts with one of `CMD_PREFIXES = ("uv ", "python ", "pip ", "git ", "cd ", ".venv", "ffmpeg ")` (105) wraps at spaces; any other block scrolls sideways.
- Pinned Markdown: Python-Markdown 3.11. `MARKDOWN_PIN = "3.11"` (78), `uvx --with markdown==3.11 python site/build.py` (docstring, 32), `python -m pip install "markdown==3.11"` in `.github/workflows/pages.yml`. Another version is a warning only (1132-1135). It is not a project dependency: `import markdown` fails in the project environment. Extensions: `tables`, `fenced_code`, `TocExtension(permalink="#")`.
- Where an app chapter goes. By file name: `07b-app.md` sorts after `07-commands.md` and before `08-outputs.md`; `02b-app.md` after `02-quick-start.md`; `13-app.md` last (checked with `sorted`). Precedent: SP1 added `05b-offload.md`, titled "5b. ...". Hand edits a new chapter needs: its own nav line and closing "Next:" line; the neighbours' lines (for 07b: 07-commands.md:3 and :156, 08-outputs.md:3); a row in the contents table of docs/manual/README.md (44-58). The sidebar and pager need nothing.
- An app screenshot can be embedded straight from `docs/demos/SP2/*.png`: the build copies it.

## 3. The gallery and the deck

### Gallery entries (site/examples/)

| Entry (id) | Replay page, bytes | Media (site/examples/media/), bytes |
|---|---|---|
| SP1.1 `pad-vs-silo-offload` | pad-vs-silo-offload.html, 167,055 | fuel_offload_pad_vs_silo_2d.mp4 812,704; .gif 865,298; _poster.jpg 185,275 |
| SP1.2 `offload-vs-paired-pad` | offload-vs-paired-pad.html, 166,246 | none |
| 2.1 `pad-vs-silo-cold` | pad-vs-silo-cold.html, 168,272 | ascent_pad_vs_silo_cold_2d.mp4 805,301; .gif 2,661,457; _poster.jpg 137,781 |
| 2.2 `ignition-timing` | ignition-timing.html, 304,598 | ignition_timing_2d.mp4 1,115,508; .gif 1,153,049; _poster.jpg 145,481 |
| 2.3 `failed-ignition` | failed-ignition.html, 114,305 | failed_ignition_2d.mp4 646,427; .gif 678,223; _poster.jpg 131,448 |

index.html is 66,439 bytes with its CSS inline (12-212) and its own theme script. All five
replay pages carry the marker, the stale drive sentence (fixed at build time) and two
Google Fonts links each. Page names use hyphens; media names use underscores.

An entry is an `<article class="example" id="..." aria-labelledby="...">` (303-370):
`<header>` with `<p class="kicker">`, `<h2 id>`, `<p class="summary">`; an optional
`<figure>` with `<video class="media" controls preload="none" playsinline poster="media/..._poster.jpg" width="1280" height="720">`, a `<source>` and a GIF fallback link, and a `<figcaption>`;
`<div class="actions">` with `<a class="btn" href="X.html">Open the interactive replay</a>` and `<a class="btn ghost" href="media/...">MP4 <span class="size">794 KiB</span></a>`;
`<div class="col"><h3>What it shows</h3>`; `<div class="tablewrap"><table class="nums">`;
`<p class="src">Numbers: ...`; `<div class="cols">` with "For the hypothesis" (`<ul class="for">`) and "Against it, stated as plainly" (`<ul class="against">`);
`<details class="cmd"><summary>Commands that made it</summary>` with one `<div class="codeblock"><pre><code>` per command.
Entries sit under a `<section class="group" id>` (kicker, h2, provenance tags) and are listed in the toc (261-272) and in the footer's "Data:" paragraph (641).

### What an exported scene page needs to be on the site

1. A marker and a frame rule. `frame_replays` (build.py 941-957) globs `_site/examples/*.html` and skips any page without `REPLAY_MARKER = "Written by launchsim replay"` (88, test at 948). The marker is the CSS comment at `src/launchsim/templates/replay.html:13`. A scene page without a marker is copied unframed and the build says nothing: no favicon, no bar back to the gallery, no all-rights-reserved notice. A scene template that keeps the replay comment is framed as a replay and gets `REPLAY_TEXT_FIXES`.
2. The frame (`site/templates/replay-frame.html`) is inserted before `</head>`, after `<body ...>` and before `</body>` (`frame_replay`, 899-915; a page missing one of them is an error). Its CSS uses the replay page's token names: `--panel`, `--rule`, `--ink`, `--ink-2`, `--ink-3`, `--caution`, `--run-0`, `--run-1`, `--focus`, `--font-display`. A scene page must define them. Its back link text is "← Animation examples".
3. `fix_replay_text` (918-938) makes a page that still contains `REPLAY_STALE_TEXT = "Each of these favours the assisted runs."` a build error, but only for pages that pass through `frame_replays`.
4. Link check (`LinkChecker.check`, 1040-1066): every `href`, `src`, `poster`, `xlink:href` and `srcset` of every page. A `#fragment` needs an element with that id on the page (an inline `<use href="#mark">` included); a relative link must stay inside `_site`; http(s) links are skipped unless they are blob or tree links into this repository.
5. A file name git does not ignore. With a `*_scene.html` pattern, `site/examples/pad_vs_silo_cold_scene.html` is ignored and `site/examples/pad-vs-silo-cold-scene.html` is not (checked). An ignored page is not on GitHub, CI builds without it, and the gallery link then fails the build.
6. In index.html: an `<article class="example">`, a toc line, the commands block, the footer "Data:" line, and line 634 if a new ignore pattern is added.

### Deck

- 19 slides (`<section class="slide`, comments "1 ─ Title" to "19 ─ License" at 580-1285).
- PDF: `site/deck/launch-assist-sim-deck.pdf`, 988,595 bytes, 19 pages of 960 x 540 pt. Its metadata: `/Creator` "... HeadlessChrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0", `/Producer` "Skia/PDF m154", created 2026-10-04 19:22:55 UTC. So it was printed by headless Microsoft Edge.
- The command is not recorded anywhere: not in docs/phases/SP1-fuel-offload-planar.md (509, 1049, 1107, 1149 say only "PDF" and "regenerated"), docs/demos/SP1/README.md, the handoff, TODO.md, or the protocol (7.6: "and its PDF export"). The commit messages say "PDF regenerated, 19 pages". The deck supports it through `@page { size: 1280px 720px; margin: 0; }` (543), the print rules (544-557), a `?print` paged layout (1329) and `beforeprint` (1485). The handoff's gotcha applies (docs/handoff/NEXT_SESSION.md:353-357): headless Edge from Git Bash writes no file while Edge is running; run it from PowerShell with its own `--user-data-dir`. Edge is at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (not on PATH).
- The PDF link on slide 18 (1258) is an absolute Pages URL, so the link check does not test it.

## 4. Test conventions

### tests/test_replay.py helpers (49-260)

Module constants (35-46): `EXPERIMENT = "synth_replay_2d"`, `TIMESTAMP = "20260101T000000Z"`, `T_END_S = 60.0`, `PUSH_S = 2.0`, `DEPTH_M = 50.0`, `SERIES_COLUMNS = [*replay.REPLAY_COLUMNS, "stage"]`, `EVENT_COLUMNS = ["t_s", "event", "phase", "stage", "alt_m", "downrange_m", "speed_rel_mps", "m_kg"]`, `RUNS = ("pad", "silo", "silo_step")`, `BOUND_AND_CASE_RUNS = {"pad__aero_bound": False, "silo__aero_bound": True, "alt_low": False}`.

| Helper | Signature | What it makes |
|---|---|---|
| `_row` (49) | `(t_rel: float, offset: float, assist: bool) -> dict[str, object]` | one row: before release a vented-shaft push from -50 m (q and Mach NaN) or a pad hold; after it a smooth climb, GRAVITY_TURN/stage1 to 40 s then LTG_BURN/stage2. Keys: t_s, t_rel_release_s, phase, stage, alt_m, downrange_m, speed_rel_mps, gamma_rel_rad, felt_axial_g, q_pa, mach, m_kg |
| `_events` (85) | `(assist: bool) -> list[tuple[str, float]]` | push_start or ignition at -2 s, release 0, ignition or kick_end 1, propellant 40, staging 40, fairing 50, cutoff 60, end 60 |
| `_write_run` (99) | `(run_dir: Path, name: str, assist: bool) -> None` | `<run_dir>/<name>/timeseries.csv` (rows every 0.5 s from -2 to 60 s) and `events.csv`, both with `encoding="utf-8", newline=""` |
| `_run_metrics` (117) | `(assist: bool, step: bool) -> dict[str, Any]` | a metrics.json run record; `drag_loss_mps` is NaN on purpose |
| `_run_config` (143) | `(assist: bool, orbit_km: float = 200, rotation: bool = True, vehicle: str \| None = None) -> dict[str, Any]` | a resolved_config.yaml run entry (site, planar.target_orbit, assist block) |
| `_dry_mass_case` (169) | `(fraction: float, payload_kg: float) -> dict[str, Any]` | a stage-1 dry-mass sensitivity record of `silo` |
| `_make_run_dir` (183) | `(root: Path, model: str \| None = "planar_2d", vehicle: str = "toy_2d") -> Path` | `root/results/synth_replay_2d/20260101T000000Z/` with run folders pad, silo, silo_step, pad__aero_bound, silo__aero_bound, alt_low; `metrics.json` written with `json.dumps` (so it contains bare NaN and Infinity; `model=None` gives a 1-D-looking file); `resolved_config.yaml` |

Also `_listing(folder) -> set[Path]` (261, the read-only check), `_no_nan` (265), `_embedded(page) -> dict` (269: finds `<script type="application/json" id="replay-data">` and parses it with `parse_constant=_no_nan`), `_restate_push` (533).

The synthetic series has no `pitch_rad`, `thrust_N`, `thrust_vac_N`, `s_m` or track columns and its events have no `gamma_rel_rad`; a scene payload test needs a wider helper.

### The tests to mirror

- Strict JSON and ASCII page: `test_page_embeds_every_run_and_event_as_strict_json` (278-316): `page.startswith("<!doctype html>")`, `'<meta charset="utf-8">' in page`, `page.isascii()`, the data block parsed strictly, NaN and Infinity in metrics.json arriving as `None`, the results tree unchanged.
- `test_embedded_json_cannot_close_its_script_and_rejects_nan` (360-365): `replay.embed_json` output has no "<" and raises ValueError on NaN (`json.dumps(..., separators=(",", ":"), allow_nan=False, ensure_ascii=True)` then "<" to `\u003c`, replay.py 1166-1171).
- `test_template_ships_as_package_data` (368-371): `replay.load_template()` (through `importlib.resources`, replay.py 1174-1177) holds `REPLAY_DATA_TOKEN` exactly once and `template.isascii()`. Editable install only.
- `test_inline_script_is_valid_javascript` (665-682): `NODE = shutil.which("node")`; `@pytest.mark.skipif(NODE is None, reason="node not installed: inline script syntax not checked")`; it asserts exactly one bare `<script>...</script>` block, writes it to `tmp_path/inline.js` and runs `[NODE, "--check", str(js)]` (`capture_output=True, text=True, timeout=60, check=False`). Node v24.11.1 is installed here (`C:\nvm4w\nodejs\node.EXE`), so the test runs on this machine.
- CLI conventions: `main([...])` returns 0 or 1, `capsys`, `out.encode("ascii")`, "error:" and no "Traceback"; `cli.say` (cli.py 177-179) prints through `encode("ascii", "backslashreplace")`.
- Output path: `test_default_output_is_outside_the_run_dir` (374), `test_output_inside_results_or_not_html_is_refused` (393), `test_output_in_any_results_tree_is_refused` (612).

### tests/test_animate.py fixtures

`_row(t_rel, offset, assist, orbit=False)` (55), `_write_run(run_dir, name, assist, orbit=False)` (93), `_make_run_dir(root, model="planar_2d", extra_variants=0, orbit=False)` (134; runs pad and silo plus `var<k>` copies with status impact; metrics.json has no comparison block), `_listing` (165), `_no_ffmpeg(monkeypatch)` (169), `_figure(run_dir)` (438), `_BrokenFFMpeg` (489), `_make_offload_run_dir(root, orbit=False)` (549-636: adds an `offload` record with cases silo_s1 (paired pad silo_s1__pad), silo_fix5, silo_none, pad controls in three modes, `offload.runs`, and a folder per offload run). `EXPERIMENT = "synth_2d"`, `T_END_S = 80.0`. `test_custom_results_root_is_protected` (478-486) pins `plots.check_animation_out` and `plots.default_animation_path` for a results root not named "results".

Names the existing tests import, which a refactor with unchanged tests must keep where they are: from `plots`: ANIMATION_COLUMNS, ANIMATION_GRID, AnimationError, AnimationRun, CALIBRATION_RECORDS, FFMpegWriter (monkeypatched on the module), FONT_FOOTNOTE_PT, LEGEND_TITLE, MARKER_GLYPHS, NEAR_ORBIT_PHASE, OFFLOAD_CASE, OFFLOAD_PAD_CONTROL, OFFLOAD_PAIRED_PAD, READOUT_NAME_CHARS, TIMELINE_*, _AscentFigure, _legend_label, _phase_at, animation_caveats, animation_playback_fps, animation_record, animation_run_names, ascent_time_map, calibration_caveat, calibration_gap, check_animation_out, default_animation_path, frame_geometry, inside_calibration_band, legend_title, load_animation_runs, playback_label, playback_speeds, readout_names, signed, write_ascent_animation. From `replay`: DRY_MASS_PARAM, REPLAY_COLUMNS, REPLAY_DATA_TOKEN, REPLAY_EARLY_DT_S, REPLAY_EARLY_END_S, REPLAY_LATE_DT_S, ROLE_BOUND, ROLE_OFFLOAD, ReplayError, SERIES_FIELDS, _finite, calibration_caveat, default_replay_path, embed_json, load_template, replay_data, replay_grid, run_source, wrapped_deg, write_replay_page. No test names `plots._results_tree`, `plots._is_inside`, `plots._events`, `replay._read_json`, `replay._read_yaml`, `replay.run_events`, `replay.results_ancestors` or `replay.check_replay_out`.

### Repo-wide guards a new app.py, scene.py and run_data.py must pass

1. `tests/test_scaffold.py::test_every_file_open_declares_encoding` (66-75). For every `src/launchsim/**/*.py`, every line (comments and docstrings too) matching `re.search(r"\b(open|read_text|write_text)\(", line)` must have the text `encoding=` in that line or the next three (`"\n".join(lines[i : i + 4])`). Checked with the regex: `webbrowser.open(url)`, `path.open('rb')`, `os.open(...)` and a comment containing `open(url)` are flagged; `webbrowser.open_new_tab(url)`, `urlopen(...)`, `read_bytes()`, `subprocess.Popen(...)`, `wfile.write(...)` are not.
2. `tests/test_scaffold.py::test_earth_constants_only_in_constants_py` (52-63). No `src/launchsim/**/*.py` except constants.py may match any of `CONSTANT_LITERALS` (17-25): `3\.986004418e14`, `6378137`, `6_378_137`, `7\.2921150e-5`, `7\.292115e-5`, `9\.80665`, `(?<![\d.])9\.81(?![\d])`. It reads `.py` files only; a template is not scanned.
3. Docstring guards are per listed module, not repo-wide: `PHYSICS_MODULES` (test_scaffold.py 27-38), and parametrised lists in test_ltg.py:551-553, test_planar_events.py:547, test_search.py:822 and test_phases_package.py:850. A new module is covered only if its own test adds one.
4. `tests/test_scaffold.py::test_pyproject_dev_tooling_installable_both_ways` (99-106): the `dev` extra must contain pytest and ruff, and `[dependency-groups] dev` must equal `["launchsim[dev]"]` or the extra.
5. `tests/test_config_planar.py::test_every_shipped_planar_experiment_is_checked` (881-890): the set of `experiments/*.yaml` files with `dynamics: planar_2d` must equal `PLANAR_EXPERIMENTS` (62-69). A preset shipped as a file under `experiments/` fails it until listed.
6. pytest settings (pyproject.toml 42-46): `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`, `markers = ["slow: slower than 5 s"]`, `filterwarnings = ["error"]`.
7. No test scans `src/` for `print(`, `warnings.warn`, I/O in pure modules or magic numbers. Those are review rules: CLAUDE.md:140-141 and SESSION_PROTOCOL.md:390 ("never call `warnings.warn` in library code").
8. No test reads README.md, CLAUDE.md, docs/manual, docs/physics.md prose or site/. Two tests read findings notes (`test_animate.py::test_calibration_record_matches_its_findings_note`, 299-326). The only automatic check on public text is the link check of site/build.py.
9. ruff (pyproject.toml 30-40): py312, line length 100, `select = ["E", "F", "I", "UP", "B", "NPY", "RUF"]`, `ignore = ["RUF001", "RUF002", "RUF003"]`, LF endings; it also checks tests/, site/build.py and assets/brand/*.py. `.gitattributes`: `* text=auto eol=lf`; `*.png`, `*.gif`, `*.mp4` binary (no rule for `.woff2`, `.pdf`, `.jpg`).

docs/physics.md's "Test-to-equation map" (6163) states the convention for expected values: "Every expected value in a test is computed there from constants and closed forms, never from the package's own formulas".

## 5. pyproject.toml, Pillow, .gitignore

- Dependencies (7-15): numpy>=2.3, scipy>=1.16, pandas>=3.0, matplotlib>=3.10, pydantic>=2.11, pyyaml>=6.0.2, ambiance>=1.3.1,<2. Dev extra (18): `["pytest>=9.0", "ruff>=0.16"]`. Group (21): `["launchsim[dev]"]`. Script (24): `launchsim = "launchsim.cli:main"`. Build backend (27-28): `uv_build>=0.12.13,<0.13`. No package-data setting.
- KI-018. PIL is imported directly in two places: `tests/test_animate.py:26` (`from PIL import Image`) and `assets/brand/render_png.py:73`. The package uses it only through `matplotlib.animation.PillowWriter` (plots.py 35, 1873). uv.lock has pillow 12.3.0 as a dependency of matplotlib 3.11.2. Declaring it is one string, either in the dev extra (line 18; only the tests need the import) or in `dependencies`, plus a re-lock that adds one pillow line to the launchsim entry's lists in uv.lock and should move no other version. The golden exact tier keys on python, numpy, scipy, pandas, pyyaml, system and machine (tests/golden_1d_support.py 148-156), so it is not affected unless the re-lock moves one of those. Text to change with it: docs/manual/01-install.md:19-21 and :69, README.md:390.
- .gitignore (22 lines): 10-14 `results/**`, `!results/.gitkeep`, `!results/*/`, `!results/*/*/`, `!results/*/*/summary.md`; 17-19 `*_animation.mp4`, `*_animation.gif`, `*_replay.html`; 22 `_site/`. There is no `!docs/demos/**` line.
- Checked with `git check-ignore --no-index` at HEAD: `docs/demos/SP2/x_replay.html` and `x_animation.gif|mp4` are ignored (lines 19, 18, 17); `docs/demos/SP2/pad_vs_silo_cold_scene.html` is not ignored today; `results/app/<ts>/summary.md` is not ignored (line 14 un-ignores it) while its metrics.json and CSVs are.
- Checked in a throw-away repository with three lines appended (`results/app/**`, `*_scene.html`, `!docs/demos/**`): the app summary is ignored; shipped summaries stay tracked; `docs/demos/SP2/pad_vs_silo_cold_scene.html` is un-ignored, and so are `docs/demos/**/*_replay.html` and `*_animation.*`; `site/examples/pad_vs_silo_cold_scene.html` is ignored and `site/examples/pad-vs-silo-cold-scene.html` is not.
- `.claude/settings.local.json` is ignored by the user's global file; a `.claude/launch.json` would not be and would show as untracked.

## 6. docs/demos/SP1 and how the screenshot was taken

- Recorded (7 tracked files): README.md (11,150 bytes), console-run.txt, console-sweep.txt, console-bridge.txt, offload-block.md (lines 98-226 of the run's summary.md), pad_vs_offloaded_silo.html (167,055; the replay page, named so that `*_replay.html` does not catch it) and pad_vs_offloaded_silo.png (374,635).
- The screenshot (README 144-156): the folder served with `uv run python -m http.server 8761 --bind 127.0.0.1`, page at `http://127.0.0.1:8761/pad_vs_offloaded_silo.html`, "taken in a browser driven by Playwright, with a 1440 px wide viewport and the light colour scheme, over the full page height", playback paused and the slider at its end. One screenshot, light only.
- The playwright Python package is not in the project environment: `uv run python` reports `module playwright: NOT INSTALLED`; it is in neither pyproject.toml nor uv.lock; there is no `uvx` note about it in the demo README or the SP1 phase file (the only `uvx` use is the site build). `%LOCALAPPDATA%\ms-playwright` holds `mcp-chrome-*` profile folders, firefox, webkit and ffmpeg but no chromium build, which fits a Playwright MCP server driving the installed Chrome. In this surveyor session that MCP server (plugin:playwright) failed to connect (timeout), so it could not be tried.
- On this machine: node v24.11.1, npx, uvx, ffmpeg and gh are on PATH; Edge and Chrome are installed but not on PATH.
- The replay template honours a `data-theme` attribute on `<html>` (replay.html 37-46, 578), as the site pages do, so a dark screenshot does not need colour-scheme emulation.

## 7. docs/physics.md sections (6,428 lines)

1 title; 26 Atmosphere; 137 Atmosphere, drag and back-pressure in flight; 333 Frames and datum; 368 1-D ascent state and equations of motion; 429 Gravity; 494 Planar ascent state and equations of motion; 648 2-D loss identity; 750 Planar reductions; 813 Orbital elements and the circular target; 840 Planar release map; 947 Stage-1 guidance and events (planar); 1201 gamma* inner solve; 1382 Time-shift mechanism (2-D gravity loss); 1450 Stage 2 and insertion (planar); 1629 LTG shooting; 1764 Rocket-equation closure (planar); 1847 Max-Q and loads (planar); 1909 Figures of merit (planar); 2207 Virtual propellant; 2264 Payload and gamma* search; 2547 Shared budget; 2575 Convergence (planar); 2778 Performance (measured); 2953 Screening-beat rule (2-D); 3438 Reporting definitions (planar); 3835 Thrust startup; 3855 Integrator; 3988 Event rules; 4198 Phases and events; 4381 Loss accounting; 4452 Ignition-after-release loss (exactness); 4513 Assist energy identity; 4568 Silo model (constant_accel, vertical) and every reported quantity; 4921 Hot start; 5022 Failed-ignition coast; 5179 Figures of merit in 1-D; 5329 Convergence; 5389 Experiment schema (planar); 5750 Assumptions; 6012 Calibration notes (build step 26); 6061 Phase 2 research notes (build step 27); 6082 SP1 research notes (step 9); 6163 Test-to-equation map (to the end).

The opening paragraph (3-24) lists the sections in order and ends "then every assumption
the code emits, collected in one list, and the test-to-equation map." It says each section
"names the module it describes, states its frame, units and assumptions, and points at the
test that validates it."

Place for "Display-only reconstructions (not part of the model)": a new `##` section at
line 6162, after "SP1 research notes" and directly before "Test-to-equation map". Reasons:
it keeps the section out of the model sections and out of "Assumptions" (which lists only
strings the run path emits); the map stays last and takes the new tests' rows; and of the
line numbers SP7's inventory cites (1986, 3220, 4513, 4568, 5750, 5963, 6082, 6163) only
6163 moves. The opening paragraph needs one clause for it.

## 8. What SP7 expects of SP2 (SP7 phase file, sections 4, 5.10, 6, 9)

1. SP7 uses nothing from SP2 (4.1).
2. These stay green and unchanged (4.3, 5.10): the 1-D golden tier; `tests/test_config_planar.py::test_shipped_planar_resolved_dicts_match_the_pinned_digests`; `tests/test_planar_pipeline.py::test_written_outputs_keep_the_captured_structure`; pad and silo_cold P* of 26,054.3962 and 27,553.2271 kg within 0.002 kg.
3. No resolved dict changes (5.10): "a default added to `ConstantAccelConfig` would change every resolved dict and break the digest pin"; a new field is left out of `model_dump` when unset.
4. SP1's solver and pipeline "as SP1 left them" (4.4): `OffloadProblem` and `planar_problem_factory` (offload.py 151, 256), `stage1_dry_mass_added_t` (config.py 1637), `cross_vehicle_decomposition` (compare.py 1534), the slow test `tests/test_offload.py::test_gate_silo_offload_recorded_run_and_verification` (795).
5. The run data stays on disk (4.5): `results/silo_offload_2d/20261003T112934Z` and `20261003T112949Z`. Both reference directories are present now (23 and 16 entries, metrics.json, no FAILED.txt).
6. SP7 expects SP2 to edit `plots.py`, `replay.py`, `cli.py` and add modules, and allows `config.py` (a display block) and `results_io.py` (a hook) (4.6). Its inventory (section 6) cites lines in config.py, sim.py, results_io.py, summary.py, compare.py, offload.py, vehicle.py, dynamics.py, phases/prelude.py, phases/engine.py, metrics.py and metrics_planar.py; SP2's close-out re-checks every line of any of these it touched.
7. The form shows the penalty field, not a structural model (section 2, out of scope): "SP2's app exposes the penalty field (D-SP1-04), not the structural model; adding it to the form is a backlog item".
8. SP7's demo uses `launchsim replay ... --out docs/demos/SP7/<name>.html` and says "`*_replay.html` is ignored at any depth unless SP1 or SP2 added `!docs/demos/**`" (section 9). SP2's `.gitignore` choice decides whether that sentence stays true.
9. Shipped experiment and vehicle files stay byte for byte; a new experiment file would have to be classified in `PLANAR_EXPERIMENTS`.
10. `linear_motor` and `cable_winch` are refused by config today (`PLANNED_MODELS`, config.py 78-79); SP7 replaces the first.

## 9. Where the phase file and HEAD disagree

The header diff (`git diff --stat b3150c1 HEAD -- src tests configs experiments pyproject.toml .gitignore site/build.py`)
lists exactly the four files the phase file says: site/build.py (+142), src/launchsim/plots.py
(+216), src/launchsim/replay.py (72 changed), tests/test_animate.py (+316). The phase
file's line numbers for those files are from b3150c1 and are stale at HEAD, as its own
header warns:

| Phase file | Says | HEAD |
|---|---|---|
| section 6, line 957 | tests/test_animate.py: 526 lines; helpers 46-146 (`_make_run_dir` 119); `test_calibration_record_matches_its_findings_note` 281; `test_custom_results_root_is_protected` 460 | 814 lines; helpers 55-162 (`_make_run_dir` 134); 299; 478; plus `_make_offload_run_dir` 549-636 and the offload tests from 644, which the row does not mention |
| section 6, line 926 | tests/test_animate.py uses at 185-193, 255, 295-329, 348-354, 466-467 | 203-211, 273, 313-347, 366-372, 484-485 (shifted by 18) |
| section 5.8 item 2 | `plots._results_tree` (809), `plots.check_animation_out` (843), `replay.results_ancestors` (1190), `replay.check_replay_out` (1224) | plots.py 962 and 996; replay.py 1188 and 1222 |
| section 5.8 item 3 | replay calls `plots._results_tree` (1069, 1205), `plots._is_inside` (1206); plots readers 579, 588; `run_events` (447); `plots._events` (635); `calibration_caveat` replay 664, plots 956 | replay.py 1067, 1203, 1204; plots.py 627, 636; replay.py 445; plots.py 683; replay.py 662, plots.py 1128 |
| section 5.8 item 5 | `replay.drive_caveat` (736) | replay.py 734 |
| section 5.9 | "`replay.py` is 1,246 lines at b3150c1" | 1,244 lines; plots.py is 1,881 |
| section 6, line 924 | replay.py uses plots names at 668-680, 1069, 1195, 1205, 1206, 1219 | 666, 1067, 1193, 1203, 1204, 1217 (103, 203, 214, 216 hold) |

Unchanged and confirmed: tests/test_replay.py (682 lines; every line the phase file cites),
cli.py 444, 446, 450, 480, 482, `src/launchsim/templates/replay.html:13`, pyproject.toml,
.gitignore, tests/test_offload_pipeline.py (2,374 lines).

Omissions, not contradictions: the phase file names README.md:37 and
docs/manual/02-quick-start.md as the places that say there is no interface; a third is
docs/manual/12-faq-glossary.md:85-89. It names the README's quick start and status;
README.md:372, 431, 444 and 447-448 need the same pass (447-448 is already false at HEAD).
It does not say how the deck PDF is made or which tool reads page state for exit
criterion 5; neither is recorded elsewhere in the repository.
