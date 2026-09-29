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
    assert summary.startswith(f"# tiny_experiment ({run_dir.name.split('-')[0]}, git ")
    assert "Comparison basis: sweep-optimized (Phase 1 has no guidance parameters)" in summary
    assert "## Assumptions" in summary
    assert "constant_accel" in summary
    header = next(line for line in summary.splitlines() if line.startswith("| quantity |"))
    assert header == "| quantity | pad (baseline) | silo |"
    row_keys = {key for _label, _source, key in sim.VARIANT_ROWS}
    for key in sim.REQUIRED_METRICS:  # the CLAUDE.md summary list is always a row
        assert key in row_keys, key
    assert "| max-Q [Pa] | n/a (Phase 2) | n/a (Phase 2) |" in summary
    assert "## Sensitivity" in summary and sim.SENSITIVITY_NONE_DECLARED in summary
    assert sim.CD_SENSITIVITY_NOTE in summary and "| C_D |" not in summary
    assert "## Checks" in summary
    assert "- silo: delta speed at stage1_burnout " in summary and "closes" in summary
    assert "No variant exceeds its release speed + hold-down credit + altitude term" in summary
    comp = metrics["comparison"]["silo"]
    assert abs(comp["identity_line_residual_mps"]) < sim.IDENTITY_TOL_MPS
    assert comp["d_speed_mps"] == pytest.approx(comp["stage1_burnout_speed_delta_mps"])
    assert metrics["sensitivity"] == []  # the tiny experiment declares none
    # the README yardstick sits under the payload equivalent, and a pad has no track:
    # every assist item of the pad column is 0 (one convention), never a mix with n/a
    rows = {line.split("|")[1].strip(): line for line in summary.splitlines() if "|" in line}
    yardstick = next(k for k in rows if k.startswith("ideal screening at this run's speed"))
    assert rows[yardstick].split("|")[2].strip() == "(baseline)"
    assert comp["ideal_screening_payload_at_release_speed_kg"] > 0.0
    for label in (
        "assist (drive) energy [J]",
        "electrical energy [kWh]",
        "peak drive power [W]",
        "interface force, peak [N]",
        "interface force, minimum [N]",
        "peak track-normal g [g0]",
        "vehicle [g0]",
        "carriage [g0]",
        "braking distance [m]",
        "facility length incl. braking [m]",
    ):
        assert rows[label].split("|")[2].strip() == "0", label
    assert rows["peak felt g on the track [g0]"].split("|")[2].strip() == "n/a"  # no track
    assert "mass there [kg]" in rows and rows["mass there [kg]"].split("|")[3].strip() != "n/a"
    hold = next(k for k in rows if k.startswith("hold-down force m g_eff - T"))
    assert "clamps in tension" in hold  # the sign convention is on the label
    # the table says how each column ignites (t_ign, startup kind and its duration) and
    # marks a step startup as the yardstick it is; the toy's 0 s ramp is a step
    t_ign = next(k for k in rows if k.startswith("stage-1 ignition, t_ign relative to release"))
    assert [c.strip() for c in rows[t_ign].split("|")[2:4]] == ["0", "0.5"]
    kind = next(k for k in rows if k.startswith("stage-1 startup kind"))
    assert [c.strip() for c in rows[kind].split("|")[2:4]] == ["step", "step"]
    assert [c.strip() for c in rows["its t_ramp or tau [s]"].split("|")[2:4]] == ["0", "0"]
    note = next(line for line in summary.splitlines() if line.startswith("Note: "))
    assert note.startswith("Note: pad, silo: stage-1 startup kind step is instant full thrust")
    assert "unphysical" in note
    # the before-flight pair is printed only when it differs from the before-release
    # pair for some run (no hold extension here), and the gravity model is one line
    assert not any(k.startswith("propellant burned before the free flight") for k in rows)
    gravity = [ln for ln in summary.splitlines() if ln.startswith("- gravity mu/r^2")]
    assert len(gravity) == 1 and "ConstantGravity exists only for tests" in gravity[0]
    assert "InverseSquareGravity" in gravity[0] and "[all runs]" in gravity[0]

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

    # a per-point summary names its sweep, position, parent run and axis values, and
    # says that a sweep point runs no sensitivity case instead of a C_D-only table
    point_summary = (sweep_dir / "run_0002" / "summary.md").read_text(encoding="utf-8")
    assert (
        "- Sweep: sweep_1, point 2 of 4 (of silo): assist.net_accel_g = 1, assist.stroke_m = 20"
        in point_summary
    )
    assert sim.SENSITIVITY_SWEEP_POINT in point_summary and "| C_D |" not in point_summary
    # the top-level summary's assumptions cover the swept points, not only the baseline
    top = (run_dir / "summary.md").read_text(encoding="utf-8")
    assumptions = top.split("## Assumptions")[1]
    assert "constant_accel: prescribed net acceleration 1 g0 (assumed)" in assumptions
    assert "sweep_1/run_0001" in assumptions
    assert "[all runs]" in assumptions  # the Phase 1 lines are shared by pad and every point
    assert "constant_accel: carriage mass 0 t (assumed) [all sweep points]" in assumptions

    rows = _read_index(sweep_dir)
    assert len(rows) == 4
    assert [r["run_dir"] for r in rows] == [f"sweep_1/run_{i:04d}" for i in range(1, 5)]
    grid = [(float(r["assist.net_accel_g"]), float(r["assist.stroke_m"])) for r in rows]
    assert grid == [(1, 10), (1, 20), (2, 10), (2, 20)]  # itertools.product, axis order
    assert all(r["status"] == "nominal" for r in rows)
    assert list(rows[0]) == [
        "point",
        "assist.net_accel_g",
        "assist.stroke_m",
        "run_dir",
        "of",
        *sim.SWEEP_INDEX_METRICS,
        "status",
    ]
    assert all(float(r["exit_speed_mps"]) > 0.0 for r in rows)
    point3 = json.loads((sweep_dir / "run_0003" / "metrics.json").read_text(encoding="utf-8"))
    assert point3["run"] == "run_0003" and point3["baseline"] == "pad"
    # the point's metrics.json and the index carry the same comparison (computed once)
    assert float(rows[2]["stage1_burnout_speed_delta_mps"]) == pytest.approx(
        point3["comparison"]["stage1_burnout_speed_delta_mps"], rel=1e-11
    )


def _read_index(sweep_dir: Path) -> list[dict[str, str]]:
    with (sweep_dir / "sweep_index.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


SUMMARY_SECTIONS = (
    "## Variants against the baseline",
    "## Sensitivity",
    "## Flags",
    "## Assumptions",
    "## Checks",
)


def test_full_experiment_writes_identity_lines_and_sensitivity(
    repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shipped experiment end to end, plots off: every variant's identity line
    closes to 0.01 m/s (CLAUDE.md), the summary carries its sections in order, the
    bound and the README yardstick are checked in the summary itself, and the
    sensitivity block runs every case against both baselines."""
    exp = repo_root / "experiments" / "silo_screening_1d.yaml"
    code = main(["run", str(exp), "--results-root", str(tmp_path), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 0, out
    out.encode("ascii")
    assert "sensitivity: 16 cases" in out
    run_dir = _only_run_dir(tmp_path, "silo_screening_1d")
    assert not (run_dir / "plots").exists()
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert len(metrics["runs"]) == 10  # pad + 9 variants
    assert (run_dir / "silo_failed" / "timeseries.csv").is_file()
    assert metrics["runs"]["pad"]["status"] == "nominal"
    assert metrics["runs"]["silo_failed"]["status"] == "impact"

    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    positions = [summary.index(s) for s in SUMMARY_SECTIONS]
    assert positions == sorted(positions)
    assert "Comparison basis: sweep-optimized (Phase 1 has no guidance parameters)" in summary
    checks = summary.split("## Checks")[1]
    variants = [name for name in metrics["runs"] if name != "pad"]
    for name in variants:
        comp = metrics["comparison"][name]
        residual = comp["identity_line_residual_mps"]
        assert abs(residual) < sim.IDENTITY_TOL_MPS, (name, residual)
        line = next(ln for ln in checks.splitlines() if ln.startswith(f"- {name}: delta speed"))
        assert "closes" in line and "DOES NOT" not in line, line
        if name == "silo_failed":  # no stage-1 burnout: the bound is not defined
            assert comp["unexplained_gain_mps"] is None
            assert not any(ln.startswith("- silo_failed: gain") for ln in checks.splitlines())
            continue
        assert comp["unexplained_gain_mps"] <= sim.IDENTITY_TOL_MPS, name
        assert (
            comp["ideal_screening_payload_equiv_kg"] is None
            or comp["stage1_burnout_speed_delta_mps"] * comp["ideal_screening_payload_equiv_kg"]
            >= 0.0
        )
    assert "No variant exceeds its release speed + hold-down credit + altitude term" in checks
    assert "Not checkable (no stage-1 burnout on both sides, or no flight budget): silo_failed" in (
        checks
    )
    # the failed run's identity line (impact vs burnout) is marked as not a figure of
    # merit; every other line is not
    bullets = [ln for ln in checks.splitlines() if ln.startswith("- ")]
    identity = {ln.split(":")[0][2:]: ln for ln in bullets if ": delta speed at " in ln}
    assert set(identity) == set(variants)
    assert sim.NOT_A_FIGURE_OF_MERIT in identity["silo_failed"]
    assert not any(
        sim.NOT_A_FIGURE_OF_MERIT in ln for n, ln in identity.items() if n != "silo_failed"
    )
    # rounding noise is printed as 0 with the bound named, a real excess as a number
    bound = {ln.split(":")[0][2:]: ln for ln in bullets if ": gain " in ln}
    assert set(bound) == set(variants) - {"silo_failed"}
    assert bound["silo_instant"].endswith(f"excess 0 (|excess| < {sim.EXCESS_NOISE_MPS:g}) m/s")
    assert bound["silo_hot_full"].endswith(f"excess 0 (|excess| < {sim.EXCESS_NOISE_MPS:g}) m/s")
    cold_excess = float(bound["silo_cold"].rsplit("excess ", 1)[1].split()[0])
    assert cold_excess == pytest.approx(  # 6 printed digits
        -metrics["runs"]["silo_cold"]["ignition_loss_formula_mps"], rel=1e-5
    )
    table_rows = {
        line.split("|")[1].strip(): [c.strip() for c in line.split("|")[2:-1]]
        for line in summary.split("## Variants")[1].split("## Sensitivity")[0].splitlines()
        if line.startswith("| ")
    }
    assert table_rows["peak track-normal g [g0]"] == ["0"] * 10  # 6e-17 roundoff prints as 0
    assert all(abs(r["peak_track_normal_g"]) < 1e-12 for r in metrics["runs"].values())
    # how each column ignites, and which columns are step-thrust yardsticks
    kind = next(k for k in table_rows if k.startswith("stage-1 startup kind"))
    by_name = dict(zip(metrics["runs"], table_rows[kind], strict=True))
    assert by_name["pad"] == "ramp" and by_name["silo_cold_lag"] == "lag"
    assert by_name["pad_instant"] == "step" and by_name["silo_instant"] == "step"
    t_ign = next(k for k in table_rows if k.startswith("stage-1 ignition, t_ign"))
    assert dict(zip(metrics["runs"], table_rows[t_ign], strict=True))["silo_failed"] == "n/a"
    assert "Note: pad_instant, silo_instant: stage-1 startup kind step" in summary
    assert not any(k.startswith("propellant burned before the free flight") for k in table_rows)
    # the CLAUDE.md-named keys are aliases of the canonical track metrics (same numbers)
    cold_m = metrics["runs"]["silo_cold"]
    for alias, canonical in sim.TRACK_METRIC_ALIASES.items():
        assert cold_m[alias] == cold_m[canonical] != 0.0, alias
    # the CLAUDE.md rule in kg: the yardstick variants beat the README screening at
    # their release speed by exactly the hold-down credit and the altitude term, the
    # cold and hot starts do not (they pay the post-release ignition loss)
    comps = metrics["comparison"]
    equiv, yard = "ideal_screening_payload_equiv_kg", "ideal_screening_payload_at_release_speed_kg"
    for name in ("silo_instant", "pad_instant"):
        assert comps[name][equiv] > comps[name][yard]
        assert f"- {name}: payload equivalent" in checks
        assert "exceeds the README yardstick" in checks
    for name in ("silo_cold", "silo_cold_lag", "silo_hot_full", "silo_sled_22t"):
        assert comps[name][equiv] < comps[name][yard]
        assert f"- {name}: payload equivalent" not in checks
    assert comps["pad_instant"]["ideal_screening_payload_at_release_speed_kg"] == 0.0
    assert comps["silo_cold"]["ideal_screening_payload_at_release_speed_kg"] == pytest.approx(
        comps["silo_instant"]["ideal_screening_payload_at_release_speed_kg"]
    )  # same release speed, same yardstick
    assert comps["silo_failed"]["ideal_screening_payload_equiv_kg"] is None
    # the assisted variants gain their exit speed at release; silo_instant sets the
    # integrated ignition-loss yardstick and a pad does not share its release state
    silo = metrics["comparison"]["silo_cold"]
    assert silo["d_speed_release_mps"] == pytest.approx(
        metrics["runs"]["silo_cold"]["exit_speed_mps"]
    )
    assert silo["ignition_loss_integrated_mps"] == pytest.approx(
        metrics["runs"]["silo_instant"]["stage1_burnout_speed_mps"]
        - metrics["runs"]["silo_cold"]["stage1_burnout_speed_mps"]
    )
    assert (
        silo["ignition_loss_formula_mps"]
        == metrics["runs"]["silo_cold"]["ignition_loss_formula_mps"]
    )
    assert metrics["comparison"]["pad_instant"]["ignition_loss_integrated_mps"] is None
    assert metrics["comparison"]["silo_failed"]["identity_point"] == "end vs stage1_burnout"
    assert "silo_failed" in summary.split("## Variants")[1].split("## Sensitivity")[0]
    assert "| failed ignition: stage |" in summary

    cases = metrics["sensitivity"]
    assert len(cases) == 16  # 2 runs x 4 parameters x (+, -)
    assert {c["of"] for c in cases} == {"silo_cold", "silo_hot_full"}
    assert {c["fraction"] for c in cases} == {0.1, -0.1}
    vehicle_cases = [c for c in cases if c["param"].startswith("vehicle.")]
    assert len(vehicle_cases) == 12 and all(c["baseline_perturbed"] for c in vehicle_cases)
    assist_cases = [c for c in cases if c["param"] == "assist.drive_efficiency"]
    assert len(assist_cases) == 4 and not any(c["baseline_perturbed"] for c in assist_cases)
    for c in assist_cases:
        assert (
            c["stage1_burnout_speed_delta_vs_perturbed_baseline_mps"]
            == c["stage1_burnout_speed_delta_mps"]
        )
    dry = next(c for c in vehicle_cases if "dry_mass" in c["param"] and c["fraction"] > 0)
    assert (
        dry["stage1_burnout_speed_delta_mps"]
        < dry["stage1_burnout_speed_delta_vs_perturbed_baseline_mps"]
    )
    assert all("value_yaml_units" in c and "value" not in c for c in cases)
    # the perturbed value is recorded in SI (tonnes -> kg, a fraction as is) beside the
    # YAML number that reproduces the case
    assert dry["value_si"] == pytest.approx(dry["value_yaml_units"] * 1000.0)  # t -> kg
    assert dry["value_si_unit"] == "kg"
    assert all(
        c["value_si_unit"] == "-" and c["value_si"] == c["value_yaml_units"] for c in assist_cases
    )
    assert {c["value_si_unit"] for c in cases if "isp" in c["param"]} == {"s"}
    sens = summary.split("## Sensitivity")[1].split("## Flags")[0]
    assert sens.count("| C_D | +/-10% |") == 2  # one C_D row per sensitivity run
    assert sens.count(sim.CD_SENSITIVITY_NOTE) >= 2
    assert "(= unchanged)" in sens and "vehicle.stages.stage1.dry_mass_t" in sens
    assert "value (in the parameter's YAML units)" in sens
    assert "| value [SI] (unit in the cell) |" in sens and " kg |" in sens
    assert "ideal-screening payload equiv. of the same-perturbation delta [kg]" in sens
    # the track peak felt g comes with its time and mass, like the flight peak
    silo_m = metrics["runs"]["silo_cold"]
    assert silo_m["felt_g_track_peak_t_s"] <= 0.0 and silo_m["felt_g_track_peak_mass_kg"] > 0.0
    assert silo_m["peak_felt_axial_g_mass_kg"] == pytest.approx(
        silo_m["peak_felt_g_flight_mass_kg"]
    )


def test_full_experiment_plots_for_one_variant(
    repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Plots on for the pad and one silo variant (no sensitivity, to stay fast): the
    pad gets the flight panels, the silo the flight and the track panels, nothing
    else is written under plots/."""
    exp = repo_root / "experiments" / "silo_screening_1d.yaml"
    args = ["run", str(exp), "--results-root", str(tmp_path), "--no-sensitivity"]
    code = main([*args, "--variant", "silo_cold"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "sensitivity:" not in out
    run_dir = _only_run_dir(tmp_path, "silo_screening_1d")
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert sim.SENSITIVITY_SKIPPED in summary
    plots = run_dir / "plots"
    for quantity, _cols, _labels in sim.PLOT_PANELS:
        assert (plots / f"pad_{quantity}.png").is_file(), quantity
        assert (plots / f"silo_cold_{quantity}.png").is_file(), quantity
    for quantity, _cols, _labels in sim.PLOT_TRACK_PANELS:
        assert (plots / f"silo_cold_{quantity}.png").is_file(), quantity
        assert not (plots / f"pad_{quantity}.png").exists(), quantity
    assert len(list(plots.iterdir())) == 2 * len(sim.PLOT_PANELS) + len(sim.PLOT_TRACK_PANELS)


def test_full_sweep_writes_every_point_and_index(
    repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shipped sweeps produce 12 + 9 + 3 index rows with the curated columns."""
    exp = repo_root / "experiments" / "silo_screening_1d.yaml"
    code = main(["sweep", str(exp), "--results-root", str(tmp_path), "--no-plots"])
    out = capsys.readouterr().out
    assert code == 0, out
    run_dir = _only_run_dir(tmp_path, "silo_screening_1d")
    expected = {1: (12, ["assist.net_accel_g", "assist.stroke_m"]), 2: (9, None), 3: (3, None)}
    for k, (n, axes) in expected.items():
        rows = _read_index(run_dir / f"sweep_{k}")
        assert len(rows) == n, k
        assert all(r["status"] == "nominal" for r in rows)
        assert list(rows[0])[-len(sim.SWEEP_INDEX_METRICS) - 1 :] == [
            *sim.SWEEP_INDEX_METRICS,
            "status",
        ]
        if axes is not None:
            assert list(rows[0])[1 : 1 + len(axes)] == axes
        for i, r in enumerate(rows, start=1):
            assert r["run_dir"] == f"sweep_{k}/run_{i:04d}"
            assert (run_dir / r["run_dir"] / "summary.md").is_file()
            assert float(r["stage1_burnout_speed_delta_mps"]) > 0.0
    point = (run_dir / "sweep_3" / "run_0001" / "summary.md").read_text(encoding="utf-8")
    assert sim.SENSITIVITY_SWEEP_POINT in point and "| run_0001 | C_D |" not in point
    assert not (run_dir / "sweep_4").exists()
    top = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "## sweep_3: silo_cold_lag over ignition.stage1.startup.tau_s" in top
