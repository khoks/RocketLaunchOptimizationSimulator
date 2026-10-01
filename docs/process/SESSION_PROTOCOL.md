# Session protocol

How every Claude Code session on launch-assist-sim runs. Adopted 2026-09-30 (decision
D-SP1-08, approved plan in docs/phases/inputs/2026-09-30-SP1-approved-plan.md). CLAUDE.md
"Working rules" points here. Where this file and CLAUDE.md disagree, CLAUDE.md wins and
this file gets fixed.

## 1. Purpose

The program is split into phases (SP1, SP2, ...; the board is docs/phases/README.md). Each
phase is done by one fresh Claude Code session. A phase is tested, refined and completed
before the next one starts, and it ends with something the user can run or look at.

Why one session per phase:

- A session's context is finite. A phase sized to fit one session finishes with its
  reviews and gates done, instead of running out of room part-way through.
- A fresh session knows nothing the previous one did not write down. Making the documents
  carry everything forces designs, decisions and results onto disk, where the user and
  later sessions can check them.
- The user sees a working result at every boundary and can reorder, stop or redirect the
  program there (for example, move the structural-mass model earlier).

The cost is the handover. The previous session prepares the next session's phase file,
handoff, memory and prompt, and that work is part of the phase, not an extra.

## 2. The documents and what each is for

| Document | Role | Who updates it, and when |
|---|---|---|
| `docs/handoff/NEXT_SESSION.md` | Entry point for the next session: what was finished, the state of the tree, key results directories, which phase file to open, gotchas, the prompt to paste. Read first | Rewritten at every session end; the previous one moves to `docs/handoff/archive/<date>-<phase>.md` (naming rule in section 7, item 9) |
| `docs/phases/README.md` | Program board: every phase's goal, what can be seen at its end, status, session date, closing commit, link to its phase file; a one-line summary of each phase's entry and exit criteria (the full text is in the phase file, sections 4 and 8); dependency order | At session start (status "in progress") and session end (status "done", commit) |
| `docs/phases/SP<n>-<slug>.md` | One per phase. The starting document and the live record: goal, scope, decisions, entry criteria, design, fact-checked code inventory, step table with gates, exit criteria, demo script, risks, session log, deviations, the prompt that starts the phase | Written by an earlier session; fact-checked by the session before it; kept current during its own session (step rows, session log, deviations) |
| `docs/phases/inputs/` | Dated source material a phase file was written from: the approved plan, designs, code surveys. Each states the commit its line numbers were checked at | Added to when a planning pass produces a new design or survey; existing files are not edited (they are a record) |
| `TODO.md` | Program-level tracker: milestones, current phase, priorities, backlog (B-nnn), decisions log (D-...), known issues (KI-nnn), findings index. The Phase 0-2 step tables stay as history; step tables of SP phases live in the phase files | When a step's gate passes and at session end |
| `CLAUDE.md` | Project rules, commands, layout, conventions, the one-line project status | Status line when a phase closes; commands and layout when the code changes them |
| `README.md` | Background, prior art, first-order numbers, research questions, results so far, roadmap | Results and status when a phase produces findings or closes |
| `docs/physics.md` | Equations and assumptions; the source of truth for the math | In the same change as any edit to equations of motion, frames, events, integrator settings or loss accounting |
| `docs/findings/` | One write-up per research question, next to the plots it rests on; `README.md` indexes them; `probes/` holds labelled probes that are not shipped runs | When an experiment produces a finding; each note passes an honesty review before it is committed |
| `docs/demos/SP<n>/` | The recorded demo of each finished phase: command output, screenshots, a short README saying what was run at which commit | At session end, before the phase is closed |
| Memory directory (`C:\Users\rahul\.claude\projects\D--DEV-ClaudeProjects-SpaceRocketOptimization\memory\`, index `MEMORY.md`) | Short notes that load into every session: project status and which file to open, user profile, way of working, toolchain quirks. Pointers, not content: the detail lives in the repository | At session end (project status always; the others when something new was learned) |

Nothing under `results/` is edited by hand or deleted. Only each run's top-level
`summary.md` is tracked in git.

## 3. Session start checklist

1. Read, in this order: `docs/handoff/NEXT_SESSION.md`; this file; the program board
   (`docs/phases/README.md`); the phase file the handoff names
   (`docs/phases/SP<n>-<slug>.md`); `CLAUDE.md`; `TODO.md`; `README.md`; the memory index
   (`MEMORY.md`) and the notes it links; then the files in `docs/phases/inputs/` that the
   phase file's design section links. Every handoff and every section 13 prompt gives
   this same order. While reading `TODO.md`, list the open known issues (KI) and backlog
   items (B) whose owner or target is this phase: each needs a step or a scope line in
   the phase file, or is re-owned in Plan mode (item 6).
2. Check the entry criteria in section 4 of the phase file. If one fails, stop and tell
   the user; do not start the phase on a broken base.
3. Confirm a clean tree and the expected commits. The handoff cannot contain the hash of
   the commit it is part of, so HEAD is identified by its subject and the closing commit
   by its hash:
   - `git status` shows nothing to commit;
   - `git log -1 --format=%s` is the bookkeeping subject the handoff names
     (`Close SP<n>: trackers, handoff, next phase file`; section 7, item 12);
   - the closing commit the handoff names by hash exists (`git cat-file -e <hash>`) and is
     an ancestor of HEAD;
   - `git diff --stat <hash> HEAD` touches only `docs/`, `TODO.md`, `CLAUDE.md`,
     `README.md` and `.gitignore` (bookkeeping files; no code, tests, configs,
     experiments or results).

   If any of these fails, find out why before touching anything. If the phase file says
   "in progress", the checks are those of section 10 instead (every `[x]` row has its
   commit in `git log`; the tree is clean or holds only tracker edits).
4. Confirm a green fast suite: `uv run pytest -q -m "not slow"`. Record the test count in
   the phase file's session log.
5. Re-check the phase file's inventory (section 6) against the code if the handoff or the
   phase file flags drift, or if the inventory's stated commit is not the current HEAD.
   Correct line numbers and function names in the phase file before planning from them.
6. Enter Plan mode. Confirm or refine the phase's steps and gates against the code as it
   is. Put every open decision (phase file section 10, items marked as needing the user)
   to the user, with the recommendation first and the trade-off in one line. Show the
   plan before writing code.
7. After the user approves: log new decisions in `TODO.md` (D-SP<n>-nn) and cite them in
   the phase file; save any new design or survey under `docs/phases/inputs/`; record
   changes to the step table under "Deviations from the plan" if they differ from what
   the previous session wrote.
8. Mark the phase "in progress (session <date>)" in three places: the phase file's status
   line, the program board (`docs/phases/README.md`) and `TODO.md`. Add one line to the
   header of `docs/handoff/NEXT_SESSION.md`: "SP<n> started <date>. If you are a new
   session and the phase file says in progress, resume per SESSION_PROTOCOL.md section 10
   from the step table." Commit these together (with the corrections of item 5 and the
   decisions of item 7), subject `Start SP<n>: status in progress`, so the tree is clean
   before the first step.

If the session is already in Plan mode when it starts (README, "Working with Claude on
this", starts each phase there), items 4 and 5 cannot run tests or edit files. Do the
read-only checks (git status and log, grep the inventory), list the inventory corrections
in the plan, and run the fast suite and write the corrections as the first actions after
the plan is approved.

## 4. The step loop

Each row of the phase file's step table goes through the same loop.

1. **Implementer.** Builds the step: code, tests, and the documentation that must change
   with it (`docs/physics.md` in the same change for anything touching equations of
   motion, frames, events, integrator settings or loss accounting).
2. **Adversarial reviewers**, independent of the implementer, chosen by what the step
   produces:
   - code: a physics or numerics skeptic, and a CLAUDE.md compliance auditor;
   - findings and summaries: an honesty auditor (every number traced to a run, caveats
     beside the headline, results that undercut the hypothesis stated as plainly as the
     ones that support it, nothing tuned toward a target);
   - anything drawn (plots, pages, scenes, the app): a visual-QA reviewer who checks the
     picture against the run data.
3. **Fix rounds.** Up to two. A finding that is not fixed is either rejected with a
   written reason or logged as a known issue (KI-nnn) in `TODO.md`.
4. **Independent gate.** An agent that did not implement or review the step checks the
   step's gate criterion from the step table, plus the standing gates below. If the gate
   fails after the fix rounds, mark the step `[!]` and ask the user.
5. **Commit.** One commit per passed gate (the user expects it).
6. **Tracker update, committed at once.** Set the step row in the phase file (status,
   commit hash); add one line to the phase file's session log (step, commit, next step),
   so the resume point is always on disk; update `TODO.md` (milestones, decisions, known
   issues, backlog, findings as they apply). A commit cannot contain its own hash, so
   these edits are their own small commit, made immediately, subject
   `SP<n> step <k>: trackers (<hash>)`. The tree is then clean between steps and before
   any pre-registered run.

Standing gates on every code step:

- the fast suite is green: `uv run pytest -q -m "not slow"`;
- ruff is clean: `uv run ruff check .` reports nothing and `uv run ruff format .` changes
  nothing;
- the golden 1-D outputs are byte-identical (`tests/test_golden_1d.py`), plus any other
  regression pin the phase file names for the program (SP1 step 1 adds a digest pin of the
  shipped planar experiments);
- after any physics-core change, the full suite: `uv run pytest -q`.

Rules for runs that produce findings:

- Experiment files are committed before they are run (pre-registration). A change to a
  committed experiment is a pre-registration amendment: its own commit, logged as a
  decision, with the earlier record kept.
- The run starts from a clean committed tree (the previous step's tracker commit
  included), so the results directory records a git hash that reproduces it and no dirty
  flag.
- Results directories are never overwritten or deleted.
- A `bug_suspect` flag blocks the finding until it is explained or fixed.
- Never tune a parameter to make an assist look better. Published claims and probe
  numbers are things to compare against, not targets.

Steps may run as multi-agent workflows. A workflow that loses agents (for example an
expired login) can be resumed from its run id and replays cached steps.

## 5. Scope

- A phase does only what section 2 of its phase file puts in scope.
- A new idea, an improvement outside the step, or a nice-to-have goes to the backlog in
  `TODO.md` as B-nnn with a priority (P0-P3) and a target phase. It is not built now.
- A defect found in passing that the phase does not need to fix goes to known issues as
  KI-nnn with a severity and an owner phase.
- Anything that expands scope is asked of the user first: CLAUDE.md lists 6-DOF, 3-D
  Earth, structural FEM, deleting results and replacing a validated model; the same
  applies to adding a step, a dependency or a deliverable the phase file does not have.
  The answer is logged as a decision.
- Dropping or shrinking a step is also a deviation: record it in section 12 of the phase
  file and, if an exit criterion is affected, follow section 6 below.
- Validated code keeps its behaviour unless the phase says otherwise: calibrated vehicle
  files are copied, not edited; baseline settings do not change without re-running every
  variant compared against them.

## 6. Definition of done for a phase

A phase is done when every exit criterion in section 8 of its phase file has been checked
by an independent gate (an agent that did not do the work) and passes.

A criterion may be left open only with the user's explicit acceptance. The acceptance is
logged as a decision (D-SP<n>-nn) that says what was missed and by how much, and the miss
is stated on the program board and in the handoff. The Phase 2 calibration (+14.3%,
accepted 2026-09-30) is the model: reported, stopped, asked, logged.

"Done" does not mean the hypothesis was confirmed. A phase whose result undercuts the
idea that the assist helps is done when that result is measured, explained and written up.

## 7. Session end checklist

1. Exit criteria gate: an independent agent checks each exit criterion and records pass
   or fail in the phase file. Open criteria go to the user (section 6).
2. Full test suite: `uv run pytest -q`; ruff clean. Record the counts.
3. Demo: run the phase file's demo script and record the output (text, screenshots, a
   short README with the commit) under `docs/demos/SP<n>/`.
4. Close the phase file: status line "done (<date>, commit <hash>)", session log
   completed, deviations listed, every step row with its status and commit.
5. Update the program board (`docs/phases/README.md`: status, session date, closing
   commit) and `TODO.md` (milestones, decisions, known issues, backlog, findings index).
6. Update the `CLAUDE.md` status line, commands and layout (if modules, commands or
   directories changed) and the `README.md` status and results.
7. Close-out decisions: put to the user the items of the phase file's section 10 marked
   "at close-out", and confirm which phase runs next, with the recommendation first (the
   board says the order can change at any session boundary). Log the answers as decisions
   in `TODO.md`. The phase chosen is the "next phase" of items 8, 9 and 13; if it has no
   phase file yet, follow "How to add a phase" on the board.
8. Fact-check the NEXT phase file against the code as it now is: inventory line numbers
   and function names; anything this phase changed that the next phase's design relies
   on; entry criteria. State the commit and date of the check in its section 6. Finalise
   its section 13 prompt (remove the "draft" mark).
9. Handoff: move the current `docs/handoff/NEXT_SESSION.md` to
   `docs/handoff/archive/<date>-<phase>.md` (date and phase of the session that wrote it)
   and write a new one (section 8 below). A handoff that was written while its phase was
   in progress is archived as `<date>-<phase>-in-progress.md`. If the name is taken, add
   `-2`, `-3`, and so on. An archived handoff is never overwritten.
10. Memory directory: update the project-status note and `MEMORY.md`; add or correct the
    way-of-working and toolchain notes if something new was learned. A gotcha or rule
    recorded in memory is also written into this file (section 11) or the handoff: memory
    holds pointers, the repository holds the content.
11. Cold-read check, by an agent that did not write the documents. Starting from
    `docs/handoff/NEXT_SESSION.md` and reading only what it names, the agent confirms
    that: every path exists; every commit hash resolves (`git cat-file -e <hash>`); the
    test counts equal those of the recorded full-suite run (item 2); every results
    directory named is on disk; the memory status note and `MEMORY.md` agree with the
    program board; and the prompt text is identical in the handoff, in the next phase
    file's section 13 and in the copy to be printed. Fix what it finds and record the
    check in the session log.
12. Final commit, subject `Close SP<n>: trackers, handoff, next phase file`, with a clean
    tree afterwards. The closing commit hash on the board, in the phase file and in the
    handoff is the last commit that changed code or results. This bookkeeping commit
    follows it; the handoff names the closing commit by hash and the bookkeeping commit
    by this subject, because a file cannot contain the hash of the commit it is in.
13. Print the prompt for the next session to the user (the same text as in the handoff
    and in the next phase file's section 13).

## 8. What a handoff file must contain

`docs/handoff/NEXT_SESSION.md` is short and points at the phase file; it does not repeat
the design. It is modelled on the 2026-09-30 handoff (archived under
`docs/handoff/archive/`). Sections, in this order:

1. **Header.** Date written; the phase just closed (or "phase in progress", section 10);
   the closing commit by hash and the subject of the bookkeeping commit that contains the
   handoff (section 7, item 12); the reading order for the new session (section 3,
   item 1).
2. **The request.** The user's own words for anything new they asked for in the session,
   lightly cleaned and quoted, so intent is not lost in paraphrase. "No new request" if
   there was none.
3. **What was finished.** The closed phase's exit criteria with pass, fail or accepted
   miss; headline results with their caveats beside them; links to the findings notes and
   the recorded demo.
4. **Requirements and status.** The table of the user's standing requirements (R1, R2,
   ...) with the status of each at handoff.
5. **The next phase.** Which phase file to open; its goal in one paragraph; what the
   closed phase changed that the next one relies on; inventory items flagged as drifted
   or unchecked.
6. **Decisions to put to the user first.** Each with the recommendation first, or "none".
7. **State of the project.** Commits of the session, newest first; test counts (fast and
   slow) and ruff state; key results directories with their timestamps; the findings
   index; open known issues that matter to the next phase.
8. **How work is done.** A pointer to this file, plus anything specific to the next
   phase.
9. **Gotchas learned this session.** New ones only; the standing list is section 11 here,
   and a gotcha that will apply to every later session is added there.
10. **Prompt to start the next session.** Ready to paste; identical to section 13 of the
    next phase file. If the copies ever differ, the phase file's section 13 wins.

A handoff written while its phase is in progress has a different layout; section 10 lists
it.

## 9. ID conventions and status marks

| Kind | Form | Fields | Where it lives |
|---|---|---|---|
| Decision | `D-<phase>-<nn>`, for example `D-SP1-03`; decisions from before this system are `D-P0-nn`, `D-P1-nn`, `D-P2-nn` in chronological order | date; the decision; who took it (user, or design approved with a plan) | `TODO.md` decisions log; phase files cite the id and do not restate it at length |
| Known issue | `KI-nnn` | severity `low`, `medium` or `high`; status `open`, `closed` or `wontfix`; owner phase | `TODO.md` known issues |
| Backlog item | `B-nnn` | priority `P0` to `P3`; target phase | `TODO.md` backlog |

- The approved plan wrote decisions as `D-nnn`; the per-phase form above replaces it.
- Numbers are assigned in `TODO.md` and never reused. A document that needs to mention an
  issue or backlog item that has no number yet describes it in a few words and says "see
  TODO.md known issues" (or "backlog"); it does not invent a number. Once the number
  exists, documents cite it.
- Entries are closed or superseded in place, with a date; they are not deleted. A decision
  that replaces an earlier one names it ("supersedes D-SP1-11").
- Phases are `SP<n>`; steps are numbered inside their phase file ("SP1 step 5"). A step
  added during a session takes a letter suffix (5a) so later numbers do not move.

Status marks, in step tables, milestones and checklists:

| Mark | Meaning |
|---|---|
| `[ ]` | not started |
| `[~]` | in progress |
| `[x]` | done: its gate passed |
| `[!]` | blocked, or needs a decision from the user |

Phase status lines use exactly one of: `not started`, `in progress (session <date>)`,
`done (<date>, commit <hash>)`. Dates are ISO (2026-09-30). Results timestamps are UTC.

## 10. If a session ends early

Context runs low, time runs out, or a blocker needs the user. Stop at a step boundary if
possible; do not leave a half-edited physics change uncommitted.

1. Bring the tree to a state the next session can trust: either commit the work in
   progress on a passing fast suite with a message that says "WIP, SP<n> step <k>", or
   revert the uncommitted part. Say which in the session log. Never leave a results
   directory from a dirty tree cited anywhere.
2. Phase file: step rows up to date (`[x]` with commits, `[~]` for the step in hand, `[!]`
   for a blocked one). Add a session-log entry with the exact resume point: the step, what
   is done inside it, what is not, which review or gate is outstanding, the failing test
   or open question, and the command to run first. Leave the status line as "in progress
   (session <date>)".
3. `TODO.md` and the program board: the phase stays "in progress"; new decisions, known
   issues and backlog items are logged.
4. Handoff: archive the old one (section 7, item 9) and write
   `docs/handoff/NEXT_SESSION.md` with "phase in progress" in the header, the resume point
   copied from the session log, the state of the tree, and a prompt that says "resume
   SP<n>" and sends the reader to the step table (it names the step if one is in hand).
   The next phase's file is not finalised. Sections of an in-progress handoff, in this
   order: header; the reading order (section 3, item 1); the request; the state when the
   file was written (a dated snapshot); requirements and status; how to resume (the resume
   point); decisions to put to the user first; what must stay true; how work is done, and
   the gotchas; the prompt to resume, identical to the "Resume" prompt in section 13 of the
   phase file. The handoff written in SP1 step T follows this layout.
5. Memory: the project-status note says the phase is in progress and where to resume.
6. Commit, subject `SP<n> in progress: handoff at step <k>`, and print the resume prompt
   to the user.

The resuming session runs the start checklist (section 3) from the top, skips the status
change in item 8, and adds its own dated entry to the session log.

**If the previous session ended without this checklist** (context exhausted, a crash, the
window closed). The handoff on disk may then still say "start SP<n>" and name the previous
phase's closing commit, while the tree holds SP<n> commits and the phase file says "in
progress". The order of authority is:

1. `git log` and `git status`: what was committed, and what is left in the working tree;
2. the step table of the phase file (section 7): which steps passed their gate;
3. the session log of the phase file (section 11): one line per passed gate (section 4,
   item 6) and the notes of the last session.

Any "state" section of a handoff is a dated snapshot and loses against these three. What
the working tree holds:

- Only `docs/phases/SP<n>-*.md` and `TODO.md` modified: the stop was at a step boundary,
  after a step's commit and before its tracker commit. Check the rows against `git log`,
  commit them (`SP<n> step <k>: trackers (<hash>)`) and continue with the next step.
- Anything else uncommitted: the stop was inside a step. Read the diff, then finish the
  step through its reviews and gate, or put the choice to the user. Nothing is discarded
  without asking.

Then write an in-progress handoff (item 4) before continuing, so the next interruption
finds a current one.

## 11. Gotchas that apply to every session

Tools and shell (Windows 11, PowerShell 5.1 and Git Bash):

- PowerShell 5.1 has no `&&`. Run the two ruff commands separately, or use Git Bash.
- The Bash tool can reject a long command with a quoted heredoc before anything runs.
  Write longer scripts to the scratchpad with the Write tool and run them with
  `python <file>`; keep file-writing calls to about 150 lines.
- `cd` inside a Bash command can move the session's working directory. Use absolute paths.
- The console is cp1252. Every file open passes `encoding="utf-8"`; console output stays
  ASCII.
- Background Bash commands are not killed at the 10-minute tool timeout. A Monitor expires
  after 30 minutes and must be re-armed.
- The output files of background subagents were 0 bytes in the 2026-09-30 session: a
  subagent's report existed only in its notification text. Save any design, survey or
  review worth keeping to a repository file (`docs/phases/inputs/` for designs and
  surveys) as soon as it arrives (TODO.md KI-020).
- Background Explore agents took from 10 minutes to 2.5 hours of wall clock in that
  session. Do not wait idle for them: put the open questions to the user while they run.

Code and data:

- pytest runs with `filterwarnings=error`: never call `warnings.warn` in library code.
- Python's `json` writes `NaN`, which JavaScript rejects. q and Mach are NaN during the
  vented-shaft push; emit `null`.
- A standalone HTML file needs `<meta charset="utf-8">`; a local server sends no charset
  and the minus and degree signs turn into mojibake. The Write tool turns `\uXXXX` escapes
  into real characters.
- The browser pane shows files outside the project folder as static snapshots (no
  JavaScript). To test a page, serve its folder with `python -m http.server` on 127.0.0.1
  and open that URL.

Results and timing:

- Never write into `results/` by hand, and never overwrite or delete a results directory.
- Only each run's top-level `summary.md` is tracked. A fresh clone must re-run an
  experiment before `animate` or `replay` can read its CSVs.
- Machine speed varies about 3x under load (full suite 4-20 min at 2eebcae). A searched
  planar run takes 7-25 s; `silo_screening_2d` took about 27 min for the run and 26 min
  for the sweeps. Budget long runs as background commands.
- `plots.CALIBRATION_RECORDS` feeds the calibration caveat in `animate` and `replay`;
  update it whenever the calibration is re-run.

Working with the user:

- Plan first; show the plan before code. Put the recommendation first in every decision
  question and give the trade-off in one line.
- Keep caveats next to every headline number. On the gate vehicle that means, at least:
  the calibration miss (+14.3%), sweep-optimized and unthrottled guidance, and no
  structural mass charged for the 4 g push.
- Commit at each gate and keep the trackers current; the user reads them.
