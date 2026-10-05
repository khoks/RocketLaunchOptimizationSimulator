# SP2 code survey (step A0, 2026-10-05)

Nine read-only surveys made by nine agents on 2026-10-05, at commit b69ff0c (clean tree),
for SP2's Plan mode (step A0). The approved design
([../2026-10-05-SP2-design.md](../2026-10-05-SP2-design.md)) was written from them, and the
corrections to section 6 of the phase file
([../../SP2-launch-app-2d-scene.md](../../SP2-launch-app-2d-scene.md)) come from report 01.

- Every line number in the reports is for commit b69ff0c and will drift as SP2 changes the
  code. Where a report and the code disagree, the code wins.
- The scratch scripts and output files the reports mention (`inv_*.py`, `s03_*.py` to
  `s09_*.py`, `m07_*.py`, `rp_*.py` and their outputs) stayed in the session scratchpad and
  are not in the repository. A number that rests on one of them can be reproduced only by
  writing the script again.
- Each file starts with a one-line provenance header; the rest is the agent's report, byte
  for byte. The reports are a record and are not edited: corrections go into the phase file.
- Report 01 was written to the session's plan folder, because Plan mode was active while
  its agent ran (the report says so); the other eight were written to the scratchpad.
- The reports address the session that planned SP2. A recommendation in them is a proposal;
  what was decided is in the approved design and in TODO.md (D-SP2-01 to D-SP2-38).

| File | What it covers |
|---|---|
| [01-inventory-recheck.md](01-inventory-recheck.md) | The re-check of the phase file's section 6 against HEAD: the header diff (four files), the corrected line numbers of plots.py, replay.py, tests/test_animate.py and site/build.py, the users of the names step A1 moves, the three monkeypatches, what SP1 step 10a added, entry criteria 2 to 6 and 10, the two fix tables of site/build.py, and the statements of the phase file that HEAD contradicts |
| [02-run-path.md](02-run-path.md) | The run path of one experiment, from `cli.load_experiment` to `write_run`: `run_experiment`, `planar_experiment_result`, `git_info` and where its record goes, the experiment label, progress, thread safety and process state, the in-memory composition in the tests, and run times recorded and measured |
| [03-config-and-form.md](03-config-and-form.md) | The mapping from a form to an experiment dict: the structure of experiments/silo_offload_2d.yaml, each form field's keys, the refusals and the bad inputs that are not refused, run names, what the form may not change, the presets, the README-loads fork, and pad-only launches |
| [04-replay-template-and-brand.md](04-replay-template-and-brand.md) | templates/replay.html and the payload it consumes, the brand tokens with their measured contrast, site/build.py (framing, the gallery, the link check), the 2026-09-30 prototype, the tests that pin the template, and the recommendation of a deliberate copy guarded by a pin test |
| [05-run-data-on-disk.md](05-run-data-on-disk.md) | The recorded run data: directory layout, timeseries.csv, events.csv, metrics.json, resolved_config.yaml, the key numbers for a mock-up and the camera, the liftoff-mass identity and the tank-level inputs, sizes, and the gate vehicle file |
| [06-run-data-refactor-plan.md](06-run-data-refactor-plan.md) | The move plan for step A1 (`run_data.py`): inventory and destinations, the duplicates and their exact differences, error types, monkeypatch and identity traps, the fairing event reader (KI-016), the byte-identity risks of the replay page, model-keyed column sets, and the proposed public API |
| [07-server-and-worker.md](07-server-and-worker.md) | The app server and job runner: the measurement behind thread against child process, safety rules for a loopback-only server, shutdown and interruption on Windows, port, browser and console output, and the proposed endpoints |
| [08-docs-site-tests.md](08-docs-site-tests.md) | The statements in the documents and the site that become wrong once `launchsim app` exists, the manual, the gallery and the deck, the test conventions, pyproject.toml, Pillow and .gitignore, how SP1's demo screenshot was taken, the sections of docs/physics.md, and what SP7 expects of SP2 |
| [09-scene-math-prototype.md](09-scene-math-prototype.md) | The scene's arithmetic tried on recorded runs: tank levels, separation states and the ballistic coast, the Earth-fixed drawing transform, the camera, the time grid, the plume fraction, and what the scene would show that the model does not support |
