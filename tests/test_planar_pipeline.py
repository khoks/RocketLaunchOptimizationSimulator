"""The planar_2d reporting pipeline (build step 24; docs/physics.md, "Screening-beat rule
(2-D)" and "Reporting definitions (planar)").

Fast: a fixed-guidance experiment (figure_of_merit none: gamma* 20 deg, delta solved for
it, the pad's LTG pair) with the pad, silo_cold and silo_failed of silo_screening_2d on
the gate fork, run end to end through ``sim.run_experiment`` into a temporary results
root: every PLANAR_REQUIRED_METRICS key filled (P* aside: a run without a search has
none), the summary rows, the fixed-guidance label (the sweep-optimized one in the slow
searched test), the screening line, the attribution closing, the energy-only
sensitivity cases reusing the nominal trajectory and attributed, the planar assumptions
(pinned; the track's actual g_eff and Coriolis neglected; the search-only and
fixed-guidance lines; the azimuth caveat) and none of them in a 1-D summary, a typed
guidance failure as a status. Also fast, at unit level on the same runs: the
screening-beat machinery (t_v0 and the time-shift estimate against an independent
quadrature, the M2/M3 ratio rule and M2's sign, M4 and its floor, M5 and the anchor,
per-run bug_suspect, the attribution check and not_checked, the stricter yardstick, the
gamma*-sensitivity ranges, the M2 stage-1 diagnostic, the M3 floor, the trajectory key,
the unconstrained-kick label and unwrap_rad). Slow: the same with a searched payload
figure of merit on a small grid (every PLANAR_REQUIRED_METRICS key non-null, the gamma*
neighbours), and bounds, calibration cases and a paired sweep with fixed guidance.
Expected values (g_eff, the energy ratio, the angle bounds) are computed here from
constants and the configs.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.integrate import quad

from launchsim import cli, compare, sim, summary
from launchsim.atmosphere import ATMOSPHERE_ASSUMPTIONS
from launchsim.config import ChecksConfig, ResolvedExperiment, resolve_experiment
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import PLANAR_STATE_NAMES
from launchsim.metrics_planar import PLANAR_REQUIRED_METRICS, missing_required, unwrap_rad
from launchsim.summary import PLANAR_VARIANT_ROWS
from launchsim.vehicle import payload_gain_kg, with_payload

FIXED_GAMMA_DEG = 20.0
"""The fixed gamma* of the fast experiment [deg]."""
FIXED_LTG = (0.756790, 2.19338e-3)
"""The pad's LTG pair at gamma* 20 deg and 22.8 t (docs/physics.md, step 22): the
fixed guidance of the fast experiment (silo_cold flies it off target, by design)."""
FAST_SAMPLE_DT_S = 0.5
"""Coarse time-series interval of the fast experiment [s] (shared by every run)."""
ATTRIBUTION_TOL_MPS = 1e-5
"""The plan's matched-payload attribution tolerance [m/s]."""
SITE_LAT_DEG = 28.5
"""The shipped site latitude [deg] (azimuth 90 deg)."""


def _raw(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """silo_screening_2d.yaml and the gate fork as raw dicts."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_2d.yaml").read_text(encoding="utf-8")
    )
    veh = yaml.safe_load(
        (repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text(
            encoding="utf-8"
        )
    )
    return exp, veh


def _fixed(exp: dict[str, Any], variants: tuple[str, ...]) -> dict[str, Any]:
    """The experiment with the fixed guidance, a coarse sample interval, only the named
    variants and no sweeps, sensitivity or bounds."""
    exp = copy.deepcopy(exp)
    exp["search"].update(
        {
            "figure_of_merit": "none",
            "fixed_gamma_star_deg": FIXED_GAMMA_DEG,
            "fixed_ltg_a": FIXED_LTG[0],
            "fixed_ltg_b_per_s": FIXED_LTG[1],
        }
    )
    exp["baseline"]["integrator"]["sample_dt_s"] = FAST_SAMPLE_DT_S
    exp["variants"] = {k: v for k, v in exp["variants"].items() if k in variants}
    for key in ("sweeps", "sensitivity", "bounds"):
        exp.pop(key, None)
    return exp


@pytest.fixture(scope="module")
def fast_run(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Path]:
    """The fixed-guidance experiment (pad, silo_cold, silo_failed) with two energy-only
    sensitivity cases of silo_cold, run and written (no plots)."""
    exp, veh = _raw(repo_root)
    exp = _fixed(exp, ("silo_cold", "silo_failed"))
    exp["sensitivity"] = {
        "of": ["silo_cold"],
        "params": {"assist.drive_efficiency": 0.1, "vehicle.screening.stage_isp_eff_s.0": 0.1},
    }
    resolved = resolve_experiment(exp, veh)
    root = tmp_path_factory.mktemp("planar_fast")
    return sim.run_experiment(resolved, root, plots=False, repo_root=repo_root)


def _g_eff_track() -> float:
    """mu/R_E^2 - omega_p^2 R_E at the shipped site (28.5 deg, azimuth 90)."""
    omega_p = OMEGA_EARTH_RADS * math.cos(math.radians(SITE_LAT_DEG))
    return MU_EARTH_M3S2 / R_EARTH_M**2 - omega_p**2 * R_EARTH_M


def test_fixed_guidance_runs_fill_every_required_metric_but_p_star(
    fast_run: tuple[Any, Path],
) -> None:
    """Every PLANAR_REQUIRED_METRICS key is non-null for the pad and silo_cold, except
    payload_kg (no search, no P*); the statuses are the planar ones, the per-run checks
    pass, and the search status names the fixed guidance or the skip."""
    er, _out = fast_run
    for name in ("pad", "silo_cold"):
        m = er.runs[name].result.metrics
        assert missing_required(m) == ["payload_kg"], name
        assert m["run_checks"] == "ok"
        assert m["search_status"] == sim.FIXED_GUIDANCE_STATUS
        assert m["gamma_star_rad"] == pytest.approx(math.radians(FIXED_GAMMA_DEG), rel=1e-15)
    assert er.runs["pad"].result.status == "inserted"
    assert er.runs["silo_cold"].result.status in ("inserted", "off_target")
    failed = er.runs["silo_failed"].result
    assert failed.status == "impact" and failed.model == "planar_2d"
    assert failed.metrics["search_status"].startswith(sim.SKIPPED_STATUS_PREFIX)
    assert failed.metrics["failed_stage"] == "stage1"


def test_files_and_columns(fast_run: tuple[Any, Path]) -> None:
    """metrics.json carries the model and the comparison; every run has a planar
    timeseries.csv and events.csv with the planar columns; the silo_failed fall-back
    reports gamma_rel unwrapped (amendment 14): continuous (every step below pi) and
    past pi after the apex, where the raw atan2 would wrap to -pi."""
    er, out = fast_run
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["model"] == "planar_2d" and set(metrics["runs"]) == set(er.runs)
    assert "silo_cold" in metrics["comparison"]
    for name in er.runs:
        ts = pd.read_csv(out / name / "timeseries.csv")
        ev = pd.read_csv(out / name / "events.csv")
        assert list(ts.columns) == list(sim.PLANAR_TIMESERIES_COLUMNS)
        assert list(ev.columns) == list(sim.PLANAR_EVENT_COLUMNS)
    frame = er.runs["silo_failed"].result.timeseries
    for column in ("gamma_rel_rad", "pitch_rad"):
        angle = frame[column].to_numpy()
        assert np.max(np.abs(np.diff(angle))) < math.pi, column
        assert angle.max() > math.pi, column


def test_summary_rows_label_and_screening_line(fast_run: tuple[Any, Path]) -> None:
    """summary.md has every PLANAR_VARIANT_ROWS label, the fixed-guidance comparison
    basis and label (no run searched, so not the sweep-optimized ones, and none of the
    search-only assumption lines), the screening line of every variant (dP* against the
    yardstick, the matched-payload attribution with its gamma* caveat, the checks, the
    screening status) and the blocked-findings line or its absence; every
    PLANAR_REQUIRED_METRICS key is a row."""
    er, out = fast_run
    text = (out / "summary.md").read_text(encoding="utf-8")
    keys = {key for _label, _source, key in PLANAR_VARIANT_ROWS}
    assert set(PLANAR_REQUIRED_METRICS) <= keys
    for label, _source, _key in PLANAR_VARIANT_ROWS:
        assert f"| {label} |" in text, label
    assert sim.PLANAR_FIXED_COMPARISON_BASIS in text and sim.FIXED_GUIDANCE_LABEL in text
    assert sim.PLANAR_COMPARISON_BASIS not in text and sim.SWEEP_OPTIMIZED_LABEL not in text
    assert not [a for a in sim.SEARCH_ASSUMPTIONS if a in text]
    assert summary.SPLIT_CAVEAT in text
    for name in ("silo_cold", "silo_failed"):
        line = next(ln for ln in text.splitlines() if ln.startswith(f"- {name}: dP* "))
        assert "ideal screening yardstick" in line and "Screening status:" in line
        assert "Checks: closure" in line
    silo = next(ln for ln in text.splitlines() if ln.startswith("- silo_cold: dP* "))
    assert "matched-payload attribution at P_ref" in silo
    status = er.comparison["silo_cold"]["screening_status"]
    assert (sim.FINDINGS_BLOCKED in text) == (status == sim.BUG_SUSPECT)
    assert "CALIBRATION" not in text


def test_attribution_closes_at_the_matched_payload(fast_run: tuple[Any, Path]) -> None:
    """With fixed guidance the matched payload is P0 and the matched runs are the
    recorded ones: d dv_margin equals the sum of its terms within the plan's 1e-5 m/s,
    and the release-speed term is silo_cold's release speed (the pad starts at rest)."""
    er, _out = fast_run
    c = er.comparison["silo_cold"]
    assert c["attr_payload_kg"] == er.baseline.resolved.to_vehicle().payload_mass_kg
    assert abs(c["attr_residual_mps"]) < ATTRIBUTION_TOL_MPS
    v0 = er.runs["silo_cold"].result.metrics["speed_at_release_mps"]
    assert c["attr_release_speed_mps"] == pytest.approx(v0, rel=1e-12)
    assert c["checks_closure"]["status"] == "pass"
    assert er.comparison["silo_failed"]["attr_d_dv_margin_mps"] is None


def test_energy_only_sensitivity_reuses_the_trajectory(fast_run: tuple[Any, Path]) -> None:
    """The drive-efficiency and screening-Isp cases fly nothing: each reuses silo_cold's
    trajectory (the same time series object, trajectory_reused), and the electrical
    energy scales as 1/efficiency: E_case = E_nominal x 0.5/(0.5 (1 +/- 0.1)); the
    screening cases leave it unchanged; none has a perturbed baseline to fly
    (assist.* leaves the pad alone; the screening case's pad is reused too). Every case
    is attributed against the baseline of its own vehicle (the screening-beat rule
    applies to sensitivity cases too); a screening case against the unchanged baseline
    (two vehicles) is not_checked."""
    er, _out = fast_run
    nominal = er.runs["silo_cold"].result
    e_nom = nominal.metrics["electrical_energy_J"]
    assert len(er.sensitivity) == 4
    for row in er.sensitivity:
        m = row.result.result.metrics
        assert m["trajectory_reused"] is True
        assert row.result.result.timeseries is nominal.timeseries
        attributed = row.comparison_perturbed
        assert attributed["attr_residual_mps"] is not None
        assert abs(attributed["attr_residual_mps"]) < ATTRIBUTION_TOL_MPS
        assert attributed["screening_status"] != sim.SCREENING_NOT_CHECKED
        assert attributed["checks_attribution"]["status"] == "pass"
        if row.param == "assist.drive_efficiency":
            assert m["electrical_energy_J"] == pytest.approx(
                e_nom / (1.0 + row.fraction), rel=1e-12
            )
            assert row.baseline_perturbed is None
        else:
            assert m["electrical_energy_J"] == e_nom
            assert row.baseline_perturbed is not None
            assert row.baseline_perturbed.result.metrics["trajectory_reused"] is True
            assert row.comparison["screening_status"] == sim.SCREENING_NOT_CHECKED


def test_planar_assumptions_name_the_track_gravity(fast_run: tuple[Any, Path]) -> None:
    """silo_cold lists the constant_accel line with the actual g_eff_track = mu/R_E^2 -
    omega_p^2 R_E at 28.5 deg (9.7720917 m/s^2, computed here) and Coriolis neglected,
    every planar run carries the PLANAR_ASSUMPTIONS and ATMOSPHERE_ASSUMPTIONS, and the
    pad lists its hold-down convention."""
    er, _out = fast_run
    silo = er.runs["silo_cold"].result.assumptions
    line = next(a for a in silo if a.startswith("constant_accel: constant g_eff"))
    assert f"{_g_eff_track():.7g} m/s^2" in line and "Coriolis neglected" in line
    assert "omega_p = 0," not in line
    for rr in er.runs.values():
        assert set(sim.PLANAR_ASSUMPTIONS) <= set(rr.result.assumptions)
        assert set(ATMOSPHERE_ASSUMPTIONS) <= set(rr.result.assumptions)
    assert any(a.startswith("pad: held down") for a in er.runs["pad"].result.assumptions)
    for name in ("pad", "silo_cold"):
        lines = er.runs[name].result.assumptions
        assert set(sim.FIXED_GUIDANCE_ASSUMPTIONS) <= set(lines)
        assert not set(sim.SEARCH_ASSUMPTIONS) & set(lines)
    failed = set(er.runs["silo_failed"].result.assumptions)
    assert not (set(sim.SEARCH_ASSUMPTIONS) | set(sim.FIXED_GUIDANCE_ASSUMPTIONS)) & failed


PINNED_ASSUMPTIONS: tuple[str, ...] = (
    "out-of-plane velocity",
    "spherical Earth",
    "mu/r^2",
    "co-rotates with Earth and has no wind",
    "no lift",
    "one A_ref for the whole flight",
    "also used in unlit coasts",
    "no throttling",
    "no flight-performance reserve, no unusable residuals",
    "the fairing is jettisoned instantly",
    "cuts off instantly",
    "no Coriolis and no air drag in the vented shaft",
    "constant ambient pressure of the exit",
    "unwrapped per run",
)
"""Distinctive substrings of the plan's PLANAR_ASSUMPTIONS list (plan section 5 and
amendment 14) that every planar run must state."""
PINNED_SEARCH_ASSUMPTIONS: tuple[str, ...] = (
    "virtual stage-2 propellant",
    '"sweep-optimized" guidance',
)
"""The search-only items of the plan's list (virtual propellant; sweep-optimized)."""


def test_planar_assumptions_are_pinned(fast_run: tuple[Any, Path]) -> None:
    """Plan section 5 ("a test pins them") and amendment 14: every item of the planar
    assumption list appears in a planar run's assumptions (silo_cold), the search-only
    items in SEARCH_ASSUMPTIONS, the stage-2 exit area and step startup and the pad's
    hold-down at t = 0 in the run lines."""
    er, _out = fast_run
    silo = " | ".join(er.runs["silo_cold"].result.assumptions)
    for item in PINNED_ASSUMPTIONS:
        assert item in silo, item
    search = " | ".join(sim.SEARCH_ASSUMPTIONS)
    for item in PINNED_SEARCH_ASSUMPTIONS:
        assert item in search, item
    assert "at full thrust (step startup)" in silo and "exit area" in silo
    pad = " | ".join(er.runs["pad"].result.assumptions)
    assert "held down to the release at t = 0 s" in pad


def test_azimuth_away_from_east_is_a_flag_and_an_assumption(fast_run: tuple[Any, Path]) -> None:
    """Amendment 13: azimuth 90 deg raises nothing; 80 deg raises the planar-azimuth flag
    and adds PLANAR_AZIMUTH_ASSUMPTION to the run's assumption lines."""
    er, _out = fast_run
    rr = er.runs["pad"]
    vehicle = rr.resolved.to_vehicle()
    run = rr.resolved.run
    assert sim._run_flags(run) == []
    setup = sim.planar_setup(run, vehicle)
    assert sim.PLANAR_AZIMUTH_ASSUMPTION not in sim.planar_run_assumptions(run, vehicle, setup)
    tilted = run.model_copy(update={"site": run.site.model_copy(update={"azimuth_deg": 80.0})})
    flags = sim._run_flags(tilted)
    assert len(flags) == 1 and flags[0].startswith("planar azimuth: 80 deg")
    lines = sim.planar_run_assumptions(tilted, vehicle, sim.planar_setup(tilted, vehicle))
    assert sim.PLANAR_AZIMUTH_ASSUMPTION in lines


def test_one_d_summaries_carry_no_planar_assumption(repo_root: Path) -> None:
    """The pinned 1-D summaries (the golden, byte-identical to the pipeline's 1-D
    output) and a fresh 1-D silo run carry none of the planar or atmosphere assumption
    strings, and the 1-D constant_accel line keeps its Phase 1 text."""
    golden = repo_root / "tests" / "data" / "golden" / "silo_screening_1d" / "experiment"
    text = (golden / "summary.md").read_text(encoding="utf-8")
    planar = [*sim.PLANAR_ASSUMPTIONS, *ATMOSPHERE_ASSUMPTIONS]
    assert not [a for a in planar if a in text]
    assert "omega_p = 0, Coriolis neglected" in text
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_1d.yaml").read_text(encoding="utf-8")
    )
    veh = yaml.safe_load(
        (repo_root / "configs" / "vehicles" / "generic_f9_class.yaml").read_text(encoding="utf-8")
    )
    resolved: ResolvedExperiment = resolve_experiment(exp, veh)
    rr = sim.run_resolved(resolved.variants["silo_cold"])
    assert rr.result.model == "vertical_1d" and rr.result.search is None
    assert not [a for a in planar if a in rr.result.assumptions]


def test_cli_loads_every_shipped_planar_experiment(repo_root: Path) -> None:
    """cli.load_experiment resolves the four shipped planar experiments, the calibration
    cases' own vehicle files included (the loader), and checks every result name; a
    case named like a results directory is refused before anything runs; the console
    line of a planar run carries P*, gamma*_ref in degrees and max-Q."""
    names = ("calibration_f9_2d", "silo_screening_2d", "silo_bridge_2d_readme")
    for name in (*names, "guidance_trigger_2d"):
        resolved = cli.load_experiment(repo_root / "experiments" / f"{name}.yaml")
        assert resolved.baseline.run.dynamics == "planar_2d"
    cal = cli.load_experiment(repo_root / "experiments" / "calibration_f9_2d.yaml")
    assert cal.cases["readme_loads"].vehicle.name != cal.baseline.vehicle.name
    exp, veh = _raw(repo_root)
    bad = _fixed(exp, ())
    bad["label"] = "calibration"
    bad["cases"] = {"baseline": {"site": {"include_rotation": False}}}
    with pytest.raises(sim.InvalidNameError):
        sim.check_result_names(resolve_experiment(bad, veh))


def test_console_line_of_a_planar_run(fast_run: tuple[Any, Path]) -> None:
    """The CLI headline of a planar run: status, P* (n/a without a search), gamma*_ref
    in degrees and max-Q; a 1-D run keeps its Phase 1 line."""
    er, _out = fast_run
    line = cli.run_line("pad", er.baseline.result, True)
    assert line.startswith("  pad (baseline): inserted (P* n/a kg, gamma* 20 deg, max-Q ")
    assert line.isascii()


# ------------------------------------------- screening-beat machinery (unit level)

BEAT_MARGIN_KG = 5000.0
"""A dP* far above any ideal yardstick at 77 m/s (about 0.8 t): an injected beat [kg]."""
P_BASE_TEST_KG = 25000.0
"""An injected baseline P* [kg] for the fixed-guidance runs (which have none)."""


def _with_metrics(result: Any, **items: Any) -> Any:
    """A copy of a Result with some metrics replaced."""
    return dataclasses.replace(result, metrics={**result.metrics, **items})


def _checks(er: Any) -> ChecksConfig:
    """The experiment's shared ChecksConfig."""
    return er.baseline.resolved.run.planar.checks


def _site_omega_p() -> float:
    """omega_E cos(lat) sin(az) at the shipped site (az 90 deg) [rad/s]."""
    return OMEGA_EARTH_RADS * math.cos(math.radians(SITE_LAT_DEG))


def _dense_state(trace: Any, t: float) -> np.ndarray:
    """The planar state at t [s] from the dense output of the ascent phase spanning t
    (the end state at a phase end)."""
    for res in trace.ascent_phases():
        if res.spec.t0 <= t <= res.t_end:
            if t == res.t_end or res.dense is None:
                return np.asarray(res.y_end, dtype=float)
            return np.asarray(res.dense(t), dtype=float)
    raise AssertionError(f"no ascent phase spans t = {t}")


def test_time_to_speed_and_the_time_shift_estimate_by_independent_quadrature(
    fast_run: tuple[Any, Path],
) -> None:
    """On the recorded pad: t_v0 is the first instant |v_rel| = hypot(v_r, v_theta -
    omega_p r) reaches silo_cold's release speed (every earlier dense sample is below
    it); the estimate equals [G(t_MECO) - G(t_MECO - t_v0)] - [G(t_fs + t_v0) - G(t_fs)]
    with G the integral of (mu/r^2 - omega_p^2 r) v_r/|v_rel|, computed here by quad
    phase by phase; t_v0 is 0 for a speed the run starts at and None for one it never
    reaches."""
    er, _out = fast_run
    trace = er.baseline.result.trace
    omega_p = _site_omega_p()
    assert trace.view.omega_p_rads == pytest.approx(omega_p, rel=1e-15)
    v0 = er.runs["silo_cold"].result.metrics["speed_at_release_mps"]
    t_fs = trace.t_flight_start_s
    t_v0 = compare.time_to_speed_s(trace, v0, omega_p, R_EARTH_M)

    def speed(y: np.ndarray) -> float:
        return math.hypot(y[2], y[3] - omega_p * y[0])

    assert speed(_dense_state(trace, t_fs + t_v0)) == pytest.approx(v0, rel=1e-9)
    before = np.linspace(t_fs, t_fs + t_v0, 400)[:-1]
    assert max(speed(_dense_state(trace, float(t))) for t in before) < v0

    def g_sin_gamma(t: float) -> float:
        r, _th, w, v_th = _dense_state(trace, t)[:4]
        big_v = math.hypot(w, v_th - omega_p * r)
        sin_g = 1.0 if big_v == 0.0 else w / big_v
        return (MU_EARTH_M3S2 / r**2 - omega_p**2 * r) * sin_g

    def integral(a: float, b: float) -> float:
        total = 0.0
        for res in trace.ascent_phases():
            lo, hi = max(a, res.spec.t0), min(b, res.t_end)
            if hi > lo:
                total += quad(g_sin_gamma, lo, hi, epsabs=1e-11, epsrel=1e-12, limit=200)[0]
        return total

    t_meco = min(t for t, _y in trace.burnouts.values())
    expected = integral(t_meco - t_v0, t_meco) - integral(t_fs, t_fs + t_v0)
    got = compare.time_shift_estimate_mps(trace, t_v0, "J_grav_mps")
    assert got == pytest.approx(expected, rel=1e-7)
    assert got < 0.0  # the shifted time is flown shallower than the removed time
    assert compare.time_shift_estimate_mps(trace, 0.0, "J_grav_mps") == 0.0
    assert compare.time_to_speed_s(trace, 0.0, omega_p, R_EARTH_M) == 0.0
    assert compare.time_to_speed_s(trace, 1.0e9, omega_p, R_EARTH_M) is None


def test_ratio_check_signs_and_bounds() -> None:
    """M2/M3: pass for d/est inside the bounds; fail for the opposite sign, below and
    above them; an estimate of 0 passes only a d of 0."""
    bounds = (0.33, 3.0)
    assert compare._ratio_check(-40.0, -100.0, bounds) == ("pass", pytest.approx(0.4))
    assert compare._ratio_check(40.0, -100.0, bounds)[0] == "fail"
    assert compare._ratio_check(-10.0, -100.0, bounds)[0] == "fail"
    assert compare._ratio_check(-400.0, -100.0, bounds)[0] == "fail"
    assert compare._ratio_check(-33.0, -100.0, bounds)[0] == "pass"
    assert compare._ratio_check(1.0, 0.0, bounds) == ("fail", None)
    assert compare._ratio_check(0.0, 0.0, bounds) == ("pass", None)


def test_m4_share_and_its_floor() -> None:
    """M4: drag + steering as contributions in the variant's favour pass at up to
    max_drag_steer_share of the gain beyond the release speed and fail above; n/a
    without an attribution and when that gain is below min_term_mps."""
    checks = ChecksConfig()
    share = checks.max_drag_steer_share

    def attr(beyond: float, drag: float, steer: float) -> dict[str, float]:
        return {
            "attr_beyond_release_mps": beyond,
            "attr_drag_mps": drag,
            "attr_steering_mps": steer,
        }

    ok = compare._m4(attr(10.0, 0.4 * 10.0 * share, 0.5 * 10.0 * share), checks)
    assert ok["status"] == "pass" and ok["share"] == pytest.approx(0.9 * share)
    bad = compare._m4(attr(10.0, 0.6 * 10.0 * share, 0.5 * 10.0 * share), checks)
    assert bad["status"] == "fail"
    floor = checks.min_term_mps
    assert compare._m4(attr(0.9 * floor, 0.9 * floor, 0.0), checks)["status"] == "n/a"
    assert compare._m4(None, checks)["status"] == "n/a"


def test_m5_bound_direction_and_the_anchor(fast_run: tuple[Any, Path]) -> None:
    """M5: a named variant released at the anchor's speed passes at dP* <= anchor dP* +
    the pad pre-flight term in kg + anchor_margin_kg and fails above; n/a for the anchor
    runs, for other release speeds and without an anchor. anchor_from takes dP* of
    silo_instant against pad_instant, the baseline's pre-flight term on the vehicle at
    the baseline's P* and silo_instant's release speed; None without the pair."""
    checks = ChecksConfig()
    v0 = 76.7
    anchor = compare.Anchor(d_payload_kg=1000.0, pad_preflight_kg=140.0, release_speed_mps=v0)
    bound = 1000.0 + 140.0 + checks.anchor_margin_kg
    run = SimpleNamespace(metrics={"speed_at_release_mps": v0})
    assert compare._m5("silo_cold", run, bound - 0.01, anchor, checks)["status"] == "pass"
    failed = compare._m5("silo_cold", run, bound + 0.01, anchor, checks)
    assert failed["status"] == "fail" and failed["bound_kg"] == pytest.approx(bound)
    assert compare._m5("silo_instant", run, bound + 1.0, anchor, checks)["status"] == "n/a"
    other = SimpleNamespace(metrics={"speed_at_release_mps": v0 + 1e-3})
    assert compare._m5("silo_cold", other, bound + 1.0, anchor, checks)["status"] == "n/a"
    assert compare._m5("silo_cold", run, bound + 1.0, None, checks)["status"] == "n/a"

    er, _out = fast_run
    vehicle = er.baseline.resolved.to_vehicle()
    base = SimpleNamespace(metrics={"preflight_dv_mps": 20.0, "payload_kg": P_BASE_TEST_KG})
    runs = {
        "silo_instant": SimpleNamespace(
            metrics={"payload_kg": P_BASE_TEST_KG + 1700.0, "speed_at_release_mps": v0}
        ),
        "pad_instant": SimpleNamespace(metrics={"payload_kg": P_BASE_TEST_KG + 200.0}),
    }
    got = compare.anchor_from(runs, base, vehicle)
    assert got is not None
    assert got.d_payload_kg == pytest.approx(1500.0, abs=1e-9)
    assert got.release_speed_mps == v0
    at_p_base = with_payload(vehicle, P_BASE_TEST_KG)
    assert got.pad_preflight_kg == compare.payload_equiv_kg(at_p_base, 20.0)
    assert got.pad_preflight_kg > 0.0
    assert compare.anchor_from({"silo_instant": runs["silo_instant"]}, base, vehicle) is None


def test_per_run_check_failure_sets_bug_suspect(fast_run: tuple[Any, Path]) -> None:
    """simulate_planar with the closure, identity and eccentricity tolerances far below
    the pad's residuals: status bug_suspect, the trajectory's status kept in
    trace_status, run_checks bug_suspect with the three reasons, and a bug_suspect
    flag per failure; with the shipped tolerances the same trace is inserted and ok."""
    er, _out = fast_run
    rr = er.baseline
    vehicle = rr.resolved.to_vehicle()
    setup = sim.planar_setup(rr.resolved.run, vehicle)
    tiny = {"closure_tol_mps": 1e-15, "identity_tol_mps": 1e-15, "insertion_e_max": 1e-15}
    strict = dataclasses.replace(setup, checks=setup.checks.model_copy(update=tiny))
    trace = rr.result.trace
    result = sim.simulate_planar(trace, vehicle, strict, sample_dt_s=10.0, figure_items={})
    assert result.status == sim.BUG_SUSPECT
    assert result.metrics["trace_status"] == "inserted"
    assert result.metrics["run_checks"] == sim.BUG_SUSPECT
    reasons = result.metrics["run_checks_failed"]
    for what in ("closure residual", "loss-identity residual", "insertion e"):
        assert what in reasons
    assert sum(f.startswith(f"{sim.BUG_SUSPECT}: ") for f in result.flags) == 3
    nominal = sim.simulate_planar(trace, vehicle, setup, sample_dt_s=10.0, figure_items={})
    assert nominal.status == "inserted" and nominal.metrics["run_checks"] == "ok"


def test_unexplained_beat_is_bug_suspect_and_unattributed_rows_are_not_checked(
    fast_run: tuple[Any, Path],
) -> None:
    """With an injected baseline P* and a silo_cold P* far above the yardstick: no
    attribution -> the attribution check fails (bug_suspect) when one is required and
    the status is not_checked when it is not (sensitivity rows, bounds); a variant
    below the yardstick without an attribution is not_checked; a variant without a
    stage-2 burn gets closure n/a, not the baseline's pass."""
    er, _out = fast_run
    checks = _checks(er)
    pad = _with_metrics(er.baseline.result, payload_kg=P_BASE_TEST_KG)
    silo = er.runs["silo_cold"].result
    vehicle = er.runs["silo_cold"].resolved.to_vehicle()
    beat = _with_metrics(silo, payload_kg=P_BASE_TEST_KG + BEAT_MARGIN_KG)
    c = compare.compare_planar(beat, pad, vehicle, checks=checks, name="silo_cold")
    assert c["beats_screening"] is True
    assert c["checks_attribution"]["status"] == "fail"
    assert "attribution" in c["screening_failed"]
    assert c["screening_status"] == sim.BUG_SUSPECT
    free = compare.compare_planar(
        beat, pad, vehicle, checks=checks, name="silo_cold", attribution_required=False
    )
    assert free["checks_attribution"]["status"] == "n/a"
    assert free["screening_status"] == sim.SCREENING_NOT_CHECKED
    low = _with_metrics(silo, payload_kg=P_BASE_TEST_KG + 1.0)
    c_low = compare.compare_planar(low, pad, vehicle, checks=checks, name="silo_cold")
    assert c_low["beats_screening"] is False
    assert c_low["screening_status"] == sim.SCREENING_NOT_CHECKED
    failed = er.comparison["silo_failed"]
    assert failed["checks_closure"]["status"] == "n/a"
    assert failed["checks_closure"]["baseline_residual_mps"] is not None
    assert failed["screening_status"] == sim.SCREENING_NOT_CHECKED


def test_attribution_check_fails_a_non_closing_attribution(fast_run: tuple[Any, Path]) -> None:
    """The recorded matched runs close (attribution pass, worst closure below the
    tolerance); a variant matched run given a vehicle 100 kg lighter than its trace
    flew breaks its closure, and the attribution check fails (bug_suspect)."""
    er, _out = fast_run
    checks = _checks(er)
    p0 = er.baseline.resolved.to_vehicle().payload_mass_kg
    pad, silo_rr = er.baseline, er.runs["silo_cold"]
    mb = sim.matched_run(pad.resolved, pad.result, p0)
    mv = sim.matched_run(silo_rr.resolved, silo_rr.result, p0)
    assert mb is not None and mv is not None
    vehicle = silo_rr.resolved.to_vehicle()
    kwargs = {"checks": checks, "name": "silo_cold", "matched_baseline": mb}
    good = compare.compare_planar(silo_rr.result, pad.result, vehicle, matched=mv, **kwargs)
    assert good["checks_attribution"]["status"] == "pass"
    assert good["checks_attribution"]["worst_closure_mps"] < checks.closure_tol_mps
    bad_mv = dataclasses.replace(mv, vehicle=with_payload(mv.vehicle, p0 - 100.0))
    bad = compare.compare_planar(silo_rr.result, pad.result, vehicle, matched=bad_mv, **kwargs)
    assert bad["checks_attribution"]["status"] == "fail"
    assert "attribution" in bad["screening_failed"]
    assert bad["screening_status"] == sim.BUG_SUSPECT


def test_m2_stage1_diagnostic_and_the_m3_floor(fast_run: tuple[Any, Path]) -> None:
    """The M2 record carries the stage-1 part of d J_grav: minus the difference of the
    two recorded runs' J_grav at their stage-1 burnouts (read here off the burnout
    states), with its ratio to the same estimate; M3 is n/a (d recorded) when |d J_bp|
    is at most min_term_mps and applies when the floor is 0."""
    er, _out = fast_run
    c = er.comparison["silo_cold"]
    j = PLANAR_STATE_NAMES.index("J_grav_mps")
    g_pad = er.baseline.result.trace.burnouts["stage1"][1][j]
    g_silo = er.runs["silo_cold"].result.trace.burnouts["stage1"][1][j]
    m2 = c["checks_m2"]
    end_pad = er.baseline.result.trace.ascent_phases()[-1].y_end[j]
    end_silo = er.runs["silo_cold"].result.trace.ascent_phases()[-1].y_end[j]
    assert m2["d_mps"] == pytest.approx(end_silo - end_pad, rel=1e-12)  # variant - baseline
    assert m2["ratio"] == pytest.approx(m2["d_mps"] / m2["estimate_mps"], rel=1e-12)
    assert m2["gamma_robust"] is None and m2["value_range"] is None  # fixed guidance
    assert m2["d_stage1_mps"] == pytest.approx(g_silo - g_pad, rel=1e-12)
    assert m2["ratio_stage1"] == pytest.approx(m2["d_stage1_mps"] / m2["estimate_mps"])
    assert c["attr_gravity_stage1_mps"] == pytest.approx(-(g_silo - g_pad), rel=1e-12)
    p0 = er.baseline.resolved.to_vehicle().payload_mass_kg
    silo_rr = er.runs["silo_cold"]
    mb = sim.matched_run(er.baseline.resolved, er.baseline.result, p0)
    mv = sim.matched_run(silo_rr.resolved, silo_rr.result, p0)
    vehicle = silo_rr.resolved.to_vehicle()
    d_bp = -c["attr_back_pressure_mps"]
    for floor, status_na in ((abs(d_bp) + 1.0, True), (0.0, False)):
        checks = _checks(er).model_copy(update={"min_term_mps": floor})
        out = compare.compare_planar(
            silo_rr.result,
            er.baseline.result,
            vehicle,
            checks=checks,
            name="silo_cold",
            matched=mv,
            matched_baseline=mb,
        )
        m3 = out["checks_m3"]
        assert (m3["status"] == "n/a") is status_na
        assert m3["d_mps"] == pytest.approx(d_bp, rel=1e-12)
        assert ("ratio" in m3) is not status_na


def test_beats_uses_the_stricter_yardstick(fast_run: tuple[Any, Path]) -> None:
    """beats_screening compares dP* with the smaller of the two ideal yardsticks at the
    release speed (the vehicle at P0 and at the baseline's P*), each written here with
    vehicle.payload_gain_kg: with P*_base above P0 the P0 one is used, so a dP* between
    the two beats; with P*_base below P0 the P*_base one is used."""
    er, _out = fast_run
    checks = _checks(er)
    silo = er.runs["silo_cold"].result
    vehicle = er.runs["silo_cold"].resolved.to_vehicle()
    v0 = silo.metrics["speed_at_release_mps"]
    for p_base, basis in ((P_BASE_TEST_KG, "P0"), (0.8 * vehicle.payload_mass_kg, "P*_base")):
        y0 = payload_gain_kg(vehicle, v0)
        yb = payload_gain_kg(with_payload(vehicle, p_base), v0)
        strict = min(y0, yb)
        pad = _with_metrics(er.baseline.result, payload_kg=p_base)
        between = _with_metrics(silo, payload_kg=p_base + 0.5 * (y0 + yb))
        c = compare.compare_planar(between, pad, vehicle, checks=checks, name="silo_cold")
        assert c["screening_yardstick_kg"] == pytest.approx(strict, rel=1e-12)
        assert c["screening_yardstick_basis"] == basis
        assert c["payload_beyond_screening_kg"] == pytest.approx(0.5 * (y0 + yb) - strict, rel=1e-9)
        assert c["beats_screening"] is True


def test_gamma_sensitivity_ranges_in_the_checks(fast_run: tuple[Any, Path]) -> None:
    """With neighbours on the variant's matched run (built here: the variant's own run at
    -h, a copy at +h) the M2 and M4 records carry the ratio or share range over gamma*
    +/- h and gamma_robust; the verdict at gamma*_ref is unchanged; neighbours whose
    gravity term equals the centre's are robust; with the pad as the -h neighbour (every
    contribution 0: ratio 0) the M2 verdict changes, so it is not robust, and the
    summary's Checks section names it."""
    er, _out = fast_run
    checks = _checks(er)
    p0 = er.baseline.resolved.to_vehicle().payload_mass_kg
    pad, silo_rr = er.baseline, er.runs["silo_cold"]
    mb = sim.matched_run(pad.resolved, pad.result, p0)
    mv = sim.matched_run(silo_rr.resolved, silo_rr.result, p0)
    assert mb is not None and mv is not None and mv.neighbours is None
    h = sim.gamma_sensitivity_step_rad(silo_rr.resolved.run.planar.checks)
    g = mv.gamma_star_rad
    same = (
        dataclasses.replace(mv, gamma_star_rad=g - h),
        dataclasses.replace(mv, gamma_star_rad=g + h),
    )
    flat = dataclasses.replace(mv, neighbours=same)
    vehicle = silo_rr.resolved.to_vehicle()
    kwargs = {"checks": checks, "name": "silo_cold", "matched_baseline": mb}
    c0 = compare.compare_planar(silo_rr.result, pad.result, vehicle, matched=mv, **kwargs)
    c1 = compare.compare_planar(silo_rr.result, pad.result, vehicle, matched=flat, **kwargs)
    m2 = c1["checks_m2"]
    assert m2["status"] == c0["checks_m2"]["status"]
    assert m2["gamma_robust"] is True
    assert m2["value_range"] == pytest.approx([m2["ratio"], m2["ratio"]], rel=1e-12)
    assert c1["attr_gravity_dgamma_mps_per_rad"] == pytest.approx(0.0, abs=1e-6)
    pad_as_minus = dataclasses.replace(mb, name="silo_cold", gamma_star_rad=g - h)
    tilted = dataclasses.replace(mv, neighbours=(pad_as_minus, same[1]))
    c2 = compare.compare_planar(silo_rr.result, pad.result, vehicle, matched=tilted, **kwargs)
    m2 = c2["checks_m2"]
    assert m2["status"] == c0["checks_m2"]["status"]
    lo, hi = m2["value_range"]
    assert m2["neighbour_status"][0] == "fail" and lo <= 0.0 <= hi
    assert m2["gamma_robust"] is (m2["status"] == "fail")
    if m2["status"] == "pass":
        assert "M2" in summary._gamma_sensitive(c2)
        assert "NOT robust" in summary._check_text("m2", m2)
    assert c2["checks_m4"]["gamma_robust"] is not None


def test_fixed_guidance_failure_is_a_typed_status(repo_root: Path, tmp_path: Path) -> None:
    """A fixed-guidance run whose kick never triggers (v_k above any speed stage 1
    reaches) ends with status guidance_failed and a flag naming GuidanceFailure's kind,
    instead of raising out of the experiment; the summary is written."""
    exp, veh = _raw(repo_root)
    exp = _fixed(exp, ())
    exp["guidance"]["kick"]["v_kick_mps"] = 5000.0
    er, out = sim.run_experiment(resolve_experiment(exp, veh), tmp_path, plots=False)
    result = er.baseline.result
    assert result.status == sim.GUIDANCE_FAILED_STATUS
    assert result.metrics["guidance_failure_kind"] == "no_kick"
    assert any(f.startswith("guidance_failed: no_kick") for f in result.flags)
    assert result.metrics["search_status"] == sim.FIXED_GUIDANCE_STATUS
    assert "guidance_failed" in (out / "summary.md").read_text(encoding="utf-8")


def test_trajectory_key_drops_the_efficiency_only_for_constant_accel() -> None:
    """The drive efficiency is energy-only for constant_accel (the same trajectory key
    at two efficiencies) and trajectory-relevant for any other assist model."""

    def key(model: str, efficiency: float) -> str:
        run = {"name": "x", "assist": {"model": model, "drive_efficiency": efficiency}}
        return compare.trajectory_key(SimpleNamespace(run_dict=run, vehicle_dict={}))

    assert key("constant_accel", 0.5) == key("constant_accel", 0.6)
    assert key("linear_motor", 0.5) != key("linear_motor", 0.6)


def test_unconstrained_kick_labels_the_dp_star(fast_run: tuple[Any, Path]) -> None:
    """A kick faster than checks.unconstrained_kick_mps sets unconstrained_kick and
    payload_delta_upper_bound, and the screening line's bound text names it;
    silo_cold's recorded kick (at about 77 m/s) is below the threshold."""
    er, _out = fast_run
    checks = _checks(er)
    c = er.comparison["silo_cold"]
    assert er.runs["silo_cold"].result.metrics["speed_at_kick_mps"] < checks.unconstrained_kick_mps
    assert c["unconstrained_kick"] is False
    silo = er.runs["silo_cold"].result
    fast = _with_metrics(silo, speed_at_kick_mps=checks.unconstrained_kick_mps + 1.0)
    vehicle = er.runs["silo_cold"].resolved.to_vehicle()
    out = compare.compare_planar(fast, er.baseline.result, vehicle, checks=checks)
    assert out["unconstrained_kick"] is True and out["payload_delta_upper_bound"] is True
    assert "unconstrained kick" in summary._upper_bound_text(out)


def test_unwrap_takes_the_ambiguous_minus_pi_step_as_plus_pi() -> None:
    """unwrap_rad: a step past pi is unwrapped the short way (rotation on: pi/2 -> 3 ->
    -3 reads pi/2, 3, 2 pi - 3); an exact -pi step (rotation off: +pi/2 -> -pi/2 at the
    apex) is taken as +pi, so the fall reads 3 pi/2 either way; a smooth series is
    unchanged."""
    half = 0.5 * math.pi
    on = unwrap_rad(np.array([half, 3.0, -3.0, -half]))
    assert on == pytest.approx([half, 3.0, 2.0 * math.pi - 3.0, 3.0 * half], abs=1e-15)
    off = unwrap_rad(np.array([half, half, -half, -half]))
    assert off == pytest.approx([half, half, 3.0 * half, 3.0 * half], abs=1e-15)
    smooth = np.array([0.1, 0.2, 0.3])
    assert np.array_equal(unwrap_rad(smooth), smooth)
    tiny = 1e-14  # below the integrator's angular tolerance ATOL_RAD (1.57e-13 rad)
    near = unwrap_rad(np.array([half, -half + tiny]))
    assert near[1] == pytest.approx(3.0 * half + tiny, abs=1e-15)


# ---------------------------------------------------------------------------- slow


def _searched(exp: dict[str, Any], veh: dict[str, Any]) -> tuple[dict, dict]:
    """A small payload search: grid 20-24 deg, a short refine, the vehicle payload set
    near the pad's capacity so the payload brackets close at once; search rtol 1e-9
    (tests fly at most 1e-9, plan section 8)."""
    exp, veh = copy.deepcopy(exp), copy.deepcopy(veh)
    exp["search"].update(
        {
            "gamma_grid_deg": [20.0, 24.0, 2.0],
            "gamma_refine_maxiter": 3,
            "gamma_refine_halfwidth_deg": 1.0,
            "search_rtol": 1.0e-9,
        }
    )
    exp["baseline"]["integrator"]["sample_dt_s"] = FAST_SAMPLE_DT_S
    veh["payload_mass_t"]["value"] = 26.0
    exp["variants"] = {k: v for k, v in exp["variants"].items() if k == "silo_cold"}
    for key in ("sweeps", "sensitivity", "bounds"):
        exp.pop(key, None)
    return exp, veh


@pytest.mark.slow
def test_searched_runs_fill_every_required_metric(repo_root: Path, tmp_path: Path) -> None:
    """Searched pad and silo_cold (small grid): every PLANAR_REQUIRED_METRICS key is
    non-null, both end inserted with ok per-run checks, the search status is ok, dP* is
    the difference of the two P*, the matched-payload attribution (silo_cold re-flown at
    the pad's P*) closes within 1e-5 m/s and its kg split adds up to dP*, the matched
    run carries its gamma* neighbours (the gamma*-sensitivity rates and the M2 range),
    the summary states the sweep-optimized label, the search assumptions and the
    screening line, and the planar plots are written."""
    exp, veh = _searched(*_raw(repo_root))
    resolved = resolve_experiment(exp, veh)
    er, out = sim.run_experiment(resolved, tmp_path, plots=True, repo_root=repo_root)
    for name, rr in er.runs.items():
        m = rr.result.metrics
        assert missing_required(m) == [], name
        assert rr.result.status == "inserted" and m["search_status"] == "ok"
    c = er.comparison["silo_cold"]
    p_pad = er.runs["pad"].result.metrics["payload_kg"]
    d_p = er.runs["silo_cold"].result.metrics["payload_kg"] - p_pad
    assert c["payload_delta_kg"] == pytest.approx(d_p, abs=1e-9)
    assert c["attr_payload_kg"] == p_pad
    assert abs(c["attr_residual_mps"]) < ATTRIBUTION_TOL_MPS
    kg = [c[f"attr_{t}_kg"] for t in sim.ATTRIBUTION_TERMS]
    assert math.fsum(kg) == pytest.approx(d_p, abs=1e-6)
    h = sim.gamma_sensitivity_step_rad(er.runs["silo_cold"].resolved.run.planar.checks)
    assert c["attr_gamma_step_rad"] == pytest.approx(h, rel=1e-9)
    for term in ("gravity", "steering", "gravity_steering"):
        assert math.isfinite(c[f"attr_{term}_dgamma_mps_per_rad"]), term
    if c["checks_m2"]["status"] != "n/a":
        assert c["checks_m2"]["gamma_robust"] is not None
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert sim.SWEEP_OPTIMIZED_LABEL in text and sim.PLANAR_COMPARISON_BASIS in text
    assert all(a in text for a in sim.SEARCH_ASSUMPTIONS)
    assert any(ln.startswith("- silo_cold: dP* +") for ln in text.splitlines())
    pngs = sorted(p.name for p in (out / "plots").glob("*.png"))
    assert "pad_trajectory.png" in pngs and "silo_cold_track_forces.png" in pngs


@pytest.mark.slow
def test_bounds_cases_and_paired_sweeps(repo_root: Path, tmp_path: Path) -> None:
    """Fixed guidance: a bound re-runs silo_cold and the pad with the fairing-section
    A_ref (both written, compared with the pair: attributed, against the unchanged
    baseline: not_checked); a calibration-labelled experiment's case runs independently
    (never compared) under the CALIBRATION banner; a paired sweep of v_k compares each
    point with its paired baseline (written beside it), and the sweep summary carries the
    fixed-guidance label and a Checks section."""
    exp, veh = _raw(repo_root)
    bound = _fixed(exp, ("silo_cold",))
    bound["bounds"] = copy.deepcopy(exp["bounds"])
    er, out = sim.run_experiment(resolve_experiment(bound, veh), tmp_path, plots=False)
    assert [row.result.name for row in er.bounds] == ["silo_cold__aero_bound"]
    row = er.bounds[0]
    assert row.baseline.name == "pad__aero_bound"
    assert (
        row.result.result.metrics["drag_loss_mps"]
        > er.runs["silo_cold"].result.metrics["drag_loss_mps"]
    )
    assert (out / "silo_cold__aero_bound" / "timeseries.csv").is_file()
    assert (out / "pad__aero_bound" / "events.csv").is_file()
    assert "## Bounds" in (out / "summary.md").read_text(encoding="utf-8")
    assert abs(row.comparison["attr_residual_mps"]) < ATTRIBUTION_TOL_MPS
    assert row.comparison["screening_status"] != sim.SCREENING_NOT_CHECKED
    assert row.comparison_vs_nominal["screening_status"] == sim.SCREENING_NOT_CHECKED

    cal = _fixed(exp, ())
    cal["label"] = "calibration"
    cal["cases"] = {"no_rotation": {"site": {"include_rotation": False}}}
    er, out = sim.run_experiment(resolve_experiment(cal, veh), tmp_path, plots=False)
    case = er.cases["no_rotation"].result
    assert case.model == "planar_2d" and "no_rotation" not in er.comparison
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert text.startswith(sim.CALIBRATION_BANNER) and "## Cases" in text
    assert (out / "no_rotation" / "timeseries.csv").is_file()

    trig = _fixed(exp, ("silo_cold",))
    trig["label"] = "guidance_study"
    trig["sweeps"] = [
        {"of": "silo_cold", "axes": {"guidance.kick.v_kick_mps": [50, 80]}, "paired": True}
    ]
    sweeps, out = sim.run_sweep(resolve_experiment(trig, veh), tmp_path, plots=False)
    assert [p.name for p in sweeps[0].paired] == ["run_0001__pad", "run_0002__pad"]
    index = pd.read_csv(out / "sweep_1" / "sweep_index.csv")
    assert list(index["paired_baseline"]) == ["run_0001__pad", "run_0002__pad"]
    assert set(index["kick_regime"]) <= {"after_vertical_rise", "at_first_lit_instant"}
    assert (out / "sweep_1" / "run_0002__pad" / "metrics.json").is_file()
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert sim.FIXED_GUIDANCE_LABEL in text and sim.PLANAR_FIXED_COMPARISON_BASIS in text
    assert "## Checks" in text and "sweep_1/run_0002__pad" in text
    status = [c["screening_status"] for c in sweeps[0].comparisons]
    assert (sim.FINDINGS_BLOCKED in text) == (sim.BUG_SUSPECT in status)
