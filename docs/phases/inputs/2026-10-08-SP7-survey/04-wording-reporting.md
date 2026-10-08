<!-- Record of SP7 step 0: read-only survey 04-wording-reporting (the 'nothing structural' wording and the reporting SP7 owns), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0 survey 04: the "nothing structural" wording and the reporting SP7 owns (HEAD 22c62e9)

Summary. At HEAD 22c62e9 (clean tree) the claim that no structural mass is charged has eleven code sources, not the five (plus the form text) that section 5.1 of the phase file lists. The sources the brief does not name are `scene.structure_note`, `app.SP1_HEADLINE` and its "Structure." caveat, the summary's case-row label, and three sentences that do not say "no structural mass" but turn false once a structure is charged. Those three are `sim.OFFLOAD_ASSUMPTIONS`, the tank item of `summary.OFFLOAD_CAVEATS` and the "dry masses unchanged" clause of `compare.OFFLOAD_COMPARISON_BASIS`. Most sources are run-specific: they stay true for every run that charges no structure. Four make claims about the whole program that SP7 makes false: "no structural model exists" in `replay.penalty_structure_sentence` and in app.py's "Structure." caveat; "no structural model exists yet" in site/build.py; and the drive item of `OFFLOAD_CAVEATS`, which is printed for every offload block whatever its drive. Every reader decides whether a run is a penalty row through one function, `replay.penalty_added_kg`, which reads `stage1_dry_mass_added_kg`. If SP7 stored a modelled mass under that key, every page would call it an assumed penalty. The tests pin the wording in the eight files the brief names, in 24 assertions, plus 11 selector filters on the word "structural". Counted the brief's way the six SP2 files hold 25 lines, which matches the brief. The six gallery pages regenerate byte-identical at HEAD with their recorded commands, and their source directories and CSVs are on disk. If the uncharged sentences stay as they are for runs without a structure, SP7 does not need to change any gallery page. KI-039's section name is quoted in about 30 places, among them replay.py 1399, which points the gallery pages at it. Splitting the imposed cases out avoids renaming it. KI-036 is a one-line data fix that the frozen template allows only by putting the state into `meta.git`. Only one of the app's checks compares files: `sp1_files_same` diffs experiments/silo_offload_2d.yaml and the vehicle file. A change to src/ alone, or a new configs/structures/ file, does not end the reproduction mark unless it moves x* by more than 0.002 kg.

## 1. Method and state

- Facts. HEAD 22c62e9, `git status` clean before and after the survey. Everything below was read at HEAD with grep and sed. Two read-only checks were run, writing only to the scratchpad: a count script (scratchpad .../04-wording-reporting/count_pins.py) and the six gallery regeneration commands with `--out` in the scratchpad (section 7). No file in the repository was edited, and no run, sweep, app or test suite was started.
- "Run-specific" below means the sentence describes the runs it is printed for and stays true for any run that charges no structure. "Global" means it states something about the program, which SP7 makes false for every run.

## 2. The code sources at HEAD

### 2.1 Sources that say no structural mass is charged

| # | File:line | Holder | Text (abridged) | Kind | Who calls it and where it goes |
|---|---|---|---|---|---|
| C1 | src/launchsim/summary.py:1680-1682 | `OFFLOAD_CAVEATS[1]` (tuple at 1677) | "no structural mass is charged for the push load (the fully fuelled stack rides the push ...); the penalty rows add an assumed stage-1 dry mass, a parametric assumption, not a sized structure" | block-wide (every offload block) | `summary.offload_caveats` 1730 -> `results_io.planar_offload` 1687 writes it into the metrics.json `offload.caveats` record (1798) -> printed by `summary.offload_section` 2074 (called at 2218 by `planar_experiment_summary` 2185), and read back as data by scene.py 1389-1437 (the page's `caveats` and `offload_caveats`) and by the app's results panel (app.py 2839-2842). Recorded directories keep their recorded text. |
| C2 | src/launchsim/summary.py:761 | `EXPLORATORY_PUSH_CAVEAT` = "no structural mass for the push" | | run-specific (any app launch with a push) | `exploratory_banner` 814, line 861, called by `planar_experiment_summary` 2205. Fact: the banner prints it for an app penalty-row launch too, beside the case row that charges the assumed mass. |
| C3 | src/launchsim/replay.py:966 | `uncharged_structure_sentence` 948 | "No structural mass is charged for the assist load case: <run> (<load>) feels up to <g> during the push." | run-specific (only runs without a penalty) | `structure_caveat` 1011 (1040) <- `replay.caveats` 1492 (1507) <- `replay_data` 1779 (meta.caveats 1829) <- `write_replay_page` 1885, `scene_payload` 1329 (scene.py 1389), app panel (app.py 2832) |
| C4 | src/launchsim/replay.py:1004-1008 | `penalty_structure_sentence` 978 | "An assumed +X t of stage-1 dry mass is charged on <run> (...): a parametric assumption, not a sized structure; no structural model exists." | first clause run-specific; "no structural model exists" global | `structure_caveat` 1042; same chain as C3 |
| C5 | src/launchsim/scene.py:1310 and 1312-1313 | `structure_note` 1296 (not in the brief) | "no structural mass is charged for the push"; penalty: "an assumed +X t of stage-1 dry mass is charged for the push: an assumption, not a sized structure" | run-specific | `run_payload` 983 (1134) -> payload `runs[].structure_note` -> templates/scene.html 2665-2670 (the captured frame's footer; the app video footer as well) |
| C6 | src/launchsim/plots.py:1069 (penalty clause 1070-1074) | `animation_caveats` 1049 | "; no sized structural mass for the <max peak> g push load" (+ "; the penalty row(s) charge(s) an assumed stage-1 dry mass") | applies to the whole selection | `_AscentFigure` (plots.py 1130; line 1170) for `launchsim animate`; `app.video_footer` 3701 (3720) burns it into every MP4 frame |
| C7 | src/launchsim/sim.py:1694-1695 | `offload_penalty_assumption` 1690 | "offload: stage-1 dry mass +X t is an assumed structural penalty (a parametric row), not a structure sized for the push load" | run-specific (penalty rows) | `results_io._offload_assumptions` 1291 (1299) -> the run's assumption list; quoted in docs/physics.md 5997-6000 |
| C8 | src/launchsim/config.py:2702-2705 | the note `offload_overrides` 2671 writes | "<what>: X t of stage-1 dry mass added, an assumed structural penalty, not a sized structure" | run-specific, keyed only on `dry_added_kg > 0` | `offload_case_start` 2721 (2743) and `offload_solved_run` 2747 (2756, always 0.0) -> resolved_config.yaml's case vehicle dict (outside the digest pin) |
| C9 | src/launchsim/summary.py:1820-1824 | `OFFLOAD_CASE_ROWS` 1802 (not in the brief) | row "assumed stage-1 dry mass added [t] (an assumption, not a sized structure)" from `stage1_dry_mass_added_kg` | label of a table row | `offload_section` |
| C10 | src/launchsim/app.py:1433-1435 and 1473-1478 | `SP1_HEADLINE` 1420 text; `HeadlineCaveat("Structure.", ...)` (not in the brief) | text: "It charges no structural mass for the 4 g0 push ..."; caveat: "The penalty rows are the only stand-in for the structure a 4 g0 full-stack push needs, and the needed mass is unknown: no structural model exists. They are assumptions, not a sized structure." | text historical (true of SP1's run); caveat global | GET /api/form `headline` and the results panel's `sp1_headline`. tests/test_app_server.py 3045-3070 requires `head.text` verbatim in docs/findings/RQ1-fuel-offload-2d.md, and each caveat's numbers ("4 g0") in the note and in its text |
| C11 | src/launchsim/app.py:3706 | docstring of `video_footer` | "no sized structural mass" | docstring | none |

### 2.2 Sentences that do not say "no structural mass" but turn false once a structure is charged

All three are in the inventory but not in the brief's list of sources.

- src/launchsim/sim.py:1680-1685 `OFFLOAD_ASSUMPTIONS`: "every dry mass (tank structure included) ... unchanged". Attached to every offloaded run (sim.py 1752; results_io 1296, 1527).
- src/launchsim/summary.py:1688-1689, item 5 of `OFFLOAD_CAVEATS`: "the tanks are partly filled: dry masses and tank structure unchanged ...".
- src/launchsim/compare.py:1639-1645 `OFFLOAD_COMPARISON_BASIS`: "dry masses unchanged unless a row says so". This is still true if the structural row says so; it needs a row.
- src/launchsim/summary.py:1683-1685, item 3 of `OFFLOAD_CAVEATS`: "the drive is a prescribed constant acceleration with no force or power limit, the carriage is massless unless ..., the shaft is vented". It is printed for every offload block whatever the drive, so it is false for a `linear_motor` offload case (section 8).

### 2.3 The one reader every page goes through

- Fact. `replay.penalty_added_kg` (replay.py 471-480) returns `stage1_dry_mass_added_kg` when it is > 0, whatever `assumed_penalty` says (480 is only the unrecorded-size case). Its callers:
  - replay.py: `penalty_clause` 491 (case notes, 587) and `structure_caveat` 1033;
  - scene.py: `scene_run_label` 902 ("(offload penalty row: assumed ...)") and `structure_note` 1308;
  - plots.py 749 (`AnimationRun.penalty_added_kg`), which drives C6's penalty clause;
  - app.py 2032, 2040 and 2146 (`penalty_clause` in the headlines);
  - app.py `_record_settings` 2560, which reads the record key directly.
- Fact. results_io.py 1462-1467 writes `stage1_dry_mass_added_kg` and `assumed_penalty = cfg.stage1_dry_mass_added_t is not None`.
- Recommendation. Give a modelled structure its own record keys, for example the mass, the model, the coefficient set and the sizing basis. Teach each reader a third branch: uncharged, assumed penalty, modelled. Never write the modelled mass into `stage1_dry_mass_added_kg`, and give `offload_overrides` a note argument so that C8 does not label the modelled mass as "an assumed structural penalty". If SP7's factory wrapper (section 5.5, option i) passes dm(x) through `offload_overrides`, C8's note would otherwise be wrong (inferred from 2697-2709).

### 2.4 Templates

- src/launchsim/templates/app.html:294: the legend "Assumed structural penalty".
- src/launchsim/templates/app.html:1216: `FIELD_HELP.stage1_dry_mass_added_t` = "Assumed: a parametric stand-in for the structure a push needs, not a sized structure." It stays true of the penalty field. It changes only if the form changes.
- src/launchsim/appform.py:400: the field label "Assumed structural penalty, stage-1 dry mass added (0: none)".
- src/launchsim/templates/scene.html:2665-2670 composes the footer from `r.structure_note` and has no wording of its own (tests/test_scene_page.py 2116 pins the field name).
- templates/replay.html has no structural wording; it shows `meta.caveats` (line 571).

## 3. Site, manual, README and findings index (facts, with line numbers at HEAD)

- site/build.py:220-231 `REPLAY_OFFLOAD_STRUCTURE_SOURCE` and `REPLAY_OFFLOAD_STRUCTURE`: the editorial addition to pad-vs-silo-offload.html and offload-vs-paired-pad.html (`REPLAY_PAGE_FIXES` 260). It is keyed on C3's exact text for silo_cold_s1 and adds "no structural model exists yet". That is a global claim, so it must change at SP7's close. If C3's text changes for SP1's run, the key stops matching and the build warns (build.py 188-191).
- site/examples/: each of the five replay pages carries one C3 sentence. In the scene page pad-vs-silo-offload-scene.html, C3 appears once, C1 twice (in `caveats` and in `offload_caveats`, from the recorded metrics) and C5 once. No gallery page shows a penalty row, so C4 is on none of them. site/examples/index.html (hand-written) has lines 256, 348, 459 and 535.
- site/index.html: lines 110, 131 ("no structural model exists yet (phase SP7, next)"), 268, 276, 316 ("there is no structural model yet"), 353, 379 and 421.
- site/deck/index.html: lines 667, 865, 1016, 1063, 1085, 1180 ("No structural model exists yet: phase SP7, the next phase, decides ...") and 1235.
- docs/manual/:
  - 02-quick-start.md: 86 and 147;
  - 03-concepts.md: 182;
  - 05b-offload.md: 100 (the brief's line), 224 and 351;
  - 07b-app.md: 25, 129 (the form-table row, "a penalty row, not a sized structure"), 269 and 422;
  - 08-outputs.md: 75;
  - 09-reading-results.md: 314, 340 and 361;
  - 12-faq-glossary.md: 23, 46, 54, 122 and 191 (the glossary row **penalty row**, "a parametric stand-in for structure, not a sized one");
  - README.md (the manual's): 32.
- README.md: 19, 227, 229, 254, 269, 318, 335, 347 ("No structural model exists yet.") and 348.
- docs/findings/README.md: 20, 21 and 36 ("a sized structure ... not covered").
- docs/physics.md: 3781 (describes `OFFLOAD_CAVEATS`) and 5997-6000 (C7).
- Fact. Most of these lines describe SP1's or Phase 2's recorded runs and stay true as a record. Present-tense status claims ("no structural model exists (yet)", "phase SP7, next", "the needed mass is unknown") are false once SP7 lands: README 347, site/index.html 131 and 316, the deck 1180 and 1195, build.py 227, the gallery index, and C4 and C10.
- No test reads the manual, README or site prose. tests/test_site_build.py only tests the scene frame helpers.

## 4. Tests that pin the wording

Method A, the brief's (it reproduces the brief's 25): lines matching, case-insensitively, `structural mass|structural model|sized structur`. Method B (count_pins.py): occurrences of the exact phrases, with string literals that span lines joined. An "assert" below is an assertion that fails if the sentence is reworded. A "selector" picks the caveat by the word "structural" or "structur" and breaks only if the word leaves the sentence.

| Test file | A (lines) | B (occurrences) | Asserts on the wording (line) | Selectors | Other pins |
|---|---|---|---|---|---|
| tests/test_caveat_wording.py | 12 | 14 | 9: 725 (startswith C3), 729 ("would cancel the gain", the dry-mass-slope clause), 738, 762, 779 (== C3), 852 (== C3 + C4), 860 (== C4), 865 ("No structural mass" not in), 867 (== C4 plural) | 10: 724, 731, 737, 761, 771, 778, 851, 859, 866, 1108 | `penalty_added_kg`, `penalty_mass_text`, `penalty_clause`: 7 asserts at 881-891; the four structure tests at 721, 746, 775 and 840 |
| tests/test_animate.py | 4 | 4 | 4: 296, 316-319, 320-322 (penalty plural), 326-328 | 0 | the 1280 px width check of the line at 329-336 |
| tests/test_scene.py | 4 | 3 | 6: 1332, 1354, 1355, 1363, 1364, 1365 (literals at 1342-1346) | 0 | fixture `OFFLOAD_CAVEATS` 103 (fake text) |
| tests/test_app.py | 2 | 2 | 1: 213-215 | 0 | 265 (`EXPLORATORY_PUSH_CAVEAT` not in a pad banner); 239 is a docstring |
| tests/test_video.py | 2 | 2 | 1: 1133 | 0 | 1129 (footer == `plots.animation_caveats(...)`) |
| tests/test_app_server.py | 1 | 0 | 0 | 1: 1920 ("structural mass" in c; 1921 checks the load text) | fixture `OFFLOAD_CAVEATS` 136 (fake); 3045-3070 (`SP1_HEADLINE` against RQ1) |
| tests/test_offload_pipeline.py | 0 (one line, 232) | 1 | 1: 232 (`"assumed structural penalty" in pen["note"]`) | 0 | symbol pins on `OFFLOAD_CAVEATS`: 874-875, 2031 (`offload_caveats(...) == [gate, *OFFLOAD_CAVEATS]`), 2052-2059 (the last item, word for word: the item's position is pinned), 2307; 1770 (`offload_penalty_assumption(2.0)`) |
| tests/test_app_page.py | 0 (one line, 1937) | 1 | 1: 1937 (`template.count("a parametric stand-in for the structure a push needs") == 1`) | 0 | |

Totals:

- Method A: 25 lines in the six SP2 files, plus the two named lines, 27 in all.
- 24 wording asserts and 11 selectors.
- Adjacent pins outside the eight files: tests/test_replay.py 514-516 (the extra-structure sentence of `structure_caveat`: "200 kg of payload per tonne", a borrowed slope); tests/test_scene_page.py 2116 (`"r.structure_note" in footer`).

What a change would break (facts derived from the asserts):

- If the sentences branch, and runs without a structure keep today's wording, no assert in this table needs to change.
- Turning C1 from one constant item into a per-record branch breaks the symbol pins of test_offload_pipeline.py 2031 and 2052-2059, the latter because the last item's position is pinned.
- Rewording C4's "no structural model exists" changes the asserts at 852, 860 and 867.

## 5. KI-039: the offload section's heading, its basis line and the banner disclaimer

Facts:

- summary.py:1668 `OFFLOAD_SECTION_NAME` = "Propellant saved at fixed payload"; 1671 `OFFLOAD_SECTION_TITLE`, used at 2218; `offload_section` 2074 prints `record["basis"]` first (2085).
- compare.py:1639-1645 `OFFLOAD_COMPARISON_BASIS` ("... every offload is measured at the reference payload P_ref ...") goes into metrics.json `offload.basis` (results_io.py 1717). No other reader prints it: app, scene and replay do not read `basis`.
- summary.py:710-715 `EXPLORATORY_IMPOSED_TEXT`, used by `_imposed_lines` 783-797 (793), which `exploratory_banner` 866 calls.
- The section name is also typed out at results_io.py 1919 (`SENSITIVITY_ARMS_REPORTED`, the payload Sensitivity note) and replay.py 1399. In replay.py the at-P_ref sentence of the comparison caveat names the section ("summary.md, 'Propellant saved at fixed payload', with its caveats"). That sentence is in pad-vs-silo-offload.html, offload-vs-paired-pad.html and the scene page, and site/build.py keys `REPLAY_OFFLOAD_CASE_SOURCE` 233-237 and `REPLAY_PAIRED_PAD_SOURCE` 238-245 on it.
- Tests that pin it:
  - tests/test_offload_pipeline.py 1314 (literal title), 1302-1305 (literal name in the expected note), 2306 (symbols), 839 and 869 (basis by symbol);
  - tests/test_config_planar.py 1373 (literal);
  - tests/test_caveat_wording.py 1009 and 1304 (replay's pointer, literal);
  - tests/test_app.py 301 and 304 (`EXPLORATORY_IMPOSED_TEXT` by symbol).
- Tracked summaries that carry the heading:
  - results/silo_offload_2d/20261003T112934Z/summary.md: heading 98, basis 100, and the Sensitivity note 238 also names the section. It is the only one with imposed cases under the heading (silo_cold_fix5pct and silo_cold_fix10pct, "fixed" in its kind row).
  - results/silo_offload_2d_readme/20261003T112956Z/summary.md: 98 and 100.
  - results/app/20261007T130614Z/summary.md and results/app/20261007T130817Z/summary.md: 100 and 102 (solved stage-1 cases only, no imposed case).
  - The other 17 tracked summaries, including SP1's sweep 20261003T112949Z, have no such section. None is rewritten.
- Blast radius of a rename: the string appears in docs/physics.md (10 times), five manual chapters (02, 05b, 08, 09, 12), site/build.py (3), the three gallery pages, docs/demos/SP1 (4), docs/handoff/NEXT_SESSION.md (2) and several phase files and inputs.

Recommendation:

- Keep the heading for the solved cases, where it is true and where every existing pointer aims, and print imposed cases under their own sub-heading and table with their own one-line basis ("each imposed case flies its own P*, read as P* - P_ref").
- Reword `OFFLOAD_COMPARISON_BASIS` so that "measured at P_ref" covers the solved cases only.
- Then drop `EXPLORATORY_IMPOSED_TEXT` from `_imposed_lines` and keep `EXPLORATORY_IMPOSED_NOT_NETTED_TEXT`. test_app.py 301 and 304 change.
- This leaves replay.py 1399, the gallery pages, build.py's keys and the docs' pointers valid. Recorded summaries keep the old layout; their own text is self-consistent.

## 6. KI-036 (and KI-038 for context)

Facts:

- src/launchsim/replay.py:1820 in `replay_data` 1779: `"dirty": bool(git.get("dirty")),` (1819 writes `"git": str(git.get("hash", "unknown"))`).
- The frozen template renders `"(git " + META.git + (META.dirty ? ", dirty" : "") + ")"` (templates/replay.html 572). A `null` dirty is falsy, so writing None instead of a bool still shows a clean state. The sha256 pin is tests/test_caveat_wording.py 377-383 (`REPLAY_TEMPLATE_SHA256`).
- The scene already writes `dirty if isinstance(dirty, bool) else None` (scene.py 1222-1226), and the banner's `_tree_state` (summary.py 771-776) reads None or a hash of "no-git" as unknown (`EXPLORATORY_NO_GIT_HASHES` 773).
- What a fix touches: replay.py 1819-1820 only, putting the unknown state into the `git` string (for example "<hash>, state unknown", reusing `_tree_state`'s rule) and keeping `dirty` a bool. Add one test with dirty None and one with hash no-git; tests/test_replay.py 214's fixture (`dirty: False`) is unchanged.
- Fact: every metrics.json on disk records dirty as a bool (12 False, 3 True; scanned at HEAD), and all six gallery pages carry `"dirty":false`. A fix that leaves the bool cases alone therefore changes no page made from a directory on disk (inferred from the scan).
- KI-038 (scene.py meta names only the run directory's git state, not the renderer's): the replay meta has the package `version` (replay.py 1821, `__version__` "0.1.0") but no renderer commit either. It falls to SP7 only if SP7 edits scene.py.

## 7. How SP2 regenerated the gallery, and what SP7 would need

Facts:

- Step A1a, commit 41f838a (2026-10-05), changed the five replay pages by one line each (the data block), replay.py, plots.py, site/build.py (232 lines), site/examples/index.html, docs/manual 05b and 07, tests/test_caveat_wording.py (new) and test_offload_pipeline.py.
- The record of the diff:
  - session log docs/phases/SP2-launch-app-2d-scene.md 1708-1721: 13 reference pages differ "in text keys only (meta.caveats, meta.subtitle, meta.closeup_notes, offload labels and notes)", with every numeric series and event number identical. The gate script gate_a1a_g1.py was a session scratch file and is not in the repository. "The five gallery pages were regenerated and equal fresh renders", and the site build was clean.
  - the gate text at 1262-1264;
  - section 12, item 6 at 1956-1961;
  - section 8, criterion 10 at 1416 ("35 keys over 13 pages, no number");
  - A1's rule at 1283-1287: regenerated with their recorded commands, `git status --porcelain site/examples` must stay empty.
- site/build.py:
  - `REPLAY_TEXT_FIXES` 160-186 now holds only three JavaScript canvas patches of the frozen template (KI-031);
  - `REPLAY_STALE_TEXT` 153 and `GALLERY_STALE_TEXT` 159 are tripwires;
  - the editorial additions `REPLAY_PAGE_FIXES` 260 (`REPLAY_SHAFT_BIAS` 207-218, `REPLAY_OFFLOAD_STRUCTURE` 220-231, the offload-case and paired-pad keys 233-258) are applied at build time;
  - the files in site/examples stay as written. Scene pages get only the frame, no text fix.
- The scene page came later, from 7cb440f (SP2 step A7 part 1). Its command is in docs/demos/SP2/README.md 97. The media files under site/examples/media are separate ffmpeg products (README 141-145); they carry burned-in footers from C5 and C6.
- The six commands, as site/examples/index.html 361, 420, 469, 548, 612 and 671 record them:
  - `replay results/silo_offload_2d/20261003T112934Z --runs pad silo_cold_s1`
  - `replay ... --runs silo_cold_s1__pad silo_cold_s1`
  - `scene results/silo_offload_2d/20261003T112934Z --runs pad silo_cold_s1`
  - `replay results/silo_screening_2d/20260930T175743Z --runs pad silo_cold`
  - `... --runs silo_instant silo_cold silo_hot_ramp_on_track silo_cold_lag`
  - `... --runs silo_cold silo_failed`
  - each with `--out site/examples/<page>.html`.
- On disk: both directories, with timeseries.csv and events.csv in every run folder these pages use. CSVs are ignored (.gitignore:10 `results/**`), so a fresh clone needs re-runs.
- Checked in this survey: the six commands, run at HEAD into the scratchpad, give files byte-identical to the committed site/examples pages.

What SP7 needs:

- No source run of these pages charges a structure or uses a linear motor. If C3, C5, C6 and the record-driven C1 keep today's text for uncharged runs, and KI-039 is done as section 5 recommends, regeneration at SP7's close should again be byte-identical (inferred). The gate becomes "regenerated with the recorded commands, `git status --porcelain site/examples` empty", recorded in the session log.
- What does need editing at the close: site/build.py 227 ("no structural model exists yet") and the prose of the gallery index, the landing page and the deck.
- If SP7 adds a gallery page for its own run, it comes from an SP7 directory made from a clean commit, and build.py refuses app or exploratory sources (`check_scene_source`, D-SP2-37).

## 8. What the readers show for a run whose assist.model is linear_motor

Facts (from the code):

- metrics: `push_setting_metrics` (metrics_planar.py 949-960) writes `net_accel_mps2` and `net_accel_g` as None for any drive that is not `ConstantAccelAssist` (`prescribed_accel_mps2` 939-946); `stroke_m` is the track length. `exit_speed_mps` is always the measured |v_rel| at release (991-993, 999), and `push_time_s`, `carriage_mass_kg`, `braking_distance_m` and `facility_length_m` come from the drive object (1000-1023). `LinearMotorAssist` must therefore expose `efficiency`, `carriage_mass_kg`, `braking_distance_m()` and `facility_length_m()` (inferred from 980, 1014-1015, 1022). KI-032: `drive_power_peak_t_s` is on the absolute clock (1012).
- `replay.push_accel_g` (699-706) returns None: no metric, and no `net_accel_g` key in the block. `assist_text` (743-777) then says "<where>, linear_motor drive, ... exit X m/s". It names no force or power limit. This is honest but says little.
- `replay.drive_caveat` (1172):
  - the run goes to `others` (1213-1217);
  - no "the drive is ..." clause is built for it (1243-1250 only for prescribed drives);
  - its sentence (1278-1291) is written only when the run has a massless carriage or a vented shaft (`if not left_out: continue`, 1280). A linear-motor run with a carriage mass and a sealed shaft (S5) would get no drive sentence at all (inferred);
  - `is_vented` (718-721) needs `assist.shaft == "vented"`, so a `LinearMotorConfig` without a `shaft` key would silently drop the shaft-drag omission;
  - tests/test_caveat_wording.py 479-489 and 689-712 pin today's other-drive wording.
- scene.py `assist_settings` (484-591) finds no acceleration in the metric or the config and derives a = v_exit^2 / (2 L), labelled `sources["net_accel_mps2"] = "derived"` (522-525), together with `net_accel_g`. For a force- then power-limited push that is the acceleration of an equivalent constant push over the stroke, not the motor's. templates/scene.html does not read `net_accel` (grep), so only the data block carries the figure (inferred low impact). `push_time_s` comes from the metric, and the carriage-braking reconstruction (scene.html 1530-1535) uses `exit_speed_mps` and `braking_distance_m`, which still hold for a constant braking deceleration.
- Key collision: scene.py 520-521 and appform `PUSH_KEYS` (106) read an assist-block `exit_speed_mps` as the constant_accel push key. A linear motor whose target release speed reused that name would be read as a push setting (inferred).
- `plots.animation_caveats` reads no drive model. The peak g comes from the time series (`push_peak_g` 597-600), so nothing in it is false under a linear motor except C6 when the selection carries a modelled structure.
- summary.py: drive-agnostic rows. But `OFFLOAD_CAVEATS[2]` (1683-1685), "a prescribed constant acceleration with no force or power limit", is printed for every offload block, so it would be false for a linear-motor case. sim.py 973-978 limits its drag sentence to constant_accel; under a linear motor the missing shaft drag lowers the exit speed, and that sentence does not say so.
- compare.py 1744-1748 `ENERGY_ONLY_ASSIST_KEYS` lists only constant_accel's `drive_efficiency`. Every `linear_motor` key therefore changes the trajectory key, so a drive-efficiency arm re-flies. That is correct if P_max is electrical; if P_max is mechanical, efficiency is energy-only and an entry would save runs (a design point).
- The app: `push_view` (app.py 2248) uses `assist_text`; `PUSH_METRICS` (1355-1367) shows `net_accel_g` as None; `DRIVE_NOTE` (app.html 467-468) is shown only for constant_accel (992).
- `ASSIST_UNION_TAGS` (appform.py 187) = {"none", "constant_accel", *PLANNED_MODELS}. When S4 removes `linear_motor` from `PLANNED_MODELS`, the tag drops out instead of "following". A pydantic error location under a `LinearMotorConfig` would then keep "linear_motor" in the field path that `_clean_loc` (1700-1707) builds. No test pins `ASSIST_UNION_TAGS` (grep). This changes nothing visible today, because the form never builds a linear-motor block.

Recommendations for S4:

- Settle the metric names. Leave `net_accel_*` None for a non-prescribed drive, and add, for example, `push_accel_mean_mps2` (v_exit / t_push), named as a mean.
- Make scene.py stop deriving `net_accel_mps2` for a drive that is not constant_accel, or label it as an equivalent value.
- Give `LinearMotorConfig` the `shaft` key, and a target-speed key with its own name.
- Add a linear-motor clause to `drive_caveat` that names F_max, P_max and the rise time, and is always present.
- Branch `OFFLOAD_CAVEATS[2]` by drive.
- Build `ASSIST_UNION_TAGS` from config's union tags and test it.

## 9. Calibration records

Facts:

- src/launchsim/run_data.py:958-961 `CALIBRATION_RECORDS` is keyed by the resolved `vehicle.name`. It holds "generic_f9_class_2d" (26054.4, 22800.0) and "generic_f9_class_2d_readme_loads" (24700.0, 22800.0), both docs/findings/CAL-f9-leo-2d. Note: configs/vehicles/generic_f9_class_2d_recorded_scope.yaml is a calibration case without a record.
- Four readers: plots.calibration_caveat 1020; replay.calibration_caveat 876-880; summary.exploratory_banner 850-855; and summary.offload_calibration_caveat 1707-1727, via `offload_caveats` and results_io 1796-1798 (with `vehicle_name = resolved.baseline.vehicle.name`). The docstring at 1711 still says `plots.CALIBRATION_RECORDS` (the same object, plots.py 516).
- A vehicle without a record gets "... has no calibration record on file; read every offload as a difference between runs of the vehicle model ..." (1714-1719). The footnote and the replay page say the same in their own words.
- Adding a record needs more than a dict entry. tests/test_animate.py 339-366 asserts `set(CALIBRATION_RECORDS) == {GATE_VEHICLE, README_VEHICLE}` (353), that each vehicle is a case of tests/data/calibration_record.json with that recorded P* to 0.1 kg, and that CAL-f9-leo-2d has its results row. A new fork can only get a record from a calibration run that includes it. tests/test_run_data.py 618, 651 and 710 and test_config_planar.py 1376-1378 also read the dict.
- The offload overrides change only `stages.*` paths (config.py 2683-2709), not `vehicle.name`. A structural case on the gate vehicle therefore keeps "+14.3% high" (inferred).

Recommendation: keep the coefficients in configs/structures/<vehicle>.yaml (section 5.4 of the brief), not in a forked vehicle file. A fork would read "no calibration record" on every page, or force a calibration run, and the bridge on the README-loads fork already has a record.

## 10. The app

### 10.1 Facts

- Form:
  - the site choice is the drive: `SITES` = (pad, silo) at appform.py 101-104, mapped to `assist.model` (306);
  - the silo block is `_assist_dict` 1081-1102: silo_cold's committed assist (`SILO_FRAGMENT_VARIANT` 96; experiments/silo_offload_2d.yaml 89-91, `model: constant_accel`) with the form's `push_by` key, stroke, carriage mass and impingement;
  - `push_numbers` 772-782 and `_check_push` 785-811 use the constant_accel relations;
  - `_push_values` 1481 and `derived` 1559 (1583) compute live values only for `ConstantAccelAssist`.
- Penalty field:
  - appform.py 398-405, with `PENALTY_RANGE_T` (0, 100) t at 295, part of `OFFLOAD_OPTIONAL_FIELDS` 416;
  - the case dict at 1160-1161, the neutral tag "_dry+<t>t" at 1181-1182, the description at 1071-1072, the preset mapping at 1641 and 1669;
  - the page: legend 294, help 1216, the paired-pad clearing at 417, 547-548 and 1649;
  - D-SP1-04's refusal of a penalty with a paired pad is config.py 1659-1664.
- `make_basis` (appform.py 582-636) requires both experiment files to name the same vehicle and to have equal `SHARED_KEYS` (config 171) and baselines, and silo_cold to exist. Every preset (217-235) must name a committed run or case, and every committed run must resolve.
- `load_basis` (app.py 296-326) reads `OFFLOAD_EXPERIMENT` (164), `SCREENING_EXPERIMENT` (167) and the vehicle file at the server-start HEAD with `git cat-file`, never from the working tree when git is present.
- Effect of an edit of experiments/silo_offload_2d.yaml: an uncommitted edit is ignored. A committed edit is what the next server launches. If it breaks any `make_basis` rule, `launchsim app` does not start (cli.py 681-684, a `CliError`). Changing silo_cold's assist changes every silo launch, including its model. A new variant or case is harmless to the presets but becomes a "committed name" the app can reproduce. Separately, `CODE_PATHS` (169) makes a running server refuse launches once src, configs or experiments change after its start (`code_changed`).
- Reproduction mark (`sp1_comparison` 2660-2730): reproduces is True only if all of these hold:
  1. the launch kept the committed case name silo_cold_s1;
  2. `sp1_differences` (2566) finds nothing. That function compares the directory's run dict with the basis's committed run, both resolved by the current code, and the case record with the committed fragment (`_record_settings` 2543, `_fragment_settings` 2524);
  3. x* is within `REPRODUCTION_TOL_KG` 0.002 kg (1542) of 41,262.908 kg (`sp1_figure_matches` 2744);
  4. `sp1_files_same` (2632-2657) is True. It runs `git diff --quiet b3150c1754ee <basis commit> -- experiments/silo_offload_2d.yaml configs/vehicles/generic_f9_class_2d.yaml`. Both are unchanged from b3150c1754ee to HEAD (checked: exit 0).
- So a change to src/ alone does not end the mark unless it moves x* by more than 0.002 kg ("the code differs" text), and a new configs/structures/ file is not compared at all. An SP7 that charges structure by default on existing cases would move x* and end it (inferred). So would an amendment of silo_offload_2d.yaml or of the vehicle file.

### 10.2 Estimates (inferred, from the code above; with the review loop of protocol section 4)

(a) A modelled-structure switch in the form.

- What it needs:
  - a choice field (none / assumed penalty / modelled, possibly with the coefficient set), and its config key on the case;
  - exclusion rules against the penalty field and the paired pad;
  - the description, the neutral tag, `_case_dict` and `_form_from_case`;
  - in app.py, a "modelled structure" setting in `_fragment_settings` and `_record_settings`, and the headline clauses (the `penalty_clause` equivalents);
  - a C2 banner branch;
  - in app.html, a fieldset, help text and disabled-state logic;
  - presets only if SP7's cases join the basis files. That would need a third basis file or an amendment of silo_offload_2d.yaml.
- Tests touched:
  - tests/test_appform.py (field whitelist, refusals, the neutral names at 293 and 420, describe);
  - tests/test_app_page.py (the choice matrix `_matrix` 913-940 gains a dimension, the help count at 1937, the disabled-state matrix, the node mapping);
  - tests/test_app_server.py (the fields list at 3036, the panel at 1888-1921, the SP1 comparison lines at 2077 and 2146-2151);
  - tests/test_app.py (the banner at 213 and 265, and one launch);
  - tests/app_support.py.
- Size: one step, about half a day to a day; roughly 150-250 source lines and 200-300 test lines.

(b) A linear-motor push in the form.

- What it needs:
  - a drive choice;
  - fields for F_max, P_max, the rise time, the release rule and the efficiency;
  - `push_by` does not apply, because the exit speed is a result;
  - new live values in `push_numbers`, `_check_push`, `_push_values` and `derived` (the closed forms of brief 5.7: corner speed and estimated exit speed);
  - `expected_work`;
  - a committed linear-motor fragment for `_assist_dict`. The two basis files have none, so either amend silo_offload_2d.yaml (a pre-registration amendment and a basis change, entry criterion 8) or let `load_basis` and `make_basis` take SP7's experiment as a third file;
  - the `ASSIST_UNION_TAGS` fix;
  - in app.html, a fieldset, show/hide, live checks and the panel text.
- Tests touched: tests/test_appform.py (+5-10 tests), tests/test_app_page.py (the `_matrix` product over `SITES` grows, so the node mapping test runs longer), tests/test_app_server.py (fields, panel), tests/test_app.py (a slow linear-motor launch) and tests/app_support.py.
- Size: one to one and a half steps, about one to two days; roughly 300-450 source lines and 300-500 test lines.
- Order: it can only follow S4, once `LinearMotorConfig` is final.

Recommendation: keep both in the backlog, as the brief proposes. Neither is needed for the structural answer, and (b) also needs a basis decision.

## 11. Recommendations for S3 and S4 (all recommendations, not facts)

1. Branch every source in section 2 three ways, from the run's own record: uncharged (today's text, word for word, so the 24 asserts and the six gallery pages stay as they are), assumed penalty (today's text) and modelled (new: the mass, "first-order sizing model, coefficient set <set>, configs/structures/<file>", "not a sized structure in the FEM sense" or similar, settled with the honesty review).
2. Reword the global claims everywhere at once, for old and new runs alike: C4's "no structural model exists" (for example "the penalty row is an assumption, not the first-order model's mass"), C10's "Structure." caveat (keep "4 g0" and make the claim about SP1's run), and build.py 227. C10's `text` must stay verbatim in RQ1 (test 3055). Q6's recommendation of a new note with a pointer section in RQ1 is compatible with that; an edit of RQ1's bold headline is not.
3. Give the modelled mass its own record keys, readers and `offload_overrides` note (section 2.3). Add a summary row beside the penalty row (C9). Branch `OFFLOAD_ASSUMPTIONS` and the tank and drive items of `OFFLOAD_CAVEATS` (section 2.2) per record. Expect the symbol pins of test_offload_pipeline.py 2031 and 2052-2059 to change.
4. C6 makes one claim for the whole selection. Word it from each run's record, as C5 does, within the 1280 px footnote width that test_animate.py 329-336 checks.
5. KI-039 as section 5 recommends (split the cases, do not rename); KI-036 as section 6 says.
6. Gallery gate at S3 and at the close: the six recorded commands, byte-identical pages, and `git status --porcelain site/examples` empty, recorded in the session log. Edit only build.py's editorial text and the hand-written prose.
7. Configs/structures/ rather than a vehicle fork (section 9). A new experiment file rather than an amendment of silo_offload_2d.yaml, which leaves the app's basis and the SP1 reproduction mark untouched (section 10).

Note: REPORT.md was not written, because the harness refused report files for subagents. This message is the report. Scratch files: C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/04-wording-reporting/count_pins.py, heads.py, and regen/ (the six regenerated gallery pages).
