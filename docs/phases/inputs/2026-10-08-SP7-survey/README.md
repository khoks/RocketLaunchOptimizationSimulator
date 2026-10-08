# SP7 step 0: read-only code and source surveys

Nine surveys made by workflow agents in SP7 step 0 on 2026-10-07 and 2026-10-08, at HEAD 22c62e9
("Close SP2: trackers, handoff, next phase file"; clean tree), before any SP7 code. Line numbers
are for that commit and drift as the code changes. Each file has a one-line provenance header
and is otherwise the agent's report byte for byte, taken from the workflow journal (the agents
could not write report files themselves). The scratch scripts and the scratch folders they name
are not in the repository. These files are a record and are not edited; corrections go into
docs/phases/SP7-structural-mass-push-load.md. The design built on them is
../2026-10-08-SP7-design.md.

| File | Subject | Used for |
|---|---|---|
| [01-assist-track-events.md](01-assist-track-events.md) | The drive seam (`AssistModel`), the track phase, its events, the 1-D and planar preludes, the push metrics, the assist energy identity; the linear motor's closed forms checked | design 4.6-4.8; D-SP7-24 to D-SP7-27 |
| [02-config-and-validators.md](02-config-and-validators.md) | The configuration layer: resolved dicts as raw YAML, the assist and offload models, KI-030 reproduced and the validators that close it, where a structural switch can live | design 4.3, 4.9; D-SP7-21, D-SP7-28 |
| [03-offload-pipeline.md](03-offload-pipeline.md) | The offload solver, the factory seam, the constant-2 t cross-check measured bit for bit, the memo collision, the payload search, timings | design 4.4; D-SP7-20, D-SP7-30 |
| [04-wording-reporting.md](04-wording-reporting.md) | Every "nothing structural" sentence and its pinned tests, KI-039, KI-036, KI-038, the gallery regeneration, the readers of a linear-motor run, the app | design 4.5; D-SP7-22, D-SP7-23 |
| [05-recorded-loads.md](05-recorded-loads.md) | The recorded pad and silo load-case histories, the pad envelope per element, the push against it | design 1, 4.2 |
| [06-sources-structures.md](06-sources-structures.md) | Sources: Falcon 9 construction (SpaceX user guides), Al-Li 2195 allowables, SP-8007, NASA-STD-5001B, Gerard's stiffened-shell relations, mass-estimating relations | design 4.2; S0 |
| [07-sources-drive-dynamics.md](07-sources-drive-dynamics.md) | Sources: EMALS, NASA MSFC magnetic launch assist, MagLifter, linear-motor efficiency, braking, the axial frequency and damping of a liquid stack, dynamic load factors, the snug-shaft piston | design 4.2.1, 4.6-4.8; S0 |
| [08-closed-forms-and-probe.md](08-closed-forms-and-probe.md) | Closed forms checked numerically (linear motor, DLF, trapped column, braking) and a labelled PLANNING PROBE of the structural increment with placeholder coefficients: not a finding, not a target, disclosed in the pre-registration | design 1; the pre-registration's "what is already known" |
| [09-process-tests-budget.md](09-process-tests-budget.md) | Process and test conventions, the design and pre-registration templates, the run-time budget from SP1's measured rates | design 5, 4.10 |
