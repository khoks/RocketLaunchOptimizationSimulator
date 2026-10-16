"""The ascent animation (plots.write_ascent_animation, ``launchsim animate``) on a tiny
synthetic planar results directory: a GIF with the expected frames, default and refused
output paths, a vertical_1d run refused, unknown runs named, and the two-speed timeline
monotone over the whole flight, the playback labels, GIF frame timing, event labels
that name their runs and values, and the calibration caveat checked against its
findings note (every record; inside the band said when it is, and the line fits the
frame), and runs of the offload block labelled from its record (cases, paired pads, pad
controls, a case without an offload) with their two-line legend clear of the path and of
the event labels. Nothing here needs ffmpeg (a stand-in writer tests its failure)."""

from __future__ import annotations

import contextlib
import csv
import dataclasses
import itertools
import json
import math
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

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
ORBIT_ALT_M = 200_000.0
ORBIT_RANGE_M = 1_600_000.0
ASSIST_RANGE_FACTOR = 1.03
"""The orbit-shaped synthetic ascent (``_row(..., orbit=True)``): it levels off at
ORBIT_ALT_M with zero climb rate at T_END_S, ORBIT_RANGE_M downrange (an assisted run
ASSIST_RANGE_FACTOR times further), so the path under the legend runs near its top and
the 'cutoff' label sits at the top right, as on a real 200 km insertion."""


def _row(t_rel: float, offset: float, assist: bool, orbit: bool = False) -> dict[str, object]:
    """One synthetic time-series row at t_rel [s after release]: a push from -50 m for
    the assist run, a hold on the pad otherwise, then a smooth climb (``orbit``: one that
    levels off at ORBIT_ALT_M, alt = ORBIT_ALT_M (1 - (1 - t/T_END_S)^3), downrange =
    ORBIT_RANGE_M (t/T_END_S)^2, times ASSIST_RANGE_FACTOR for the assist run)."""
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
    frac = t_rel / T_END_S
    alt = ORBIT_ALT_M * (1.0 - (1.0 - frac) ** 3) if orbit else (head + t_rel) ** 2 * 10.0
    reach = ORBIT_RANGE_M * (ASSIST_RANGE_FACTOR if assist else 1.0)
    return {
        "t_s": t_rel + offset,
        "t_rel_release_s": t_rel,
        "phase": "GRAVITY_TURN" if t_rel < 40.0 else "LTG_BURN",
        "stage": "stage1" if t_rel < 40.0 else "stage2",
        "alt_m": alt,
        "downrange_m": reach * frac**2 if orbit else t_rel**3,
        "speed_rel_mps": 25.0 * head + 20.0 * t_rel,
        "felt_axial_g": 1.5 + t_rel / 40.0,
        "q_pa": 1000.0 * math.sin(math.pi * t_rel / T_END_S),
        "m_kg": 1000.0 - 10.0 * t_rel,
    }


def _write_run(run_dir: Path, name: str, assist: bool, orbit: bool = False) -> None:
    """<run_dir>/<name>/timeseries.csv and events.csv of one synthetic planar run
    (``orbit``: the orbit-shaped ascent of ``_row``)."""
    offset = PUSH_S if assist else 0.0  # t_s starts at 0 at the push start
    t_start = -PUSH_S
    times = np.arange(t_start, T_END_S + 1e-9, 0.5)
    rows = [_row(float(t), offset, assist, orbit) for t in times]
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
            row = _row(t_rel, offset, assist, orbit)
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


def _make_run_dir(
    root: Path, model: str | None = "planar_2d", extra_variants: int = 0, orbit: bool = False
) -> Path:
    """A synthetic results/<experiment>/<timestamp> directory: the baseline 'pad', the
    variant 'silo' (an assist push) and ``extra_variants`` more pad copies (``orbit``:
    every run flies the orbit-shaped ascent of ``_row``)."""
    run_dir = root / "results" / EXPERIMENT / TIMESTAMP
    run_dir.mkdir(parents=True)
    runs = {"pad": {"payload_kg": 1000.0, "status": "inserted"}}
    runs["silo"] = {"payload_kg": 1100.0, "status": "inserted"}
    _write_run(run_dir, "pad", assist=False, orbit=orbit)
    _write_run(run_dir, "silo", assist=True, orbit=orbit)
    for k in range(extra_variants):
        name = f"var{k}"
        runs[name] = {"payload_kg": None, "status": "impact"}
        _write_run(run_dir, name, assist=False, orbit=orbit)
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
    assert "no calibration record" in caveats
    assert "no sized structural mass for the 3.0 g push load." in caveats  # A6v fix round 2
    assert "penalty row" not in caveats  # neither run is one
    assert (pad.penalty_added_kg, silo.penalty_added_kg) == (None, None)
    assert "+14.3% high" in " ".join(plots.animation_caveats(runs, "generic_f9_class_2d"))


def test_footnote_names_what_a_penalty_row_charges(tmp_path: Path) -> None:
    """A6v fix round 2 (honesty review pass 2): the footnote's structural line says 'no
    sized structural mass' for the push load and, when a shown run is a penalty row (an
    offload case whose record charges an assumed stage-1 dry mass: AnimationRun's
    penalty_added_kg from replay.penalty_added_kg), that the penalty row charges an assumed
    stage-1 dry mass, so the fixed line and the run's own structure line on a frame no longer
    read against each other; a selection without a penalty row gets no such clause. The
    longest such line (the penalty clause) still ends left of the 1280 px frame's right edge
    in the animation's footnote."""
    run_dir = _make_offload_run_dir(tmp_path)
    runs, _ = plots.load_animation_runs(run_dir, ["pad", "silo_fix5"])
    pad, penalty = runs
    assert pad.penalty_added_kg is None and penalty.penalty_added_kg == PENALTY_ADDED_KG
    second = plots.animation_caveats(runs, "toy_2d")[1]
    assert second == (
        "Unthrottled (no max-Q or g limit); no sized structural mass for the 3.0 g push load; "
        "the penalty row charges an assumed stage-1 dry mass."
    )
    # two penalty rows shown: the plural (the fixed case beside itself, for the wording only)
    assert plots.animation_caveats([pad, penalty, penalty], "toy_2d")[1].endswith(
        "; the penalty rows charge an assumed stage-1 dry mass."
    )
    plain, _ = plots.load_animation_runs(run_dir, ["pad", "silo_s1"])
    assert plain[1].penalty_added_kg is None
    assert plots.animation_caveats(plain, "toy_2d")[1] == (
        "Unthrottled (no max-Q or g limit); no sized structural mass for the 3.0 g push load."
    )
    assert plots.animation_caveats([pad], "toy_2d")[1] == "Unthrottled (no max-Q or g limit)."
    size_in, dpi, (width_px, _height_px) = plots.frame_geometry(1280)
    fig = Figure(figsize=size_in, dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    artist = fig.text(plots.ANIMATION_GRID["left"], 0.0, second, fontsize=plots.FONT_FOOTNOTE_PT)
    canvas.draw()
    right_px = artist.get_window_extent(renderer=canvas.get_renderer()).x1
    assert right_px < width_px * plots.ANIMATION_GRID["right"], second


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


P_REF_KG = 1000.0
"""The synthetic offload block's reference payload: the baseline pad's P*."""
STRUCTURE_KEYS: dict[str, Any] = {
    "structure_charged": True,
    "structure_dm_kg": 9100.3,
    "structure_dm_stage2_kg": 200.2,
    "structure_dm_x0_kg": 9000.0,
    "structure_set": "central",
    "structure_sizing": "flown",
    "structure_dynamic": "rise_time",
    "structure_entry": "aft_ring",
    "structure_margin": 0.0,
    "structure_envelope_cap_g": None,
    "structure_overrides": {},
    "structure_plausibility_ratio": 1.05,
    "structure_plausibility_factor": 1.0,
    "structure_plausibility_scaled": False,
    "structure_flags": [{"name": "release_unload", "fired": False, "values": {}}],
    "structure_file": "configs/structures/toy.yaml",
}
"""The run-level structure keys of D-SP7-22 a structural run's metrics record carries (a
central case at the headline settings: dm1 + dm2 = 9,100.3 kg, dm2 = 200.2 kg, no fired
flag, not plausibility-scaled); synthetic, never read from results/."""
SETS_METHOD = (
    "Design 4.2.6, sizing only, at the headline push of toy_offload's silo_cold (the analytic "
    "constant_accel case at a stage-1 offload of 36006.44430169878 kg and P_ref "
    "24700.013061881455 kg) on the envelope of its pad baseline as flown."
)
"""A frozen sets' ``method`` in sim.structure_search_method's form, naming the push the
sets were searched at (synthetic: toy_offload's silo_cold at 36,006 kg, not SP1's
headline; final clean-up, N3a-02)."""
STRUCTURE_INPUTS: dict[str, Any] = {
    "file": "configs/structures/toy.yaml",
    "sets": {
        "method": SETS_METHOD,
        "physics_low_mass": {
            "polish": [
                {"search": "A", "dm_after_kg": 3677.06},
                {"search": "B", "dm_after_kg": 8492.47},
            ]
        },
        "physics_high_mass": {"polish": [{"search": "A", "dm_after_kg": 18603.8}]},
    },
}
"""A block's ``structure_inputs`` record as far as the readers go: the frozen sets'
method (SETS_METHOD, the push they were searched at) and the physics sets' polish of the
headline search A (the band's ends, dm 3,677 and 18,604 kg)."""
MODELLED_CORE = (
    "9,100.3 kg (stage 1 8,900.1 kg, stage 2 200.2 kg): a first-order station sizing of the "
    "push load (layer and set central (every coefficient at its central value): central; "
    "configs/structures/toy.yaml); the physics band's ends at the structure file's headline "
    "push (toy_offload's silo_cold at a stage-1 offload of 36,006 kg, per its sets.method) "
    "are dm 3,677 kg and 18,604 kg; both ends are sizing-only numbers from the frozen sets, "
    "not this run's band: the run is sized at its own push and offload; no structure flag "
    "fired; a first-order estimate with its stated ranges, not a detailed structural design"
)
"""summary.modelled_structure_text of STRUCTURE_KEYS with STRUCTURE_INPUTS, as every reader
quotes it (the replay and scene caveats, the scene frame's footer)."""
PENALTY_ADDED_KG = 2000.0
"""The assumed stage-1 dry mass the fixed case silo_fix5 charges (a penalty row)."""
PSTAR_DELTA_KG = 10.0
"""P_2* - P_ref of the structure payload case silo_pstar_st."""
CASE_OFFLOAD_KG = 41262.9
FIXED_OFFLOAD_KG = 20000.0
FIXED_PAYLOAD_KG = 1030.0
PAIRED_PAD_KG = 958.6
CONTROL_OFFLOAD_KG = 513.6
CONTROL_M_RES_KG = -0.0016
"""m_res(0) [kg] of the stage-1 pad control: grams below zero (a resolution effect)."""
MISSED_M_RES_KG = -3.0
"""m_res(0) [kg] of the 'both' pad control: a real miss, beyond the search resolution."""


def _make_offload_run_dir(root: Path, orbit: bool = False) -> Path:
    """The synthetic directory of ``_make_run_dir`` plus an offload block, written as
    results_io writes one: metrics.json ``offload`` (reference, P_ref, a solved case
    silo_s1 with its paired pad silo_s1__pad, a fixed case silo_fix5, a solved case
    silo_none whose solve found no offload (its recorded run is the full-load run),
    pad controls in three modes, each run's record in ``offload.runs``, none of them in
    ``runs``) and a timeseries.csv and events.csv per offload run (``orbit``: every run
    flies the orbit-shaped ascent of ``_row``)."""
    run_dir = _make_run_dir(root, orbit=orbit)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    inserted, short = "inserted", "short_of_orbit"
    metrics["offload"] = {
        "reference": "pad",
        "reference_payload_kg": P_REF_KG,
        "cases": [
            {
                "name": "silo_s1",
                "of": "silo",
                "kind": "solve",
                "mode": "stage1",
                "run": "silo_s1",
                "total_offload_kg": CASE_OFFLOAD_KG,
                "payload_kg": P_REF_KG,
                "paired_pad": {"run": "silo_s1__pad", "payload_kg": PAIRED_PAD_KG},
            },
            {
                "name": "silo_fix5",
                "of": "silo",
                "kind": "fixed",
                "mode": "stage1",
                "run": "silo_fix5",
                "total_offload_kg": FIXED_OFFLOAD_KG,
                "payload_kg": FIXED_PAYLOAD_KG,
                "paired_pad": None,
                # a penalty row: an assumed stage-1 dry mass charged on the run (A6v fix round 2)
                "stage1_dry_mass_added_kg": PENALTY_ADDED_KG,
                "assumed_penalty": True,
            },
            {
                "name": "silo_none",
                "of": "silo",
                "kind": "solve",
                "mode": "stage1",
                "run": "silo_none",
                "status": "no_offload",
                "total_offload_kg": 0.0,
                "payload_kg": P_REF_KG,
                "paired_pad": None,
            },
            {
                # a structural case (SP7 step S3a): its record and its run's carry the
                # run-level structure keys of D-SP7-22
                "name": "silo_s1_st",
                "of": "silo",
                "kind": "solve",
                "mode": "stage1",
                "run": "silo_s1_st",
                "total_offload_kg": CASE_OFFLOAD_KG,
                "payload_kg": P_REF_KG,
                "paired_pad": None,
                **STRUCTURE_KEYS,
            },
        ],
        # a structure payload case (fix round 1, H-S3a-01 and S3A-R1-06): its run flies
        # its own P_2* on the full load; recorded here and in ``runs``, never in ``cases``
        "structure_payload_cases": [
            {
                "name": "silo_pstar_st",
                "kind": "structure payload case",
                "of": "silo",
                "run": "silo_pstar_st",
                "status": "ok",
                "payload_kg": P_REF_KG + PSTAR_DELTA_KG,
                "payload_delta_kg": PSTAR_DELTA_KG,
                "flags": [],
                **STRUCTURE_KEYS,
            }
        ],
        "pad_controls": [
            {
                "mode": "stage1",
                "run": "pad__offload_stage1",
                "status": "no_offload",
                "offload_kg": 0.0,
                "m_res_kg": CONTROL_M_RES_KG,
                "resolution_effect": True,
            },
            {
                "mode": "stage2",
                "run": "pad__offload_stage2",
                "status": "ok",
                "offload_kg": CONTROL_OFFLOAD_KG,
                "m_res_kg": 1e-6,
                "resolution_effect": False,
            },
            {
                "mode": "both",
                "run": "pad__offload_both",
                "status": "no_offload",
                "offload_kg": 0.0,
                "m_res_kg": MISSED_M_RES_KG,
                "resolution_effect": False,
            },
        ],
        "runs": {
            "silo_s1": {"payload_kg": P_REF_KG, "status": inserted},
            "silo_s1__pad": {"payload_kg": PAIRED_PAD_KG, "status": inserted},
            "silo_fix5": {"payload_kg": FIXED_PAYLOAD_KG, "status": inserted},
            "silo_none": {"payload_kg": P_REF_KG, "status": short},
            "silo_s1_st": {"payload_kg": P_REF_KG, "status": inserted, **STRUCTURE_KEYS},
            "silo_pstar_st": {
                "payload_kg": P_REF_KG + PSTAR_DELTA_KG,
                "status": inserted,
                **STRUCTURE_KEYS,
            },
            "pad__offload_stage1": {"payload_kg": P_REF_KG, "status": short},
            "pad__offload_stage2": {"payload_kg": P_REF_KG, "status": inserted},
            "pad__offload_both": {"payload_kg": P_REF_KG, "status": short},
        },
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    for name in metrics["offload"]["runs"]:
        assist = name in ("silo_s1", "silo_fix5", "silo_none", "silo_s1_st", "silo_pstar_st")
        _write_run(run_dir, name, assist=assist, orbit=orbit)
    return run_dir


def metrics_of(run_dir: Path) -> dict[str, Any]:
    """The directory's metrics.json."""
    return json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))


def _footnote_right_px(line: str) -> tuple[float, float]:
    """(the right edge of ``line`` drawn as the animation's footnote at 1280 px, the
    footnote's right limit) [px]."""
    size_in, dpi, (width_px, _height_px) = plots.frame_geometry(1280)
    fig = Figure(figsize=size_in, dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    artist = fig.text(plots.ANIMATION_GRID["left"], 0.0, line, fontsize=plots.FONT_FOOTNOTE_PT)
    canvas.draw()
    return artist.get_window_extent(renderer=canvas.get_renderer()).x1, (
        width_px * plots.ANIMATION_GRID["right"]
    )


def _assert_footnote_fits(lines: list[str]) -> None:
    """Every line ends left of the footnote's right limit at 1280 px, measured here
    (``_footnote_right_px``) and by plots.footnote_right_px alike."""
    rights, limit = plots.footnote_right_px(lines)
    for line, right in zip(lines, rights, strict=True):
        right_px, limit_px = _footnote_right_px(line)
        assert right_px < limit_px, line
        assert right == pytest.approx(right_px) and limit == pytest.approx(limit_px)


FOOTNOTE_TEST_WIDTHS_PX = (320, 480, 640, 960, 1280, 1920)
"""Frame widths the footnote's wrapped lines are checked at (fix round 2, N2-03: the
smallest width ``animate --width`` accepts, the gallery GIFs' 640, the app's three video
widths and two between)."""
FOOTNOTE_POINTER = (
    "modelled mass by stage: the caveats of summary.md's offload section; structure file "
    "and x* at the physics band's ends: its Structure subsection"
)
"""The clause the footnote's structural line ends with, once per line, word for word (S3a
gate fix and its review, R-G1-02 and R-G1-03: plots.STRUCTURE_FOOTNOTE_POINTER)."""
SPLIT_9100 = "8,900.1 kg (stage 1) and 200.2 kg (stage 2)"
"""STRUCTURE_KEYS' mass by stage as the footnote prints it, to 0.1 kg as the replay caveat
does (S3a gate review, R-G1-05): dm1 = 9,100.3 - 200.2 kg."""


def test_footnote_words_a_modelled_structure_from_the_runs_record(tmp_path: Path) -> None:
    """SP7 step S3a (D-SP7-22): the footnote's structural clause is worded from each
    run's own record. A shown run whose metrics record charges a modelled structural mass
    (``AnimationRun.modelled``, its ``structure_dm_kg``) is said to carry that many kg of
    modelled structural mass (fix round 1, H-S3a-06: the dm is the modelled increment,
    never "a structure" of that mass), "first-order sizing, not an assumed penalty" (fix
    round 3, H-S3a-P3-01: never "not assumed" of a model output on assumed coefficients);
    beside it a penalty row is named on the structural line with its assumed stage-1 dry
    mass, which then leaves the limits line, and the "no sized structural mass" clause
    names only the uncharged pushed runs, never a penalty row (fix round 3, H-S3a-P3-02);
    word for word as before when no modelled run is shown; a design-axis row on the
    central set gets its own clause, 'set central at margin 0.05' (fix round 3,
    H-S3a-P3-04, ``structure_departures`` read from the record); two modelled runs take
    the plural; an unrecorded dm reads "of unrecorded size"; ``width_px`` None hands the
    structural line over unwrapped, one line (fix round 3, S3A-NUM-01: the app's video
    footer, which the scene canvas wraps itself); a structure payload case's run
    (S3A-R1-06: in ``offload.runs`` and
    ``structure_payload_cases``, not in ``cases``) is modelled from its own record and
    its legend names its kind and P_2*. Every line of every selection, wide-glyph and
    digit-heavy names included, ends left of the 1280 px frame's right edge: the line
    is wrapped by measured width (N-S3a-R1-01, plots.footnote_wrap) and never splits a
    number from its unit ('3.0 g'). The full sentence (stages, layer, set, file, band,
    flags) is the scene frame's per-run structure note and the replay caveat, not this
    footnote. S3a gate fix: the record's stage-2 share is above zero here, so the mass
    is given by stage ('8,900.1 kg (stage 1) and 200.2 kg (stage 2)'), each such run in a
    clause of its own; a run whose stage-2 share is unrecorded keeps the total and the
    plural; the line ends with FOOTNOTE_POINTER once."""
    run_dir = _make_offload_run_dir(tmp_path)
    runs, _ = plots.load_animation_runs(run_dir, ["pad", "silo", "silo_s1_st", "silo_fix5"])
    pad, silo, modelled, penalty = runs
    assert (pad.modelled, silo.modelled, modelled.modelled, penalty.modelled) == (
        False,
        False,
        True,
        False,
    )
    assert modelled.structure_dm_kg == pytest.approx(9100.3)
    assert modelled.structure_dm_stage2_kg == pytest.approx(200.2)
    assert (pad.structure_dm_kg, silo.structure_dm_kg, penalty.structure_dm_kg) == (None,) * 3
    assert modelled.penalty_added_kg is None
    mixed = plots.animation_caveats(runs, "toy_2d")
    assert len(mixed) >= 4  # the structural line(s) of its own, wrapped
    assert mixed[1] == "Unthrottled (no max-Q or g limit)."
    assert " ".join(mixed[2:-1]) == (
        f"Structure, per run: silo_s1_st carries {SPLIT_9100} of modelled structural mass "
        "(set central; first-order sizing, not an assumed penalty); silo_fix5 charges an "
        "assumed stage-1 dry mass; no sized structural mass for the 3.0 g push load of silo; "
        f"{FOOTNOTE_POINTER}."
    )
    two_penalties = dataclasses.replace(penalty, name="silo_fix7")
    assert " ".join(
        plots.animation_caveats([modelled, penalty, two_penalties], "toy_2d")[2:-1]
    ) == (
        f"Structure, per run: silo_s1_st carries {SPLIT_9100} of modelled structural mass "
        "(set central; first-order sizing, not an assumed penalty); silo_fix5 and silo_fix7 "
        f"charge an assumed stage-1 dry mass; {FOOTNOTE_POINTER}."
    )
    # the uncharged selection with the penalty row keeps its limits line word for word
    assert plots.animation_caveats([pad, silo, penalty], "toy_2d")[1] == (
        "Unthrottled (no max-Q or g limit); no sized structural mass for the 3.0 g push load; "
        "the penalty row charges an assumed stage-1 dry mass."
    )
    # fix round 3, S3A-NUM-01: width_px None gives the structural line in one piece
    unwrapped = plots.animation_caveats(runs, "toy_2d", width_px=None)
    assert len(unwrapped) == 4 and unwrapped[2] == " ".join(mixed[2:-1])
    assert unwrapped[:2] == mixed[:2] and unwrapped[-1] == mixed[-1]
    assert mixed[-1].startswith("Vehicle toy_2d: no calibration record on file.")
    _assert_footnote_fits(mixed)
    alone = plots.animation_caveats([pad, modelled], "toy_2d")
    assert alone[1] == "Unthrottled (no max-Q or g limit)."
    assert " ".join(alone[2:-1]) == (
        f"Structure, per run: silo_s1_st carries {SPLIT_9100} of modelled structural mass "
        f"(set central; first-order sizing, not an assumed penalty); {FOOTNOTE_POINTER}."
    )
    assert "no sized structural mass" not in " ".join(alone)
    # runs whose stage-2 share is unrecorded keep the total and share one clause
    whole = dataclasses.replace(modelled, structure_dm_stage2_kg=None)
    two = " ".join(plots.animation_caveats([pad, whole, whole], "toy_2d")[2:-1])
    assert two == (
        "Structure, per run: silo_s1_st and silo_s1_st carry 9,100 and 9,100 kg of modelled "
        "structural mass (set central; first-order sizing, not an assumed penalty); "
        f"{FOOTNOTE_POINTER}."
    )
    assert "structure (" not in two and "structures" not in two
    unrecorded = dataclasses.replace(modelled, structure_dm_kg=None)
    assert " ".join(plots.animation_caveats([pad, unrecorded], "toy_2d")[2:-1]) == (
        "Structure, per run: silo_s1_st carries a modelled structural mass of unrecorded size "
        f"(set central; first-order sizing, not an assumed penalty); {FOOTNOTE_POINTER}."
    )
    assert " ".join(plots.animation_caveats([pad, whole, unrecorded], "toy_2d")[2:-1]) == (
        "Structure, per run: silo_s1_st and silo_s1_st carry 9,100 kg and an unrecorded size of "
        "modelled structural mass (set central; first-order sizing, not an assumed penalty); "
        f"{FOOTNOTE_POINTER}."
    )
    plain = plots.animation_caveats([pad, silo], "toy_2d")
    assert len(plain) == 3
    assert (
        plain[1]
        == "Unthrottled (no max-Q or g limit); no sized structural mass for the 3.0 g push load."
    )
    assert "of silo" not in plain[1]  # the uncharged wording is unchanged without a modelled run
    # the structure payload case's run: modelled from its own record, labelled by its kind
    (pstar,), _ = plots.load_animation_runs(run_dir, ["silo_pstar_st"])
    assert pstar.modelled is True and pstar.structure_dm_kg == pytest.approx(9100.3)
    assert pstar.penalty_added_kg is None and pstar.offload is not None
    assert pstar.offload.kind == plots.OFFLOAD_STRUCTURE_PAYLOAD == "structure payload case"
    assert plots._legend_label(pstar, pad) == (
        f"silo_pstar_st (structure payload case): P* {P_REF_KG + PSTAR_DELTA_KG:,.0f} kg "
        f"({PSTAR_DELTA_KG:+,.0f} kg vs P_ref)\non the full load, carrying its modelled structure"
    )
    assert " ".join(plots.animation_caveats([pad, silo, pstar], "toy_2d")[2:-1]) == (
        f"Structure, per run: silo_pstar_st carries {SPLIT_9100} of modelled structural mass "
        "(set central; first-order sizing, not an assumed penalty); no sized structural mass "
        f"for the 3.0 g push load of silo; {FOOTNOTE_POINTER}."
    )
    # fix round 2, H-S3a-P2-04: the footnote says the set, the plausibility rule's factor
    # when the dm carries it and the fired flags (the release flag with D-SP7-39's
    # comparison), all read from the run's own record; runs whose qualifiers differ get one
    # clause each
    assert (modelled.structure_set, modelled.structure_scale_factor) == ("central", None)
    assert modelled.structure_flags_fired == () and modelled.structure_release_note is None
    scaled = dataclasses.replace(
        modelled,
        name="silo_lo_st",
        structure_dm_kg=3476.4,
        structure_dm_stage2_kg=0.0,
        structure_set="physics_low_mass",
        structure_scale_factor=0.845549,
        structure_flags_fired=("structure_release_unload", "structure_payload_limit"),
        structure_release_note=(
            "D-SP7-39: the pad's own MECO separates stage 2's LOX column too under the same "
            "step treatment"
        ),
    )
    both = " ".join(plots.animation_caveats([pad, modelled, scaled], "toy_2d")[2:-1])
    assert both == (
        f"Structure, per run: silo_s1_st carries {SPLIT_9100} of modelled structural mass (set "
        "central; first-order sizing, not an assumed penalty); silo_lo_st carries 3,476 kg of "
        "modelled structural mass (set physics_low_mass, scaled x0.846 by the plausibility "
        "rule; flags fired: structure_release_unload (D-SP7-39: the pad's own MECO separates "
        "stage 2's LOX column too under the same step treatment) and structure_payload_limit; "
        f"first-order sizing, not an assumed penalty); {FOOTNOTE_POINTER}."
    )
    assert "not assumed" not in both and both.count("not an assumed penalty)") == 2
    # fix round 3, H-S3a-P3-04: a design-axis row on the central set never shares the
    # headline central case's clause
    margin = dataclasses.replace(
        whole,
        name="silo_s1_st_m05",
        structure_dm_kg=9800.0,
        structure_departures=("margin 0.05",),
    )
    assert " ".join(plots.animation_caveats([whole, margin], "toy_2d")[2:-1]) == (
        "Structure, per run: silo_s1_st carries 9,100 kg of modelled structural mass (set "
        "central; first-order sizing, not an assumed penalty); silo_s1_st_m05 carries 9,800 kg "
        "of modelled structural mass (set central at margin 0.05; first-order sizing, not an "
        f"assumed penalty); {FOOTNOTE_POINTER}."
    )
    for width in FOOTNOTE_TEST_WIDTHS_PX:
        lines = plots.animation_caveats([pad, silo, modelled, scaled], "toy_2d", width_px=width)
        rights, limit = plots.footnote_right_px(lines, width)
        assert all(right < limit for right in rights), (width, lines)
    # read from a record: the scale factor only when the record says the dm carries it
    metrics = metrics_of(run_dir)
    record = metrics["offload"]["runs"]["silo_s1_st"]
    record.update(
        structure_set="physics_low_mass",
        structure_plausibility_scaled=True,
        structure_plausibility_factor=0.845549,
        structure_flags=[
            {"name": "structure_payload_limit", "fired": True, "values": {}},
            {"name": "structure_upper_stack_exceeded", "fired": False, "values": {}},
        ],
    )
    read = plots.read_animation_run(run_dir, "silo_s1_st", metrics)
    assert (read.structure_set, read.structure_scale_factor) == ("physics_low_mass", 0.845549)
    assert read.structure_flags_fired == ("structure_payload_limit",)
    assert read.structure_departures == ()
    record["structure_plausibility_scaled"] = False
    unscaled = plots.read_animation_run(run_dir, "silo_s1_st", metrics)
    assert unscaled.structure_scale_factor is None
    record.update(structure_set="central", structure_margin=0.05, structure_dynamic="step")
    axis = plots.read_animation_run(run_dir, "silo_s1_st", metrics)
    assert axis.structure_departures == ("margin 0.05", "dynamic step")
    assert plots._footnote_qualifier(axis).startswith("(set central at margin 0.05, dynamic step;")
    # a long structural line wraps by measured width, every piece within the frame
    long_names = [dataclasses.replace(modelled, name=f"silo_structural_case_{k}") for k in range(3)]
    wrapped = plots.animation_caveats([pad, silo, *long_names], "toy_2d")
    assert len(wrapped) >= 5 and wrapped[2].startswith(plots.STRUCTURE_FOOTNOTE_HEAD)
    _assert_footnote_fits(wrapped)
    assert " ".join(wrapped[2:-1]).endswith(f"push load of silo; {FOOTNOTE_POINTER}.")
    # names rich in digits, underscores and wide glyphs (N-S3a-R1-01: a character budget
    # let them run past the frame), three modelled runs beside an uncharged one
    for names, dm in (
        (
            (
                "silo_warm_200m_mmw_st_dry+8.1t",
                "silo_warm_300m_mmw_st_dry+10.0t",
                "silo_warm_100m_mmw_st_dry+12.5t",
            ),
            123456.7,
        ),
        (tuple(f"1234567890_1234567890_1234567890_{k}" for k in range(3)), 1234567.0),
        (tuple("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm_" + str(k) for k in range(3)), 99999.0),
    ):
        heavy = [dataclasses.replace(modelled, name=n, structure_dm_kg=dm) for n in names]
        wide = dataclasses.replace(silo, name="silo_warm_mmw_wwmm_200m")
        lines = plots.animation_caveats([pad, wide, *heavy], "generic_f9_class_2d")
        _assert_footnote_fits(lines)
        # wrapped at each frame's own width (fix round 2, N2-03), every line fits that frame
        for width in FOOTNOTE_TEST_WIDTHS_PX:
            at = plots.animation_caveats([pad, wide, *heavy], "generic_f9_class_2d", width_px=width)
            structural = [line for line in at if line not in (at[0], at[1], at[-1])]
            rights, limit = plots.footnote_right_px(structural, width)
            assert all(right < limit for right in rights), (width, structural)
        joined = " ".join(lines[2:-1])
        assert joined.startswith(plots.STRUCTURE_FOOTNOTE_HEAD) and all(n in joined for n in names)
        assert joined.endswith(f"push load of silo_warm_mmw_wwmm_200m; {FOOTNOTE_POINTER}.")
        for a, b in itertools.pairwise(lines[2:-1]):
            assert not (a[-1].isdigit() and b.split(" ")[0] in ("g", "kg", "t")), (a, b)
    assert plots.footnote_tokens("for the 3.0 g push; 9,100 kg, 2 t.") == [
        "for",
        "the",
        "3.0 g",
        "push;",
        "9,100 kg,",
        "2 t.",
    ]
    # the footnote block with its extra lines stays clear of every panel's axis label at 1280 px
    size, dpi, _ = plots.frame_geometry(1280)
    fig = plots._AscentFigure([pad, silo, *long_names], metrics_of(run_dir), "toy_2d", size, dpi)
    canvas = FigureCanvasAgg(fig.fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    top_px = fig.footnote.get_window_extent(renderer=renderer).y1
    labels = [
        ax.xaxis.label.get_window_extent(renderer=renderer).y0
        for ax in fig.fig.axes
        if ax.xaxis.label.get_text()
    ]
    assert labels and top_px < min(labels), (top_px, min(labels))


def test_footnote_gives_the_stage_split_and_points_to_the_summary(tmp_path: Path) -> None:
    """S3a gate fix (G1): the footnote is the only caveat of an ``animate`` frame, so a
    modelled run whose record's stage-2 share (``structure_dm_stage2_kg``) is above zero
    gives its mass by stage, dm1 = dm - dm2 as replay's modelled sentence reads it and
    to 0.1 kg as it prints it ('8,900.1 kg (stage 1) and 200.2 kg (stage 2) of modelled
    structural mass'; S3a gate review, R-G1-05: a share under 0.5 kg reads '0.3 kg
    (stage 2)', never '0 kg'), and a run whose share is zero, absent, None or not finite
    keeps the total as before; runs whose mass is given by stage take a clause each (same
    qualifier or not); the structural line ends, once, with the pointer to summary.md
    (R-G1-02 and R-G1-03): the mass by stage in its offload section's caveats (where a
    structure payload case's split is given too), the structure file and x* at the
    physics band's ends in its Structure subsection, neither of which the frame quotes
    (phase file, deviation 38: no file path, no band end on the frame); a footnote with no
    modelled run is unchanged word for word and has no pointer; every line of every
    selection fits each test width and, at 1280 px, by this file's own Agg measurement
    too (R-G1-06); ``width_px`` None gives the line, pointer included, in one piece."""
    run_dir = _make_offload_run_dir(tmp_path)
    metrics = metrics_of(run_dir)
    record = metrics["offload"]["runs"]["silo_s1_st"]
    pad, silo, penalty = (
        plots.read_animation_run(run_dir, n, metrics) for n in ("pad", "silo", "silo_fix5")
    )
    read = plots.read_animation_run(run_dir, "silo_s1_st", metrics)
    assert read.structure_dm_stage2_kg == pytest.approx(200.2)
    assert (pad.structure_dm_stage2_kg, silo.structure_dm_stage2_kg) == (None, None)
    assert plots.STRUCTURE_FOOTNOTE_POINTER == FOOTNOTE_POINTER
    vehicle = "generic_f9_class_2d"
    one = plots.animation_caveats([pad, read], vehicle)
    assert " ".join(one[2:-1]) == (
        "Structure, per run: silo_s1_st carries 8,900.1 kg (stage 1) and 200.2 kg (stage 2) "
        "of modelled structural mass (set central; first-order sizing, not an assumed "
        "penalty); modelled mass by stage: the caveats of summary.md's offload section; "
        "structure file and x* at the physics band's ends: its Structure subsection."
    )
    total = (
        "Structure, per run: silo_s1_st carries 9,100 kg of modelled structural mass (set "
        f"central; first-order sizing, not an assumed penalty); {FOOTNOTE_POINTER}."
    )
    for share in (0.0, None, float("nan"), "absent"):
        if share == "absent":
            del record["structure_dm_stage2_kg"]
        else:
            record["structure_dm_stage2_kg"] = share
        whole = plots.read_animation_run(run_dir, "silo_s1_st", metrics)
        expected = 0.0 if share == 0.0 else None
        assert whole.structure_dm_stage2_kg == expected, share
        assert " ".join(plots.animation_caveats([pad, whole], vehicle)[2:-1]) == total, share
    # a mass all on stage 2 still reads by stage, dm1 the difference
    upper = dataclasses.replace(read, structure_dm_kg=312.4, structure_dm_stage2_kg=312.4)
    assert plots._footnote_stage_split(upper) == "0.0 kg (stage 1) and 312.4 kg (stage 2)"
    # a stage-2 share under 0.5 kg reads as the replay caveat prints it (R-G1-05)
    small = dataclasses.replace(read, structure_dm_kg=9100.3, structure_dm_stage2_kg=0.3)
    assert plots._footnote_stage_split(small) == "9,100.0 kg (stage 1) and 0.3 kg (stage 2)"
    assert " 0 kg (stage 2)" not in " ".join(plots.animation_caveats([pad, small], vehicle))
    # two runs given by stage take a clause each, the pointer once at the end
    high = dataclasses.replace(
        read,
        name="silo_hi_st",
        structure_dm_kg=18603.8,
        structure_dm_stage2_kg=312.4,
        structure_set="physics_high_mass",
    )
    twin = dataclasses.replace(read, name="silo_s1_st_b")
    two = " ".join(plots.animation_caveats([read, high], vehicle)[2:-1])
    assert two == (
        f"Structure, per run: silo_s1_st carries {SPLIT_9100} of "
        "modelled structural mass (set central; first-order sizing, not an assumed penalty); "
        "silo_hi_st carries 18,291.4 kg (stage 1) and 312.4 kg (stage 2) of modelled "
        "structural mass (set physics_high_mass; first-order sizing, not an assumed penalty); "
        f"{FOOTNOTE_POINTER}."
    )
    same = " ".join(plots.animation_caveats([read, twin], vehicle)[2:-1])
    assert same.count(f" carries {SPLIT_9100} of modelled ") == 2
    assert " carry " not in same
    mixed = " ".join(plots.animation_caveats([pad, silo, read, penalty], vehicle)[2:-1])
    assert mixed.endswith(f"for the 3.0 g push load of silo; {FOOTNOTE_POINTER}.")
    selections = ([pad, read], [read, high], [read, twin], [pad, silo, read, penalty])
    for runs in selections:
        joined = " ".join(plots.animation_caveats(runs, vehicle))
        assert joined.count(FOOTNOTE_POINTER) == 1 and joined.count("summary.md") == 1
        # the file path and the band's dm ends stay off the frame (deviation 38); the
        # pointer names x* at the band's ends, the Structure subsection's quantity
        assert "configs/structures" not in joined and "toy.yaml" not in joined
        assert "3,677" not in joined and "18,604" not in joined and " are dm " not in joined
        assert "headline push" not in joined and "x* at the physics band's ends" in joined
        for width in FOOTNOTE_TEST_WIDTHS_PX:
            lines = plots.animation_caveats(runs, vehicle, width_px=width)
            rights, limit = plots.footnote_right_px(lines, width)
            assert all(right < limit for right in rights), (width, lines)
            assert " ".join(lines[2:-1]).endswith(f"; {FOOTNOTE_POINTER}."), (width, lines)
        unwrapped = plots.animation_caveats(runs, vehicle, width_px=None)
        assert len(unwrapped) == 4 and unwrapped[2].endswith(f"; {FOOTNOTE_POINTER}.")
        # and at 1280 px by this file's own Agg measurement (R-G1-06)
        _assert_footnote_fits(plots.animation_caveats(runs, vehicle))
    # no modelled run: the three lines word for word, no pointer
    plain = plots.animation_caveats([pad, silo, penalty], "toy_2d")
    assert plain == [
        "Planar 2-D model (rotating spherical Earth, ICAO atmosphere, drag); "
        "sweep-optimized guidance, not optimal control.",
        "Unthrottled (no max-Q or g limit); no sized structural mass for the 3.0 g push load; "
        "the penalty row charges an assumed stage-1 dry mass.",
        "Vehicle toy_2d: no calibration record on file. A model replay, not a design result.",
    ]
    assert "summary.md" not in " ".join(plain)


def _end_phase(run: plots.AnimationRun) -> str:
    """The readout's phase of ``run`` from its last time on."""
    return plots._phase_at(run, run.t_end_s)


def test_offload_runs_are_labelled_from_the_offload_record(tmp_path: Path) -> None:
    """A run recorded only in metrics.json ``offload.runs`` takes its payload and status
    from that record, as replay does: the solved case silo_s1 flies P_REF_KG and reads
    'inserted' at its end, its legend giving the offload in tonnes (41,262.9 kg / 1000 =
    41.3 t) and no change against the baseline; the paired pad gives its own P* (959 kg)
    and 958.6 - 1000 = -41 kg against P_ref. The experiment runs keep their labels word
    for word (pad 1,000 kg; silo 1,100 kg, +100 kg against it) and the legend title is
    LEGEND_TITLE unless an offload run is shown, when it names P_ref."""
    run_dir = _make_offload_run_dir(tmp_path)
    runs, metrics = plots.load_animation_runs(run_dir, ["pad", "silo", "silo_s1", "silo_s1__pad"])
    pad, silo, case, paired = runs
    assert (pad.offload, silo.offload) == (None, None)
    assert plots._legend_label(pad, pad) == f"pad (baseline): P* {P_REF_KG:,.0f} kg"
    assert plots._legend_label(silo, pad) == "silo: P* 1,100 kg (+100 kg)"
    assert case.payload_kg == pytest.approx(P_REF_KG) and case.status == "inserted"
    assert paired.payload_kg == pytest.approx(PAIRED_PAD_KG) and paired.status == "inserted"
    assert case.offload is not None and case.offload.kind == plots.OFFLOAD_CASE == "offload case"
    assert paired.offload is not None and paired.offload.kind == plots.OFFLOAD_PAIRED_PAD
    offload_t = CASE_OFFLOAD_KG / 1000.0
    assert plots._legend_label(case, pad) == (
        f"silo_s1 (offload case): flies P_ref {P_REF_KG:,.0f} kg\n"
        f"on {offload_t:.1f} t less propellant"
    )
    assert "41.3 t" in plots._legend_label(case, pad)
    assert plots._legend_label(paired, pad) == (
        f"silo_s1__pad (paired pad): P* {PAIRED_PAD_KG:,.0f} kg "
        f"({PAIRED_PAD_KG - P_REF_KG:+,.0f} kg vs P_ref)\nwith the same offload, no push"
    )
    assert "P* 959 kg (-41 kg vs P_ref)" in plots._legend_label(paired, pad)
    assert [_end_phase(r) for r in runs] == ["inserted"] * 4
    assert plots.legend_title(runs[:2], metrics) == plots.LEGEND_TITLE
    assert plots.LEGEND_TITLE == "payload capacity P* (sweep-optimized)"
    assert plots.legend_title(runs, metrics) == f"{plots.LEGEND_TITLE}; P_ref = pad's P*"


def test_pad_controls_are_labelled_as_pad_controls_not_failures(tmp_path: Path) -> None:
    """The stage-1 pad control's recorded run ends short_of_orbit by grams by
    construction (m_res(0) = -0.0016 kg, within the search resolution): it is labelled a
    pad control flying P_ref with no offload, its second legend line gives 0.0016 kg of
    propellant short of orbit as a resolution effect, not a failure, and its readout
    ends '~inserted', not 'ended, short_of_orbit'. An ok control gives its x_pad (513.6
    kg = 0.5 t); a no_offload control that misses by more (m_res(0) = -3 kg) still reads
    'ended, short_of_orbit'. A fixed case gives its own P* against P_ref (1,030 - 1,000 =
    +30 kg) and its imposed 20.0 t."""
    run_dir = _make_offload_run_dir(tmp_path)
    names = ["pad", "pad__offload_stage1", "pad__offload_stage2", "pad__offload_both"]
    runs, _ = plots.load_animation_runs(run_dir, names)
    pad, stage1, stage2, both = runs
    assert stage1.status == "short_of_orbit" and stage1.payload_kg == pytest.approx(P_REF_KG)
    assert stage1.offload is not None and stage1.offload.kind == plots.OFFLOAD_PAD_CONTROL
    assert stage1.offload.resolution_effect
    head, detail = plots._legend_label(stage1, pad).split("\n")
    assert head == f"pad__offload_stage1 (pad control): flies P_ref {P_REF_KG:,.0f} kg, no offload"
    assert detail.startswith(f"{abs(CONTROL_M_RES_KG):.2g} kg of propellant short of orbit")
    assert detail.startswith("0.0016 kg") and "resolution effect, not a failure" in detail
    assert _end_phase(stage1) == plots.NEAR_ORBIT_PHASE == "~inserted"
    assert plots._legend_label(stage2, pad) == (
        f"pad__offload_stage2 (pad control): flies P_ref {P_REF_KG:,.0f} kg\n"
        f"on {CONTROL_OFFLOAD_KG / 1000.0:.1f} t less propellant"
    )
    assert _end_phase(stage2) == "inserted"
    assert both.offload is not None and not both.offload.resolution_effect
    assert _end_phase(both) == "ended, short_of_orbit"
    assert "more than the search resolution" in plots._legend_label(both, pad)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    record, tag = plots.animation_record(metrics, "silo_fix5")
    assert record["payload_kg"] == FIXED_PAYLOAD_KG and tag is not None
    assert tag.legend == (
        f"P* {FIXED_PAYLOAD_KG:,.0f} kg ({FIXED_PAYLOAD_KG - P_REF_KG:+,.0f} kg vs P_ref)\n"
        f"on {FIXED_OFFLOAD_KG / 1000.0:.1f} t less propellant"
    )
    assert "(+30 kg vs P_ref)" in tag.legend and "20.0 t" in tag.legend
    assert plots.animation_record(metrics, "pad") == (metrics["runs"]["pad"], None)
    assert plots.animation_record(metrics, "nowhere") == ({}, None)


def test_solved_case_without_an_offload_says_it_misses_orbit(tmp_path: Path) -> None:
    """A solved case whose solve found no offload (status no_offload) records its
    full-load run (x* = 0), which cannot carry P_ref: its legend says so instead of
    'flies P_ref ... on 0.0 t less propellant', and its readout ends 'ended,
    short_of_orbit' (its record's status), not '~inserted' (no resolution effect)."""
    run_dir = _make_offload_run_dir(tmp_path)
    runs, _ = plots.load_animation_runs(run_dir, ["pad", "silo_none"])
    pad, none = runs
    assert none.payload_kg == pytest.approx(P_REF_KG) and none.status == "short_of_orbit"
    assert none.offload is not None and none.offload.kind == plots.OFFLOAD_CASE
    assert not none.offload.resolution_effect
    assert plots._legend_label(none, pad) == (
        f"silo_none (offload case): flies P_ref {P_REF_KG:,.0f} kg, no offload\n"
        "does not reach orbit at P_ref even at full load"
    )
    assert "less propellant" not in plots._legend_label(none, pad)
    assert _end_phase(none) == "ended, short_of_orbit"


def test_offload_animation_renders_with_its_legend_inside_the_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``animate --runs pad silo_s1`` writes a GIF; drawn at 1280 and 640 px, the legend
    of each offload selection (pad with the offloaded silo, the paired pad with it, and
    the three together) ends left of the trajectory panel's right edge, its bottom lies
    above every drawn path point under it, it overlaps no event label shown on the
    trajectory panel at the end of the flight (where the 'cutoff' label sits at the top
    of the path), its title names P_ref, and the readout ends 'inserted' for every run.
    The runs fly the orbit-shaped ascent (level at the top, like a real insertion), so
    the path under the legend runs near its top. Clearances are measured on the drawn
    artists in pixels, not from the layout rule."""
    run_dir = _make_offload_run_dir(tmp_path, orbit=True)
    _no_ffmpeg(monkeypatch)
    out = tmp_path / "offload.gif"
    args = ["animate", str(run_dir), "--runs", "pad", "silo_s1", "--out", str(out)]
    code = main([*args, "--fps", "2", "--seconds", "1", "--width", "320"])
    assert code == 0, capsys.readouterr().out
    assert out.is_file()
    selections = (
        ["pad", "silo_s1"],
        ["silo_s1__pad", "silo_s1"],
        ["pad", "silo_s1", "silo_s1__pad"],
    )
    for names in selections:
        runs, metrics = plots.load_animation_runs(run_dir, names)
        for width in (1280, 640):
            size, dpi, _ = plots.frame_geometry(width)
            fig = plots._AscentFigure(runs, metrics, "toy_2d", size, dpi)
            canvas = FigureCanvasAgg(fig.fig)
            fig.draw_frame(fig.t1, 0.0)
            canvas.draw()
            renderer = canvas.get_renderer()
            legend = fig.ax_main.get_legend()
            assert legend.get_title().get_text().endswith("P_ref = pad's P*")
            box = legend.get_window_extent(renderer=renderer)
            assert box.x1 < fig.ax_main.get_window_extent(renderer=renderer).x1, (names, width)
            path_gap, label_gap = _legend_clearance(fig, renderer)
            assert path_gap > 0.0, (names, width, path_gap)
            assert label_gap > 0.0, (names, width, label_gap)
            assert all(" inserted " in r.get_text() for r in fig.readouts)


def _legend_clearance(fig: plots._AscentFigure, renderer: object) -> tuple[float, float]:
    """(legend bottom less the highest drawn path point under the legend, legend bottom
    less the top of the highest visible trajectory-panel event label that shares its
    columns) [px] of a drawn frame; inf when nothing lies under the legend."""
    ax = fig.ax_main
    box = ax.get_legend().get_window_extent(renderer=renderer)
    path_top = -math.inf
    for run in fig.runs:
        km = np.column_stack([run.downrange_m, run.alt_m]) / 1000.0
        px = ax.transData.transform(km)
        under = px[(px[:, 0] >= box.x0) & (px[:, 0] <= box.x1)]
        if under.size:
            path_top = max(path_top, float(under[:, 1].max()))
    label_top = -math.inf
    for group in fig.label_groups:
        artist = group.artist
        if group.ax is not ax or not artist.get_visible() or not artist.get_text():
            continue
        label = artist.get_window_extent(renderer=renderer)
        if min(box.x1, label.x1) > max(box.x0, label.x0):
            label_top = max(label_top, label.y1)
    return box.y0 - path_top, box.y0 - label_top


def test_frame_geometry_is_16_by_9_and_even() -> None:
    for width, height in ((1280, 720), (640, 360), (1000, 562)):
        size, dpi, frame = plots.frame_geometry(width)
        assert frame == (width, height)
        assert int(size[0] * dpi) == width and int(size[1] * dpi) == height
    with pytest.raises(plots.AnimationError, match="even"):
        plots.frame_geometry(641)
    with pytest.raises(plots.AnimationError):
        plots.frame_geometry(100)
