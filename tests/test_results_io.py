"""Results I/O: run-directory naming (never overwrite), JSON without NaN, UTF-8 summaries
on a cp1252 console, git provenance states, and the preflight of SP1 step 3 (a
configuration whose ramp start cannot be converted writes nothing)."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest
import yaml

from launchsim import sim
from launchsim.config import ResolvedExperiment, RunConfig, resolve_experiment
from launchsim.constants import G0_MPS2
from launchsim.units import t_to_kg
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
    deltas = {k: v for k, v in comp.items() if k.startswith("delta_")}
    assert deltas == {"delta_a": None, "delta_b": None, "delta_c": 1.5}
    assert comp["status"] == "nominal" and comp["baseline_status"] == "nominal"
    # a hand-built Result has no flight budget: every figure of merit is unavailable
    assert comp["identity_point"] is None and comp["identity_line_residual_mps"] is None
    assert comp["d_speed_mps"] is None and comp["ideal_screening_payload_equiv_kg"] is None
    assert comp["ideal_screening_payload_at_release_speed_kg"] is None
    assert comp["ignition_loss_integrated_mps"] is None and comp["unexplained_gain_mps"] is None
    assert sim._fmt(math.nan) == "n/a" and sim._fmt(math.inf) == "n/a" and sim._fmt(None) == "n/a"


def test_summary_formatting_prints_rounding_noise_as_zero() -> None:
    """Summary cells snap a magnitude below DISPLAY_ZERO_ABS to 0 (the cos(pi/2)
    roundoff of a vertical track's normal load, a -2.5e-13 m/s credit); the bound lines
    print an excess below EXCESS_NOISE_MPS as 0 with the bound named; real numbers and
    the JSON values are untouched."""
    assert sim._fmt(6.11801e-17) == "0" and sim._fmt(-2.52243e-13) == "0"
    assert sim._signed(-2.52243e-13) == "+0" and sim._signed(1.74053e-14) == "+0"
    assert sim._fmt(1e-3) == "0.001" and sim._signed(-14.6974) == "-14.6974"
    assert sim._fmt(0.0) == "0" and sim._fmt(-0.0) == "0"
    assert sim._excess_text(4.35528e-08) == "0 (|excess| < 1e-06)"
    assert sim._excess_text(-1.75466e-08) == "0 (|excess| < 1e-06)"
    assert sim._excess_text(-14.6974) == "-14.6974" and sim._excess_text(None) == "n/a"
    assert sim.json_safe({"g": 6.11801e-17}) == {"g": 6.11801e-17}


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


def _frame(phases: list[str]) -> pd.DataFrame:
    """A time series with the standard columns over the given phase kinds."""
    n = len(phases)
    frame = sim.empty_timeseries()
    rows = {c: [float(i) for i in range(n)] for c in sim.TIMESERIES_COLUMNS}
    rows["phase"] = phases
    rows["stage"] = ["stage1"] * n
    return pd.concat([frame, pd.DataFrame(rows)], ignore_index=True)


def test_write_plots_curated_panels_with_safe_names(tmp_path: Path) -> None:
    """A pad run gets the four flight panels; a run with ASSIST rows also gets the
    track panels; a separator in the prefix never becomes a directory; an empty time
    series writes nothing. A panel's y labels are one shared label or one per column
    (its own axis each): mass and thrust never share a scale."""
    for _quantity, columns, ylabels in (*sim.PLOT_PANELS, *sim.PLOT_TRACK_PANELS):
        assert len(ylabels) in (1, len(columns))
    panels = {quantity: (columns, ylabels) for quantity, columns, ylabels in sim.PLOT_PANELS}
    assert panels["mass_thrust"] == (("m_kg", "thrust_N"), ("m [kg]", "T [N]"))
    pad = _result({}, _frame(["HOLD", "BURN", "BURN"]))
    written = sim.write_plots(pad, tmp_path / "plots", "run$1")
    assert sorted(p.name for p in written) == sorted(
        f"run_1_{quantity}.png" for quantity, _cols, _label in sim.PLOT_PANELS
    )
    assert all(p.parent == tmp_path / "plots" for p in written)
    assert all(p.stat().st_size > 0 for p in written)
    silo = _result({}, _frame(["ASSIST", "ASSIST", "BURN"]))
    written = sim.write_plots(silo, tmp_path / "plots", "silo")
    assert sorted(p.name for p in written) == sorted(
        f"silo_{quantity}.png"
        for quantity, _cols, _label in (*sim.PLOT_PANELS, *sim.PLOT_TRACK_PANELS)
    )
    assert sim.write_plots(_result({}), tmp_path / "plots2", "x") == []
    assert not (tmp_path / "plots2").exists()


# ----------------------------------------------------------------------- sweep index


def test_sweep_index_frame_has_the_curated_columns_and_rejects_axis_collisions(
    tmp_path: Path,
) -> None:
    """The index carries point, the axis values, run_dir, of, SWEEP_INDEX_METRICS (from
    the point's metrics or its comparison; non-finite or absent -> empty cell) and
    status; an axis path named like an index column is a schema error."""
    resolved = _tiny_resolved()
    point = resolved.sweeps[0][0]
    baseline = sim.run_resolved(resolved.baseline)
    axes = ["assist.net_accel_g", "assist.stroke_m"]
    rr = sim.RunResult(
        point.run.name,
        point.run,
        _result({"exit_speed_mps": 7.5, "drive_energy_J": math.inf, "x_unlisted": 1.0}),
    )
    comparison = sim.compare(rr.result, baseline.result)
    sweep = sim.SweepResult(
        1, point.of, axes, [point], [rr], [comparison], [tmp_path / "sweep_1" / "run_0001"]
    )
    frame = sim.sweep_index_frame(sweep, baseline, tmp_path)
    assert list(frame.columns) == [
        "point",
        *axes,
        "run_dir",
        "of",
        *sim.SWEEP_INDEX_METRICS,
        "status",
    ]
    assert frame.loc[0, "point"] == 1 and frame.loc[0, "run_dir"] == "sweep_1/run_0001"
    assert frame.loc[0, "assist.net_accel_g"] == 1 and frame.loc[0, "exit_speed_mps"] == 7.5
    assert pd.isna(frame.loc[0, "drive_energy_J"])  # inf -> empty cell
    assert pd.isna(frame.loc[0, "felt_g_track_peak"])  # absent -> empty cell
    assert pd.isna(frame.loc[0, "stage1_burnout_speed_delta_mps"])  # no burnout on the point
    assert frame.loc[0, "status"] == "nominal"
    bad = sim.SweepResult(
        1, point.of, ["status"], [point], [rr], [comparison], [tmp_path / "sweep_1" / "run_0001"]
    )
    with pytest.raises(ValueError, match="collide"):
        sim.sweep_index_frame(bad, baseline, tmp_path)


# ---------------------------------------------------------------- figures of merit


def test_compare_identity_line_closes_on_the_tiny_experiment() -> None:
    """The variant's identity decomposition against the baseline closes to rounding,
    is written at both runs' stage-1 burnout, and its speed delta is the burnout speed
    delta; the ignition-loss yardstick needs an instant run from the same release
    state, so a pad instant run is not one for a silo."""
    resolved = _tiny_resolved()
    pad = sim.run_resolved(resolved.baseline)
    silo = sim.run_resolved(resolved.variants["silo"])
    vehicle = resolved.baseline.to_vehicle()
    comp = sim.compare(silo.result, pad.result, vehicle, instant=pad.result)
    assert comp["identity_point"] == "stage1_burnout"
    assert abs(comp["identity_line_residual_mps"]) < 1e-9
    assert comp["d_speed_mps"] == pytest.approx(comp["stage1_burnout_speed_delta_mps"], abs=1e-12)
    assert comp["d_speed_release_mps"] == pytest.approx(silo.result.metrics["exit_speed_mps"])
    assert comp["d_drag_mps"] == 0.0 and comp["d_back_pressure_mps"] == 0.0
    assert comp["ignition_loss_integrated_mps"] is None  # the pad releases at rest
    assert comp["ignition_loss_formula_mps"] == silo.result.metrics["ignition_loss_formula_mps"]
    assert comp["hold_down_credit_mps"] == pytest.approx(
        pad.result.metrics["preflight_burn_cost_mps"]
        - silo.result.metrics["preflight_burn_cost_mps"]
    )
    assert comp["unexplained_gain_mps"] <= sim.IDENTITY_TOL_MPS
    same = sim.compare(silo.result, pad.result, vehicle, instant=silo.result)
    assert same["ignition_loss_integrated_mps"] == 0.0
    # the payload equivalent solves the ideal two-stage rocket equation for the
    # burnout speed delta; the equation is written here from the toy vehicle file
    # (fairing dropped at staging, screening Isp per stage), not taken from the package
    payload0 = t_to_kg(_toy_value(resolved, "payload_mass_t"))
    dv = comp["stage1_burnout_speed_delta_mps"]
    gain = comp["ideal_screening_payload_equiv_kg"]
    assert gain > 0.0
    assert _toy_ideal_dv(resolved, payload0 + gain) == pytest.approx(
        _toy_ideal_dv(resolved, payload0) - dv, rel=1e-9
    )
    # the README yardstick: the same equation at the speed at release alone; 0 for a
    # pad (released at rest)
    v_release = silo.result.metrics["speed_at_release_mps"]
    yardstick = comp["ideal_screening_payload_at_release_speed_kg"]
    assert 0.0 < yardstick
    assert _toy_ideal_dv(resolved, payload0 + yardstick) == pytest.approx(
        _toy_ideal_dv(resolved, payload0) - v_release, rel=1e-9
    )
    assert (
        sim.compare(pad.result, pad.result, vehicle)["ideal_screening_payload_at_release_speed_kg"]
        == 0.0
    )
    loss = sim.payload_equiv_kg(vehicle, -dv)
    assert loss < 0.0
    assert _toy_ideal_dv(resolved, payload0 + loss) == pytest.approx(
        _toy_ideal_dv(resolved, payload0) + dv, rel=1e-9
    )
    assert sim.payload_equiv_kg(vehicle, -1e6) is None  # beyond an empty payload bay


def _toy_value(resolved: ResolvedExperiment, path: str) -> float:
    """A number of the toy vehicle file (dotted path; list segments by index)."""
    node: object = resolved.baseline.vehicle_dict
    for seg in path.split("."):
        node = node[int(seg)] if isinstance(node, list) else node[seg]  # type: ignore[index]
    return float(node["value"] if isinstance(node, dict) else node)  # type: ignore[index]


def _toy_ideal_dv(resolved: ResolvedExperiment, payload_kg: float) -> float:
    """The ideal two-stage rocket equation of the toy vehicle, written out: stage 1
    burns with stage 2, the fairing and the payload on top; stage 2 burns with the
    payload alone (fairing_drop: staging); c_i = g0 x screening Isp_i."""
    dry1 = t_to_kg(_toy_value(resolved, "stages.0.dry_mass_t"))
    prop1 = t_to_kg(_toy_value(resolved, "stages.0.propellant_mass_t"))
    dry2 = t_to_kg(_toy_value(resolved, "stages.1.dry_mass_t"))
    prop2 = t_to_kg(_toy_value(resolved, "stages.1.propellant_mass_t"))
    fairing = t_to_kg(_toy_value(resolved, "fairing_mass_t"))
    c1 = G0_MPS2 * _toy_value(resolved, "screening.stage_isp_eff_s.0")
    c2 = G0_MPS2 * _toy_value(resolved, "screening.stage_isp_eff_s.1")
    assert resolved.baseline.vehicle_dict["fairing_drop"] == "staging"
    top1 = dry2 + prop2 + fairing + payload_kg
    return c1 * math.log((dry1 + prop1 + top1) / (dry1 + top1)) + c2 * math.log(
        (dry2 + prop2 + payload_kg) / (dry2 + payload_kg)
    )


def test_variant_rows_insert_the_ignition_rows_and_the_flight_pair_only_when_it_differs() -> None:
    """The per-variant table names how each run ignites (rows keyed by the first
    stage's name, after the flags row) and prints the before-flight burn pair only when
    some run burned more before its flight than before its release."""
    resolved = _tiny_resolved()
    pad = sim.run_resolved(resolved.baseline)
    er = sim.ExperimentResult("tiny", "toy", pad, {}, {}, {"hash": "x"}, "20260101T000000Z")
    rows = sim.variant_rows(er)
    keys = [key for _label, _source, key in rows]
    assert sim.first_stage_name(er) == "stage1"
    ignition = [key for _label, _source, key in sim.ignition_rows("stage1")]
    assert ignition == ["t_ign_rel_release_s_stage1", "startup_kind_stage1", "t_startup_s_stage1"]
    i_flags = keys.index("", 1)  # status and flags both have an empty key; flags is second
    assert keys[i_flags + 1 : i_flags + 1 + len(ignition)] == ignition  # right after flags
    assert all(k in keys for k in ignition) and "propellant_burned_before_flight_kg" not in keys
    assert pad.result.metrics["startup_kind_stage1"] == "step"  # the toy's 0 s ramp
    assert pad.result.metrics["t_startup_s_stage1"] == 0.0
    m = pad.result.metrics
    extended = replace(
        pad,
        result=replace(
            pad.result,
            metrics={
                **m,
                "propellant_burned_before_flight_kg": m["propellant_burned_before_release_kg"]
                + 1.0,
            },
        ),
    )
    er2 = replace(er, baseline=extended)
    keys2 = [key for _label, _source, key in sim.variant_rows(er2)]
    i = keys2.index("dv_vac_equiv_before_release_mps")
    assert keys2[i + 1 : i + 3] == [
        "propellant_burned_before_flight_kg",
        "dv_vac_equiv_before_flight_mps",
    ]
    assert sim.step_startup_note(er.runs, "stage1").startswith(
        "Note: pad: stage-1 startup kind step"
    )
    assert sim.step_startup_note(er.runs, "other_stage") == ""


def test_si_value_converts_by_the_yaml_suffix() -> None:
    """The sensitivity table's SI column: tonnes, kN, degrees, km, g and kWh convert
    through units.py by the key's suffix (a list index at the end is skipped); s, m,
    kg and friends are SI already; no listed suffix means dimensionless."""
    assert sim.si_value("vehicle.stages.stage1.dry_mass_t", 28.16) == (
        pytest.approx(28160.0),
        "kg",
    )
    assert sim.si_value("vehicle.stages.stage1.engine.thrust_vac_kN", 914.1) == (
        pytest.approx(914100.0),
        "N",
    )
    assert sim.si_value("site.azimuth_deg", 90.0) == (pytest.approx(math.pi / 2), "rad")
    assert sim.si_value("track.length_km", 0.1) == (pytest.approx(100.0), "m")
    assert sim.si_value("assist.net_accel_g", 3.0) == (pytest.approx(3.0 * G0_MPS2), "m/s^2")
    assert sim.si_value("battery.energy_kWh", 1.0) == (pytest.approx(3.6e6), "J")
    assert sim.si_value("vehicle.screening.stage_isp_eff_s.0", 295.0) == (295.0, "s")
    assert sim.si_value("assist.stroke_m", 100.0) == (100.0, "m")
    assert sim.si_value("assist.drive_efficiency", 0.55) == (0.55, sim.DIMENSIONLESS_UNIT)
    assert sim.si_value("vehicle.stages.stage1.dry_mass_t", None) == (None, "kg")


def _tiny_with_sensitivity() -> ResolvedExperiment:
    """The tiny experiment plus a sensitivity block: one vehicle and one run parameter
    on the silo variant."""
    data = Path(__file__).resolve().parent / "data"
    exp = yaml.safe_load((data / "tiny_experiment.yaml").read_text(encoding="utf-8"))
    exp["sensitivity"] = {
        "of": ["silo"],
        "params": {"vehicle.stages.stage1.dry_mass_t": 0.1, "assist.drive_efficiency": 0.1},
    }
    vehicle = yaml.safe_load((data / "toy_vehicle.yaml").read_text(encoding="utf-8"))
    return resolve_experiment(exp, vehicle)


def test_sensitivity_rows_compare_against_both_baselines_and_table_shape() -> None:
    """Every case is compared against the unchanged baseline and, for a vehicle
    parameter, against the baseline carrying the same perturbation; a run parameter
    leaves the baseline alone; the table has one row per case plus the C_D row."""
    resolved = _tiny_with_sensitivity()
    baseline = sim.run_resolved(resolved.baseline)
    rows = sim.run_sensitivity(resolved, baseline)
    assert [(r.param, r.fraction) for r in rows] == [
        ("vehicle.stages.stage1.dry_mass_t", 0.1),
        ("vehicle.stages.stage1.dry_mass_t", -0.1),
        ("assist.drive_efficiency", 0.1),
        ("assist.drive_efficiency", -0.1),
    ]
    dry_up, dry_down, eta_up, eta_down = rows
    assert dry_up.value_yaml_units == pytest.approx(0.2 * 1.1)  # t, as in the vehicle file
    assert dry_down.value_yaml_units == pytest.approx(0.2 * 0.9)
    assert eta_up.value_yaml_units == pytest.approx(0.55)
    assert eta_down.value_yaml_units == pytest.approx(0.45)
    assert (dry_up.value_si, dry_up.value_si_unit) == (pytest.approx(t_to_kg(0.2 * 1.1)), "kg")
    assert (eta_up.value_si, eta_up.value_si_unit) == (pytest.approx(0.55), "-")
    for row in (dry_up, dry_down):
        assert row.is_vehicle_param and row.baseline_perturbed is not None
        assert row.baseline_perturbed.name == baseline.name
        base_m = row.baseline_perturbed.result.metrics
        assert base_m["liftoff_mass_kg"] == pytest.approx(
            row.result.result.metrics["liftoff_mass_kg"]
        )
        assert (
            base_m["stage1_burnout_speed_mps"]
            != baseline.result.metrics["stage1_burnout_speed_mps"]
        )
        assert row.comparison_perturbed["stage1_burnout_speed_delta_mps"] == pytest.approx(
            row.result.result.metrics["stage1_burnout_speed_mps"]
            - base_m["stage1_burnout_speed_mps"]
        )
        assert abs(row.comparison_perturbed["identity_line_residual_mps"]) < 1e-9
    assert dry_up.baseline_perturbed is not dry_down.baseline_perturbed
    for row in (eta_up, eta_down):
        assert not row.is_vehicle_param and row.baseline_perturbed is None
        assert row.comparison_perturbed is row.comparison
        assert row.result.result.metrics["stage1_burnout_speed_mps"] == pytest.approx(
            baseline.result.metrics["stage1_burnout_speed_mps"]
            + row.comparison["stage1_burnout_speed_delta_mps"]
        )
    assert eta_up.result.result.metrics["electrical_energy_J"] * 0.55 == pytest.approx(
        eta_down.result.result.metrics["electrical_energy_J"] * 0.45
    )
    # run_names filters by the parent run; an unknown name runs nothing
    assert sim.run_sensitivity(resolved, baseline, {"pad"}) == []
    assert len(sim.run_sensitivity(resolved, baseline, {"silo"})) == 4

    table = sim.sensitivity_table(rows).splitlines()
    assert table[0] == "| " + " | ".join(sim.SENSITIVITY_HEADER) + " |"
    body = table[2:]
    assert len(body) == 4 + 1
    assert body[-1].startswith("| silo | C_D | +/-10% | ") and sim.CD_SENSITIVITY_NOTE in body[-1]
    assert "(= unchanged)" in body[2] and "(= unchanged)" not in body[0]
    assert all(len(line.split("|")) == len(sim.SENSITIVITY_HEADER) + 2 for line in body)
    assert "YAML units" in table[0]  # the one column not in SI says so
    assert "| value [SI] (unit in the cell) |" in table[0]
    assert body[0].split("|")[4].strip() == f"{sim._fmt(t_to_kg(0.2 * 1.1))} kg"
    assert body[2].split("|")[4].strip() == "0.55 -"
    # both payload equivalents are columns, the same-perturbation one beside the other
    i_same = sim.SENSITIVITY_HEADER.index(
        "ideal-screening payload equiv. of the same-perturbation delta [kg]"
    )
    assert sim.SENSITIVITY_HEADER[i_same - 1].endswith("of the unchanged delta [kg]")
    assert body[0].split("|")[i_same + 1].strip() == sim._signed(
        dry_up.comparison_perturbed["ideal_screening_payload_equiv_kg"]
    )
    # without a case the table is the reason none ran, never a C_D-only table
    assert sim.sensitivity_table([]) == sim.SENSITIVITY_NONE_DECLARED
    assert sim.sensitivity_table([], "(why)") == "(why)"
    assert sim.CD_SENSITIVITY_NOTE in sim.SENSITIVITY_NONE_DECLARED
    assert sim.CD_SENSITIVITY_NOTE not in sim.SENSITIVITY_SWEEP_POINT

    record = sim.sensitivity_record(dry_up)
    assert record["of"] == "silo" and record["baseline_perturbed"] is True
    assert record["value_yaml_units"] == dry_up.value_yaml_units and "value" not in record
    assert record["value_si"] == dry_up.value_si and record["value_si_unit"] == "kg"
    assert record["stage1_burnout_speed_delta_vs_perturbed_baseline_mps"] == pytest.approx(
        dry_up.comparison_perturbed["stage1_burnout_speed_delta_mps"]
    )
    assert set(record["metrics"]) >= {"status", "flags", "stage1_burnout_speed_mps"}
    sim.write_json(Path(os.devnull), record)  # JSON-safe


def test_run_experiment_writes_sensitivity_and_the_no_sensitivity_switch(tmp_path: Path) -> None:
    resolved = _tiny_with_sensitivity()
    er, out_dir = sim.run_experiment(resolved, tmp_path, plots=False, repo_root=tmp_path)
    assert len(er.sensitivity) == 4
    metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert [c["param"] for c in metrics["sensitivity"]] == [r.param for r in er.sensitivity]
    summary = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert "| silo | vehicle.stages.stage1.dry_mass_t | +10% |" in summary
    assert "| silo | C_D | +/-10% |" in summary
    er2, out_dir2 = sim.run_experiment(
        resolved, tmp_path, plots=False, repo_root=tmp_path, sensitivity=False
    )
    assert er2.sensitivity == [] and er2.sensitivity_note == sim.SENSITIVITY_SKIPPED
    assert json.loads((out_dir2 / "metrics.json").read_text(encoding="utf-8"))["sensitivity"] == []
    summary2 = (out_dir2 / "summary.md").read_text(encoding="utf-8")
    assert sim.SENSITIVITY_SKIPPED in summary2 and "| C_D |" not in summary2
    # declared for the silo only: a pad-only run has no case and says so
    er3, _out_dir3 = sim.run_experiment(
        resolved, tmp_path, plots=False, repo_root=tmp_path, only_variant="silo"
    )
    assert len(er3.sensitivity) == 4
    sweep = sim.write_single(
        er3.variants["silo"], er3.baseline, er3, tmp_path / "single", plots=False
    )
    assert sim.SENSITIVITY_SWEEP_POINT in (sweep / "summary.md").read_text(encoding="utf-8")


# ------------------------------------------------------------- preflight (SP1 step 3)

TINY_SILO_EXIT_MPS = math.sqrt(2.0 * G0_MPS2 * 20.0)
"""Exit speed of the tiny experiment's 1 g0, 20 m silo [m/s] (19.8 m/s)."""


def _tiny_dicts() -> tuple[dict, dict]:
    """tests/data/tiny_experiment.yaml and its toy vehicle as raw dicts."""
    data = Path(__file__).resolve().parent / "data"
    exp = yaml.safe_load((data / "tiny_experiment.yaml").read_text(encoding="utf-8"))
    veh = yaml.safe_load((data / "toy_vehicle.yaml").read_text(encoding="utf-8"))
    return exp, veh


def _no_run(run_config: RunConfig, vehicle: Vehicle) -> sim.Result:
    raise AssertionError("a run started although the preflight should have refused")


def test_preflight_refuses_a_bad_ramp_start_before_any_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configuration that resolves but whose ramp start cannot be converted (a speed
    above the exit speed sqrt(2 a L) of the 1 g0, 20 m silo, 19.8 m/s; a height at or
    above the drag-free apex v_exit^2 / (2 g_eff), 20.0 m) is refused by the preflight
    sim.check_resolved, naming the run and where it comes from (a variant, a sweep
    point, a sensitivity run whose -10 % acceleration lowers the exit speed below the
    requested speed), before run_experiment and run_sweep create anything: no results
    directory, no run started."""
    monkeypatch.setattr(sim, "run", _no_run)
    exp, veh = _tiny_dicts()
    exp["variants"]["fast"] = {
        **exp["variants"]["silo"],
        "ignition": {"stage1": {"at_speed_mps": 25.0}},
    }
    resolved = resolve_experiment(exp, veh)
    assert TINY_SILO_EXIT_MPS < 25.0
    with pytest.raises(ValueError, match=r"run 'fast': at_speed_mps 25 m/s exceeds"):
        sim.run_experiment(resolved, tmp_path, plots=False, repo_root=tmp_path)
    assert list(tmp_path.iterdir()) == []
    exp, veh = _tiny_dicts()
    exp["sweeps"] = [
        {
            "of": "silo",
            "axes": {
                "ignition.stage1.at_height_m": [5.0, 25.0],
                "ignition.stage1.height_method": ["closed_form"],
            },
        }
    ]
    resolved = resolve_experiment(exp, veh)
    point = resolved.sweeps[0][1].run
    assert point.run_dict["ignition"]["stage1"] == {
        "at_height_m": 25.0,
        "height_method": "closed_form",
    }
    with pytest.raises(
        ValueError, match=r"sweep 1 point run_0002: at_height_m 25 m is at or above"
    ):
        sim.run_sweep(resolved, tmp_path, plots=False, repo_root=tmp_path)
    assert list(tmp_path.iterdir()) == []
    exp, veh = _tiny_dicts()
    exp["variants"]["near"] = {
        **exp["variants"]["silo"],
        "ignition": {"stage1": {"at_speed_mps": 19.0}},
    }
    exp["sensitivity"] = {"of": ["near"], "params": {"assist.net_accel_g": 0.1}}
    resolved = resolve_experiment(exp, veh)
    assert TINY_SILO_EXIT_MPS * math.sqrt(0.9) < 19.0 < TINY_SILO_EXIT_MPS
    with pytest.raises(ValueError, match=r"sensitivity run 'near__assist\.net_accel_g__-0\.1'"):
        sim.run_experiment(resolved, tmp_path, plots=False, repo_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_preflight_visits_every_resolved_run_and_passes_the_shipped_experiments(
    repo_root: Path, planar_pins: ModuleType
) -> None:
    """sim.every_resolved_run lists the same runs, in the same order, as the planar pin's
    inventory (baseline and variants, sweep points with their paired baselines,
    sensitivity runs, bound runs with their paired baselines, calibration cases), and
    the preflight passes on every shipped experiment."""
    from launchsim.cli import load_experiment

    for path in sorted((repo_root / "experiments").glob("*.yaml")):
        resolved = load_experiment(path)
        listed = [run for _label, run in sim.every_resolved_run(resolved)]
        pinned = list(planar_pins.resolved_runs(resolved).values())
        assert [id(r) for r in listed] == [id(r) for r in pinned], path.name
        sim.check_resolved(resolved)
