"""Results I/O: run-directory naming (never overwrite), JSON without NaN, UTF-8 summaries
on a cp1252 console, and git provenance states."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from launchsim import sim
from launchsim.config import ResolvedExperiment, RunConfig
from launchsim.vehicle import Vehicle

RUN_DIR_PATTERN = re.compile(r"^\d{8}T\d{6}Z(-\d+)?$")
FIXED_NOW = datetime(2026, 9, 28, 12, 34, 56, tzinfo=UTC)


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, timeout=30)


# ------------------------------------------------------------------- run directories


def test_run_dir_name_matches_timestamp_pattern(tmp_path: Path) -> None:
    out = sim.make_run_dir(tmp_path, "exp")
    assert out.parent == tmp_path / "exp"
    assert RUN_DIR_PATTERN.match(out.name), out.name
    assert out.is_dir()


def test_second_run_dir_in_same_second_gets_suffix(tmp_path: Path) -> None:
    first = sim.make_run_dir(tmp_path, "exp", now=FIXED_NOW)
    second = sim.make_run_dir(tmp_path, "exp", now=FIXED_NOW)
    third = sim.make_run_dir(tmp_path, "exp", now=FIXED_NOW)
    assert first.name == "20260928T123456Z"
    assert second.name == "20260928T123456Z-2"
    assert third.name == "20260928T123456Z-3"
    assert all(RUN_DIR_PATTERN.match(p.name) for p in (first, second, third))


def test_run_dir_never_overwrites(tmp_path: Path) -> None:
    first = sim.make_run_dir(tmp_path, "exp", now=FIXED_NOW)
    marker = first / "summary.md"
    marker.write_text("keep me", encoding="utf-8")
    second = sim.make_run_dir(tmp_path, "exp", now=FIXED_NOW)
    assert second != first
    assert marker.read_text(encoding="utf-8") == "keep me"
    assert not (second / "summary.md").exists()


# ---------------------------------------------------------------------------- JSON


def test_metrics_json_has_no_nan_and_round_trips(tmp_path: Path) -> None:
    data = {
        "a": float("nan"),
        "b": float("inf"),
        "c": -float("inf"),
        "d": 1.5,
        "e": np.float64(2.5),
        "f": np.int64(3),
        "g": [float("nan"), 1.0],
        "h": {"nested": np.array([1.0, math.nan])},
        "i": True,
        "j": None,
        "k": "text with unicode: \u0394v \u03bc \u00b0",
        "p": Path("x/y"),
    }
    path = sim.write_json(tmp_path / "metrics.json", data)
    raw = path.read_text(encoding="utf-8")
    assert "NaN" not in raw
    assert "Infinity" not in raw
    back = json.loads(raw)
    assert back["a"] is None and back["b"] is None and back["c"] is None
    assert back["d"] == 1.5 and back["e"] == 2.5 and back["f"] == 3
    assert back["g"] == [None, 1.0]
    assert back["h"] == {"nested": [1.0, None]}
    assert back["i"] is True and back["j"] is None
    assert back["k"] == data["k"]
    assert back["p"] == "x/y"
    # strict re-parse: the file must be valid with NaN tokens forbidden
    json.loads(raw, parse_constant=lambda name: pytest.fail(f"non-finite token {name}"))


# --------------------------------------------------------------------- UTF-8 summary


SUMMARY_TEXT = "# Summary\n\n\u0394v = 77 m/s; \u03bc = 3.986e14; latitude 28.5\u00b0\n"


def test_summary_written_and_read_back_in_cp1252_subprocess(tmp_path: Path) -> None:
    """A summary containing Delta, mu and the degree sign survives a subprocess with
    UTF-8 mode off (PYTHONUTF8=0) and no PYTHONIOENCODING: the writer must pass
    encoding='utf-8' itself."""
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    path = sim.write_summary(out_dir, SUMMARY_TEXT)
    assert path.name == "summary.md"
    assert path.read_bytes() == SUMMARY_TEXT.encode("utf-8")  # LF only, UTF-8 bytes

    env = dict(os.environ)
    env["PYTHONUTF8"] = "0"
    env.pop("PYTHONIOENCODING", None)
    child_dir = tmp_path / "child"
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from launchsim import sim\n"
        "expected = " + repr(SUMMARY_TEXT) + "\n"
        "out = Path(sys.argv[1]); out.mkdir()\n"
        "p = sim.write_summary(out, expected)\n"
        "assert p.read_text(encoding='utf-8') == expected\n"
        "assert Path(sys.argv[2]).read_text(encoding='utf-8') == expected\n"
        "print('OK')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(child_dir), str(path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "OK"
    assert (child_dir / "summary.md").read_text(encoding="utf-8") == SUMMARY_TEXT


# ----------------------------------------------------------------------------- git


def test_git_info_no_git_outside_a_repository(tmp_path: Path) -> None:
    info = sim.git_info(tmp_path)
    assert info["hash"] == "no-git"
    assert info["dirty"] is False
    assert set(info) == {"hash", "dirty", "error"}
    assert sim.git_label(info) == "no-git"


def test_git_info_unborn_after_git_init(tmp_path: Path) -> None:
    _git(["init", "-q"], tmp_path)
    info = sim.git_info(tmp_path)
    assert info["hash"] == "unborn"
    assert info["error"] is None
    assert sim.git_label(info) == "unborn"


def test_git_info_hash_after_a_commit(tmp_path: Path) -> None:
    _git(["init", "-q"], tmp_path)
    _git(
        [
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "init",
        ],
        tmp_path,
    )
    info = sim.git_info(tmp_path)
    assert re.fullmatch(r"[0-9a-f]{12}", info["hash"]), info
    assert info["dirty"] is False
    assert sim.git_label(info) == info["hash"]
    (tmp_path / "new.txt").write_text("x", encoding="utf-8")
    info = sim.git_info(tmp_path)
    assert info["dirty"] is True
    assert sim.git_label(info) == info["hash"] + "-dirty"


def test_git_info_in_repo_root(repo_root: Path) -> None:
    """The repository itself: a 12-hex hash once committed, 'unborn' before the first
    commit (the Phase 0 exit gate makes it); never 'no-git' and never an exception."""
    info = sim.git_info(repo_root)
    assert info["hash"] == "unborn" or re.fullmatch(r"[0-9a-f]{12}", info["hash"]), info
    assert isinstance(info["dirty"], bool)


def test_git_info_keeps_git_stderr_when_git_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """A refusal such as 'dubious ownership' is reported; a plain 'not a repository' is not."""

    def refuse(args: list[str], cwd: Path) -> str:
        raise subprocess.CalledProcessError(
            128, ["git", *args], stderr="fatal: detected dubious ownership in repository"
        )

    monkeypatch.setattr(sim, "_git", refuse)
    info = sim.git_info(Path("."))
    assert info["hash"] == "no-git"
    assert "dubious ownership" in info["error"]

    def not_a_repo(args: list[str], cwd: Path) -> str:
        raise subprocess.CalledProcessError(
            128, ["git", *args], stderr="fatal: not a git repository: .git"
        )

    monkeypatch.setattr(sim, "_git", not_a_repo)
    assert sim.git_info(Path(".")) == {"hash": "no-git", "dirty": False, "error": None}


def _init_repo_with_one_commit(root: Path) -> None:
    _git(["init", "-q"], root)
    _git(
        [
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "init",
        ],
        root,
    )


def test_git_info_dirty_ignores_the_results_tree(tmp_path: Path) -> None:
    """Untracked run summaries under results/ (un-ignored by .gitignore so they can be
    committed) must not stamp later runs as -dirty; other untracked files still do."""
    _init_repo_with_one_commit(tmp_path)
    run_dir = tmp_path / "results" / "exp" / "20260928T123456Z"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.md").write_text("# exp\n", encoding="utf-8")
    assert sim.git_info(tmp_path)["dirty"] is False
    (tmp_path / "src.py").write_text("x = 1\n", encoding="utf-8")
    assert sim.git_info(tmp_path)["dirty"] is True


def test_git_info_is_anchored_at_the_repository_top_level(tmp_path: Path) -> None:
    """Given a subdirectory, the dirty flag still covers the whole work tree and the
    results exclusion still means the top-level results/ (not <subdir>/results)."""
    _init_repo_with_one_commit(tmp_path)
    sub = tmp_path / "experiments" / "deeper"
    sub.mkdir(parents=True)
    run_dir = tmp_path / "results" / "exp" / "20260928T123456Z"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.md").write_text("# exp\n", encoding="utf-8")
    info = sim.git_info(sub)
    assert re.fullmatch(r"[0-9a-f]{12}", info["hash"]) and info["dirty"] is False, info
    (tmp_path / "src.py").write_text("x = 1\n", encoding="utf-8")  # outside the subdirectory
    assert sim.git_info(sub)["dirty"] is True


def test_git_info_keeps_the_hash_when_status_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """A slow ``git status`` must not downgrade a real repository to no-git: the hash is
    kept, dirty is unknown (None) and the label says so."""

    def slow_status(args: list[str], cwd: Path) -> str:
        if args[0] == "status":
            raise subprocess.TimeoutExpired(["git", *args], sim.GIT_TIMEOUT_S)
        return {"--is-inside-work-tree": "true", "--show-toplevel": str(cwd)}.get(
            args[1], "abcdef123456"
        )

    monkeypatch.setattr(sim, "_git", slow_status)
    info = sim.git_info(Path("."))
    assert info["hash"] == "abcdef123456"
    assert info["dirty"] is None
    assert "TimeoutExpired" in info["error"]
    assert sim.git_label(info) == "abcdef123456-dirty?"


# ----------------------------------------------------------------------- names


@pytest.mark.parametrize(
    "bad",
    [
        "..",
        ".",
        "C:/x",
        "a:b",
        "a/b",
        "a\b",
        "silo.",
        "",
        ".hidden",
        "-x",
        "CON",
        "nul.txt",
        "COM1",
    ],
)
def test_check_name_rejects_unsafe_experiment_names(bad: str) -> None:
    with pytest.raises(sim.InvalidNameError):
        sim.check_name(bad, "experiment name")


@pytest.mark.parametrize("bad", ["plots", "baseline", "sweep_1", "run_0001"])
def test_check_run_name_rejects_layout_names(bad: str) -> None:
    with pytest.raises(sim.InvalidNameError, match="reserved"):
        sim.check_run_name(bad)
    sim.check_name(bad, "experiment name")  # only reserved as run names


@pytest.mark.parametrize(
    "good", ["pad", "silo_cold", "silo-sled.22t", "stage1.dry_mass_t+10", "x", "Run7"]
)
def test_check_name_accepts_safe_names(good: str) -> None:
    assert sim.check_run_name(good) == good


def test_check_name_caps_the_length(tmp_path: Path) -> None:
    """Long names overflow Windows' default MAX_PATH once the sweep layout and a plot
    file name are appended; the cap keeps the failure at validation time."""
    assert sim.check_name("x" * sim.MAX_NAME_LEN, "experiment name")
    with pytest.raises(sim.InvalidNameError, match="longer than"):
        sim.check_name("x" * (sim.MAX_NAME_LEN + 1), "experiment name")
    with pytest.raises(sim.InvalidNameError):
        sim.make_run_dir(tmp_path, "y" * 240, now=FIXED_NOW)
    assert list(tmp_path.iterdir()) == []


def test_make_run_dir_rejects_unsafe_experiment_name(tmp_path: Path) -> None:
    with pytest.raises(sim.InvalidNameError):
        sim.make_run_dir(tmp_path, "..", now=FIXED_NOW)
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------- non-finite metrics


def _result(metrics: dict, frame: pd.DataFrame | None = None) -> sim.Result:
    return sim.Result(
        metrics=metrics,
        timeseries=sim.empty_timeseries() if frame is None else frame,
        loss_budget=None,
        assist_budget=None,
        assumptions=[],
        phases=[],
        status="nominal",
        flags=[],
    )


def test_compare_gives_none_for_non_finite_metrics() -> None:
    result = _result({"a": math.nan, "b": math.inf, "c": 2.0, "d": True, "e": "text"})
    base = _result({"a": 1.0, "b": math.inf, "c": 0.5, "d": False, "e": "text"})
    comp = sim.compare(result, base)
    assert comp == {
        "status": "nominal",
        "baseline_status": "nominal",
        "delta_a": None,
        "delta_b": None,
        "delta_c": 1.5,
    }
    assert sim._fmt(math.nan) == "n/a" and sim._fmt(math.inf) == "n/a" and sim._fmt(None) == "n/a"


def test_pandas_missing_values_are_unavailable_everywhere(tmp_path: Path) -> None:
    """pd.NA / pd.NaT (a max over an empty column, say) must behave like NaN: null in
    JSON, "n/a" in a summary, None in a comparison, an empty sweep-index cell; never the
    string '<NA>'."""
    assert sim.json_safe({"a": pd.NA, "b": pd.NaT, "c": [pd.NA, 1.0]}) == {
        "a": None,
        "b": None,
        "c": [None, 1.0],
    }
    raw = sim.write_json(tmp_path / "m.json", {"a": pd.NA}).read_text(encoding="utf-8")
    assert "<NA>" not in raw and json.loads(raw) == {"a": None}
    assert sim._fmt(pd.NA) == "n/a" and sim._fmt(pd.NaT) == "n/a"
    comp = sim.compare(_result({"a": pd.NA, "b": 2.0}), _result({"a": 1.0, "b": pd.NA}))
    assert comp["delta_a"] is None and comp["delta_b"] is None


def test_metrics_record_refuses_reserved_metric_keys() -> None:
    """A metric named status or flags would be overwritten in metrics.json while
    summary.md kept it: refused as a schema error."""
    record = sim.metrics_record(_result({"x_m": 1.0}))
    assert record == {"x_m": 1.0, "status": "nominal", "flags": []}
    with pytest.raises(ValueError, match="reserved"):
        sim.metrics_record(_result({"flags": "clash"}))
    with pytest.raises(ValueError, match="reserved"):
        sim.metrics_record(_result({"status": "nominal"}))


# ------------------------------------------------------------- partial run directories


def _tiny_resolved() -> ResolvedExperiment:
    from launchsim.cli import load_experiment

    return load_experiment(Path(__file__).resolve().parent / "data" / "tiny_experiment.yaml")


@pytest.mark.parametrize("entry", ["run_experiment", "run_sweep"])
def test_failed_run_leaves_a_marker_in_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    """The run directory is created before any run starts; if a run raises, FAILED.txt
    carries the traceback, the exception propagates (a simulator bug keeps its
    traceback) and no summary.md is written, so the directory is recognisably partial."""
    calls = {"n": 0}
    real_run = sim.run

    def failing_run(run_config: RunConfig, vehicle: Vehicle) -> sim.Result:
        calls["n"] += 1
        if calls["n"] == 2:  # the baseline succeeds, the first variant/point raises
            raise RuntimeError("boom in the second run")
        return real_run(run_config, vehicle)

    monkeypatch.setattr(sim, "run", failing_run)
    with pytest.raises(RuntimeError, match="boom"):
        getattr(sim, entry)(_tiny_resolved(), tmp_path, plots=False, repo_root=tmp_path)
    (run_dir,) = (tmp_path / "tiny_experiment").iterdir()
    marker = run_dir / sim.FAILED_MARKER
    assert marker.is_file()
    text = marker.read_text(encoding="utf-8")
    assert "partial" in text and "RuntimeError: boom in the second run" in text
    assert not (run_dir / "summary.md").exists()


def test_unwritable_results_root_fails_before_any_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A results root that is a file is detected before the (possibly long) runs start."""
    blocker = tmp_path / "results"
    blocker.write_text("not a directory", encoding="utf-8")

    def never(run_config: RunConfig, vehicle: Vehicle) -> sim.Result:
        raise AssertionError("a run started before the results directory existed")

    monkeypatch.setattr(sim, "run", never)
    with pytest.raises(OSError):
        sim.run_experiment(_tiny_resolved(), blocker, plots=False, repo_root=tmp_path)
    with pytest.raises(OSError):
        sim.run_sweep(_tiny_resolved(), blocker, plots=False, repo_root=tmp_path)


# --------------------------------------------------------------------------- plots


def test_write_plots_one_png_per_numeric_column_with_safe_names(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "t_s": [0.0, 1.0, 2.0],
            "z_m": [0.0, 4.9, 19.6],
            "v_mps": [0.0, 9.8, 19.6],
            "m_kg": [1000.0, 995.0, 990.0],
            "F/N": [1.0, 2.0, 3.0],  # a separator in the name must not become a directory
            "phase": ["a", "b", "c"],  # non-numeric: no plot
        }
    )
    written = sim.write_plots(_result({}, frame), tmp_path / "plots", "run$1")
    names = sorted(p.name for p in written)
    assert names == sorted(["run_1_z_m.png", "run_1_v_mps.png", "run_1_m_kg.png", "run_1_F_N.png"])
    assert all(p.parent == tmp_path / "plots" for p in written)
    assert all(p.stat().st_size > 0 for p in written)
    assert sim.write_plots(_result({}), tmp_path / "plots2", "x") == []
    assert not (tmp_path / "plots2").exists()


# ----------------------------------------------------------------------- sweep index


def test_sweep_index_frame_rejects_metric_keys_that_collide_with_index_columns(
    tmp_path: Path,
) -> None:
    from launchsim.cli import load_experiment

    resolved = load_experiment(Path(__file__).resolve().parent / "data" / "tiny_experiment.yaml")
    point = resolved.sweeps[0][0]
    baseline = sim.run_resolved(resolved.baseline)
    rr = sim.RunResult(point.run.name, point.run, _result({"point": 99.0, "x_mps": math.inf}))
    sweep = sim.SweepResult(
        1,
        point.of,
        ["assist.net_accel_g", "assist.stroke_m"],
        [point],
        [rr],
        [sim.compare(rr.result, baseline.result)],
        [tmp_path / "sweep_1" / "run_0001"],
    )
    with pytest.raises(ValueError, match="collide"):
        sim.sweep_index_frame(sweep, baseline, tmp_path)
    ok = sim.RunResult(point.run.name, point.run, _result({"x_mps": math.inf, "y_m": 2.0}))
    sweep = sim.SweepResult(
        1,
        point.of,
        ["assist.net_accel_g", "assist.stroke_m"],
        [point],
        [ok],
        [sim.compare(ok.result, baseline.result)],
        [tmp_path / "sweep_1" / "run_0001"],
    )
    frame = sim.sweep_index_frame(sweep, baseline, tmp_path)
    assert frame.loc[0, "point"] == 1 and frame.loc[0, "run_dir"] == "sweep_1/run_0001"
    assert frame.loc[0, "assist.net_accel_g"] == 1 and frame.loc[0, "y_m"] == 2.0
    assert frame.loc[0, "x_mps"] is None or pd.isna(frame.loc[0, "x_mps"])  # inf -> empty cell
