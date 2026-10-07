"""The app's launch function (SP2 step A4; src/launchsim/app.py; design
docs/phases/inputs/2026-10-05-SP2-design.md, section 4.6, D-SP2-10, 11, 12, 25, 26).
Every launch goes to a folder under tmp_path, never to results/.

Fast:

- a real launch on the fixed-guidance basis (sample step 0.5 s, no plots) writes the
  directory ``results_io.run_experiment`` (its defaults, as ``launchsim run``) writes for
  the same resolved experiment, key by key except the git record, the timestamp and the
  directory name; its summary opens with the exploratory banner naming both git states
  (server start dirty, launch clean: dirty), metrics.json and resolved_config.yaml carry
  the label and git.server_start; progress is told the five stages in order; no PNG is
  written; on the edited fixed basis (not committed) the variant is 'silo' and nothing
  is called a reproduction, and the banner says no sensitivity check ran and M5 reads
  n/a; the pad alone launches too, its banner saying there was no push;
- the committed basis (read at HEAD with read-only git): a launch (fake runs) and the
  dry run of the pad say what they reproduce at that commit, and the banner says so with
  the commit; an edited copy of the offload file is never called committed, and a
  commit without the files is one BasisError;
- a refusal writes nothing (the results root is not even created), and so does a launch
  after the code changed and an absurd push (a denormal stroke or acceleration, a
  derived acceleration or exit speed outside the form's ranges); a crash leaves
  FAILED.txt and returns crashed (and a KeyboardInterrupt is re-raised after the marker);
- an imposed offload's banner says it is not propellant saved (and, from stage 2, not
  netted); a no-git server start never reads clean;
- the counting test: two launches with an unchanged baseline fly the baseline once
  (calls of sim.run_resolved whose argument equals the resolved baseline; the pad-derived
  runs of the offload pass, the verification and the paired pad, are other runs);
- a faked-seam offload launch (tests/app_support.py) with a fresh and with a cached pad
  gives the checked runs and offload record of results_io.run_experiment, with no
  rerun_resolved (the cache re-wraps the pad with this launch's resolved baseline);
- an outcome per row of design 4.6's table where it is cheap: complete (with the M5
  check n/a said), flagged (a run flag, a bug_suspect comparison, a pad control's flag,
  and on synthetic directories a bug_suspect decomposition or paired pad, a failed
  pad-control verification and a failed case verification read by the sign of its P* -
  P_ref as the replay reads it), not in orbit (a paired pad short of orbit), did not
  fly (also a stage-2 pad control or a paired pad that did not fly), not in orbit (an
  imposed offload that reaches no orbit), offload found nothing (also a stage-2 solve
  that nets to nothing), crashed (the fresh message is the one the directory gives
  later), refused, incomplete (also a metrics.json cut short);
- the cache key, the git record, code_changed on the repository (read-only git) and
  load_basis.

Slow (one): a real launch on the small searched grid with a stage-1 solve (about one to
two minutes): a complete directory, label exploratory, the banner, git.server_start, the
case ok and verified; nothing is asserted about the pad control's verdict (on this grid
it may fail, as tests/test_offload_pipeline.py notes).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import subprocess
import sys
import threading
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
import yaml

from launchsim import app, appform, results_io, sim, summary
from launchsim.config import resolve_experiment


def _load_support() -> ModuleType:
    """tests/app_support.py, loaded by path (any pytest import mode)."""
    name = "app_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sup = _load_support()

START_HASH = "0123456789ab"
START_DIRTY = {"hash": START_HASH, "dirty": True, "error": None}
LAUNCH_CLEAN = {"hash": START_HASH, "dirty": False, "error": None}
"""Git states of the tests: the server started on a dirty tree, the launch saw it clean."""
NORMALISED = ("git", "timestamp_utc")
"""Top-level keys of metrics.json and resolved_config.yaml that differ between an app
launch and run_experiment by design."""


def _start(git: dict[str, Any] = START_DIRTY, head: str | None = None) -> app.ServerStart:
    """A ServerStart without a HEAD hash (no code check) unless one is given."""
    return app.ServerStart(git=dict(git), head=head)


def _files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def _strip(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k not in NORMALISED}


def _summary_body(text: str) -> list[str]:
    """summary.md without the exploratory banner, the title and the provenance lines."""
    lines = text.splitlines()
    if lines and lines[0].startswith(">"):
        lines = lines[2:]
    return [
        line
        for line in lines
        if not line.startswith(("# ", "- Timestamp (UTC):", "- Git:", "- Git error:"))
    ]


@pytest.fixture(scope="module")
def fixed_launch(tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """The silo_cold preset launched on the fixed-guidance basis (edited, so not
    committed: the variant is 'silo'; server start dirty, launch clean, progress recorded)
    and the same resolved experiment run by results_io.run_experiment (its defaults, as
    ``launchsim run``; no plots), each into its own folder."""
    basis = sup.fixed_basis()
    form = appform.preset_form(basis, "silo_cold")
    root = tmp_path_factory.mktemp("app_root")
    stages: list[tuple[str, dict[str, Any]]] = []
    cache = app.BaselineCache()
    with pytest.MonkeyPatch.context() as mp:
        sup.git_states(mp, LAUNCH_CLEAN)
        outcome = app.run_launch(
            basis,
            form,
            results_root=root,
            repo_root=sup.REPO_ROOT,
            cache=cache,
            server_start=_start(),
            progress=lambda stage, info: stages.append((stage, info)),
        )
        resolved = resolve_experiment(appform.build_experiment(basis, form), basis.vehicle_copy())
        cli_root = tmp_path_factory.mktemp("cli_root")
        _, cli_dir = results_io.run_experiment(
            resolved, cli_root, plots=False, repo_root=sup.REPO_ROOT
        )
    return SimpleNamespace(
        basis=basis,
        form=form,
        outcome=outcome,
        stages=stages,
        cli_dir=cli_dir,
        root=root,
        cache=cache,
    )


# ------------------------------------------------------------------ the composition


def test_a_launch_writes_what_run_experiment_writes(fixed_launch: SimpleNamespace) -> None:
    """The app's directory and run_experiment's for the same resolved experiment: the
    same files; metrics.json and resolved_config.yaml equal key by key but for git and
    timestamp_utc; every CSV byte-equal; summary.md equal but for the banner, the title
    and the provenance lines (the sensitivity note included: none declared, as
    ``launchsim run`` writes it). The directory is results_root/app/<timestamp>. The
    command-line run of the exploratory label, with no server-start record, says it was
    not launched from the app."""
    out = fixed_launch.outcome.out_dir
    cli = fixed_launch.cli_dir
    assert out.parent == fixed_launch.root / "app" and cli.parent.name == "app"
    assert _files(out) == _files(cli)
    for name in ("metrics.json",):
        mine = json.loads((out / name).read_text(encoding="utf-8"))
        theirs = json.loads((cli / name).read_text(encoding="utf-8"))
        assert _strip(mine) == _strip(theirs)
        assert set(mine) == set(theirs)
    mine = yaml.safe_load((out / "resolved_config.yaml").read_text(encoding="utf-8"))
    theirs = yaml.safe_load((cli / "resolved_config.yaml").read_text(encoding="utf-8"))
    assert _strip(mine) == _strip(theirs) and list(mine) == list(theirs)
    for rel in _files(out):
        if rel.endswith(".csv"):
            assert (out / rel).read_bytes() == (cli / rel).read_bytes(), rel
    mine_text = (out / "summary.md").read_text(encoding="utf-8")
    cli_text = (cli / "summary.md").read_text(encoding="utf-8")
    assert _summary_body(mine_text) == _summary_body(cli_text)
    assert "(no sensitivity block declared;" in mine_text and "--no-sensitivity" not in mine_text
    cli_banner = cli_text.splitlines()[0]
    assert cli_banner.startswith(summary.EXPLORATORY_NOT_APP_HEAD)
    assert "reproduction" not in cli_banner
    assert summary.EXPLORATORY_NO_ANCHOR_TEXT not in cli_banner
    assert summary.EXPLORATORY_UNCOMMITTED_BASIS_TEXT not in cli_banner
    assert mine_text.splitlines()[0].startswith(summary.EXPLORATORY_BANNER_HEAD)
    assert not (out / "plots").exists() and not (out / results_io.FAILED_MARKER).exists()


def test_the_summary_banner_and_both_git_states(fixed_launch: SimpleNamespace) -> None:
    """summary.md opens with the exploratory banner (D-SP2-12) naming the server-start
    commit dirty and the working tree at launch clean; that no sensitivity check ran
    (the Sensitivity line's cd_scale pointer is not this directory's); on this basis,
    not read from a commit, that no name is called a reproduction (D-SP2-36); that M5
    reads n/a with one variant; the title's git label is dirty (either state dirty);
    metrics.json and resolved_config.yaml carry label exploratory, git.server_start,
    git.launch_dirty, the code-check note and no basis commit."""
    out = fixed_launch.outcome.out_dir
    text = (out / "summary.md").read_text(encoding="utf-8")
    banner, blank, title = text.splitlines()[:3]
    assert banner.startswith("> **EXPLORATORY app run, not a finding.**") and blank == ""
    assert (
        f"Code: the commit imported at server start ({START_HASH}, dirty); working tree at "
        "launch: clean." in banner
    )
    assert "not pre-registered" in banner
    assert "Do not cite; findings are in docs/findings/." in banner
    assert "Calibration +14.3%, no structural mass for the push, fixed guidance, unthrottled." in (
        banner
    )
    assert banner.endswith(
        f"{summary.EXPLORATORY_NO_SENSITIVITY_TEXT} {summary.EXPLORATORY_UNCOMMITTED_BASIS_TEXT} "
        f"{summary.EXPLORATORY_NO_ANCHOR_TEXT}"
    )
    assert "not new evidence" not in banner and "(no sensitivity block declared;" in text
    assert "a reproduction, not new evidence" in summary.EXPLORATORY_REPRODUCTION_TEXT
    assert "silo_<tag>__pad" in summary.EXPLORATORY_REPRODUCTION_TEXT
    assert title.startswith("# app (") and title.endswith(f"git {START_HASH}-dirty)")
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    config = yaml.safe_load((out / "resolved_config.yaml").read_text(encoding="utf-8"))
    for record in (metrics, config):
        assert record["label"] == "exploratory"
        git = record["git"]
        assert git["server_start"] == START_DIRTY and git["dirty"] is True
        assert git["launch_dirty"] is False and git["hash"] == START_HASH
        assert git["code_check"] == app.CODE_CHECK_SKIPPED
        assert git[summary.EXPLORATORY_BASIS_COMMIT_KEY] is None


def test_the_pad_alone_launches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The pad preset (survey 03 section 8: the unlabelled baseline-only write was never
    executed): complete, metrics.json runs only the pad with label exploratory,
    resolved_config.yaml runs only the pad, summary.md opens with the exploratory banner,
    which calls it a pad launch with no push (never 'structural mass for the push'), and
    says '(no variants)' and has no M5 sentence; no FAILED.txt and no plots/; nothing
    reproduced on this edited basis; on the committed basis the dry run of the pad says it
    is the committed baseline: a reproduction (D-SP2-36)."""
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.fixed_basis()
    outcome = app.run_launch(
        basis,
        appform.preset_form(basis, "pad"),
        results_root=tmp_path,
        repo_root=sup.REPO_ROOT,
        cache=app.BaselineCache(),
        server_start=_start(),
    )
    assert outcome.kind == app.OUTCOME_COMPLETE, outcome
    assert outcome.message.startswith("complete: pad reached the target orbit")
    assert outcome.reproduces == ()
    out = outcome.out_dir
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert list(metrics["runs"]) == ["pad"] and metrics["label"] == "exploratory"
    config = yaml.safe_load((out / "resolved_config.yaml").read_text(encoding="utf-8"))
    assert list(config["runs"]) == ["pad"] and config["label"] == "exploratory"
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert text.startswith(summary.EXPLORATORY_BANNER_HEAD) and "(no variants)" in text
    banner = text.splitlines()[0]
    assert f", {summary.EXPLORATORY_NO_PUSH_CAVEAT}, fixed guidance, unthrottled." in banner
    assert summary.EXPLORATORY_PUSH_CAVEAT not in banner
    assert summary.EXPLORATORY_NO_ANCHOR_TEXT not in banner
    assert not (out / results_io.FAILED_MARKER).exists() and not (out / "plots").exists()
    shipped = sup.shipped_basis()
    values = app.dry_run(shipped, appform.preset_form(shipped, "pad"))
    assert isinstance(values, dict)
    assert values["reproduces"] == [
        f"pad: the committed baseline of experiments/silo_offload_2d.yaml and "
        f"experiments/silo_screening_2d.yaml at commit {shipped.commit[:12]}: "
        f"{app.REPRODUCTION_TAIL}"
    ]


def test_an_imposed_offload_is_not_called_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit criterion 7 and D-SP2-27 in summary.md (SP1's section title is printed for
    any offload block): a launch of silo_cold_fix5pct says in its banner that an imposed
    offload is not propellant saved; an Advanced imposed stage-2 offload adds that it is
    not netted (no pad control); a stage-1 solve's banner says neither."""
    sup.install_fake_sim(monkeypatch)
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.searched_basis()
    common = dict(repo_root=sup.REPO_ROOT, cache=app.BaselineCache(), server_start=_start())
    fix5 = appform.preset_form(basis, "silo_cold_fix5pct")
    s2 = dataclasses.replace(fix5, fixed_key="stage2_fraction", advanced=True)
    banners = {}
    for name, form in (
        ("fix5", fix5),
        ("s2", s2),
        ("s1", dataclasses.replace(appform.preset_form(basis, "silo_cold_s1"), paired_pad=False)),
    ):
        outcome = app.run_launch(basis, form, results_root=tmp_path / name, **common)
        assert outcome.kind == app.OUTCOME_COMPLETE, outcome
        text = (outcome.out_dir / "summary.md").read_text(encoding="utf-8")
        banners[name] = text.splitlines()[0]
    assert banners["fix5"].endswith(summary.EXPLORATORY_IMPOSED_TEXT)
    assert summary.EXPLORATORY_IMPOSED_NOT_NETTED_TEXT not in banners["fix5"]
    assert banners["s2"].endswith(
        f"{summary.EXPLORATORY_IMPOSED_TEXT} {summary.EXPLORATORY_IMPOSED_NOT_NETTED_TEXT}"
    )
    assert "imposed" not in banners["s1"].lower() and "netted" not in banners["s1"]


def test_progress_is_told_the_five_stages_in_order(fixed_launch: SimpleNamespace) -> None:
    """progress(stage, info): the five STAGES in order, the elapsed time non-decreasing,
    the expected range from the pad stage on, the pad stage saying it ran (not cached)."""
    stages = fixed_launch.stages
    assert [s for s, _ in stages] == list(app.STAGES)
    elapsed = [info["elapsed_s"] for _, info in stages]
    assert elapsed == sorted(elapsed) and elapsed[0] >= 0.0
    assert stages[0][1]["expected_s"] is None
    assert all(info["expected_s"] is not None for _, info in stages[1:])
    assert stages[1][1]["cached"] is False and stages[2][1]["runs"] == ["silo"]


def test_the_fixed_launch_did_not_reach_orbit(fixed_launch: SimpleNamespace) -> None:
    """The fixed-guidance silo preset ends off target (it flies the pad's LTG pair):
    the outcome not_in_orbit, with the pad and the result kept in memory; the basis is
    edited (not committed), so the variant is 'silo' and nothing is called a
    reproduction (D-SP2-31, 36); its M5 check reads n/a (one variant per launch)."""
    outcome = fixed_launch.outcome
    assert outcome.kind == app.OUTCOME_NOT_IN_ORBIT
    assert outcome.message == "silo did not reach the target orbit: off_target"
    assert outcome.result is not None and outcome.expected_s is not None
    assert len(fixed_launch.cache) == 1
    assert outcome.reproduces == ()
    metrics = json.loads((outcome.out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["comparison"]["silo"]["checks_m5"]["status"] == "n/a"


# ------------------------------------------------------------------ refusals and crashes


def test_a_refusal_writes_nothing(tmp_path: Path) -> None:
    """A refused form (a ramp start below the shaft floor) and a launch after the code
    changed (code_changed patched) return refused and leave the results root unmade."""
    basis = sup.fixed_basis()
    root = tmp_path / "results"
    bad = dataclasses.replace(
        appform.preset_form(basis, "silo_cold"), ramp_by="depth", t_ign_s=None, at_depth_m=150
    )
    kwargs = dict(results_root=root, repo_root=sup.REPO_ROOT, cache=app.BaselineCache())
    outcome = app.run_launch(basis, bad, server_start=_start(), **kwargs)
    assert outcome.kind == app.OUTCOME_REFUSED and outcome.field == "at_depth_m"
    assert outcome.out_dir is None and "deeper" in outcome.message
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(app, "code_changed", lambda repo_root, start: True)
        ok_form = appform.preset_form(basis, "silo_cold")
        outcome = app.run_launch(basis, ok_form, server_start=_start(), **kwargs)
    assert outcome.kind == app.OUTCOME_REFUSED and outcome.message == app.CODE_CHANGED_MESSAGE
    assert not root.exists()


def test_an_absurd_push_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    """Pushes that pass each field's own range but hang or crash the track phase (A4
    numerics review) are refused before anything is written, even when the form bypasses
    the request parser: a 1e-9 m and a 1e-300 m stroke under silo_cold_200m's exit speed,
    a 5e-324 g0 net acceleration, a 1 m stroke at that exit speed (300 g0 derived) and 20
    g0 over 1000 m (626 m/s derived). The dry run refuses them too, and never returns a
    value that is not finite."""
    basis = sup.fixed_basis()
    cold = appform.preset_form(basis, "silo_cold")
    long = appform.preset_form(basis, "silo_cold_200m")
    root = tmp_path / "results"
    cases = [
        (dataclasses.replace(long, stroke_m=1e-9), "stroke_m"),
        (dataclasses.replace(long, stroke_m=1e-300), "stroke_m"),
        (dataclasses.replace(cold, net_accel_g=5e-324), "net_accel_g"),
        (dataclasses.replace(long, stroke_m=1.0), "exit_speed_mps"),
        (dataclasses.replace(cold, stroke_m=1000, net_accel_g=20), "net_accel_g"),
    ]
    for form, field in cases:
        outcome = app.run_launch(
            basis,
            form,
            results_root=root,
            repo_root=sup.REPO_ROOT,
            cache=app.BaselineCache(),
            server_start=_start(),
        )
        assert outcome.kind == app.OUTCOME_REFUSED and outcome.field == field, outcome
        assert outcome.out_dir is None and "range" in outcome.message
        refusal = app.dry_run(basis, form)
        assert isinstance(refusal, appform.Refusal) and refusal.field == field
        request = appform.form_to_request(form)
        parsed = appform.parse_request(json.loads(json.dumps(request)))
        assert isinstance(parsed, appform.Refusal) and parsed.field == field
    assert not root.exists()
    values = app.dry_run(basis, cold)
    assert isinstance(values, dict)
    json.dumps(values, allow_nan=False)
    assert values["reproduces"] == []


def test_a_crash_writes_the_failed_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception in a run leaves FAILED.txt (no summary.md) and returns crashed with
    the marker's last line (its type and message for a one-line message), the line the
    directory classifies with later, also for a message of two lines; a
    KeyboardInterrupt writes the marker and is re-raised; a raising progress callback
    never stops the launch."""
    basis = sup.fixed_basis()
    form = appform.preset_form(basis, "silo_cold")
    sup.git_states(monkeypatch, LAUNCH_CLEAN)

    def boom(resolved: Any) -> Any:
        raise RuntimeError("boom in the run")

    def bad_progress(stage: str, info: dict[str, Any]) -> None:
        raise ValueError("display broke")

    monkeypatch.setattr(sim, "run_resolved", boom)
    common = dict(repo_root=sup.REPO_ROOT, cache=app.BaselineCache(), server_start=_start())
    outcome = app.run_launch(
        basis, form, results_root=tmp_path / "a", progress=bad_progress, **common
    )
    assert outcome.kind == app.OUTCOME_CRASHED
    assert outcome.message == "RuntimeError: boom in the run"
    marker = outcome.out_dir / results_io.FAILED_MARKER
    assert marker.is_file() and not (outcome.out_dir / "summary.md").exists()
    assert app.classify(outcome.out_dir)[:2] == (app.OUTCOME_CRASHED, outcome.message)

    def two_lines(resolved: Any) -> Any:
        raise RuntimeError("line one\nline two")

    monkeypatch.setattr(sim, "run_resolved", two_lines)
    outcome = app.run_launch(basis, form, results_root=tmp_path / "c", **common)
    assert outcome.kind == app.OUTCOME_CRASHED
    assert outcome.message == app.classify(outcome.out_dir)[1] == "line two"

    def interrupt(resolved: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(sim, "run_resolved", interrupt)
    with pytest.raises(KeyboardInterrupt):
        app.run_launch(basis, form, results_root=tmp_path / "b", **common)
    (folder,) = (tmp_path / "b" / "app").iterdir()
    assert (folder / results_io.FAILED_MARKER).is_file()


# ------------------------------------------------------------------ the cached pad


def test_two_launches_fly_the_baseline_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit criterion 9 on fake runs: a stage-1 solve with its paired pad, then a fixed
    offload, on an unchanged baseline: sim.run_resolved is called once with an argument
    equal to the resolved baseline; the pad-derived runs (the verification of the case,
    the paired pad) are other runs; the second launch's pad stage says cached."""
    state = sup.install_fake_sim(monkeypatch)
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.searched_basis()
    cache = app.BaselineCache()
    stages: list[tuple[str, dict[str, Any]]] = []
    for name in ("silo_cold_s1", "silo_cold_fix5pct"):
        outcome = app.run_launch(
            basis,
            appform.preset_form(basis, name),
            results_root=tmp_path,
            repo_root=sup.REPO_ROOT,
            cache=cache,
            server_start=_start(),
            progress=lambda stage, info: stages.append((stage, info)),
        )
        assert outcome.kind == app.OUTCOME_COMPLETE, outcome
    resolved = resolve_experiment(
        appform.build_experiment(basis, appform.preset_form(basis, "silo_cold")),
        basis.vehicle_copy(),
    )
    baseline_calls = [r for r in state.ran if r == resolved.baseline]
    assert len(baseline_calls) == 1
    assert any("pad" in r.name and r != resolved.baseline for r in state.ran)
    pads = [info["cached"] for stage, info in stages if stage == app.STAGE_PAD]
    assert pads == [False, True] and len(cache) == 1


def _offload_record(er: results_io.ExperimentResult) -> str:
    return json.dumps(er.offload.record, sort_keys=True, default=str)


def test_an_offload_launch_with_a_fresh_and_a_cached_pad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The silo_cold_s1 preset on the committed basis and fake runs, launched with an
    empty cache, again with
    the pad cached, and run by results_io.run_experiment: the same checked runs and the
    same offload record all three ways, and rerun_resolved never called (the cached pad
    is re-wrapped with each launch's resolved baseline, so results_io's identity tests
    take the CLI's branch)."""
    state = sup.install_fake_sim(monkeypatch)
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.shipped_basis()
    form = appform.preset_form(basis, "silo_cold_s1")
    cache = app.BaselineCache()
    common = dict(repo_root=sup.REPO_ROOT, cache=cache, server_start=_start())
    fresh = app.run_launch(basis, form, results_root=tmp_path / "a", **common)
    cached = app.run_launch(basis, form, results_root=tmp_path / "b", **common)
    resolved = resolve_experiment(appform.build_experiment(basis, form), basis.vehicle_copy())
    er, _ = results_io.run_experiment(
        resolved, tmp_path / "c", plots=False, repo_root=sup.REPO_ROOT
    )
    assert fresh.result is not None and cached.result is not None
    for launch in (fresh.result, cached.result):
        assert set(launch.offload.checked_runs) == set(er.offload.checked_runs)
        assert set(launch.offload.runs) == set(er.offload.runs)
        assert _offload_record(launch) == _offload_record(er)
    assert set(er.offload.runs) == {"silo_cold_s1", "silo_cold_s1__pad", "pad__offload_stage1"}
    assert state.reruns == 0
    assert cached.result.baseline.resolved is not fresh.result.baseline.resolved
    for outcome in (fresh, cached):
        metrics = json.loads((outcome.out_dir / "metrics.json").read_text(encoding="utf-8"))
        assert metrics["offload"]["pad_control"] is True and metrics["label"] == "exploratory"


# ------------------------------------------------------------------ outcomes


def _fake_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, preset: str, **state_changes: Any
) -> app.LaunchOutcome:
    state = sup.install_fake_sim(monkeypatch)
    for key, value in state_changes.items():
        setattr(state, key, value)
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.shipped_basis()
    return app.run_launch(
        basis,
        appform.preset_form(basis, preset),
        results_root=tmp_path,
        repo_root=sup.REPO_ROOT,
        cache=app.BaselineCache(),
        server_start=_start(),
    )


def test_outcome_did_not_fly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A variant whose search failed (no recorded run): did_not_fly with its kind."""
    outcome = _fake_launch(tmp_path, monkeypatch, "silo_cold", payloads={"silo_cold": None})
    assert outcome.kind == app.OUTCOME_DID_NOT_FLY
    assert outcome.message == "silo_cold did not fly: search_failed (fake)"


def test_outcome_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A run with a flag: flagged, the count named."""
    outcome = _fake_launch(tmp_path, monkeypatch, "silo_cold", flags={"silo_cold": ["f1"]})
    assert outcome.kind == app.OUTCOME_FLAGGED and outcome.message == "silo_cold: 1 flag"


def test_outcome_offload_found_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A case solve that ends no_offload: offload_found_nothing with the pad control's
    verdict."""
    outcome = _fake_launch(tmp_path, monkeypatch, "silo_cold_s1", case_status="no_offload")
    assert outcome.kind == app.OUTCOME_OFFLOAD_NOTHING
    assert outcome.message.startswith(
        "offload case silo_cold_s1 found no offload at P_ref: no_offload (pad control stage1"
    )


def test_outcome_flagged_by_a_bug_suspect_comparison_or_a_pad_control_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A comparison whose screening_status is bug_suspect (summary.md blocks findings on
    it) and a flag on the stage-1 pad control's run (a run of the offload block, not of
    metrics.json's runs) each give flagged."""
    state = sup.install_fake_sim(monkeypatch)
    monkeypatch.setattr(
        results_io,
        "planar_comparisons",
        lambda resolved, baseline, runs: {n: {"screening_status": "bug_suspect"} for n in runs},
    )
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.shipped_basis()
    common = dict(repo_root=sup.REPO_ROOT, cache=app.BaselineCache(), server_start=_start())
    outcome = app.run_launch(
        basis, appform.preset_form(basis, "silo_cold"), results_root=tmp_path / "a", **common
    )
    assert outcome.kind == app.OUTCOME_FLAGGED
    assert outcome.message == "silo_cold against the baseline: bug_suspect"
    summary_text = (outcome.out_dir / "summary.md").read_text(encoding="utf-8")
    assert "silo_cold (comparison)" in summary_text
    monkeypatch.setattr(
        results_io, "planar_comparisons", lambda resolved, baseline, runs: {n: {} for n in runs}
    )
    state.flags = {"pad__offload_stage1": ["a flag"]}
    form = dataclasses.replace(appform.preset_form(basis, "silo_cold_s1"), paired_pad=False)
    outcome = app.run_launch(basis, form, results_root=tmp_path / "b", **common)
    assert outcome.kind == app.OUTCOME_FLAGGED
    assert outcome.message == "pad__offload_stage1: 1 flag"


def _write_dir(folder: Path, metrics: dict[str, Any]) -> Path:
    """A synthetic complete directory: metrics.json and a summary.md."""
    folder.mkdir(parents=True)
    (folder / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (folder / "summary.md").write_text("# synthetic\n", encoding="utf-8")
    return folder


def test_classify_reads_the_offload_record(tmp_path: Path) -> None:
    """classify on synthetic directories (design 4.6's table): an imposed case whose
    vehicle reaches no orbit is not_in_orbit, never 'found nothing'; an imposed case that
    did not fly and a solve that did not fly are did_not_fly; a solve with no offload is
    offload_found_nothing in words; a bug_suspect decomposition, a bug_suspect paired-pad
    comparison and a failed pad-control verification are flagged; a stage-2 pad control
    that did not fly and a paired pad whose search failed are did_not_fly, and the
    control's flags without a run are noted; a stage-2 solve that nets to nothing (or has
    no control to net against) is offload_found_nothing, one that nets above zero is
    complete; a complete directory's message claims only the baseline and the variant."""
    runs = {"pad": {"status": "inserted", "flags": []}, "silo": {"status": "inserted"}}

    def classify(name: str, offload: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
        folder = _write_dir(tmp_path / name, {"runs": runs, "comparison": {}, "offload": offload})
        return app.classify(folder)

    imposed = {"name": "silo_fix60pct", "kind": "fixed", "run": "silo_fix60pct"}
    kind, message, _ = classify(
        "no_orbit", {"cases": [{**imposed, "status": "no_orbit", "run_status": "short_of_orbit"}]}
    )
    assert kind == app.OUTCOME_NOT_IN_ORBIT
    assert message == (
        "imposed offload silo_fix60pct: the offloaded vehicle reaches no orbit at any "
        "payload (no_orbit)"
    )
    kind, _, _ = classify("fixed_failed", {"cases": [{**imposed, "status": "search_failed"}]})
    assert kind == app.OUTCOME_DID_NOT_FLY
    solve = {"name": "silo_s1", "kind": "solve", "run": "silo_s1"}
    kind, _, _ = classify("solve_failed", {"cases": [{**solve, "status": "search_failed"}]})
    assert kind == app.OUTCOME_DID_NOT_FLY
    kind, message, _ = classify("no_offload", {"cases": [{**solve, "status": "no_offload"}]})
    assert kind == app.OUTCOME_OFFLOAD_NOTHING
    assert message == (
        "offload case silo_s1 found no offload at P_ref: no_offload (no pad control)"
    )
    flagged = [
        {"cases": [{**solve, "status": "ok", "decomposition_status": "bug_suspect"}]},
        {
            "cases": [
                {
                    **solve,
                    "status": "ok",
                    "paired_pad": {
                        "run": "silo_s1__pad",
                        "comparison": {"screening_status": "bug_suspect"},
                    },
                }
            ]
        },
        {
            "cases": [{**solve, "status": "ok"}],
            "pad_controls": [{"mode": "stage1", "status": "ok", "verification": {"passed": False}}],
        },
        {"cases": [{**solve, "status": "ok"}], "runs": {"silo_s1__pad": {"status": "bug_suspect"}}},
    ]
    for i, offload in enumerate(flagged):
        kind, _, notes = classify(f"flagged_{i}", offload)
        assert kind == app.OUTCOME_FLAGGED, (offload, notes)
    # a stage-2 pad control that did not fly: no stage-2 case can be netted against it,
    # so the case quotes nothing (results_io._quoted_offload)
    s2 = {
        **solve,
        "name": "silo_s2",
        "run": "silo_s2",
        "mode": "stage2",
        "status": "ok",
        "offload_kg": 30000.0,
        "pad_control_offload_kg": None,
        "net_offload_kg": None,
        "quoted_offload_kg": None,
    }
    control = {"mode": "stage2", "status": "search_failed", "run": None, "consistency": "n/a"}
    kind, message, notes = classify(
        "control_not_flown", {"cases": [s2], "pad_controls": [{**control, "flags": []}]}
    )
    assert kind == app.OUTCOME_DID_NOT_FLY
    assert message == (
        "pad control stage2 did not fly (search_failed): no stage2 case can be netted against it"
    )
    assert any(n.startswith("offload case silo_s2: nothing net of the pad control") for n in notes)
    _, _, notes = classify(
        "control_flags",
        {"cases": [s2], "pad_controls": [{**control, "flags": ["search_failed: edge: x"]}]},
    )
    assert "pad control stage2: 1 flag" in notes
    # a paired pad whose search failed (a run of the offload block, not of the case)
    kind, message, _ = classify(
        "paired_not_flown",
        {
            "cases": [{**solve, "status": "ok"}],
            "runs": {"silo_s1__pad": {"status": "search_failed", "flags": []}},
        },
    )
    assert kind == app.OUTCOME_DID_NOT_FLY and message == "silo_s1__pad did not fly: search_failed"
    # a stage-2 solve that ends ok but nets to less than its pad control
    netted = {
        **s2,
        "offload_kg": 300.0,
        "pad_control_offload_kg": 500.0,
        "net_offload_kg": -200.0,
        "quoted_offload_kg": -200.0,
    }
    ok_control = {**control, "status": "ok", "run": "pad__offload_stage2", "flags": []}
    kind, message, _ = classify("net_nothing", {"cases": [netted], "pad_controls": [ok_control]})
    assert kind == app.OUTCOME_OFFLOAD_NOTHING
    assert message.startswith(
        "offload case silo_s2: nothing net of the pad control (x* 0.300 t, pad control "
        "0.500 t, net -0.200 t) (pad control stage2: ok"
    )
    positive = {**netted, "offload_kg": 900.0, "net_offload_kg": 400.0, "quoted_offload_kg": 400.0}
    kind, _, notes = classify("net_positive", {"cases": [positive], "pad_controls": [ok_control]})
    assert kind == app.OUTCOME_COMPLETE and notes == ()
    kind, message, notes = classify("complete", {"cases": [{**solve, "status": "ok"}]})
    assert kind == app.OUTCOME_COMPLETE and notes == ()
    # in words, not check IDs (review of A5, usability): the status name kept in parentheses
    assert message == (
        "complete: pad, silo reached the target orbit; no flag, no failed verification and no "
        "result marked as a suspected bug (status bug_suspect) recorded"
    )


def test_classify_reads_verifications_paired_pads_and_m5(tmp_path: Path) -> None:
    """A failed case verification reads as the replay reads it, by the sign of its P* -
    P_ref: below P_ref by more than the tolerance it is uncertain both ways, a search that
    did not end ok is unverified (neither is 'a flagged lower bound'), above P_ref it is a
    flagged lower bound; a stage-2 case netted against a flagged pad control says its net
    figure is uncertain both ways; a paired pad short of orbit is not_in_orbit; a complete
    directory whose M5 check reads n/a says the check was not made."""
    runs = {"pad": {"status": "inserted", "flags": []}, "silo": {"status": "inserted"}}

    def classify(
        name: str, offload: dict[str, Any], comparison: dict[str, Any] | None = None
    ) -> tuple[str, str, tuple[str, ...]]:
        metrics = {"runs": runs, "comparison": comparison or {}, "offload": offload}
        return app.classify(_write_dir(tmp_path / name, metrics))

    solve = {"name": "silo_s1", "kind": "solve", "run": "silo_s1", "mode": "stage1"}
    failed = {"passed": False, "status": "ok", "tolerance_kg": 2.6}
    below = {**solve, "status": "ok", "verification": {**failed, "delta_kg": -54.4}}
    kind, message, _ = classify("below", {"cases": [below]})
    assert kind == app.OUTCOME_FLAGGED
    assert message == (
        "offload case silo_s1: verification failed (-54.40 kg against 2.6 kg): the gross "
        "removal is uncertain both ways, not a lower bound (the independent search carried "
        "less than P_ref at this removal)"
    )
    search_failed = {**failed, "status": "search_failed", "delta_kg": None}
    unverified = {**solve, "status": "ok", "verification": search_failed}
    kind, message, _ = classify("unverified", {"cases": [unverified]})
    assert kind == app.OUTCOME_FLAGGED and "a flagged lower bound" not in message
    assert message == (
        "offload case silo_s1: verification failed: the gross removal is unverified (the "
        "verification search ended search_failed)"
    )
    above = {**solve, "status": "ok", "verification": {**failed, "delta_kg": 15.36}}
    _, message, _ = classify("above", {"cases": [above]})
    assert message.endswith(
        "(+15.36 kg against 2.6 kg): the gross removal is a flagged lower bound"
    )
    s2 = {
        "name": "silo_s2",
        "kind": "solve",
        "run": "silo_s2",
        "mode": "stage2",
        "status": "ok",
        "offload_kg": 900.0,
        "pad_control_offload_kg": 500.0,
        "net_offload_kg": 400.0,
        "quoted_offload_kg": 400.0,
        "verification": {"passed": True, "status": "ok", "delta_kg": 0.1, "tolerance_kg": 2.6},
    }
    control = {
        "mode": "stage2",
        "status": "ok",
        "run": "pad__offload_stage2",
        "consistency": "n/a",
        "flags": ["a flag"],
    }
    kind, message, _ = classify("flagged_control", {"cases": [s2], "pad_controls": [control]})
    assert kind == app.OUTCOME_FLAGGED
    assert message == (
        "offload case silo_s2: the net figure subtracts a flagged pad control and is "
        "uncertain both ways"
    )
    imposed = {
        "name": "silo_fix60pct",
        "kind": "fixed",
        "run": "silo_fix60pct",
        "mode": "stage1",
        "status": "ok",
        "paired_pad": {"run": "silo_fix60pct__pad", "status": "short_of_orbit", "payload_kg": 0},
    }
    pad_run = {"status": "short_of_orbit", "search_status": "no_orbit", "flags": []}
    kind, message, _ = classify(
        "paired_short", {"cases": [imposed], "runs": {"silo_fix60pct__pad": pad_run}}
    )
    assert kind == app.OUTCOME_NOT_IN_ORBIT
    assert message == "paired pad silo_fix60pct__pad did not reach the target orbit: short_of_orbit"
    kind, message, _ = classify("m5_na", {}, {"silo": {"checks_m5": {"status": "n/a"}}})
    assert kind == app.OUTCOME_COMPLETE and message.endswith(app.M5_NOT_MADE_TEXT)
    kind, message, _ = classify("m5_pass", {}, {"silo": {"checks_m5": {"status": "pass"}}})
    assert kind == app.OUTCOME_COMPLETE and app.M5_NOT_MADE_TEXT not in message


def test_a_launch_on_the_committed_basis_says_what_it_reproduces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On the committed basis (read at HEAD; fake runs): the silo_cold preset keeps its
    name and the outcome says it reproduces silo_cold of experiments/silo_offload_2d.yaml
    at the basis commit; the git record names that commit and the banner says a committed
    name marks a reproduction at it, then that M5 reads n/a. An edited stage-1 solve with
    its paired pad writes silo, silo_s1 and silo_s1__pad, which the banner's rule names
    neutral, and reproduces nothing (D-SP2-31, 36)."""
    sup.install_fake_sim(monkeypatch)
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.shipped_basis()
    commit = basis.commit[:12]
    common = dict(repo_root=sup.REPO_ROOT, cache=app.BaselineCache(), server_start=_start())
    cold = appform.preset_form(basis, "silo_cold")
    outcome = app.run_launch(basis, cold, results_root=tmp_path / "a", **common)
    assert outcome.kind == app.OUTCOME_COMPLETE, outcome
    assert outcome.reproduces == (
        "silo_cold: same configuration as the committed silo_cold in "
        f"experiments/silo_offload_2d.yaml at commit {commit}: {app.REPRODUCTION_TAIL}",
    )
    metrics = json.loads((outcome.out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["git"][summary.EXPLORATORY_BASIS_COMMIT_KEY] == basis.commit
    banner = (outcome.out_dir / "summary.md").read_text(encoding="utf-8").splitlines()[0]
    assert banner.endswith(
        f"{summary.EXPLORATORY_REPRODUCTION_TEXT.format(commit=commit)} "
        f"{summary.EXPLORATORY_NO_ANCHOR_TEXT}"
    )
    assert summary.EXPLORATORY_UNCOMMITTED_BASIS_TEXT not in banner
    edited = dataclasses.replace(appform.preset_form(basis, "silo_cold_s1"), stroke_m=150)
    outcome = app.run_launch(basis, edited, results_root=tmp_path / "b", **common)
    assert outcome.kind == app.OUTCOME_COMPLETE, outcome
    assert outcome.reproduces == ()
    metrics = json.loads((outcome.out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert list(metrics["runs"]) == ["pad", "silo"]
    assert set(metrics["offload"]["runs"]) == {"silo_s1", "silo_s1__pad", "pad__offload_stage1"}


def test_an_edited_offload_file_is_never_called_committed(tmp_path: Path) -> None:
    """A copy of the three files with silo_cold's net acceleration edited (3.0 to 2.5 g0),
    loaded without a HEAD (read from the working tree, no commit): the silo_cold preset
    reads the edited value but takes the neutral name 'silo' and the dry run reproduces
    nothing; with a HEAD the same folder (no commit holds it) is one BasisError, never
    the working tree."""
    off, scr, veh = sup.raw_files()
    off = dict(off, variants=dict(off["variants"]))
    off["variants"]["silo_cold"] = dict(off["variants"]["silo_cold"])
    off["variants"]["silo_cold"]["assist"] = {
        **off["variants"]["silo_cold"]["assist"],
        "net_accel_g": 2.5,
    }
    for rel, data in ((sup.OFFLOAD_EXPERIMENT, off), (sup.SCREENING_EXPERIMENT, scr)):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    vehicle = tmp_path / sup.VEHICLE
    vehicle.parent.mkdir(parents=True, exist_ok=True)
    vehicle.write_text(yaml.safe_dump(veh, sort_keys=False), encoding="utf-8")
    basis = app.load_basis(tmp_path, app.ServerStart(git={}, head=None))
    assert basis.commit is None
    form = appform.preset_form(basis, "silo_cold")
    assert form.net_accel_g == 2.5
    assert list(appform.build_experiment(basis, form)["variants"]) == ["silo"]
    values = app.dry_run(basis, form)
    assert isinstance(values, dict) and values["reproduces"] == []
    with pytest.raises(app.BasisError, match=r"silo_offload_2d\.yaml"):
        app.load_basis(tmp_path, app.ServerStart(git={}, head="f" * 40))


def test_outcome_complete_and_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every run inserted with no flag: complete; the same directory without summary.md
    reads incomplete, and so does one whose metrics.json was cut short by a killed
    process (with or without summary.md: never a JSON error); failed_line skips
    traceback frames and pydantic's URL line."""
    outcome = _fake_launch(tmp_path, monkeypatch, "silo_cold")
    assert outcome.kind == app.OUTCOME_COMPLETE and outcome.notes == ()
    (outcome.out_dir / "summary.md").unlink()
    assert app.classify(outcome.out_dir)[0] == app.OUTCOME_INCOMPLETE
    cut = tmp_path / "cut"
    cut.mkdir()
    (cut / "metrics.json").write_text('{"runs": {"pad": ', encoding="utf-8")
    assert app.classify(cut) == (app.OUTCOME_INCOMPLETE, app.INCOMPLETE_MESSAGE, ())
    (cut / "summary.md").write_text("# cut\n", encoding="utf-8")
    assert app.classify(cut) == (app.OUTCOME_INCOMPLETE, app.METRICS_UNREADABLE_MESSAGE, ())
    marker = tmp_path / "FAILED.txt"
    marker.write_text(
        "header\n\nTraceback (most recent call last):\n  File x\npydantic_core.ValidationError:"
        " 1 validation error\nfield\n  Input should be a number\n"
        "    For further information visit https://errors.pydantic.dev/x\n",
        encoding="utf-8",
    )
    assert app.failed_line(marker) == "field"


# ------------------------------------------------------------------ pieces


def test_the_cache_key_and_the_rewrap() -> None:
    """The key covers the baseline's run dict, vehicle dict and the server-start state
    (another dirty flag, another key); a hit comes back wrapping the resolved baseline it
    is asked for, not the one it was stored with; concurrent puts are safe."""
    basis = sup.fixed_basis()
    form = appform.preset_form(basis, "pad")

    def baseline() -> Any:
        exp = appform.build_experiment(basis, form)
        return resolve_experiment(exp, basis.vehicle_copy()).baseline

    first, second = baseline(), baseline()
    assert first == second and first is not second
    start = _start()
    key = app.BaselineCache.key(first, start)
    assert key == app.BaselineCache.key(second, start)
    assert key != app.BaselineCache.key(first, _start({**START_DIRTY, "dirty": False}))
    cache = app.BaselineCache()
    stored = sup.fake_rr(first, sup.P_REF_KG)
    threads = [threading.Thread(target=cache.put, args=(first, start, stored)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(cache) == 1 and cache.get(second, _start({**START_DIRTY, "dirty": None})) is None
    hit = cache.get(second, start)
    assert hit is not None and hit.resolved is second and hit.result is stored.result


def test_the_git_record_of_a_launch() -> None:
    """dirty is true when either state is dirty, None when one is unknown and neither
    dirty; the launch-time flag and the server-start record are kept beside it; the code
    check reads done only when it ran and found no change; a no-git state (git_info's
    dirty False) is unknown, never clean."""
    assert app.combined_dirty(False, False) is False
    assert app.combined_dirty(True, None) is True and app.combined_dirty(None, False) is None
    record = app.launch_git_record(LAUNCH_CLEAN, _start(head="f" * 40), checked=False)
    assert record["dirty"] is True and record["launch_dirty"] is False
    assert record["server_start"] == START_DIRTY and record["code_check"] == app.CODE_CHECK_DONE
    skipped = app.launch_git_record(LAUNCH_CLEAN, _start(head="f" * 40), checked=None)
    assert skipped["code_check"] == app.CODE_CHECK_SKIPPED
    no_git = {"hash": "no-git", "dirty": False, "error": "TimeoutExpired: git timed out"}
    record = app.launch_git_record(LAUNCH_CLEAN, _start(no_git), checked=None)
    assert record["dirty"] is None and record["launch_dirty"] is False
    record = app.launch_git_record(no_git, _start(LAUNCH_CLEAN), checked=None)
    assert record["dirty"] is None and record["launch_dirty"] is None


def test_a_no_git_server_start_never_reads_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A launch whose server start had no git (git_info: no-git, dirty False) and whose
    launch-time tree is clean: metrics git.dirty is null and the summary title ends
    '-dirty?)' (unknown), never a bare hash."""
    sup.install_fake_sim(monkeypatch)
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.searched_basis()
    no_git = {"hash": "no-git", "dirty": False, "error": "TimeoutExpired: git timed out"}
    outcome = app.run_launch(
        basis,
        appform.preset_form(basis, "silo_cold"),
        results_root=tmp_path,
        repo_root=sup.REPO_ROOT,
        cache=app.BaselineCache(),
        server_start=_start(no_git),
    )
    metrics = json.loads((outcome.out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["git"]["dirty"] is None
    lines = (outcome.out_dir / "summary.md").read_text(encoding="utf-8").splitlines()
    assert lines[2].endswith(f"git {START_HASH}-dirty?)")
    assert "(no-git, unknown)" in lines[0]


def test_code_changed_on_the_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read-only git on this repository: HEAD against itself is unchanged (False); an
    unknown commit cannot be compared (True: refused); no HEAD at start means the check
    is not made (None: the record says so); git missing now, while present at start,
    cannot compare them (True: refused, never a launch recorded as checked)."""
    start = app.take_server_start(sup.REPO_ROOT)
    assert start.head is not None and len(start.head) == 40
    assert app.code_changed(sup.REPO_ROOT, start) is False
    assert app.code_changed(sup.REPO_ROOT, dataclasses.replace(start, head="0" * 40)) is True
    assert app.code_changed(sup.REPO_ROOT, dataclasses.replace(start, head=None)) is None

    def missing(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", missing)
    assert app.code_changed(sup.REPO_ROOT, start) is True


def test_load_basis(tmp_path: Path) -> None:
    """load_basis reads the files as committed at the server-start HEAD (read-only git):
    equal to the working tree's (experiments/ and configs/ are unchanged), with that
    commit; a commit that lacks them is one BasisError, so the working tree is not read;
    without a HEAD (no git) a folder without them is one BasisError naming
    experiments/silo_offload_2d.yaml."""
    start = app.take_server_start(sup.REPO_ROOT)
    assert start.head is not None
    basis = app.load_basis(sup.REPO_ROOT, start)
    off, scr, veh = sup.raw_files()
    assert basis.offload_experiment == off and basis.screening_experiment == scr
    assert basis.vehicle == veh and basis.commit == start.head
    assert basis.vehicle_path == "configs/vehicles/generic_f9_class_2d.yaml"
    unknown = dataclasses.replace(start, head="0" * 40)
    with pytest.raises(app.BasisError, match=r"silo_offload_2d\.yaml is not in commit"):
        app.load_basis(sup.REPO_ROOT, unknown)
    with pytest.raises(app.BasisError, match=r"experiments/silo_offload_2d\.yaml not found"):
        app.load_basis(tmp_path, dataclasses.replace(start, head=None))


# ------------------------------------------------------------------ slow


@pytest.mark.slow
def test_a_searched_launch_with_a_stage1_solve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real launch on the small searched grid: silo_cold with a stage-1 solve (no
    paired pad). A complete directory (summary.md, no FAILED.txt), label exploratory,
    the banner, git.server_start; the case ok and verified. The pad control's verdict
    is not asserted (on this grid it may fail)."""
    sup.git_states(monkeypatch, LAUNCH_CLEAN)
    basis = sup.searched_basis()
    form = dataclasses.replace(appform.preset_form(basis, "silo_cold_s1"), paired_pad=False)
    outcome = app.run_launch(
        basis,
        form,
        results_root=tmp_path,
        repo_root=sup.REPO_ROOT,
        cache=app.BaselineCache(),
        server_start=_start(),
    )
    out = outcome.out_dir
    assert outcome.kind not in (app.OUTCOME_CRASHED, app.OUTCOME_REFUSED, app.OUTCOME_INCOMPLETE)
    assert (out / "summary.md").is_file() and not (out / results_io.FAILED_MARKER).exists()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["label"] == "exploratory" and metrics["git"]["server_start"] == START_DIRTY
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert summary.startswith("> **EXPLORATORY app run, not a finding.**")
    assert "sweep-optimized, unthrottled." in summary.splitlines()[0]
    (case,) = metrics["offload"]["cases"]
    assert case["name"] == "silo_s1" and case["status"] == "ok"
    assert case["verification"]["passed"] is True
    assert not (out / "plots").exists()
