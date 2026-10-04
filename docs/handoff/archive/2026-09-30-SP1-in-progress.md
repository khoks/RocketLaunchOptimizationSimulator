Archived 2026-10-04: SP1 closed; the live handoff is docs/handoff/NEXT_SESSION.md.

# Handoff: Phase SP1 in progress (session 2026-09-30)

**Phase SP1 in progress (session 2026-09-30).** Written 2026-09-30 during SP1 step T and
committed with step T's documents: the first commit after 2eebcae (the oldest entry of
`git log --oneline 2eebcae..HEAD`). 2eebcae is the last commit that changed code; up to
the commit that contains this file, steps 1 to 10 have not started. For anything later,
the step table of the phase file and `git log` are the authority, not this file
(SESSION_PROTOCOL.md, section 10).

This is the live handoff. It exists so that a fresh session can resume SP1 if the
2026-09-30 session ends before SP1 closes. **When SP1 closes (step 10), the end-of-phase
handoff for SP2 replaces this file**, and this version moves to docs/handoff/archive/.

SP1 is: the work-tracking system; the launch settings (silo depth with exit speed; the
thrust-ramp start by time, depth, speed and height); the fuel-offload solver; and the
headline finding on the planar model (how much rocket propellant a silo push replaces at a
fixed payload and orbit on the Falcon 9-class gate vehicle).

## 1. Read these first, in this order

1. This file.
2. docs/process/SESSION_PROTOCOL.md: how every session runs (start checklist, step loop,
   end checklist, ID conventions, what to do when a session ends early).
3. docs/phases/README.md: the program board (phases SP1 to SP6 and "later", status,
   dependency order, the input files).
4. docs/phases/SP1-fuel-offload-planar.md: the phase file. Its step table (section 7) is
   the record of what is done; its session log (section 11) says what happened last.
5. CLAUDE.md: build rules, commands, conventions, the validation list.
6. TODO.md: program-level tracker (milestones, priorities, backlog B-nnn, decisions log
   D-..., known issues KI-nnn, findings so far).
7. README.md: research brief, first-order numbers, results so far, roadmap.
8. The memory index and the notes it links:
   C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md

Reference material for SP1 (read the parts the step in hand needs):

- docs/phases/inputs/2026-09-30-SP1-approved-plan.md: the plan the user approved on
  2026-09-30. It is the source of truth for scope, steps, gates and exit criteria.
- docs/phases/inputs/2026-09-30-design-settings-and-offload.md: the SP1 design in full.
- docs/phases/inputs/2026-09-30-survey-config-search-compare.md and
  docs/phases/inputs/2026-09-30-survey-ignition-assist-physics.md: code surveys with file
  and line references, checked at commit 2eebcae.
- docs/physics.md: the equations. A change to events or physics updates it in the same
  change (CLAUDE.md).

## 2. The request

The user's original request and the headline research question, in their own words, are in
section 1 of the archived handoff, docs/handoff/archive/2026-09-30-phases-0-2.md. Read it;
it is not repeated here.

In the 2026-09-30 planning session the user answered the decision questions in Plan mode.
The answers are recorded as decisions, not as quotes (TODO.md, decisions log, D-SP1-01 to
D-SP1-08). Two of them go beyond what the archived handoff recommended: 3-D means true 3-D
dynamics up to 6-DOF (D-SP1-01), and the visual tool is a local app (D-SP1-02).

The one new request of the session is the way of working (D-SP1-08). The user asked for
the work to be divided so that each big, self-contained, demonstrable phase runs in its
own fresh Claude session; each session tests, refines and completes its phase and prepares
the next one's documents, memory and context, ending with a detailed prompt to paste. The
full wording was not saved to the repository. Two phrases of the user's own survive, as
recorded in the memory note session-per-phase-workflow.md: the prompt for the next session
is to be prepared "just like it was done for this session by the first session", and work
tracking "has to mature a lot" for this. The approved plan's "Context" paragraph states the
same request in the plan's words.

## 3. State when this file was written

This section is a snapshot of the commit that contains this file. It is true at that
commit and is not updated afterwards.

- The SP1 plan was approved by the user on 2026-09-30 in Plan mode. Decisions D-SP1-01 to
  D-SP1-13 are in TODO.md's decisions log.
- Step T (tracking system) is what that commit holds: the session protocol, the program
  board, the phase files SP1 to SP6, the six input files under docs/phases/inputs/, the
  TODO.md restructure with ids, the status lines in CLAUDE.md and README.md, this handoff
  and the archive of the previous one. The memory notes were updated in the same step
  (they live outside the repository).
- No code has changed. Nothing under src/, tests/, experiments/, configs/ or results/ has
  been touched in SP1 up to that commit. Steps 1 to 10 have not started.
- The commit changes only docs/, TODO.md, CLAUDE.md and README.md
  (`git diff --stat 2eebcae <that commit>` shows it). If the step table still shows step T
  as [~], only its tracker row is outstanding: mark it [x] with the commit hash and commit
  that (section 5, item 2).
- Tests at 2eebcae: 928 fast plus 23 slow, ruff clean, and the golden 1-D test pins every
  1-D output (from the archived handoff, section 7). The SP1 session log records a clean
  tree and a green fast suite at the start of the session.
- Key results directories (unchanged since the archived handoff, section 7):
  results/calibration_f9_2d/20260930T173928Z, results/silo_screening_2d/20260930T175743Z
  (run) and 20260930T182453Z (sweeps), results/guidance_trigger_2d/20260930T174950Z,
  results/silo_bridge_2d_readme/20260930T185034Z.
- Nothing is finished yet in SP1, so there is no result to report. The headline number does
  not exist. The only figure is the probe's: about 10% of stage-1 propellant (41.1 t, 7.9%
  of the total load) on the 3 g / 100 m cold-start silo. It is a probe, not a finding; it
  is a sanity check for the solved value, not a target.

## 4. Requirements and status

R1 to R8 are the requirements of the archived handoff (its section 2); R9 is new.

| # | Requirement | Status on 2026-09-30 |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done before SP1 (`launchsim replay`) |
| R2 | An animated scene of the launch itself, 2-D first | Not started. Phase SP2, inside the local app (D-SP1-02) |
| R3 | The same in a 3-D world | Not started. True 3-D dynamics in SP3, SP5 and SP6; the 3-D scene in SP4 (D-SP1-01) |
| R4 | Configure the launch depth in the silo | Not started. SP1 step 2 (D-SP1-05) |
| R5 | Configure where the thrust ramp-up starts | Not started. SP1 steps 3 and 4 (D-SP1-06) |
| R6 | Reduce the rocket's propellant at fixed payload and report the fraction replaced (the headline question) | Not started; probe only. SP1 steps 5 to 9 (D-SP1-03, D-SP1-04, D-SP1-09, D-SP1-10, D-SP1-13) |
| R7 | Stay on the Falcon 9-class model | Standing: configs/vehicles/generic_f9_class_2d.yaml, never edited |
| R8 | Lose nothing between sessions | Built in step T (the commit that contains this file): protocol, board, phase files, trackers, this file, memory |
| R9 | One fresh session per phase; each phase tested, refined and completed before the next; the previous session prepares the next one's documents, memory and prompt | Set up in step T (D-SP1-08); first exercised when SP1 closes |

## 5. How to resume SP1 if the session ended early

1. Open docs/phases/SP1-fuel-offload-planar.md. In the step table (section 7), find the
   first step not marked [x]. A step marked [~] was in hand; the session log (section 11)
   says what was done inside it and what is outstanding. Section 12 lists deviations.
2. Check the tree against the table:
   - `git -C "D:\DEV\ClaudeProjects\SpaceRocketOptimization" log --oneline -15`
   - `git -C "D:\DEV\ClaudeProjects\SpaceRocketOptimization" status --short`
   Every step marked [x] should have a commit. What a dirty tree means:
   - only docs/phases/SP1-fuel-offload-planar.md and TODO.md are modified: the stop was at
     a step boundary (the step was committed, its tracker rows were not). Check the rows
     against `git log`, commit them (`SP1 step <k>: trackers (<hash>)`) and continue;
   - anything else is uncommitted: the session stopped inside a step. Read the diff, then
     either finish that step or ask the user before discarding anything. Do not discard
     work without asking.
3. If step T itself is not committed: check that these exist and are complete, finish what
   is missing, run the compliance review, then commit. Files:
   docs/process/SESSION_PROTOCOL.md, docs/phases/README.md,
   docs/phases/SP1-fuel-offload-planar.md, docs/phases/SP2-launch-app-2d-scene.md,
   docs/phases/SP3-3d-dynamics-s1-sphere.md, docs/phases/SP4-3d-scene-and-recheck.md,
   docs/phases/SP5-3d-dynamics-s2-oblate.md, docs/phases/SP6-3d-dynamics-s3-6dof.md,
   docs/phases/inputs/ (six files: the approved plan, two designs, three code surveys),
   TODO.md, CLAUDE.md, README.md, this file,
   docs/handoff/archive/2026-09-30-phases-0-2.md, and the memory directory.
4. Run the fast suite and ruff before changing anything:
   - `uv run pytest -q -m "not slow"`
   - `uv run ruff check .`
   If either fails on a clean tree, stop and report it; do not build on a red suite.
5. Continue the step loop from the first open step, as SESSION_PROTOCOL.md section 4
   describes it: implementer; adversarial reviewers (a physics or numerics skeptic and a
   CLAUDE.md compliance auditor; an honesty auditor for findings); up to two fix rounds; an
   independent gate; commit; update the step table, the session log and TODO.md, and
   commit that tracker update at once, so the tree is clean before the next step.
6. Standing gate on every code step: fast suite green, ruff clean, golden 1-D
   byte-identical. Run the full suite (`uv run pytest -q`) after the physics-core steps
   (4, 5 and 6) and before closing the phase.
7. Steps 8 and 9 are pre-registered: the experiment files are committed before any run,
   and the run and the sweeps start from a clean committed tree.
8. Step 10 closes SP1 (SESSION_PROTOCOL.md, section 7): the exit criteria are checked by an
   independent gate, the demo is recorded under docs/demos/SP1/, the close-out question of
   section 6 is put to the user and the next phase confirmed, that phase's file (SP2 in the
   planned order) is fact-checked against the code as it then is, this file is replaced by
   the handoff for it, memory and status lines are updated, a cold-read check is run, and
   the final commit is made.

## 6. Decisions to put to the user first

None before resuming. One is due at SP1's close-out (SP1 phase file, section 10): whether
to move the structural-mass model (README Phase 3; TODO.md backlog B-004) ahead of the 3-D
work. A step whose gate cannot be met, or an exit criterion that stays open, also goes to
the user (SESSION_PROTOCOL.md, section 6).

## 7. What must stay true (short list; the rules are in CLAUDE.md)

- Never edit configs/vehicles/generic_f9_class_2d.yaml or any shipped experiment file. No
  pre-registered block or budget id changes in SP1 (D-SP1-09).
- Regression guards: the golden 1-D tests; the planar digest pin of step 1; pad and
  silo_cold payload capacities reproduce the recorded values within 0.002 kg. The recorded
  values are 26,054.3962 kg for the pad (tests/data/calibration_record.json,
  `amended_rerun` block) and 27,553.2271 kg for silo_cold (metrics.json of
  results/silo_screening_2d/20260930T175743Z, git 7ad381f; that file is not tracked, so
  SP1 step 1 pins the value in a test). The one-decimal figures 26,054.4 and 27,553.2 kg
  are 0.004 and 0.027 kg away and are not the reference.
- Caveats travel with the headline: calibration +14.3%; sweep-optimized and unthrottled
  guidance; no structural mass for the 4 g push (about 8.1 t of stage-1 strengthening would
  cancel the payload gain, and would cut the offload too); prescribed-acceleration drive
  with a massless carriage and no shaft drag; the offloaded run's max-Q can exceed the
  pad's (38.4 against 37.2 kPa in the probe); tanks partly filled with dry mass unchanged.
- Stage 1 is the only headline. Stage-2 and both-stage offloads are reported net of the pad
  control and may be small or ill-conditioned (D-SP1-10).
- Never tune toward the probe's figure or any published claim. A result that undercuts the
  hypothesis is reported as plainly as one that supports it.

## 8. How work is done, and the gotchas

- How work is done: docs/process/SESSION_PROTOCOL.md (sections 3 to 7).
- Gotchas that apply to every session: SESSION_PROTOCOL.md section 11. The archived
  handoff's section 9 is the original list (long heredocs fail in the Bash tool, `cd`
  persists, PowerShell 5.1 has no `&&`, the cp1252 console, NaN in JSON, the charset of a
  standalone HTML page, the browser pane and local files, `filterwarnings=error`, machine
  speed and run times, which results files are tracked).
- The archived handoff also holds the fact-checked inventory of what existed at 2eebcae
  (its section 4) and the probe table with its caveats (its section 3). Its sections 5 and
  6 (decisions to ask, the proposed plan V0 to V4) are superseded by the approved plan and
  the phase files.
- New in this session, and now in SESSION_PROTOCOL.md section 11 (TODO.md KI-020): the
  output files of background subagents were 0 bytes, so a subagent's report exists only in
  its notification text and must be saved to a repository file at once
  (docs/phases/inputs/ for designs and surveys); and background Explore agents took from
  10 minutes to 2.5 hours of wall clock, so ask the user the open questions while they run.

## 9. Prompt to resume SP1

Paste this into a fresh Claude Code session opened in this folder. It is the same text as
the "Resume SP1" prompt in section 13 of docs/phases/SP1-fuel-offload-planar.md; if the two
ever differ, the phase file's version is the one to use.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP1-fuel-offload-planar.md, CLAUDE.md, TODO.md,
> README.md, the memory index, and the inputs the phase file links. We are resuming phase
> SP1 of launch-assist-sim: launch settings (silo depth with exit speed, thrust-ramp start
> by depth, speed and height) and the fuel offload at fixed payload on the planar model,
> ending in the findings note docs/findings/RQ1-fuel-offload-2d.md. The step table in
> section 7 of the SP1 phase file shows which steps are done and where the last session
> stopped; the session log in section 11 and any deviations in section 12 say why. Follow
> the session protocol: confirm a clean tree and a green fast suite, re-check the file:line
> inventory in section 6 for the remaining steps against the code as it is now, then show
> me in Plan mode the remaining steps (confirmed or refined) before writing any code. Keep
> the per-step loop (implementer, adversarial reviewers, up to two fix rounds, independent
> gate, commit, tracker update committed at once), run the full suite after steps 4, 5 and
> 6 and before closing, and commit the experiment files before any run. Do not edit shipped
> experiment or vehicle files, and do not start SP2: SP1 ends with its seven exit criteria
> checked, the demo recorded under docs/demos/SP1/, the close-out question put to me, and
> the handoff and prompt for the next phase written. Report results that undercut the
> hypothesis as plainly as the others.
