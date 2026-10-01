# Code survey: animate, replay, run data and what a launch scene needs

Read-only survey made in the SP1 planning session on 2026-09-30. Line numbers are for
commit 2eebcae; SP1 touches replay.py, metrics_planar.py, results_io.py and cli.py, so the
SP1 close-out re-checks this file's claims. Input to
docs/phases/SP2-launch-app-2d-scene.md. Paths are relative to the repository root.

## Summary of what matters for a scene

- There are three loaders today, plus a near-copy of the replay template in the probes
  folder:
  - animate's loader in `plots.py`
  - replay's loader in `replay.py`, which copies the JSON/YAML readers and reaches into
    private helpers in `plots.py`
  - the handoff prototype `prep_data.py`
- None of them carries the fields a scene needs: `pitch_rad` (attitude), `thrust_N` /
  `thrust_vac_N` (plume size), `stage`, the track columns, the per-run assist geometry,
  the vehicle masses.
- No vehicle or silo geometry is recorded anywhere. Only `reference_area_m2` = 10.52 m^2
  exists, which gives a 3.66 m diameter.
- Spent stage 1 and the fairing are not in the time series. Their separation state can be
  rebuilt from `events.csv`.
- Real 2-D data is on disk: `results/silo_screening_2d/20260930T175743Z` has 12 runs with
  CSVs.
- No new Python dependency is needed for the 2-D scene: matplotlib, Pillow (pulled in by
  matplotlib) and ffmpeg are all present. three.js would come from a CDN or a file
  vendored under `templates/`.

## 1. cli.py (src/launchsim/cli.py)

**How subcommands are registered**

- `build_parser()` (L56-147) calls
  `sub = parser.add_subparsers(dest="command", required=True)` (L63).
- Commands are dispatched through a dict in `main()` (L406-411):
  `{"run": command_run, "sweep": command_sweep, "animate": command_animate,
  "replay": command_replay}`.
- The module docstring (L11-17) lists the usage lines; a new command adds one there.

**`animate` arguments (L81-124)**

| Argument | Default |
|---|---|
| `run_dir` (positional) | - |
| `--runs NAME [NAME ...]` | None: baseline plus up to 3 variants |
| `--out PATH` | see below |
| `--fps N` (int) | `plots.ANIMATION_DEFAULT_FPS` = 30 |
| `--seconds S` (float) | 20.0 |
| `--width PX` (int) | 1280 |

**`replay` arguments (L126-146):** `run_dir`, `--runs NAME [NAME ...]`, `--out PATH`.

**`command_animate(args)` (L349-381)** runs these steps in order:
`plots.load_animation_runs` (validates the directory and run names);
`default_animation_path` or `--out`; `check_animation_out`; `animation_playback_fps`;
`animation_frame_count`; `frame_geometry`; prints `rendering ...`, then calls
`write_ascent_animation`. It catches `plots.AnimationError` and turns it into `CliError`.

**`command_replay(args)` (L384-397)** calls `replay.check_replay_run_dir`, then
`default_replay_path` (or `--out`), then `write_replay_page`. It catches `ReplayError` and
prints `replay: <path> (<n> KiB)`.

**Default output paths (never inside `results/`)**

- Animate: `./<experiment>_<timestamp>_animation.mp4`, or `.gif` when ffmpeg is missing.
- Replay: `./<experiment>_<timestamp>_replay.html`.
- If the current directory is inside a results tree, the file goes next to that tree
  instead.
- `.gitignore` already ignores `*_animation.mp4`, `*_animation.gif` and `*_replay.html`. A
  `*_scene.*` pattern would need adding.

**1-D runs**

- Both commands decide on `metrics.get("model") != PLANAR_2D`; a 1-D `metrics.json` has no
  `model` key.
- Animate: `plots.check_planar_run_dir` L584-603. Replay: `replay.check_replay_run_dir`
  L163-192.
- The message reads "`<dir> is a vertical_1d run; replay shows planar_2d runs only (a
  vertical_1d run has no downrange or flight-path angle to show)`".
- Replay also rejects a `metrics.json` without a `runs` dict, i.e. a sweep point.

**Exit codes (`main`, L400-419):** 0 success; 1 for `CliError` or `OSError`, printed as
one ASCII `error:` line via `say()`, with no traceback; 2 for an argparse usage error;
`--version` exits through `SystemExit(0)`.

## 2. replay.py in detail (src/launchsim/replay.py, 1161 lines)

**Run discovery and validation**

- `check_replay_run_dir(run_dir) -> dict` (L163). The directory must exist, have
  `metrics.json`, have `runs` as a dict, and have `model == "planar_2d"`.
- `select_runs(run_dir, runs) -> list[str]` (L195) reuses `plots.animation_run_names`:
  - plots.py L568-581: a run is any subdirectory holding `timeseries.csv`.
  - Order is the `metrics.json` run order, then the other folders sorted.
  - It rejects unknown names, repeated names, an empty selection, and more than
    `plots.ANIMATION_MAX_RUNS` (4).
- `run_source(metrics, config, name)` (L241) sorts each run into one of four roles: `run`,
  `bound`, `paired_baseline` or `case`. A folder that metrics.json does not describe
  raises an error.
- `read_series(run_dir, name) -> pd.DataFrame` (L306) requires `REPLAY_COLUMNS`, rejects
  an empty file, sorts on `t_rel_release_s`, and drops duplicate times with `keep="last"`
  (phase boundaries are written twice).

**What `replay.py` borrows from `plots.py`**

| Kind | Helper | Used at |
|---|---|---|
| Private | `plots._results_tree(run_dir)` (plots L780-790) | `source_text` L984, `protected_tree` L1120 |
| Private | `plots._is_inside(path, root)` (plots L793-795) | `protected_tree` L1121 |
| Public | `animation_run_names`, `ANIMATION_MAX_RUNS`, `ANIMATION_COLUMNS`, `CALIBRATION_RECORDS`, `RESULTS_TREE_NAME`, `plot_stem` | various |

**Duplicated readers**

- `replay._read_json` (L145) and `replay._read_yaml` (L154) are identical to
  `plots._read_json` (L550) and `plots._read_yaml` (L559). Both return `{}` when the file
  is missing.
- There is also a third YAML loader, `cli.load_yaml` (L177), which raises `CliError`
  instead.

**Other duplication between the two modules**

- `check_replay_run_dir` re-does `check_planar_run_dir` with a different error type (its
  docstring explains why).
- `calibration_caveat` exists in both: `replay.py` L593 and `plots.py` L927, with
  different wording.
- `run_events` (replay L386) duplicates `plots._events` (L606).
- **Rule mismatch:**
  - `plots._results_tree` matches the name `"results"` case-sensitively.
  - `replay.results_ancestors` (L1105) matches case-insensitively.
  - `replay.check_replay_out` (L1139) refuses output inside *any* folder named results.
  - `plots.check_animation_out` (L814) refuses only the run's own tree.

**How the payload is built: `replay_data(run_dir, runs) -> {"meta":..., "runs":[...]}`
(L1022)**

Columns: `REPLAY_COLUMNS = (*plots.ANIMATION_COLUMNS, "gamma_rel_rad", "mach")` (L99).
Fields (`SERIES_FIELDS`, L116-125):

| Page field | CSV column | Conversion | Decimals |
|---|---|---|---|
| `alt_m` | `alt_m` | - | 1 |
| `x_km` | `downrange_m` | m to km | 3 |
| `v` | `speed_rel_mps` | - | 2 |
| `gamma_deg` | `gamma_rel_rad` | `wrapped_deg`, to [-180, 180] | 2 |
| `m_t` | `m_kg` | kg to t | 3 |
| `g_ax` | `felt_axial_g` | - | 3 |
| `q_kpa` | `q_pa` | Pa to kPa | 3 |
| `mach` | `mach` | - | 3 |

Each run also gets `phase[]` (the phase of the last row at or before each sample) and
`t[]`.

- **Not embedded:** `pitch_rad`, `thrust_N`, `stage`, track columns. `test_replay.py` L306
  asserts `"pitch_deg" not in silo`.
- **Downsampling:** `replay_grid(t0_s, t1_s)` (L335) uses 0.1 s steps up to
  `REPLAY_EARLY_END_S` = 40 s after release, then 1 s steps, plus both endpoints. Values
  are interpolated linearly with `np.interp` (`series_values`, L356).
- **NaN to null:**
  - `defined_mask` (L346) gives null when either bracketing source sample is NaN (q and
    Mach in the vented shaft).
  - `_finite(value, decimals)` (L324) gives `None` for non-finite values and turns `-0.0`
    into `0.0`.
  - `embed_json` (L1083) uses `json.dumps(..., allow_nan=False, ensure_ascii=True)` and
    replaces every `<` with `<`.
- **Events:** `run_events(path, offset_s)` (L386) keeps *every* row as
  `{t (after release), name, stage, alt_m, x_km, v}`, with
  `offset_s = t_s[0] - t_rel_release_s[0]`.
- **Metrics per run:** `run_record` (L897-977) adds `payload_kg`, `payload_delta_kg`,
  `ideal_screening_kg`, `screening_yardstick_kg`, `upper_bound(+reasons)`, `max_q_kpa`,
  `peak_g_flight`, `losses_mps` (only if inserted), `exit_speed_mps`, `felt_g_track`,
  `push_s`, `start_alt_m` (assisted only), `pre_label` / `end_label`, `color` index, and
  `dashed` (step startup, the "yardstick" case).
- **Meta:** `experiment`, `timestamp`, `source`, `git`, `dirty`, `version`, `vehicle`,
  `baseline`, `orbit`; `subtitle`, `tags` (lat/az from `site`); `closeup_notes`,
  `results_notes`, `caveats`; `floors` (depth per silo or track start), `downrange_note`,
  `yardstick_shown_kg`.
- **Caveats (generated from the data):** `caveats()` (L761) combines `model_caveat`,
  `calibration_caveat` (from `plots.CALIBRATION_RECORDS`), `structure_caveat` (peak felt g
  plus the dry-mass slope from the sensitivity cases), `drive_caveat`,
  `upper_bound_caveat`, `comparison_caveats`, the yardstick note, and runs that did not
  reach orbit.
- **`CALIBRATION_RECORDS`** (plots L474-482):
  `{"generic_f9_class_2d": (26054.4, 22800.0, "docs/findings/CAL-f9-leo-2d")}`.
  `test_animate.py` L271 checks it against the findings note.

**How the payload is injected**

- `REPLAY_DATA_TOKEN = "__REPLAY_DATA__"` (L61). The template has
  `<script type="application/json" id="replay-data">__REPLAY_DATA__</script>` (L197).
- `render_page` (L1097) requires the token exactly once, then does a `str.replace`. The
  page reads it with `JSON.parse(document.getElementById("replay-data").textContent)`.
- The probe template used `__DATA__` instead.

**Output size** (measured on `silo_screening_2d/20260930T175743Z`): default 4 runs: page
300,810 bytes, of which 268,817 bytes are JSON; about 900-927 samples per run, 10-12
events per run.

**Template location and packaging**

- `REPLAY_TEMPLATE = ("templates", "replay.html")`; `load_template()` (L1091) calls
  `resources.files("launchsim").joinpath(*REPLAY_TEMPLATE).read_text("utf-8")`.
- `templates/` has no `__init__.py`.
- `pyproject.toml` has no `[tool.uv.build-backend]` section and no package-data setting.
  It relies on uv_build's default of putting the whole `src/launchsim` folder into the
  wheel.
- The development install is editable: `.venv/Lib/site-packages/launchsim.pth` points at
  `src`.
- `test_template_ships_as_package_data` only goes through the editable path, not a built
  wheel.

## 3. templates/replay.html (588 lines, src/launchsim/templates/replay.html)

**Page structure**

- Header (L133-137): `h1`, `#subtitle`, `#tags`.
- Transport panel (L139-158): `#play` button, `#clock`/`#clockSub`, a `#ticks` canvas over
  an `<input type=range id=scrub step=0.1>`, a `#rate` select (Auto, 1x, 5x, 20x, 60x) and
  `#chips` run toggles.
- `.main` grid: `#traj` canvas and the `#telemetry` cards.
- `.plots2` grid: `#closeup` canvas and strips `#s_v`, `#s_g`, `#s_q`.
- `#results` table, a `.caveats` list, and the `#foot` provenance line.

**Script**

- One `"use strict"` immediately-invoked function (L198-585). No ES modules and no
  libraries.
- Everything is drawn on `<canvas>` with 2D context; there is no SVG.

**JS functions**

| Group | Functions |
|---|---|
| Helpers | `esc`, `css`, `readPalette` (reads CSS variables into `PAL`), `idxAt` (binary search), `valAt(run, field, t)` (linear interpolation, null-aware), `phaseAt`, `fmt`, `orDash`, `qOr`, `clockText`, `signedKg`, `setupCanvas(cv)` (handles devicePixelRatio), `niceStep`, `niceMax`, `axes(ctx, box, xr, yr, ...)` returns `{sx, sy}`, `pathXY`, `pathTime`, `stroke`, `marker`, `shown`, `swatch` |
| Drawing | `drawTraj`, `drawCloseup`, `drawStrip(id, field, label, yr0)`, `drawTicks`, `telemetry`, `results`, `draw` |
| Playback | `currentRate`, `tick(ts)` (`requestAnimationFrame`), `setPlaying` |
| Wiring | `listItems`, `init` |

**How playback time is mapped (L509-515)**

- Auto mode: 1x while `tNow < 12` s, 5x up to 45 s, 30x after that.
- Each frame advances `tNow += dt_wall * rate`.
- Autoplay starts after 900 ms unless the user prefers reduced motion.
- Space bar toggles play.
- This is *not* animate's piecewise timeline (section 4).

**What the launch close-up draws today (`drawCloseup`, L370-411)**

- It is a chart of **altitude against time** from `min(-3, T_MIN-0.5)` to 30 s.
- The y range goes down to `-1.6 x deepest floor`.
- The shaft is just a filled band (`PAL.shaft`) from the ground down to the deepest floor.
- There is a ground line labelled "ground / silo mouth" (or "ground"), plus dashed floor
  lines labelled from `META.floors`.
- Each run has a faint full path, a bold trail and a circle marker, and there is a dashed
  cursor line.
- **No shaft walls, rings, carriage or vehicle shape are drawn.**
- `drawTraj` draws altitude against downrange on a flat axis, with dots for
  `MARK_EVENTS = ["propellant","fairing","cutoff","impact"]`.

**Theme and CSS**

- CSS custom properties: `--bg`, `--panel`, `--ink`/`-2`/`-3`, `--rule`, `--grid`,
  `--ground`, `--shaft`, `--run-0..3`, `--good`, `--bad`, `--caution(-bg)`, `--focus`.
- Dark mode works through `prefers-color-scheme` and a `:root[data-theme]` override.
- Fonts are Barlow Condensed, IBM Plex Sans and IBM Plex Mono **from Google Fonts**
  (L7-9), with local fallbacks. So the page is not fully offline today.
- A ResizeObserver, a MutationObserver on `data-theme`, and `document.fonts.ready` all
  trigger a redraw.

**Reusable for a scene as-is:** the playback clock, `tick`/`setPlaying`, the scrubber and
rate select, the chips, `valAt`/`idxAt`/`phaseAt`, `setupCanvas`, `readPalette`, the
telemetry cards (become the HUD), `results()`, the caveats list and footer, and the
`PHASE_NAME`/`EVENT_LABEL` maps.

## 4. plots.py `animate` (src/launchsim/plots.py)

**Frame-time mapping**

- `_timeline_knots` (L690) and `ascent_time_map(t_start_s, t_end_s, n_frames)` (L719).
- The video is split into segments:

| Flight time after release | Share of video | Speed |
|---|---|---|
| start to `TIMELINE_LAUNCH_END_S` = 3 s | 28% | about real time |
| 3 s to `TIMELINE_KNEE_S` = 30 s | 20% | faster |
| 30 s to the end | until 94% | fast |
| final hold | last 6% | holds the last state |

- `playback_speeds` (L731) gives the slope of each segment; `playback_label` (L744) prints
  "playback Nx real time (launch | close-up to T+30 s | fast forward | slow motion)".
- `animation_playback_fps` (L762) accounts for GIF frame delays coming in whole 10 ms
  steps (at most 50 fps).
- `frame_geometry(width_px)` (L838) makes a 16:9 frame with an even height and
  dpi = width / 10 in.

**Launch close-up (`_AscentFigure._close_axes`, L1184):** altitude on a symlog axis
(`CLOSEUP_LINTHRESH_M` = 100) against time up to 30 s; ground band (`axhspan`) with a
"below ground: assist shaft" note; `_hold_spans` (L1245) draws hatched hold-down spans;
trails, markers and a cursor; launch event labels are laid out in the ground band
(`_place_labels`, L1449). No vehicle drawing.

**Writer selection (`write_ascent_animation`, L1602-1664)**

- `.mp4` uses `FFMpegWriter(fps, codec="h264", extra_args=["-pix_fmt","yuv420p","-crf",
  "20","-movflags","+faststart"])`.
- Anything else uses `PillowWriter(fps)`.
- `with writer.saving(fig, out, dpi)` then, per frame, `draw_frame` and
  `grab_frame(facecolor="white")`.
- `CalledProcessError` and `BrokenPipeError` become `AnimationError`.
- `check_animation_out` requires `FFMpegWriter.isAvailable()` for `.mp4`.
- ffmpeg 8.1 is installed (WinGet); node is at `/c/nvm4w/nodejs/node`.

**Performance:** there is no blitting: the whole figure is redrawn every frame. README:
about 4 minutes for the 600-frame 1280 px MP4, under a minute for the 640 px GIF.
`docs/media` files: the MP4 is 1280x720, 30 fps, 600 frames, 805 KB; the GIF is 640x360,
189 frames, 2.66 MB.

**Reusable loader (built for animate)**

- `load_animation_runs(run_dir, runs) -> (list[AnimationRun], metrics)` (L665).
- `read_animation_run(run_dir, name, metrics) -> AnimationRun` (L633).
- `AnimationRun` (L499) is a frozen dataclass: `t_s`, `alt_m`, `downrange_m`,
  `speed_rel_mps`, `felt_axial_g`, `q_pa`, `m_kg`, `phase`, `events`, `payload_kg`,
  `status`, `baseline`.
- `_events` (L606) keeps only the event names in `EVENT_LABELS`.
- It does not read `pitch_rad`, thrust or track columns, and it reads `runs` only, so
  bounds and cases get no payload.

## 5. Columns, config fields, and what is on disk

**`timeseries.csv`** (`metrics_planar.PLANAR_TIMESERIES_COLUMNS`,
src/launchsim/metrics_planar.py L287-338; written by `results_io.write_csv` L472 with
`%.12g` floats)

| Column | Meaning and units |
|---|---|
| `t_s` | absolute time [s]; 0 at push start (silo) or at hold start/ignition (pad) |
| `t_rel_release_s` | time after release [s] |
| `phase` | HOLD, ASSIST, COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN, COAST |
| `stage` | stage1 / stage2 |
| `alt_m` | altitude [m]; -100 at the silo floor |
| `downrange_m` | Earth-fixed arc [m]; 0 during hold and track |
| `speed_rel_mps`, `speed_inertial_mps` | speeds [m/s] |
| `gamma_rel_rad` | flight-path angle [rad], unwrapped per run; a fall reads 3 pi/2 |
| `pitch_rad` | thrust direction above local horizontal [rad], unwrapped; pi/2 in HOLD; equals the track angle in ASSIST; along v_rel when unpowered |
| `psi_rad` | angle between thrust and v_rel [rad] |
| `m_kg` | mass [kg] |
| `thrust_N`, `thrust_vac_N`, `drag_N` | forces [N] |
| `q_pa`, `mach` | dynamic pressure [Pa], Mach; NaN on the track |
| `q_alpha_pa_rad` | q psi [Pa rad] |
| `felt_axial_g`, `felt_lateral_g` | felt loads [g0] |
| `J_vac_mps`, `J_grav_mps`, `J_alt_mps`, `J_drag_mps`, `J_steer_mps`, `J_bp_mps` | loss integrals [m/s] |
| `s_m`, `drive_force_N`, `interface_force_N`, `drive_power_W`, `track_normal_g_vehicle`, `track_normal_g_carriage` | track columns (`metrics.TRACK_COLUMNS`, `metrics.py` L60); NaN outside ASSIST |

- Sampling is every 0.05 s (`integrator.sample_dt_s`), about 10.8k rows and 3.6 MB per
  run.
- Phase counts for silo_cold: ASSIST 54, COAST_PRE_IGN 12, KICK 154, GRAVITY_TURN 2918,
  COAST_STAGING 222, LTG_BURN 7484.

**`events.csv`** (`PLANAR_EVENT_COLUMNS`, L369)

- Columns: `t_s` (absolute), `event`, `phase`, `stage`, `alt_m`, `downrange_m`,
  `speed_rel_mps`, `speed_inertial_mps`, `gamma_rel_rad` (unwrapped across the run's
  events), `m_kg`.
- Event names: push_start, ignition, ramp_end, release, liftoff (only when the hold is
  extended), kick_start, kick_end, propellant (MECO), staging, fairing, cutoff,
  ignition_failed, apex, impact, end.

**`resolved_config.yaml` fields**

- `runs.<name>.run` holds the run settings. Bounds are under `bound_runs.<name>.run` and
  cases under `cases.<name>.run`. A run with a different vehicle carries its own `vehicle`
  block.

| Field | Where | Value (silo_cold) |
|---|---|---|
| Site | `site.latitude_deg`, `site.azimuth_deg`, `site.include_rotation` | 28.5, 90, true |
| Assist model, net acceleration, stroke | `assist.model`, `assist.net_accel_g`, `assist.stroke_m` | constant_accel, 3.0, 100 |
| Carriage, braking, drive | `assist.carriage_mass_t`, `assist.brake_decel_g`, `assist.drive_efficiency`, `assist.exhaust_impingement_fraction`, `assist.shaft` | 0 (22 for silo_sled_22t), 5, 0.5, 0.0, vented |
| Track | `assist.track.angle_deg`, `assist.track.exit_altitude_m` | 90, 0 |
| Ignition | `ignition.stage1.{t_ign_s, reference}` | 0.5, release |
| Target orbit | `planar.target_orbit.{kind, altitude_km}` | circular, 200 |
| Stage masses | top-level `vehicle.stages[i].{dry_mass_t, propellant_mass_t, engine{count, thrust_vac_kN, thrust_sl_kN, isp_vac_s, exit_area_m2}, startup, coast_before_ignition_s}` | stage1 22.2 / 410.9 t; stage2 4.0 / 107.5 t, coast 11 s |
| Fairing, payload | `vehicle.fairing_mass_t`, `vehicle.fairing_drop.{trigger, limit_W_m2}`, `vehicle.payload_mass_t` | 1.7, free_molecular_heating at 1135, 22.8 |
| Reference area | `vehicle.aero.reference_area_m2` | 10.52, i.e. pi 3.66^2/4 per the source note |

**`metrics.json` fields** (`runs.<name>`, 150 keys). Times here are **after release**,
except `t_release_s`, which is absolute.

- Track and facility: `track_start_altitude_m` (-100), `exit_speed_mps` (76.7),
  `push_time_s` (2.607), `facility_length_m` (160 = stroke plus braking),
  `braking_distance_m` (60), `carriage_mass_kg`, `felt_g_track_peak`.
- Staging: `stage1_burnout_{t_s, alt_m, mass_kg, speed_mps}`,
  `meco_{downrange_m, gamma_rel_rad, speed_inertial_mps}`.
- Fairing: `fairing_{t_s, alt_m, drop}`.
- Other: `t_release_s`, `t_flight_start_s`, `hold_duration_s`, `kick_t_s`,
  `kick_duration_s`, `apogee_alt_m`, `perigee_alt_m`, `status`, `payload_kg`,
  `liftoff_mass_kg`.

**Results on disk (2026-09-30)**

| Directory | Run folders | With `timeseries.csv` | metrics.json |
|---|---|---|---|
| `calibration_f9_2d/20260930T100100Z` | 9 | 8 | yes |
| `calibration_f9_2d/20260930T173928Z` | 9 | 8 | yes |
| `guidance_trigger_2d/20260930T174950Z` | 2 | 1 | no |
| `silo_bridge_2d_readme/20260930T185034Z` | 5 | 4 | yes |
| `silo_screening_1d/...103623Z`, `...104503Z`, `...105657Z` | 11 each | 10 each | yes (1-D) |
| `silo_screening_1d/...103634Z`, `...104510Z`, `...105707Z` | 4 each | 1 each | no |
| **`silo_screening_2d/20260930T175743Z`** | 13 | **12** | yes, 1.84 MB |
| `silo_screening_2d/20260930T182453Z` | sweeps: baseline + sweep_1..3 | 1 | no top-level |

- In `20260930T175743Z`, each of these 12 has `timeseries.csv` and `events.csv`: pad,
  pad__aero_bound, pad_instant, silo_cold, silo_cold__aero_bound, silo_cold_lag,
  silo_failed (372 rows, impact), silo_hot_full, silo_hot_full_impinged,
  silo_hot_ramp_on_track, silo_instant, silo_sled_22t. The folder is 45 MB in total.
- Only `summary.md` files are tracked in git; the CSVs exist only on disk.

## 6. Vehicle geometry: confirmed absent

- In `configs/vehicles/*.yaml` and `src/launchsim/vehicle.py` there are no lengths,
  diameters, heights or fairing dimensions.
- The only size-like numbers: `aero.reference_area_m2` = 10.52 (diameter 3.66 m can be
  derived), `engine.exit_area_m2` = 8.6 (stage-2 vacuum nozzle, marked assumed), and
  `DragModel.reference_area_m2` (vehicle.py L406).
- Silo geometry is limited to `stroke_m`, `exit_altitude_m`, `angle_deg` = 90 (config.py
  `TrackConfig` L508), plus `braking_distance_m` / `facility_length_m`. Where the braking
  section sits is not modelled.
- So any scene geometry (stage lengths, ring pitch, carriage size) has to be a labelled
  display choice: a new config block or display constants.
- CLAUDE.md says "No magic numbers outside constants.py and configs" and never to edit
  the calibrated vehicle file.

## 7. Tests (tests/test_animate.py, tests/test_replay.py)

**Fixtures (both files)**

- A synthetic `results/<exp>/<ts>` is built under `tmp_path` by hand-written `_row` /
  `_write_run` / `_make_run_dir` with `csv.DictWriter`. No simulation and no search are
  run.
- `test_animate.py` L36-134: a push from -50 m or a hold, then an analytic climb, 0.5 s
  steps, ending at 80 s. `metrics.json` holds only `experiment`, `timestamp`, `git`,
  `baseline`, `runs`. The vehicle is `toy_2d`.
- `test_replay.py` L44-253 is richer: a NaN q/Mach shaft, NaN and Infinity losses, a bound
  plus its paired baseline, a case with its own vehicle and orbit, dry-mass sensitivity
  cases, a carriage, and impingement.

**No test is marked `slow`.** `node --check` of the inline script is skipped when node is
missing. There is no `test_*plots*` file.

**What `test_animate.py` asserts:** GIF frame count, total duration and size (320x180);
the results tree is left untouched; default path, including from inside the tree; output
inside results or with a bad extension is refused; `.mp4` without ffmpeg is a clear
error; vertical_1d gives exit 1 with no traceback; unknown runs are named; default
selection (baseline plus 3); events on the time after release; caveats;
`CALIBRATION_RECORDS` matches the findings note; the timeline is monotone with about 1x
launch speed and the end hold; playback labels, GIF fps, readout name cutting, event label
text, hidden markers before a run starts; a custom results root is protected; an ffmpeg
stand-in failure gives one error line; help metavars; frame geometry.

**What `test_replay.py` asserts:** the embedded JSON parses strictly (`parse_constant`
rejects NaN); the page is ASCII; events and the shaft's null q survive; colours, floors,
run selection and generated text; calibration caveat is conditional on the vehicle;
`embed_json` escaping; template ships as package data; default and refused output paths,
including in any results tree; vertical_1d and sweep-point rejection; bound and case
metrics; failed run has no losses; grid steps and interpolation; wrapped gamma; caveat
slopes and upper-bound reasons; carriage and impingement detail; template string checks
(L521-526); too many or repeated runs; inline JavaScript is valid.

## 8. Handoff probes and docs/media

**docs/findings/probes/handoff-2026-09-30/** (all tracked in git; excluded from ruff)

- `template.html` (516 lines) is the prototype the packaged template was ported from. Same
  layout and nearly the same function set. The packaged version adds `esc`, `listItems`,
  `niceMax`, `signedKg`, `swatch`. Its placeholder is `__DATA__`; its caveats are
  hard-coded.
- `prep_data.py` hard-codes the run directory, 4 runs and their labels. Same grid and null
  logic as `replay.py`, but it *does* emit `pitch_deg`. It writes `replay_data.json` next
  to itself.
- Also present: `probe_ign_table.py/.out`, `probe_offload.py/.out`,
  `probe_resolve.py/.out`.
- The first handoff (archived under docs/handoff/archive/) section 4.6 sketches the scene
  data plan: a curved-Earth placement at angle downrange/R_E, attitude from pitch, and a
  site longitude of -80.6 deg as a display choice.

**docs/media/:** `ascent_pad_vs_silo_cold_2d.mp4` (805 KB, 1280x720) and `.gif` (2.66 MB,
640x360), both produced by `launchsim animate --runs pad silo_cold` and referenced in the
README.

## 9. pyproject.toml

- **Dependencies:** numpy>=2.3, scipy>=1.16, pandas>=3.0, matplotlib>=3.10,
  pydantic>=2.11, pyyaml>=6.0.2, ambiance>=1.3.1,<2.
- **Dev:** `[project.optional-dependencies] dev = ["pytest>=9.0", "ruff>=0.16"]`, and
  `[dependency-groups] dev = ["launchsim[dev]"]`.
- **Pillow** is not declared; it arrives through matplotlib (12.3.0 installed), but
  `test_animate.py` imports `PIL` directly.
- **Build:** `uv_build>=0.12.13,<0.13`, with no package-data configuration.
- **Script:** `launchsim = "launchsim.cli:main"`.
- **ruff:** `target-version py312`, `line-length 100`,
  `extend-exclude ["*.md","notebooks","docs/findings/probes"]`, select
  `E,F,I,UP,B,NPY,RUF`, ignore `RUF001-003`, format `line-ending = "lf"`.
- **pytest:** `testpaths=["tests"]`, `addopts="-ra --strict-markers"`,
  `markers=["slow: slower than 5 s"]`, `filterwarnings=["error"]`.
- **JS tooling:** none (no `package.json`, no bundler). three.js would come either from a
  CDN `<script type="importmap">`/module, which matches the existing Google Fonts external
  link, or as a vendored `three.module.min.js` under `templates/`, which uv_build's
  default would ship. CLAUDE.md requires a one-line justification for any new dependency.

## 10. Objects after separation

**The time series is one body only.** After staging, the rows carry `stage=stage2` and the
stack mass; there are no columns for the spent stage or the fairing.
`map_staging_planar` (`phases/planar.py` L446) and `map_fairing_planar` (L470) only
subtract mass. Their docstrings say r, theta, v_r and v_theta are unchanged: an
instantaneous, impulse-free separation.

**What the event rows contain** (pad run)

```
151.328437545,propellant,GRAVITY_TURN,stage1,69485.82,99171.02,2665.03,3049.68,0.401236,161454.396
151.328437545,staging,COAST_STAGING,stage2,69485.82,99171.02,2665.03,3049.68,0.401236,139254.396
196.807530921,fairing,LTG_BURN,stage2,110483.04,212323.82,2766.55,3167.08,0.291558,129343.226
```

- **staging** is logged *after* the drop (`_stage_and_coast` L1580-1581): stage2,
  post-drop mass. The dropped stage-1 mass = propellant row `m_kg` minus staging row
  `m_kg` = 22,200 kg, which equals `stage1.dry_mass_t`.
- **fairing** in LTG_BURN is logged by `_integrate` (L1311) with the event state *before*
  `map_fairing_planar` (L1271), so its `m_kg` still includes the 1.7 t fairing.
- **The mass convention is inconsistent across fairing cases:**

| Fairing case | Logged at | Mass in the row |
|---|---|---|
| Dropped at stage-2 ignition | L1253 | before the drop |
| Dropped at staging (heating criterion already met) | L1583 | after both drops |

**Rebuilding the separation state** (the rows have no r, theta, v_r, v_theta or pitch)

- `r = R_E + alt_m`, with `r_datum = R_E = 6,378,137 m`.
- `v_r = V_rel sin(gamma)`, `u = V_rel cos(gamma)`, `v_theta = u + omega_p r`, where
  `omega_p = omega_E cos(lat) sin(az)`.
- `theta = downrange/R_E + omega_p (t - t_fs)` (`PlanarView.row`, L229-250).
- Check: `hypot(v_r, v_theta)` should match `speed_inertial_mps`. It does for the pad
  staging row (about 3049 against 3049.68).
- Ballistic propagation of the dropped stage needs its own drag assumptions; that is
  display-only.

**Carriage after release:** not recorded. It stays in the facility; only
`braking_distance_m` (60 m at 5 g) is given.

## Recommendation: how to organise the scene code

1. **A new module `src/launchsim/scene.py` (I/O) with its own `templates/scene.html`;
   don't extend `replay.py`.** `replay.py` is already 1161 lines and mostly caveat and
   results-table text. A scene needs other data (pitch, thrust, stage, track columns,
   assist geometry, vehicle masses, reconstructed separation states) and a different
   renderer. CLAUDE.md lists the modules allowed to do I/O; `scene.py` (and any new data
   module) must be added there and to the layout list.
2. **Pull the shared run-directory loading into a new module, e.g.
   `src/launchsim/run_data.py` (I/O, read-only).** This is better than putting it in
   `results_io.py`, which is the writer side and imports `compare`, `summary` and `plots`.
   Move into it:
   - one `read_json`/`read_yaml` pair, replacing the four copies
   - `results_tree`/`is_inside`/`protected_tree`/`default_output_path(run_dir, cwd,
     suffix)`/`check_output`, using replay's stricter case-insensitive "any results tree"
     rule for all three commands
   - `check_planar_dir` with a configurable error type
   - `animation_run_names`/`select_runs`, `run_source`, `read_series`, `read_events` (all
     rows plus pre/post mass), `CALIBRATION_RECORDS` and `calibration_caveat`

   `plots.py` and `replay.py` would then import public names instead of
   `plots._results_tree` / `plots._is_inside`. The existing tests already cover this
   behaviour.
3. **Keep the payload pattern** (`embed_json`, a single token, `allow_nan=False`, `<`
   escaped), but under a new token such as `__SCENE_DATA__`. Factor the grid and
   `series_values` resampling into the shared module and pass the field list in, so the
   scene can add `pitch_deg`, `thrust_frac`, `stage` and `s_m`. Pull the reusable JS parts
   of `replay.html` (clock, `tick`, scrubber, chips, `valAt`, `setupCanvas`, palette, HUD
   cards, caveats footer) into a shared template fragment, or copy them deliberately;
   don't let the two pages drift.
4. **Put display geometry in a labelled config block or display constants marked as
   assumed**, never in the vehicle file: stage lengths, fairing length, ring spacing,
   carriage size, braking-section placement.
5. **Ballistic paths for the dropped stage and fairing go in a pure function** (in
   `scene.py` or the data module), seeded from the rebuilt event state above. Label them
   display-only in the page's caveats, because the simulator does not model them.
6. **Tests:** copy the synthetic-directory fixture pattern from `test_replay.py` (fast, no
   slow marker). Assert strict JSON, nulls in the shaft, pitch and thrust present,
   staging-state reconstruction against `speed_inertial_mps`, refused output paths, 1-D
   rejection, and a `node --check` of the inline script.

## App decisions already taken (2026-09-30, user)

- The visual tool is a local app first: a form (depth, ramp start, fuel offload), a Launch
  button, scenes rendered inside it.
- Planned route, to confirm in SP2's Plan mode: `launchsim app` bound to 127.0.0.1 on
  Python's standard-library HTTP server (no new dependency); the same resolve and run path
  as the CLI in a worker; a normal results directory per launch; the pad baseline cached;
  app runs labelled exploratory (not pre-registered).
