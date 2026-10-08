<!-- Record of SP7 step 0: read-only survey 09-process-tests-budget (process conventions, test conventions and the run-time budget), made by a workflow agent on 2026-10-07/08 at HEAD 22c62e9 and saved byte for byte from the workflow journal. Line numbers are for 22c62e9; scratch scripts and paths it names are not in the repository. Not edited; corrections go into the phase file. -->

# SP7 step 0 survey 09: process conventions, test conventions and the run-time budget

This is a read-only survey at HEAD 22c62e9 ("Close SP2: trackers, handoff, next phase file", clean tree), made on 2026-10-07. SP7's design and pre-registration should follow the shapes SP2 and SP1 left behind.
- **The design** is a word-for-word record of the approved plan. Its sections are context, start checklist, a decisions table, the design per step, the step table, exit criteria with fixed tolerances, verification, risks and first actions.
- **The pre-registration note** is committed with the experiment files before any run. It holds what is registered and the commands, what is already known, the comparison basis with a derived resolution, the cases and sweeps with their purpose, the choices fixed, a reading for every outcome, the blocking checks, what nothing measures, a runtime estimate, and amendments appended at the end.
- **Test conventions** are strict but have two gaps that matter to SP7. The docstring check silently skips a module path that does not exist, and nothing enforces the 5 s slow-test rule.
- **The run-time budget** is smaller than the phase file says. SP1's production run implies about 35-45 s per verified stage-1 solve with three commands running at once, not the 90-110 s quoted in sections 5.5 and 5.8.
  - At measured rates, SP7's full set costs about 20-33 min serial and about 14-24 min wall with three commands in parallel. The set is about 15-20 solves plus the stroke series, the drive cases, the bridge and the arms.
  - At pessimistic rates it costs 43-80 min serial.

Line numbers are at 22c62e9. "(inferred)" marks what was not read directly.

## 1. The process template SP7's design and pre-registration should follow

### 1.1 Facts: the session protocol (docs/process/SESSION_PROTOCOL.md)

**Start checklist (46-98)**
- Read order (48-55). This includes listing the open KI and B items the phase owns.
- Entry criteria (56-57).
- Git checks (58-72): a clean tree, HEAD's subject, the closing commit an ancestor of HEAD, and `git diff --stat <closing> HEAD` touching only docs/, TODO.md, CLAUDE.md, README.md, .gitignore and site/.
- Fast suite, with its test count in the session log (73-74).
- Inventory re-check (75-77).
- Plan mode (78-81): every open decision goes to the user with the recommendation first and the trade-off in one line.
- After approval (82-85): log D-SP<n>-nn decisions, save the design under docs/phases/inputs/, record deviations.
- Mark "in progress" in three places plus a handoff header line, and commit once as "Start SP<n>: status in progress" (86-92).
- If the session starts in Plan mode, do the read-only checks first. Run the suite and write the corrections right after approval (94-98).

**Step loop (100-134)**
- Implementer. physics.md changes in the same change for equations, frames, events, integrator settings and loss accounting.
- Reviewers by kind of output:
  - code: a physics or numerics skeptic plus a CLAUDE.md compliance auditor;
  - findings and summaries: an honesty auditor;
  - anything drawn: visual QA.
- Up to two fix rounds. An unfixed finding is either rejected with a reason or logged as a KI.
- Independent gate. On failure, mark the step `[!]` and ask the user.
- One commit per gate.
- The tracker commit at once, subject `SP<n> step <k>: trackers (<hash>)`.
- Push, then the Pages check (`gh run list --workflow pages.yml --limit 1`).

**Standing gates (136-144)**
- Fast suite green.
- `ruff check` clean and `ruff format` changing nothing.
- Golden 1-D outputs byte-identical, plus any program pin the phase names.
- The full suite after any physics-core change.

**Rules for finding runs (146-157)**
- Experiment files are committed before they are run.
- Any later change is a pre-registration amendment: its own commit, a logged decision, the earlier record kept.
- Runs start from a clean committed tree, tracker commit included.
- Results are never overwritten or deleted.
- `bug_suspect` blocks the finding.
- Never tune toward a target.

**App runs (159-169, D-SP2-37)**
- App summaries go in their own commit, `SP<n> step <k>: app summaries`, before any pre-registered run.
- Reviewers and gates use `--results-root <scratch>`.
- Demo launches come from a clean tree after the last code commit.
- No app run is cited in docs/findings/.

**Scope (174-189)**
- Anything outside section 2 of the phase file goes to the backlog or the known issues.
- Adding a step, a dependency or a deliverable is asked of the user and logged.
- Dropping or shrinking a step is a deviation recorded in section 12.

**Definition of done (191-202)**
- Every exit criterion is checked by an independent gate.
- A criterion stays open only with the user's acceptance, logged as a decision. The models are D-P2-08 (the calibration miss) and SP2's D-SP2-41 and D-SP2-42.

**End checklist (204-257)**
- Exit-criteria gate.
- Full suite and ruff, with counts.
- Demo under docs/demos/SP<n>/.
- Phase file closed; board and TODO.md updated.
- CLAUDE.md status, commands and layout; README.
- Public face (landing page, deck and its PDF, gallery, manual), with a local site build (220-222).
- Close-out questions to the user.
- Fact-check of the next phase file (SP3 by default) and its section 13 prompt finalised.
- Handoff archived and rewritten in the layout of section 8 (259-292).
- Memory updated.
- Cold-read check by an agent that did not write the documents (241-248).
- The closing-commit naming rule (249-253).
- Print the next prompt; push; Pages green.

**Gotchas that bear on SP7 (380-443)**
- Plan mode freezes background workflow agents that write scratch files (399-401). Run workflows outside Plan mode.
- A usage limit can orphan child processes (402-405).
- Subagent output files can be 0 bytes (393-396, KI-020).
- Machine speed varies about 3x under load; a searched planar run takes 7-25 s (426-428).
- A full suite run beside heavy jobs fails subprocess tests with 0xC0000142. Re-run those tests alone (429-432).
- `run_data.CALIBRATION_RECORDS` must be updated when a calibration changes (433-434; KI-003).
- Keep three caveats beside every headline number (440-442): the calibration miss, sweep-optimized unthrottled guidance, and "no structural mass charged". The last one changes meaning once SP7 charges a structural mass.

### 1.2 Facts: how SP2 wrote its step table, gates and checkpoints (docs/phases/SP2-launch-app-2d-scene.md, section 7, 1214-1305)

- **Opening paragraph (1216-1219).** The table is the approved design's table with Status and Commit columns added; section 12 lists the differences from the brief.
- **Process paragraph (1221-1230).**
  - Reviewers per step: a numerics skeptic on code steps, compliance on every step, visual QA through a 127.0.0.1 server, honesty on labels and caveats, security on two steps.
  - The standing gates.
  - Tests run on synthetic directories or a short fixed-guidance run, never on results/.
  - Reviewers and gates use a scratch results root.
- **Columns (1235):** `# | Step | Main files | Tests | Gate | Status | Commit`.
  - Steps added inside the plan take letter suffixes (A1a, A1b, A3b, A4b, A6v).
  - Two empty "Checkpoint" rows mark points where the work can be shown (1244, 1248).
  - Each Gate cell can be checked by an independent agent: byte identity against recorded sha256s, named tolerances, named runs and times, the reviews required.
- **Supporting text under the table.**
  - A deferral order "if room runs out", each item put to the user when it happens (1257-1260).
  - The detailed gate of one step spelled out (1262-1264).
  - A reference artefact defined with its expected bytes and sha256 before any edit (1266-1287).
  - "Notes on the order", giving the reason for the sequence (1289-1305).
- **Section 8 (1307-1423).**
  - The approved criteria word for word, with "the tolerances are fixed".
  - A paragraph listing what changed against the brief's draft (1388-1395).
  - At the close, a results table `# | Criterion | Verdict | Evidence`, with misses marked "fail, accepted (D-...)" (1397-1423).
- **Section 11, first entry (1643-1689 at least).**
  - The start checklist, including each literal check that failed and why.
  - Then step 0: the questions asked, the surveys, the reviews with finding counts, the approval, the files saved, the bookkeeping of the start commit, and a process note.

### 1.3 Facts: what a saved design contains (docs/phases/inputs/2026-10-05-SP2-design.md)

**Record header (1-16).** It states:
- the date approved, and that it is "copied word for word from the session's plan file";
- the commit its line numbers were checked at;
- that it supersedes the phase file's sections 5, 7 and 8 where they differ;
- that it is not edited (corrections go into the phase file);
- links to the surveys, reviews and mock-ups saved beside it.

**The plan itself:**
- provenance and a status line naming what approval approves (18-30);
- section 1, Context (32-40);
- section 2, Start checklist (done), with each literal failure and its cause, the facts the brief had wrong, and the open KI/B items (42-66);
- section 3, Decisions (68-119): the user's answers as a table (Id, Question, Answer), then the design decisions as a table (Id, Decision, Reason), then a "Not taken" line;
- section 4, Design per step (121-399), starting with a module and file table and a list of what stays unchanged;
- section 5, Steps (401-433);
- section 6, Exit criteria with tolerances fixed, and "Changes against the brief's N" (435-511);
- section 7, Verification commands (513-525);
- section 8, Risks, including measured timings and the new known issues to log (527-553);
- section 9, First actions after approval (555-565).

**Sources saved beside it as directories:**
- 2026-10-05-SP2-survey/ holds nine reports plus a README index. The index states the commit, that line numbers drift, that scratch scripts are not in the repository, and that each file has a one-line provenance header and is a byte-for-byte record.
- 2026-10-05-SP2-review/ holds six reviews.
- 2026-10-05-SP2-mockups/ holds the mock-ups.

### 1.4 Facts: the SP1 pre-registration (docs/phases/inputs/2026-10-03-sp1-preregistration.md)

- **Header (1-7).** Which step it was written for; that it is committed with the experiment files before any run; which step runs them; the amendment rule (own commit, logged decision, note kept and extended, never rewritten).
- **Section 1, What is registered (9-25).**
  - A table: File / Vehicle / What it declares.
  - The exact commands, in order.
  - A statement that nothing was run: only the resolve, the preflight `sim.check_resolved`, `results_io.check_result_names` and the config tests.
- **Section 2, The headline is not unknown (27-49).** It discloses that the headline number was already measured during validation. So the note fixes the design and the readings, not ignorance of the number, and it sets a reproduction tolerance.
- **Section 3, Comparison basis (51-123).**
  - P_ref and the offload definition.
  - Which numbers are headline and which are net of pad controls.
  - The basis of the arms, the sweep points and the calibration.
  - A derived "Resolution" R = R_P + 0.25 kg + G, every term traced to a documented constant (slope s, final_payload_xtol_kg, the gamma* curvature k and resolution w). This gives 2.55 kg at the same P_ref and about 3.8 kg against a re-solved P_ref.
  - A three-way reading rule: equal / unresolved / a real difference or a defect.
- **Sections 4, Cases (125-152), and 5, Sweeps (154-191).** Tables of what each is for, plus the checks made on the file and notes on regime changes inside sweeps.
- **Section 6, Choices fixed (193-228).** For example the unrounded exit speed 76.70717046013364 m/s and why rounding would bias the comparison; the closed-form heights; names; energy inputs with sources.
- **Section 7, How each result will be read (230-376).**
  - An expected reading for every case, labelled as estimates and explicitly "None is a target".
  - Undercut tests labelled as such.
  - Numeric branches covering every outcome. For example, the 200 m sign test: +3.14 to +30 kg is the expected reading, -3.14 to +3.14 kg is unresolved, and anything outside is investigated before any finding.
- **Section 8, Checks that block findings (378-405).** Three groups: those blocked by the code; those blocked by the pre-registration (verify mismatch, nonmonotone, capped refine, reference_failed pad); and those reported beside every number but never a gate.
- **Section 9, What nothing here measures (407-412).**
- **Section 10, Runtime estimate, serial (414-458).** Named unit costs S, V, O and a table per command.
- **Amendment 1 (460-573).** Made before any run, with the experiment files byte-identical and only reporting code changed. Every registered verdict is kept; a second reading is added beside the registered one and never replaces it.

### 1.5 Recommendations: the template for SP7

**Design file.** Save it as docs/phases/inputs/<date>-SP7-design.md, with the record header of 1.3 and the same nine sections.
- The decisions table separates the user's answers (Q1-Q7 of the phase file's section 10) from the design decisions, which get a Reason column.
- The step table keeps the phase file's S0-S7 and C, with letter suffixes for any split (S3a, S4b).
- Add a checkpoint after S3 (the structural headline can be produced) and one after S4 (the drive).
- Add a deferral order. Section 2, item 6 already names braking and the air column as the first to cut.
- Save this survey set as 2026-10-07-SP7-survey/ with a README index, as SP2 did.

**Pre-registration note (step S6).** Use the sections of 1.4, plus four items specific to SP7 (recommendations, partly inferred):
1. **Expected x\* before any flight.** The sizing model computes dm for each coefficient set (low, central, high), the full-load-sizing bound and the dynamic-factor bound before anything is flown. Each dm is placed on SP1's penalty-row curve (32.29, 22.88, 1.98 t at +2, +4, +8.1 t) to give an expected x\*, stated as an estimate. This is the phase file's own idea (5.5, 396-399).
2. **A re-derived resolution.** With dm depending on x, the slope of m_res in x is no longer SP1's s (inferred). So either derive R again from the coupling, or keep SP1's R and state why.
3. **The constant-2 t cross-check's tolerance, by branch.**
   - Against SP1's recorded 32,285 kg, P_ref is re-solved, so about 3.8 kg applies, as the phase file says (5.5, 392-394).
   - Against a +2 t row re-run in the same command, both solves fly the same vehicle at the same P_ref. Near bit-identity is expected, which justifies a tighter bound (inferred; check against the code path in S3).
4. **The band reading rule, decided in advance.** Report the offload range with dm at each end, and fix now the sentence used if the band is wider than the offload itself (phase file 5.6, 409-411; risk R1).

## 2. Test conventions

### Facts

**Docstring check (tests/test_scaffold.py)**
- `PHYSICS_MODULES` (27-39) lists atmosphere, dynamics, losses, phases, vehicle, units, assist/base, assist/constant_accel, assist/none, assist/track and display.
- `test_public_physics_functions_have_docstrings` (79-97) reads `SRC / f"{module}.py"` and skips any path that does not exist (83-84).
- `src/launchsim/phases.py` does not exist (phases is a package), so the "phases" entry is silently skipped.
- Nothing is hidden today: a probe at HEAD found no public def without a docstring in phases/*.py, offload.py, guidance.py, orbit.py, search.py, metrics.py, metrics_planar.py or compare.py.
- offload.py is a pure module per CLAUDE.md's layout but is not in the list.
- The check only requires that a docstring exists. The physics.md test-map row (6469) says it checks that the docstring states inputs, outputs, units and frame; the code at 79-97 does not.

**Import guard (tests/test_scene.py)**
- `RUN_PATH_MODULES` (108-125) lists sim, results_io, search, guidance, dynamics, offload, compare, metrics, metrics_planar, run_data and the six phases files. `SCENE_MODULES` is at 127; `test_run_path_modules_never_import_display_or_scene` is at 1373.
- The AST part reads each listed file and fails on a missing one; there is no skip (1380-1381).
- It matches absolute imports `launchsim.display` and `launchsim.scene` only. The codebase uses absolute imports (e.g. src/launchsim/sim.py 62-66).
- A second part starts a fresh interpreter, imports `launchsim.sim` and `launchsim.results_io`, and checks that neither display nor scene got loaded (about 1407-1430). This covers every module those two import, directly or indirectly.
- The assist package, config, vehicle and losses are not in the AST list.

**Slow marker**
- pyproject.toml 44-48: `addopts = "-ra --strict-markers"`, `markers = ["slow: slower than 5 s"]`, `filterwarnings = ["error"]`.
- CLAUDE.md requires `@pytest.mark.slow` above 5 s. No test or hook enforces it; no duration check exists under tests/.
- Collected at HEAD with `pytest --collect-only`: 1678 fast, 41 slow.
- Related records: KI-035 (TODO.md 352, fast tests over 5 s under load); KI-010 (292, planar convergence tests just over 5 s, slow tier only); D-SP2-42 (TODO.md 258, six slow tests accepted as a logged miss).

**Exact golden tier (tests/golden_1d_support.py)**
- 163-166: `REQUIRE_EXACT_ENV_VAR = "LAUNCHSIM_REQUIRE_EXACT_GOLDEN"`, value "1".
- `exact_tier_status` (348-364): the exact tier runs only when the recorded `EXACT_ENV_KEYS` (148-156: python, numpy, scipy, pandas, pyyaml, system, machine) match. Otherwise it skips, or it fails when the variable is set.
- SP1's and SP2's closing full suites ran with the variable set (SP2 section 8, row 11, line 1417).
- `GUARDED_PATHS` (147, which includes configs/) governs only recapture (755-775). A new configs/structures/ file does not affect the golden tests.

**Closed-form test style**
- tests/test_silo.py:
  - The module docstring (1-36) lists every closed form the file asserts.
  - Module constants hold the inputs (73-80): `G_EFF = MU_EARTH_M3S2 / R_EARTH_M**2`, `A = 3.0 * G0_MPS2`, `L = 100.0`, `A_BRAKE`, `ETA`, `REL = 1e-10`.
  - Each test computes the expected value from those constants in its own body. Example: `test_cold_energy_power_and_facility` (541-575) computes `e_drive = m0 * (A + G_EFF) * L` and `d_brake = L * A / A_BRAKE` and checks them with `math.isclose(..., rel_tol=REL)`.
  - Rounded README numbers appear only as "a cross-check of the constants only, never the expected value" (177-178, 570).
- tests/test_assist_energy.py states the identity and its closed forms in the docstring (1-22), with `REL = 1e-9  # required 1e-6` (48). The asserted tolerance is tighter than CLAUDE.md's, and the required one is quoted beside it.

**Test-to-equation map (docs/physics.md, from 6457; 258 table rows)**
- The preamble (6459-6462) says:
  - every expected value is computed in the test from constants and closed forms;
  - a rounded hand number is labelled as such;
  - tolerances are what the test asserts, with CLAUDE.md's minimum quoted where it is looser;
  - parametrised cases are one row.
- Columns: `Test | Equation / section | Tolerance`. The Test cell is `file.py::test_name`; several tests of one file are joined with `` `::name` ``. The middle cell names the equation and the physics.md section in quotes.
- Example (6577): `test_silo.py::test_cold_push_kinematics_and_drive_force` | v_exit = sqrt(2 a L) ... ("Silo model") | 1e-10 relative.

**Experiment classification**
- `test_every_shipped_planar_experiment_is_checked` (tests/test_config_planar.py 880-890) requires every planar_2d file under experiments/ to be listed in `PLANAR_EXPERIMENTS` (62-69). SP7's experiment file fails the fast suite until it is listed.
- `results_io.PREREGISTERED_PATHS = ("configs", "experiments")` (src/launchsim/results_io.py 447). A configs/structures/ file is therefore part of a run's pre-registration state (inferred from the name and the docstring at 448; tests/test_preregistration.py exercises this state).

### Recommendations

- Add `structure` and `assist/linear_motor` to `PHYSICS_MODULES` and to `RUN_PATH_MODULES` (phase file 5.11 already says so). In the same change:
  - make the docstring check fail on a missing path;
  - replace the dead "phases" entry with the six phases files;
  - consider adding `offload` (pure).

  This is a test-only change; log it as a KI if not taken.
- Write SP7's closed-form tests the way test_silo.py does:
  - inputs as module constants;
  - the closed form typed out in the test: hoop thickness p r / sigma, buckling stress E t / (r sqrt(3 (1 - nu^2))), the linear motor's power-limited t(v) and s(v) of phase file 5.7;
  - hand numbers only as cross-checks of the constants;
  - the asserted tolerance, with the CLAUDE.md requirement quoted;
  - one test-map row per test or parametrised group.
- Take KI-021, KI-022 and KI-023 in S4.
  - They are docstring and comment fixes in tests/test_silo.py, tests/test_convergence_2d.py, tests/test_search.py, tests/test_payload_search.py and tests/test_config.py.
  - Their owner rule is "the next phase that may touch those tests".
  - S4 edits tests/test_config.py (219-220, 283-289) and likely tests/test_silo.py, so it can fix all three at no risk.

## 3. Run-time budget

### 3.1 Facts: measured times

| Source | What ran | Wall time |
|---|---|---|
| SP1 step 9: three commands started within 22 s of each other from b3150c1 and ran concurrently (SP1 phase file 1079-1083, deviation at 1551-1553; physics.md "SP1 research notes" 6126-6134) | `run experiments/silo_offload_2d.yaml` | 14.1 min. From the directory timestamp 11:29:34 UTC, metrics.json lands at +820.9 s and summary.md at +844.8 s (file times read in this survey) |
| same | `sweep`: 5 sweeps, 20 points, each a searched point run plus a verified stage-1 solve | 20.9 min (summary at +1253.0 s). Pad baseline directory at +18.9 s. Points 57.5-68.4 s apart. Each sweep's first point lands 19.9-25.7 s after the previous index (the point run, inferred). Each index lands 34.3-45.5 s after its last point directory (that point's verified solve, inferred) |
| same | `run experiments/silo_offload_2d_readme.yaml`: pad, silo_cold, stage-1 pad control, one verified solve, paired pad | 2.1 min (summary at +127.5 s) |
| Inside the run command | All 19 run directories and their plots are written in the last 24 s (directory times 04:43:15-04:43:38 local), so per-solve times cannot be recovered (physics.md 6131-6133). Evaluation counts: stage-1 solves 37-44 (headline 42); pad controls 27, 41 and 29 (6133-6134) | |
| SP1 step 5 (SP1 phase file 1271-1273) | One stage-1 solve with verification, on a loaded machine | 89 s; the pad control about 30 s |
| SP1 pre-registration estimate (section 10, 414-458) | S 25-55 s, V 90-110 s, O 65-100 s | Run 30-50 min, sweep 39-64 min, bridge 3-6 min serial. The measured concurrent times came out at 0.3-0.5 of this |
| SP2 demo launches through the app, single job, clean tree fb34b24 (docs/demos/SP2/README.md 287-295) | Pad baseline 12 s. Assisted variant 14-16 s. Stage-1 pad control plus verified solve (penalty +8.1 t) 38 s. Pad control plus verified solve plus paired pad and decomposition (silo_cold_s1) 55 s | Totals 28.9, 70.4 and 54.5 s |
| SP2 A5 gate driver, on a machine loaded by other agents (docs/demos/SP2/criterion2-launches.md, rows 1-26) | Pad 18.6 s. Variants 21.5-24.9 s. silo_cold_s1 100.1 s. Penalty solves 74.5-83.9 s. Fixed cases 41.2-45.3 s. Stage-2 solve 107.5 s | |
| results/silo_offload_2d/20261003T112934Z/metrics.json | No wall-time field. The scan found only physics `*_time_s` / `*_duration_*` keys and `solve.n_evaluations` | |
| summary.md of that run | No timing line | |
| Silo screening (protocol 427-428; directory times) | silo_screening_2d run and sweeps | 27.1 and 25.7 min |

The machine has 32 logical processors (`NUMBER_OF_PROCESSORS=32`), so three single-process commands do not compete for cores. That they did not slow each other measurably is inferred: no serial run of the same commands exists to compare.

Derived unit costs (inferred from the table above). Splitting the app's 38 s into pad control and solve assumes one cost per evaluation: 69 evaluations plus one verification search gives about 0.35 s per evaluation, so V is about 29 s and C1 about 9 s.

| Rate set | S: searched run with comparison and writes | V: verified stage-1 solve | O: solve without verification | C1: stage-1 pad control |
|---|---|---|---|---|
| U, unloaded single job | 12-16 s | about 29 s | about 17 s | about 9-10 s |
| M, measured production (SP1 step 9, three commands at once) | 20-26 s | 34-46 s | 25-30 s | about 15 s |
| P, pessimistic (SP1 pre-registration rates) | 25-55 s | 90-110 s | 65-100 s | 30 s |

Check of set M against SP1's own commands:

| Command | Contents | Set M predicts | Measured |
|---|---|---|---|
| run | 4 S, C1, 2 verified pad controls, 9 V, paired pad, 2 fixed cases (S), 6 arms (S + O), 19 directories at 1.3 s | 13.7-17.7 min | 14.1 min |
| bridge | 3 S, C1, 1 V | 115 s | 127.5 s |
| sweep | own pad (S), 20 points (S + V) | 18.3-24.4 min | 20.9 min |

So M is the right central set.

**Correction for the phase file (fact).** Sections 5.5 (387, "about 90-110 s each with the verification, measured in SP1") and 5.8 (474-476) quote step 5's planning figure. The production run implies:
- about 35-45 s per verified solve under three-way concurrency;
- about 29 s unloaded (inferred split);
- about 15 s per stage-1 pad control, not 30 s.

### 3.2 Estimate for SP7's experiments (inferred; counts from the brief, costs from 3.1)

Assumptions:
- The structural sizing at each evaluation is closed-form arithmetic and adds nothing measurable (inferred). This holds if the load case comes from the vehicle at x, and the envelope from the pad run, which is flown anyway.
- Coupling option (i) keeps a solve's evaluation count near SP1's 37-44.
- A linear-motor or air-column case costs about the same as a constant_accel case; the track phase is a few seconds of integration (inferred).
- Each run directory costs 1-2.5 s to write with plots.

| Item | Counts | U [min] | M [min] | P [min] |
|---|---|---|---|---|
| A. Headline: pad, silo_cold, C1, 6 structural solves (central, low, high, full-load bound, constant-2 t, dynamic-factor bound) and 1 structure-off control | 2 S + C1 + 7 V | 4.1-4.2 | 5.1-6.7 | 12.2-15.5 |
| A'. Re-run SP1's three penalty rows (optional; citing them costs 0) | 3 V | 1.5 | 1.8-2.4 | 4.6-5.6 |
| A''. Coupling option (ii), the fixed point: 1-3 extra solves for each of 5 structural cases. Only needed if option (i) fails its monotonicity probe | 5-15 O | 1.4-4.2 | 2.1-7.5 | 5.4-25.0 |
| B. Stroke series at 76.7072 m/s, 4 points with structure, run as a sweep (its own pad, then S + V per point) | 5 S + 4 V | 3.0-3.4 | 4.0-5.3 | 8.3-12.1 |
| C. Linear-motor cases, 2-4 (a full-load P* and an offload solve each) | 2-4 (S + V) | 1.4-3.1 | 1.9-5.0 | 4.0-11.3 |
| D. Air-column cases, 1-2 | 1-2 (S + V) | 0.7-1.6 | 0.9-2.5 | 2.0-5.7 |
| E. Payload form: silo_cold P* with structure, 1-3 searches | 1-3 S | 0.2-0.8 | 0.4-1.3 | 0.5-2.8 |
| F. README-loads bridge, its own command (pad, silo_cold, C1, 1-2 V, paired pad) | 3 S + C1 + 1-2 V | 1.3-2.0 | 1.9-3.2 | 3.5-7.2 |
| G1. SP1's eight arms on the headline (6 effective: perturbed pad plus solve; the 2 efficiency arms reuse the nominal solve) | 6 (S + O) | 2.9-3.3 | 4.5-5.6 | 9.0-15.5 |
| G2. 3-6 one-at-a-time structural-coefficient arms (the pad is unchanged, so one O each; inferred, a new kind of arm) | 3-6 O | 0.8-1.7 | 1.2-3.0 | 3.2-10.0 |
| **Serial total**, A to G2 without A' and A'' | | 14.5-20.1 | 20.0-32.6 | 42.7-80.1 |

Wall time with commands in parallel (the wall time is the longest command):

| Grouping | Command | U [min] | M [min] | P [min] |
|---|---|---|---|---|
| Three commands | run (A, C, D, E, G1, G2) | 10.2-14.8 | 14.0-24.1 | 30.9-60.8 |
| | sweep (B) | 3.0-3.4 | 4.0-5.3 | 8.3-12.1 |
| | bridge (F) | 1.3-2.0 | 1.9-3.2 | 3.5-7.2 |
| Four commands: the drive cases (C, D) in their own experiment file, with its own pad and C1 | structural run (A, E, G1, G2) | 8.1-10.1 | 11.2-16.6 | 24.9-43.8 |
| | drive run (C, D) | 2.5-5.1 | 3.4-8.1 | 6.9-18.4 |
| | sweep (B) | 3.0-3.4 | 4.0-5.3 | 8.3-12.1 |
| | bridge (F) | 1.3-2.0 | 1.9-3.2 | 3.5-7.2 |

Reading (recommendation):
- **Totals.** At measured rates the whole SP7 set takes about 20-33 min serial. With SP1's three-command pattern it takes about 14-24 min wall, or 11-17 min if the drive cases get their own file. For comparison, SP1's commands took 14.1, 20.9 and 2.1 min.
- **Add-ons.** A' adds about 2 min; A'' adds up to about 7.5 min (at M).
- **Thresholds.** Under heavy load (set P, about 3x), the longest command stays under about 61 min. That is below D-SP1-17's 90-minute trim threshold (TODO.md 202), but above D-P2-05's 30-minute guide for `--jobs` (TODO.md 159). B-011 (TODO.md 109) stays deferred.
- **Wider stroke series.** Running low, central and high sets at every stroke point would triple B's solves, from 4 to 12, adding about 5-6 min at M (inferred).
- **How to run.** Run the commands in the background (protocol 428). Record each command's start time and each directory's last file time in the findings' Reproduction section: the run command writes all its directories at the end and records no per-solve wall time.

## 4. Full suite and the slow tests SP7 adds

### Facts

| Record | Result |
|---|---|
| SP2's close (SP2 phase file 1417 and 1887-1891; docs/handoff/NEXT_SESSION.md 282-288) | 1719 passed (1678 fast, 41 slow) in 3,062.98 s (51 min), with LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1, on a machine loaded by parallel gates. The first run had 28 failures and 3 skips, every one a subprocess exiting 0xC0000142; all passed on an immediate re-run |
| SP1's close (SP1 phase file 1126) | 1299 passed (1264 fast, 35 slow) in 13 min 8 s |
| Protocol (426-427) | Full suite 4-20 min at 2eebcae |
| Fast tier (SP2 phase file 1657) | Last recorded duration: 98.55 s for 1264 tests, at SP2's start. No duration is recorded for the 1678-test fast tier at HEAD; the "about 3 min" figure is not in the repository, and it was not measured here |

The 41 slow tests at HEAD, by file:

| File | Slow tests |
|---|---|
| test_app | 1 |
| test_app_server | 1 |
| test_calibration | 3 |
| test_closure | 1 |
| test_convergence_2d | 9 |
| test_golden_1d | 2 |
| test_height_event | 1 |
| test_ltg | 2 |
| test_offload | 3: the headline (795), the pad control (830), the tightened-budget convergence (861) |
| test_offload_pipeline | 5 |
| test_payload_search | 3 |
| test_planar_pipeline | 2 |
| test_search | 2 |
| test_silo_screening_record | 2: pad and silo_cold P* within 0.002 kg |
| test_video | 4 |

### Slow tests SP7 would add (recommendation; durations inferred from the unit costs of 3.1)

| Test | Cost |
|---|---|
| Constant-2 t cross-check against the +2 t row (phase file 5.9, 489; S3) | One verified solve at the shipped budget, plus the pad's P* unless pinned: 0.5-2 min |
| m_res in x stays monotone with dm(x) (S3; also the Plan-mode probe of option (i)) | 5-10 problem evaluations: 5-20 s |
| Convergence: tightening tolerances 10x moves the structural offload by < 0.1% (5.9, 498) | Two solves, one at a tightened budget, modelled on test_offload.py 861: 2-6 min |
| A searched planar run under `linear_motor` end to end, plus a linear-motor offload solve if pre-registered (S4) | 0.3-1.5 min |
| The structural offload case written and summarised end to end (S3, like test_offload_pipeline.py 2196) | 0.5-1.5 min |
| Payload form with structure (silo_cold P* with dm) | 0.3-0.5 min |
| Headline reproduction with the structure off | Already exists: test_offload.py 795; no new test |

Together these add about 4-12 min to the slow tier on an unloaded machine (inferred).

Everything else in section 5.9 fits the fast tier, because each is pure arithmetic or a push of a few seconds, as tests/test_silo.py does through `sim.simulate` (inferred):
- hydrostatic pressure, hoop and axial stress, buckling, domes;
- zero increment inside the envelope, and the sizing's monotonicity;
- the linear motor's closed forms on track-only pushes;
- braking, the adiabatic air column, the dynamic load factor;
- config refusals, KI-030's validators, the structure file's validation;
- the reworded caveat tests.

The step table (phase file 790-795) asks for the full suite after S3, S4 and S5 and before the close: four runs of about 15-50 min each, depending on load.

## 5. Site and public face

### Facts

**Site build**
- Build with `uvx --with markdown==3.11 python site/build.py`; preview with `python -m http.server 8000 --directory _site --bind 127.0.0.1` (site/build.py 35-36).
- `MARKDOWN_PIN = "3.11"` is checked at run time (83, 1267-1269).
- CI installs `markdown==3.11` (.github/workflows/pages.yml 46) and fails on any broken internal link. `--allow-broken-links` is for local previews only (38, 1260).
- The protocol's end checklist writes the command without the pin (SESSION_PROTOCOL.md 220-222, "see site/build.py for the pinned version").
- The build refuses scene pages written from results/app/ or flagged exploratory (site/build.py 20, 101-110, 1012-1023).

**Deck**
- site/deck/index.html and site/deck/launch-assist-sim-deck.pdf (20 pages at SP2's close).
- The PDF is printed by headless Edge from PowerShell (not Git Bash), against the built site served on 127.0.0.1 with `?print` (docs/demos/SP2/README.md 540-560; the full command is at 553).

**Gallery**
- site/examples/index.html gives the regeneration command of each entry: replay at 361, 420, 548, 612 and 671; scene at 469; animate at 363, 367, 549-550, 613 and 615.
- Six pages: failed-ignition, ignition-timing, offload-vs-paired-pad, pad-vs-silo-cold, pad-vs-silo-offload, pad-vs-silo-offload-scene.
- media/ holds an MP4, GIF and poster per animation, the scene's MP4 and GIF, and the app screenshot.
- Lines that mention "structur": 12 in site/index.html, 17 in site/deck/index.html, 12 in site/examples/index.html. For example site/index.html 131 and 316 say "no structural model exists yet (phase SP7, next)".

**Manual chapters SP7 would touch**

| Chapter | Lines |
|---|---|
| 05b-offload.md | 100 (the penalty field, "a penalty row, not a sized structure"); 162-163, 224, 285, 296, 351 |
| 12-faq-glossary.md | 23, 46, 80-81 ("Can I simulate ... a linear motor": "Not yet"), 97, 122, 191 (the glossary row **penalty row**) |
| 07b-app.md | 25, 106, 128-129 (the penalty field), 269, 404-405, 422 |
| 07-commands.md | sections `run` (24), `sweep` (64), `scene` (126), `app` (144); only if commands or options change |
| 06-vehicles.md | 142-146 ("Never edit a calibrated file; fork it"); a new structures section beside "Display files" (128) if configs/structures/ is created |

Not in the brief's list but also affected (fact):

| Chapter | Lines |
|---|---|
| 05-assist-and-ignition.md | 14-16 (`linear_motor` "planned, README roadmap Phase 3 ... Refused today"); 32 (track angle) |
| 08-outputs.md | 278 (`drive_power_peak_t_s` "on the run clock (t = 0 at push start)", KI-032); 280-281 (push metrics); 228 (penalty keys) |
| 09-reading-results.md | 314, 340, 361, 389 |
| 03-concepts.md | 118, 182-183 |

**Demo record models**
- docs/demos/SP1/README.md is the closer model for SP7, since SP1 was also a CLI phase. Its sections: What it shows (11), Files (63), Commits (93), Results directories (107), Exact commands (119), The screenshot (144), Reproduce on a fresh clone (158). Its files: the console captures console-run.txt, console-sweep.txt and console-bridge.txt, the offload block, a replay page and its screenshot.
- docs/demos/SP2/README.md: What it shows and what it is not (12), Commit (42), Commands (87), screenshots, the QA table, launches with wall times (287-295), the deck PDF (540), Left open (562).

**.gitignore**
- `*_animation.mp4`, `*_animation.gif`, `*_replay.html`, `*_scene.html` and `*_scene.mp4` are ignored at any depth, and there is no `!docs/demos/**` exception. Demo pages therefore need different names, with hyphens instead of these suffixes (SP1 used pad_vs_offloaded_silo.html; SP2 used pad-vs-silo-cold-scene.html).
- results/** is ignored except each run's top-level summary.md.

### Found in passing (facts, for S3's wording step)

**Further sources of the "nothing structural" wording.** The phase file lists its sources in 5.1 (295-313). The wording also appears in:
- `app.SP1_HEADLINE`'s "Structure." caveat (src/launchsim/app.py 1473-1478): "the needed mass is unknown: no structural model exists. They are assumptions, not a sized structure."
- `scene.structure_note`, used in video footers (src/launchsim/scene.py 1295-1314): "no structural mass is charged for the push" (1310) and "an assumption, not a sized structure" (1312-1313).
- The offload section's table label (src/launchsim/summary.py 1821): "assumed stage-1 dry mass added [t] (an assumption, not a sized structure)".
- Docstrings at replay.py 476 and 988 and app.py 3706.

**A test that pins RQ1's text.** `tests/test_app_server.py::test_sp1_headline_matches_the_findings_note` (3045-3075; `FINDINGS_NOTE` at 117) requires SP1_HEADLINE's text, its six caveat titles and their phrases to stay verbatim in docs/findings/RQ1-fuel-offload-2d.md. So Q6 (update RQ1, or write a new note with a pointer section) must either keep RQ1's headline paragraph and the bold caveat titles, or change the test and the constant together. Recommendation: the new note, which leaves RQ1's text alone.

**The gallery pages.** A run without structure keeps today's sentences (5.1, 312-313). All six gallery pages come from SP1's and Phase 2's directories, so they may regenerate byte-identical unless the uncharged wording itself changes (inferred). Record the diff either way.

## 6. TODO.md items and the decisions that bind SP7

### Open items

Text is quoted exactly, abridged only where marked "..."; line numbers are at 22c62e9.

| Item | Line | Owner / target | Text |
|---|---|---|---|
| B-004 | 102 | P1, SP7 (D-SP1-18) | "Structural mass for the 4 g full-stack push and the interface-hardware mass penalty. Decides whether the headline survives; SP1 shows it only as parametric rows (D-SP1-04)" |
| B-005 | 103 | P1, SP7 for the force-limited drive; any remainder later | "`linear_motor`: force- and power-limited drive with efficiency. Needed before the hot-start question can be answered" |
| B-007 | 105 | P2, later (README Phase 3) | "Air-column piston, friction, modelled carriage braking, release at a target speed". To be re-targeted if Plan mode takes braking, the air column or the target-speed release (phase file section 2, item 6) |
| KI-030 | 347 (the phase file says 346) | medium, SP7 | "The config accepts `true`, numeric strings, inf and NaN for several numbers. The models are not strict and most numeric fields do not set `allow_inf_nan=False`. ... `stroke_m: true` (taken as 1.0 m); `stroke_m: "100"` and `fixed.stage1_fraction: "0.05"` (strings); `paired_pad: "yes"` (taken as true); `stroke_m: inf` with `net_accel_g`; `net_accel_g`, `brake_decel_g` and `carriage_mass_t` of inf; `t_ign_s` of NaN, inf, 1e9 or -1e9 (no bound); `track.exit_altitude_m` of NaN, -1000 or 5000 (no bound); `startup.t_ramp_s: inf`. ... Evidence: docs/phases/inputs/2026-10-05-SP2-survey/03-config-and-form.md, section 3.3." |
| KI-039 | 356 | low, SP7 (S3) | "A summary.md whose offload block has an imposed (fixed) case files that case under the section "Propellant saved at fixed payload" (summary.py `OFFLOAD_SECTION_NAME`, `offload_section`), whose basis line (compare.py `OFFLOAD_COMPARISON_BASIS`, also in metrics.json's `offload` record) says "every offload is measured at the reference payload P_ref"; an imposed case flies its own payload capacity P*. ... Reword the heading and the basis line for imposed cases at source with the honesty review, then drop the banner's disclaimer; recorded results are not rewritten. ... accepted by D-SP2-41." |
| KI-036 | 353 (the phase file says 352) | low, the phase that next edits replay.py (SP7, if S3 rewords replay.py) | "`replay.py` (around line 1820) writes `bool(git.get("dirty"))` into the page, so a directory whose git state is unknown ... reads as clean on the replay page; the scene page and the app's banner show it as unknown." |
| KI-032 | 349 | low, later (S4 may take it) | "The metric `drive_power_peak_t_s` is on the absolute run clock (metrics_planar.py 1012), while the other time metrics of a planar run are after release, `t_release_s` excepted. It reads 2.6073 s on silo_cold and 5.2146 s on silo_cold_200m ... A reader subtracts `t_release_s` before showing it on the release clock." |
| KI-021 | 314 | low, the next phase that may touch those tests | Summary: tests/test_silo.py gives the 3 g0, 100 m felt load as 3.9992 g0 in three places (the module docstring, the `test_cold_felt_acceleration_and_interface_force` docstring, and its 1e-4 hand-number literal). The value is 3.99915, "3.9991 to four decimals". "Correct all three together when a step may touch that existing test" |
| KI-022 | 318 | same | Summary: stale docstrings in tests/test_convergence_2d.py 34-38, tests/test_search.py 72-74 and tests/test_payload_search.py 80 about which tests "fly the shipped search rtol of 1e-8". "Docstring-only fix." |
| KI-023 | 322 | same | Summary: two comments in tests/test_config.py stale since SP1 step 3. "Comment-only edits, together with KI-021 and KI-022." |
| KI-035 | 352 | low, the next phase that edits tests/test_scene.py, else standing | Summary: fast tests run over 5 s under load (test_golden_1d 5.84 s, test_search 5.57 s, and the import-guard test reported over 5 s, though 2.8-2.9 s alone). "Split the import check into a cheaper fast part and a slow part, or mark it slow, when a step may edit that file." SP7 edits RUN_PATH_MODULES in that file, so it becomes the owner |
| KI-003 | 283 | low, standing | "run_data.CALIBRATION_RECORDS ... feeds the calibration caveat in animate and replay; update it whenever the calibration is re-run." A new vehicle fork for the bridge gets the no-record caveat unless SP7 adds an entry (phase file 527) |

Also relevant (facts):
- KI-038 (355, owner: the phase that next edits scene.py). The scene page lacks the renderer's version and git state. It falls to SP7 if S3 or S4 edits scene.py, which `scene.structure_note` (1295-1314) and the push-metric readers (scene.py 513-528) make likely.
- KI-019 and KI-031 (306, 348) stay with the phase that edits templates/replay.html. SP7 does not (D-SP2-34).
- KI-010 (292) and KI-020 (310) are standing.
- KI-006 (287, medium, later) requires disclosing M2 and M4 over gamma* +/- 0.5 deg on offload runs, as RQ1 did.

### Decisions that bind SP7's design (TODO.md decisions log)

**Physics and calibration (Phases 1-2)**
- D-P1-01 (148): `constant_accel` is prescribed, so a hot start buys no exit speed. The linear motor is where carriage mass and efficiency can move the exit speed and the offload.
- D-P2-02 (156): the reference orbit is fixed.
- D-P2-04 (158): a shared guidance parametrisation and grid, sweep-optimized per run.
- D-P2-05 (159): `--jobs` is deferred unless an experiment exceeds 30 min serial.
- D-P2-07 (161): nothing in results/ is deleted.
- D-P2-08 (165): the +14.3% calibration miss travels with every finding.
- D-P2-09 (166): M2 is diagnostic only.

**SP1**
- D-SP1-03 (188): offload semantics. P_ref is the full-load pad's P*; tanks are partly filled; dry masses are unchanged except for a penalty.
- D-SP1-04 (189): the penalty rows stay.
- D-SP1-08 (193): one session per phase, with the next phase prepared.
- D-SP1-09 and D-SP1-10 (194-195): the `offload:` block and post-pass; pad controls; stage 1 is the only headline.
- D-SP1-13 (198): the README-loads bridge.
- D-SP1-14 to D-SP1-16 (199-201): public repository, push after every step, public face refreshed at every close.
- D-SP1-17 (202): a trim is considered only above about 90 min per command.
- D-SP1-18 (203): SP7 runs before SP3-SP6.

**SP2**
- D-SP2-12 (228): the `exploratory` label is reserved for app runs.
- D-SP2-23 (239): one caveat source, fixed at source in replay.py.
- D-SP2-31 (247) and D-SP2-39 (255): the app's basis and run names. A change to experiments/silo_offload_2d.yaml changes what the app launches.
- D-SP2-34 (250): templates/replay.html is frozen and its sha256 pinned.
- D-SP2-36 (252): SP1's headline constant is checked against RQ1 by a test.
- D-SP2-37 (253): app-run commits and scratch results roots.
- D-SP2-40 (256): SP7 runs next.
- D-SP2-41 (257): KI-039 goes to SP7's reporting step.
- D-SP2-42 (258): the slow-test miss, a precedent for SP7's own slow tests.

## 7. Summary of corrections and recommendations

Facts that differ from the phase file or other records:
1. **Per-solve cost** in sections 5.5 (387) and 5.8 (474-476). Measured production is about 35-45 s per verified solve under three-way concurrency and about 29 s unloaded (inferred split), not 90-110 s. A stage-1 pad control takes about 15 s, not 30 s.
2. **TODO.md line numbers.** KI-030 is at 347 (phase file line 684 says 346); KI-036 is at 353 (the phase file says 352).
3. **More sources of the structural wording** beyond section 5.1's list: app.py 1473-1478, scene.py 1295-1314, summary.py 1821, and docstrings at replay.py 476 and 988 and app.py 3706.
4. **tests/test_scaffold.py's "phases" entry is skipped** (83-84; there is no src/launchsim/phases.py).
5. **The protocol's site-build command** (220-222) omits the markdown pin that site/build.py (83) and pages.yml (46) enforce.
6. **Two more manual chapters change with the linear motor:** 05-assist-and-ignition.md (14-16) and 08-outputs.md (278-281). The brief does not list them.

Recommendations:
- Follow the templates of 1.5.
- Put the drive cases in their own experiment file, so four commands run in parallel (about 11-17 min wall at measured rates).
- Budget the band, the bounds, the stroke series, the drive cases, the bridge and the arms in full; no trim is needed at any measured rate.
- Take KI-021 to KI-023 and KI-035 with the test edits S3 and S4 already make.
- Fix the docstring check's silent skip when the new modules are added.

Note: the harness refused the scratch copy at scratchpad/a0/09-process-tests-budget/REPORT.md, because subagents may not write report files, so this message is the only copy. The scratch scripts used are in C:/Users/rahul/AppData/Local/Temp/claude/D--DEV-ClaudeProjects-SpaceRocketOptimization/3e237173-2609-4e7b-ac46-15c1a393670f/scratchpad/a0/09-process-tests-budget/: scan_metrics.py, sweep_times.py, docstring_probe.py and budget.py.
