"""The interactive replay page (replay.write_replay_page, ``launchsim replay``) on a tiny
synthetic planar results directory: the embedded JSON parses, holds no NaN or Infinity,
and carries every selected run with its events and the shaft's undefined q as null; the
common clock steps 0.1 s then 1 s and interpolates the source linearly; bound re-runs
and cases read their own metrics and config; a run that did not reach orbit shows no
comparison or losses; the flight-path angle is wrapped; the page is a self-contained
UTF-8 document; the default output lands outside the results tree; vertical_1d runs,
sweep points, unknown, repeated or too many runs and outputs inside results/ are
refused with one error line; the text is generated from the run data (calibration
caveat conditional on the vehicle, each run's own dry-mass slope and upper-bound
flags; the push's net acceleration from the run's ``net_accel_g`` metric, so a run
defined by exit speed has its label, with the config key as the fallback for results
written before the metric); and the page's inline script is syntactically valid
(checked with node when it is installed, skipped otherwise)."""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from launchsim import replay
from launchsim.cli import main
from launchsim.constants import G0_MPS2

EXPERIMENT = "synth_replay_2d"
TIMESTAMP = "20260101T000000Z"
T_END_S = 60.0
PUSH_S = 2.0
DEPTH_M = 50.0
SERIES_COLUMNS = [*replay.REPLAY_COLUMNS, "stage"]
EVENT_COLUMNS = ["t_s", "event", "phase", "stage", "alt_m", "downrange_m", "speed_rel_mps", "m_kg"]
RUNS = ("pad", "silo", "silo_step")
BOUND_AND_CASE_RUNS = {"pad__aero_bound": False, "silo__aero_bound": True, "alt_low": False}
"""Run folders outside metrics.json runs: a bound re-run, its paired baseline, a case."""


def _row(t_rel: float, offset: float, assist: bool) -> dict[str, object]:
    """One synthetic row at t_rel [s after release]: a vented-shaft push from -DEPTH_M
    (q and Mach undefined) for an assisted run, a hold on the pad otherwise, then a
    smooth climb."""
    if t_rel < 0.0:
        frac = 1.0 + t_rel / PUSH_S
        return {
            "t_s": t_rel + offset,
            "t_rel_release_s": t_rel,
            "phase": "ASSIST" if assist else "HOLD",
            "stage": "stage1",
            "alt_m": -DEPTH_M * (1.0 - frac**2) if assist else 0.0,
            "downrange_m": 0.0,
            "speed_rel_mps": 50.0 * frac if assist else 0.0,
            "gamma_rel_rad": math.pi / 2,
            "felt_axial_g": 4.0 if assist else 1.0,
            "q_pa": math.nan if assist else 0.0,
            "mach": math.nan if assist else 0.0,
            "m_kg": 1000.0,
        }
    return {
        "t_s": t_rel + offset,
        "t_rel_release_s": t_rel,
        "phase": "GRAVITY_TURN" if t_rel < 40.0 else "LTG_BURN",
        "stage": "stage1" if t_rel < 40.0 else "stage2",
        "alt_m": (2.0 + t_rel) ** 2 * 10.0,
        "downrange_m": t_rel**3,
        "speed_rel_mps": 50.0 + 20.0 * t_rel,
        "gamma_rel_rad": math.pi / 2 - t_rel / T_END_S,
        "felt_axial_g": 1.5 + t_rel / 40.0,
        "q_pa": 1000.0 * math.sin(math.pi * t_rel / T_END_S),
        "mach": t_rel / 10.0,
        "m_kg": 1000.0 - 10.0 * t_rel,
    }


def _events(assist: bool) -> list[tuple[str, float]]:
    """(event, t after release [s]) of a synthetic run."""
    return [
        ("push_start" if assist else "ignition", -PUSH_S),
        ("release", 0.0),
        ("ignition" if assist else "kick_end", 1.0),
        ("propellant", 40.0),
        ("staging", 40.0),
        ("fairing", 50.0),
        ("cutoff", T_END_S),
        ("end", T_END_S),
    ]


def _write_run(run_dir: Path, name: str, assist: bool) -> None:
    """<run_dir>/<name>/timeseries.csv and events.csv of one synthetic planar run."""
    offset = PUSH_S  # t_s starts at 0 at the first row
    rows = [_row(float(t), offset, assist) for t in np.arange(-PUSH_S, T_END_S + 1e-9, 0.5)]
    folder = run_dir / name
    folder.mkdir(parents=True)
    with (folder / "timeseries.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SERIES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with (folder / "events.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        for event, t_rel in _events(assist):
            row = _row(t_rel, offset, assist)
            writer.writerow({"event": event, **{k: row[k] for k in EVENT_COLUMNS if k != "event"}})


def _run_metrics(assist: bool, step: bool) -> dict[str, Any]:
    """metrics.json record of a synthetic run (drag loss NaN, as a failed term writes)."""
    record: dict[str, Any] = {
        "status": "inserted",
        "payload_kg": 1100.0 if assist else 1000.0,
        "startup_kind_stage1": "step" if step else "ramp",
        "t_startup_s_stage1": 0.0 if step else 2.0,
        "t_ign_rel_release_s_stage1": 0.0 if step else (0.5 if assist else -2.0),
        "max_q_pa": 1000.0,
        "peak_felt_axial_g_flight": 3.0,
        "gravity_loss_mps": 1400.0,
        "drag_loss_mps": math.nan,
        "steering_loss_mps": 90.0,
        "back_pressure_loss_mps": 50.0,
        "assist_model": "constant_accel" if assist else "none",
    }
    if assist:
        record.update(
            exit_speed_mps=50.0,
            felt_g_track_peak=4.0,
            push_time_s=PUSH_S,
            track_start_altitude_m=-DEPTH_M,
        )
    return record


def _run_config(
    assist: bool, orbit_km: float = 200, rotation: bool = True, vehicle: str | None = None
) -> dict[str, Any]:
    """resolved_config.yaml entry of a synthetic run (its own vehicle name when given)."""
    block: dict[str, Any] = {"model": "none"}
    if assist:
        block = {
            "model": "constant_accel",
            "net_accel_g": 3.0,
            "stroke_m": DEPTH_M,
            "carriage_mass_t": 0,
            "shaft": "vented",
            "track": {"angle_deg": 90, "exit_altitude_m": 0},
        }
    entry: dict[str, Any] = {
        "run": {
            "site": {"latitude_deg": 28.5, "azimuth_deg": 90, "include_rotation": rotation},
            "planar": {"target_orbit": {"kind": "circular", "altitude_km": orbit_km}},
            "assist": block,
        }
    }
    if vehicle is not None:
        entry["vehicle"] = {"name": vehicle}
    return entry


def _dry_mass_case(fraction: float, payload_kg: float) -> dict[str, Any]:
    """A stage-1 dry-mass sensitivity case of 'silo' (dry mass 1000 kg, +/- fraction),
    whose comparison with the unperturbed baseline is an unexplained beat (which must not
    cast doubt on the slope: it rests on the payloads alone)."""
    return {
        "of": "silo",
        "param": replay.DRY_MASS_PARAM,
        "fraction": fraction,
        "value_si": 1000.0 * (1.0 + fraction),
        "payload_kg": payload_kg,
        "comparison": {"screening_status": "not_checked", "beats_screening": True},
    }


def _make_run_dir(root: Path, model: str | None = "planar_2d", vehicle: str = "toy_2d") -> Path:
    """A synthetic results/<experiment>/<timestamp> directory: the baseline 'pad' (held
    on the pad), 'silo' (a vented-shaft push, cold start) and 'silo_step' (the same push,
    instant ignition; an upper-bound gain, its steering loss Infinity); the bound re-run
    'silo__aero_bound' with its paired baseline 'pad__aero_bound'; and the case
    'alt_low' (150 km orbit, non-rotating Earth, its own vehicle). Dry-mass cases of
    'silo' give dP*/d(dry mass) = -0.2 kg/kg. 'silo_step' has a 5 t carriage and its
    exhaust impinges on it; 'silo' has a screening yardstick (P0 basis) below its ideal
    screening."""
    run_dir = root / "results" / EXPERIMENT / TIMESTAMP
    run_dir.mkdir(parents=True)
    flags = {"pad": (False, False), "silo": (True, False), "silo_step": (True, True)}
    for name, (assist, _) in flags.items():
        _write_run(run_dir, name, assist)
    for name, assist in BOUND_AND_CASE_RUNS.items():
        _write_run(run_dir, name, assist)
    runs = {n: _run_metrics(a, s) for n, (a, s) in flags.items()}
    runs["silo_step"]["steering_loss_mps"] = math.inf
    comparison = {
        n: {
            "payload_delta_kg": 100.0,
            "ideal_screening_payload_at_release_speed_at_pbase_kg": 60.0,
            "payload_delta_upper_bound": False,
        }
        for n in ("silo", "silo_step")
    }
    comparison["silo_step"].update(payload_delta_upper_bound=True, q_alpha_above_baseline=True)
    comparison["silo"]["screening_yardstick_kg"] = 52.0
    metrics: dict[str, Any] = {
        "experiment": EXPERIMENT,
        "timestamp_utc": TIMESTAMP,
        "git": {"hash": "abc123", "dirty": False},
        "baseline": "pad",
        "runs": runs,
        "comparison": comparison,
        "sensitivity": [_dry_mass_case(0.1, 1080.0), _dry_mass_case(-0.1, 1120.0)],
        "bounds": [
            {
                "bound": "aero_bound",
                "of": "silo",
                "run": "silo__aero_bound",
                "paired_baseline": "pad__aero_bound",
                "overrides": {"vehicle.aero.reference_area_m2": 21.24},
                "metrics": {**_run_metrics(True, False), "payload_kg": 1090.0},
                "paired_baseline_metrics": {**_run_metrics(False, False), "payload_kg": 990.0},
                "comparison_vs_paired_baseline": {
                    "payload_delta_kg": 90.0,
                    "ideal_screening_payload_at_release_speed_at_pbase_kg": 55.0,
                    "payload_delta_upper_bound": False,
                },
            }
        ],
        "cases": {"alt_low": {**_run_metrics(False, False), "payload_kg": 1050.0}},
    }
    if model is not None:
        metrics["model"] = model
    # json.dumps writes NaN and Infinity as bare literals, as the simulator may.
    (run_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    config = {
        "experiment": EXPERIMENT,
        "vehicle": {"name": vehicle},
        "runs": {n: _run_config(a) for n, (a, _) in flags.items()},
        "bound_runs": {
            n: {**_run_config(a), "vehicle": {"name": vehicle}}
            for n, a in BOUND_AND_CASE_RUNS.items()
            if n != "alt_low"
        },
        "cases": {
            "alt_low": _run_config(False, orbit_km=150, rotation=False, vehicle="toy_2d_light")
        },
    }
    config["runs"]["silo_step"]["run"]["assist"].update(
        carriage_mass_t=5, exhaust_impingement_fraction=1.0
    )
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return run_dir


def _listing(folder: Path) -> set[Path]:
    return set(folder.rglob("*"))


def _no_nan(token: str) -> float:
    raise AssertionError(f"non-JSON constant {token} in the embedded data")


def _embedded(page: str) -> dict[str, Any]:
    """The JSON of the page's replay-data block, parsed strictly (no NaN/Infinity)."""
    match = re.search(
        r'<script type="application/json" id="replay-data">(.*?)</script>', page, re.S
    )
    assert match is not None
    return json.loads(match.group(1), parse_constant=_no_nan)


def test_page_embeds_every_run_and_event_as_strict_json(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    before = _listing(tmp_path / "results")
    out = replay.write_replay_page(run_dir, None, tmp_path / "page.html")
    assert _listing(tmp_path / "results") == before  # read only
    page = out.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in page
    assert page.isascii()  # non-ASCII text travels as escapes: no mojibake from disk
    data = _embedded(page)
    runs = {r["key"]: r for r in data["runs"]}
    assert list(runs) == list(RUNS)  # default: baseline plus up to three variants
    for name, run in runs.items():
        assist = name != "pad"
        assert [e["name"] for e in run["events"]] == [n for n, _ in _events(assist)]
        assert run["events"][0]["t"] == pytest.approx(-PUSH_S)
        assert len(run["t"]) == len(run["alt_m"]) == len(run["phase"]) == len(run["q_kpa"])
        assert run["t"][0] == pytest.approx(-PUSH_S) and run["t"][-1] == pytest.approx(T_END_S)
        assert run["losses_mps"]["drag_loss_mps"] is None  # NaN in metrics.json -> null
    assert runs["silo_step"]["losses_mps"]["steering_loss_mps"] is None  # Infinity -> null
    silo = runs["silo"]
    shaft = [q for t, q in zip(silo["t"], silo["q_kpa"], strict=True) if t < 0.0]
    assert shaft and all(q is None for q in shaft)  # vented shaft: no q
    assert all(q is not None for t, q in zip(silo["t"], silo["q_kpa"], strict=True) if t > 0.6)
    assert silo["alt_m"][0] == pytest.approx(-DEPTH_M)
    assert silo["payload_delta_kg"] == pytest.approx(100.0)
    assert runs["silo_step"]["dashed"] and not silo["dashed"] and runs["pad"]["baseline"]
    assert [r["color"] for r in data["runs"]] == [0, 1, 2]
    assert data["meta"]["floors"] == [
        {"depth_m": DEPTH_M, "label": "silo floor, 50 m down", "vertical": True}
    ]
    assert runs["pad"]["inserted"] and runs["silo"]["screening_yardstick_kg"] == 52.0
    assert runs["pad"]["screening_yardstick_kg"] is None  # the baseline is not compared
    assert "pitch_deg" not in silo  # not shown, so not embedded
    meta = data["meta"]
    assert meta["downrange_note"] == (
        "Downrange is the ground arc from the launch site over the rotating Earth."
    )
    assert any("screening yardstick" in n for n in meta["results_notes"])


def test_runs_selection_and_text_come_from_the_data(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    data = replay.replay_data(run_dir, ["silo", "pad"])
    assert [r["key"] for r in data["runs"]] == ["silo", "pad"]
    meta = data["meta"]
    assert "200 km circular orbit" in meta["subtitle"] and EXPERIMENT in meta["subtitle"]
    assert any("50 m below ground" in n and "50.0 m/s" in n for n in meta["closeup_notes"])
    text = " ".join(meta["caveats"])
    assert "toy_2d has no calibration record" in text
    assert "4.0 g" in text and "prescribed 3 g push" in text
    assert "instantly" not in text  # no step-ignition run selected
    detail = data["runs"][0]["detail"]
    assert "vertical silo 50 m deep" in detail and "T+0.5 s" in detail
    assert "carriage" not in detail and "impingement" not in detail  # massless, clear


def test_calibration_caveat_is_conditional_on_the_vehicle() -> None:
    gate = replay.calibration_caveat("generic_f9_class_2d")
    assert "+14.3% high" in gate and "documented miss" in gate
    assert "no calibration record" in replay.calibration_caveat("some_other_vehicle")


def test_embedded_json_cannot_close_its_script_and_rejects_nan() -> None:
    for value in ("</script><b>", "<!--<script>"):
        text = replay.embed_json({"s": value})
        assert "<" not in text and json.loads(text) == {"s": value}
    with pytest.raises(ValueError):
        replay.embed_json({"x": math.nan})


def test_template_ships_as_package_data() -> None:
    template = replay.load_template()
    assert template.count(replay.REPLAY_DATA_TOKEN) == 1
    assert template.isascii()


def test_default_output_is_outside_the_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _make_run_dir(tmp_path)
    name = f"{EXPERIMENT}_{TIMESTAMP}_replay.html"
    elsewhere = tmp_path / "work"
    elsewhere.mkdir()
    assert replay.default_replay_path(run_dir, elsewhere) == elsewhere / name
    before = _listing(tmp_path / "results")
    monkeypatch.chdir(run_dir)
    code = main(["replay", str(run_dir)])
    out = capsys.readouterr().out
    assert code == 0, out
    out.encode("ascii")
    assert (tmp_path / name).is_file()  # next to the results tree, never inside it
    assert "replay:" in out
    assert _listing(tmp_path / "results") == before


def test_output_inside_results_or_not_html_is_refused(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    with pytest.raises(replay.ReplayError, match="results tree"):
        replay.write_replay_page(run_dir, None, run_dir / "page.html")
    with pytest.raises(replay.ReplayError, match=r"\.html"):
        replay.write_replay_page(run_dir, None, tmp_path / "page.txt")
    assert not (run_dir / "page.html").exists()


def test_vertical_1d_run_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = _make_run_dir(tmp_path, model=None)  # a vertical_1d metrics.json has no model
    code = main(["replay", str(run_dir), "--out", str(tmp_path / "page.html")])
    out = capsys.readouterr().out
    assert code == 1
    assert "error:" in out and "vertical_1d" in out and "Traceback" not in out
    assert not (tmp_path / "page.html").exists()


def test_unknown_run_and_missing_dir_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _make_run_dir(tmp_path)
    code = main(
        ["replay", str(run_dir), "--runs", "pad", "nope", "--out", str(tmp_path / "p.html")]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "unknown run(s) nope" in out and "available: pad, silo, silo_step" in out
    code = main(["replay", str(tmp_path / "missing"), "--out", str(tmp_path / "p.html")])
    assert code == 1 and "run directory not found" in capsys.readouterr().out
    assert not (tmp_path / "p.html").exists()


def test_bound_runs_and_cases_use_their_own_metrics_and_config(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    names = ["pad", "silo__aero_bound", "pad__aero_bound", "alt_low"]
    data = replay.replay_data(run_dir, names)
    runs = {r["key"]: r for r in data["runs"]}
    bound = runs["silo__aero_bound"]
    assert bound["role"] == replay.ROLE_BOUND and bound["assisted"] and bound["vertical"]
    assert bound["status"] == "inserted" and bound["payload_kg"] == pytest.approx(1090.0)
    assert bound["compared_to"] == "pad__aero_bound"
    assert bound["payload_delta_kg"] == pytest.approx(90.0)
    assert bound["ideal_screening_kg"] == pytest.approx(55.0)
    override = "(with vehicle.aero.reference_area_m2 = 21.24)"
    assert f"aero_bound re-run of silo {override}" in bound["detail"]
    assert bound["pre_label"].startswith("Waiting at the bottom of the shaft")
    paired = runs["pad__aero_bound"]
    assert paired["label"] == "pad__aero_bound (paired baseline)"
    assert paired["payload_kg"] == pytest.approx(990.0) and paired["payload_delta_kg"] is None
    case = runs["alt_low"]
    assert case["label"] == "alt_low (case)" and case["status"] == "inserted"
    assert case["payload_kg"] == pytest.approx(1050.0) and case["compared_to"] is None
    assert "150 km circular orbit" in case["detail"] and "non-rotating Earth" in case["detail"]
    assert case["end_label"] == "In orbit, 150 km circular"
    assert runs["pad"]["end_label"] == "In orbit, 200 km circular"
    meta = data["meta"]
    assert "another orbit for alt_low" in meta["subtitle"]
    assert "the toy_2d vehicle (another vehicle for alt_low)" in meta["subtitle"]
    assert "vehicle toy_2d_light" in case["detail"]
    assert meta["downrange_note"].endswith("rotating Earth (the non-rotating Earth for alt_low).")
    text = " ".join(meta["caveats"])
    assert "silo__aero_bound with pad__aero_bound" in text
    assert "alt_low is a case" in text and "non-rotating Earth for alt_low" in text
    assert "did not reach orbit" not in text
    assert any("unless the row names another run" in n for n in meta["results_notes"])


def test_run_folder_unknown_to_metrics_is_refused(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    shutil.copytree(run_dir / "pad", run_dir / "stray")
    with pytest.raises(replay.ReplayError, match="describes it nowhere"):
        replay.replay_data(run_dir, ["pad", "stray"])


def test_failed_run_has_no_comparison_or_losses(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    path = run_dir / "metrics.json"
    metrics = json.loads(path.read_text(encoding="utf-8"))
    metrics["runs"]["silo"]["status"] = "impact"
    path.write_text(json.dumps(metrics), encoding="utf-8")
    data = replay.replay_data(run_dir, ["pad", "silo"])
    silo = data["runs"][1]
    assert silo["payload_delta_kg"] is None and silo["ideal_screening_kg"] is None
    assert all(v is None for v in silo["losses_mps"].values())
    assert silo["end_label"] == "Ended: impact"
    assert any("silo did not reach orbit (status impact)" in c for c in data["meta"]["caveats"])


def test_replay_grid_steps_and_interpolated_values(tmp_path: Path) -> None:
    grid = replay.replay_grid(-2.6073, 60.0)
    assert grid[0] == pytest.approx(-2.6073) and grid[1] == pytest.approx(-2.6)
    steps = np.diff(grid[1:-1])
    early = grid[1:-1][:-1] < replay.REPLAY_EARLY_END_S
    assert np.allclose(steps[early], replay.REPLAY_EARLY_DT_S)
    assert np.allclose(steps[~early], replay.REPLAY_LATE_DT_S)
    assert replay.REPLAY_EARLY_END_S in grid and grid[-1] == pytest.approx(60.0)
    run_dir = _make_run_dir(tmp_path)
    silo = {r["key"]: r for r in replay.replay_data(run_dir, ["silo"])["runs"]}["silo"]
    k = silo["t"].index(10.3)  # between the 0.5 s source rows at 10.0 and 10.5
    lo, hi = _row(10.0, 0.0, True), _row(10.5, 0.0, True)
    expected = lo["alt_m"] + 0.6 * (hi["alt_m"] - lo["alt_m"])
    assert silo["alt_m"][k] == pytest.approx(expected, abs=0.05)
    assert silo["v"][k] == pytest.approx(50.0 + 20.0 * 10.3, abs=0.005)


def test_flight_path_angle_is_wrapped_and_negative_zero_is_zero() -> None:
    # A fall-back run records gamma 1.590 rad rising, then 4.673 rad (268 deg) falling.
    assert replay.wrapped_deg(np.array([1.590, 4.673])) == pytest.approx(
        [91.1003, -92.2568], abs=1e-3
    )
    fields = {f: convert for f, _, convert, _ in replay.SERIES_FIELDS}
    assert fields["gamma_deg"] is replay.wrapped_deg
    zero = replay._finite(-0.0, 1)
    assert zero == 0.0 and math.copysign(1.0, zero) == 1.0


def test_caveats_name_each_runs_own_slope_and_upper_bound_reasons(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    text = " ".join(replay.replay_data(run_dir, None)["meta"]["caveats"])
    # -0.2 kg of payload per kg of dry mass: 200 kg/t; a 100 kg gain breaks even at 0.5 t.
    assert "0.5 t for silo and 0.5 t for silo_step (silo's \u00b110% dry-mass cases" in text
    assert "200 kg of payload per tonne" in text
    assert "applied to silo_step, which has no such cases of its own" in text
    assert "rough guide" not in text  # the slope rests on the payloads, not on screening
    assert "silo_step (q-alpha above the baseline) is an upper bound" in text


def test_detail_names_carriage_mass_and_exhaust_impingement(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    runs = {r["key"]: r for r in replay.replay_data(run_dir, ["pad", "silo_step"])["runs"]}
    detail = runs["silo_step"]["detail"]
    assert "5 t carriage" in detail and "exhaust impingement fraction 1" in detail
    assert runs["pad"]["detail"].startswith("pad start")


SILO_EXIT_SPEED_MPS = 50.0
"""The exit speed of the synthetic silo runs [m/s] (``_row``, ``_run_metrics``)."""


def _restate_push(
    run_dir: Path, name: str, *, metric_g: float | None, config: dict[str, float]
) -> None:
    """Rewrite run ``name`` of a synthetic directory: its metrics.json record gets the
    ``net_accel_g`` metric ``metric_g`` (None: no such key, as results written before
    the metric existed) and its resolved_config.yaml assist block states the push by
    ``config`` alone (``net_accel_g`` or ``exit_speed_mps``; {} for neither)."""
    path = run_dir / "metrics.json"
    metrics = json.loads(path.read_text(encoding="utf-8"))
    record = metrics["runs"][name]
    record.pop("net_accel_g", None)
    if metric_g is not None:
        record["net_accel_g"] = metric_g
    path.write_text(json.dumps(metrics), encoding="utf-8")
    path = run_dir / "resolved_config.yaml"
    resolved = yaml.safe_load(path.read_text(encoding="utf-8"))
    assist = resolved["runs"][name]["run"]["assist"]
    for key in ("net_accel_g", "exit_speed_mps"):
        assist.pop(key, None)
    assist.update(config)
    path.write_text(yaml.safe_dump(resolved), encoding="utf-8")


def test_push_label_of_a_run_defined_by_exit_speed_comes_from_the_metric(tmp_path: Path) -> None:
    """A run whose assist block states the push by ``exit_speed_mps`` (no ``net_accel_g``
    key in resolved_config.yaml) still gets its drive label and its caveat: both read
    the run's ``net_accel_g`` metric, here v^2 / (2 g0 L) for the synthetic silo (50 m/s
    over 50 m: 25 m/s^2, computed in the test). The metric wins over a config key that
    disagrees; results without the metric fall back to the config key (the fixture's
    3 g, as before the metric existed); with neither, the label names the model and the
    caveat drops the prescribed-push part."""
    run_dir = _make_run_dir(tmp_path)
    accel_g = SILO_EXIT_SPEED_MPS**2 / (2.0 * G0_MPS2 * DEPTH_M)
    label = f"{accel_g:g} g"
    assert label == "2.54929 g"  # hand number: 25 / 9.80665
    _restate_push(run_dir, "silo", metric_g=accel_g, config={"exit_speed_mps": SILO_EXIT_SPEED_MPS})
    data = replay.replay_data(run_dir, ["pad", "silo"])
    detail = data["runs"][1]["detail"]
    assert f"vertical silo 50 m deep, {label} net push" in detail and "exit 50.0 m/s" in detail
    text = " ".join(data["meta"]["caveats"])
    assert f"The drive is a prescribed {label} push with no force or power limit" in text
    assert "3 g" not in detail and "prescribed 3 g push" not in text
    # the metric first: a config key that disagrees does not win
    _restate_push(run_dir, "silo", metric_g=accel_g, config={"net_accel_g": 3.0})
    detail = replay.replay_data(run_dir, ["pad", "silo"])["runs"][1]["detail"]
    assert f"{label} net push" in detail and "3 g net push" not in detail
    # no metric (older results): the config key
    _restate_push(run_dir, "silo", metric_g=None, config={"net_accel_g": 3.0})
    data = replay.replay_data(run_dir, ["pad", "silo"])
    assert "3 g net push" in data["runs"][1]["detail"]
    assert "prescribed 3 g push" in " ".join(data["meta"]["caveats"])
    # neither: no acceleration to name
    _restate_push(run_dir, "silo", metric_g=None, config={"exit_speed_mps": SILO_EXIT_SPEED_MPS})
    data = replay.replay_data(run_dir, ["pad", "silo"])
    detail = data["runs"][1]["detail"]
    assert "constant_accel drive" in detail and "net push" not in detail
    text = " ".join(data["meta"]["caveats"])
    assert "push with no force or power limit" not in text
    assert "The carriage is massless" in text
    # the page of the exit-speed run renders (strict JSON, the label embedded)
    _restate_push(run_dir, "silo", metric_g=accel_g, config={"exit_speed_mps": SILO_EXIT_SPEED_MPS})
    page = replay.write_replay_page(run_dir, ["pad", "silo"], tmp_path / "page.html")
    embedded = _embedded(page.read_text(encoding="utf-8"))
    assert f"{label} net push" in embedded["runs"][1]["detail"]


def test_two_runs_with_different_push_accelerations_are_named_in_the_caveat(
    tmp_path: Path,
) -> None:
    """One run stated by exit speed (its metric) beside one stated by net_accel_g (its
    config key): the caveat names each prescribed push with its own run."""
    run_dir = _make_run_dir(tmp_path)
    accel_g = SILO_EXIT_SPEED_MPS**2 / (2.0 * G0_MPS2 * DEPTH_M)
    _restate_push(run_dir, "silo", metric_g=accel_g, config={"exit_speed_mps": SILO_EXIT_SPEED_MPS})
    text = " ".join(replay.replay_data(run_dir, None)["meta"]["caveats"])
    assert f"a prescribed {accel_g:g} g push with no force or power limit (silo)" in text
    assert "a prescribed 3 g push with no force or power limit (silo_step)" in text


def test_output_in_any_results_tree_is_refused(tmp_path: Path) -> None:
    # The run lies in one results tree; the repository's results/ is another.
    run_dir = _make_run_dir(tmp_path / "elsewhere")
    repo_results = tmp_path / "repo" / "Results" / "exp"
    repo_results.mkdir(parents=True)
    with pytest.raises(replay.ReplayError, match="results tree"):
        replay.write_replay_page(run_dir, None, repo_results / "page.html")
    assert not (repo_results / "page.html").exists()
    name = f"{EXPERIMENT}_{TIMESTAMP}_replay.html"
    # cwd inside the other tree: the default goes next to that tree, outside it.
    assert replay.default_replay_path(run_dir, repo_results) == tmp_path / "repo" / name
    nested = tmp_path / "repo" / "results" / "a" / "results" / "b"
    nested.mkdir(parents=True)
    assert replay.default_replay_path(run_dir, nested) == tmp_path / "repo" / name


def test_template_shows_every_run_and_the_flight_peak_g() -> None:
    template = replay.load_template()
    assert "const visible = new Set(runs.map(r => r.key));" in template
    assert "r.peak_g_flight" in template and "META.downrange_note" in template
    assert "Speed and path angle are relative to the Earth" in template
    assert "rotating Earth" not in template  # generated from the run data


def test_sweep_point_is_not_called_vertical(tmp_path: Path) -> None:
    point = tmp_path / "results" / EXPERIMENT / TIMESTAMP / "baseline"
    point.mkdir(parents=True)
    (point / "metrics.json").write_text(
        json.dumps({"experiment": EXPERIMENT, "run": {}, "metrics": {}}), encoding="utf-8"
    )
    with pytest.raises(replay.ReplayError, match="not an experiment results directory") as err:
        replay.replay_data(point, None)
    assert "vertical_1d" not in str(err.value)


@pytest.mark.parametrize(
    ("runs", "message"),
    [
        (["pad", "silo", "silo_step", "alt_low", "pad__aero_bound"], "at most 4"),
        (["pad", "pad"], "a run is named twice"),
    ],
)
def test_too_many_or_repeated_runs_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], runs: list[str], message: str
) -> None:
    run_dir = _make_run_dir(tmp_path)
    out_path = tmp_path / "p.html"
    code = main(["replay", str(run_dir), "--runs", *runs, "--out", str(out_path)])
    out = capsys.readouterr().out
    assert code == 1 and message in out and "Traceback" not in out
    assert not out_path.exists()


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node not installed: inline script syntax not checked")
def test_inline_script_is_valid_javascript(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path)
    page = replay.write_replay_page(run_dir, None, tmp_path / "page.html").read_text(
        encoding="utf-8"
    )
    scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
    assert len(scripts) == 1
    js = tmp_path / "inline.js"
    js.write_text(scripts[0], encoding="utf-8")
    assert NODE is not None
    proc = subprocess.run(
        [NODE, "--check", str(js)], capture_output=True, text=True, timeout=60, check=False
    )
    assert proc.returncode == 0, proc.stderr
