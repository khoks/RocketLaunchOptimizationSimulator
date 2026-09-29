"""CLI smoke tests: run and sweep on the tiny experiment write the results layout, print
ASCII only and exit 0; a bad configuration exits 1 without a traceback."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from launchsim import sim
from launchsim.cli import main

TINY = Path(__file__).resolve().parent / "data" / "tiny_experiment.yaml"
TOY_VEHICLE = TINY.parent / "toy_vehicle.yaml"


def _only_run_dir(root: Path, experiment: str) -> Path:
    dirs = sorted((root / experiment).iterdir())
    assert len(dirs) == 1, dirs
    return dirs[0]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _copy_tiny(into: Path, **changes: object) -> Path:
    """Write a copy of the tiny experiment (plus its vehicle) into ``into`` with top-level
    keys replaced by ``changes``; returns the experiment path."""
    into.mkdir(parents=True, exist_ok=True)
    exp = yaml.safe_load(TINY.read_text(encoding="utf-8"))
    exp.update(changes)
    path = into / "experiment.yaml"
    path.write_text(yaml.safe_dump(exp, sort_keys=False), encoding="utf-8")
    (into / "toy_vehicle.yaml").write_bytes(TOY_VEHICLE.read_bytes())
    return path


def test_run_writes_layout_and_prints_ascii(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(TINY), "--results-root", str(tmp_path), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 0, out
    out.encode("ascii")  # pure ASCII stdout
    run_dir = _only_run_dir(tmp_path, "tiny_experiment")
    assert _ascii(str(run_dir)) in out  # say() escapes non-ASCII temp paths
    assert "pad (baseline): nominal" in out
    assert "silo: nominal" in out

    for name in ("resolved_config.yaml", "metrics.json", "summary.md"):
        assert (run_dir / name).is_file(), name
    for variant in ("pad", "silo"):
        assert (run_dir / variant / "timeseries.csv").is_file()
        assert (run_dir / variant / "events.csv").is_file()
    assert not (run_dir / "plots").exists()  # --no-plots

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["timestamp_utc"] == run_dir.name.split("-")[0]  # one clock read
    assert set(metrics["runs"]) == {"pad", "silo"}
    assert metrics["runs"]["silo"]["status"] == "nominal"
    assert metrics["runs"]["silo"]["assist_model"] == "constant_accel"
    assert metrics["runs"]["pad"]["liftoff_mass_kg"] == pytest.approx(1360.0)
    assert metrics["comparison"]["silo"]["delta_liftoff_mass_kg"] == 0.0
    assert metrics["git"]["hash"]

    cfg = yaml.safe_load((run_dir / "resolved_config.yaml").read_text(encoding="utf-8"))
    assert cfg["experiment"] == "tiny_experiment"
    assert cfg["vehicle"]["name"] == "toy_vehicle"
    assert cfg["runs"]["silo"]["run"]["assist"]["model"] == "constant_accel"

    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# tiny_experiment")
    assert "Comparison basis: sweep-optimized (Phase 1 has no guidance parameters)" in summary
    assert "## Assumptions" in summary
    assert "constant_accel" in summary
    header = next(line for line in summary.splitlines() if line.startswith("| run | status |"))
    for key in sim.REQUIRED_METRICS:  # the CLAUDE.md summary list is always a column
        assert f" {key} " in header, key

    silo_rows = (run_dir / "silo" / "timeseries.csv").read_text(encoding="utf-8").splitlines()
    assert silo_rows[0] == ",".join(sim.TIMESERIES_COLUMNS) and len(silo_rows) > 100
    events = (run_dir / "silo" / "events.csv").read_text(encoding="utf-8").splitlines()
    assert events[0] == ",".join(sim.EVENT_COLUMNS) and len(events) > 3
    assert metrics["runs"]["silo"]["exit_speed_mps"] > 0.0
    pad_rows = (run_dir / "pad" / "timeseries.csv").read_text(encoding="utf-8").splitlines()
    assert pad_rows[0] == ",".join(sim.TIMESERIES_COLUMNS) and len(pad_rows) > 100
    assert metrics["runs"]["pad"]["status"] == "nominal"
    assert metrics["runs"]["pad"]["stage1_burnout_t_s"] == pytest.approx(160.0, rel=1e-9)


def test_second_run_creates_a_new_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["run", str(TINY), "--results-root", str(tmp_path), "--no-plots"]) == 0
    assert main(["run", str(TINY), "--results-root", str(tmp_path), "--no-plots"]) == 0
    capsys.readouterr()
    dirs = sorted((tmp_path / "tiny_experiment").iterdir())
    assert len(dirs) == 2
    assert dirs[0] != dirs[1]
    assert all((d / "summary.md").is_file() for d in dirs)


def test_run_single_variant(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["run", str(TINY), "--results-root", str(tmp_path), "--no-plots"]
    assert main([*args, "--variant", "silo"]) == 0
    run_dir = _only_run_dir(tmp_path, "tiny_experiment")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert set(metrics["runs"]) == {"pad", "silo"}
    capsys.readouterr()
    assert main([*args, "--variant", "nope"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("error:")
    assert "nope" in out and "Traceback" not in out


def test_invalid_config_exits_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exp = yaml.safe_load(TINY.read_text(encoding="utf-8"))
    exp["baseline"]["site"]["include_rotation"] = True
    bad = tmp_path / "bad_experiment.yaml"
    bad.write_text(yaml.safe_dump(exp), encoding="utf-8")
    (tmp_path / "toy_vehicle.yaml").write_bytes((TINY.parent / "toy_vehicle.yaml").read_bytes())
    code = main(["run", str(bad), "--results-root", str(tmp_path / "results"), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 1
    assert out.startswith("error:")
    assert "Phase 2" in out
    assert "Traceback" not in out
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("which", ["experiment", "vehicle"])
def test_non_utf8_file_exits_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], which: str
) -> None:
    """A YAML saved as ANSI/cp1252 with a degree sign (a Windows editor default) is a
    configuration error, not a traceback: UnicodeDecodeError is a ValueError, not an
    OSError, so load_yaml must catch it itself."""
    exp = _copy_tiny(tmp_path / "proj")
    target = exp if which == "experiment" else exp.parent / "toy_vehicle.yaml"
    target.write_bytes("# latitude 28.5\u00b0\n".encode("cp1252") + target.read_bytes())
    root = tmp_path / "results"
    code = main(["run", str(exp), "--results-root", str(root), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error:") and "Traceback" not in out, out
    assert "not UTF-8" in out and target.name in out
    assert not root.exists()


def test_drive_relative_vehicle_path_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``C:x`` resolves through Windows' hidden per-drive cwd: refused, never joined."""
    exp = _copy_tiny(tmp_path / "proj", vehicle="C:toy_vehicle.yaml")
    code = main(["run", str(exp), "--results-root", str(tmp_path / "results")])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error: vehicle path"), out
    assert "drive-relative" in out and "Traceback" not in out
    assert not (tmp_path / "results").exists()


def test_no_command_is_a_usage_error_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_missing_experiment_file_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(tmp_path / "missing.yaml"), "--results-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error:") and "not found" in out


def test_directory_as_experiment_path_exits_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run", str(tmp_path), "--results-root", str(tmp_path / "results")])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error: cannot read"), out
    assert "Traceback" not in out
    assert not (tmp_path / "results").exists()


def test_results_root_that_is_a_file_exits_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "results"
    blocker.write_text("not a directory", encoding="utf-8")
    code = main(["run", str(TINY), "--results-root", str(blocker), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error:") and "Traceback" not in out, out
    assert blocker.read_text(encoding="utf-8") == "not a directory"


@pytest.mark.parametrize("bad_experiment_name", ["..", "C:/x", "a:b", "a/b", "silo.", "NUL"])
def test_unsafe_experiment_name_exits_1_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bad_experiment_name: str
) -> None:
    exp = _copy_tiny(tmp_path / "proj", name=bad_experiment_name)
    root = tmp_path / "results"
    code = main(["run", str(exp), "--results-root", str(root), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error:") and "Traceback" not in out, out
    assert "not a valid results directory name" in out or "reserved" in out
    assert not root.exists()
    assert sorted(p.name for p in (tmp_path / "proj").iterdir()) == [
        "experiment.yaml",
        "toy_vehicle.yaml",
    ]


@pytest.mark.parametrize("bad_variant_name", ["..", "plots", "a/b", "C:/x", "sweep_1"])
def test_unsafe_variant_name_exits_1_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bad_variant_name: str
) -> None:
    base = yaml.safe_load(TINY.read_text(encoding="utf-8"))
    variants = {bad_variant_name: base["variants"]["silo"]}
    exp = _copy_tiny(tmp_path / "proj", variants=variants, sweeps=[])
    root = tmp_path / "results"
    code = main(["run", str(exp), "--results-root", str(root), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error:") and "Traceback" not in out, out
    assert not root.exists()


def test_default_results_root_is_the_repo_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --results-root the results tree lives next to the pyproject.toml that owns
    the experiment file, whatever the current directory is."""
    proj = tmp_path / "proj"
    exp = _copy_tiny(proj / "experiments")
    (proj / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    code = main(["run", str(exp), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 0, out
    run_dir = _only_run_dir(proj / "results", "tiny_experiment")
    assert (run_dir / "summary.md").is_file()
    assert not (elsewhere / "results").exists()


def test_posix_rooted_vehicle_path_is_not_joined(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exp = _copy_tiny(tmp_path / "proj", vehicle="/no/such/dir/toy_vehicle.yaml")
    code = main(["run", str(exp), "--results-root", str(tmp_path / "results")])
    out = capsys.readouterr().out
    assert code == 1 and out.startswith("error: vehicle file not found"), out
    assert "tried" not in out  # used as given, never joined onto the experiment dir
    assert not (tmp_path / "results").exists()


def test_help_in_subprocess_exits_0() -> None:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "launchsim", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "run" in proc.stdout and "sweep" in proc.stdout


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out.startswith("launchsim ")


def test_sweep_writes_points_and_index(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["sweep", str(TINY), "--results-root", str(tmp_path), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 0, out
    out.encode("ascii")
    run_dir = _only_run_dir(tmp_path, "tiny_experiment")
    sweep_dir = run_dir / "sweep_1"
    point_files = (
        "resolved_config.yaml",
        "metrics.json",
        "summary.md",
        "timeseries.csv",
        "events.csv",
    )
    for i in range(1, 5):
        point = sweep_dir / f"run_{i:04d}"
        for name in point_files:
            assert (point / name).is_file(), point / name
    assert not (sweep_dir / "run_0005").exists()
    assert not (run_dir / sim.FAILED_MARKER).exists()
    for name in point_files:
        assert (run_dir / "baseline" / name).is_file(), name
    base_cfg = _load_yaml(run_dir / "baseline" / "resolved_config.yaml")
    assert base_cfg["run"]["name"] == "pad" and base_cfg["run"]["assist"]["model"] == "none"
    cfg1 = _load_yaml(sweep_dir / "run_0001" / "resolved_config.yaml")
    assert cfg1["run"]["assist"]["stroke_m"] == 10 and cfg1["run"]["assist"]["net_accel_g"] == 1

    # a per-point summary names its sweep, position, parent run and axis values
    point_summary = (sweep_dir / "run_0002" / "summary.md").read_text(encoding="utf-8")
    assert (
        "- Sweep: sweep_1, point 2 of 4 (of silo): assist.net_accel_g = 1, assist.stroke_m = 20"
        in point_summary
    )
    # the top-level summary's assumptions cover the swept points, not only the baseline
    top = (run_dir / "summary.md").read_text(encoding="utf-8")
    assumptions = top.split("## Assumptions")[1]
    assert "constant_accel: prescribed net acceleration 1 g0 (assumed)" in assumptions
    assert "sweep_1/run_0001" in assumptions
    assert "[all runs]" in assumptions  # the Phase 1 lines are shared by pad and every point
    assert "constant_accel: carriage mass 0 t (assumed) [all sweep points]" in assumptions

    with (sweep_dir / "sweep_index.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    assert [r["run_dir"] for r in rows] == [f"sweep_1/run_{i:04d}" for i in range(1, 5)]
    grid = [(float(r["assist.net_accel_g"]), float(r["assist.stroke_m"])) for r in rows]
    assert grid == [(1, 10), (1, 20), (2, 10), (2, 20)]  # itertools.product, axis order
    assert all(r["status"] == "nominal" for r in rows)
    point3 = json.loads((sweep_dir / "run_0003" / "metrics.json").read_text(encoding="utf-8"))
    assert point3["run"] == "run_0003" and point3["baseline"] == "pad"


@pytest.mark.slow
def test_full_experiment_with_plots_enabled_writes_pad_plots(
    repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shipped experiment runs end to end with plots on: every run, pad and silo,
    gets its PNGs. Build step 9 curates the plotted set."""
    exp = repo_root / "experiments" / "silo_screening_1d.yaml"
    code = main(["run", str(exp), "--results-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0, out
    out.encode("ascii")
    run_dir = _only_run_dir(tmp_path, "silo_screening_1d")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert len(metrics["runs"]) == 10  # pad + 9 variants
    assert (run_dir / "silo_failed" / "timeseries.csv").is_file()
    assert metrics["runs"]["pad"]["status"] == "nominal"
    assert metrics["runs"]["pad_instant"]["status"] == "nominal"
    assert metrics["runs"]["silo_cold"]["status"] == "nominal"
    assert metrics["runs"]["silo_failed"]["status"] == "impact"
    assert (run_dir / "plots" / "pad_v_mps.png").is_file()
    assert (run_dir / "plots" / "silo_cold_v_mps.png").is_file()
