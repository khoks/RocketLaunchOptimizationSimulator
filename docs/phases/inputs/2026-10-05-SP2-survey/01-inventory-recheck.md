Provenance: SP2 step A0 survey 01 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session's plan folder (starry-dreaming-emerson-agent-aacde06c2f22d233f.md); a record, not edited (README.md).

# 01-inventory-recheck: SP2 section 6 against HEAD b69ff0c

Surveyor report for SP2 step A0 (read-only). Repository D:/DEV/ClaudeProjects/SpaceRocketOptimization,
HEAD b69ff0c45c29, clean tree. Phase file: docs/phases/SP2-launch-app-2d-scene.md (1,359 lines),
sections 4, 5.2, 5.8, 5.10 and 6.

Where this report lives. The task asked for
`<scratchpad>/a0/01-inventory-recheck.md`. Plan mode became active during the survey and allows
writing only this plan file, so the report is here instead. Nothing in the repository was touched,
pytest was not run, no git state changed. The scratch scripts written before plan mode started are
in `C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/6999a833-8705-4f59-babb-7d35feacc46d/scratchpad/a0/`:
`inv_symbols.py` (AST symbol tables at b3150c1 and HEAD), `inv_users.py` (AST scan of users and
setattr patches), `inv_lines.py`, `inv_entry.py`, `inv_imports.py`, each with its `*_out.txt`.

## 0. The diff

    git diff --stat b3150c1 HEAD -- src tests configs experiments pyproject.toml .gitignore site/build.py
     site/build.py           | 142 +++++++++++++++++++++-
     src/launchsim/plots.py  | 216 ++++++++++++++++++++++++++++++---
     src/launchsim/replay.py |  72 ++++++-----
     tests/test_animate.py   | 316 +++++++++++++++++++++++++++++++++++++++++++++---
     4 files changed, 673 insertions(+), 73 deletions(-)

Confirmed: exactly the four files. Commits since b3150c1: ac66fd0, fd664a5, cfd9059, 5007515 (step
10a: the three launchsim files and site/build.py), d3dc509, 03fe7a7, b69ff0c. Every other inventoried
file (cli.py, config.py, results_io.py, sim.py, summary.py, compare.py, metrics.py,
metrics_planar.py, offload.py, phases/planar.py, phases/prelude.py, templates/replay.html,
tests/test_replay.py, tests/test_offload_pipeline.py, tests/test_config_planar.py,
tests/test_planar_pipeline.py, pyproject.toml, .gitignore) is byte-identical to b3150c1.

File lengths: plots.py 1,701 -> 1,881; replay.py 1,246 -> 1,244; tests/test_animate.py 526 -> 814;
site/build.py 1,028 -> 1,162. Unchanged: cli.py 510, config.py 2,898, results_io.py 2,262, sim.py
1,752, summary.py 2,196, compare.py 1,942, metrics_planar.py 1,382, metrics.py 772, offload.py 567,
phases/planar.py 1,733, phases/prelude.py 922, templates/replay.html 588, test_replay.py 682,
test_offload_pipeline.py 2,374.

## 1. Corrections table (the four changed files)

### 1a. src/launchsim/plots.py (every line the phase file gives is stale)

Shift: +3 up to old line ~406 (two docstring lines, one import), +33 at the calibration block, +48 at
the readers, +153 from `load_animation_runs` to `frame_geometry`, +172 at `calibration_caveat`, +179
at `write_ascent_animation`.

| Symbol | Phase file (b3150c1) | HEAD | Changed behaviour |
|---|---|---|---|
| `plot_stem` (not listed; used by replay) | 90 | 93-96 (`PLOT_STEM_UNSAFE` 90) | none |
| `AnimationError` | 309 | 312 | none |
| `ANIMATION_MAX_RUNS` | 321 | 324 (`ANIMATION_DEFAULT_VARIANTS` 325) | none |
| `RESULTS_TREE_NAME` | 344 | 347 | none |
| `MAIN_HEADROOM`, `MAIN_HEADROOM_PER_RUN` | 407, 408 | 410, 411; new `MAIN_HEADROOM_PER_SECOND_LINE = 0.25` at 412 | legend headroom counts second legend lines |
| `CALIBRATION_RECORDS` | 474-487 | 507-510 (docstring to 520) | none (same two records) |
| `CALIBRATION_BAND` | 488 | 521 | none |
| `CALIBRATION_BAND_EDGE_REL_TOL` | 492 | 525 | none |
| `CALIBRATION_GATE_VEHICLE` | 497 | 530 | none |
| `calibration_gap` | 501 | 534-538 | none |
| `inside_calibration_band` | 508 | 541-544 | none |
| `AnimationEvent` | 514 | 547-557 | none |
| `AnimationRun` | 528 | 573-610 (class line 574) | new field `offload: OffloadTag \| None = None` (595) |
| `ANIMATION_COLUMNS` | 565 | 613-623 | none (same nine columns) |
| `_read_json`, `_read_yaml` | 579, 588 | 627-633, 636-642 | none |
| `animation_run_names` | 597 | 645-658 | none |
| `check_planar_run_dir` | 613 | 661-680 | none |
| `_events` | 635 | 683-707 | none |
| `read_animation_run` | 662 | 813-844 | record now from `animation_record(metrics, name)` (827): an offload run gets payload and status from `offload.runs` and an `OffloadTag` (843) |
| `load_animation_runs` | 694 | 847-869 | none |
| `ascent_time_map` | 748 | 901-910 | none |
| `_results_tree` | 809 | 962-972 (name test at 969) | none |
| `_is_inside` | 822 | 975-977 | none |
| `default_animation_path` | 827 | 980-993 | none |
| `check_animation_out` | 843 | 996-1017 (tree test 1006, ffmpeg test 1011) | none |
| `frame_geometry` | 867 | 1020-1032 | none |
| `_phase_at` (not listed) | 896 | 1049-1064 | end of a pad control with `resolution_effect` reads `NEAR_ORBIT_PHASE` ("~inserted") |
| `_legend_label` (not listed) | 945 | 1103-1115 | an offload run: `"<name> (<kind>): <OffloadTag.legend>"`, no delta against the baseline |
| `calibration_caveat` | 956 | 1128-1146 (reads `CALIBRATION_RECORDS` at 1135) | none |
| `animation_caveats` | - | 1149 (calls `calibration_caveat` at 1161) | none |
| `_AscentFigure` | 1041 | 1213-1815 (`__init__` 1218, `_title` 1288, `_main_axes(self, base, title)` 1338) | legend title from `legend_title(runs, metrics)` (1245); headroom formula 1352-1356 |
| `write_ascent_animation` | 1639-1701 | 1818-1881 (`_read_yaml` use at 1863, `FFMpegWriter(...)` at 1867) | docstring only |

New in step 10a (no line in the phase file): `OFFLOAD_CASE` 488, `OFFLOAD_PAIRED_PAD` 489,
`OFFLOAD_PAD_CONTROL` 490, `OFFLOAD_SOLVED_KIND` 495, `NEAR_ORBIT_PHASE` 498, `LEGEND_TITLE` 503,
`OffloadTag` 560-570, `_as_dict` 710-712, `_finite_kg` 715-719, `offload_role` 722-737,
`offload_tag` 740-792, `animation_record` 795-810, `legend_title` 1118-1125. New import at 44:
`from launchsim.offload import NO_OFFLOAD_STATUS` (and `Mapping` at 27).

### 1b. src/launchsim/replay.py (1,244 lines; everything after `offload_note` is 2 lines lower)

Unchanged lines: `REPLAY_TEMPLATE` 62, `REPLAY_DATA_TOKEN` 64, grid constants 68-77, `ROLE_RUN` ..
`ROLE_OFFLOAD` 93-97 (the third is `ROLE_PAIRED_BASELINE`, 95), `REPLAY_COLUMNS` 102,
`SERIES_FIELDS` 119-128, `_read_json` 148, `_read_yaml` 157, `check_replay_run_dir` 166,
`select_runs` 198 (uses 203, 214, 216), `_mapping` 221, `run_source` 244-319.

| Symbol | Phase file | HEAD | Changed behaviour |
|---|---|---|---|
| `offload_note` | 322 (322-364) | 322-362 | body rewritten on `plots.offload_role` (330), `plots.OFFLOAD_PAIRED_PAD` (334), `plots.OFFLOAD_PAD_CONTROL` (339), `plots.OFFLOAD_SOLVED_KIND` (344); same strings |
| `read_series` | 367 | 365 | none |
| `_finite` | 385 | 383 | none |
| `replay_grid` | 396 | 394 | none |
| `defined_mask` | 407 | 405 | none |
| `series_values` | 417 | 415 | none |
| `run_series` | 432 | 430 | none |
| `run_events` | 447 | 445 | none |
| `push_accel_g`, `assist_text` | 521, 531 | 519, 529 | none |
| `calibration_caveat` | 664 (uses 668, 675, 677, 680; docstring 665-666) | 662-685 (uses 666, 673, 675, 678; docstring 663-664) | none |
| `structure_caveat` | - | 688 ("the fully fuelled stack" at 700) | none |
| `drive_caveat` | 736, stale sentence 763 | 734-761, stale sentence 761 | none |
| `comparison_caveats` | - | 805-840 (offload sentence 831-839) | none |
| `caveats` | 845 | 843-878 | none |
| `closeup_notes` | - | 881-925 ("and leave" at 900) | none |
| `ROLE_LABELS`, `run_label` | - | 964-968, 972 | none |
| `run_record` | 982-1062 | 980-1060 | none |
| `source_text` | 1065 (`plots._results_tree` 1069) | 1063 (1067) | none |
| `replay_data` | 1107 | 1105-1160 | none |
| `embed_json`, `load_template`, `render_page` | 1168, 1176, 1182 | 1166, 1174, 1180 | none |
| `results_ancestors` | 1190 (`RESULTS_TREE_NAME` 1195; docstring 1191) | 1188 (1193; docstring 1189) | none |
| `protected_tree` | 1199 (`_results_tree` 1205, `_is_inside` 1206; docstring 1201-1202) | 1197 (1203, 1204; docstring 1199-1200) | none |
| `default_replay_path` | 1211 (`plots.plot_stem` 1219) | 1209 (1217) | none |
| `check_replay_out` | 1224 | 1222-1234 | none |
| `write_replay_page` | 1239 | 1237-1244 | none |

### 1c. tests/test_animate.py (814 lines, 26 tests, none slow)

Old tests moved by +18; the helpers changed; four tests and three helpers are new.

| Item | Phase file | HEAD |
|---|---|---|
| file length | 526 | 814 |
| fixture helpers | 46-146 | `_row(t_rel, offset, assist, orbit=False)` 55, `_write_run(run_dir, name, assist, orbit=False)` 93, `_make_run_dir(root, model="planar_2d", extra_variants=0, orbit=False)` 134-162, `_listing` 165, `_no_ffmpeg` 169 |
| `_make_run_dir` | 119 | 134 |
| animate path tests (5.2) | 180-195 and 460-468 | `test_default_output_is_outside_the_run_dir` 198-213; `test_custom_results_root_is_protected` 478-486 |
| `test_calibration_record_matches_its_findings_note` | 281 | 299-326 |
| `test_calibration_band_includes_both_edges` | setattr at 353 | 355-375; `mp.setattr(plots, "CALIBRATION_RECORDS", edge)` at 371, `plots.calibration_caveat("edge_2d")` at 372 |
| `test_custom_results_root_is_protected` | 460 | 478 |
| users of moved names | 185-193, 255, 295-329, 348-354, 466-467 | 203-211, 273, 313-347, 366-372, 484-485 (full list in section 2) |
| new in 10a | - | `_make_offload_run_dir(root, orbit=False)` 549-636 (synthetic directory with an offload block: 3 cases, 1 paired pad, 3 pad controls); `_end_phase` 639; tests at 644, 679, 720, 739; `_legend_clearance` 782; `test_frame_geometry_is_16_by_9_and_even` now 806 |

### 1d. site/build.py (1,162 lines)

| Symbol | b3150c1 | HEAD |
|---|---|---|
| `REPLAY_DIR` | 86 | 87 |
| `REPLAY_MARKER` | 87 | 88 |
| `FRAME_PART_RE`, `BODY_OPEN_RE` | 88, 89 | 89, 90 |
| `REPLAY_STALE_TEXT` | 121 | 122 |
| `REPLAY_TEXT_FIXES` | 122-135 (1 entry) | 123-166 (5 entries) |
| `REPLAY_OFFLOAD_DRIVE`, `_ROUNDING`, `_STRUCTURE`, `REPLAY_PAGE_FIXES` | absent | 178, 183, 191, 200-260 |
| `read_replay_frame`, `frame_replay`, `fix_replay_text`, `frame_replays` | 765, 774, 793, 807 | 890-896, 899-915, 918-938, 941-957 |
| `PageScan`, `LinkChecker`, `build`, `main` | 844, 866, 957, 980 | 978, 999-1084, 1091-1103, 1114 |

`fix_replay_text` is the only function whose behaviour changed: it now also applies the page's
`REPLAY_PAGE_FIXES` and warns when an entry matches neither its old nor its new text.

## 2. Users of the names A1 moves (rebuilt at HEAD)

Code lines unless marked. Found by an AST scan of every .py under src/, tests/ and site/ (module
attribute uses, from-imports, setattr patches) plus a regex pass over strings and comments, then
cross-checked with ripgrep.

| User | Lines | Names |
|---|---|---|
| `results_io.py` | 143; 1798 (also 699, 705, 767 for `write_plots`) | `from launchsim.plots import CALIBRATION_RECORDS, write_plots`; `offload_caveats(vehicle_name, CALIBRATION_RECORDS.get(vehicle_name))` |
| `summary.py` | 1534 (docstring) | names `plots.CALIBRATION_RECORDS`; imports nothing from plots |
| `sim.py` | 200-221 (from-import), `__all__` 396 and 529 | re-exports `plot_stem` (218) and `PLOT_STEM_UNSAFE` (212) from plots, with 18 other plot names; no test uses `sim.plot_stem` |
| `replay.py` | 103; 203, 214, 216; 330, 334, 339, 344; 666, 673, 675, 678; 1067, 1193, 1203, 1204; 1217 (docstrings 18-19, 172, 200-202, 327, 663-664, 1189, 1199-1200) | `plots.ANIMATION_COLUMNS`; `plots.animation_run_names`, `plots.ANIMATION_MAX_RUNS` (x2); **new** `plots.offload_role`, `plots.OFFLOAD_PAIRED_PAD`, `plots.OFFLOAD_PAD_CONTROL`, `plots.OFFLOAD_SOLVED_KIND`; `plots.CALIBRATION_RECORDS`, `calibration_gap`, `CALIBRATION_BAND`, `inside_calibration_band`; `plots._results_tree` (1067, 1203), `plots.RESULTS_TREE_NAME` (1193), `plots._is_inside` (1204); `plots.plot_stem` |
| `plots.py` (replay names, docstrings only) | 726, 800 | `replay.offload_note`, `replay.run_source` |
| `cli.py` | 444, 446, 450 (also 120, 128, 135, 451, 452, 453, 461, 469); 480, 482, 484, 485 | `plots.load_animation_runs`, `plots.default_animation_path`, `plots.check_animation_out` (and `ANIMATION_DEFAULT_FPS/_SECONDS/_WIDTH_PX`, `animation_playback_fps`, `animation_frame_count`, `frame_geometry`, `write_ascent_animation`, `AnimationError`); `replay.check_replay_run_dir`, `replay.default_replay_path`, `replay.write_replay_page`, `replay.ReplayError` |
| `site/build.py` | none | does not import launchsim. It depends on text only: the marker (88, tested at 948), the stale sentence (122), exact page strings in `REPLAY_TEXT_FIXES` and `REPLAY_PAGE_FIXES`; comments name replay.py at 120, 169, 176, 930, 936 and replay.html at 153 |
| `tests/test_animate.py` | 36; 203, 206, 211, 485; 264, 277, 282, 439, 653, 690, 726, 764; 273; 313, 314, 322, 347; 335, 339, 342, 343, 372; 366, 368; 484 | `plots.ANIMATION_COLUMNS`; `plots.default_animation_path`; `plots.load_animation_runs`; `plots.animation_run_names`; `plots.CALIBRATION_RECORDS`; `plots.calibration_caveat`; `plots.calibration_gap` and `plots.inside_calibration_band`; `plots.check_animation_out` |
| `tests/test_animate.py` (10a names) | 660, 729; 661; 693; 699; 674-676; 674, 676; 709, 716, 717; 656-735 (11 calls); 641; 639 | `plots.OFFLOAD_CASE`; `OFFLOAD_PAIRED_PAD`; `OFFLOAD_PAD_CONTROL`; `NEAR_ORBIT_PHASE`; `LEGEND_TITLE`; `plots.legend_title`; `plots.animation_record`; `plots._legend_label` (private); `plots._phase_at` (private); `plots.AnimationRun` |
| `tests/test_replay.py` | 336, 338, 345, 352; 381, 622, 625; 432; 483; 504; 506 | `replay.calibration_caveat`; `replay.default_replay_path`; `replay.ROLE_BOUND`; `replay.replay_grid`; `replay.SERIES_FIELDS`; `replay._finite` (private) |
| `tests/test_replay.py` (other replay names) | 40; 175; 370; 486-489; 395, 397, 464, 617, 642; 362, 365; 369, 629; 501, 505; 13 calls from 321 to 643; 281, 396, 398, 594, 618, 671 | `REPLAY_COLUMNS`; `DRY_MASS_PARAM`; `REPLAY_DATA_TOKEN`; `REPLAY_EARLY_END_S`, `REPLAY_EARLY_DT_S`, `REPLAY_LATE_DT_S`; `ReplayError`; `embed_json`; `load_template`; `wrapped_deg`; `replay_data`; `write_replay_page` |
| `tests/test_config_planar.py` | 1376, 1378 | `plots.CALIBRATION_RECORDS` |
| `tests/test_offload_pipeline.py` | 842, 1733, 2023, 2038, 2061 (docstring 124); 1087, 1095, 1096; 1088; 973; 1098, 2318; 1103 | `plots.CALIBRATION_RECORDS`; `replay.run_source`; `replay.ROLE_OFFLOAD`; `replay.REPLAY_COLUMNS`; `replay.replay_data`; `replay.write_replay_page` |

No user outside plots.py: `CALIBRATION_BAND_EDGE_REL_TOL` (plots 525, 544), `CALIBRATION_GATE_VEHICLE`
(530, 1142), `read_animation_run` (813, called at 869), `check_planar_run_dir` (661, called at 853;
replay docstring 172), `plots._read_json` (650, 667, 984), `plots._read_yaml` (1863), `plots._events`
(839). The `_events` helpers in tests/test_replay.py 85 and tests/test_failed_ignition.py 159 are
unrelated local functions. No test imports with `from launchsim.plots import` or
`from launchsim.replay import`; every test goes through the module attribute.

CLI-level users (through `main`): tests/test_animate.py 223, 254, 265, 517, 528, 754 (`animate`);
tests/test_replay.py 384, 404, 416, 421, 659 (`replay`).

### Monkeypatches (these constrain where a function may live)

| Where | Patch | What it pins |
|---|---|---|
| tests/test_animate.py 371 | `mp.setattr(plots, "CALIBRATION_RECORDS", edge)`, then `plots.calibration_caveat("edge_2d")` at 372 | `plots.calibration_caveat` (1128) must read the name `CALIBRATION_RECORDS` from the plots module's globals at call time (as 5.2 says; the line was 353) |
| tests/test_animate.py 515 | `monkeypatch.setattr(plots, "FFMpegWriter", _BrokenFFMpeg)`, then `main(["animate", ..., "--out", "a.mp4"])` expecting "error: ffmpeg failed" | `check_animation_out` (ffmpeg test at plots 1011), `default_animation_path` (988) and `write_ascent_animation` (1867) all resolve `FFMpegWriter` in the plots namespace. A shared `check_output` in run_data that asked the real `FFMpegWriter.isAvailable()` would make this test fail on a machine without ffmpeg (it would stop at "writing .mp4 needs ffmpeg"). Not in the phase file (was line 497 at b3150c1) |
| tests/test_animate.py 170 (`_no_ffmpeg`, used at 221, 245, 752) | `monkeypatch.setattr(plots.FFMpegWriter, "isAvailable", classmethod(lambda cls: False))` | patches matplotlib's class object, so it holds wherever the check lives, as long as `plots.FFMpegWriter` stays an attribute of plots |
| replay | none | no test patches the replay module |

Other setattr patches in the suite (not on names A1 moves, relevant to the app's composition of the
run path): tests/test_offload_pipeline.py patches `sim.run_resolved` 1593, `sim.rerun_resolved`
1594, `sim.matched_run` 1595, `sim.solve_resolved_offload` 1596, `sim.offload_run_result` 1597,
`results_io.attributed_comparison` 1598, `results_io.planar_comparisons` 1341/1798/2109,
`results_io.planar_bounds` 1342/1799, `results_io._offload_arm_record` 1677,
`results_io.offload_sweep_point` 2107, `results_io.write_single` 2108; tests/test_results_io.py
patches `sim._git` 205/215/275 and `sim.run` 438/459/851. results_io reaches these through the
`sim` module attribute.

## 3. What step 10a added

| Symbol | Signature and lines | What it does | Callers | Shared module? |
|---|---|---|---|---|
| `OFFLOAD_CASE`, `OFFLOAD_PAIRED_PAD`, `OFFLOAD_PAD_CONTROL` | plots 488-490: `"offload case"`, `"paired pad"`, `"pad control"` | the kind of a run of metrics.json `offload.runs`; the strings are printed in the animation legend | plots 730-780; replay 334, 339; tests 660, 661, 693, 729 | yes, with `offload_role` (re-exported from plots) |
| `OFFLOAD_SOLVED_KIND` | plots 495: `"solve"` | `kind` of a solved case in `offload.cases` | plots 775; replay 344 | yes |
| `offload_role` | `offload_role(offload: Mapping[str, Any], name: str) -> tuple[str, dict[str, Any]] \| None`, plots 722-737 | (kind, record): the case record whose `run` is `name`; the case record whose `paired_pad.run` is `name`; the `pad_controls` record whose `run` is `name`; None otherwise. Pure, needs only `_as_dict` | `plots.offload_tag` 757; `replay.offload_note` 330; no test calls it directly | yes. It is the missing half of `run_source` (which only says role "offload") and is already used by both modules |
| `OffloadTag` | frozen dataclass, plots 560-570: `kind: str`, `legend: str`, `resolution_effect: bool = False` | how the animation labels an offload run | `AnimationRun.offload` 595; `_phase_at` 1059; `_legend_label` 1107 | no: legend text for the animation |
| `offload_tag` | `offload_tag(offload: Mapping[str, Any], name: str, record: Mapping[str, Any]) -> OffloadTag`, plots 740-792 | the two-line legend text (joined by "\n") from the run's record (`payload_kg`, `status`), `offload.reference_payload_kg` and the role record (`total_offload_kg` for a case, `offload_kg` for a control, `kind`, `status`, `resolution_effect`, `m_res_kg`); needs `NO_OFFLOAD_STATUS` from launchsim.offload, `kg_to_t`, `_finite_kg` | `plots.animation_record` 809 | no as written (wording and line layout of the animation, tied to `MAIN_HEADROOM_PER_SECOND_LINE`). The facts it reads are what the scene's HUD and results panel need, so the shared module should expose them as data and plots should format |
| `animation_record` | `animation_record(metrics: Mapping[str, Any], name: str) -> tuple[dict[str, Any], OffloadTag \| None]`, plots 795-810 | the run's record from `runs`, else from `offload.runs` with its tag, else `({}, None)` | `plots.read_animation_run` 827; tests 709, 716, 717 | partly: the lookup duplicates `replay.run_source` for two of its five roles. A bound re-run or a case still gets `{}`, so by reading `_legend_label` (1110-1111) animate labels it "P* n/a (None)" (not run here). Keep the function in plots (tests call it); it can sit on the shared lookup |
| `legend_title` | `legend_title(runs: Sequence[AnimationRun], metrics: Mapping[str, Any]) -> str`, plots 1118-1125 | `LEGEND_TITLE` (503), or with an offload run shown `"<LEGEND_TITLE>; P_ref = <offload.reference or baseline>'s P*"` | `_AscentFigure.__init__` 1245 -> `_main_axes(base, title)` 1338; tests 674, 676 | no (animation text) |
| `NEAR_ORBIT_PHASE` | plots 498: `"~inserted"` | readout phase at the end of a pad control short of orbit by a resolution effect | `_phase_at` 1060; test 699 | no (animation text); the fact `resolution_effect` is data the scene needs |
| `_as_dict`, `_finite_kg` | plots 710, 715 | mapping-or-{} ; finite float or None | plots only | duplicates: `_as_dict` is identical to `replay._mapping` (221); `_finite_kg` is `replay._finite` (383) without rounding and numpy scalars. One copy each belongs in run_data |
| `replay.offload_note` | `offload_note(offload: Mapping[str, Any], name: str, baseline: str) -> str`, replay 322-362 | the note of an offload run for the replay page; since 10a it classifies with `plots.offload_role` | `replay.run_source` 314 | stays in replay (page wording); its strings did not change (test_offload_pipeline 1093-1096 unchanged) |

Import cost of the new dependency: `launchsim.offload` loads `search`, `guidance`, `atmosphere`,
`phases.*` and `ambiance` (22 launchsim modules). `plots` already loaded `config` and
`phases.planar`; `config` alone loads numpy, scipy and pydantic (about 1.1 s here). Measured import
times in fresh interpreters: units 0.16 s, config 1.08 s, offload 1.15 s, plots 2.09 s, replay
2.15 s, cli 1.72 s (noisy, one sample each).

## 4. Spot-check of the unchanged files (section 6)

All files are byte-identical to b3150c1. 107 definitions of section 6 were located by AST at both
commits and more than 200 further lines (the sub-line references) were printed and read.
Everything holds except one line that was already wrong at b3150c1:

| Claim | Finding |
|---|---|
| `_resolved_config_dict` at results_io.py 588 | it is at 590-622 (587 is the section comment, 588-589 blank). `runs` inline is 597-601, not 597-599; `git` at 605 holds |
| class lines given one above the AST start | `ResolvedRun` 2346, `ResolvedExperiment` 2470, `OffloadReport` 276, `ExperimentResult` 292, `OffloadResult` 307, `AnimationRun`: the phase file gives the `class` line; the decorator is one line above. `_labelled_features` 1948 is its decorator line. Not errors |

Checked and holding (file: lines): cli.py 11-17, 58-161, 65, 67, 73, 79, 85, 90, 95-138, 140-160,
191, 254-276, 272, 273, 285, 309, 317, 377-414, 417-437, 440-472, 475-488, 491-510, 497-502;
config.py 88, 91, 143, 148-149, 157-159, 584, 613, 726, 761, 875, 897, 1441, 1459, 1521, 1549, 1555,
1559, 1619, 1676, 1709, 1865, 1948-1987, 2102, 2107, 2346, 2470, 2483, 2816-2898; results_io.py
143, 167, 186, 187, 234, 276, 292, 365, 400, 567, 625, 687, 793-889, 830-831, 834, 836, 837-852,
886-887, 960, 999, 1687, 1798, 1973-2027, 2120, 2143; sim.py 876, 896, 932, 1708, 1717, 1728;
offload.py 307, 472; summary.py 1491, 1500, 1534, 1897, 2008; compare.py 1639, 1657; metrics.py 60;
metrics_planar.py 298, 340, 351, 380, 393-399, 669, 933, 963-1026, 1029, 1041, 1062, 1225, 1234;
phases/planar.py 171, 174, 234, 451, 475, 1299, 1305, 1317, 1351, 1357, 1672, 1684, 1689, 1690,
1691-1692; phases/prelude.py 84 (`resolve_ignition` at 231-294); templates/replay.html 7-9, 13,
197, 198-585, 586, 213, 230, 235, 242, 250, 263, 348, 370-411, 509-515, 516, 526, 539;
tests/test_replay.py 49-260, 183, 311, 368, 628, 665-682; tests/test_offload_pipeline.py 1077,
2165-2181, 2185, 2291; tests/test_config_planar.py 323, 1376, 1378; tests/test_planar_pipeline.py
1146. Values: `len(PLANAR_TIMESERIES_COLUMNS) == 32`; `IntegratorConfig.sample_dt_s` default 0.05;
`OffloadConfig.reference_run` has alias `reference`; pyproject.toml dependencies are numpy, scipy,
pandas, matplotlib, pydantic, pyyaml, ambiance (Pillow not declared), build backend `uv_build`,
ruff line length 100, pytest `filterwarnings = ["error"]`.

## 5. Entry criteria 2 to 6 and 10 (read-only)

- Item 2. `ConstantAccelConfig` config.py 613 with fields `net_accel_g`, `exit_speed_mps`,
  `stroke_m`; `ASSIST_KEY_FAMILIES` 88 = `(("net_accel_g",), ("exit_speed_mps",))`; `IgnitionConfig`
  761 with `t_ign_s`, `reference`, `at_depth_m`, `at_speed_mps`, `at_height_m`, `height_method`,
  `startup`, `fails`; `IGNITION_KEY_FAMILIES` 91 has four families; `RAMP_START_TRIGGERS` =
  `("time", "depth", "speed", "height_closed_form", "height_event")`; `prelude.resolve_ignition`
  231; `IGNITION_HEIGHT_EVENT` prelude.py 84; `GuidanceFailure("no_ignition")` raised in
  phases/planar.py 1599-1615; `OffloadConfig` 1709 (`reference_run` alias `reference`, `cases`,
  `pad_control`, `sensitivity_of`, `energy`); `OffloadCaseConfig` fields `name`, `of`, `solve`,
  `fixed`, `stage2_offload_t`, `stage1_dry_mass_added_t`, `paired_pad`; `OFFLOAD_FIXED_KEYS` =
  `stage1_t`, `stage1_fraction`, `stage2_t`, `stage2_fraction`, `both_fraction`;
  `SweepConfig.offload` 1459; `sim.check_resolved` 932, called at results_io.py 831 and 2143 and
  cli.py 273. Test files exist: test_config.py (56 tests), test_silo.py (31), test_height_event.py
  (24, 1 slow), test_offload.py (14, 3 slow), test_offload_pipeline.py (38, 5 slow).
- Item 3. `test_offload_in_memory_writes_nothing` at tests/test_offload_pipeline.py 2185 (slow
  marker 2184); fixture `offload_e2e` 2165-2181.
- Item 4. `replay.ROLE_OFFLOAD` 97, `run_source` 244, `offload_note` 322;
  `test_replay_shows_an_offload_run_beside_the_pad` 1077 (no slow marker);
  `test_offload_outputs_written_and_replayed` 2291 (slow marker 2290). The 298,591-byte page was
  not re-written (it would need a write).
- Item 5. metrics_planar.py: `PUSH_SETTING_METRICS` 933 = `stroke_m`, `net_accel_mps2`,
  `net_accel_g`; `planar_track_metrics` 963-1026 writes `exit_speed_mps` 995, `push_time_s` 996,
  `braking_distance_m` 1014, `facility_length_m` 1015, `track_start_altitude_m` 1020,
  `carriage_mass_kg` 1021; `RAMP_START_METRICS` 1029 (six keys as stated);
  `RAMP_START_REQUEST_METRICS` 1041 (five keys as stated); `OFFLOAD_METRIC_KEYS` 1225 =
  `offload_mode`, `offload_kg`, `offload_status`, `offload_reference_payload_kg`.
- Item 6. All present:

  | Directory | Run folders with timeseries.csv | Top-level files | Size |
  |---|---|---|---|
  | results/silo_screening_2d/20260930T175743Z | 12 (the stated names) | metrics.json, resolved_config.yaml, summary.md | 45.9e6 bytes |
  | results/silo_offload_2d/20261003T112934Z | 19: 4 in `runs` (pad, silo_cold, silo_hot_ramp_on_track, silo_cold_200m), 15 in `offload.runs` (11 cases, paired pad silo_cold_s1__pad, 3 pad controls); git b3150c1754ee, dirty false | same three | 74.3e6 bytes |
  | results/silo_offload_2d/20261003T112949Z | 21 at depth: baseline plus sweep_1..sweep_5 holding 5+4+5+4+2 = 20 points (`sweep_k/run_000n`) | summary.md only (no metrics.json) | 85.5e6 bytes |
  | results/silo_offload_2d_readme/20261003T112956Z | 5: pad, pad__offload_stage1, silo_cold, silo_cold_s1, silo_cold_s1__pad | three | 17.6e6 bytes |
  | results/calibration_f9_2d/20260930T173928Z and 20260930T100100Z | 8 each | three | 16.8e6 bytes each |
  | results/silo_bridge_2d_readme/20260930T185034Z | 4 | three | 14.3e6 bytes |

  The phase file's 72, 83, 45 and 17 MB are these byte counts divided by 1.024e6; no discrepancy.
  `silo_cold_s1/timeseries.csv` is 3,630,414 bytes, as stated.
- Item 10. node v24.11.1 at C:\nvm4w\nodejs\node.EXE; ffmpeg 8.1-full_build (gyan.dev) on PATH
  under the WinGet packages folder, and matplotlib's `FFMpegWriter.isAvailable()` is True; uvx and
  uv 0.12.13; gh 2.89.0; Python 3.12.11; matplotlib 3.11.2; Pillow 12.3.0. A browser was not tested.
- `.gitignore` is unchanged (22 lines) and has **no** `!docs/demos/**` line:

      1  # environments and caches
      2  .venv/
      3  __pycache__/
      4  *.pyc
      5  .pytest_cache/
      6  .ruff_cache/
      7  .ipynb_checkpoints/
      8
      9  # generated results: keep only the top-level summary of each run directory (CLAUDE.md)
      10 results/**
      11 !results/.gitkeep
      12 !results/*/
      13 !results/*/*/
      14 !results/*/*/summary.md
      15
      16 # default outputs of `launchsim animate` and `launchsim replay` (written to the current directory)
      17 *_animation.mp4
      18 *_animation.gif
      19 *_replay.html
      20
      21 # the GitHub Pages site, built by site/build.py (deployed by .github/workflows/pages.yml)
      22 _site/

  SP1's demo avoided the patterns by its file names (docs/demos/SP1/pad_vs_offloaded_silo.html and
  .png, tracked). `git check-ignore` confirms `docs/demos/SP2/x_replay.html` would be ignored by
  line 19; `docs/demos/SP2/pad_vs_silo_cold_scene.html` is not ignored today and would be once a
  `*_scene.html` pattern is added.

## 6. site/build.py and the gallery

Constants at HEAD:

    REPLAY_DIR = "examples"                                  # 87
    REPLAY_MARKER = "Written by launchsim replay"            # 88; templates/replay.html line 13
    REPLAY_STALE_TEXT = "Each of these favours the assisted runs."   # 122

`REPLAY_TEXT_FIXES` (123-166) is a tuple of five (old, new) pairs applied to every framed page:

1. the drive caveat of an all-silo selection: "The drive is a prescribed 3 g push with no force or
   power limit, the carriage is massless, the shaft has no air drag and the pitch kick has no
   aerodynamic penalty. " + `REPLAY_STALE_TEXT` -> the same first sentence followed by "Under this
   drive the release speed and the payload do not depend on the carriage mass or the shaft drag:
   the massless carriage biases the drive energy and peak power low, and the missing shaft drag
   biases those and the interface force low (by about 0.04%, 0.08% and 0.08%). The free kick
   favours the silo runs, whose q-alpha at the kick is above the pad's." (replay.py 761);
2. "starts 100 m below ground and leave the silo mouth" -> "... and leaves the silo mouth" (a
   grammar bug of `replay.closeup_notes`, replay.py 900: "and leave" is not conjugated for one
   run);
3. the close-up's lower bound in the template's JavaScript (`const yr = [deepest > 0 ? -1.6 *
   deepest : ...`) deepened so the "silo floor" label clears the time axis;
4. the x-axis tick label `ctx.fillText(fmt(x, xs < 1 ? 1 : 0), px, box.y + box.h + 4);` clamped
   inside its canvas;
5. the timeline's event label `ctx.fillText(EVENT_LABEL[e.name] || e.name, x, 0)` clamped.

New since b3150c1: `REPLAY_PAGE_FIXES` (200-260), a dict from a page's file name to (old, new)
pairs applied after the text fixes: "pad-vs-silo-offload.html" has 4 pairs and
"offload-vs-paired-pad.html" has 7, sharing `REPLAY_OFFLOAD_DRIVE` (178), `REPLAY_OFFLOAD_ROUNDING`
(183: "41.3 t ... 10.0% ... 8.0%" -> "41.26 t ... 10.04% ... 7.96%") and `REPLAY_OFFLOAD_STRUCTURE`
(191: "the fully fuelled stack" is wrong for an offloaded run; replay.py 700). The others reword
the subtitle, the label `"silo_cold_s1__pad (offload)"` -> `"(paired pad)"` (replay.py
`ROLE_LABELS` 967), the paired-pad note (replay.py 334-338) and the comparison caveat (replay.py
831-839, which says a paired pad measures "propellant saved ... not a payload change"; it flies
its own payload capacity). `REPLAY_OFFLOAD_DRIVE` matches text that pair 1 above produced.

How a replay page is handled:

- found: `frame_replays(out, log)` 941-957 globs `out/examples/*.html` (946) and skips any page
  without `REPLAY_MARKER` (948). `copy_sources` 875-887 has already copied all of site/ (minus
  build.py and templates/), so an unmarked page is still published, unframed;
- framed: `read_replay_frame()` 890-896 reads site/templates/replay-frame.html into the parts
  head, top, bottom (`FRAME_PART_RE` 89); `frame_replay(text, parts, root)` 899-915 inserts head
  before `</head>`, top after the `<body ...>` tag (`BODY_OPEN_RE` 90) and bottom before the last
  `</body>`, with `{{root}}` = "../" (951); a page without head and body is a build error (953).
  The frame's styles use the page's own tokens `--panel`, `--rule`, `--ink`, `--ink-2`, `--focus`,
  `--font-display`, `--run-0`, `--run-1` and override `--ink-3` (#626c71 light, #87919a dark) and
  the light `--caution` (#845a00); its top bar links `index.html` relative to the page;
- text: `fix_replay_text(text, label, log)` 918-938 applies the two fix tables; a page that still
  holds `REPLAY_STALE_TEXT` is a build **error** (932-937); a page fix that matches neither its old
  nor its new text is a warning (927-931);
- stamps: `write_stamps` 960-971 fills `<!-- stamp -->` markers where present (replay pages have
  none);
- link check: `LinkChecker.run` 1020-1034 parses every `*.html` under the output (`PageScan`
  978-996: `id`, `a name`, `href`, `src`, `poster`, `xlink:href`, `srcset`); `check` 1040-1066
  skips http(s) except this repository's GitHub blob/tree links, requires a fragment-only link to
  match an id on the page, and requires every relative link to be a file inside the site;
  `check_repo_refs` 1068-1084 fails a GitHub link to a missing or git-ignored path. `build`
  1091-1103 runs copy, frame, stamp, manual, link check; `main` prints "replay: N pages" (1148).

The gallery holds five replay pages (failed-ignition, ignition-timing, pad-vs-silo-cold,
pad-vs-silo-offload, offload-vs-paired-pad; 114 to 305 KB), a hand-written site/examples/index.html
and media/.

What an exported scene page would need:

1. its own marker string in the scene template (for example a `SCENE_MARKER` beside `REPLAY_MARKER`)
   and a loop that frames pages carrying it; without one the page is published without the site
   bar, favicon and rights notice;
2. to live in site/examples/ (the frame's "Animation examples" link and `{{root}}` assume it), under
   a name that the `.gitignore` output pattern does not match;
3. either the same token names as replay.html, so replay-frame.html can be reused (if the scene
   already uses the site's `--ink-3` and `--caution` values the two overrides are no-ops), or its
   own frame file;
4. not to pass through `REPLAY_TEXT_FIXES`/`REPLAY_PAGE_FIXES` (they are exact strings of replay's
   output), and not to carry `REPLAY_STALE_TEXT` if it does share the loop (build error);
5. a `<head>`, a `<body>` and a `</body>`; only links that resolve inside `_site` (Google Fonts
   https links are skipped; any `href="#id"` or `xlink:href="#id"` needs that id on the page);
6. a hand-edited card in site/examples/index.html, and a count line in `main` if wanted.

## 7. Statements of the phase file that HEAD contradicts

1. Every plots.py line in 5.8 items 2-3 and in section 6 ("Animate" table, replay table notes) is
   stale; section 6's heading "plots.py (1,701 lines)" is 1,881 (table 1a).
2. replay.py is 1,244 lines, not 1,246 (5.9 and section 6), and every line after 322 is 2 lower
   (table 1b); 5.8 item 5's `drive_caveat` (736) is 734 with the stale sentence at 761.
3. tests/test_animate.py is 814 lines, not 526; the setattr of 5.2 and section 6 is at 371, not
   353; the path tests are 198-213 and 478-486, not 180-195 and 460-468; helpers 55-162
   (`_make_run_dir` 134, not 119); 299 not 281; 478 not 460.
4. Section 6's users table omits the 10a uses in replay.py (330, 334, 339, 344: `plots.offload_role`
   and three `plots.OFFLOAD_*` constants), so 5.2's "plots.py and replay.py switch to the public
   names" covers more names than listed.
5. The users table also omits, at b3150c1 already, `plots.load_animation_runs` (test_animate 264,
   277, 282, 439 and the new 653, 690, 726, 764) and `plots.ANIMATION_COLUMNS` (test_animate 36),
   and it names one monkeypatch where there are three (170, 371, 515).
6. 5.8 item 5, 5.9 and R17 describe `REPLAY_TEXT_FIXES` as one entry to drop. It has five entries
   (two about replay.py wording, three about the template's JavaScript) and there is a second
   table, `REPLAY_PAGE_FIXES`, that the phase file never names.
7. 5.8 item 3 lists the duplicates between plots and replay as the readers, the event reader and
   the calibration caveat. Since 10a there are three more: `plots._as_dict` (710) and
   `replay._mapping` (221); `plots._finite_kg` (715) and `replay._finite` (383);
   `plots.animation_record` (795) and `replay.run_source` (244).
8. Section 6 gives `_resolved_config_dict` at results_io.py 588; it is at 590 (wrong at b3150c1
   too).

## 8. Consequences for the design

1. A1's re-export list from plots must add `offload_role`, `OFFLOAD_CASE`, `OFFLOAD_PAIRED_PAD`,
   `OFFLOAD_PAD_CONTROL`, `OFFLOAD_SOLVED_KIND` if they move (tests use `plots.OFFLOAD_*` at 660,
   661, 693, 729), and keep `animation_record`, `legend_title`, `LEGEND_TITLE`, `NEAR_ORBIT_PHASE`,
   `_legend_label`, `_phase_at`, `AnimationRun`, `OffloadTag` in plots.
2. The ffmpeg test must stay in a plots function: `plots.check_animation_out` stays a plots
   function that calls the shared path rule and then tests `FFMpegWriter` from the plots namespace
   (test_animate 515). Its order of checks is suffix, results tree, ffmpeg, folder exists; replay's
   is suffix, tree, folder. A shared `check_output` therefore needs to be callable in two parts or
   take a hook, and take the error type and the noun ("animation"/"page") of the message.
3. `plots.calibration_caveat` stays in plots and reads `CALIBRATION_RECORDS` from plots' globals
   (test_animate 371-372), as 5.2 says.
4. `default_output_path` in run_data needs `plot_stem`. run_data cannot import plots (plots will
   import run_data), so `plot_stem` and `PLOT_STEM_UNSAFE` (plots 90-96) move to run_data and are
   re-exported by plots; sim.py 212, 218 and `sim.__all__` 396, 529 then keep working unchanged.
5. run_data must not import plots, replay, results_io or summary. `PLANAR_2D`/`VERTICAL_1D` come
   from config (pydantic and scipy load, about 1 s). `offload_tag` needs
   `launchsim.offload.NO_OFFLOAD_STATUS`, which loads the search stack; leaving `offload_tag` in
   plots keeps run_data free of it.
6. The scene should label an offload run by `offload_role`'s kind, not by replay's `ROLE_LABELS`
   "(offload)" (the site already rewrites that label for a paired pad), and take its facts
   (payload, P_ref, offload kg, `resolution_effect`, `m_res_kg`, solved or fixed, status) from one
   shared accessor instead of re-deriving them a third time.
7. Wording the scene must not inherit from replay.py, each patched today by site/build.py: 761
   (stale drive sentence), 900 ("and leave"), 700 ("fully fuelled stack" for an offloaded run), 967
   (paired pad labelled "offload"), 831-839 (a paired pad described as measuring propellant saved),
   348-353 (headline rounded to 41.3 t / 10.0% / 8.0%), and three clipped or overlapping labels in
   the template's canvas code. If the scene template copies replay's drawing helpers, it copies
   the three JavaScript defects too.
8. If A0 takes 5.8 item 5, the honest scope is larger than one sentence: fixing replay.py and the
   template after A1's byte-identical gate lets up to five `REPLAY_TEXT_FIXES` entries and both
   `REPLAY_PAGE_FIXES` pages go, and all five gallery pages must be regenerated in the same change
   (the build errors on the stale sentence and warns on page fixes that no longer match).
9. A1's byte-identical gate should include an offload selection that exercises all three kinds
   through `offload_role`, for example `results/silo_offload_2d/20261003T112934Z --runs pad
   silo_cold_s1 silo_cold_s1__pad pad__offload_stage1`, and a directory with bound re-runs
   (silo_screening_2d/20260930T175743Z).
10. Replacing `animation_record`'s lookup by `run_source` would give bound re-runs and cases a
    payload in the animation legend (today "P* n/a (None)"). That changes animate's output: either
    keep the lookup as it is in A1 or log it as a deliberate change with a test.
11. `tests/test_animate.py::_make_offload_run_dir` (549-636) is a ready synthetic results directory
    with an offload block (solved case, fixed case, no-offload case, paired pad, three pad
    controls) for run_data and scene tests without a simulation.
12. `.gitignore`: add the scene's default pattern together with `!docs/demos/**` (or name the demo
    file so the pattern misses it). A git-ignored file linked from the manual or the site fails the
    site build (build.py 1078-1079).
