"""Plan amendment 1: a calibration run records the frozen-input state of configs/ and
experiments/ (the last commit touching them, and any uncommitted or untracked change),
and its summary marks a dirty or unknown state as not a valid calibration record."""

from __future__ import annotations

import subprocess
from pathlib import Path

from launchsim.results_io import PREREGISTERED_PATHS, preregistration_state
from launchsim.summary import PREREGISTRATION_DIRTY_FLAG, preregistration_lines


def _git(repo: Path, *args: str) -> str:
    """Run git in repo with a throwaway identity; return stdout."""
    proc = subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout.strip()


def _repo_with_inputs(tmp_path: Path) -> Path:
    """A repository with one committed file under each pre-registered path."""
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    (repo / "experiments").mkdir()
    (repo / "configs" / "vehicle.yaml").write_text("a: 1\n", encoding="utf-8")
    (repo / "experiments" / "cal.yaml").write_text("b: 2\n", encoding="utf-8")
    (repo / "README.md").write_text("readme\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "inputs")
    return repo


def test_preregistered_paths_are_configs_and_experiments() -> None:
    assert PREREGISTERED_PATHS == ("configs", "experiments")


def test_clean_inputs_record_their_commit(tmp_path: Path) -> None:
    repo = _repo_with_inputs(tmp_path)
    state = preregistration_state(repo / "configs")  # any directory inside the repo
    assert state["dirty"] is False
    assert state["dirty_paths"] == []
    assert state["error"] is None
    assert state["inputs_commit"] == _git(repo, "rev-parse", "--short=12", "HEAD")


def test_changes_outside_the_inputs_do_not_count(tmp_path: Path) -> None:
    repo = _repo_with_inputs(tmp_path)
    (repo / "README.md").write_text("edited\n", encoding="utf-8")
    (repo / "notes.txt").write_text("untracked\n", encoding="utf-8")
    assert preregistration_state(repo)["dirty"] is False


def test_modified_and_untracked_inputs_are_dirty(tmp_path: Path) -> None:
    repo = _repo_with_inputs(tmp_path)
    (repo / "configs" / "vehicle.yaml").write_text("a: 2\n", encoding="utf-8")
    (repo / "experiments" / "new.yaml").write_text("c: 3\n", encoding="utf-8")
    state = preregistration_state(repo)
    assert state["dirty"] is True
    assert sorted(state["dirty_paths"]) == ["configs/vehicle.yaml", "experiments/new.yaml"]


def test_outside_a_repository_the_state_is_unknown(tmp_path: Path) -> None:
    state = preregistration_state(tmp_path)
    assert state["dirty"] is None
    assert state["inputs_commit"] is None
    assert state["error"]


def test_summary_lines_mark_dirty_and_unknown_states() -> None:
    assert preregistration_lines(None) == []
    clean = preregistration_lines(
        {"inputs_commit": "abc123def456", "dirty": False, "dirty_paths": [], "error": None}
    )
    assert "clean at commit abc123def456" in clean[0]
    assert PREREGISTRATION_DIRTY_FLAG not in "".join(clean)
    dirty = preregistration_lines(
        {
            "inputs_commit": "abc123def456",
            "dirty": True,
            "dirty_paths": ["configs/vehicle.yaml"],
            "error": None,
        }
    )
    assert PREREGISTRATION_DIRTY_FLAG in dirty[0]
    assert "configs/vehicle.yaml" in dirty[0]
    assert "not a valid calibration record" in dirty[0]
    unknown = preregistration_lines(
        {"inputs_commit": None, "dirty": None, "dirty_paths": [], "error": "no git"}
    )
    assert PREREGISTRATION_DIRTY_FLAG in unknown[0]
    assert "not a valid calibration record" in unknown[0]
    for lines in (clean, dirty, unknown):
        assert all(line.isascii() for line in lines)
