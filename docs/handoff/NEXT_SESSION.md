# Handoff: SP7 in progress (session 2026-10-08), at step S7a

SP7 started 2026-10-08. If you are a new session and the phase file says in progress, resume
per SESSION_PROTOCOL.md section 10 from the step table.

## 1. Header

- **Phase in progress: SP7**, the structural mass of the push load and a force-limited drive
  (planar model), docs/phases/SP7-structural-mass-push-load.md, status line "in progress
  (session 2026-10-08)". Written 2026-10-16 at checkpoint 1 of the step table (an
  in-progress handoff point, D-SP7-29), following docs/process/SESSION_PROTOCOL.md section
  10, while step S7a's three pre-registered commands were running.
- The last commit before this file is 1b5f9d4 (`SP7 step S6a: trackers (cbbd7bc); D-SP7-45
  to D-SP7-47`), pushed to origin/main. The pre-registration commit is cbbd7bc (files A and
  C, their tests in tests/test_config_planar.py, the pre-registration note, and 15 lines of
  docs/physics.md: the two files' rows in the shipped-experiments table, the test-map rows
  for their tests (one added, one extended) and two sentences that list the shipped planar
  experiments, reworded to name them; `git show --stat cbbd7bc`). The last commit that
  changed src/ is 0a16a89 (step S3a).
- This file is part of the documents-only commit that follows 1b5f9d4, subject
  `SP7 in progress: handoff at step S7a` (protocol section 10, item 6); a file cannot hold
  the hash of its own commit. That commit changes docs/ and TODO.md only; it changes no
  code, configuration, experiment or result, so it is a clean commit S7a may re-run from
  (pre-registration section 12).
- SP2's handoff (written 2026-10-07 at SP2's close) is archived as
  docs/handoff/archive/2026-10-07-SP2.md. SP1 closed 2026-10-04 (5007515); SP2 closed
  2026-10-07 (3a1b243).
- Authority (protocol section 10): `git log` and `git status`, then the step table (phase
  file section 7), then the session log (section 11). Section 4 below is a dated snapshot
  and loses against all three.

## 0. Update of 2026-10-19 (session 2; read first: sections 4 and 6 below are the 2026-10-16 snapshot)

- The three S7a commands finished on 2026-10-16 (run A 18:19:59Z, sweep A 17:48:15Z, run C
  17:21:03Z; no FAILED.txt). The note docs/findings/RQ1-structural-2d.md was drafted by
  session 1 (untracked until S7a's commit), with its tables, figures and three scripts.
- Session 2 committed the scripts (0a12c36), re-ran the convergence check from the committed
  script (the same bits; deviation 42), and, for the failing section 9 check (no shortfall
  on the three no-offload sweep points), the user decided D-SP7-48: step S3c (1e4c732,
  77e1691), pre-registration Amendment 1 (74eb3c8), and `sweep` A re-run alone from the
  clean commit after S3c's tracker commit.
- Later on 2026-10-19: the sweep re-run (results/silo_structure_2d/20261019T172327Z) reproduced
  the first sweep cell for cell; step S7a closed at 6fa2ff0 (the note, docs/findings/RQ1-structural-2d.md).
  S4 runs in a git worktree on branch `sp7-s4` (outside the repository, in the session's scratch
  folder); if this session ended before it was merged, the branch holds its work (`git log main..sp7-s4`).
- 2026-10-24: step S4 closed (25967be on `sp7-s4`, merged into main as 8c4b41a; the linear
  motor, KI-030, KI-021 to KI-023). D-SP7-49 (the push's event set) and D-SP7-50 (the force
  law's power cap on the flown, tapered force; KI-045, fixed in S4a) recorded. Next: S4a, S4b,
  S5, checkpoint 2, S6b, S7b, S7c, S8, C1, C2.
- Resume point: the phase file's section 11, entry "2026-10-19 (session 2)" and its S7a close line. If a sweep
  directory newer than 20261016T171522Z exists under results/silo_structure_2d/, check it
  as item 1 of section 6 says (finished, interrupted or raised); the reproduction check of
  Amendment 1 (every pre-existing column of both sweeps' sweep_index.csv equal by name at
  %.12g) comes before any use of it.

## 2. Read these first, in this order

1. This file.
2. docs/process/SESSION_PROTOCOL.md (sections 3, 4, 10 and 11 above all).
3. docs/phases/README.md (the program board).
4. docs/phases/SP7-structural-mass-push-load.md: the step table (section 7), the exit
   criteria (section 8), the session log (section 11), the deviations (section 12, items
   1-41) and the Resume prompt (section 13).
5. CLAUDE.md.
6. TODO.md. While reading it, list the open known issues and backlog items owned by SP7
   (section 4 below lists them as of this file).
7. README.md.
8. The memory index and the notes it links:
   C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md
9. The inputs the phase file links: docs/phases/inputs/2026-10-08-SP7-design.md (the
   approved design, version 2; it supersedes the brief's sections 5, 7 and 8),
   docs/phases/inputs/2026-10-08-SP7-sources.md (the source note for every coefficient)
   and docs/phases/inputs/2026-10-15-SP7-preregistration.md (files A and C; for S7a read
   its sections 1, 7, 8, 9, 11 and 12 first). The surveys
   (docs/phases/inputs/2026-10-08-SP7-survey/) and the review of draft v1
   (docs/phases/inputs/2026-10-08-SP7-review/) as a step needs them.

## 3. The request

No new research request in SP7. The phase is the user's own ordering (D-SP1-18, confirmed
by D-SP2-40): charge the structural mass that the 4 g full-stack push needs, with a
first-order sizing model validated against closed forms, so that SP1's headline (41.26 t
of stage-1 propellant, 10.04% of stage 1, before any structural mass) carries a modelled
structural cost with an uncertainty band beside the assumed penalty rows; re-open the
depth question; and build the drive realism that interacts with it (phase file, section 1).

The user's rules for the session, quoted from the start prompt (phase file, section 13):

> Rules for the whole session. Plan mode, and docs/physics.md in the same change, for
> anything touching the equations of motion, frames, events, integrator settings or loss
> accounting (the linear motor, the air column and braking touch the track equation and
> its events). Every structural coefficient is sourced or marked assumed, in a structure
> file, never in a calibrated vehicle file. Every new physics piece passes its closed-form
> test before an experiment uses it. Never choose a drive or structural parameter to make
> the assist look better; published claims and probe numbers are comparisons, never
> targets. The experiment file and its expected readings are committed before any run
> (pre-registration), the runs start from a clean commit, and no results directory is ever
> overwritten or deleted. App runs follow D-SP2-37: reviewers and gates use a scratch
> results root, demo launches come from a clean tree after the last code commit, their
> summaries go in their own commit, and no app run is cited in a finding. Keep SP1's
> penalty rows beside the modelled number.

and, from the same prompt: "No validated number may move: the pad and silo_cold payload
capacities, and SP1's headline with the structural model off", and "Report anything that
undercuts the hypothesis, a modelled structure that cancels most of the offload included,
as plainly as the rest."

The user's answers during the session (full text in TODO.md's decisions log): Q1-Q7 and
the app point, every recommended option (D-SP7-01 to D-SP7-08); the four follow-ups after
the review of draft v1, every recommended option (D-SP7-09 to D-SP7-12); the design
approved with the plan (D-SP7-13 to D-SP7-35); the interstage's increment charged to stage
1 (D-SP7-36, S0); the plausibility rule kept as approved, both ends printed (D-SP7-41, S2);
at S6a's gate, both fork tests registered (D-SP7-45), the headline form's four amendments
(D-SP7-46) and exit criterion 3's gallery clause read as deviation 32's four regions
(D-SP7-47), each the recommended option. On 2026-10-11 the workflow resumed with the
session model changed to Fable 5.1 (agents inherit the session model; no criterion
depends on it; session log, step S3).

## 4. State when this file was written (snapshot, 2026-10-16, about 17:21 UTC)

**Step table** (phase file, section 7). Steps ran in the order 0, S1, S0, S2, S3, S3b, S3a,
checkpoint 1 with S6a.

| Step | What | Status | Commit (tracker commit) |
|---|---|---|---|
| 0 | Plan mode: surveys, questions, design v2 approved | [x] | a7c9f0a, "Start SP7: status in progress" |
| S0 | The source note for every coefficient | [x] | 81e045d (4494fe1) |
| S1 | Sizing primitives (structure.py) with closed-form tests | [x] | a3bd183 (1945144) |
| S2 | Station model, the two structure files, the frozen sets | [x] | 45e39d4 (792dd69; D-SP7-41 in 15b4e6e) |
| S3 | The sizing coupled into the offload solve | [x] | 889f6ea (6180ae1) |
| S3b | Reporting the structure | [x] | 216a79c (77eb006) |
| S3a | The structural wording at every source; KI-036, KI-038, KI-039 | [x] | 0a16a89 (f10cf58) |
| checkpoint 1 and S6a | Preflight of files A and C, the timing case; files A and C and the pre-registration | [x] | cbbd7bc (1b5f9d4) |
| S7a | `run` A, `sweep` A, `run` C; the findings note's structural part | [~] in hand | |
| S4, S4a, S4b, S5, checkpoint 2, S6b, S7b, S7c, S8, C1, C2 | the drive, file B, the note completed, the public face, the close | [ ] | |

**S7a's three commands**, started together from the clean commit 1b5f9d4 as the
pre-registration (section 1) gives them, with plots:

| Command | Started (UTC) | Results directory | State at about 17:21 UTC |
|---|---|---|---|
| `uv run python -m launchsim run experiments/silo_structure_2d.yaml` (run A) | 2026-10-16T17:15:10Z | results/silo_structure_2d/20261016T171513Z | running; the directory is empty until the end (the run command writes every file at the end) |
| `uv run python -m launchsim sweep experiments/silo_structure_2d.yaml` (sweep A) | 2026-10-16T17:15:19Z | results/silo_structure_2d/20261016T171522Z | running; baseline/ and sweep_1/ started |
| `uv run python -m launchsim run experiments/silo_structure_2d_readme.yaml` (run C) | 2026-10-16T17:15:26Z | results/silo_structure_2d_readme/20261016T171529Z | finished: summary.md written 17:21:03Z (5 min 37 s), no FAILED.txt; not yet checked against the pre-registration's section 9; its summary.md is untracked until S7a commits it |

Runtime estimate (pre-registration section 11): run A about 59 min at this machine's
measured rate (26-34 min at SP1's production rates, 56-80 min pessimistic), sweep A about
34 min (34-45), run C about 5 min (5-6); under D-SP1-17's 90 min. The machine ran about
1.8-2.3 times slower than in SP1's production runs at checkpoint 1.

**The expected readings registered** (pre-registration section 7; estimates by the coupled
placement on SP1's penalty curve, sizing only, no offload solved; none is a target, and a
different result is reported as it is): the headline silo_cold_s1_st about 11,105 kg of
stage-1 offload (26.9% of 41,262.9 kg; 2.70% of stage 1), reading "cancels most"; the
physics band from no offload (high-mass end) to 28,514 kg (the plausibility-scaled
low-mass end; 23,658 kg unscaled), "undecided"; the outer envelope from no offload to
31,093 kg; the arms 8.1 to 14.8 t; sweep 1 no offload at 25 and 50 m, offloads from 100 m;
sweep 2 no offload at 50 m (7.07 g0 felt, stage 2 sized); file C about 7,475 kg on the
fork. The placement's measured error on the synthetic timing case: 297 kg (2.0%) low
(deviation 41). The pre-registration's section 8 fixes how each result is read (D-SP7-32,
D-SP7-46).

**Tests and lint at the last gates** (phase file, session log): fast suite 1881 passed, 47
deselected (S6a's gate, 2026-10-16); the last full slow tier 47 passed in 3,424.9 s (S3a's
first gate, 2026-10-15; the suite then 1,921); ruff clean; the exact golden tier, the
planar digest pin, the output capture and the golden-dump field lists pass;
templates/replay.html's sha256 unchanged.

**Open items owned by SP7** (TODO.md): KI-030 (medium; the strict validators, step S4,
D-SP7-28); KI-021, KI-022 and KI-023 (low; stale test docstrings and comments, step S4,
D-SP7-34); B-004 and B-005 [~]; B-007 [~] in part (the sealed shaft, the target-speed
release, braking as closed-form functions). Opened in SP7: KI-040 (low; an app video of two
modelled runs does not fit 1280 x 720; owner the phase that next edits
templates/scene.html or scene.py's per-run note; deviation 37). Closed in SP7: KI-035 (S1),
KI-036, KI-038 and KI-039 (S3a). Not SP7's: B-016 (the app's form, later, D-SP7-08); KI-032
(later); KI-019 and KI-031 (the phase that next edits replay.html, which SP7 does not);
KI-003 (standing: update run_data.CALIBRATION_RECORDS when the calibration is re-run).

**Decisions of the session**: D-SP7-01 to D-SP7-47 (TODO.md). D-SP7-01 to D-SP7-12 the
user's answers; D-SP7-13 to D-SP7-35 the approved design; D-SP7-36 and D-SP7-37 from S0;
D-SP7-38 to D-SP7-41 from S2; D-SP7-42 to D-SP7-44 from S3; D-SP7-45 to D-SP7-47 from S6a.
Deviations 1-41 are in the phase file's section 12.

**Results directories that S7a compares against** (on disk; only each directory's top-level
summary.md is tracked):

- results/silo_offload_2d/20261003T112934Z (SP1's run: the headline and the penalty rows);
- results/silo_offload_2d/20261003T112949Z (SP1's sweeps);
- results/silo_offload_2d_readme/20261003T112956Z (SP1's bridge on the README-loads fork);
- results/silo_screening_2d/20260930T175743Z (silo_cold's uncharged P*).

## 5. Requirements and status

| # | Requirement | Status on 2026-10-16 |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done before SP1; caveats branched for a structural run in S3a |
| R2 | An animated scene of the launch, 2-D first | Done in SP2 |
| R3 | The same in a 3-D world | Not started: SP3-SP6, after SP7 |
| R4 | Configure the launch depth in the silo | Done in SP1; the depth sweep with the structure charged runs in S7a |
| R5 | Configure where the thrust ramp starts | Done in SP1 |
| R6 | Reduce the propellant at fixed payload and report the fraction replaced | SP1's first answer stands with its caveats; the structural re-solve is running (S7a) |
| R7 | Stay on the Falcon 9-class model | Standing; configs/vehicles/ unchanged since a7c9f0a |
| R8 | Lose nothing between sessions | This in-progress handoff, the session log and the step table |
| R9 | One fresh session per phase | SP7 has run in one session since 2026-10-08; this file is its resume point |
| R10 | Public repository pushed after every step | origin/main at 1b5f9d4 when this file was written |

**SP7's exit criteria** (phase file section 8; checked by the independent gate at C2):

| # | Criterion | Status so far |
|---|---|---|
| 1 | Validation first | Structural pieces met: the S1-S3a test commits precede cbbd7bc; the drive pieces (S4-S5) not built |
| 2 | Provenance and freeze | Holding: both structure files at their S2 sha256; configs/vehicles/ and the seven shipped experiment files unchanged since a7c9f0a (checked 2026-10-16) |
| 3 | Nothing validated moved | Holding at every gate so far (pins, field lists, replay.html, the structure-off headline and the constant-2 t cross-check reproduced to 0.0 kg in S3, the gallery per D-SP7-47); S7a's reproductions and the app's slow launch after KI-030 (S4) pending |
| 4 | The structural headline | Pending: S7a |
| 5 | The frozen sets recomputed | S6a's half met (both files reproduce, pre-registration section 12); S7a's gate and C2 pending |
| 6 | Convergence | Pending: S7a's convergence check (pre-registration section 1); the linear-motor part at S4b and S7b |
| 7 | Axes and drive | Pending: the sweeps run in S7a; file B in S6b and S7b |
| 8 | The findings note and the KI closures | Pending (S7a, S7b, S7c); KI-035, KI-036, KI-038, KI-039 closed |
| 9 | docs/physics.md | Holding for S1-S6a; the drive sections pending |
| 10 | Full suite, ruff, no new dependency | Pending (C2) |
| 11 | Demo | Pending (S8) |
| 12 | Close-out | Pending (S8, C1, C2) |

## 6. How to resume SP7

1. **Look before running anything.** No test suite, app or other heavy job runs beside the
   S7a commands (pre-registration sections 1 and 11). Check for them by command line
   (PowerShell: `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` and match
   `launchsim` in the command line). If a command is still running, wait for it with a
   read-only check; never end a turn waiting on it. A stopped command's top-level directory
   says how it ended:
   - **finished**: its summary.md (written last) and no FAILED.txt; item 3.
   - **FAILED.txt**: written for any exception that reached the command, Ctrl+C included
     (src/launchsim/results_io.py: `except BaseException` calls `write_failure_marker`,
     which writes the traceback under "This run raised before its results were complete",
     then re-raises). Read the traceback's last line. `KeyboardInterrupt` means the command
     was **interrupted** (item 4). Any other exception means it **raised** (item 5).
   - **neither file, and no live process**: the process ended without a Python exception
     (for example a killed process or a closed console), so it was **interrupted** (item
     4).
2. **Protocol checks** (section 10, then section 3 without the status change): the tree is
   clean apart from the S7a summaries under results/ (untracked); every `[x]` row's commit
   is in `git log`; HEAD's subject is `SP7 in progress: handoff at step S7a`, or a later
   SP7 commit the session log names. Then the fast suite, once nothing runs beside it:
   `uv run pytest -q -m "not slow"` (the last count: 1881 passed, 47 deselected).
3. **When all three commands have finished** (a re-run under item 4 counts as its
   command): check each directory against the pre-registration's section 9 blocking
   checks (no `bug_suspect`; pads at P_ref within 0.002 kg; the pad control's consistency;
   the reproductions within 0.002 kg of the listed values; verifications within 1e-4 P_ref
   or flagged; `xv_dry_mass_delta_kg` equal to dm1 + dm2 within 1e-6 kg; the structure
   files' sha256 in each run's record; no unexplained `offload_nonmonotone`, capped refine
   or `structure_fixed_point_cap`). Then continue S7a:
   - **The run's commit** is 1b5f9d4, the commit the three commands started from. A
     re-run under item 4 starts from a commit that changes no code against it, so all
     three directories come from 1b5f9d4's code; each directory's git record names its own
     commit, and the findings note's Reproduction section lists them.
   - **The convergence check** of the pre-registration's section 1 runs after the three
     commands, never beside them, by a script under docs/findings/scripts/ that writes
     only to the session's scratch folder. Neither the script nor the folder exists yet,
     so the script needs a commit of its own before it runs. Section 1's "from the same
     commit" is read as "from the same code", the reading section 12 already gives the
     commands. The script's commit changes nothing in section 12's code list (src/,
     configs/, experiments/, pyproject.toml, uv.lock) and nothing in tests/. Check that
     before the script runs with `git diff --quiet 1b5f9d4 HEAD -- src configs experiments
     pyproject.toml uv.lock tests` (exit 0). The findings note's Reproduction section
     names the commit the check ran from and that check.
   - **The frozen sets** (tests/test_structure_search.py::test_frozen_sets_reproduce, both
     files) run at the run's commit, or at a later commit that passes the same `git diff
     --quiet` check.
   - **Then** the findings note docs/findings/RQ1-structural-2d.md (not yet written). Write
     its structural part now, in the headline form of design 4.11 with D-SP7-46's
     amendments, and put each command's start time and each directory's last file time in
     its Reproduction section. Then the honesty review; the independent gate; the step's
     commit with the S7a summaries (as SP1 step 9 committed its run summaries with the
     note, fd664a5); the tracker commit; push and the Pages check.
4. **If a command was interrupted** (item 1: `KeyboardInterrupt` in FAILED.txt, or neither
   file with no live process): its incomplete directory stays (never deleted or
   overwritten). Re-run that command from a clean commit that changes no code (src/,
   configs/, experiments/, pyproject.toml, uv.lock; pre-registration section 12), on a
   quiet machine. Log the interruption, the old directory and the new one in the session
   log. The findings note's Reproduction section names both.
5. **If a command raised** (item 1: FAILED.txt with any exception other than
   `KeyboardInterrupt`): re-run nothing. Such an exception is most likely a bug: unchanged
   code would raise again, and a fix changes code. Pre-registration section 12 lets S7a run
   only from a commit that changes no code, so a fixed re-run needs the user's logged
   decision or a pre-registration amendment (its own commit, a logged decision, the note
   extended, never rewritten).
   Stop and put it to the user (section 7): the traceback, the directory (kept, never
   deleted or overwritten), what the other two commands showed, and the options with a
   recommendation. For a bug: a fix through the step loop with its tests, then an
   amendment that names the commands to re-run. For an environmental cause (a full disk,
   say): a re-run with no code change, logged as a decision. A code change touches the code
   that all three commands ran on, so which commands re-run is part of that decision. Log
   the decision in TODO.md and the session log.
6. **Then the remaining steps, in order:** S4 (linear_motor core, KI-030, KI-021-KI-023),
   S4a (release at a target speed, the readers), S4b (the structural transform on
   linear-motor pushes), S5 (the sealed shaft), checkpoint 2 (the next in-progress handoff
   point), S6b (file B and the pre-registration addendum, committed before it runs), S7b
   (`run` B; the note completed; RQ1's pointer; README results; the findings index), S7c
   (program-level wording in code), S8 (the public face), C1 (documents, SP3's file
   fact-checked, the handoff, memory) and C2 (the independent exit gate, the full suite,
   the cold read, the closing commit, the push).

## 7. Decisions to put to the user first

None open when this file was written. Reserved for the user later by the plan:

- the cut order if room runs out (phase file section 7, "If room runs out"; put to the
  user when it happens): S5 and lm_fixed_sealed; S4a's target-speed release with
  lm_fixed_target. Compute-only cases and the CLAUDE.md arms are never cut. Three items of
  the planned order are spent: the payload cases and the thrust-structure row
  (silo_cold_s1_st_ts) are inside run A's command, and file C is run C, which finished at
  17:21:03Z. All three are pre-registered and already running or run. Leaving them out now
  would mean not reporting pre-registered results that exist, which is selective reporting
  (pre-registration section 9: "Every case must end ok, or no_offload with its shortfall
  and deficit, or be flagged");
- any exit criterion that misses at C2 (protocol section 6: open only with the user's
  explicit acceptance, logged as a decision);
- a step whose gate fails after its fix rounds (`[!]`, protocol section 4, item 4), and a
  blocking check of pre-registration section 9 that the session cannot explain or fix;
- an S7a command that raised (section 6, item 5): put to the user before any re-run;
- at the close, which phase runs next (SP3 in the planned order; protocol section 7,
  item 7).

Waiting on the user, not blocking: KI-026 (the social preview image, uploaded by hand) and
B-001 (results retention; deleting results needs the user's OK).

## 8. What must stay true

- **The freeze (D-SP7-31).** Tests never solve a pre-registered case; the structure files
  stay as frozen at S2's commit 45e39d4; a change to a structure file or to files A and C
  after cbbd7bc is a pre-registration amendment (its own commit, a logged decision, the
  note extended, never rewritten).
- **The structure files' sha256** (pinned in tests/test_config_planar.py; checked
  2026-10-16): configs/structures/generic_f9_class_2d.yaml
  a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232;
  configs/structures/generic_f9_class_2d_readme_loads.yaml
  a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997.
- **No validated number moves**: the pad 26,054.3962 kg and silo_cold 27,553.2271 kg within
  0.002 kg (tests/data/silo_screening_2d_record.json); SP1's headline with the structure
  off, 41,262.908 kg, and its three penalty rows within 0.002 kg
  (tests/data/silo_offload_2d_record.json); the constant-2 t cross-check within 0.002 kg of
  32,285.203 kg.
- **The replay template's sha256** (src/launchsim/templates/replay.html; checked
  2026-10-16): 1fa6eba6be18c5c2a8d10a3e42880ae556375dcf1508f6feb937aca641916990.
- **D-SP7-27**: no field is added to any dataclass the 1-D golden dump reaches;
  tests/test_golden_dump_fields.py pins their field lists.
- **The standing gates on every code step** (phase file section 7): fast suite green; ruff
  clean; the exact 1-D golden tier; the planar digest pin; the planar output capture; the
  golden-dump field lists; no shipped experiment or vehicle file changed (configs/vehicles/
  and the seven shipped experiment files, unchanged since a7c9f0a); replay.html's sha256;
  docs/physics.md holding the step's section and test-map rows. The full suite after S4,
  S4a, S4b and S5 and in C2.
- experiments/silo_offload_2d.yaml stays unchanged (the app's basis, D-SP7-29); the label
  `exploratory` stays reserved for app runs; no app run is cited in a finding.
- Nothing under results/ is written by hand, overwritten or deleted.
- The caveats travel with every structural number: a first-order station sizing, not a
  sized structure (D-SP7-01); SP1's penalty rows beside it; the gate vehicle's +14.3%
  calibration miss; sweep-optimized and unthrottled guidance; what nothing measures
  (pre-registration section 10).

## 9. How work is done, and the gotchas

How a step runs: protocol section 4 and the phase file's section 7 (who reviews what).
Steps run as multi-agent workflows: an implementer; the adversarial reviewers in parallel,
three passes; up to two fix rounds; an independent gate with its own scripts; the
orchestrator commits, then the tracker commit, the push and the Pages check
(`gh run list --workflow pages.yml --limit 1`). Gotchas learned in SP7 (the standing list is
protocol section 11):

- **Pass 3's majors get an extra round.** The loop leaves the third review pass's findings
  unfixed by design; a step whose third pass still has majors gets an extra round before
  its gate: one fixer over every pass-3 finding, verification reviewers, a clean-up of their
  residuals and a fresh independent gate (deviation 31; S0, S3b, S3a and S6a needed one).
- **A gate never ends its turn on a running command.** S3b's first gate launched the full
  suite in the background and ended on a status line, which the workflow took as its
  verdict (deviation 31). Gates run every command in the foreground, in chunks under ten
  minutes. Slow-tier groups and their wall times at S3b's second gate (2026-10-11, quiet
  machine): tests/test_structure_search.py 2 passed in 207.0 s;
  tests/test_structure_pipeline.py with tests/test_structure_reporting.py 3 in 145.0 s;
  test_convergence_2d, test_calibration, test_payload_search, test_offload, test_search and
  test_ltg 22 in 430.0 s; the rest of the slow tier 20 in 368.9 s (47 in 1,150.9 s).
  Under load (S3a's gate, 2026-10-15) the first group and the six-file group each passed ten
  minutes and were split into 13 smaller groups (3,424.9 s in all; one frozen-sets test
  alone 312-317 s). The fast suite in three chunks at S6a's gate: tests/test_[a-c]* 696 in
  143.5 s, [d-o] 394 in 63.9 s, [p-z] 791 in 221.5 s. (These group timings come from the
  gate reports in the session's scratch folder, which is temporary; the totals are in the
  session log.)
- **Workflows resume from their journal.** Usage limits (a weekly one in S3 on 2026-10-09;
  S3a's pass 2 and gate) and a network error (S3a's gate retry) stopped workflows; each
  resumed with `Workflow({scriptPath, resumeFromRunId})`, which replays the finished agents
  from the journal and reruns only the lost ones (SP2's handoff, archived, section 9;
  protocol section 11 for stopping orphaned processes first).
- **A gate's file list includes docs/physics.md.** S6a's G7 failed on a list that left out
  the file holding the step's test-map rows (deviation 39); every step's list names it.
- **Windows**: set PYTHONIOENCODING=utf-8 for scripts that print non-ASCII (the console is
  cp1252); PowerShell 5.1 has no `&&`; write long scripts to files rather than heredocs;
  normalise agent edits to LF before a commit (`git ls-files --eol`).
- **App runs** follow D-SP2-37 (protocol section 4, "App runs"): reviewers and gates use
  `--results-root <scratch>`; demo launches from a clean tree after the last code commit,
  their summaries in their own commit.
- **The pre-registered runs need a quiet machine**: no suite, app or agent that runs the
  code beside them; checkpoint 1's timing case measured the machine 1.8-2.3 times slower
  than SP1's production rates.

## 10. Prompt to resume SP7

Paste this into a fresh Claude Code session opened in this folder. It is the same text as
the "Resume" prompt in section 13 of docs/phases/SP7-structural-mass-push-load.md; if the
two ever differ, the phase file's version is the one to use.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP7-structural-mass-push-load.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links, then the inputs the phase file links:
> docs/phases/inputs/2026-10-08-SP7-design.md (the approved design),
> docs/phases/inputs/2026-10-08-SP7-sources.md (the source note) and
> docs/phases/inputs/2026-10-15-SP7-preregistration.md (files A and C; its sections 1, 7,
> 8, 9, 11 and 12 first).
>
> We are resuming phase SP7 of launch-assist-sim, in progress since 2026-10-08: the
> structural mass that the 4 g full-stack push needs, charged by a first-order station
> sizing model into SP1's offload solve with an uncertainty band beside SP1's penalty rows,
> and the drive realism that interacts with it (a force- and power-limited linear motor
> with carriage mass, braking functions, the sealed shaft). Resume SP7 from the step table
> in section 7 of the phase file; the session log in section 11 holds the resume point and
> section 12 the deviations. The step in hand is S7a: the three pre-registered commands
> (`run` and `sweep` of experiments/silo_structure_2d.yaml, `run` of
> experiments/silo_structure_2d_readme.yaml) were started together from the clean commit
> 1b5f9d4 on 2026-10-16 between 17:15:10 and 17:15:26 UTC.
>
> Follow the session protocol for a phase in progress: the checks of its section 10, then
> the start checklist of section 3 without the status change. Before any test suite, app or
> other heavy job, find out whether the S7a commands are still running; nothing heavy runs
> beside them (pre-registration sections 1 and 11). A finished directory has its top-level
> summary.md and no FAILED.txt. The code writes FAILED.txt for any exception, Ctrl+C
> included, so read its traceback. If it ends in KeyboardInterrupt, or a directory has
> neither file and no live command, the command was interrupted: keep its directory (no
> results directory is ever deleted or overwritten), re-run that command from a clean
> commit that changes no code (pre-registration section 12), and log the interruption in
> the session log. Any other exception means the command raised: re-run nothing and put it
> to me with the traceback and a recommendation, because a fix changes code and needs a
> logged decision or a pre-registration amendment first (handoff section 6, item 5). When
> all three have finished, check each against the pre-registration's section 9 blocking
> checks, then continue S7a: the convergence check of its section 1 (after the runs, never
> beside them, by a script whose own commit changes no code and nothing in tests/; handoff
> section 6, item 3), the frozen sets recomputed at the run's commit (1b5f9d4, or a later
> commit with the same code and tests), the structural part of
> docs/findings/RQ1-structural-2d.md with the honesty review, and the independent gate.
> Then S4, S4a, S4b, S5, checkpoint 2, S6b, S7b, S7c, S8, C1 and C2.
>
> Rules for the rest of the phase. The freeze D-SP7-31 holds: tests never solve a
> pre-registered case, the structure files stay as frozen at S2's commit, and a change to a
> structure file or to files A and C is a pre-registration amendment (its own commit, a
> logged decision, the note extended, never rewritten). Plan mode, and docs/physics.md in
> the same change, for anything touching the equations of motion, frames, events,
> integrator settings or loss accounting (the linear motor, the target-speed release and
> the sealed shaft do). Never choose a drive or structural parameter to make the assist
> look better; the registered estimates and published claims are comparisons, never
> targets. File B and its addendum are committed before it runs, from a clean commit. App
> runs follow D-SP2-37. Keep SP1's penalty rows beside the modelled number. Run every step
> through the loop: implementer; adversarial reviewers as section 7 of the phase file names
> them; up to two fix rounds, and an extra round before the gate when the third review pass
> still has majors (deviation 31); an independent gate that runs every command in the
> foreground, in chunks under ten minutes, and never ends its turn on a running command,
> with docs/physics.md in its file list (deviation 39); one commit per gate; the tracker
> commit at once; then `git push origin main` and the Pages check. The standing gates of
> section 7 hold on every code step. No validated number may move: the pad and silo_cold
> payload capacities (26,054.3962 and 27,553.2271 kg) and SP1's headline with the
> structural model off (41,262.908 kg). Close with the end checklist of the protocol's
> section 7 (steps C1 and C2). Report anything that undercuts the hypothesis, a modelled
> structure that cancels most of the offload included, as plainly as the rest.
