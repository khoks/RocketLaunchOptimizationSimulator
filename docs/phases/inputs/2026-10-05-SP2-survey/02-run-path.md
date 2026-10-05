Provenance: SP2 step A0 survey 02 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/02-run-path.md); a record, not edited (README.md).

# SP2 A0 survey 02: the run path of one experiment

Repository D:/DEV/ClaudeProjects/SpaceRocketOptimization at HEAD b69ff0c (clean tree before
and after this survey). Read: phase file sections 3, 5.1, 5.6 and the "Run path" table of
section 6. Nothing in the repository was created, edited or deleted; nothing was written
under results/; pytest was not run. Probe scripts and their outputs are in this folder
(`rp_probe_fast.py`, `rp_probe_identity.py`, `rp_probe_thread.py`, `rp_probe_offload.py`,
`rp_probe_offload.log`, `rp_out/`).

All timings below that are marked "measured today" were taken on 2026-10-05 while the fast
test suite and other survey probes were running on the same machine, so they are
loaded-machine numbers (the documents say machine speed varies about 3x under load).

Files of the run path are unchanged since b3150c1 (`git diff --stat b3150c1 HEAD -- src
tests configs experiments pyproject.toml .gitignore site/build.py` lists only
site/build.py, src/launchsim/plots.py, src/launchsim/replay.py and tests/test_animate.py),
so the line numbers of cli.py, config.py, results_io.py, sim.py, offload.py, summary.py and
compare.py in the phase file's "Run path" table hold, with one exception (section 11).

## 1. cli.load_experiment and cli.command_run

`cli.load_experiment(experiment_path: Path) -> ResolvedExperiment` (cli.py 254-276), in
order:

| Line | Call | Raises (all turned into `CliError`) |
|---|---|---|
| 261 | `exp_dict = load_yaml(experiment_path)` | file not found, unreadable, not UTF-8, YAML parse error, top level not a mapping (`load_yaml` 191-208) |
| 262-264 | `exp_dict.get("vehicle")` must be a `str` | `CliError("...: 'vehicle' must be a path string")` |
| 265 | `vehicle_dict = load_yaml(resolve_vehicle_path(experiment_path, vehicle))` | drive-relative path, missing file (`resolve_vehicle_path` 229-251) |
| 267-268 | closure `load_vehicle(path)` for a calibration case's own vehicle file | |
| 271 | `resolved = resolve_experiment(exp_dict, vehicle_dict, load_vehicle)` | pydantic `ValidationError`, `ConfigPathError`, `ExclusiveKeysError`, `ValueError` |
| 272 | `sim.check_result_names(resolved)` | `InvalidNameError` |
| 273 | `sim.check_resolved(resolved)` (the preflight) | `ValueError` |
| 274-275 | `except ValueError as exc: raise CliError(f"invalid configuration in {experiment_path}:\n{exc}")` | |

It prints nothing. The `CliError` text for a pydantic error is multi-line (the `\n{exc}` at
275), so the app cannot reuse it as the "one-line message in the form" of exit criterion 4;
it has to condense the `ValueError` itself.

`cli.command_run(args) -> int` (cli.py 377-414):

1. 380 `resolved = load_experiment(experiment_path)`.
2. 381-385 an unknown `--variant` raises `CliError`.
3. 386-394 `er, out_dir = sim.run_experiment(resolved, results_root(args, experiment_path),
   plots=not args.no_plots, only_variant=args.variant,
   repo_root=repo_root_or_cwd(experiment_path), sensitivity=not args.no_sensitivity,
   offload=not args.no_offload)`. So the names and the preflight are checked twice on the
   CLI path (cli.py 272-273 and results_io.py 830-831). The app needs them once.
4. Prints, through `say` (ASCII, backslash escapes; cli.py 177-179): `results: <out_dir>`
   (395); one `run_line` per run (396-397: status and flags; a planar run adds P* [kg],
   gamma* [deg], max-Q [Pa]); one per calibration case (398-399); `offload_lines(er.offload.record)`
   when the experiment has a block (400-402: the skip note, or `offload at P_ref ... kg:`,
   one line per case and per pad control, the arm count); the pre-registration line of a
   calibration run (403-411); the sensitivity count (412-413). Returns 0.

`cli.main` (491-510) catches `CliError` (prints `error: <message>`, exit 1) and `OSError`
(prints `error: <type>: <message>`, exit 1; an unwritable results root); anything else
keeps its traceback. `_configure_stdout` (164-174) sets `sys.stdout.reconfigure(errors="replace")`,
process-wide.

`cli.results_root(args, experiment_path)` (285-289) and `repo_root_or_cwd(experiment_path)`
(279-282) both need an experiment file path: `find_repo_root` (182-188) walks up to the
nearest `pyproject.toml`. The app has no experiment path of its own; it must find the
repository (and from it experiments/ and configs/, which do not ship in the package) from
the committed template file or from the working directory.

## 2. results_io.run_experiment

Signature (results_io.py 793-801):

```python
def run_experiment(
    resolved: ResolvedExperiment,
    out_root: Path,
    plots: bool,
    only_variant: str | None = None,
    repo_root: Path | None = None,
    sensitivity: bool = True,
    offload: bool = True,
) -> tuple[ExperimentResult, Path]:
```

Arguments: `resolved`, the resolved experiment; `out_root`, the results root (the directory
is `<out_root>/<experiment name>/<stamp>`); `plots`, write PNGs or not; `only_variant`, run
only that variant beside the baseline (and, on planar, skip the calibration cases:
`run_cases=only_variant is None`); `repo_root`, the directory handed to `git_info` and
`preregistration_state` (None means `Path.cwd()`, `_repo_root_of` 789-790);
`sensitivity`, False skips the sensitivity cases and the offload block's arms;
`offload`, False skips the offload block (its record then says `OFFLOAD_SKIPPED`).

Statements in order:

| Line | Statement |
|---|---|
| 820 | `from launchsim import sim` (late import; `run_resolved`, `git_info`, `check_resolved` are looked up on `sim` at call time) |
| 822-823 | `exp = resolved.experiment`; `variants = resolved.variants` |
| 824-829 | `only_variant` filter; `ValueError` when it names no variant |
| 830 | `check_result_names(resolved)` |
| 831 | `sim.check_resolved(resolved)` (the preflight; a refused configuration writes nothing) |
| 832 | `git = sim.git_info(_repo_root_of(repo_root))` |
| 833 | `now = datetime.now(UTC)` (one clock read for the directory name and `timestamp_utc`) |
| 834 | `out_dir = make_run_dir(Path(out_root), exp.name, now=now)` |
| 835 | `try:` |
| 836 | `baseline = sim.run_resolved(resolved.baseline)` (always; no cache) |
| 837 | `variant_results = {name: sim.run_resolved(r) for name, r in variants.items()}` |
| 838 | `if is_planar(resolved):` |
| 839-848 | `er = planar_experiment_result(resolved, baseline, variant_results, git, utc_timestamp(now), sensitivity=sensitivity, run_cases=only_variant is None, offload=offload)` |
| 849-850 | calibration label only: `er = replace(er, preregistration=preregistration_state(...))` |
| 851 | `write_run(er, out_dir, plots)` |
| 852 | `return er, out_dir` |
| 853-885 | the 1-D branch (compare, `run_sensitivity`, `ExperimentResult`, `write_run`) |
| 886-888 | `except BaseException as exc: write_failure_marker(out_dir, exc); raise` |
| 889 | `return er, out_dir` (1-D) |

Every name the planar branch uses is public and importable from `launchsim.results_io`
(most also re-exported by `launchsim.sim`, sim.py 222-271): `check_result_names` (234),
`utc_timestamp` (359), `make_run_dir` (365), `git_info` (400), `write_failure_marker` (567),
`write_run` (687), `planar_experiment_result` (1973), `is_planar` (948). The phase file's
list of pieces (section 5.6) omits `utc_timestamp`, which the app needs to turn `now` into
the `timestamp_utc` string.

`make_run_dir(root, experiment_name, now=None) -> Path` (365-382): `check_name` on the
experiment name, `mkdir(parents=True, exist_ok=True)` of `<root>/<name>`, then
`mkdir(exist_ok=False)` of `<stamp>`, `<stamp>-2`, ... up to `MAX_DIR_SUFFIX` (1000). On a
collision the directory is `<stamp>-2` while `timestamp_utc` inside the files stays
`<stamp>` (line 844 passes `utc_timestamp(now)`), so a directory must be addressed by its
directory name, not by the timestamp in metrics.json.

`write_failure_marker(out_dir, exc) -> Path` (567-584) writes `FAILED.txt` with the
traceback; best effort (an `OSError` while writing is swallowed).

## 3. results_io.planar_experiment_result

Signature (results_io.py 1973-1983):

```python
def planar_experiment_result(
    resolved: ResolvedExperiment,
    baseline: RunResult,
    variants: dict[str, RunResult],
    git: dict[str, Any],
    timestamp_utc: str,
    *,
    sensitivity: bool,
    run_cases: bool,
    offload: bool = True,
) -> ExperimentResult:
```

Inputs: the resolved experiment; the baseline `RunResult`; the variant `RunResult`s that
ran, by name; the git dict (stored as given); the timestamp string; `sensitivity` and
`run_cases` are required keywords.

What it computes, in order:

| Line | What |
|---|---|
| 1996 | `ran = {baseline.name, *variants}` |
| 1997-2001 | `run_sensitivity(resolved, baseline, ran, nominal={baseline.name: baseline, **variants})` when `sensitivity` (compare.py 373; planar: `_run_planar_sensitivity` 1786-1869, one loop over `resolved.sensitivity`) |
| 2002-2004 | `planar_sensitivity_note(...)` |
| 2005 | calibration cases: `{n: sim.run_resolved(r) for n, r in resolved.cases.items()}` when `run_cases` |
| 2007 | `planar_comparisons(resolved, baseline, variants)` (960-996): the baseline's matched run at P_ref (`sim.matched_run`; for a baseline at its own P* it reuses the final evaluation's trace and flies nothing, sim.py 1654-1655), then per variant `sim.matched_run(..., neighbours=True)` (one final-mode evaluation at P_ref and two gamma* neighbours) and `compare_planar`. The `resolved` argument is not read in the body |
| 2008 | `planar_bounds(resolved, baseline, ran)` (999-1038) |
| 2009 | `planar_offload(resolved, baseline, variants, sensitivity=sensitivity, offload=offload)` (1687-1807), the offload post-pass |
| 2010-2027 | `ExperimentResult(experiment_name=resolved.experiment.name, vehicle_name=resolved.baseline.vehicle.name, baseline=baseline, variants=variants, comparison=..., git=git, timestamp_utc=timestamp_utc, comparison_basis=shared_basis(resolved), sensitivity=rows, sensitivity_note=note, model=PLANAR_2D, label=resolved.experiment.label, bounds=bounds, cases=cases, search_budget_id=planar.search.budget_id(), offload=report)` |

It writes nothing (checked: the probes' working directory stayed empty apart from what
`write_run` wrote; SP1's `test_offload_in_memory_writes_nothing` asserts the same).

### 3.1 Is it callable with a baseline produced earlier in the same process?

Yes. It takes the baseline as an argument and never runs `resolved.baseline` itself. What
it reads from the baseline `RunResult`:

- `baseline.name` (1996, record keys);
- `baseline.resolved`: `run.planar.checks` (974), `to_vehicle()` (980, `reference_payload_kg`
  compare.py 1271-1277), `trajectory_key(baseline.resolved)` (the memo of `_run_memo`
  1125 and of `_run_planar_sensitivity` compare.py 1810), `run_dict` and `vehicle_dict`
  (resolved_config.yaml 595-601);
- `baseline.result`: metrics, time series, events, search record, trace.

What it reads from `resolved` about the baseline: `resolved.baseline.run.planar`,
`resolved.baseline.to_vehicle()` (the energy vehicle, 1733), `resolved.baseline.vehicle.name`
(1794, 2012), `resolved.baseline.run_dict` (compare.py 1846).

Two identity tests compare the baseline's `ResolvedRun` object, not its content:

- results_io.py 1134, in `_run_memo`: `if hit.resolved is resolved: return hit, True`,
  else `sim.rerun_resolved(resolved, hit)`;
- results_io.py 1762, in the arm loop: `if arm.pad is baseline.resolved: pad = baseline`,
  else `pad, _ = ctx.run(arm.pad)` and `checked[f"{arm.pad.name} (offload sensitivity pad)"] = pad`.

`config._resolve_offload` gives a run-parameter arm `pad = baseline`, the `ResolvedRun`
object of this launch's resolve (config.py 2800-2807). So a cached `RunResult` that still
wraps the `ResolvedRun` of an earlier launch (equal as a dataclass, a different object)
takes the other branch.

Measured (`rp_probe_identity.py`, the fake sim seams of tests/test_offload_pipeline.py, a
block with one stage-1 solve and its `assist.drive_efficiency` arms):

| Baseline handed in | `checked_runs` | `rerun_resolved` calls |
|---|---|---|
| wraps this launch's `resolved.baseline` (the CLI path) | 3 entries | none |
| cached and used verbatim (wraps the earlier, equal `ResolvedRun`) | 4 entries: an extra `pad (offload sensitivity pad)` | 2 (`pad` from `pad`, once per arm) |
| cached and re-wrapped: `dataclasses.replace(cached, name=resolved.baseline.name, resolved=resolved.baseline)` | 3 entries | none |

The offload record is the same in all three; the verbatim reuse changes the summary's
Checks section (one more listed run, carrying the "trajectory reused" flag). The re-wrap
gives the CLI path exactly.

### 3.2 What in a RunResult is mutable or tied to one experiment

- `RunResult` (sim.py 664-670): frozen dataclass of `name`, `resolved`, `result`.
- `ResolvedRun` (config.py 2345-2357): frozen dataclass; `run` and `vehicle` are frozen
  pydantic models (`_Model`, config.py 214-217); `run_dict` and `vehicle_dict` are plain,
  mutable dicts (written to resolved_config.yaml as they are).
- `Result` (sim.py 626-661): frozen dataclass whose fields are mutable containers
  (`metrics` dict, `timeseries` and `events` DataFrames, `assumptions` and `flags` lists,
  `phases`, `search`, `closure`, `trace`). It holds no experiment name, no timestamp, no
  git state and no reference to the `ResolvedExperiment`. The run's name is only in
  `RunResult.name` and `ResolvedRun.name` / `run_dict["name"]`.
- `ExperimentResult` (results_io.py 291-330) is what is tied to one launch:
  `experiment_name`, `vehicle_name`, `git`, `timestamp_utc`, `label`, `comparison` (keyed by
  variant name), `search_budget_id`, `offload`.

Nothing in the pipeline mutates a finished `Result` in place: `with_assumptions` (sim.py
1699-1705) and `rerun_planar` (1557-1588) build new objects with `replace`; `metrics_record`
(metrics.py 763-772) builds a new dict; a grep for in-place writes to `.metrics`, `.flags`,
`.assumptions` of results finds only the planners appending to a trace under construction.
Measured (`rp_probe_fast.py`): a fingerprint of the baseline result (metrics JSON, both
CSV texts at 17 digits, assumptions, flags, status) was unchanged after two
`planar_experiment_result` passes and three `write_run` calls.

### 3.3 Reuse under another launch, and what must be equal

A baseline `Result` is a function of `(RunConfig, Vehicle)`, that is of the resolved
`run_dict` and `vehicle_dict`, plus the code and the numeric stack of the process
(`sim.run_resolved` 876-880, `sim.run` 847, `run_planar(run_config, vehicle)` 1512). The
experiment name does not enter it.

The resolved baseline dicts already contain every block the brief lists. For
experiments/silo_offload_2d.yaml at HEAD:

- `resolved.baseline.run_dict` keys: `name`, `dynamics`, `site`, `planar` (`guidance`,
  `search`, `target_orbit`, `checks`), `assist`, `ignition`, `end`, `integrator`
  (`{'method': 'DOP853', 'rtol': 1e-10, 'planar_max_step_s': 2.0, 'sample_dt_s': 0.05}`);
- `resolved.baseline.vehicle_dict` keys: `name`, `description`, `stages`, `fairing_mass_t`,
  `payload_mass_t`, `fairing_drop`, `screening`, `aero`.

So equality of those two dicts covers the baseline run block, the vehicle, the search,
guidance and integrator blocks, the target orbit, the site and the checks. Both dicts are
JSON-serialisable (`json.dumps` works; the SP1 digest pin relies on it).

Measured (`rp_probe_fast.py`, fixed guidance): two experiments with different names and a
different variant (stroke 100 m and 200 m) resolve equal baseline dicts (equal digests,
equal `trajectory_key`, `ResolvedRun` objects equal but not identical). With the cached
baseline re-wrapped, the second launch's metrics dict, resolved-config dict and summary
text were equal, character for character, to those built from a freshly run baseline.

### 3.4 The cache key

Existing digest helpers:

| Helper | Where | Serialisation |
|---|---|---|
| `compare.trajectory_key(run: ResolvedRun) -> str` | compare.py 1768-1783 | sha256 of `json.dumps({"run": ..., "vehicle": ...}, sort_keys=True, separators=(",", ":"), default=str)` with the run's `name`, the energy-only assist keys and the vehicle's `screening` block removed |
| `SearchConfig.budget_id() -> str` | config.py 1213-1217 | sha256 of the search block's canonical JSON (sorted keys) |
| `dict_digest(data)` | tests/planar_pin_support.py 126-129 | sha256 of `json.dumps(data)`, key order kept; the helper behind `test_shipped_planar_resolved_dicts_match_the_pinned_digests`. It lives under tests/ and is not importable from the package |

Proposed key (a new small function in the app; same serialisation as `trajectory_key`,
on the full dicts):

```python
def baseline_cache_key(baseline: ResolvedRun, server_git: Mapping[str, Any]) -> str:
    payload = {
        "run": baseline.run_dict,          # name, dynamics, site, planar{guidance, search,
                                           # target_orbit, checks}, assist, ignition, end, integrator
        "vehicle": baseline.vehicle_dict,  # the whole vehicle, payload_mass_t and screening included
        "code": {"hash": server_git.get("hash"), "dirty": server_git.get("dirty")},
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

On a hit return `dataclasses.replace(entry, name=resolved.baseline.name,
resolved=resolved.baseline)`. Reasons for the full dicts and not `trajectory_key`: the
sanctioned path for "same trajectory, different dict" is `sim.rerun_resolved`, which adds
`trajectory_reused` and a flag and so would differ from the CLI path; with the full dicts
an equal key means an equal `ResolvedRun` and the re-wrap is exact. `sort_keys=True` makes
the key insensitive to key order; an int against a float (100 and 100.0) gives two keys,
which costs one extra pad run and is never wrong. A dirty tree is not identified by hash
and flag, which is harmless in the process (the code is the one imported) and a reason
not to persist the cache.

Because the form cannot change a shared block, the baseline block or the vehicle file, the
key is the same for every launch of a server: the cache holds one entry (two if Q5 adds
the README-loads fork).

## 4. write_run and the plots

`write_run(experiment_result: ExperimentResult, out_dir: Path, plots: bool) -> Path`
(results_io.py 687-707):

| Line | Writes |
|---|---|
| 691-692 | `check_run_name` of every run |
| 693 | `out_dir.mkdir(parents=True, exist_ok=True)` (it accepts an existing directory: the never-overwrite rule is `make_run_dir`'s, not `write_run`'s) |
| 694 | `resolved_config.yaml` (`_resolved_config_dict` 590-622) |
| 695 | `metrics.json` (`_metrics_dict` 660-684) |
| 696-699 | per run of `er.runs` (the baseline first): `<run>/timeseries.csv`, `<run>/events.csv` (`write_timeseries` 560-564) and, with `plots`, `write_plots(rr.result, out_dir / "plots", name)` |
| 700-705 | the same for the bound runs, the calibration cases and the offload runs |
| 706 | `summary.md` last (`experiment_summary(er)`; `write_run` passes no `header_lines`) |

The cached baseline is in `er.runs`, so it is written into every launch's directory with
no extra code.

Sizes, measured today:

| File | 2 runs, no offload block, sample_dt 0.05 s | 4 runs with an offload block, sample_dt 0.5 s |
|---|---|---|
| metrics.json | 22,718 bytes | 86,828 bytes |
| resolved_config.yaml | 11,536 | 22,911 |
| summary.md | 14,649 | 25,336 |
| `<run>/timeseries.csv` | 3,557,464 (pad, 10,560 rows) and 3,618,868 (silo_cold, 10,550 rows) | 364,308 to 375,835 |
| `<run>/events.csv` | 1,190 and 1,438 | 1,227 to 1,490 |
| `plots/*.png` | 16 files, 502,590 bytes (20,889 to 37,790 each) | 32 files |

Plots: `write_plots(result, plots_dir, prefix) -> list[Path]` (plots.py 115-175) hands a
planar run to `write_planar_plots` (256-298): one PNG per panel of `PLANAR_PLOT_PANELS`
(188-226: trajectory, speed, angles, q_mach, mass_thrust, felt_g, losses; 7 panels) plus
the two `PLOT_TRACK_PANELS` (83-86: track_forces, drive_power) for a run with ASSIST rows.
So 7 PNGs for a pad-type run and 9 for a pushed run, each a 6.4 x 3.6 inch figure at 120
dpi (`PLOT_FIGSIZE_IN`, `PLOT_DPI`, 65-66), named `plots/<run>_<quantity>.png`. Every
figure is a `matplotlib.figure.Figure` saved with `fig.savefig(path, format="png")`.

Timing:

- recorded: docs/physics.md 2796, "writing its files and plots 1.2 s" for one searched pad
  run (against 9.3 s for the run itself, build step 25);
- measured today: `write_run` of 2 runs at sample_dt 0.05 s took 0.59 s without plots and
  2.61 s with them (16 PNGs, about 0.13 s each); of 4 runs at sample_dt 0.5 s, 0.38 s
  without and 6.94 s with (32 PNGs, about 0.2 s each, machine more loaded).

So plots cost about 1 to 2 s per written run: 4 to 14 % of one searched run (7 to 25 s),
and under 5 % of a launch with an offload solve. They are switched off by `plots=False`
(the CLI's `--no-plots`).

## 5. git_info and where its dict goes

`git_info(repo_root: Path) -> dict[str, Any]` (results_io.py 400-444) returns exactly
`{"hash": "<sha12>" | "unborn" | "no-git", "dirty": bool | None, "error": str | None}`. It
runs up to four git commands through `sim._git` (`rev-parse --is-inside-work-tree`,
`rev-parse --show-toplevel`, `rev-parse --short=12 HEAD`, `status --porcelain -- .
:(exclude)results`), each with `GIT_TIMEOUT_S = 5.0`, and never raises. `dirty` ignores the
top-level results tree only, so app runs under `<repo>/results/` do not make later launches
dirty; a results root elsewhere inside the repository would. Measured today: 0.18 s; at
HEAD it returned `{'hash': 'b69ff0c45c29', 'dirty': False, 'error': None}`.

Flow of the dict:

| Sink | Code | What is written |
|---|---|---|
| resolved_config.yaml | `"git": dict(er.git)` (results_io.py 605) | every key, as given |
| metrics.json | `"git": dict(er.git)` (667) | every key, as given |
| summary.md title | `git {git_label(er.git)}` (summary.py 2032; `git_label` 75-84) | hash, with `-dirty` or `-dirty?` |
| summary.md header | `provenance_lines(er.git, er.timestamp_utc)` (summary.py 2042; 571-576) | `- Timestamp (UTC): ...`, `- Git: <label>`, and `- Git error: ...` when set |
| replay page | replay.py 1121, 1145-1146 | `hash`, `dirty` |
| animation | plots.py 1307 | `hash` |

Extra keys survive into the two data files and nowhere else. Measured: with
`git = {**git, "server_start": {"hash": ..., "dirty": ..., "error": None}, "launched_by": "app"}`
both metrics.json and resolved_config.yaml carried the two extra keys unchanged; summary.md
printed only `- Timestamp (UTC): ...` and `- Git: b69ff0c45c29` and did not mention them.

Constraints: the values must be plain YAML types (`write_yaml` uses `yaml.safe_dump`,
538-542, which refuses a `Path` or a numpy scalar; `write_json` goes through `json_safe`).
The extra keys must be added by the app to its own copy of the dict, not inside
`git_info`: the planar output capture pins the key paths `git.hash`, `git.dirty`,
`git.error` of what `run_experiment` writes (tests/data/planar_pins/output_capture.json,
`metrics_keys`).

## 6. The experiment `label`

Today:

| Item | Where |
|---|---|
| `ExperimentLabel = Literal["calibration", "guidance_study"]`, `CALIBRATION_LABEL`, `GUIDANCE_STUDY_LABEL` | config.py 157-159 |
| field `label: ExperimentLabel | None = None` | config.py 1865 (docstring 1853-1854) |
| validator `_labelled_features` | config.py 1948-1987: a paired sweep that varies `guidance.*` needs `label: guidance_study` (1969-1973); `cases` need `label: calibration` (1978-1979) |
| written | results_io.py 613 (resolved_config.yaml `label`) and 676 (metrics.json `label`), both from `er.label`, set at 2022 from `resolved.experiment.label`; also 779 and 2190 (sweep points) |
| read by code | results_io.py 849 (the calibration run's pre-registration state); summary.py 2021 (`banner = [CALIBRATION_BANNER, ""] if er.label == CALIBRATION_LABEL else []`; the banner text is 686-692) |
| read by replay or animate | nowhere |
| shipped files with a label | experiments/calibration_f9_2d.yaml 16, experiments/guidance_trigger_2d.yaml 12; the others have none (written as null) |

Both keys exist in every planar directory already, so a reader can test
`metrics["label"] == "exploratory"`; recorded directories have null or one of the two
values.

Route A, a new value `exploratory`:

| Touch | Change |
|---|---|
| config.py 157 | add the literal; a constant beside 158-159; the docstring at 1853-1854 |
| config.py 1948-1987 | no change needed. A label is single-valued, so an exploratory experiment can declare neither `cases` nor a paired `guidance.*` sweep; the app declares neither |
| results_io.py | no change: 613, 676 and 2022 pass the label through. The app sets `exp_dict["label"] = "exploratory"` and the value reaches both files without any `replace` |
| summary.py 2021 | one more branch and a banner constant for the new value |
| tests | new ones only. Existing label tests match error texts that do not list the allowed values (tests/test_config_planar.py 588, 633, 681) and set labels at tests/test_planar_pipeline.py 434, 1745, 1755; no test reads the literal's members |
| docs | docs/physics.md (schema text near 5409 and 5489, the experiments table at 5732), docs/manual/04-experiments.md, 08-outputs.md, 11-troubleshooting.md |

Route B, a separate provenance field:

- as extra keys of the `git` dict: no code change; reaches metrics.json and
  resolved_config.yaml (section 5); does not reach summary.md unless `provenance_lines`
  (summary.py 571-576) learns to print them;
- as a new `ExperimentResult` field: results_io.py changes (the dataclass 291-320,
  `_metrics_dict` 660-684, `_resolved_config_dict` 590-622) plus summary.py. It must be
  written only when set, as `preregistration` (680-681) and `offload` (682-683) are;
  written unconditionally it would add a key path to metrics.json and a top-level key to
  resolved_config.yaml and fail `test_written_outputs_keep_the_captured_structure`.

Pinned artefacts, either route:

- the resolved digest pin hashes `run_dict` and `vehicle_dict` of every resolved run
  (tests/planar_pin_support.py 185-194). The label is an experiment-level field and is not
  in either dict, so no digest moves;
- the output capture compares file names, key paths and CSV headers of the fast
  experiment (label null) and the sha256 of its normalised summary. `label` is already in
  both key lists and its value is not captured; a banner printed only for the new value
  leaves that summary unchanged.

So Route A (new value plus banner), Route B with git-dict keys, and Route B with a
conditional field all leave every pinned digest and captured output unchanged. Only an
unconditional new key, or a change to what `git_info` returns, would break the capture.
The route that needs no results_io.py change and still puts the word in summary.md is
Route A.

## 7. Progress

### 7.1 Coarse stages the app owns (no pipeline change)

The app makes these calls itself, so it can publish a stage before each:

| Stage | Call | Cost (measured today unless noted) |
|---|---|---|
| resolving | `resolve_experiment`, `check_result_names`, `check_resolved` | 4 ms, under 1 ms, 1 ms |
| provenance | `git_info` | 0.18 s |
| directory | `make_run_dir` | negligible |
| pad baseline | cache hit, or `sim.run_resolved(resolved.baseline)` | 7 to 25 s recorded; 20.8 to 27.7 s today under load |
| each variant | `sim.run_resolved(run)`, one stage per variant because the app owns the loop | 7 to 25 s recorded |
| comparison and offload pass | `planar_experiment_result(...)`, one opaque call | 4 ms with fixed guidance and no block; 2.3 s for one variant's matched run with neighbours; minutes with an offload block |
| writing | `write_run` | 0.2 to 0.3 s per run at 0.05 s sampling; 1 to 2 s more per run with plots |

The long stage is the opaque one. What it will do is known before it starts, from the
resolved block: `resolved.offload.pad_control_modes`, `len(resolved.offload.cases)`, the
cases with `pad_start is not None` (paired pads) and `len(resolved.offload.arms)`; the app
can show "1 pad control, 1 solve with its verification" and an expected range from the
recorded costs.

### 7.2 Loops inside the opaque stage

- `planar_experiment_result`: the sensitivity cases (compare.py 1823), the calibration
  cases (2005), the variants in `planar_comparisons` (982), the bounds (1012, 1017).
- `planar_offload` (1687-1807): `for mode in modes` (1741-1747, one `_pad_control` each:
  a solve on the baseline, 1517, and for an ok solve a verification search, 1521);
  `for case in ro.cases` (1749-1756, one `_offload_case` each: `_solve` 1337, the
  verification `_verified` 1341, `sim.offload_run_result` 1346, the decomposition, the
  paired pad through `ctx.run` 1370); `for arm in offload_arms_that_run(...)` (1759-1790).
  Within one pass, runs and solves of one trajectory key are flown once (`_run_memo` 1118,
  `ctx.solves` 1174-1180).
- `offload.solve_offload` (offload.py 472-567) has no loop of its own: `optimise_gamma`
  (507) and `final_verify` (509). The loops are in search.py: the gamma* grid
  (`_evaluate_grid` 1172, the centre-out `for` at 1187 and the retry `while` at 1196), the
  payload root (`payload_root` 863, `while` at 933 and 970), the Brent refine (`_refine`
  1279) and the final bisection (`_bisect_to_residual` 1587, `while` at 1604). Every
  evaluation passes through `OffloadProblem.evaluate` (offload.py 210-246), which counts
  it (`warm.evaluations += 1`, 235). Recorded counts per solve: 37 to 44 for stage-1
  solves, 63 for stage 2, 42 for both; pad controls 27, 41 and 29 (docs/physics.md
  6097-6098).

### 7.3 What a finer callback would touch

- Per pad control, case, verification and arm: an optional keyword
  (`progress: Callable[[str], None] | None = None`) on `planar_experiment_result` (1973)
  and `planar_offload` (1687), called at 1741, 1749 and 1759 and passed to `_pad_control`
  and `_offload_case` for the verification. results_io.py only; with the default None the
  outputs are unchanged.
- Per evaluation inside a solve: the callback must travel through
  `sim.solve_resolved_offload` (sim.py 1717-1725) into `offload.solve_offload` (472) and
  `OffloadProblem.evaluate` (210) or `OffloadWarmStore` (122-147). That touches sim.py and
  offload.py, the solver the phase file keeps out of scope.
- With no pipeline change at all: results_io looks up `sim.run_resolved`,
  `sim.solve_resolved_offload`, `sim.matched_run`, `sim.rerun_resolved` and
  `sim.offload_run_result` on the `sim` module at call time (sim.py docstring 34-45;
  results_io.py 5-11, 1131, 1178). `rp_probe_offload.py` wrapped those attributes and got
  a line per pad-control solve, case solve, verification search and matched run, with its
  duration (section 10). The same mechanism could memoise the pad controls across
  launches. It is a process-wide patch of module attributes that the tests also patch, so
  it is a test seam used in production; reported as possible, not recommended.

## 8. Thread safety and process state

| Item | Finding |
|---|---|
| Module-level mutable objects | constant tables only (for example `plots.CALIBRATION_RECORDS` plots.py 507, `compare.ENERGY_ONLY_ASSIST_KEYS` 1744, `assist.ASSIST_MODELS`); nothing in src/launchsim assigns to them at run time (tests monkeypatch `CALIBRATION_RECORDS`) |
| Caches | two `functools.cache` functions without arguments, constants of the atmosphere (atmosphere.py 174, 180). No `lru_cache`. `WarmStore` (search.py 353-410) and `OffloadWarmStore` (offload.py 122-147) are created per run or per solve and bound to one problem (`claim`); `_run_memo` and `ctx.solves` live for one pass |
| matplotlib | importing `launchsim.sim` does not import `matplotlib.pyplot` and loads no backend module (checked: `'matplotlib.pyplot' in sys.modules` is False; only `matplotlib.backends` and `.registry`). `write_plots` builds `Figure` objects and saves PNGs through Agg; no pyplot state, no `rcParams` writes, no `matplotlib.use` (plots.py 8-10, 125-127) |
| numpy error state | no `np.seterr` or `np.errstate` anywhere in src/launchsim |
| Working directory | no `os.chdir`. `Path.cwd()` is read at results_io.py 790 (`_repo_root_of(None)`), cli.py 282, 446, 482 and plots.py 1854. The app passes explicit paths. (The SP1 fixture uses `contextlib.chdir`, which is process-wide; do not copy that into a threaded server or its tests) |
| Environment variables | none read in src/launchsim |
| Logging, printing, warnings | no `logging`, no `warnings.warn`; the only `print` is `cli.say` (cli.py 179). The run path is silent |
| Subprocesses | `git_info` only (`subprocess.run`, 5 s timeout each) |
| Late-bound seams | `sim.run_resolved`, `sim.git_info`, `sim._git`, `sim.solve_resolved_offload`, `sim.offload_run_result`, `sim.matched_run`, `sim.rerun_resolved`, `sim.with_assumptions`: module attributes looked up per call. Safe as long as nothing patches them while a job runs |

Running the whole path in one worker thread of the server process is safe on these
grounds, with one job at a time. Measured (`rp_probe_thread.py`, Python 3.12.11 with the
GIL, `sys.getswitchinterval()` 0.005 s): a `ThreadingHTTPServer` on 127.0.0.1 answered a
status request in 1.2 ms median (p95 23 ms, max 34 ms) when idle and in 16.3 ms median
(p95 40.2 ms, max 98.7 ms; 172 requests, one every 0.1 s) while a searched pad run at the
shipped budget ran in a worker thread. The run took 20.8 s in the worker with polling and
22.7 s alone in the main thread; P* (26,054.396 kg) and the whole time series were
bit-identical between the two. The client was in the same process, so a browser should
see no worse.

Hazards that remain with a thread: it cannot be cancelled; a non-daemon worker keeps the
process alive until the solve ends, and a daemon worker killed at exit can leave a
directory with neither summary.md nor FAILED.txt (the marker is written by the `except`
of the job, which a killed thread never reaches). An uncaught exception in the worker goes
to `threading.excepthook` (stderr), so the job function must catch `BaseException`, write
the marker and keep the error for the status endpoint.

Pickling (what a child process under Windows spawn would have to return):

- `pickle.dumps(RunResult)` and `pickle.dumps(ExperimentResult)` fail, for a fixed-guidance
  and for a searched run: `AttributeError: Can't get local object 'hold_rhs_for.<locals>.rhs'`.
  The unpicklable parts are `Result.phases` and `Result.trace`: the phase specs they keep
  hold right-hand-side closures (the one pickle names is the local `rhs` of
  `hold_rhs_for`, phases/prelude.py 507).
- Picklable: `Result.metrics`, `timeseries` (2.76 MB for 10,560 rows), `events`,
  `loss_budget`, `assumptions`, `flags`, `closure`; `ResolvedRun.run`, `.vehicle`,
  `.run_dict`, `.vehicle_dict`; the experiment and vehicle dicts.

So a child process can be given the dicts and can return the directory path (the scene
reads the directory anyway) or plain metrics, but it can neither receive nor return a
`RunResult`. A baseline cache would have to live inside a long-lived child; the phase
file's "cannot share the cache" has this concrete cause.

## 9. tests/test_offload_pipeline.py: the in-memory composition and cheap experiments

The fixture (tests/test_offload_pipeline.py 2165-2181), quoted:

```python
@pytest.fixture(scope="module")
def offload_e2e(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    exp, veh = _searched_experiment(repo_root)
    cwd = tmp_path_factory.mktemp("offload_cwd")
    with contextlib.chdir(cwd):
        resolved = resolve_experiment(exp, veh)
        baseline = sim.run_resolved(resolved.baseline)
        variants = {name: sim.run_resolved(run) for name, run in resolved.variants.items()}
        er = results_io.planar_experiment_result(
            resolved, baseline, variants, {}, "20260101T000000Z", sensitivity=True, run_cases=True
        )
        listing = sorted(p.name for p in cwd.iterdir())
    out = results_io.write_run(er, tmp_path_factory.mktemp("offload_out") / "run", plots=False)
    return SimpleNamespace(exp=exp, veh=veh, resolved=resolved, er=er, out=out, listing=listing)
```

and the test (2184-2192, slow-marked):

```python
def test_offload_in_memory_writes_nothing(offload_e2e: SimpleNamespace) -> None:
    assert offload_e2e.listing == []
    report = offload_e2e.er.offload
    assert isinstance(report, OffloadReport)
    assert [c["name"] for c in report.record["cases"]] == ["s1", "f5"]
    assert set(report.runs) == {"s1", "s1__pad", "f5", "pad__offload_stage1"}
```

The fixture passes an empty git dict and a fixed timestamp, calls neither
`check_result_names`, `check_resolved`, `git_info` nor `make_run_dir`, and writes into a
directory `write_run` creates itself. The app's composition adds those four calls and the
failure marker.

How the tests make an experiment small:

| Device | Where | Values |
|---|---|---|
| start from the shipped files | `_raw` 132-136 | experiments/silo_screening_2d.yaml and configs/vehicles/generic_f9_class_2d.yaml read with `yaml.safe_load`; there is no toy vehicle |
| trim | `_experiment` 185-194, `_searched_experiment` 2139-2162 | keep only the variant `silo_cold`; drop `sweeps` and `bounds` |
| small searched grid | `SMALL_GRID` 2129-2134 | `gamma_grid_deg: [18.0, 28.0, 2.0]` (6 points against the shipped `[8, 36, 2]`, 15 points), `gamma_refine_maxiter: 3` (shipped 30), `gamma_refine_halfwidth_deg: 1.0` (shipped 4), `search_rtol: 1.0e-9` (shipped 1e-8; CLAUDE.md's test rule) |
| payload near capacity | 2147 | `veh["payload_mass_t"]["value"] = 26.0`, so the payload brackets close at once |
| coarse sampling | 2146 | `exp["baseline"]["integrator"]["sample_dt_s"] = 0.5` (shipped 0.05) |
| block | 2152-2161 | `s1` solved in stage 1 with a paired pad, `f5` fixed at 5 %, `pad_control: True`, `sensitivity_of: ["s1"]`, the test energy block `_energy()` 149-153 |
| no search at all | tests/test_planar_pipeline.py `_fixed` 110-126, `fast_experiment` 129-139 | `figure_of_merit: none`, `fixed_gamma_star_deg: 20.0`, `fixed_ltg_a: 0.756790`, `fixed_ltg_b_per_s: 2.19338e-3`, `sample_dt_s: 0.5`; the fast tier's end-to-end experiment |
| no simulation | the `fake_sim` fixture 1554-1599 | replaces `sim.run_resolved`, `rerun_resolved`, `matched_run`, `solve_resolved_offload`, `offload_run_result` and `results_io.attributed_comparison` with fakes |

Limits: an offload block needs `figure_of_merit: payload` (the refusal "fixed guidance",
tests/test_offload_pipeline.py 435), so a fixed-guidance launch cannot carry a block.

Cost of a real launch for tests/test_app.py, measured today through the app's composition:

- fixed guidance, pad and silo_cold, sample_dt 0.5 s, no plots, resolve to summary.md:
  1.51 s. Fits the fast tier (under 5 s).
- small searched grid with a block of one stage-1 solve and the pad control
  (`rp_probe_offload.py`): 124.6 s in total under load (pad 27.7 s, silo_cold 21.5 s,
  comparison and offload pass 67.9 s, writing 0.38 s). Slow tier. The same searched pad
  took 12.2 s in an earlier probe on a less loaded machine.

Both need the shared blocks to be changed (the search block, the sampling interval, the
vehicle payload), which the form cannot do. So the function that runs a launch has to take
the template experiment dict and the vehicle dict as arguments.

On that small grid the stage-1 pad control ended `no_offload` with `consistency: fail`
(12 evaluations), as the SP1 test allows (tests/test_offload_pipeline.py 2264-2274: "on
this small grid it may fail"); the summary then carries a blocked-findings line for the
pad control. A test on the small grid must not assert a passing control. The solve itself
was ok (x* 41,255.7 kg, 29 evaluations, verification passed).

## 10. Run times, recorded and measured

Recorded:

| Item | Time | Source |
|---|---|---|
| searched pad of silo_screening_2d, uncapped | 9.3 s in `sim.run_resolved` (search 9.2 s, `simulate_planar` 0.16 s); import of `launchsim.sim` 1.6 s; loading the experiment 0.1 s; writing files and plots 1.2 s | docs/physics.md 2796 |
| searched runs with the 2 s planar cap | pad 12.1 s, silo_cold 14.1 s, silo_cold_lag 24.7 s (26.5 s in the review) | docs/physics.md 2916 |
| "a planar run takes 7-25 s" | | docs/process/SESSION_PROTOCOL.md 406; phase file 5.6 |
| stage-1 pad control | 27 evaluations, about 30 s | docs/physics.md 2169-2170 |
| silo_cold stage-1 solve with its verification | 42 evaluations plus one payload search: 87 to 89 s at the shipped budget, 92 to 109 s at the test budget (loaded machine) | docs/physics.md 2170-2172 |
| 10x-tightened budget | pad search 75 s; silo_cold offload 45 evaluations, 172 s with verification | docs/physics.md 2174-2175 |
| SP1 step 5 | 89 s per verified stage-1 solve against a design estimate of 33 s | docs/phases/SP1-fuel-offload-planar.md 1271-1273 |
| wall clock per searched run including comparisons, writes and plots | 38 s (calibration re-run, 16 runs in 612 s), 54 s (guidance_trigger_2d), 59 to 81 s per sweep point (silo_screening_2d) | docs/phases/inputs/2026-10-03-sp1-preregistration.md 416-421 |
| pad controls in the estimate | stage 1 about 30 s; stage 2 and both budgeted as a verified solve each, 90 to 110 s | same file, 431-432 |
| SP1's three commands, run side by side | `run` 14.1 min, `sweep` 20.9 min, bridge 2.1 min; sweep points 55 to 68 s apart | docs/physics.md 6090-6096; docs/handoff/NEXT_SESSION.md 313-314 |
| evaluation counts | stage-1 solves 37 to 44, stage 2 63, both 42; pad controls 27, 41, 29 | docs/physics.md 6097-6098 |
| full suite at SP1's close | 1299 passed (1264 fast, 35 slow) in 13 min 8 s | docs/handoff/NEXT_SESSION.md 295 |

No test records a wall time; the only rule is the slow marker above 5 s.

Measured today (loaded machine; Python 3.12.11, numpy 2.5.3, scipy 1.18.1, pandas 3.0.6,
matplotlib 3.11.2):

| Item | Time |
|---|---|
| import of `launchsim.sim` | 1.79 s |
| `resolve_experiment` / `check_result_names` / `check_resolved` / `git_info` | 0.004 / under 0.001 / 0.001 / 0.184 s |
| fixed-guidance run, sample_dt 0.05 s | pad 0.72 s, silo_cold 0.81 s |
| searched pad, shipped budget | 20.8 s (worker thread, polled), 22.7 s (main thread) |
| searched pad and silo_cold, small test grid | 12.2 s and 12.7 s; 27.7 s and 21.5 s in a later probe |
| `sim.matched_run(silo_cold, neighbours=True)` | 2.3 s |
| stage-1 pad control, small grid | 8.3 s (12 evaluations, no_offload, no verification) |
| stage-1 solve of silo_cold, small grid | 33.4 s (29 evaluations) plus 23.4 s for the verification search |
| `sim.offload_run_result` | 0.1 and 0.4 s |
| `write_run` | 0.59 s (2 runs at 0.05 s), 0.38 s (4 runs at 0.5 s); with plots 2.61 s and 6.94 s |

Sequence of the seam calls in the offload launch (`rp_probe_offload.log`), which is also
the list a finer progress line could show: `run_resolved(pad)`, `run_resolved(silo_cold)`,
`matched_run(pad)`, `matched_run(silo_cold)`, `matched_run(pad)`,
`solve_resolved_offload(pad, stage1)`, `offload_run_result(pad__offload_stage1)`,
`solve_resolved_offload(silo_cold_s1, stage1)`, `run_resolved(silo_cold_s1)` (the
verification search), `offload_run_result(silo_cold_s1)`. Written runs: `pad`, `silo_cold`,
`pad__offload_stage1`, `silo_cold_s1`.

Note for exit criterion 9's counting stub: `sim.run_resolved` is called for runs other
than the baseline that are pad-derived (the verification of an ok pad control, a paired
pad `<case>__<baseline>`), so the stub must count calls whose argument is
`resolved.baseline`, not calls whose name contains "pad".

## 11. Where the phase file and HEAD disagree

1. Section 6, "Run path" table: `_resolved_config_dict` is given at results_io.py 588. The
   definition is at 590 (587 is the section comment); it was at 590 at b3150c1 too.
2. Section 5.6, "What is not cached": "solves a pad control per solve mode on every pass
   (...; about 30 s each)". About 30 s is the stage-1 control, which ends no_offload and
   has no verification (docs/physics.md 2169-2170). A stage-2 or both control is a solve
   of 41 or 29 evaluations (docs/physics.md 6098) that is verified when ok (results_io.py
   1519-1522) and was budgeted at 90 to 110 s each (pre-registration 431-432).
3. Section 5.6, "Progress" and "What is not cached": a finer progress line "needs a
   callback in results_io.py or offload.py" and caching the pad controls "needs a hook in
   `planar_offload`". Both are reachable without touching either file through the
   call-time seams on `sim` (sim.py 34-45; results_io.py 1131, 1178), as the probe showed.
   That route is a process-wide patch and is not recommended, but the "needs" is not
   strictly true.
4. Section 5.6, run-path item: the shared blocks to copy are listed as "site,
   target_orbit, guidance, search, checks, the baseline's integrator". `dynamics` is a
   shared block too (config.py 162-166, `RUN_SHARED_KEYS = ("dynamics", "site")`) and a
   planar experiment needs it; and `ExperimentConfig` requires `vehicle` as a path string
   (config.py 1864) although `resolve_experiment` takes the vehicle dict separately.
5. Section 5.6, the list of pieces the app composes omits `utc_timestamp`
   (results_io.py 359), needed for the `timestamp_utc` argument (run_experiment 844).
6. Section 6, "Animate" and "Replay" tables (outside the run path; the phase file expects
   this re-check): plots.py has 1,881 lines, not 1,701, and its symbols moved
   (`AnimationError` 312, `CALIBRATION_RECORDS` 507, `_read_json` 627, `calibration_caveat`
   1128, `write_ascent_animation` 1818); replay.py has 1,244 lines, not 1,246. The import
   at results_io.py 143 (`from launchsim.plots import CALIBRATION_RECORDS, write_plots`)
   and its use at 1798 are as stated.

Everything else checked in sections 3, 5.1, 5.6 and the "Run path" table matches HEAD:
cli.py 254-276, 272, 273, 377-414, 491-510; results_io.py 234, 186, 187, 276, 292, 365,
400, 567, 167, 605, 613, 625, 667, 676, 687, 793-889 (830-831, 834, 836, 886-887), 960,
999, 1687, 1973-2027, 2120, 2143; sim.py 876, 896, 932, 1708, 1717, 1728; offload.py 307,
472; config.py 157-159, 1865, 1948-1987, 2346, 2470, 2483, 2816-2898; summary.py 1491,
1500, 1897, 2008, 2021; compare.py 1639, 1657; tests/test_offload_pipeline.py 2165-2181,
2185, 2291.

## 12. Consequences for the design

1. Compose in app.py, in this order: `resolve_experiment(exp_dict, vehicle_dict)`;
   `check_result_names(resolved)`; `sim.check_resolved(resolved)` (catch `ValueError` for
   the three: a refusal, nothing written); `git = sim.git_info(repo_root)`;
   `now = datetime.now(UTC)`; `out_dir = make_run_dir(results_root, resolved.experiment.name, now=now)`;
   then inside `try`: the baseline from the cache or `sim.run_resolved(resolved.baseline)`;
   `variants = {name: sim.run_resolved(run) ...}`;
   `er = planar_experiment_result(resolved, baseline, variants, git, utc_timestamp(now), sensitivity=True, run_cases=True, offload=True)`;
   `write_run(er, out_dir, plots)`; and `except BaseException as exc: write_failure_marker(out_dir, exc)`.
   results_io.py stays unchanged.
2. Cache the baseline `RunResult` under the full-dict key of section 3.4 and re-wrap it on
   every hit with this launch's `resolved.baseline`. Do not hand the cached object in
   verbatim (section 3.1) and do not use `trajectory_key` plus `rerun_resolved`.
3. Worker thread. It is safe, the server stays responsive (16 ms median, 99 ms worst), and
   a child process could not share the cache because `RunResult` does not pickle. Catch
   `BaseException` in the job; decide daemon or not knowing that a killed worker leaves a
   directory with neither summary.md nor FAILED.txt; the run browser needs that third
   state (incomplete) and should list a directory as playable only when summary.md exists.
4. Exploratory marking: `label: exploratory` set in the app's experiment dict, plus a
   banner branch at summary.py 2021. It reaches resolved_config.yaml, metrics.json and
   summary.md with no results_io.py change and moves no pin.
5. Server-start git state: extra keys of the app's copy of the git dict (plain types
   only). They reach both data files. For summary.md, extend `provenance_lines` to print
   them when present, or say it in the exploratory banner. Do not change `git_info`.
6. Progress: the coarse stages of section 7.1, with the expected work read from
   `resolved.offload` before the opaque stage starts and the elapsed time. If the user
   wants more, add an optional `progress` keyword to `planar_experiment_result` and
   `planar_offload` rather than patching the `sim` seams.
7. Plots cost 1 to 2 s per written run. Writing them by default is affordable; the scene
   does not read them.
8. Address a directory by its directory name. `timestamp_utc` in the files lacks the `-2`
   suffix of a collision.
9. The launch function takes the template experiment dict, the vehicle dict, the results
   root and the repository root as arguments, so that tests can pass a fixed-guidance
   template (1.5 s, fast tier) or the small searched grid (about 1 to 2 min, slow tier),
   and so that the server decides once where the committed template lives (a repository
   checkout is required: experiments/ and configs/ do not ship in the package).
10. Refusal messages: condense the `ValueError` yourself; `cli.load_experiment`'s text is
    multi-line.
11. Always create the directory with `make_run_dir`; `write_run` alone would write into an
    existing directory.
12. Copy `dynamics` with the other shared blocks, and set `name` (the directory under the
    results root) and `vehicle` (a string) in the dict.
