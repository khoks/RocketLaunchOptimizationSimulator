# Review of the first draft of the SP2 design (step A0, 2026-10-05)

Six independent reviewers read the first draft of the SP2 plan on 2026-10-05, at commit
b69ff0c, each through one lens. Together they made 2 blocker, 49 major and 31 minor
findings. The approved design
([../2026-10-05-SP2-design.md](../2026-10-05-SP2-design.md)) is the second version of the
plan, with the findings folded in; the user approved that version, not the draft these
files review.

| File | Lens | Blocker | Major | Minor |
|---|---|---|---|---|
| [01-numerics.md](01-numerics.md) | numerics | 0 | 4 | 7 |
| [02-honesty.md](02-honesty.md) | honesty | 0 | 11 | 4 |
| [03-compliance.md](03-compliance.md) | compliance with CLAUDE.md and the session protocol | 0 | 6 | 8 |
| [04-security.md](04-security.md) | security | 0 | 8 | 5 |
| [05-delivery.md](05-delivery.md) | delivery | 1 | 11 | 4 |
| [06-design.md](06-design.md) | interaction design | 1 | 9 | 3 |
| Total | | 2 | 49 | 31 |

How to read them:

- Each finding has a claim, its evidence and a proposed change. A proposed change is the
  reviewer's proposal; what was decided is in the approved design and in TODO.md (D-SP2-01
  to D-SP2-38).
- The first draft is not saved here: the plan file was rewritten into the second version.
  Plan line numbers and some section numbers in the reviews (for example a section 4.10)
  are those of the draft and do not match the approved design.
- Findings that mention scratch scripts or probe files refer to the session scratchpad;
  those files are not in the repository. Survey reports the findings cite are saved in
  [../2026-10-05-SP2-survey/](../2026-10-05-SP2-survey/README.md).
- Line numbers of repository files are for commit b69ff0c. Where a review and the code
  disagree, the code wins.
- The files are a record and are not edited. Each is the reviewer's output as the session
  saved it, with its first line (a hash that named the lens) replaced by a title.
