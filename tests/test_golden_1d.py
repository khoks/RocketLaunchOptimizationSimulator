"""Golden test of the 1-D reference (plan build step 15).

Two golden sets under tests/data/golden were captured from the CLI at a commit whose
src/, configs/, experiments/, pyproject.toml and uv.lock equal 104ea07 (the Phase 1
commit; see each manifest.json), before any Phase 2 source change:

- silo_screening_1d: the run and sweep of experiments/silo_screening_1d.yaml;
- vertical_1d_paths: tests/data/golden/inputs/vertical_1d_paths.yaml, the vertical_1d
  paths the Phase 1 experiment never reaches (staging and stage 2, the coast to apex, a
  pad no_liftoff, drive_limit, ignition after release with a fall-back).

These tests re-run the entry points in-process (plots off) and compare them with the
golden sets in two tiers (tests/golden_1d_support.py states exactly what each covers):

- tolerant (always on): every pinned file and object; JSON floats within rel 1e-12 /
  abs 1e-9; strings, keys (and key order), ints, bools, CSV headers, the sign of v_mps
  and the resolved inputs exactly; the set of output files exactly. It is not
  environment-robust: CSV and summary cells are effectively exact at their printed
  precision, and a 1-ulp change of the floating-point path moves integrated results by
  more than 1e-12, so after a dependency or platform change that alters floating-point
  results both tiers fail (never loosen the tolerances);
- exact (only when the environment matches the manifest's exact_env_keys; skipped with
  the reason otherwise, failed instead when LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1): every
  non-PNG output file byte for byte (sha256 of its provenance-stripped, LF text) and
  the object dumps bit for bit. Only this tier catches a sub-tolerance change such as a
  reordered sum; the step 16-17 gates therefore run with LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1.

The PNG file names are pinned by a slow test (the bytes are not reproducible).

A failure here means the 1-D model or its reporting changed. The golden sets are never
edited to make a refactor pass; recapture refuses to run unless the guarded sources
equal 104ea07.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from launchsim import cli, sim
from launchsim.config import ResolvedExperiment


def _load_support() -> ModuleType:
    """The sibling helper module, loaded by path so the test collects under any pytest
    import mode (prepend or importlib)."""
    name = "golden_1d_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gs = _load_support()

MANIFESTS: dict[str, dict[str, Any]] = {
    name: gs.read_manifest(gset.golden_dir) for name, gset in gs.GOLDEN_SETS.items()
}
MAX_REPORTED = 25  # differences listed in a failure message


class GoldenRuns:
    """Lazy, cached in-process runs of each golden set (plots off, one per set per
    module) with their object dumps and output digests."""

    def __init__(self, factory: pytest.TempPathFactory) -> None:
        self._factory = factory
        self._runs: dict[str, tuple[ResolvedExperiment, dict[str, tuple[Any, Path]]]] = {}
        self._digests: dict[tuple[str, str], dict[str, str]] = {}

    def _get(self, name: str) -> tuple[ResolvedExperiment, dict[str, tuple[Any, Path]]]:
        if name not in self._runs:
            root = self._factory.mktemp(f"golden_{name}")
            self._runs[name] = gs.run_in_process(gs.GOLDEN_SETS[name], root)
        return self._runs[name]

    def run_dir(self, name: str, section: str) -> Path:
        """The run directory of one section."""
        return self._get(name)[1][section][1]

    def objects(self, name: str, section: str) -> Any:
        """The fresh object dump of one section, in the golden objects.json layout."""
        resolved, outputs = self._get(name)
        output, run_dir = outputs[section]
        return gs.section_objects(section, output, run_dir, resolved.baseline.vehicle_dict)

    def digests(self, name: str, section: str) -> dict[str, str]:
        """output_digests of one section's run directory (computed once)."""
        key = (name, section)
        if key not in self._digests:
            self._digests[key] = gs.output_digests(self.run_dir(name, section))
        return self._digests[key]


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> GoldenRuns:
    """The in-process golden runs of this module."""
    return GoldenRuns(tmp_path_factory)


def _report(problems: list[str]) -> str:
    more = len(problems) - MAX_REPORTED
    tail = [f"... and {more} more"] if more > 0 else []
    return "\n".join([*problems[:MAX_REPORTED], *tail])


def _golden_objects(name: str, section: str) -> Any:
    path = gs.GOLDEN_SETS[name].golden_dir / section / gs.OBJECTS_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def _exact_gate(name: str) -> None:
    """Skip (or, with LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1, fail) outside the capture
    environment of golden set ``name``."""
    status, reason = gs.exact_tier_status(MANIFESTS[name]["environment"], os.environ)
    if status == "fail":
        pytest.fail(reason)
    if status == "skip":
        pytest.skip(reason)


SET_SECTIONS = [
    pytest.param(name, section, id=f"{name}/{section}")
    for name, gset in gs.GOLDEN_SETS.items()
    for section in gset.sections
]
SET_NAMES = pytest.mark.parametrize("name", list(gs.GOLDEN_SETS))
SECTION_PARAMS = pytest.mark.parametrize(("name", "section"), SET_SECTIONS)


def _file_params() -> list[Any]:
    return [
        pytest.param(name, section, fname, id=f"{name}/{section}/{fname}")
        for name, gset in gs.GOLDEN_SETS.items()
        for section in gset.sections
        for fname in MANIFESTS[name]["files"][section]
    ]


# ---------------------------------------------------------------- tolerant tier


@pytest.mark.parametrize(("name", "section", "fname"), _file_params())
def test_output_file_matches_golden(name: str, section: str, fname: str, runs: GoldenRuns) -> None:
    """Each pinned output file equals its golden copy (after provenance stripping)."""
    entry = MANIFESTS[name]["files"][section][fname]
    actual = runs.run_dir(name, section) / entry["output"]
    assert actual.is_file(), f"missing output {entry['output']}"
    golden = gs.GOLDEN_SETS[name].golden_dir / section / fname
    problems = gs.compare_file(entry["kind"], actual, golden, fname)
    assert not problems, _report(problems)


@SECTION_PARAMS
def test_objects_match_golden(name: str, section: str, runs: GoldenRuns) -> None:
    """Experiment: per-run status, flags, metrics, loss and assist budgets, assumptions,
    the comparison and every SensitivityRow (with its perturbed baseline). Sweep: every
    point's overrides, run dict, status, flags, metrics, budgets, assumptions and
    comparison."""
    problems = gs.compare_tree(runs.objects(name, section), _golden_objects(name, section))
    assert not problems, _report(problems)


@SECTION_PARAMS
def test_selection_still_covers_every_run_and_point(
    name: str, section: str, runs: GoldenRuns
) -> None:
    """The files the selection picks from a fresh run are exactly the manifest's (a
    run or sweep point that appears or disappears is a change, not a skip)."""
    selection = gs.section_selection(gs.GOLDEN_SETS[name], section, runs.run_dir(name, section))
    picked = {gs.golden_name(rel, kind): rel for rel, (kind, _src) in selection.items()}
    expected = {n: e["output"] for n, e in MANIFESTS[name]["files"][section].items()}
    assert picked == expected


@SECTION_PARAMS
def test_output_file_set_matches_manifest(name: str, section: str, runs: GoldenRuns) -> None:
    """A fresh run writes exactly the non-PNG files the golden digests list (in any
    environment): no output file appears or disappears."""
    assert set(runs.digests(name, section)) == set(MANIFESTS[name][gs.DIGESTS_KEY][section])


@SET_NAMES
def test_golden_directory_holds_exactly_the_manifest(name: str) -> None:
    """No stray or missing golden file: manifest, objects and the listed files."""
    golden_dir = gs.GOLDEN_SETS[name].golden_dir
    on_disk = {p.relative_to(golden_dir).as_posix() for p in golden_dir.rglob("*") if p.is_file()}
    listed = {gs.MANIFEST_NAME}
    for section in gs.GOLDEN_SETS[name].sections:
        listed.add(f"{section}/{gs.OBJECTS_NAME}")
        listed |= {f"{section}/{fname}" for fname in MANIFESTS[name]["files"][section]}
    assert on_disk == listed


@SET_NAMES
def test_experiment_input_is_the_captured_one(name: str) -> None:
    """The experiment file each golden set was captured from is unchanged (the
    supplementary input under tests/data/golden/inputs is not a guarded source path)."""
    gset = gs.GOLDEN_SETS[name]
    manifest = MANIFESTS[name]
    assert manifest["experiment_file"] == gset.experiment_file.relative_to(gs.REPO_ROOT).as_posix()
    assert gs.input_digest(gset.experiment_file) == manifest[gs.INPUT_DIGEST_KEY]


def test_supplementary_set_reaches_the_paths_it_exists_for() -> None:
    """vertical_1d_paths covers what silo_screening_1d does not: the statuses
    no_liftoff and drive_limit, the staging, apex and turnaround events, and stage 2."""
    runs_ = _golden_objects(gs.PATHS_SET.name, gs.EXPERIMENT_SECTION)["runs"]
    statuses = {r["result"]["status"] for r in runs_.values()}
    assert {"nominal", "no_liftoff", "drive_limit"} <= statuses
    events = "".join(
        (gs.PATHS_SET.golden_dir / gs.EXPERIMENT_SECTION / f"{run}/events.csv").read_text(
            encoding="utf-8"
        )
        for run in runs_
    )
    for token in (",staging,", ",apex,", ",turnaround,", ",drive_limit,", ",stage2"):
        assert token in events, token


# ------------------------------------------------------------------- exact tier


@SECTION_PARAMS
def test_exact_output_bytes(name: str, section: str, runs: GoldenRuns) -> None:
    """Every non-PNG output file (all runs, all sweep points: metrics, resolved config,
    summaries, events, time series, sweep indexes) is byte-identical to the capture
    after provenance stripping. Pinned files that differ get an exact diff."""
    _exact_gate(name)
    manifest = MANIFESTS[name]
    run_dir = runs.run_dir(name, section)
    problems = gs.compare_digests(runs.digests(name, section), manifest[gs.DIGESTS_KEY][section])
    pinned = {e["output"]: (n, e["kind"]) for n, e in manifest["files"][section].items()}
    for rel in [p.split(":")[0] for p in problems]:
        if rel in pinned and (run_dir / rel).is_file():
            fname, kind = pinned[rel]
            golden = gs.GOLDEN_SETS[name].golden_dir / section / fname
            problems += gs.compare_file(kind, run_dir / rel, golden, rel, exact=True)
    assert not problems, _report(problems)


@SECTION_PARAMS
def test_exact_objects(name: str, section: str, runs: GoldenRuns) -> None:
    """The object dumps equal the golden bit for bit (every float by repr, so a 1-ulp
    change, a sign flip below 1e-9 or -0.0 against 0.0 fails)."""
    _exact_gate(name)
    golden = _golden_objects(name, section)
    problems = gs.compare_tree(runs.objects(name, section), golden, exact=True)
    assert not problems, _report(problems)


# ------------------------------------------------------------------ plot names (slow)


@pytest.mark.slow
@SET_NAMES
def test_plot_file_names_match_manifest(name: str, tmp_path: Path) -> None:
    """With plots on, the run (and sweep) write exactly the PNG paths the CLI capture
    wrote: no plot appears, disappears, is renamed or moves (bytes not compared)."""
    gset = gs.GOLDEN_SETS[name]
    resolved = cli.load_experiment(gset.experiment_file)
    run_dirs = {
        gs.EXPERIMENT_SECTION: sim.run_experiment(
            resolved, tmp_path, plots=True, repo_root=gs.REPO_ROOT
        )[1]
    }
    if gset.has_sweep:
        run_dirs[gs.SWEEP_SECTION] = sim.run_sweep(
            resolved, tmp_path, plots=True, repo_root=gs.REPO_ROOT
        )[1]
    for section, run_dir in run_dirs.items():
        assert gs.png_files(run_dir) == MANIFESTS[name][gs.PNG_KEY][section], section


# ------------------------------------------------------- the comparator is not vacuous


def test_exact_tier_gate_skips_or_fails_on_request() -> None:
    """The exact tier runs in the capture environment; outside it, it skips unless
    LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1, which turns the skip into a failure."""
    here = gs.environment()
    assert gs.exact_tier_status(here, {}) == ("run", "")
    elsewhere = {**here, "python": "0.0.0"}
    status, reason = gs.exact_tier_status(elsewhere, {})
    assert status == "skip" and "python: 0.0.0 ->" in reason
    status, _reason = gs.exact_tier_status(elsewhere, {gs.REQUIRE_EXACT_ENV_VAR: "0"})
    assert status == "skip"
    status, _reason = gs.exact_tier_status(elsewhere, {gs.REQUIRE_EXACT_ENV_VAR: "1"})
    assert status == "fail"
    assert gs.exact_tier_status(here, {gs.REQUIRE_EXACT_ENV_VAR: "1"}) == ("run", "")


def test_tree_comparator_tolerance_and_types() -> None:
    """Floats pass at rel 1e-13 and fail at rel 1e-11; ints, strings, None and key
    order are exact; resolved inputs and the exact mode compare bits."""
    base = {"a": 1234.5678, "b": 3, "c": "x", "d": None, "e": [0.0, -1.0]}
    assert gs.compare_tree(dict(base), base) == []
    assert gs.compare_tree({**base, "a": 1234.5678 * (1 + 1e-13)}, base) == []
    assert gs.compare_tree({**base, "a": 1234.5678 * (1 + 1e-11)}, base)
    assert gs.compare_tree({**base, "e": [5e-10, -1.0]}, base) == []  # abs 1e-9
    assert gs.compare_tree({**base, "e": [2e-9, -1.0]}, base)
    assert gs.compare_tree({**base, "b": 3.0}, base)  # an int must stay an int
    assert gs.compare_tree({**base, "c": "y"}, base)
    assert gs.compare_tree({**base, "d": 0.0}, base)
    assert gs.compare_tree({"b": 3, "a": 1234.5678, "c": "x", "d": None, "e": [0.0, -1.0]}, base)
    assert gs.compare_tree({k: v for k, v in base.items() if k != "e"}, base)
    assert gs.compare_tree({**base, "e": [0.0]}, base)
    # exact mode: one ulp, a sub-1e-9 sign flip and the sign of zero all fail
    one_ulp = {**base, "a": math.nextafter(1234.5678, math.inf)}
    assert gs.compare_tree(one_ulp, base) == []
    assert gs.compare_tree(one_ulp, base, exact=True)
    assert gs.compare_tree({**base, "e": [-0.0, -1.0]}, base) == []
    assert gs.compare_tree({**base, "e": [-0.0, -1.0]}, base, exact=True)
    assert gs.compare_tree(dict(base), base, exact=True) == []
    # resolved inputs are exact even in the tolerant tier
    inputs = {"run_dict": {"rtol": 1e-10}, "metric": 1e-10}
    assert gs.compare_tree({"run_dict": {"rtol": 1e-10}, "metric": 1e-11}, inputs) == []
    assert gs.compare_tree({"run_dict": {"rtol": 1e-11}, "metric": 1e-10}, inputs)


def test_csv_comparator_pins_header_rows_and_sign() -> None:
    """Header, row count, text cells and the v_mps sign (sign bit included) are exact;
    floats tolerant."""
    golden = "t_s,event,v_mps\n0,release,76.7\n10.4,apex,1.95e-14\n12,stop,0\n"
    assert gs.compare_csv(golden, golden, "g") == []
    assert gs.compare_csv(golden.replace("76.7", "76.70000000000001"), golden, "g") == []
    assert gs.compare_csv(golden.replace("1.95e-14", "-1.95e-14"), golden, "g")
    assert gs.compare_csv(golden.replace("1.95e-14", "0"), golden, "g")
    assert gs.compare_csv(golden.replace("stop,0", "stop,-0"), golden, "g")
    assert gs.compare_csv(golden.replace("v_mps", "speed"), golden, "g")
    assert gs.compare_csv("t_s,event,v_mps\n0,release,76.7\n", golden, "g")
    assert gs.compare_csv(golden.replace("release", "liftoff"), golden, "g")
    assert gs.compare_csv(golden.replace("76.7", "76.70001"), golden, "g")
    assert gs.compare_csv(golden.replace("0,release", ",release"), golden, "g")


def test_summary_normalisation_strips_only_provenance(tmp_path: Path) -> None:
    """Title provenance and the Timestamp/Git bullets go (a multi-line Git error bullet
    whole); any other change is caught."""
    text = (
        "# exp (20260929T161034Z, git d8d6951d8069-dirty)\n\n- Baseline: pad\n"
        "- Timestamp (UTC): 20260929T161034Z\n- Git: d8d6951d8069-dirty\n"
        "- Git error: boom\n\n| a | 1.0 |\n"
    )
    other = text.replace("20260929T161034Z", "20270101T000000Z").replace("-dirty", "")
    multi = text.replace("boom", "fatal: detected dubious ownership\nTo add an exception:\n  x")
    expected = "# exp (<timestamp>, git <label>)\n\n- Baseline: pad\n\n| a | 1.0 |\n"
    assert gs.normalise_summary(text) == expected
    assert gs.normalise_summary(other) == expected
    assert gs.normalise_summary(multi) == expected
    assert gs.normalise_summary(multi.replace("\n  x\n", "\n  x\n- Vehicle: v\n")) == (
        expected.replace("- Baseline: pad\n", "- Baseline: pad\n- Vehicle: v\n")
    )
    golden = tmp_path / "golden.md"
    changed = tmp_path / "changed.md"
    golden.write_text(gs.normalise_summary(text), encoding="utf-8")
    changed.write_text(text.replace("| a | 1.0 |", "| a | 1.00 |"), encoding="utf-8")
    assert gs.compare_file("summary", changed, golden, "s")


def test_record_text_normalisation_and_digests() -> None:
    """metrics.json / resolved_config.yaml text: only the timestamp and git entries are
    replaced (a multi-line git error included); a changed value changes the digest; a
    reformatting or a missing entry is refused (output_digests then never matches)."""
    record = {"experiment": "e", "timestamp_utc": "T1", "git": {"hash": "h"}, "x": 1.5}
    other = {**record, "timestamp_utc": "T2", "git": {"hash": "k", "error": "a\nb"}}
    texts = [json.dumps(r, indent=2) + "\n" for r in (record, other)]
    norm = [gs.normalise_output_text("metrics.json", t) for t in texts]
    assert norm[0] == norm[1]
    assert '"x": 1.5' in norm[0] and "T1" not in norm[0] and '"h"' not in norm[0]
    yaml_texts = [
        "experiment: e\ntimestamp_utc: T1\ngit:\n  hash: h\n  dirty: false\nx: 1.5\n",
        "experiment: e\ntimestamp_utc: T2\ngit:\n  hash: k\n  error: 'a\n\n    b'\nx: 1.5\n",
    ]
    yaml_norm = [gs.normalise_output_text("resolved_config.yaml", t) for t in yaml_texts]
    assert yaml_norm[0] == yaml_norm[1]
    assert yaml_norm[0].endswith("<provenance:git>\nx: 1.5\n")
    changed = gs.normalise_output_text("metrics.json", texts[0].replace("1.5", "1.50"))
    assert gs.text_digest(changed) != gs.text_digest(norm[0])
    with pytest.raises(ValueError):
        gs.normalise_record_text(json.dumps(record, indent=4) + "\n", ".json")
    with pytest.raises(ValueError):
        gs.normalise_record_text(json.dumps({"x": 1}, indent=2), ".json")
