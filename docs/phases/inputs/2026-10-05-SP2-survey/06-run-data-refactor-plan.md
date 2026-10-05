Provenance: SP2 step A0 survey 06 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/06-run-data-refactor-plan.md); a record, not edited (README.md).

# 06 - Move plan for step A1: `src/launchsim/run_data.py`

Surveyed at HEAD b69ff0c (clean tree), 2026-10-05. Read-only: no repository file was
created or changed, nothing was written under results/, pytest was not run. Scratch
scripts are next to this file (`s06_*.py`); the two generated pages
(`s06_reference_replay_cli.html`, `s06_reference_replay_inprocess.html`) are in the
scratchpad only.

File sizes at HEAD: plots.py 1,881 lines, replay.py 1,244, cli.py 510,
tests/test_animate.py 814, tests/test_replay.py 682, tests/test_offload_pipeline.py 2,374.

## 0. Facts measured in this survey

| Fact | Value | How |
|---|---|---|
| Reference page (`results/silo_screening_2d/20260930T175743Z`, runs pad, silo_cold, silo_hot_ramp_on_track, silo_failed) | 247,949 bytes, sha256 `3ca23dc5ce6532e6b9e3fd4656ab4846bcb4cdddfced7a077ce05c9411fd1eab` | the phase file's CLI command with `--out` in the scratchpad, and in memory (`replay.render_page(replay.replay_data(...))`); two processes, same hash. Equal to the b3150c1 value in the phase file, so SP1 steps 10a and later did not move this page |
| Build time of that page | 0.25 s | in memory |
| `-0.0` tokens in the page's JSON | 6, all in event `x_km`: pad `kick_start`; silo_cold `ignition`, `kick_start`; silo_failed `apex`, `impact`, `end` | `s06_reference_page.py` |
| Roles on the reference page | four `run` roles only (no bound, paired baseline, case or offload run) | `s06_gate_pages.py` |
| Fairing cases on disk | 55 planar run folders in 6 experiment directories and 55 planar sweep-point folders (9 + 21 + 25 in three sweep directories): all `fairing_drop` = "in the stage-2 burn (heating event)" with a `fairing` row in LTG_BURN; `silo_failed`: `fairing_drop` null, no staging and no fairing row. No recorded run of any model shows the fairing leaving at stage-2 ignition or at staging | `s06_fairing_survey.py` |
| Drop-mass rule checked on the 56 planar run folders (23 with their own vehicle block) | staging row mass + stage-1 dry mass = `propellant` row mass to 2.9e-11 kg; fairing row mass - fairing mass = first series row after the drop to 1.5e-11 kg; every vehicle block validates with `config.VehicleConfig.model_validate` | `s06_drop_masses.py` |
| Animate path tests under replay's rule | all hold (table in section 2.4) | `s06_path_rules.py` |
| Import cost (one run each, other work on the machine) | `launchsim.metrics_planar` 1.8 s (no matplotlib), `launchsim.plots` 2.6 s, `launchsim.replay` 3.3 s (matplotlib through plots) | `python -c` timing |

## 0.1 Where the phase file and HEAD disagree

Line numbers of plots.py, replay.py and tests/test_animate.py in sections 5.2, 5.8 and 6
of the phase file are those of b3150c1; SP1 step 10a moved them. cli.py, results_io.py,
phases/planar.py, metrics_planar.py and tests/test_replay.py are unchanged since b3150c1
(`git diff --stat b3150c1 HEAD` is empty for them) and their numbers hold, except
`_resolved_config_dict`, which is at results_io.py 590, not 588.

| Phase file | HEAD |
|---|---|
| plots.py 1,701 lines | 1,881 |
| `AnimationError` 309, `ANIMATION_MAX_RUNS` 321, `RESULTS_TREE_NAME` 344 | 312, 324, 347 |
| `CALIBRATION_RECORDS` 474-487; band constants 488, 492, 497; `calibration_gap` 501; `inside_calibration_band` 508 | 507-520; 521, 525, 530; 534; 541 |
| `AnimationRun` 528, `ANIMATION_COLUMNS` 565 | 574, 613 |
| plots `_read_json` 579, `_read_yaml` 588 | 627, 636 |
| `animation_run_names` 597, `check_planar_run_dir` 613 | 645, 661 |
| `_events` 635, `read_animation_run` 662, `load_animation_runs` 694 | 683, 813, 847 |
| `ascent_time_map` 748 | 901 |
| `_results_tree` 809, `_is_inside` 822 | 962, 975 |
| `default_animation_path` 827, `check_animation_out` 843, `frame_geometry` 867 | 980, 996, 1020 |
| plots `calibration_caveat` 956 | 1128 |
| `_AscentFigure` 1041, `write_ascent_animation` 1639-1701 | 1213, 1818-1881 |
| replay.py 1,246 lines | 1,244 |
| `read_series` 367, `_finite` 385, `replay_grid` 396, `defined_mask` 407, `series_values` 417, `run_series` 432, `run_events` 447 | 365, 383, 394, 405, 415, 430, 445 |
| `push_accel_g` 521, `assist_text` 531 | 519, 529 |
| replay `calibration_caveat` 664, `drive_caveat` 736 (sentence at 763), `caveats` 845 | 662, 734 (761), 843 |
| `run_record` 982-1062, `source_text` 1065, `replay_data` 1107 | 980-1060, 1063, 1105 |
| `embed_json` 1168, `load_template` 1176, `render_page` 1182 | 1166, 1174, 1180 |
| `results_ancestors` 1190, `protected_tree` 1199, `default_replay_path` 1211, `check_replay_out` 1224, `write_replay_page` 1239 | 1188, 1197, 1209, 1222, 1237 |
| `plots._results_tree` used at replay 1069, 1205; `plots._is_inside` at 1206 | 1067, 1203; 1204 |
| replay's uses of plots names: 103; 203, 214, 216; 668, 675, 677, 680; 1069, 1195, 1205, 1206; 1219 | 103; 203, 214, 216; 666, 673, 675, 678; 1067, 1193, 1203, 1204; 1217; and, not listed at all, 330, 334, 339, 344 (`plots.offload_role`, `OFFLOAD_PAIRED_PAD`, `OFFLOAD_PAD_CONTROL`, `OFFLOAD_SOLVED_KIND`) |
| tests/test_animate.py 526 lines; path tests 180-195 and 460-468; `mp.setattr` at 353; findings-note test 281; `_make_run_dir` 119 | 814 lines; 198-238 and 478-486; 371 (test at 355); 299; 134 |

New in plots.py since the inventory (step 10a), none of them in the phase file:
`OFFLOAD_CASE`, `OFFLOAD_PAIRED_PAD`, `OFFLOAD_PAD_CONTROL` (488-490),
`OFFLOAD_SOLVED_KIND` (495), `NEAR_ORBIT_PHASE` (498), `LEGEND_TITLE` (503), `OffloadTag`
(560-570), `_as_dict` (710), `_finite_kg` (715), `offload_role` (722), `offload_tag`
(740), `animation_record` (795), `legend_title` (1118), and the `offload` field of
`AnimationRun` (595).

## 1. Inventory and destinations

Destination codes: **MOVE** = body moves to `run_data`, the old name stays importable as
a plain re-export (same object). **WRAP** = the logic moves, the old name stays as a
thin function in its module that calls `run_data` with its own error type and wording.
**STAY** = unchanged in its module (may read moved names). **MERGE** = one `run_data`
function replaces two copies.

### 1.1 plots.py

| Symbol | Lines | Signature / value | Depends on | Called by | Destination |
|---|---|---|---|---|---|
| `plot_stem`, `PLOT_STEM_UNSAFE` | 93-96, 90 | `plot_stem(prefix: str, quantity: str) -> str` | `re` | `write_plots` 172, `write_planar_plots` 295, `default_animation_path` 990, `replay.default_replay_path` 1217; re-exported by sim.py 212, 218 | STAY (see 1.3: `default_output_path` takes the file name, so run_data does not need it). Alternative: MOVE and re-export, which lets replay.py drop `import plots` altogether |
| `AnimationError` | 312-315 | `class AnimationError(ValueError)` | - | 12 `pytest.raises` in test_animate; cli 469 | STAY, rebased: `class AnimationError(RunDataError)` |
| `ANIMATION_MAX_RUNS`, `ANIMATION_DEFAULT_VARIANTS` | 324, 325 | 4, 3 | - | `animation_run_names`, `load_animation_runs`; replay 214, 216 | MOVE as `MAX_RUNS`, `DEFAULT_VARIANTS`; re-export under the old names |
| `RESULTS_TREE_NAME` | 347 | `"results"` | - | `_results_tree` 969; replay 1193 | MOVE; re-export. (`cli.RESULTS_DIR_NAME`, cli.py 47, is a third copy of the string on the writer side; leave it) |
| `EVENT_LABELS`, `PHASE_LABELS` | 460-471, 475-485 | drawing labels | phase constants | `_events`, `_phase_at` | STAY |
| `OFFLOAD_CASE`, `OFFLOAD_PAIRED_PAD`, `OFFLOAD_PAD_CONTROL`, `OFFLOAD_SOLVED_KIND` | 488-490, 495 | `"offload case"`, `"paired pad"`, `"pad control"`, `"solve"` | - | `offload_role`, `offload_tag`; replay 334, 339, 344; test_animate 660, 661, 693, 729 | MOVE; re-export from plots |
| `NEAR_ORBIT_PHASE`, `LEGEND_TITLE` | 498, 503 | labels | - | animate only | STAY |
| `CALIBRATION_RECORDS` | 507-520 | `dict[str, tuple[float, float, str]]`, two vehicles | - | `plots.calibration_caveat` 1135; replay 666; results_io 143, 1798; tests (12 uses) | MOVE; re-export from plots (results_io keeps its import) |
| `CALIBRATION_BAND`, `CALIBRATION_BAND_EDGE_REL_TOL`, `CALIBRATION_GATE_VEHICLE` | 521, 525, 530 | 0.10, 1e-12, `"generic_f9_class_2d"` | - | both caveats, `inside_calibration_band` | MOVE; re-export |
| `calibration_gap`, `inside_calibration_band` | 534-538, 541-544 | `(model_kg: float, reference_kg: float) -> float`; `(gap: float) -> bool` | the band constants | plots 1139, 1144; replay 673, 678; test_animate 366, 368 | MOVE; re-export |
| `AnimationEvent`, `OffloadTag`, `AnimationRun` | 547-557, 560-570, 573-610 | frozen dataclasses | - | animate | STAY |
| `ANIMATION_COLUMNS` | 613-623 | `("t_s","t_rel_release_s","phase","alt_m","downrange_m","speed_rel_mps","felt_axial_g","q_pa","m_kg")` | - | `read_animation_run` 820; replay 103; test_animate 36 | MOVE as `PLANAR_BASE_COLUMNS` (same tuple, same order); re-export under the old name |
| `_read_json`, `_read_yaml` | 627-633, 636-642 | `(path: Path) -> dict[str, Any]` | json, yaml | `animation_run_names` 650, `check_planar_run_dir` 667, `default_animation_path` 984; `write_ascent_animation` 1863 | MERGE with replay's copies into `run_data.read_json` / `read_yaml`; no test uses the private names, so no alias is needed |
| `animation_run_names` | 645-658 | `(run_dir: Path) -> tuple[list[str], list[str]]` | `_read_json`, `ANIMATION_DEFAULT_VARIANTS` | `load_animation_runs` 854; replay 203; test_animate 273 | MOVE as `run_names`; re-export under the old name |
| `check_planar_run_dir` | 661-680 | `(run_dir: Path) -> dict[str, Any]` | `_read_json`, `PLANAR_2D`, `VERTICAL_1D`, `AnimationError` | `load_animation_runs` 853 only | WRAP over `run_data.check_run_dir` (MERGE with `check_replay_run_dir`) |
| `_events` | 683-707 | `(path: Path, offset_s: float) -> tuple[AnimationEvent, ...]` | pandas, `EVENT_LABELS` | `read_animation_run` 839 | WRAP: a projection of `run_data.read_events` (recorded rows whose name is in `EVENT_LABELS`) to `AnimationEvent` |
| `_as_dict` | 710-712 | `(value: Any) -> dict[str, Any]` | - | `offload_role`, `animation_record`, `legend_title` | MERGE with `replay._mapping` into `run_data.as_mapping` |
| `_finite_kg` | 715-719 | `(value: Any) -> float \| None` | math | `offload_tag` | STAY (differs from `replay._finite`: no numpy numbers, no rounding, keeps -0.0; merging is optional and not needed for A1) |
| `offload_role` | 722-737 | `(offload: Mapping[str, Any], name: str) -> tuple[str, dict[str, Any]] \| None` | `_as_dict`, `OFFLOAD_*` | `offload_tag` 757; replay 330 | MOVE; re-export from plots |
| `offload_tag`, `animation_record`, `legend_title` | 740-792, 795-810, 1118-1125 | animate's labels from metrics.json | `offload_role`, `_finite_kg`, `NO_OFFLOAD_STATUS` | animate; tests | STAY |
| `read_animation_run` | 813-844 | `(run_dir: Path, name: str, metrics: dict[str, Any]) -> AnimationRun` | pandas, `ANIMATION_COLUMNS`, `_events`, `animation_record` | `load_animation_runs` 869 | STAY; its CSV read and two checks call `run_data.read_series_frame(..., error=AnimationError)`. It must not use replay's sort and de-duplication (section 2.2) |
| `load_animation_runs` | 847-869 | `(run_dir: Path, runs: Sequence[str] \| None) -> tuple[list[AnimationRun], dict[str, Any]]` | the two above, selection | `write_ascent_animation` 1853; cli 444; 8 test uses | STAY; its selection block (854-868) becomes `run_data.select_runs(run_dir, runs, what="animation", error=AnimationError)` |
| `_results_tree` | 962-972 | `(run_dir: Path) -> Path` | `RESULTS_TREE_NAME` | 991, 1006; replay 1067, 1203 | MOVE as `results_tree` (verbatim, case-sensitive; section 2.4) |
| `_is_inside` | 975-977 | `(path: Path, root: Path) -> bool` | - | 992, 1006; replay 1204 | MOVE as `is_inside` |
| `default_animation_path` | 980-993 | `(run_dir: Path, cwd: Path, *, ffmpeg: bool \| None = None) -> Path` | `_read_json`, `FFMpegWriter.isAvailable`, `plot_stem`, `_results_tree` | `write_ascent_animation` 1854; cli 446; test_animate 203, 206, 211, 485 | WRAP: keeps the ffmpeg question and the name; folder from `run_data.default_output_path` (the stricter rule: a behaviour change, section 2.4) |
| `check_animation_out` | 996-1017 | `(out_path: Path, run_dir: Path) -> None` | `ANIMATION_FORMATS`, `_results_tree`, `FFMpegWriter` | `write_ascent_animation` 1855; cli 450; test_animate 484 | WRAP: suffix check and ffmpeg check stay; tree and folder checks from run_data |
| `calibration_caveat` | 1128-1146 | `(vehicle_name: str \| None) -> str` | the plots global `CALIBRATION_RECORDS` | `animation_caveats` 1161; test_animate 335-343, 372 | STAY, reading the plots-module name at call time (section 4) |
| `write_ascent_animation` | 1818-1881 | unchanged | `_read_yaml` 1863 | cli 461; tests | STAY; 1863 calls `run_data.read_yaml` |

### 1.2 replay.py

| Symbol | Lines | Signature / value | Depends on | Called by | Destination |
|---|---|---|---|---|---|
| `ReplayError` | 57-59 | `class ReplayError(ValueError)` | - | 5 `pytest.raises`; cli 485 | STAY, rebased on `RunDataError` |
| `REPLAY_EARLY_END_S`, `REPLAY_EARLY_DT_S`, `REPLAY_LATE_DT_S`, `REPLAY_GRID_DECIMALS`, `REPLAY_TIME_DECIMALS` | 68, 70, 72, 74, 77 | 40.0, 0.1, 1.0, 6, 3 | - | `replay_grid`, `run_series`, `run_events`; test_replay 486-489 | MOVE as `GRID_*`, `TIME_DECIMALS`; re-export under the old names |
| `ROLE_RUN`, `ROLE_BOUND`, `ROLE_PAIRED_BASELINE`, `ROLE_CASE`, `ROLE_OFFLOAD` | 93-97 | `"run"`, `"bound"`, `"paired_baseline"`, `"case"`, `"offload"` | - | `run_source`, `ROLE_LABELS`, `comparison_caveats`; tests | MOVE; re-export |
| `REPLAY_COLUMNS` | 102-106 | `(*plots.ANIMATION_COLUMNS, "gamma_rel_rad", "mach")` | plots | `read_series`; test_replay 40, test_offload_pipeline 973 | STAY, built from `run_data.PLANAR_BASE_COLUMNS`; content and order must not change (the tests build their CSV fixtures from it) |
| `wrapped_deg`, `Converter` | 110-113, 116 | `(angle_rad: np.ndarray) -> np.ndarray` | numpy, `rad_to_deg` | `SERIES_FIELDS`; test_replay 501, 505 | MOVE; re-export (the scene needs it for pitch) |
| `SERIES_FIELDS` | 119-128 | eight `(field, column, convert, decimals)` tuples | converters | `run_series`; test_replay 504 | STAY (it is the replay page's field list; `run_data.run_series` takes the list) |
| `_read_json`, `_read_yaml` | 148-154, 157-163 | `(path: Path) -> dict[str, Any]` | json, yaml | 176, 1213; 1110 | MERGE (see plots) |
| `check_replay_run_dir` | 166-195 | `(run_dir: Path) -> dict[str, Any]` | `_read_json`, model names | `replay_data` 1108; cli 480 | WRAP over `run_data.check_run_dir(..., verb="replay shows", error=ReplayError)` |
| `select_runs` | 198-218 | `(run_dir: Path, runs: Sequence[str] \| None) -> list[str]` | `plots.animation_run_names`, `plots.ANIMATION_MAX_RUNS` | `replay_data` 1109 | WRAP over `run_data.select_runs(..., what="replay", error=ReplayError)` (MERGE with plots 854-868) |
| `_mapping` | 221-223 | `(value: Any) -> dict[str, Any]` | - | 20+ uses in replay | MERGE into `run_data.as_mapping`; replay imports it as `_mapping` |
| `_entry_config` | 226-229 | `(entry: Any) -> tuple[dict[str, Any], str \| None]` | `_mapping` | `run_source`, `replay_data` 1113 | MOVE as `entry_config`; replay imports it as `_entry_config` |
| `overrides_text` | 232-241 | `(overrides: Mapping[str, Any]) -> str` | - | `run_source` 269 | MOVE with `run_source`; re-export |
| `run_source` | 244-319 | `(metrics: dict[str, Any], config: dict[str, Any], name: str) -> dict[str, Any]` | roles, `_entry_config`, `overrides_text`, `offload_note` | `replay_data` 1111; test_offload_pipeline 1087, 1095, 1096 (three positional arguments) | WRAP (it raises: 316-319 "describes it nowhere"); logic in `run_data.run_source(metrics, config, name, *, error=RunDataError)` |
| `offload_note` | 322-362 | `(offload: Mapping[str, Any], name: str, baseline: str) -> str` | `_finite`, `plots.offload_role`, `plots.OFFLOAD_*`, `kg_to_t`, `to_percent` | `run_source` 314 | MOVE; re-export |
| `read_series` | 365-377 | `(run_dir: Path, name: str) -> pd.DataFrame` | pandas, `REPLAY_COLUMNS` | `run_record` 993 | WRAP over `run_data.read_series(run_dir, name, REPLAY_COLUMNS, error=ReplayError)` |
| `_finite` | 383-391 | `(value: Any, decimals: int \| None = None) -> float \| None` | math, numpy | 30+ uses; test_replay 506 | MOVE as `finite`; replay imports it as `_finite` (the test calls the private name) |
| `replay_grid` | 394-402 | `(t0_s: float, t1_s: float) -> np.ndarray` | the grid constants | `run_series` 434; test_replay 483 | MOVE as `sample_grid` (verbatim); re-export as `replay_grid` |
| `defined_mask`, `series_values` | 405-412, 415-427 | `(t_s, values, grid) -> list[bool]`; `(t_s, values, grid, decimals) -> list[float \| None]` | numpy | `series_values` 420; `run_series` 439 | MOVE; re-export |
| `run_series` | 430-442 | `(frame: pd.DataFrame) -> dict[str, Any]` | grid, `SERIES_FIELDS`, `REPLAY_TIME_DECIMALS` | `run_record` 1023 | WRAP: `run_data.run_series(frame, SERIES_FIELDS)`; key order "t", the fields in list order, "phase" |
| `run_events` | 445-464 | `(path: Path, offset_s: float) -> list[dict[str, Any]]` | pandas, `_finite`, `m_to_km` | `run_record` 1024 | WRAP: a projection of `run_data.read_events` to the six keys with today's rounding (section 6, item 1) |
| `calibration_caveat` | 662-685 | `(vehicle: str) -> str` | `plots.CALIBRATION_*`, `plots.calibration_gap`, `plots.inside_calibration_band` | `caveats` 854; test_replay 336-357 | STAY; reads the run_data names |
| `source_text` | 1063-1071 | `(run_dir: Path) -> str` | `plots._results_tree` 1067 | `replay_data` 1144 | STAY, calling `run_data.results_tree` (the run's own tree, not `protected_tree`) |
| `results_ancestors` | 1188-1194 | `(path: Path) -> list[Path]` | `plots.RESULTS_TREE_NAME` | `protected_tree` 1202 | MOVE; re-export |
| `protected_tree` | 1197-1206 | `(path: Path, run_dir: Path) -> Path \| None` | `results_ancestors`, `plots._results_tree` 1203, `plots._is_inside` 1204 | 1218, 1228 | MOVE; re-export |
| `default_replay_path` | 1209-1219 | `(run_dir: Path, cwd: Path) -> Path` | `_read_json`, `plots.plot_stem` 1217, `protected_tree` | cli 482; test_replay 381, 622, 625 | WRAP over `run_data.run_identity` and `run_data.default_output_path` |
| `check_replay_out` | 1222-1234 | `(out_path: Path, run_dir: Path) -> None` | `REPLAY_SUFFIXES`, `protected_tree` | `write_replay_page` 1241 | WRAP over `run_data.check_output(..., error=ReplayError)` |
| page text (`run_assist` 470 to `downrange_note` 945), `run_record` 980, `replay_data` 1105, `embed_json` 1166, `load_template` 1174, `render_page` 1180, `write_replay_page` 1237 | | unchanged | | | STAY |

After the move replay.py still needs plots for one name only, `plots.plot_stem` (1217).
If `plot_stem` moves too, replay.py imports nothing from plots and no longer loads
matplotlib.

### 1.3 cli.py

| Symbol | Lines | Note | Destination |
|---|---|---|---|
| `CliError` | 54-55 | `class CliError(Exception)`; not a ValueError | STAY |
| `load_yaml` | 191-208 | strict reader of configuration files | STAY (not merged, section 2.1) |
| `command_animate`, `command_replay` | 440-472, 475-488 | call `plots.load_animation_runs`, `plots.default_animation_path`, `plots.check_animation_out`; `replay.check_replay_run_dir`, `replay.default_replay_path`, `replay.write_replay_page`; catch `plots.AnimationError`, `replay.ReplayError` | STAY. With the wrappers above, cli.py needs no edit in A1 |

## 2. Duplicates and their exact differences

### 2.1 JSON and YAML readers

| | plots `_read_json` 627 / `_read_yaml` 636 | replay `_read_json` 148 / `_read_yaml` 157 | `cli.load_yaml` 191 |
|---|---|---|---|
| Missing file | returns `{}` | returns `{}` | `CliError("file not found: {path}")` |
| Top level not a mapping | returns `{}` | returns `{}` | `CliError("{path}: expected a YAML mapping at the top level")` |
| Directory, permission, unreadable | `OSError` propagates (cli.main prints `error: <Type>: ...`, exit 1) | same | `CliError("cannot read {path}: {exc}")` |
| Not UTF-8 | `UnicodeDecodeError` propagates (a ValueError; cli.main does not catch it: traceback) | same | `CliError("{path} is not UTF-8 (byte {start}: {reason}); save the file as UTF-8")` |
| Parse error | `json.JSONDecodeError` (a ValueError) or `yaml.YAMLError` propagates: traceback | same | `CliError("cannot parse YAML {path}: {exc}")` |
| NaN / Infinity literals in JSON | accepted (`json.load` default) | accepted (docstring says so) | - |

The plots and replay bodies are identical line for line; only the docstrings differ.
`cli.load_yaml` has a different contract (a configuration file must exist and be a
mapping; tests/test_cli.py 210, 246 assert its messages) and must not be merged.
Recommendation: `run_data.read_json(path)` and `read_yaml(path)` with the lenient body,
verbatim. For the app (A4), which lists directories that a job may still be writing, add
an optional `error: type[RunDataError] | None = None` that turns a parse or decode error
into one message; with `None` the behaviour is today's.

### 2.2 Event and series readers

| | `plots._events` 683-707 | `replay.run_events` 445-464 |
|---|---|---|
| Rows returned | only rows whose `event` is a key of `EVENT_LABELS` (10 names: push_start, release, ignition, liftoff, kick_end, staging, fairing, cutoff, apex, impact); drops kick_start, ramp_end, propellant, ignition_failed, end | every row |
| Type | `tuple[AnimationEvent, ...]` (t_s, label, alt_m, downrange_m, speed_rel_mps) | `list[dict]` with keys, in this order, `t`, `name`, `stage`, `alt_m`, `x_km`, `v` |
| Name | the label text; a non-stage1 `ignition` becomes "S2 ignition" | the raw event name |
| Time | `float(row.t_s) - offset_s`, not rounded | `_finite(float(row["t_s"]) - offset_s, 3)` |
| Units and rounding | metres, raw floats, NaN kept | alt 1 decimal, downrange in km to 3 decimals by `round(float(m_to_km(d)), 3)` (no `+ 0.0`, so -0.0 survives), speed 2 decimals; non-finite becomes None |
| Columns required | `event`, `t_s`, `alt_m`, `downrange_m` (attribute access; AttributeError if absent); `stage` and `speed_rel_mps` optional | `t_s`, `event`; all others optional (`row.get`) |
| Missing file | `()` | `[]` |
| Mass | not read | not read |

Neither reads `phase` or `m_kg`. The test fixtures write events.csv with eight columns
(`t_s, event, phase, stage, alt_m, downrange_m, speed_rel_mps, m_kg`; test_animate 37,
test_replay 41, test_offload_pipeline 974), without `speed_inertial_mps` and
`gamma_rel_rad`, so the shared reader must require only `t_s` and `event` by default.

Series: `replay.read_series` (365-377) reads, checks the columns and emptiness, then
sorts on `t_rel_release_s` (stable) and drops duplicate times keeping the last.
`plots.read_animation_run` (818-824) reads and makes the same two checks with the same
two messages, but neither sorts nor de-duplicates: the animation keeps both rows of a
phase boundary. Sharing the sort with animate would change its frames. Share only the
read and the two checks.

### 2.3 Directory checks

| Step | `check_planar_run_dir` 661-680 | `check_replay_run_dir` 166-195 |
|---|---|---|
| Not a directory | "run directory not found: {run_dir}" | same text |
| No or empty metrics.json | "{run_dir} has no metrics.json; pass one results directory (results/<experiment>/<timestamp>)" | same text |
| `metrics["runs"]` not a dict | not checked | "{run_dir} is not an experiment results directory (its metrics.json lists no runs: a sweep point or a single run's folder); pass results/<experiment>/<timestamp>" |
| `model != "planar_2d"` | "{run_dir} is a {shown} run; animate draws planar_2d runs only (a vertical_1d run has no downrange or flight-path angle to show)" | "...; replay shows planar_2d runs only (...same parenthesis...)" |
| Error type | `AnimationError` | `ReplayError` |

A sweep point's metrics.json has the keys `experiment, timestamp_utc, git, run, baseline,
metrics, comparison` (no `model`, no `runs`; checked on
`results/silo_offload_2d/20261003T112949Z/sweep_1/run_0001`), so animate at HEAD calls a
planar sweep point "a vertical_1d run". Under one shared check with the runs test,
animate's message for a sweep point changes to "not an experiment results directory".
No existing test sees it (`test_vertical_1d_run_is_refused`, test_animate 250, uses a
directory with `runs` and no `model`). It is a second small behaviour change of animate
beside KI-017: either take it (recommended, with a test and a log line) or pass
`require_runs=False` from animate.

Selection (plots 854-868 against replay 203-217): identical logic, order (unknown,
repeated, none, too many) and messages, except the last: "...at most 4 fit one
animation" against "...fit one replay".

### 2.4 Output-path rules (KI-017)

| | animate | replay |
|---|---|---|
| The run's tree | `plots._results_tree` 962-972: the nearest ancestor of the run directory (inclusive) whose name equals "results" exactly; else `run_dir.parent.parent` (a tree written with `--results-root`), or the run directory itself when that is a filesystem root | the same function (`protected_tree` 1203) |
| Other trees | none | `results_ancestors` 1188-1194: every ancestor of the output path (inclusive) whose name is "results" ignoring case |
| Refusal | `check_animation_out` 1006: the output is inside the run's tree | `check_replay_out` 1228: `protected_tree(out, run_dir)` is not None, i.e. the output is inside the run's tree or inside any folder named results |
| Default output from a cwd inside a tree | next to the run's tree (`tree.parent`), only when cwd is inside the run's tree | next to the outermost protected tree |
| Order of checks | suffix, tree, ffmpeg (for .mp4), folder exists | suffix, tree, folder exists |
| Messages | "output {p} must end in .mp4 or .gif (the extension picks the format)"; "output {p} is inside the results tree; results/ is never edited by hand, so write the animation elsewhere (--out)"; "output folder does not exist: {parent}" | "output {p} must end in .html"; "...so write the page elsewhere (--out)"; same folder text |

Animate behaviours that change under replay's rule (each run in `s06_path_rules.py`):

1. Output inside another folder named results (any case) that is not the run's tree:
   accepted at HEAD, refused after.
2. Default output with cwd inside such a folder: written into cwd at HEAD (that is,
   inside that results folder); next to that folder after.
3. Nested trees (run in `repo/results/a/results/<exp>/<ts>`): output in
   `repo/results/zzz` accepted at HEAD (only the inner tree is protected), refused
   after; default from cwd = the inner tree goes to `repo/results/a/` at HEAD (inside
   the outer tree), to `repo/` after.
4. A tree named `Results` with the run one level deeper (`Results/group/<exp>/<ts>`):
   HEAD protects only `Results/group`; after, all of `Results`.

Nothing else changes: `protected_tree` gives the same answer whether the run's own tree
is found case-sensitively or not (a case-insensitive match would already be in
`results_ancestors`), so `results_tree` can move verbatim. Keep it case-sensitive:
`replay.source_text` (1063-1071) prints the path relative to it, and a changed rule
could change page bytes for directories outside a plain `results/` tree.

Animate tests that exercise output paths, read at HEAD, against replay's rule:

| Test (tests/test_animate.py) | Lines | What it needs | Under replay's rule |
|---|---|---|---|
| `test_gif_has_expected_frames_and_leaves_results_alone` | 173-195 | output in `tmp/out` accepted | passes (no results ancestor) |
| `test_default_output_is_outside_the_run_dir` | 198-213 | default = cwd for `tmp/work`; = `tmp` for cwd = run dir and cwd = `tmp/results` | passes (script: work, ., .) |
| `test_cli_default_output_from_inside_the_run_dir` | 216-230 | `tmp/<exp>_<ts>_animation.gif` with cwd = run dir | passes |
| `test_output_inside_results_or_bad_extension_is_refused` | 233-238 | `AnimationError` matching "results tree" for `run_dir/a.gif`; matching `\.mp4 or \.gif` for `a.avi` | passes, if the suffix check stays first and the tree message keeps the words "results tree" |
| `test_mp4_without_ffmpeg_is_a_clear_error` | 241-247 | "ffmpeg" for `tmp/a.mp4` | passes (ffmpeg check stays in plots) |
| `test_custom_results_root_is_protected` | 478-486 | `check_animation_out(other_run/"a.gif", run_dir)` refused for a tree named `out`; default from cwd `tmp/out` has parent `tmp` | passes: the run's own tree (`parent.parent`) is part of `protected_tree` |
| `test_ffmpeg_failure_is_one_error_line` | 511-521 | `--out tmp/a.mp4` accepted, then the stand-in writer fails | passes only if the ffmpeg test reads `plots.FFMpegWriter` (section 4) |

All seven hold. They would all fail on a machine whose temporary directory lies under
a folder named results, as the replay tests already would.

## 3. Error types

- `plots.AnimationError(ValueError)` (plots.py 312), `replay.ReplayError(ValueError)`
  (replay.py 57), `cli.CliError(Exception)` (cli.py 54). cli.py catches the first two
  by name (469, 485) and re-raises `CliError(str(exc))`.
- Tests assert the concrete class: 12 `pytest.raises(plots.AnimationError...)`, 5
  `pytest.raises(replay.ReplayError...)`. A shared function that raised a common base
  class would fail all of them (a base instance is not an instance of the subclass), so
  a base class alone is not enough.
- Recommendation: both. `run_data.RunDataError(ValueError)` as the base;
  `AnimationError` and `ReplayError` stay in their modules and derive from it (still
  ValueErrors). Every raising function of run_data takes
  `error: type[RunDataError] = RunDataError` and raises that type. Wording that differs
  ("animate draws" / "replay shows", "one animation" / "one replay", "the animation" /
  "the page") is a second keyword. The old names stay as thin wrappers that pass their
  class and words. A plain re-export is right only for functions that never raise.
  `functools.partial` would work but loses the docstring CLAUDE.md asks for.
- Why not re-raise in the wrapper (`except RunDataError as e: raise AnimationError(str(e))`):
  it works, but the wording still has to be passed in, and it adds a chained traceback.

Messages asserted by tests (all must survive word for word in the named part):

| File:line | Raised through | Asserted |
|---|---|---|
| test_animate 235, 483 | `write_ascent_animation`, `check_animation_out` | `AnimationError`, "results tree" |
| test_animate 237 | `write_ascent_animation` | `\.mp4 or \.gif` |
| test_animate 246 | `write_ascent_animation` | "ffmpeg" |
| test_animate 252, 257 | `write_ascent_animation`, CLI | "vertical_1d"; CLI output has "error:" and no "Traceback" |
| test_animate 263, 268 | `load_animation_runs`, CLI | regex `unknown run\(s\) nope.*available: pad, silo` (one line); "unknown run(s) nope" |
| test_animate 276 | `load_animation_runs` | "at most" |
| test_animate 403, 422, 424, 811, 813 | `ascent_time_map`, `animation_playback_fps`, `frame_geometry` (all stay in plots) | "at most 50 fps", "fps", "even" |
| test_animate 521 | CLI | "error: ffmpeg failed" |
| test_replay 395, 617 | `write_replay_page` | `ReplayError`, "results tree" |
| test_replay 397 | `write_replay_page` | `\.html` |
| test_replay 464 | `replay_data` | "describes it nowhere" |
| test_replay 642-644 | `replay_data` | "not an experiment results directory", and "vertical_1d" not in the message |
| test_replay 407, 420, 422 | CLI | "vertical_1d"; "unknown run(s) nope" and "available: pad, silo, silo_step"; "run directory not found" |
| test_replay 650-651 | CLI | "at most 4"; "a run is named twice" |
| test_offload_pipeline 1093-1097 | `replay.run_source` notes | starts "offload case s1 of silo: 41.3 t less propellant (solved; 10.0%"; "8.0% of all"; "flying 1,000.0 kg"; "P_ref = 1,000.0 kg"; "paired pad of offload case s1"; starts "pad control (stage1)" |
| test_offload_pipeline 1100-1104 | `replay_data`, page | "s1 (offload)"; "of the offload block" |

tests/test_offload_pipeline.py has no `match=` on an animation or replay error (its
`match=` lines 458-674 are config and results_io errors; 509 is `cli.CliError`,
"longer than").

Order of errors to keep: `replay.write_replay_page` builds the data first and checks
the output second (1240-1241), so a bad run selection wins over a bad output path;
`load_animation_runs` checks the directory before the selection.

## 4. Monkeypatch and identity traps

| # | Test | What it does | What must stay where |
|---|---|---|---|
| 1 | test_animate 355-375 `test_calibration_band_includes_both_edges` | `mp.setattr(plots, "CALIBRATION_RECORDS", edge)` (371), then `plots.calibration_caveat("edge_2d")` (372) | `calibration_caveat` stays a function defined in plots.py that looks up the bare name `CALIBRATION_RECORDS` in the plots module at call time. `from launchsim.run_data import CALIBRATION_RECORDS` in plots gives that name. No run_data helper may fetch the record on plots' behalf (it would read run_data's binding and return "no calibration record"). Helpers take the record or the gap as an argument, as `calibration_gap` and `inside_calibration_band` do |
| 2 | test_animate 511-521 `test_ffmpeg_failure_is_one_error_line` | `monkeypatch.setattr(plots, "FFMpegWriter", _BrokenFFMpeg)` (515), then the CLI with `--out a.mp4` | `check_animation_out`'s ".mp4 needs ffmpeg" test and `write_ascent_animation`'s writer construction read `FFMpegWriter` from the plots module. If the availability test moved to run_data, the stand-in's `isAvailable() -> True` would not be seen and, on a machine without ffmpeg, the test would get "needs ffmpeg" instead of "ffmpeg failed". The phase file does not list this patch |
| 3 | test_animate 169-170 `_no_ffmpeg` (used at 221, 245, 752) | `monkeypatch.setattr(plots.FFMpegWriter, "isAvailable", classmethod(...))` | plots keeps importing `FFMpegWriter` under that name; `default_animation_path(..., ffmpeg=None)` keeps asking it. run_data never imports matplotlib |
| 4 | test_replay 504-505 | `fields["gamma_deg"] is replay.wrapped_deg` | `SERIES_FIELDS` and `wrapped_deg` must refer to one object: both stay, or `wrapped_deg` moves and replay re-exports it (then `SERIES_FIELDS`, staying in replay, holds the same object). A wrapper named `wrapped_deg` in replay would break the identity |
| 5 | test_replay 506 | `replay._finite(-0.0, 1)` | `_finite` importable from replay under the private name |
| 6 | test_animate 36, test_replay 40, test_offload_pipeline 973 | fixture CSV headers are `[*plots.ANIMATION_COLUMNS, "stage"]` and `[*replay.REPLAY_COLUMNS, "stage"]`; test_offload_pipeline 1004 indexes each row by every column | the two tuples keep their content and order; the readers used by animate and replay may not require any other column |
| 7 | test_offload_pipeline 1087, 1095, 1096 | `replay.run_source(metrics, cfg, name)` with three positional arguments | the old signature stays; an added `error` is keyword-only with a default, or lives only in the run_data function |
| 8 | test_animate 203-211, 485 | `plots.default_animation_path(run_dir, cwd, ffmpeg=...)` | keyword-only `ffmpeg` stays |
| 9 | test_config_planar 1376-1378, test_offload_pipeline 842, 1733, 2023, 2038, 2061 | `plots.CALIBRATION_RECORDS[...]` compared with what results_io wrote | one dict object behind every name (`run_data`, `plots`, `results_io`); never copy it |

No other test sets an attribute on plots or replay. The other `setattr` calls in the
suite target `engine`, `planar_module`, `guidance`, `results_io` and `sim`
(test_height_event 281, test_insertion 237, test_ltg 506, test_offload_pipeline
1341-2109, test_results_io 205-851) and do not touch the moved names.

ruff selects `F` (pyproject.toml), so a re-exported name that its module does not use
itself needs `from launchsim.run_data import x as x` (or a `# noqa: F401`); sim.py
handles its re-exports with `__all__`.

## 5. The fairing event reader (KI-016)

### 5.1 What the planner logs (phases/planar.py at HEAD; the phase file's lines hold)

- `map_staging_planar(y, vehicle, stage_index, drop_fairing)` (451-464) removes the
  stage's dry mass, plus the fairing mass when `drop_fairing`; `map_fairing_planar(y,
  fairing_mass_kg)` (475-481) removes the fairing mass. Nothing else changes.
- `_stage_and_coast` (1672-1708): `drop = rule.trigger == "staging"` (1684); with a
  heating limit, `drop = heating_met` (1686-1688); the map (1689); then the `staging`
  row with the mapped state, phase COAST_STAGING, stage index 1 (1690); then, only when
  `heating_met`, a `fairing` row with the same mapped state (1692).
- `_fly_stage2` (1254-1347): the stage-2 `ignition` row (1283); if the fairing is on
  and the heating criterion is met at ignition, a `fairing` row with the state before
  the map, phase LTG_BURN (1299), then the map (1305). Otherwise the heating event ends
  a burn sub-phase; `_integrate` (1351-1358) logs it with the event state, before the
  map at 1317.
- `metrics_planar.fairing_items` (669-694) and the forms (393-399): `FAIRING_IN_BURN` =
  "in the stage-2 burn (heating event)", `FAIRING_AT_IGNITION` = "at stage-2 ignition
  (heating criterion met in the staging coast)", `FAIRING_AT_STAGING` = "at staging",
  `FAIRING_KEPT` = "kept to the end of the run"; None without a fairing, with one stage,
  or when the run never staged. `fairing_drop` is "at staging" both when a `fairing`
  row exists in COAST_STAGING (684-685) and when there is no row and the rule is
  `staging` (680-681): the metric alone does not tell those two apart.

### 5.2 The cases and the mass rule

With m_dry1 the dry mass of the stage dropped at the `staging` row (the stage before
the row's `stage`), m_fair the fairing mass, m_s the `staging` row's `m_kg` and m_f the
`fairing` row's `m_kg`:

| Case | `fairing_drop` metric | Rows | How to tell without the metric | `staging` drop: before -> after | `fairing` drop: before -> after |
|---|---|---|---|---|---|
| 1 in the burn | `FAIRING_IN_BURN` | `fairing` row, phase LTG_BURN, later than the stage-2 `ignition` row | `fairing` row phase LTG_BURN and `t_s` differs from the stage-2 `ignition` row's | m_s + m_dry1 -> m_s | m_f -> m_f - m_fair (row logged before) |
| 2 at stage-2 ignition | `FAIRING_AT_IGNITION` | `ignition` (stage2) row, then `fairing` row, phase LTG_BURN, same `t_s` and `m_kg` | `fairing` row phase LTG_BURN and `t_s` equal to the stage-2 `ignition` row's (the planner uses exact equality, metrics_planar 686; both rows are written with `%.12g`, so the strings are equal) | m_s + m_dry1 -> m_s | m_f -> m_f - m_fair (row logged before) |
| 3 at staging, heating criterion met | `FAIRING_AT_STAGING` and a `fairing` row | `staging` row, then `fairing` row, both COAST_STAGING, same `t_s`, same `m_kg` | `fairing` row phase COAST_STAGING | m_s + m_dry1 + m_fair -> m_s + m_fair | m_f + m_fair -> m_f (row logged after both) |
| 4 rule `staging` | `FAIRING_AT_STAGING` and no `fairing` row | `staging` row only | no `fairing` row, the vehicle's rule is `staging` and m_fair > 0 | m_s + m_dry1 + m_fair -> m_s + m_fair | a drop the reader adds at the `staging` row's time and state, marked not recorded: m_s + m_fair -> m_s |
| kept | `FAIRING_KEPT` | `staging` row, no `fairing` row | no `fairing` row and the rule is `never` or a heating rule | m_s + m_dry1 -> m_s | none |
| none | None | no `staging` row (never staged), or no fairing | - | m_s + m_dry1 -> m_s if a row exists | none |

So the rule is short:

- a `fairing` row in COAST_STAGING carries the mass after the drop; any other `fairing`
  row carries the mass before it;
- a `staging` row always carries the mass after the map; the map included the fairing
  exactly in cases 3 and 4;
- in cases 3 and 4 the two drops are one map at one instant. Reporting them as a chain
  (stage first, then fairing, the order of the rows) keeps "after" of one drop equal to
  "before" of the next. That order is a convention of the reader, to be stated in its
  docstring;
- every other row has before = after = `m_kg`.

A check from the rows alone: the stage-1 `propellant` row (phase GRAVITY_TURN) has the
same `t_s` as the `staging` row and carries the mass before the map, so
`m_propellant - m_s` is m_dry1 (cases 1, 2, kept) or m_dry1 + m_fair (cases 3, 4). On
the 56 recorded planar run folders it equals m_dry1 to 2.9e-11 kg. The reader can use
it as a third discriminator and as a consistency check.

### 5.3 Where the masses come from

The run's vehicle block is the entry's `vehicle` in resolved_config.yaml when present
(under `runs`, `bound_runs`, `cases` or `offload_runs`), else the top-level `vehicle`
(results_io.py 590-631 writes it only when it differs). It is the raw vehicle file:
`stages[i].dry_mass_t.value`, `fairing_mass_t.value` in tonnes, and `fairing_drop` as a
string (`staging`, `never`), a block with `trigger`, or absent, in which case the
default is `staging` (config.py 480). A hand-written `block.get("fairing_drop")` would
read an absent key as "no rule" and mistake case 4 for "kept".

Recommendation: `VehicleConfig.model_validate(block).to_vehicle()` (config.py 464, 499),
which applies the default, converts tonnes through units.py and gives
`stages[i].dry_mass_kg`, `fairing_mass_kg`, `fairing_rule.trigger`. All 56 recorded
blocks validate. Cost: the models forbid unknown keys (config.py 217), so a later schema
change that renames a vehicle key would make old directories unreadable by the scene;
note it for SP7. The test fixtures have no masses in their vehicle block
(`{"name": "toy_2d"}`), so the animate and replay paths must not ask for masses at all.

Dry-mass penalties change m_dry1 per run (`silo_cold_s1_dry+2t`: 24,200 kg;
`+4t`: 26,200 kg; `+8.1t`: 30,300 kg in 20261003T112934Z), which is why the per-run
block matters.

### 5.4 Which recorded directories show which case

| Directory | Runs | Case |
|---|---|---|
| `results/silo_screening_2d/20260930T175743Z` | 11 of 12 | 1 (in the burn). pad: fairing row m 129,343.226242 kg at t_s 196.807530921, series after 127,643.226242 kg (1,700 kg less); staging row 139,254.396243 kg, propellant row 161,454.396243 kg (22,200 kg more) |
| same | silo_failed | none: `ignition_failed`, never staged, `fairing_drop` null |
| `results/silo_offload_2d/20261003T112934Z` | all 19 | 1. silo_cold_s1: fairing row 129,274.26715 kg at 186.857800743 s |
| `results/silo_offload_2d_readme/20261003T112956Z` (5), `results/silo_bridge_2d_readme/20260930T185034Z` (4), `results/calibration_f9_2d/20260930T100100Z` and `20260930T173928Z` (8 each) | all | 1 (README-loads runs: m_dry1 25,600 kg, m_fair 1,900 kg) |
| sweep points (`silo_offload_2d/20261003T112949Z`, `silo_screening_2d/20260930T182453Z`, `guidance_trigger_2d/20260930T174950Z`) | 55 planar folders | 1 |
| `results/silo_screening_1d/*` | 30 run folders, 75 sweep-point folders | vehicle rule `fairing_drop: staging`, but the runs end at stage-1 burnout: events are ignition, release, propellant, end; there is no staging row, and the columns are `z_m, v_mps, m_kg` (not planar) |

No recorded directory shows case 2, 3 or 4, so their tests need built data.
tests/test_planar_events.py 308-343 (`test_staging_map_and_coast`) already flies
stage 1 through staging in the fast suite for the rule `staging`, the rule `never`,
the heating rule not met and the heating rule met
(`FairingDrop("free_molecular_heating", 1.0e12)`); the same planner call plus
`metrics_planar.events_frame_planar` gives real rows for cases 3, 4 and "kept". Cases
1 and 2 need a stage-2 burn: use hand-written rows, and check case 1 against a recorded
directory when its CSVs exist (they are not in git; skip otherwise).

### 5.5 Shape of the reader

- `read_events(path, offset_s)` returns every row in file order as a small frozen record
  (`EventRow`); it requires `t_s` and `event` only and gives None for an absent or
  non-finite optional value. No mass arithmetic.
- `with_drop_masses(rows, masses, fairing_drop)` is pure: it fills `m_before_kg`,
  `m_after_kg` and `dropped` per row and appends the case-4 row with `recorded=False`.
  `masses` None leaves the three fields None, so a caller without a vehicle block
  cannot fail.
- `replay.run_events` and `plots._events` keep their signatures and project the
  recorded rows only, with their own rounding. Their output is then unchanged for every
  directory, including a future case-4 run.

## 6. Byte-identity risks for the replay page

Ranked by how likely a tidy refactor is to trip them.

1. **Negative zero in event `x_km`.** `run_events` rounds the downrange with
   `round(float(m_to_km(downrange)), 3)` (replay.py 460), without the `+ 0.0` that
   `_finite` adds. A downrange of -0.157654 m (pad `kick_start`) becomes `-0.0`. The
   reference page holds six such tokens. A shared reader that routes this through
   `finite(..., 3)` changes them to `0.0` and breaks the hash. The projection in
   replay must keep the expression as it is. The series lists are safe today
   (`series_values` adds 0.0; `t` is rounded without it but is never negative zero in
   the reference page).
2. **Key order.** The page is `json.dumps(..., separators=(",", ":"))` without
   `sort_keys` (1170), so bytes follow dict insertion order. Fixed points: the run
   record splices `**run_series(frame)` between `inserted` and `events` (1023); the
   series keys are `t`, then `alt_m, x_km, v, gamma_deg, m_t, g_ax, q_kpa, mach`
   (`SERIES_FIELDS` order), then `phase`; the event keys are `t, name, stage, alt_m,
   x_km, v`. A reader that returns richer event records must not leak new keys
   (`m_before_kg`, ...) into the replay's dicts.
3. **CSV parsing and row handling.** `pd.read_csv(path, encoding="utf-8")` with no
   other argument (370, 450). Adding `dtype`, `float_precision`, `engine` or a
   converter can change a parsed float in the last place; `usecols` is safe but
   unnecessary. Keep the stable sort and `drop_duplicates(keep="last")` for the replay,
   and the event rows in file order.
4. **Arithmetic order.** Event time is `float(row["t_s"]) - offset_s` with
   `offset_s = float(frame["t_s"].iloc[0]) - float(frame["t_rel_release_s"].iloc[0])`
   from the sorted series (994, 456). Computing it from `t_release_s` in metrics.json
   could differ in the last place before rounding to 3 decimals. `replay_grid` (398-402)
   must keep its concatenate, round(6), unique sequence; add event-aligned times in A2,
   not A1.
5. **Embedded version.** `meta.version` is `launchsim.__version__` ("0.1.0", 1147). A
   version bump between "before" and "after" changes the page.
6. **Environment.** The page depends on numpy's `interp`, `arange`, `unique` and on
   pandas' float parser. If A1 also edits pyproject.toml (KI-018, Pillow) and the lock
   file moves numpy or pandas (pyproject asks pandas>=3.0, numpy>=2.3), bytes can
   change for a reason that is not the refactor. Generate "before" and "after" in the
   same environment; do the Pillow line after the hash is confirmed, or check that the
   lock diff adds nothing else.
7. **The results-tree rule in `source_text`.** `meta.source` is the run directory
   relative to the parent of `plots._results_tree(run_dir)`, as POSIX
   ("results/silo_screening_2d/20260930T175743Z"). It must keep using the run's own
   tree, case-sensitive, not `protected_tree`.
8. **Set iteration.** `animation_run_names` builds a set of folder names (651) but
   sorts what it takes from it (653), and metrics order drives the rest. A rewrite that
   iterates the set would make the default selection depend on the hash seed. The two
   pages of this survey were built in separate processes and are identical, which
   confirms there is no such dependence today.
9. **Path separators and newlines.** `as_posix()` is used for the one embedded path;
   the page is written with `newline="\n"` (1243) and the template is read in text
   mode, so a CRLF checkout of the template does not matter. The page has no CR.
10. **Calibration text.** `replay.calibration_caveat` formats `100 * CALIBRATION_BAND`
    and the record's numbers; it may read the names from run_data or plots, as long as
    the expressions stay.

Gate procedure (proposed):

1. First action of A1, clean tree, before any edit: record `git rev-parse HEAD`, then
   `uv run python -m launchsim replay results/silo_screening_2d/20260930T175743Z --runs pad silo_cold silo_hot_ramp_on_track silo_failed --out <scratchpad>/reference_replay.html`
   and its sha256. Expected at b69ff0c: 247,949 bytes,
   `3ca23dc5ce6532e6b9e3fd4656ab4846bcb4cdddfced7a077ce05c9411fd1eab`.
2. The reference page exercises only the `run` role. Hash seven more pages at the same
   time (0.25 s each). Values at b69ff0c, built in memory:

   | Page | Directory and runs | Roles | Bytes | sha256 |
   |---|---|---|---|---|
   | screening_default | silo_screening_2d/20260930T175743Z, no `--runs` | run x4 (default selection) | 300,810 | `f5069712753d052bc2b6a3ae71c456f0d4fa6c9f8ab2f1545f4c35e3926d29e0` |
   | screening_bound | same, pad silo_cold__aero_bound pad__aero_bound silo_sled_22t | run, bound, paired_baseline, run | 302,477 | `88710c4cb2d21d38cabae5638518a1ca125189116a3ba3536e8cff0c3dced55d` |
   | offload | silo_offload_2d/20261003T112934Z, pad silo_cold silo_cold_s1 silo_cold_s1__pad | run x2, offload x2 | 300,044 | `359918c0de55a30bb942a1c83b809acbfa66af1a7bf11790f6832720f79c61cb` |
   | offload_controls | same, pad pad__offload_stage1 pad__offload_stage2 silo_cold_s1_dry+2t | run, offload x3 | 299,600 | `1276181dfb58bc9137f50841f180912b9e4f44af5d407681f782533ccf7948f5` |
   | calibration_default | calibration_f9_2d/20260930T173928Z, no `--runs` | run x1 | 99,750 | `c6fa07cae8ca69000474dbf06a1f60a916fe03ba98601028a9dcb3d5ef92c4a9` |
   | calibration_cases | same, pad readme_loads no_rotation alt_185 | run, case x3 | 294,636 | `0411dfaa7e93e7afc8a6e2b6fe8b9b02287aab85323422cb50c0b685697e4c6f` |
   | readme_bridge | silo_offload_2d_readme/20261003T112956Z, no `--runs` | run x2, the README-loads vehicle (record inside the band) | 160,027 | `a2e4f928509f0faea0cc819904217ec5face749983313e7c3456653b4183a5c9` |

   The formal gate stays the one reference page; the seven are a wider net for
   `run_source`, `offload_note`, the default selection and the second calibration record.
3. After the refactor, same environment, same commands, compare the hashes. On a
   mismatch, extract the JSON of both pages (the `replay-data` script element), load it
   and compare key by key to find the field.
4. Record the commit and the hash in the session log at the gate commit, as the phase
   file asks.
5. In the fast suite, pin a digest of the `runs` block of a synthetic directory (built
   in test_run_data, with one event at a small negative downrange so the `-0.0` case is
   under test), computed at the SP2 start commit. It guards the series and event bytes
   without pinning the template, which later deliberate text changes (KI-029) may edit.

## 7. Model-keyed column sets (D-SP1-01)

The 3-D design says the spatial model (`dynamics: spatial_3d`) writes a superset of the
planar column names so that the 2-D scene reads a 3-D run. The minimum that honours it
without touching the planar path:

    @dataclass(frozen=True)
    class ModelColumns:
        series: tuple[str, ...]   # every column the model's timeseries.csv writes
        events: tuple[str, ...]   # every column of its events.csv
        base: tuple[str, ...]     # the columns every reader of the model needs

    MODEL_COLUMNS: dict[str, ModelColumns] = {
        PLANAR_2D: ModelColumns(
            series=metrics_planar.PLANAR_TIMESERIES_COLUMNS,   # 32 columns
            events=metrics_planar.PLANAR_EVENT_COLUMNS,        # 10 columns
            base=PLANAR_BASE_COLUMNS,                          # today's nine
        ),
    }

    def model_columns(model: str, *, error=RunDataError) -> ModelColumns

Rules that make it work:

- The readers never hard-code a column list. `read_series(run_dir, name, columns)` and
  `run_series(frame, fields)` take what the caller needs; extra columns in the file are
  ignored. Animate passes the base, replay its eleven, the scene its own larger list.
- A consumer keys its field list by model (`scene.SCENE_FIELDS[PLANAR_2D]`); a spatial
  model adds `SCENE_FIELDS["spatial_3d"] = (*SCENE_FIELDS[PLANAR_2D], more...)`.
- `check_run_dir(run_dir, models=(PLANAR_2D,))` takes the accepted models. Animate and
  replay pass the default and keep refusing everything else; SP4's scene passes two.
  The message is built from the tuple (`" or ".join(models)`), which gives today's text
  for one model.
- `MODEL_COLUMNS` records what a model writes, so a test can assert that every column a
  consumer asks for exists in its model, and SP3/SP4 add one dictionary entry.
- The drop-mass rule of section 5 is planar (phase names COAST_STAGING, LTG_BURN). Keep
  it one function taking the phase names from `phases.planar`; a spatial model that
  keeps the names reuses it.

Do not make the full 32-column set a requirement of `read_series`: the synthetic
fixtures of the three test files have 10 to 12 columns.

## 8. Proposed public API of run_data.py

Imports: json, math, dataclasses, pathlib, typing, numpy, pandas, yaml;
`launchsim.config` (`PLANAR_2D`, `VERTICAL_1D`, `VehicleConfig`), `launchsim.units`,
`launchsim.metrics_planar` (the column tuples and `FAIRING_*`), `launchsim.phases.planar`
(`COAST_STAGING`, `LTG_BURN`). Never plots, replay, results_io, summary or matplotlib.

    class RunDataError(ValueError)
        """A user-facing problem with a results directory, a run selection or an output path."""

    # constants
    RESULTS_TREE_NAME = "results"
    MAX_RUNS = 4
    DEFAULT_VARIANTS = 3
    ROLE_RUN, ROLE_BOUND, ROLE_PAIRED_BASELINE, ROLE_CASE, ROLE_OFFLOAD
    OFFLOAD_CASE, OFFLOAD_PAIRED_PAD, OFFLOAD_PAD_CONTROL, OFFLOAD_SOLVED_KIND
    CALIBRATION_RECORDS, CALIBRATION_BAND, CALIBRATION_BAND_EDGE_REL_TOL, CALIBRATION_GATE_VEHICLE
    PLANAR_BASE_COLUMNS            # the nine columns of plots.ANIMATION_COLUMNS
    GRID_EARLY_END_S = 40.0, GRID_EARLY_DT_S = 0.1, GRID_LATE_DT_S = 1.0
    GRID_DECIMALS = 6, TIME_DECIMALS = 3
    MODEL_COLUMNS, ModelColumns
    type Converter = Callable[[np.ndarray], np.ndarray]
    type SeriesField = tuple[str, str, Converter | None, int]

    # small helpers
    def as_mapping(value: Any) -> dict[str, Any]
        """``value`` when it is a mapping, else {}."""
    def finite(value: Any, decimals: int | None = None) -> float | None
        """A finite float (rounded, -0.0 made 0.0), or None."""
    def wrapped_deg(angle_rad: np.ndarray) -> np.ndarray
        """An angle [rad] wrapped to [-180, 180] deg."""

    # files
    def read_json(path: Path) -> dict[str, Any]
        """A JSON mapping read as UTF-8 (NaN literals allowed), or {} when missing."""
    def read_yaml(path: Path) -> dict[str, Any]
        """A YAML mapping read as UTF-8, or {} when missing."""

    # directory and selection
    def check_run_dir(run_dir: Path, *, verb: str, models: tuple[str, ...] = (PLANAR_2D,),
                      require_runs: bool = True,
                      error: type[RunDataError] = RunDataError) -> dict[str, Any]
        """metrics.json of an experiment results directory of an accepted model, or an error."""
    def run_names(run_dir: Path) -> tuple[list[str], list[str]]
        """(default selection, every run folder with a timeseries.csv), summary order first."""
    def select_runs(run_dir: Path, runs: Sequence[str] | None, *, what: str,
                    max_runs: int = MAX_RUNS,
                    error: type[RunDataError] = RunDataError) -> list[str]
        """The run names to show, checked: known, not repeated, at least one, at most max_runs."""
    def run_identity(run_dir: Path) -> tuple[str, str]
        """(experiment, UTC timestamp) from metrics.json, else from the folder names."""
    def model_columns(model: str, *, error: type[RunDataError] = RunDataError) -> ModelColumns
        """The column sets of a model."""

    # roles and configuration
    def entry_config(entry: Any) -> tuple[dict[str, Any], str | None]
        """(run block, vehicle name or None) of one resolved_config.yaml run entry."""
    def overrides_text(overrides: Mapping[str, Any]) -> str
        """' (with key = value)' for a bound's overrides, '' when there are none."""
    def run_source(metrics: dict[str, Any], config: dict[str, Any], name: str, *,
                   error: type[RunDataError] = RunDataError) -> dict[str, Any]
        """Role, metrics, comparison, compared run, run block, vehicle name and note of a run."""
    def offload_role(offload: Mapping[str, Any], name: str) -> tuple[str, dict[str, Any]] | None
        """(kind, record) of a run of the offload block: case, paired pad or pad control."""
    def offload_note(offload: Mapping[str, Any], name: str, baseline: str) -> str
        """What an offload run is, in one sentence."""
    def run_vehicle_block(config: Mapping[str, Any], name: str) -> dict[str, Any]      # new
        """The run's own vehicle block of resolved_config.yaml, else the experiment's."""
    def vehicle_masses(block: Mapping[str, Any], *,
                       error: type[RunDataError] = RunDataError) -> VehicleMasses      # new
        """Stage dry and propellant masses [kg], fairing mass [kg] and fairing trigger."""

    # series
    def read_series_frame(run_dir: Path, name: str, columns: Sequence[str], *,
                          error: type[RunDataError] = RunDataError) -> pd.DataFrame
        """timeseries.csv as written, with the column and emptiness checks (animate)."""
    def read_series(run_dir: Path, name: str, columns: Sequence[str], *,
                    error: type[RunDataError] = RunDataError) -> pd.DataFrame
        """The same, sorted on the time after release, one row per time (the last)."""
    def release_offset_s(frame: pd.DataFrame) -> float
        """t_s - t_rel_release_s of the first row [s]."""
    def sample_grid(t0_s: float, t1_s: float) -> np.ndarray
        """Common-clock sample times [s after release]: 0.1 s to 40 s, then 1 s, ends included."""
    def defined_mask(t_s: np.ndarray, values: np.ndarray, grid: np.ndarray) -> list[bool]
    def series_values(t_s: np.ndarray, values: np.ndarray, grid: np.ndarray,
                      decimals: int) -> list[float | None]
    def run_series(frame: pd.DataFrame, fields: Sequence[SeriesField]) -> dict[str, Any]
        """t, each field resampled and rounded, and the phase per sample."""

    # events
    @dataclass(frozen=True)
    class EventRow        # t_s, t_rel_s, name, phase, stage, alt_m, downrange_m,
                          # speed_rel_mps, speed_inertial_mps, gamma_rel_rad, m_kg,
                          # m_before_kg, m_after_kg, dropped, recorded
    def read_events(path: Path, offset_s: float, *, required: Sequence[str] = ("t_s", "event"),
                    error: type[RunDataError] = RunDataError) -> list[EventRow]
        """Every row of events.csv in file order; [] when the file is missing."""
    def fairing_case(rows: Sequence[EventRow], fairing_drop: str | None,
                     masses: VehicleMasses | None) -> str | None
        """The FAIRING_* form of a run, from its metric, else from the rows and the rule."""
    def with_drop_masses(rows: Sequence[EventRow], masses: VehicleMasses | None,
                         fairing_drop: str | None) -> list[EventRow]
        """The rows with the mass before and after every drop (pure; section 5.2)."""

    # calibration
    def calibration_gap(model_kg: float, reference_kg: float) -> float
    def inside_calibration_band(gap: float) -> bool

    # output paths (one rule)
    def results_tree(run_dir: Path) -> Path
        """The run's own results tree (nearest ancestor named results, else parent.parent)."""
    def is_inside(path: Path, root: Path) -> bool
    def results_ancestors(path: Path) -> list[Path]
        """Every ancestor of path named results, ignoring case, innermost first."""
    def protected_tree(path: Path, run_dir: Path) -> Path | None
        """The outermost results tree holding path (the run's own or any folder named results)."""
    def default_output_path(run_dir: Path, cwd: Path, file_name: str) -> Path
        """<cwd>/<file_name>, or next to the outermost protected tree when cwd is inside one."""
    def check_outside_results(out_path: Path, run_dir: Path, *, what: str,
                              error: type[RunDataError] = RunDataError) -> None
        """Refuse an output inside a protected tree ("...write the {what} elsewhere (--out)")."""
    def check_output_folder(out_path: Path, *, error: type[RunDataError] = RunDataError) -> None
        """Refuse an output whose folder does not exist."""
    def check_output(out_path: Path, run_dir: Path, *, suffixes: Sequence[str],
                     suffix_text: str, what: str,
                     error: type[RunDataError] = RunDataError) -> None
        """Suffix, protected tree, folder: the whole check for a page writer."""

`default_output_path` takes the file name because `plot_stem` lives in plots, which
imports run_data. `check_animation_out` composes `check_outside_results` and
`check_output_folder` around its own suffix and ffmpeg checks, which keeps today's
order (suffix, tree, ffmpeg, folder); replay and the scene use `check_output`.

### Re-exports and wrappers

plots.py, plain re-exports from run_data (old name <- new name):
`CALIBRATION_RECORDS`, `CALIBRATION_BAND`, `CALIBRATION_BAND_EDGE_REL_TOL`,
`CALIBRATION_GATE_VEHICLE`, `calibration_gap`, `inside_calibration_band`,
`RESULTS_TREE_NAME`, `OFFLOAD_CASE`, `OFFLOAD_PAIRED_PAD`, `OFFLOAD_PAD_CONTROL`,
`OFFLOAD_SOLVED_KIND`, `offload_role`, `ANIMATION_MAX_RUNS <- MAX_RUNS`,
`ANIMATION_DEFAULT_VARIANTS <- DEFAULT_VARIANTS`, `ANIMATION_COLUMNS <- PLANAR_BASE_COLUMNS`,
`animation_run_names <- run_names`.
plots.py, wrappers that stay (AnimationError, animate's words): `check_planar_run_dir`,
`load_animation_runs`, `read_animation_run`, `_events`, `default_animation_path`,
`check_animation_out`. Stay unchanged: `AnimationError` (new base), `calibration_caveat`,
`FFMpegWriter`, every drawing name. Dropped (no user left): `_read_json`, `_read_yaml`,
`_results_tree`, `_is_inside`, `_as_dict`.

replay.py, plain re-exports: `ROLE_RUN`, `ROLE_BOUND`, `ROLE_PAIRED_BASELINE`,
`ROLE_CASE`, `ROLE_OFFLOAD`, `REPLAY_EARLY_END_S <- GRID_EARLY_END_S`,
`REPLAY_EARLY_DT_S <- GRID_EARLY_DT_S`, `REPLAY_LATE_DT_S <- GRID_LATE_DT_S`,
`REPLAY_GRID_DECIMALS <- GRID_DECIMALS`, `REPLAY_TIME_DECIMALS <- TIME_DECIMALS`,
`_finite <- finite`, `_mapping <- as_mapping`, `_entry_config <- entry_config`,
`overrides_text`, `offload_note`, `replay_grid <- sample_grid`, `defined_mask`,
`series_values`, `wrapped_deg`, `Converter`, `results_ancestors`, `protected_tree`.
replay.py, wrappers that stay (ReplayError, replay's words): `check_replay_run_dir`,
`select_runs`, `run_source`, `read_series`, `run_series`, `run_events`, `source_text`,
`default_replay_path`, `check_replay_out`. Stay unchanged: `ReplayError` (new base),
`REPLAY_COLUMNS`, `SERIES_FIELDS`, `calibration_caveat`, all page text, `run_record`,
`replay_data`, `embed_json`, `load_template`, `render_page`, `write_replay_page`.
Dropped: `_read_json`, `_read_yaml`.

Names the existing tests take from the two modules, all covered above. From replay:
`DRY_MASS_PARAM`, `REPLAY_COLUMNS`, `REPLAY_DATA_TOKEN`, `REPLAY_EARLY_DT_S`,
`REPLAY_EARLY_END_S`, `REPLAY_LATE_DT_S`, `ROLE_BOUND`, `ROLE_OFFLOAD`, `ReplayError`,
`SERIES_FIELDS`, `_finite`, `calibration_caveat`, `default_replay_path`, `embed_json`,
`load_template`, `replay_data`, `replay_grid`, `run_source`, `wrapped_deg`,
`write_replay_page`. From plots, among the moved or wrapped names: `ANIMATION_COLUMNS`,
`AnimationError`, `CALIBRATION_RECORDS`, `FFMpegWriter`, `OFFLOAD_CASE`,
`OFFLOAD_PAD_CONTROL`, `OFFLOAD_PAIRED_PAD`, `animation_record`, `animation_run_names`,
`calibration_caveat`, `calibration_gap`, `check_animation_out`, `default_animation_path`,
`inside_calibration_band`, `load_animation_runs`.

### New tests for tests/test_run_data.py

Readers and helpers
1. `read_json` and `read_yaml`: {} for a missing file and for a non-mapping; NaN and
   Infinity literals accepted; a non-ASCII character read back as UTF-8.
2. `finite`: bool, None, text, NaN, inf give None; rounding; -0.0 gives +0.0; a numpy
   number is accepted.
3. Nothing is written: the listing of a synthetic directory is the same after every
   reader.

Compatibility
4. Identity of every re-export, parametrised: `getattr(plots, old) is getattr(run_data,
   new)`, the same for replay, and `results_io.CALIBRATION_RECORDS is
   run_data.CALIBRATION_RECORDS`.
5. `AnimationError` and `ReplayError` derive from `RunDataError` and from ValueError;
   each raising function raises the class it is given, and `RunDataError` by default.
6. The source of replay.py holds no `plots._` (the gate item, kept as a test).
7. Importing `launchsim.run_data` in a fresh interpreter loads neither matplotlib nor
   `launchsim.plots`, `launchsim.replay`, `launchsim.results_io`.

Directory, selection, roles
8. `check_run_dir`: missing directory; no metrics.json; a sweep point (no `runs`) is
   "not an experiment results directory" and not "vertical_1d"; no `model` is named
   vertical_1d; another model is named; `verb` appears in the message; a second accepted
   model passes with `models=` and is still refused by default.
9. `run_names`: baseline plus three variants in summary order; other folders after,
   sorted; a folder without timeseries.csv is left out; the result does not depend on
   the order the folders are listed in.
10. `select_runs`: unknown, repeated, none, too many (with `max_runs`), `what` in the
    message, the order of the checks.
11. `run_source`: one synthetic directory with all five roles; role, metrics,
    comparison, compared run, run block, vehicle name and note of each; a stray folder
    is refused. `offload_role` and `offload_note` for a case, a paired pad, a pad
    control and a run the block names nowhere.
12. `run_vehicle_block`: the entry's own block when present, the top-level block for an
    entry with `run` only (the `pad__offload_stage1` shape). `vehicle_masses`: 22.2 t
    gives 22,200 kg, 1.7 t gives 1,700 kg; the trigger from a block, from a string, and
    `staging` when the key is absent.

Series and resampling
13. `read_series`: the two messages; sorted, one row per time, the later row of a
    duplicated time kept; a longer column list; extra columns ignored.
    `read_series_frame` keeps duplicates and order.
14. `sample_grid`: the step pattern, both ends, no double sample when an end lies on the
    grid. `defined_mask` and `series_values`: None where a bracketing value is NaN, one
    defined value enough on a source time, all-NaN gives all None, a hand-computed
    interpolated value.
15. `run_series(frame, fields)`: key order `t`, the fields in list order, `phase`;
    adding a field leaves every other list equal, element for element.
16. Pinned digest of the `runs` block of a synthetic directory (section 6, gate step 5),
    including an event with a small negative downrange.

Events and drops
17. `read_events`: every row in file order (propellant and end included), time after
    release, the eight-column fixture accepted, a `required=` column missing refused, a
    missing file gives [].
18. The four drop cases, "kept", "no fairing" and "never staged", each from hand-written
    rows with m_dry1 = 22,200 kg and m_fair = 1,700 kg: the case found from the metric,
    and the same case found with the metric removed (row phase and the vehicle's rule);
    before and after of both drops against hand numbers (staging row 139,254.396243 kg:
    before 161,454.396243 kg in cases 1, 2, kept; 163,154.396243 kg and after
    140,954.396243 kg in cases 3, 4); the chain is continuous; the stage-1 `propellant`
    row equals the staging "before"; the case-4 row is marked not recorded.
19. Cases 3, 4 and "kept" again from the planner (`stage1` through staging with the
    vehicle rules of tests/test_planar_events.py 308-317, rows from
    `events_frame_planar` written with `CSV_FLOAT_FORMAT`): the staging "before" equals
    the mass of `trace.burnouts["stage1"]`.
20. Case 1 on a recorded directory when its CSVs exist (skipped otherwise): the fairing
    "after" equals the first series mass after the drop within 1e-6 kg.
21. `replay.run_events` and `plots._events` on a case-4 directory return what they
    return today (no added row), and no mass key.
22. `with_drop_masses(rows, None, ...)` leaves the mass fields None and does not raise.

Output rule
23. `results_tree`: nearest folder named results, case-sensitive; `parent.parent` for a
    custom root; the filesystem-root guard. `results_ancestors`: ignores case, innermost
    first. `protected_tree`: outermost; the custom-root tree; None outside.
24. `default_output_path`: cwd outside; inside the run's tree; inside another `Results`;
    nested trees. `check_output`: suffix, tree, folder, in that order, with the caller's
    words and class.
25. Animate's deliberate change (KI-017): `plots.check_animation_out` refuses an output
    in another `Results` tree and in the outer tree of a nested pair;
    `plots.default_animation_path` from a cwd inside such a tree lands next to the
    outermost one. These were accepted, or written inside the tree, at HEAD.
26. If animate takes the shared directory check: a sweep point given to
    `plots.load_animation_runs` is "not an experiment results directory".

Model-keyed columns
27. `MODEL_COLUMNS[PLANAR_2D]` holds metrics_planar's two tuples; its base and
    `replay.REPLAY_COLUMNS` are subsets of the series; an unknown model is refused with
    the known ones named; a second model registered in the test with a superset of the
    names reads through `read_series` and `run_series` with the planar field list and
    gives the planar values.
