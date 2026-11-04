# Handoff: SP7 in progress (session 2026-10-08), at checkpoint 2

SP7 started 2026-10-08. If you are a new session and the phase file says in progress, resume
per SESSION_PROTOCOL.md section 10 from the step table.

## 1. Header

- **Phase in progress: SP7**, the structural mass of the push load and a force-limited drive
  (planar model), docs/phases/SP7-structural-mass-push-load.md, status line "in progress
  (session 2026-10-08)". Written 2026-11-03 at checkpoint 2 of the step table (an
  in-progress handoff point: the drive realism complete), following
  docs/process/SESSION_PROTOCOL.md section 10. Nothing is running and nothing is
  uncommitted apart from this handoff's documents.
- The last commit before this file is cc16ec0 (`SP7 step S5a: trackers (2bd40bd)`), pushed
  to origin/main. The last commit that changed src/ is 2bd40bd (step S5a).
- This file is part of the documents-only commit that follows cc16ec0, subject
  `SP7 in progress: handoff at checkpoint 2` (protocol section 10, item 6); a file cannot
  hold the hash of its own commit. That commit changes docs/ and TODO.md only.
- The checkpoint-1 handoff (written 2026-10-16 while S7a's commands ran, with dated updates
  to 2026-11-03 in its section 0) is archived as
  docs/handoff/archive/2026-10-16-SP7-checkpoint-1.md. SP1 closed 2026-10-04 (5007515); SP2
  closed 2026-10-07 (3a1b243).
- Authority (protocol section 10): `git log` and `git status`, then the step table (phase
  file section 7), then the session log (section 11). Section 4 below is a dated snapshot
  and loses against all three.

## 2. Read these first, in this order

1. This file.
2. docs/process/SESSION_PROTOCOL.md (sections 3, 4, 10 and 11 above all).
3. docs/phases/README.md (the program board).
4. docs/phases/SP7-structural-mass-push-load.md: the step table (section 7), the exit
   criteria (section 8), the session log (section 11), the deviations (section 12, items
   1-53) and the Resume prompt (section 13).
5. CLAUDE.md.
6. TODO.md. While reading it, list the open known issues and backlog items owned by SP7
   (section 4 below lists them as of this file).
7. README.md.
8. The memory index and the notes it links:
   C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md
9. The inputs the phase file links: docs/phases/inputs/2026-10-08-SP7-design.md (the
   approved design, version 2; section 4.10 is file B), docs/phases/inputs/2026-10-08-SP7-sources.md
   (section 10: the drive rules and their closed forms) and
   docs/phases/inputs/2026-10-15-SP7-preregistration.md (part 1, files A and C, with
   Amendment 1; S6b appends or links its part 2). The surveys
   (docs/phases/inputs/2026-10-08-SP7-survey/) as a step needs them.
10. The structural findings note as S7a left it: docs/findings/RQ1-structural-2d.md (draft
    of 2026-10-19; the linear-motor part is S7b's).

## 3. The request

No new research request in SP7. The phase is the user's own ordering (D-SP1-18, confirmed
by D-SP2-40): charge the structural mass that the 4 g full-stack push needs, with a
first-order sizing model validated against closed forms, so that SP1's headline (41.26 t
of stage-1 propellant, 10.04% of stage 1, before any structural mass) carries a modelled
structural cost with an uncertainty band beside the assumed penalty rows; re-open the
depth question; and build the drive realism that interacts with it (phase file, section 1).

The user's request to the session that resumed SP7 (2026-10-19), verbatim: "resume SP7
here, starting with S7a's open check. Then continue with the rest of the SP7, then SP3-SP6,
then rest of the readme phase 3, phase 5, phase 6, keep working till it is complete." That
session works on under it; each later phase still opens with its own Plan mode and the
user's approval of its design (protocol section 3).

The user's rules for the phase, quoted from the start prompt (phase file, section 13):

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

The user's answers during the phase (full text in TODO.md's decisions log): D-SP7-01 to
D-SP7-12 (the questions and follow-ups), the design approved with the plan (D-SP7-13 to
D-SP7-35), D-SP7-36, D-SP7-41, D-SP7-45 to D-SP7-47, and on 2026-10-19 D-SP7-48 ("Fix and
re-run sweep A": step S3c, Amendment 1, the sweep re-run). Every one was the recommended
option.

## 4. State when this file was written (snapshot, 2026-11-03)

**Step table** (phase file, section 7). Steps ran in the order 0, S1, S0, S2, S3, S3b, S3a,
checkpoint 1 with S6a, S7a with S3c, S4, S4a, S4b, S5, S5a.

| Step | What | Status | Commit (tracker commit) |
|---|---|---|---|
| 0 to S3a, checkpoint 1, S6a | the structure model, files A and C, the pre-registration (part 1) | [x] | to cbbd7bc (1b5f9d4) |
| S7a with S3c | `run` A, `sweep` A (re-run under Amendment 1), `run` C; the note's structural part | [x] | 6fa2ff0; S3c 1e4c732 and 77e1691 |
| S4 | the linear motor core | [x] | 25967be, merged 8c4b41a (52b6c6b) |
| S4a | target-speed release, the flown power cap, the readers, the shaft floor | [x] | 7cdc24a (8e4da84) |
| S4b | the structural transform on linear-motor pushes | [x] | b0fcc31 (e12e524) |
| S5 | the sealed shaft and the piston-work record | [x] | 460c4d6 (f120347) |
| S5a | the sealed shaft's wording at the sources and the readers | [x] | 2bd40bd (cc16ec0) |
| checkpoint 2 | this handoff | [x] | this commit |
| S6b | file B and the addendum (after this snapshot) | [x] | 331891d |
| S7b | `run` B and the note completed (after this snapshot) | [x] | e5f64b3 |
| S7c, S8, C1, C2 | the program-level wording, the public face, the close | [ ] | |

**S7a's result** (docs/findings/RQ1-structural-2d.md, draft of 2026-10-19): with the
central first-order structure charged, 11,420.2 kg of SP1's 41,262.9 kg stage-1 offload
survives on the gate vehicle (reading "cancels most"), with the physics band, the outer
envelope, the axis rows and the caveats the note gives. The directories:
results/silo_structure_2d/20261016T171513Z (run A), results/silo_structure_2d/20261019T172327Z
(sweep A re-run under Amendment 1; the first sweep 20261016T171522Z kept),
results/silo_structure_2d_readme/20261016T171529Z (run C). File B's cross-commit check
compares against A's silo_cold_s1_st, 11,420.246638573297 kg.

**Tests and lint at the last gates**: fast suite 2210 passed, 53 deselected (S5a's gate,
2026-11-03); the last full suite 2256 passed (S5's gate, 2026-10-25; S5a then added 4 fast
and 2 slow tests, its gate ran the touched readers' slow tests and 17 of the 53 slow tests);
ruff clean; the exact golden tier, the planar digest pin, the output capture and the
golden-dump field lists pass; templates/replay.html's sha256 unchanged; the gallery's six
pages regenerate byte-identical.

**Open items owned by SP7** (TODO.md): KI-041 (S8, the manual), KI-067 (S6b states it in
the addendum: a hot push's F_int taken at rest, an unconservative bias of up to 2.3%),
KI-082 (S7c or S8: the configs/display shaft note), KI-083 and KI-084 (S8, the manual);
B-004, B-005 and B-007 [~]. Every other KI opened in SP7 (KI-044 to KI-087) is low and owned
"later", or closed; S6b's addendum reads each against file B's settings.

**Decisions of the session**: D-SP7-01 to D-SP7-54 (TODO.md). Session-made under the
user's instruction to keep working, to report at SP7's close: D-SP7-49 (the push's event
set), D-SP7-50 (the force law's power cap on the flown, tapered force), D-SP7-51 (the shaft
floor after a release below the mouth), D-SP7-52 (a flown push's dynamic factor), D-SP7-53
(dm' measured about -4e-4 kg/kg on the cold force-law case) and D-SP7-54 (file B's sealed
bore 5.24 m, open to the user's change before S6b's registration commit). Deviations 1-53
are in the phase file's section 12.

**Working files outside the repository**: the briefs for S6b and S7c and the step-loop
workflow script are in
C:/Users/rahul/.claude/projects/D--DEV-ClaudeProjects-SpaceRocketOptimization/sp7work/
(s6b/BRIEF.md, s7c/BRIEF.md, step_loop.js; s5a/ holds S5a's reports). They are working
notes, not records: the phase file and the design are the authority, and a new session
may rewrite a brief from them.

## 5. Requirements and status

| # | Requirement | Status on 2026-11-03 |
|---|---|---|
| R1 | The interactive replay page as a CLI command | Done before SP1; structural and linear-motor caveats branched in S3a, S4a and S5a |
| R2 | An animated scene of the launch, 2-D first | Done in SP2; linear-motor and sealed-shaft labels in S4a and S5a |
| R3 | The same in a 3-D world | Not started: SP3-SP6, after SP7 |
| R4 | Configure the launch depth in the silo | Done in SP1; the depth sweep with the structure charged ran in S7a |
| R5 | Configure where the thrust ramp starts | Done in SP1 |
| R6 | Reduce the propellant at fixed payload and report the fraction replaced | SP1's answer re-judged in S7a (11.42 t of 41.26 t survives the central structure); the drive cases of file B pending (S6b, S7b) |
| R7 | Stay on the Falcon 9-class model | Standing; configs/vehicles/ unchanged since 22c62e9 |
| R8 | Lose nothing between sessions | This in-progress handoff, the session log and the step table |
| R9 | One fresh session per phase | SP7 has run in one session since 2026-10-08 (resumed 2026-10-19); this file is its resume point |
| R10 | Public repository pushed after every step | origin/main at cc16ec0 when this file was written |

**SP7's exit criteria** (phase file section 8; checked by the independent gate at C2):

| # | Criterion | Status so far |
|---|---|---|
| 1 | Validation first | The structural pieces and the drive pieces (S4 to S5a) each passed their closed-form tests before any registered experiment uses them; file B is not yet registered |
| 2 | Provenance and freeze | Holding: the structure files at their S2 sha256; configs/vehicles/ and the seven shipped experiment files unchanged since 22c62e9; files A and C unchanged since cbbd7bc |
| 3 | Nothing validated moved | Holding at every gate through S5a |
| 4 | The structural headline | Drafted in S7a; final at C2 |
| 5 | The frozen sets recomputed | Done at S6a and S7a; C2 pending |
| 6 | Convergence | S7a's check passed; the linear-motor x* is registered in S6b and run at S7b |
| 7 | Axes and drive | The sweeps ran in S7a; file B pending (S6b, S7b) |
| 8 | The findings note and the KI closures | The structural part drafted (S7a); the linear-motor part S7b; the wording S7c |
| 9 | docs/physics.md | Holding through S5a |
| 10 | Full suite, ruff, no new dependency | Pending (C2) |
| 11 | Demo | Pending (S8) |
| 12 | Close-out | Pending (S8, C1, C2) |

## 6. How to resume SP7

1. **Protocol checks** (section 10, then section 3 without the status change): the tree is
   clean; every `[x]` row's commit is in `git log`; HEAD's subject is
   `SP7 in progress: handoff at checkpoint 2`, or a later SP7 commit the session log names.
   Look for leftover processes from an earlier session by command line (protocol section
   11) and stop only those. Then the fast suite: `uv run pytest -q -m "not slow"` (the last
   count: 2210 passed, 53 deselected), in three chunks if the machine is loaded.
2. **S6b: file B and the pre-registration addendum.** Sources: design 4.10, sources section
   10, part 1 of the pre-registration, D-SP7-24 and D-SP7-49 to D-SP7-54, deviations 47-53.
   Build experiments/silo_drive_2d.yaml (the shared blocks and the pad of
   experiments/silo_offload_2d.yaml verbatim, silo_cold from file A verbatim, the nine
   linear-motor variants), the rule values from the closed forms by a committed script
   (docs/findings/scripts/sp7_drive_rules.py), the checks before registration (the file
   resolves and passes the preflight; no `drive_cap` or `power_limit` on the lm_cmd family at
   the stacks the solve visits; lm_fixed reaches v_e at L; the push table at the full load
   and at 41.26 t), the addendum (part 2) with the linear-motor convergence check
   registered, and the tests that list file B. No `run`, `sweep` or offload solve of any
   case of file B, and no coupled structural solve of any of its cases (D-SP7-31). If a
   rule cannot be applied as written, stop and report it rather than choosing a value.
   Commit file B and the addendum before any run.
3. **S7b**: `uv run python -m launchsim run experiments/silo_drive_2d.yaml`, with plots,
   from the clean registration commit, alone on a quiet machine (no suite, app or agent
   beside it; `git status --porcelain` empty apart from results/ before it starts). Then
   the registered convergence check (after the run, never beside it), the blocking checks
   of the addendum, the note completed (the linear-motor cases, RQ1's pointer, README
   results, the findings index, physics.md research notes, derived figures by a committed
   script), the honesty review, the gate.
4. **Then** S7c (the program-level wording: `git grep -n "no structural model exists"` only
   in dated or archived records), S8 (the public face: demo, gallery entry, deck and PDF,
   manual, landing page, CLAUDE.md, the protocol's caveat line), C1 (documents, SP3's file
   fact-checked against the code, the handoff, memory) and C2 (the independent exit gate,
   the full suite, the cold read, the closing commit, the push).

## 7. Decisions to put to the user first

None blocks the next step. To report, and open to the user's change:

- D-SP7-54: file B's sealed bore 5.24 m (the 5.2 m fairing plus the design's 0.04 m
  clearance), in place of the sources note's 3.7 m, which the fairing cannot pass. Open to
  the user's change until S6b's registration commit; after it, a change is an amendment.
- D-SP7-49 to D-SP7-53 (section 4): session-made, reported at the close.

Reserved for the user later by the plan:

- the cut order if room runs out (phase file section 7, "If room runs out"): S5 and
  lm_fixed_sealed; S4a's target-speed release with lm_fixed_target. Both are built; cutting
  a registered case after S6b would be selective reporting;
- any exit criterion that misses at C2 (protocol section 6: open only with the user's
  explicit acceptance, logged as a decision);
- a step whose gate fails after its fix rounds (`[!]`), and a blocking check of the
  addendum that the session cannot explain or fix;
- a `run` B that raises: re-run nothing, put it to the user (the checkpoint-1 handoff's
  section 6, item 5, gives the rule);
- at the close, which phase runs next: SP3 in the planned order and in the user's request
  of 2026-10-19; SP3 opens with Plan mode and the user's approval of its design.

Waiting on the user, not blocking: KI-026 (the social preview image, uploaded by hand) and
B-001 (results retention; deleting results needs the user's OK).

## 8. What must stay true

- **The freeze (D-SP7-31).** Tests never solve a pre-registered case; the structure files
  stay as frozen at S2's commit 45e39d4; files A and C stay as at cbbd7bc; file B, once
  registered, changes only by an amendment (its own commit, a logged decision, the note
  extended, never rewritten).
- **The structure files' sha256** (pinned in tests/test_config_planar.py):
  configs/structures/generic_f9_class_2d.yaml
  a0516875d3c3b64de32f8ed1ceeb1f71a6c67694f7b07306b242522dd3cc8232;
  configs/structures/generic_f9_class_2d_readme_loads.yaml
  a850de94ae24ab28941789d7a17da3c3ff5b48f51b762373fc99b6e22edc2997.
- **No validated number moves**: the pad 26,054.3962 kg and silo_cold 27,553.2271 kg within
  0.002 kg (tests/data/silo_screening_2d_record.json); SP1's headline with the structure
  off, 41,262.908 kg, and its three penalty rows within 0.002 kg
  (tests/data/silo_offload_2d_record.json); the constant-2 t cross-check within 0.002 kg of
  32,285.203 kg; S7a's silo_cold_s1_st, 11,420.246638573297 kg, reproduced by file B within
  0.002 kg.
- **The replay template's sha256** (src/launchsim/templates/replay.html):
  1fa6eba6be18c5c2a8d10a3e42880ae556375dcf1508f6feb937aca641916990.
- **D-SP7-27**: no field is added to any dataclass the 1-D golden dump reaches;
  tests/test_golden_dump_fields.py pins their field lists.
- **Vented and constant_accel bytes** (S5, S5a): tests/data/vented_pins.json and the
  digests in tests/test_sealed_shaft.py pin them; a sealed-shaft change moves none.
- **The standing gates on every code step** (phase file section 7): fast suite green; ruff
  clean; the exact 1-D golden tier; the planar digest pin; the planar output capture; the
  golden-dump field lists; no shipped experiment or vehicle file changed; replay.html's
  sha256; docs/physics.md holding the step's section and test-map rows. The full suite in
  C2 and after any physics-core change.
- experiments/silo_offload_2d.yaml stays unchanged (the app's basis); the label
  `exploratory` stays reserved for app runs; no app run is cited in a finding.
- Nothing under results/ is written by hand, overwritten or deleted.
- The caveats travel with every structural number: a first-order station sizing, not a
  sized structure (D-SP7-01); SP1's penalty rows beside it; the gate vehicle's +14.3%
  calibration miss; sweep-optimized and unthrottled guidance; what nothing measures
  (pre-registration part 1, section 10, and the addendum's list).

## 9. How work is done, and the gotchas

How a step runs: protocol section 4 and the phase file's section 7 (who reviews what).
Steps run as multi-agent workflows (sp7work/step_loop.js): an implementer; the adversarial
reviewers in parallel, three passes with a fix round after each; verification passes (up to
pass 6) while majors remain; an independent gate with its own scripts; the orchestrator
commits, then the tracker commit, the push and the Pages check
(`gh run list --workflow pages.yml --limit 2`). Gotchas learned in SP7 (the standing list is
protocol section 11):

- **Pass 3's majors get more rounds** before the gate (deviation 31); the loop now runs
  verification passes until no major remains or pass 6 is reached, and the gate checks any
  that remain directly.
- **A gate never ends its turn on a running command.** Gates run every command in the
  foreground, in chunks under ten minutes (the fast suite in three chunks: tests/test_[a-c]*,
  [d-o]*, [p-z]*; the slow tier in groups, the frozen-sets tests one per command).
- **Workflows resume from their journal.** Usage limits (S4a, S5a), a weekly limit and a
  network error (S4b's gate) stopped workflows; each resumed with
  `Workflow({scriptPath, resumeFromRunId, args})` and the same args, which replays the
  finished agents and reruns only the lost ones. Stop orphaned processes first (protocol
  section 11).
- **Keep working files out of %TEMP%.** A temp-folder cleanup on 2026-11-02 deleted the
  session's scratch files (briefs, reports, tracker scripts) while a workflow was paused;
  the journals under ~/.claude/projects/ survived (deviation 53). Briefs, scripts and
  reports go in sp7work/.
- **A gate's file list includes docs/physics.md** (deviation 39).
- **Windows**: set PYTHONIOENCODING=utf-8 for scripts that print non-ASCII (the console is
  cp1252); PowerShell 5.1 has no `&&`; write long scripts to files rather than heredocs;
  normalise agent edits to LF before a commit (`git ls-files --eol`).
- **App runs** follow D-SP2-37: reviewers and gates use `--results-root <scratch>`; demo
  launches from a clean tree after the last code commit, their summaries in their own
  commit.
- **The pre-registered runs need a quiet machine**: no suite, app or agent that runs the
  code beside them; at checkpoint 1 the machine ran 1.8-2.3 times slower than SP1's
  production rates.

## 10. Prompt to resume SP7

Paste this into a fresh Claude Code session opened in this folder. It is the same text as
the "Resume" prompt in section 13 of docs/phases/SP7-structural-mass-push-load.md; if the
two ever differ, the phase file's version is the one to use.

> Read docs/handoff/NEXT_SESSION.md first, then docs/process/SESSION_PROTOCOL.md,
> docs/phases/README.md, docs/phases/SP7-structural-mass-push-load.md, CLAUDE.md, TODO.md,
> README.md, and the memory index
> (C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\MEMORY.md)
> with the notes it links, then the inputs the phase file links:
> docs/phases/inputs/2026-10-08-SP7-design.md (the approved design; section 4.10 is file B),
> docs/phases/inputs/2026-10-08-SP7-sources.md (section 10: the drive rules) and
> docs/phases/inputs/2026-10-15-SP7-preregistration.md (part 1 and Amendment 1), and the
> draft note docs/findings/RQ1-structural-2d.md.
>
> We are resuming phase SP7 of launch-assist-sim, in progress since 2026-10-08: the
> structural mass that the 4 g full-stack push needs, charged by a first-order station
> sizing model into SP1's offload solve with an uncertainty band beside SP1's penalty rows,
> and the drive realism that interacts with it (a force- and power-limited linear motor
> with carriage mass, braking functions, the sealed shaft). Resume SP7 from the step table
> in section 7 of the phase file; the session log in section 11 holds the resume point and
> section 12 the deviations. Steps to S5a and checkpoint 2 are done; nothing is running.
> The next step is S6b: file B (experiments/silo_drive_2d.yaml) and the pre-registration
> addendum, built and committed before any run of file B (D-SP7-31: no run, sweep, offload
> solve or coupled structural solve of any of its cases until then). D-SP7-54 (the sealed
> bore of 5.24 m) is open to my change until that commit.
>
> Follow the session protocol for a phase in progress: the checks of its section 10, then
> the start checklist of section 3 without the status change. Then S6b; S7b (`run` B from
> the clean registration commit, alone on a quiet machine, then the registered convergence
> check, never beside it, and the note completed); S7c; S8; C1 and C2.
>
> Rules for the rest of the phase. The freeze D-SP7-31 holds: tests never solve a
> pre-registered case, the structure files stay as frozen at S2's commit, and a change to a
> structure file or to files A, B and C after their registration is a pre-registration
> amendment (its own commit, a logged decision, the note extended, never rewritten). Plan
> mode, and docs/physics.md in the same change, for anything touching the equations of
> motion, frames, events, integrator settings or loss accounting. Never choose a drive or
> structural parameter to make the assist look better: every value of file B comes from a
> rule fixed in the design or the sources note, and if a rule cannot be applied as written,
> stop and report it. The registered estimates and published claims are comparisons, never
> targets. App runs follow D-SP2-37. Keep SP1's penalty rows beside the modelled number.
> Run every step through the loop: implementer; adversarial reviewers as section 7 of the
> phase file names them; fix rounds and verification passes while majors remain
> (deviation 31); an independent gate that runs every command in the foreground, in chunks
> under ten minutes, and never ends its turn on a running command, with docs/physics.md in
> its file list (deviation 39); one commit per gate; the tracker commit at once; then
> `git push origin main` and the Pages check. The standing gates of section 7 hold on every
> code step. No validated number may move: the pad and silo_cold payload capacities
> (26,054.3962 and 27,553.2271 kg) and SP1's headline with the structural model off
> (41,262.908 kg). Close with the end checklist of the protocol's section 7 (steps C1 and
> C2). Report anything that undercuts the hypothesis, a modelled structure that cancels
> most of the offload included, as plainly as the rest.
