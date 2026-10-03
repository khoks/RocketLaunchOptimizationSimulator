"""The ascent animation (plots.write_ascent_animation, ``launchsim animate``) on a tiny
synthetic planar results directory: a GIF with the expected frames, default and refused
output paths, a vertical_1d run refused, unknown runs named, and the two-speed timeline
monotone over the whole flight, the playback labels, GIF frame timing, event labels
that name their runs and values, and the calibration caveat checked against its
findings note (every record; inside the band said when it is, and the line fits the
frame). Nothing here needs ffmpeg (a stand-in writer tests its failure)."""

from __future__ import annotations

import contextlib
import csv
import json
import math
import subprocess
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from launchsim import plots
from launchsim.cli import main

EXPERIMENT = "synth_2d"
TIMESTAMP = "20260101T000000Z"
T_END_S = 80.0
"""Flight end [s after release] of the synthetic runs: past the timeline knee (30 s)."""
PUSH_S = 2.0
SERIES_COLUMNS = [*plots.ANIMATION_COLUMNS, "stage"]
EVENT_COLUMNS = ["t_s", "event", "phase", "stage", "alt_m", "downrange_m", "speed_rel_mps", "m_kg"]
REPO = Path(__file__).resolve().parents[1]
CALIBRATION_RECORD = REPO / "tests" / "data" / "calibration_record.json"
"""The recorded calibration run (case P*, case vehicle files): tests/test_calibration.py."""
GATE_VEHICLE = "generic_f9_class_2d"
README_VEHICLE = "generic_f9_class_2d_readme_loads"
"""The calibrated vehicles: the gate (mass set C) and the README-loads fork (set A)."""
CALIBRATION_BAND_PCT = 10.0
"""The calibration band [%] (CLAUDE.md, Calibration: within +/-10 %)."""


def _row(t_rel: float, offset: float, assist: bool) -> dict[str, object]:
    """One synthetic time-series row at t_rel [s after release]: a push from -50 m for
    the assist run, a hold on the pad otherwise, then a smooth climb."""
    if t_rel < 0.0:
        phase = "ASSIST" if assist else "HOLD"
        alt = -50.0 * (t_rel / PUSH_S) ** 2 if assist else 0.0
        return {
            "t_s": t_rel + offset,
            "t_rel_release_s": t_rel,
            "phase": phase,
            "stage": "stage1",
            "alt_m": alt,
            "downrange_m": 0.0,
            "speed_rel_mps": 25.0 * (1.0 + t_rel / PUSH_S) if assist else 0.0,
            "felt_axial_g": 3.0 if assist else 1.0,
            "q_pa": math.nan if assist else 0.0,
            "m_kg": 1000.0,
        }
    head = 5.0 if assist else 0.0
    return {
        "t_s": t_rel + offset,
        "t_rel_release_s": t_rel,
        "phase": "GRAVITY_TURN" if t_rel < 40.0 else "LTG_BURN",
        "stage": "stage1" if t_rel < 40.0 else "stage2",
        "alt_m": (head + t_rel) ** 2 * 10.0,
        "downrange_m": t_rel**3,
        "speed_rel_mps": 25.0 * head + 20.0 * t_rel,
        "felt_axial_g": 1.5 + t_rel / 40.0,
        "q_pa": 1000.0 * math.sin(math.pi * t_rel / T_END_S),
        "m_kg": 1000.0 - 10.0 * t_rel,
    }


def _write_run(run_dir: Path, name: str, assist: bool) -> None:
    """<run_dir>/<name>/timeseries.csv and events.csv of one synthetic planar run."""
    offset = PUSH_S if assist else 0.0  # t_s starts at 0 at the push start
    t_start = -PUSH_S
    times = np.arange(t_start, T_END_S + 1e-9, 0.5)
    rows = [_row(float(t), offset, assist) for t in times]
    folder = run_dir / name
    folder.mkdir(parents=True)
    with (folder / "timeseries.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SERIES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    events = [
        ("push_start" if assist else "ignition", t_start),
        ("release", 0.0),
        ("ignition" if assist else "kick_end", 1.0),
        ("staging", 40.0),
        ("fairing", 50.0),
        ("cutoff", T_END_S),
        ("end", T_END_S),
    ]
    with (folder / "events.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        for name_ev, t_rel in events:
            row = _row(t_rel, offset, assist)
            writer.writerow(
                {
                    "t_s": row["t_s"],
                    "event": name_ev,
                    "phase": row["phase"],
                    "stage": row["stage"],
                    "alt_m": row["alt_m"],
                    "downrange_m": row["downrange_m"],
                    "speed_rel_mps": row["speed_rel_mps"],
                    "m_kg": row["m_kg"],
                }
            )


def _make_run_dir(root: Path, model: str | None = "planar_2d", extra_variants: int = 0) -> Path:
    """A synthetic results/<experiment>/<timestamp> directory: the baseline 'pad', the
    variant 'silo' (an assist push) and ``extra_variants`` more pad copies."""
    run_dir = root / "results" / EXPERIMENT / TIMESTAMP
    run_dir.mkdir(parents=True)
    runs = {"pad": {"payload_kg": 1000.0, "status": "inserted"}}
    runs["silo"] = {"payload_kg": 1100.0, "status": "inserted"}
    _write_run(run_dir, "pad", assist=False)
    _write_run(run_dir, "silo", assist=True)
    for k in range(extra_variants):
        name = f"var{k}"
        runs[name] = {"payload_kg": None, "status": "impact"}
        _write_run(run_dir, name, assist=False)
    metrics: dict[str, object] = {
        "experiment": EXPERIMENT,
        "timestamp_utc": TIMESTAMP,
        "git": {"hash": "abc123", "dirty": False},
        "baseline": "pad",
        "runs": runs,
    }
    if model is not None:
        metrics["model"] = model
    (run_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    config = {"experiment": EXPERIMENT, "vehicle": {"name": "toy_2d"}}
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return run_dir


def _listing(folder: Path) -> set[Path]:
    return set(folder.rglob("*"))


def _no_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plots.FFMpegWriter, "isAvailable", classmethod(lambda cls: False))


def test_gif_has_expected_frames_and_leaves_results_alone(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    before = _listing(tmp_path / "results")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    fps, seconds = 4, 2.0
    out = plots.write_ascent_animation(
        run_dir, None, out_dir / "a.gif", fps=fps, seconds=seconds, width=320
    )
    assert out == out_dir / "a.gif"
    assert _listing(tmp_path / "results") == before  # read only
    expected = round(fps * seconds)
    with Image.open(out) as im:
        assert im.size == (320, 180)
        n = im.n_frames
        durations = []
        for k in range(n):
            im.seek(k)
            durations.append(im.info["duration"])
    # Pillow merges identical consecutive frames (the end hold) and sums their durations,
    # so the total duration counts every frame written.
    assert 2 <= n <= expected
    assert sum(durations) == expected * int(1000 / fps)


def test_default_output_is_outside_the_run_dir(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    name = f"{EXPERIMENT}_{TIMESTAMP}_animation"
    elsewhere = tmp_path / "work"
    elsewhere.mkdir()
    assert plots.default_animation_path(run_dir, elsewhere, ffmpeg=True) == (
        elsewhere / f"{name}.mp4"
    )
    assert plots.default_animation_path(run_dir, elsewhere, ffmpeg=False) == (
        elsewhere / f"{name}.gif"
    )
    # From inside the results tree the default moves next to the tree, never into it.
    for cwd in (run_dir, tmp_path / "results"):
        path = plots.default_animation_path(run_dir, cwd, ffmpeg=True)
        assert path == tmp_path / f"{name}.mp4"
        assert not path.resolve().is_relative_to((tmp_path / "results").resolve())


def test_cli_default_output_from_inside_the_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _make_run_dir(tmp_path)
    before = _listing(tmp_path / "results")
    _no_ffmpeg(monkeypatch)
    monkeypatch.chdir(run_dir)
    code = main(["animate", str(run_dir), "--fps", "2", "--seconds", "1", "--width", "320"])
    out = capsys.readouterr().out
    assert code == 0, out
    out.encode("ascii")
    written = tmp_path / f"{EXPERIMENT}_{TIMESTAMP}_animation.gif"
    assert written.is_file()
    assert "animation:" in out
    assert _listing(tmp_path / "results") == before


def test_output_inside_results_or_bad_extension_is_refused(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    with pytest.raises(plots.AnimationError, match="results tree"):
        plots.write_ascent_animation(run_dir, None, run_dir / "a.gif", fps=2, seconds=1, width=320)
    with pytest.raises(plots.AnimationError, match=r"\.mp4 or \.gif"):
        plots.write_ascent_animation(run_dir, None, tmp_path / "a.avi", fps=2, seconds=1, width=320)


def test_mp4_without_ffmpeg_is_a_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _make_run_dir(tmp_path)
    _no_ffmpeg(monkeypatch)
    with pytest.raises(plots.AnimationError, match="ffmpeg"):
        plots.write_ascent_animation(run_dir, None, tmp_path / "a.mp4", fps=2, seconds=1, width=320)


def test_vertical_1d_run_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = _make_run_dir(tmp_path, model=None)  # a vertical_1d metrics.json has no model
    with pytest.raises(plots.AnimationError, match="vertical_1d"):
        plots.write_ascent_animation(run_dir, None, tmp_path / "a.gif", fps=2, seconds=1, width=320)
    code = main(["animate", str(run_dir), "--out", str(tmp_path / "a.gif")])
    out = capsys.readouterr().out
    assert code == 1
    assert "error:" in out and "vertical_1d" in out and "Traceback" not in out
    assert not (tmp_path / "a.gif").exists()


def test_unknown_run_names_are_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = _make_run_dir(tmp_path)
    with pytest.raises(plots.AnimationError, match=r"unknown run\(s\) nope.*available: pad, silo"):
        plots.load_animation_runs(run_dir, ["pad", "nope"])
    code = main(["animate", str(run_dir), "--runs", "nope", "--out", str(tmp_path / "a.gif")])
    out = capsys.readouterr().out
    assert code == 1
    assert "unknown run(s) nope" in out


def test_default_selection_is_baseline_plus_three_variants(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, extra_variants=3)
    default, available = plots.animation_run_names(run_dir)
    assert default == ["pad", "silo", "var0", "var1"]
    assert available == ["pad", "silo", "var0", "var1", "var2"]
    with pytest.raises(plots.AnimationError, match="at most"):
        plots.load_animation_runs(run_dir, available)


def test_runs_are_read_on_the_time_after_release(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    runs, _ = plots.load_animation_runs(run_dir, ["pad", "silo"])
    pad, silo = runs
    assert pad.baseline and not silo.baseline
    assert silo.t_s[0] == pytest.approx(-PUSH_S)
    labels = {ev.label: ev.t_s for ev in silo.events}
    assert labels["push start"] == pytest.approx(-PUSH_S)  # t_s 0 shifted by the push
    assert labels["release"] == pytest.approx(0.0)
    assert labels["cutoff"] == pytest.approx(T_END_S)
    assert "end" not in labels
    assert silo.payload_kg == pytest.approx(1100.0)
    lines = plots.animation_caveats(runs, "toy_2d")
    assert len(lines) == 3
    caveats = " ".join(lines)
    assert "no calibration record" in caveats and "3.0 g push load" in caveats
    assert "+14.3% high" in " ".join(plots.animation_caveats(runs, "generic_f9_class_2d"))


def test_calibration_record_matches_its_findings_note() -> None:
    """The footnote's calibration numbers are the ones the findings note reports, so a
    re-run calibration that updates the note but not CALIBRATION_RECORDS fails here.
    Every record is checked the same way (SP1 step 8a added the README-loads fork): its
    vehicle is a case of the recorded calibration run (tests/data/calibration_record.json,
    the case whose vehicle file carries that name), its P* is that case's recorded P* to
    0.1 kg, and the note's results row of the case prints P* to 0.1 kg, the gap
    100 (P*/reference - 1) % to two decimals and inside or outside the +/-10 % band; the
    note quotes the reference. The gate's one-paragraph result is checked as before."""
    calibration = json.loads(CALIBRATION_RECORD.read_text(encoding="utf-8"))
    case_of = {
        yaml.safe_load((REPO / path).read_text(encoding="utf-8"))["name"]: case
        for case, path in calibration["vehicles"].items()
    }
    assert set(plots.CALIBRATION_RECORDS) == {GATE_VEHICLE, README_VEHICLE}
    for vehicle, (model_kg, reference_kg, note) in plots.CALIBRATION_RECORDS.items():
        text = (REPO / f"{note}.md").read_text(encoding="utf-8")
        gap = 100.0 * (model_kg / reference_kg - 1.0)
        case = case_of[vehicle]
        assert round(calibration["payload_kg"][case], 1) == model_kg, vehicle
        band = "inside" if abs(gap) <= CALIBRATION_BAND_PCT else "outside"
        assert f"| `{case}` | {model_kg:,.1f} | {gap:+.2f}% | {band}" in text, vehicle
        assert f"against {reference_kg:,.0f} kg" in text, vehicle
    model_kg, reference_kg, note = plots.CALIBRATION_RECORDS[GATE_VEHICLE]
    text = (REPO / f"{note}.md").read_text(encoding="utf-8")
    gap = 100.0 * (model_kg / reference_kg - 1.0)
    assert f"P* = {model_kg:,.1f} kg" in text
    assert f"{gap:+.2f}% against {reference_kg:,.0f} kg" in text


def test_calibration_footnote_says_inside_the_band_when_it_is() -> None:
    """The footnote's calibration sentence: the gate vehicle (+14.3 % high, outside the
    band) keeps its sentence word for word; the README-loads fork, 100 (24,700/22,800 - 1)
    = +8.3 % high, says it lies inside the +/-10 % band and is not called the gate
    vehicle; a vehicle without a record says so. Rendered at the frame geometry, every
    record's footnote line ends left of the frame's right edge."""
    assert plots.calibration_caveat(GATE_VEHICLE) == (
        "Gate vehicle calibrates +14.3% high on payload (docs/findings/CAL-f9-leo-2d)."
    )
    gap = 100.0 * (24700.0 / 22800.0 - 1.0)
    readme = plots.calibration_caveat(README_VEHICLE)
    assert f"{gap:+.1f}% high" in readme and "+8.3% high" in readme
    assert "inside the +/-10% band" in readme and "Gate vehicle" not in readme
    assert "band" not in plots.calibration_caveat(GATE_VEHICLE)
    assert plots.calibration_caveat("toy_2d") == "Vehicle toy_2d: no calibration record on file."
    size_in, dpi, (width_px, _height_px) = plots.frame_geometry(1280)
    fig = Figure(figsize=size_in, dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    for vehicle in plots.CALIBRATION_RECORDS:
        line = plots.animation_caveats([], vehicle)[-1]
        artist = fig.text(plots.ANIMATION_GRID["left"], 0.0, line, fontsize=plots.FONT_FOOTNOTE_PT)
        canvas.draw()
        right_px = artist.get_window_extent(renderer=canvas.get_renderer()).x1
        assert right_px < width_px * plots.ANIMATION_GRID["right"], vehicle


def test_calibration_band_includes_both_edges() -> None:
    """A record exactly on an edge of the +/-10 % band, P* = 22,800 +/- 0.1 x 22,800 =
    25,080 and 20,520 kg, reads inside, though P*/reference - 1 rounds to just above
    0.1 at the upper edge; 0.1 kg beyond either edge reads outside. The footnote
    follows the helper."""
    reference_kg = 22800.0
    band_kg = 0.1 * reference_kg
    upper_kg, lower_kg = reference_kg + band_kg, reference_kg - band_kg
    assert (upper_kg, lower_kg) == (25080.0, 20520.0)
    assert abs(upper_kg / reference_kg - 1.0) > 0.1  # the rounding the helper absorbs
    for model_kg in (upper_kg, lower_kg):
        assert plots.inside_calibration_band(plots.calibration_gap(model_kg, reference_kg))
    for model_kg in (upper_kg + 0.1, lower_kg - 0.1):
        assert not plots.inside_calibration_band(plots.calibration_gap(model_kg, reference_kg))
    edge = {"edge_2d": (upper_kg, reference_kg, "docs/findings/CAL-f9-leo-2d")}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(plots, "CALIBRATION_RECORDS", edge)
        assert plots.calibration_caveat("edge_2d") == (
            "This vehicle calibrates +10.0% high on payload, inside the +/-10% band "
            "(docs/findings/CAL-f9-leo-2d)."
        )


def test_timeline_is_monotone_covers_the_flight_and_plays_launch_near_real_time() -> None:
    t0, t1, n, fps = -2.607, 538.8, 600, 30
    times = plots.ascent_time_map(t0, t1, n)
    assert len(times) == n
    assert times[0] == t0 and times[-1] == t1
    assert np.all(np.diff(times) >= 0.0)
    speeds = plots.playback_speeds(t0, t1, n, fps)
    launch_end, knee = plots.TIMELINE_LAUNCH_END_S, plots.TIMELINE_KNEE_S
    launch = speeds[times < launch_end - 0.1]
    close = speeds[(times > launch_end + 0.1) & (times < knee - 0.1)]
    fast = speeds[(times > knee + 0.1) & (times < t1)]
    assert launch == pytest.approx(1.0, abs=0.05)  # the 2.6 s push plays at about real time
    assert launch.max() < close.min() <= close.max() < fast.min()
    for part in (launch, close, fast):  # nominal speeds: one value per segment
        assert np.isclose(part, part[0]).all()
    # The speeds are the slopes of the time map: they integrate back to the flight.
    assert np.sum(speeds[:-1] / fps) == pytest.approx(t1 - t0, rel=0.02)
    held = times == t1
    assert held.sum() >= int(plots.TIMELINE_HOLD_FRACTION * n)  # the end hold
    assert np.all(speeds[held] == 0.0)
    # A flight that ends before the knee runs at one speed.
    short = plots.ascent_time_map(0.0, 10.0, 50)
    assert np.all(np.diff(short) >= 0.0) and short[-1] == 10.0
    short_speeds = plots.playback_speeds(0.0, 10.0, 50, 10)
    assert np.isclose(short_speeds[short < 10.0], short_speeds[0]).all()
    with pytest.raises(plots.AnimationError):
        plots.ascent_time_map(0.0, 10.0, 1)


def test_playback_label_names_speed_and_segment() -> None:
    assert plots.playback_label(1.0, -1.0) == "playback 1.0x real time (launch)"
    assert "slow motion" in plots.playback_label(0.5, -1.0)
    assert "slow motion" not in plots.playback_label(4.1, 10.0)
    assert plots.playback_label(6.8, 10.0) == "playback 6.8x real time (close-up to T+30 s)"
    assert plots.playback_label(55.2, 100.0) == "playback 55x real time (fast forward)"
    assert plots.playback_label(0.0, 538.8).startswith("end of flight")
    assert plots.signed(-0.022) == "+0.0" and plots.signed(-0.06) == "-0.1"


def test_gif_playback_fps_follows_its_10_ms_delays() -> None:
    assert plots.animation_playback_fps(30, ".mp4") == 30.0
    assert plots.animation_playback_fps(12, ".gif") == pytest.approx(12.5)  # 83 ms -> 80 ms
    assert plots.animation_playback_fps(10, ".gif") == pytest.approx(10.0)
    assert plots.animation_playback_fps(30, ".GIF") == pytest.approx(1000.0 / 30.0)
    with pytest.raises(plots.AnimationError, match="at most 50 fps"):
        plots.animation_playback_fps(60, ".gif")
    with pytest.raises(plots.AnimationError, match="fps"):
        plots.animation_playback_fps(0, ".mp4")


def test_readout_names_stay_unique_after_the_cut() -> None:
    names = ["silo_hot_full", "silo_hot_full_impinged", "pad", "silo_hot_ramp_on_track"]
    short = plots.readout_names(names)
    assert short[2] == "pad"
    assert all(len(n) <= plots.READOUT_NAME_CHARS for n in short)
    assert len(set(short)) == len(short)
    assert plots.readout_names(["silo_cold"]) == ["silo_cold"]
    assert plots.readout_names(["silo_cold_lag"]) == ["silo_col~"]


def _figure(run_dir: Path) -> plots._AscentFigure:
    runs, metrics = plots.load_animation_runs(run_dir, ["pad", "silo"])
    size, dpi, _ = plots.frame_geometry(640)
    return plots._AscentFigure(runs, metrics, "toy_2d", size, dpi)


def test_event_labels_name_their_runs_and_values(tmp_path: Path) -> None:
    fig = _figure(_make_run_dir(tmp_path))
    pad_glyph, silo_glyph = plots.MARKER_GLYPHS["o"], plots.MARKER_GLYPHS["s"]
    fig.draw_frame(-1.0, 1.0)
    shown = {g.label: g.artist.get_text() for g in fig.label_groups if g.artist.get_visible()}
    assert shown["push start"] == f"{silo_glyph} push start (3.0 g)"
    assert "release" not in shown  # not yet
    fig.draw_frame(T_END_S, 0.0)
    texts = {g.label: g.artist.get_text() for g in fig.label_groups if g.label != "release"}
    # The synthetic releases are 250 m apart (the silo run is released above ground), so
    # each run gets its own label, named by its marker glyph, with its release speed.
    releases = sorted(g.artist.get_text() for g in fig.label_groups if g.label == "release")
    assert releases == sorted(
        [f"{pad_glyph} release (0.0 m/s)", f"{silo_glyph} release (125.0 m/s)"]
    )
    # Copies of an event on the trajectory panel list each run's altitude [km].
    assert texts["MECO/staging"] == f"MECO/staging ({pad_glyph} 16.0  {silo_glyph} 20.2 km)"
    assert fig.speed.get_text() == "end of flight: holding the last state"
    assert all(mark.get_visible() for _, mark in fig.event_marks)


def test_markers_are_hidden_before_a_run_starts(tmp_path: Path) -> None:
    fig = _figure(_make_run_dir(tmp_path))
    pad = fig.runs[0]
    early = pad.t_start_s - 0.5
    fig.draw_frame(early, 1.0)
    assert not fig.main_heads[0].get_visible() and not fig.close_heads[0].get_visible()
    assert "on pad" in fig.readouts[0].get_text()  # the pad run starts with its hold-down
    assert "not started" in fig.readouts[1].get_text()
    assert fig.clock.get_text() == f"T {plots.signed(early)} s"
    fig.draw_frame(pad.t_start_s, 1.0)
    assert fig.main_heads[0].get_visible() and fig.close_heads[0].get_visible()


def test_custom_results_root_is_protected(tmp_path: Path) -> None:
    run_dir = tmp_path / "out" / EXPERIMENT / TIMESTAMP  # written with --results-root out
    run_dir.mkdir(parents=True)
    other_run = tmp_path / "out" / "other" / TIMESTAMP
    other_run.mkdir(parents=True)
    with pytest.raises(plots.AnimationError, match="results tree"):
        plots.check_animation_out(other_run / "a.gif", run_dir)
    path = plots.default_animation_path(run_dir, tmp_path / "out", ffmpeg=False)
    assert path.parent == tmp_path


class _BrokenFFMpeg:
    """Stands in for FFMpegWriter: ffmpeg exits non-zero when the file is closed."""

    def __init__(self, **_: object) -> None:
        pass

    @classmethod
    def isAvailable(cls) -> bool:
        return True

    def saving(self, *_: object) -> contextlib.AbstractContextManager[None]:
        @contextlib.contextmanager
        def failing() -> Iterator[None]:
            yield
            raise subprocess.CalledProcessError(1, ["ffmpeg"])

        return failing()

    def grab_frame(self, **_: object) -> None:
        pass


def test_ffmpeg_failure_is_one_error_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _make_run_dir(tmp_path)
    monkeypatch.setattr(plots, "FFMpegWriter", _BrokenFFMpeg)
    out = tmp_path / "a.mp4"
    args = ["animate", str(run_dir), "--out", str(out), "--fps", "2", "--seconds", "1"]
    code = main([*args, "--width", "320"])
    printed = capsys.readouterr().out
    assert code == 1
    assert "error: ffmpeg failed" in printed and "Traceback" not in printed


def test_help_names_the_specified_metavars_and_defaults(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["animate", "--help"])
    text = " ".join(capsys.readouterr().out.split())
    for flag in ("--runs NAME [NAME ...]", "--out PATH", "--fps N", "--seconds S", "--width PX"):
        assert flag in text
    for default in ("(default: 30;", "(default: 20.0)", "(default: 1280)"):
        assert default in text


def test_frame_geometry_is_16_by_9_and_even() -> None:
    for width, height in ((1280, 720), (640, 360), (1000, 562)):
        size, dpi, frame = plots.frame_geometry(width)
        assert frame == (width, height)
        assert int(size[0] * dpi) == width and int(size[1] * dpi) == height
    with pytest.raises(plots.AnimationError, match="even"):
        plots.frame_geometry(641)
    with pytest.raises(plots.AnimationError):
        plots.frame_geometry(100)
