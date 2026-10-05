# SP2 design review 03: the CLAUDE.md and protocol compliance lens (first draft of the plan, 2026-10-05, at b69ff0c)

VERDICT: No blocker through this lens: the plan settles the seven questions and all but one of the listed design points, changes no equation, baseline or vehicle file, and overwrites no results directory (FAILED.txt on Ctrl+C matches run_experiment's own `except BaseException`, results_io.py 886-887). The most important change is to take the app summaries out of the tracker and bookkeeping commits, which as written breaks protocol sections 4.6, 7.12 and 3.3. Next: list the exit-criteria changes item by item (criterion 5 lost its exact thrust-on check), settle the skipped design point (brand assets in the package), and move the CLAUDE.md updates into the steps that add the modules.

## 1. [major] App summaries inside the tracker commit conflict with the protocol and with D-SP2-11

CLAIM: Committing results/app/*/summary.md in each tracker commit (and so in the closing bookkeeping commit) breaks three protocol rules and makes a running server refuse every later launch.

EVIDENCE: Plan lines 323-327 ("the tracker commit (with the session's app summaries)") and D-SP2-04 (line 66). docs/process/SESSION_PROTOCOL.md: 4.6 (lines 121-127) makes the tracker commit phase-file and TODO.md edits only; 7.12 (237-241) defines the closing commit as the last commit that changed code or results, with the bookkeeping commit after it; 3.3 (66-68) makes the next session check that `git diff --stat <closing> HEAD` holds no results; section 10 (358-363) reads anything other than the phase file and TODO.md in the tree as a stop inside a step. A8's demo launches would put results into the bookkeeping commit, and untracked summaries would misdirect a crash resume. D-SP2-11 (line 78) refuses a launch when HEAD differs from server start, so each summaries commit disables a running server and empties its in-process pad cache, although `git_info` itself ignores results/ (results_io.py 163, 439). Gate launches also run before the step's commit, so their public summaries carry the previous hash with -dirty.

CHANGE: In section 5 replace the parenthesis with: app summaries are results; they go in their own commit `SP2 step <k>: app summaries` before the tracker commit, never in a tracker or bookkeeping commit. At A8 every demo launch is made before the closing commit and no launch follows it. Reviewer and gate launches that are not demo material, and criterion 3's `launchsim run` on a scratch YAML outside experiments/, use `--results-root <scratchpad>`. In D-SP2-11 either compare only code-bearing paths (`git diff --quiet <start> HEAD -- src configs experiments pyproject.toml uv.lock`) or state that committing summaries needs a server restart and loses the cache. Log the protocol amendment as a decision.

## 2. [major] Exit criteria 5, 6 and 13 are weakened and the plan does not list the changes

CLAIM: The plan says the 14 criteria were "reworded where the survey showed them unmeasurable" but gives no item-by-item list, and three rewordings drop or narrow a check.

EVIDENCE: Phase file docs/phases/SP2-launch-app-2d-scene.md 1076-1080: "attitude within 0.5 deg; thrust on or off exactly outside a startup ramp". Plan 362-366: attitude only "wherever the model defines one (thrust on, hold, on the track)", and the thrust on/off check is gone. Survey 09 line 421 gives the reason (no meaning under a lag startup) and line 397 the replacement (thrust-on from the events), which the plan puts in the payload (line 179) but in no criterion; the attitude check's domain now depends on that unchecked flag. Criterion 6: phase 1081-1083 "reads empty at its propellant event" becomes stage-1 only (plan 367-369). Criterion 13: phase 1113-1115 "CLAUDE.md (commands, layout, I/O modules, status line) ... the user manual (the app command, the form, the outputs)" becomes "CLAUDE.md, README, manual chapter for the app" (plan 390). Plan section 8 ("what is new against the phase file") lists none of these; D-SP2-32 and section 9 only promise to record them after approval.

CHANGE: Add to criterion 5: "the thrust-on flag equals [the stage's ignition row time <= t < its propellant, cutoff, ignition_failed or end row time] exactly at every CSV row". Restore criterion 13's parentheticals. Add to section 8 a table "Changes against the brief's exit criteria": 1 (+second server); 2 (+screening presets); 4 (+types, HEAD); 5 (attitude domain narrowed by D-SP2-17; thrust on/off replaced, with the survey's reason; events 1e-6 s); 6 (1% to 1e-4; empty check stage 1 only, with the reason; every row); 8 (+incomplete); 10; 12; 15 (new). The user then approves the weakenings knowingly.

## 3. [major] One design point the starting prompt lists is not settled: brand assets in the package

CLAIM: The plan has no decision on how the app carries the logo mark and favicon, and never states the replay-contrast-token answer as a decision with a reason.

EVIDENCE: Prompt, docs/handoff/NEXT_SESSION.md 453-458: "Settle the open design points ... brand assets in the package". Phase file 5.10 (771-773: inline the mark, test against assets/brand/favicon.svg), section 10 line 1213-1214, risk R18 (1239). Grep of the plan for favicon, logo and inlin finds nothing; D-SP2-08 and section 4.5 cover only palette and tokens. Survey 04 section 8 item 2 and section 9 item 11 hold the facts a decision needs: the site's header mark is logo-mark.svg, favicon.svg is a different drawing, a data URI needs `#` written `%23`, two inline copies repeat SVG ids. On the contrast tokens, D-SP2-21 only implies "no" (replay.html not edited), while survey 04 lines 99-101 measured replay's `--ink-3` at 3.21-3.64:1 in light mode (below 4.5:1).

CHANGE: Add D-SP2-33: the app page inlines assets/brand/logo-mark.svg as the header mark and favicon.svg as a data-URI tab icon (`#` as `%23`); nothing is served from assets/; a test in tests/test_app.py compares each inline copy with its file under assets/brand/; state whether the scene page carries the mark. Add D-SP2-34: replay.html does not take the site's contrast tokens in SP2 (reason: its sha256 is pinned and site/build.py's frame overrides them in the gallery), with a known issue logged for the measured contrast.

## 4. [major] CLAUDE.md's I/O-module list, layout and commands are updated only at A8, while a CLAUDE.md compliance auditor reviews every step

CLAIM: From A1 on, new modules do file I/O that CLAUDE.md does not permit as written, and the commands list is inaccurate from A3, until the close.

EVIDENCE: CLAUDE.md line 140: "I/O lives in cli.py, sim.py, results_io.py, plots.py and replay.py"; line 13: "keep this list accurate". Protocol section 2 table: CLAUDE.md is updated for "commands and layout when the code changes them". Precedent: SP1 changed CLAUDE.md in the code steps (git log: a03e218 step 5, 6719f92 step 7). Plan section 4.1 adds run_data.py, scene.py, app.py and video.py as I/O modules and two commands, but CLAUDE.md is absent from its file table and appears only in criterion 13 and A8. The classifications themselves are right (display.py and appform.py pure; the other four I/O). tests/test_scaffold.py 27-38: the docstring guard covers only `PHYSICS_MODULES`; display.py, which holds a two-body coast and frame conversions, is not in it.

CHANGE: Add CLAUDE.md to the file table of 4.1 and to the step rows: A1 (layout line and I/O list gain run_data.py), A2 (display.py as pure; configs/display/), A3 (scene.py; the `scene` command; templates), A4 (app.py, appform.py; the `app` command), A6v (video.py). A8 keeps only the status line. Add `display` to `PHYSICS_MODULES` (or an equivalent parametrised test in tests/test_display.py) so the docstring rule (inputs, outputs, units, frame) is enforced for the coast, the separation state and the screen transform.

## 5. [major] The server-start git state never reaches summary.md, the only tracked file of an app run

CLAIM: With summaries tracked and public (D-SP2-03), the title's git label describes launch time, not the code that ran, and can read clean when the server started from a dirty tree.

EVIDENCE: D-SP2-11 (plan line 78) stores `server_start` as an extra key of the git dict; plan 4.1 limits summary.py to "the label value exploratory and its banner; nothing else". summary.py 75-84 (`git_label`) and 571-576 (`provenance_lines`) print only hash, dirty and error. Survey 02 section 5 (lines 370-373) measured it: the extra keys reach metrics.json and resolved_config.yaml (both git-ignored) and "summary.md ... did not mention them"; its section 12 item 5 recommends extending `provenance_lines` or saying it in the banner. The brief requires it: phase file 5.6 lines 584-585 ("The exploratory caveats say that the code is the one imported at server start") and 606-607.

CHANGE: Amend D-SP2-12: when `er.git` holds `server_start`, summary.md prints it, either as a `- Server start: <hash>[-dirty]` line from `provenance_lines` (emitted only when the key exists, so the output capture's summary digest does not move) or inside the exploratory banner. Add to criterion 7: "summary.md names the server-start git state". Add a test: server-start dirty with launch-time clean still shows dirty in summary.md.

## 6. [major] The step table drops the Tests and Main files columns, and three gates have no pass condition

CLAIM: Most tests the brief names per step are not named in the plan, and "Visual QA round 1/2" and A7's table cannot be passed or failed by an independent agent.

EVIDENCE: Phase file step table (1014-1024) has Main files, Tests and Gate columns; the plan's (332-344) has only Gate. Not named anywhere in the plan: A2 strict JSON, nulls in the shaft, silo_failed with null payload, staging state against `speed_inertial_mps`, the `short_of_orbit` pad control loading, a zero-offload pad control with no vehicle entry, the source of the offload caveats; A3 template string checks, ASCII page, page-writer output-path refusals; A4 stub runner, status codes, progress states, and the charset header (phase file 5.6 lines 531-533 and R14; "charset" appears nowhere in the plan); A5 one test per field; A6 camera checks through the state hook. A2's gate rests on "all 31 run folders on disk", but those CSVs are untracked (.gitignore 10-14), and survey 08 section 4 notes the existing synthetic fixtures lack `pitch_rad`, `thrust_vac_N` and `s_m`. Plan A7 omits the brief's "every row of the table passes or is logged as a deviation".

CHANGE: Restore the two columns. For each step list the test names, and state that pytest tests run on synthetic directories or a 1.5 s fixed-guidance run in tmp_path, never on results/. Add as an A2 test the plan's own 4.10 fact: the display coast started at the staging state reproduces the vehicle's recorded COAST_STAGING rows within a stated tolerance (an independent check of the frame conversion back to Earth-fixed downrange). Give A3 and A6 a pass condition (state-hook values within criterion-5 tolerances at the sampled times for the five runs) and A7 "every row passes or is a logged deviation". Restore `charset=utf-8` on every response with its test, or record its removal as a deviation.

## 7. [minor] KI bookkeeping: KI-019 is neither closed nor re-owned; KI-002 cannot fully close; new issues lack owner and severity

CLAIM: Two of the six SP2-owned issues would still read "open, owner SP2" after the close, and four new ones are named without the fields protocol section 9 requires.

EVIDENCE: TODO.md 243: KI-019 [low, open, owner SP2]. Plan 420-421: "KI-019 stays open for the replay page only", with no new owner and no wontfix. TODO.md 219: KI-002 also covers "calibration_caveat exists in both replay.py and plots.py with different wording"; D-SP2-13 keeps both, yet row A1 lists KI-002 as done, and the plan does not say whether the scene's calibration and drive sentences reuse replay's functions or add a third wording. Plan 418-420 names four new issues without severity or owner phase. TODO.md 220 (KI-003) and SESSION_PROTOCOL.md 408 name `plots.CALIBRATION_RECORDS`, which A1 moves to run_data. KI-016, 017, 018 and 029 are covered; "no backlog item targets SP2" is confirmed (TODO.md 96-110).

CHANGE: State: KI-019 becomes wontfix by D-SP2-02 for the replay page (or is re-owned to a named phase, with the reason). KI-002 closes except its calibration-caveat clause, which is split into a new issue or accepted by D-SP2-13. Name the functions the scene reuses for the calibration and drive caveats. Give each new issue a severity and owner. Reword KI-003 and protocol section 11 to `run_data.CALIBRATION_RECORDS` in A1's tracker commit.

## 8. [minor] Housekeeping of phase-file 5.8 item 4 is only half covered

CLAIM: The new ignore patterns have no demo or gallery rule, and the package-data test for the two new templates is missing.

EVIDENCE: .gitignore 16-19 has no `!docs/demos/**`. Plan line 125 adds `*_scene.html`, `*_scene.mp4`, `*_scene.gif`. Phase file 712-721 asks for the negation or non-matching names, and that a second template not weaken `test_template_ships_as_package_data` (tests/test_replay.py 368-371). Survey 08 section 3 item 5 checked that `site/examples/pad_vs_silo_cold_scene.html` would be ignored, so CI builds without it and the gallery link fails the Pages build; the video's default name `<experiment>_<timestamp>_scene.mp4` (plan 299) has the same trap under site/examples/media/. docs/phases/SP7-structural-mass-push-load.md 536-537 depends on whether SP2 adds `!docs/demos/**`. The plan also does not say which step edits .gitignore.

CHANGE: Add to 4.1 and to A3: .gitignore gains the three patterns and `!docs/demos/**` (or the plan fixes hyphenated demo and gallery names such as pad-vs-silo-cold-scene.html); the A3, A6v and A8 gates include `git status` showing the demo and gallery files as tracked; SP7's sentence is corrected at the close. Add tests that scene.html and app.html load through `importlib.resources`, hold their data token exactly once and are ASCII.

## 9. [minor] The fast-tier real launch was timed without plots, but D-SP2-26 turns plots on

CLAIM: The 1.5 s launch that justifies a fast-tier test excludes the 2.6-2.7 s of plot writing the app adds, so the test sits at the 5 s limit under load.

EVIDENCE: Plan 256-257: "a fixed-guidance basis gives a real launch in 1.5 s (fast tier)". Survey 02 lines 603-604: "fixed guidance, pad and silo_cold, sample_dt 0.5 s, no plots, resolve to summary.md: 1.51 s". D-SP2-26: plots are written for app launches. Survey 07 line 197: plots 2.6-2.7 s on a plain launch. CLAUDE.md: tests slower than 5 s are marked slow; protocol section 11: machine speed varies about 3x.

CHANGE: In 4.6 state that the launch function takes `plots` as an argument: the app passes True, the fast-tier tests pass False, and plot writing is covered once in the slow end-to-end test.

## 10. [minor] "run_data imports only units and config" contradicts the survey and the plan's own reader

CLAIM: The fairing reader and `MODEL_COLUMNS` need names that live in metrics_planar and phases.planar, so the stated import rule would force restated literals.

EVIDENCE: Plan line 113: "imports only units and config". Survey 06 section 8 (lines 578-581): imports include `launchsim.metrics_planar` (the column tuples and `FAIRING_*`) and `launchsim.phases.planar` (`COAST_STAGING`, `LTG_BURN`); its section 7 (547-549) builds `MODEL_COLUMNS` from `metrics_planar.PLANAR_TIMESERIES_COLUMNS`. D-SP2-15 keys the mass rule on the COAST_STAGING phase name.

CHANGE: Reword 4.1 to: "imports units, config, metrics_planar (column tuples, FAIRING_*) and phases.planar (phase names); never matplotlib, plots, replay, results_io or summary". Keep A1's gate as "imports no matplotlib".

## 11. [minor] Numbers outside the display YAML have no stated home, and camera lengths sit in a vehicle-specific file

CLAIM: The plan fixes many numbers in prose without saying where they are defined, and the generic-shape fallback has no source for its camera lengths or proportions.

EVIDENCE: CLAUDE.md 141: no magic numbers outside constants.py and configs. The codebase reads this as named, documented module constants: replay.py 68-77, cli.py 120-135 (`plots.ANIMATION_DEFAULT_*`). Plan numbers with no home: port 8765 (D-SP2-29); 64 KiB (line 234); 1,800 frames and 4 MiB (295-296); the grid rule "every 2nd row to 40 s, every 20th after" (D-SP2-16); the criterion-5 tolerances the builder applies at load time (line 191). D-SP2-18 puts the camera lengths in configs/display/f9_class.yaml with `applies_to`, yet a vehicle without a display block gets a generic shape; the README-loads fork directories and test vehicles take that path. The plan is also silent on payload units and on conversion in JavaScript; replay.html already divides by 1000 at lines 343, 359 and 449.

CHANGE: Add one rule to section 4: every server, video, grid and tolerance number is a named, documented module constant, as in replay.py; the scene script takes camera and tolerance numbers from the payload; payload geometry is SI and display-unit fields are converted in Python through units.py. Move the camera lengths and generic-shape proportions to a vehicle-independent file (for example configs/display/scene.yaml), each `assumed: true`.

## 12. [minor] docs/physics.md and manual edits are narrower than the changes need

CLAIM: The plan's only physics.md edit is the display-only section, and its only manual edit is a new app chapter, though A1 and A4 change documented behaviour.

EVIDENCE: docs/physics.md 1791-1792 says the `fairing` event's record "holds the mass before the drop", while phases/planar.py 1689-1692 logs it after the staging map in COAST_STAGING; that is the convention D-SP2-15's reader encodes. The new label value changes the schema that physics.md 5489-5498 and docs/manual/04-experiments.md line 20 ("`calibration` ... or `guidance_study`") describe. D-SP2-14 changes what docs/manual/07-commands.md 93-95 and 11-troubleshooting.md 137, 140 say about animate. docs/manual/12-faq-glossary.md 85-89 says there is no app. Survey 08 section 1 lists these and more; plan criterion 13 keeps only "manual chapter for the app". The deck PDF command is recorded nowhere (survey 08 section 3).

CHANGE: A1: correct physics.md 1791-1793 to state both row conventions, in the change that adds `with_drop_masses`. A4: add the label value to physics.md's schema text. A8: adopt survey 08 section 1 as the checklist for criterion 13 (manual 02, 04, 05b, 07, 08, 11, 12; README 37, 372, 431, 444, 447) and record the headless-Edge PDF command in docs/demos/SP2/README.md.

## 13. [minor] First actions after approval omit the session-log record and the mock-ups; A8 omits the close-out question

CLAIM: Section 9 matches protocol section 3 items 7 and 8 but leaves out three things the protocol or the plan's own decisions require.

EVIDENCE: Protocol 3.4: "Record the test count in the phase file's session log"; phase file 187-188: entry-criteria checks are recorded in section 11. The plan reports 1264 passed and two literal failures of item 3 (HEAD subject; site/ in `git diff --stat 5007515 HEAD`, confirmed) only in the plan itself. D-SP2-08 decides the look "as in the mock-up" and A0's gate is approval of the mock-ups, but section 9 saves only "this design and the survey". TODO.md line 64 (M13) says a separate `launchsim scene` command is no longer the plan, which D-SP2-01 reverses. Plan row A8 omits protocol 7.7 (close-out question on the next phase) and 7.13 (print the prompt), both in the starting prompt.

CHANGE: Add to section 9: write the start-checklist record into the phase file's section 11 (fast-suite count, entry criteria, the header diff, the two literal item-3 failures and their cause); save both mock-ups under docs/phases/inputs/ beside the design; correct M13. Add to row A8: close-out question to the user (next phase, recommendation first), answer logged, prompt printed.

## 14. [minor] Pillow "after A1's hash gate" leaves A1 with two gates or an ungated change

CLAIM: Row A1 bundles the Pillow declaration into a step whose gate it is scheduled to follow, which does not fit one commit per passed gate.

EVIDENCE: Plan line 335: "A1 | run_data; ...; then Pillow (KI-018)". D-SP2-24: "Done after A1's hash gate", with its own condition (the lock change must not move numpy, scipy, pandas or pyyaml) that is not in A1's gate text. Protocol 4.4-4.5: an independent gate checks the step's criterion, then one commit per passed gate; 9: a step added in a session takes a letter suffix.

CHANGE: Make it row A1b (after A1a or directly after A1) with its own gate: pyproject.toml gains pillow with the one-line justification; the uv.lock diff adds only pillow to launchsim's entry; numpy, scipy, pandas and pyyaml versions are unchanged; the golden exact tier and the fast suite pass; the reference page's sha256 is unchanged.
