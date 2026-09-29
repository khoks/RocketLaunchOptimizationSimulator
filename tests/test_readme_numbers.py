"""Reproduces README hand numbers; calibration-flavoured, not validation.

The README's concept-A table was derived by hand for a 549 t Falcon-9-class rocket
pushed 100 m vertically at 3 g net (v = sqrt(2 a L) = 77 m/s in 2.6 s, 4 g felt, 21.5 MN
at the interface, about 2.2 GJ and 1.65 GW, 1.2 MWh at 50 % efficiency, ~300 m and
~7.8 s of fall-back coast after a failed ignition, 5-25 m/s of ignition loss for a
0-1 s delay and a 1-3 s ramp). This module runs the shipped experiment
(experiments/silo_screening_1d.yaml: the 542,570 kg generic vehicle, mu/r^2 gravity,
the run model) in-process through ``sim.run`` and checks that the simulator lands
within the tolerances the plan set for each hand number. Those tolerances are loose on
purpose: the README used 549 t and g0 where the simulator uses 542.57 t and
g_eff = mu/R_E^2, so agreement is a sanity check on the constants and the wiring, not
a validation of the physics (the closed-form validation tests live in test_silo.py,
test_ignition_loss.py, test_failed_ignition.py and test_loss_identity.py).

Two checks here are exact and are stated as such: the ignition-timing loss between
``silo_instant`` and a delayed variant is, by the loss identity, the difference of
their gravity losses with identical dv_vac (asserted to 1e-6 m/s), and every variant's
identity line must close (CLAUDE.md, 0.01 m/s) with no gain beyond its release speed,
hold-down credit and altitude term.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
import yaml

from launchsim import sim
from launchsim.config import SweepPoint, resolve_experiment
from launchsim.constants import MU_EARTH_M3S2, R_EARTH_M
from launchsim.vehicle import Vehicle

EXPERIMENT = "silo_screening_1d.yaml"
VARIANTS = (
    "pad_instant",
    "silo_instant",
    "silo_cold",
    "silo_cold_lag",
    "silo_hot_ramp_on_track",
    "silo_hot_full",
    "silo_hot_full_impinged",
    "silo_failed",
    "silo_sled_22t",
)

# README / plan hand numbers (rounded on purpose; see the module docstring) and the
# plan's tolerances for each.
V_EXIT_MPS, V_EXIT_ABS = 76.71, 0.01
T_PUSH_S, T_PUSH_ABS = 2.607, 0.001
FELT_G, FELT_G_ABS = 3.999, 0.001
F_INT_README_N, F_INT_REL = 21.5e6, 0.02  # README: 21.5 MN at 549 t
E_DRIVE_README_J, E_DRIVE_REL = 2.2e9, 0.04  # README: about 2.2 GJ
P_PEAK_README_W, P_PEAK_REL = 1.65e9, 0.02  # README: near 1.65 GW mechanical
E_ELEC_README_KWH, E_ELEC_REL = 1200.0, 0.03  # README: ~1.2 MWh at 50 % efficiency
D_BRAKE_M, D_BRAKE_ABS = 60.0, 0.01
FACILITY_M = 160.0
FAILED_APEX_M, FAILED_APEX_ABS = 300.3, 0.5
FAILED_T_APEX_S, FAILED_T_APEX_ABS = 7.83, 0.01
IGNITION_LOSS_ABS_MPS = 0.8
"""The constant-g formula vs the mu/r^2 integration (the delayed vehicle flies lower)."""
EXACT_MPS = 1e-6
BURNOUT_DELTA_ABS_MPS = 2.0
BURNOUT_DELTAS_MPS = {
    "silo_instant": 85.0,
    "silo_cold": 70.0,
    "silo_cold_lag": 70.0,
    "silo_hot_ramp_on_track": 79.0,
    "silo_hot_full": 64.0,
    "silo_hot_full_impinged": 64.0,
    "silo_sled_22t": 70.0,
}
"""Plan, 'Verification': stage-1 burnout speed deltas against the pad."""
HOT_FULL_ENERGY_J = {"silo_hot_full": 1.28e9, "silo_hot_full_impinged": 2.10e9}
HOT_FULL_POWER_W = {"silo_hot_full": 0.97e9, "silo_hot_full_impinged": 1.60e9}
HOT_FULL_REL = 0.01
HOT_FULL_POWER_SAVING_MIN = 0.35
"""The hot start at f_imp = 0 must cut the peak drive power by at least 35 %."""

RAMP_SWEEP = ((0.0, 1.0), (0.5, 2.0), (1.0, 3.0))
"""(delay, ramp) points of the shipped ignition sweep: the README's 5-25 m/s band."""
LAG_SWEEP_TAU_S = 1.0
LAG_SWEEP_DELAY_S = 0.5

G_EFF_MPS2 = MU_EARTH_M3S2 / R_EARTH_M**2
"""The track g_eff with omega_p = 0 (Phase 1), also the g_ref of the loss split."""


def _within(x: float, ref: float, rel: float) -> bool:
    """|x - ref| <= rel |ref|."""
    return abs(x - ref) <= rel * abs(ref)


def _pick_point(points: list[SweepPoint], **wanted: float) -> SweepPoint:
    """The sweep point whose overrides end with the given path suffixes and values."""
    for point in points:
        got = {path.rsplit(".", 1)[-1]: value for path, value in point.overrides.items()}
        if all(math.isclose(got[k], v) for k, v in wanted.items()):
            return point
    raise LookupError(f"no sweep point with {wanted}")


@pytest.fixture(scope="module")
def results(
    repo_root: Path, f9_vehicle_dict: dict[str, Any], f9_vehicle: Vehicle
) -> dict[str, sim.Result]:
    """Every run of the shipped experiment (baseline and variants), plus the ignition
    sweep points named in RAMP_SWEEP (keys 'ramp_<delay>_<t_ramp>') and the lag sweep
    point at LAG_SWEEP_TAU_S (key 'lag_1'), through sim.run (mu/r^2)."""
    exp = yaml.safe_load((repo_root / "experiments" / EXPERIMENT).read_text(encoding="utf-8"))
    resolved = resolve_experiment(exp, f9_vehicle_dict)
    assert tuple(resolved.variants) == VARIANTS, "the shipped variant list changed"
    out = {name: sim.run(r.run, f9_vehicle) for name, r in resolved.runs.items()}
    ramp_sweep, lag_sweep = resolved.sweeps[1], resolved.sweeps[2]
    for delay, t_ramp in RAMP_SWEEP:
        point = _pick_point(ramp_sweep, t_ign_s=delay, t_ramp_s=t_ramp)
        out[f"ramp_{delay}_{t_ramp}"] = sim.run(point.run.run, f9_vehicle)
    point = _pick_point(lag_sweep, tau_s=LAG_SWEEP_TAU_S)
    assert point.run.run.ignition["stage1"].t_ign_s == LAG_SWEEP_DELAY_S
    out["lag_1"] = sim.run(point.run.run, f9_vehicle)
    return out


def test_every_shipped_variant_runs_nominally_except_the_failed_ignition(
    results: dict[str, sim.Result],
) -> None:
    for name in ("pad", *VARIANTS):
        expected = "impact" if name == "silo_failed" else "nominal"
        assert results[name].status == expected, name


def test_exit_speed_push_time_and_felt_g(results: dict[str, sim.Result]) -> None:
    m = results["silo_cold"].metrics
    assert abs(m["exit_speed_mps"] - V_EXIT_MPS) <= V_EXIT_ABS
    assert abs(m["speed_at_release_mps"] - V_EXIT_MPS) <= V_EXIT_ABS
    assert abs(m["push_time_s"] - T_PUSH_S) <= T_PUSH_ABS
    assert abs(m["felt_g_track_peak"] - FELT_G) <= FELT_G_ABS
    # The README's headline load: 4 g on a full stack, below the 5.7 g at burnout.
    assert m["felt_g_track_peak_mass_kg"] == pytest.approx(542_570.0)
    assert m["peak_felt_g_flight"] > m["felt_g_track_peak"]
    assert m["peak_track_normal_g"] == pytest.approx(0.0, abs=1e-12)


def test_interface_force_energy_power_and_electrical(results: dict[str, sim.Result]) -> None:
    m = results["silo_cold"].metrics
    assert _within(m["interface_force_peak_N"], F_INT_README_N, F_INT_REL)
    assert _within(m["drive_energy_J"], E_DRIVE_README_J, E_DRIVE_REL)
    assert _within(m["drive_power_peak_W"], P_PEAK_README_W, P_PEAK_REL)
    assert _within(m["electrical_energy_kWh"], E_ELEC_README_KWH, E_ELEC_REL)
    # Cold push: the whole drive energy is mechanical work on the stack, so the
    # electrical figure is exactly E_drive / efficiency (0.5 in the shipped config).
    assert m["electrical_energy_J"] == pytest.approx(2.0 * m["drive_energy_J"], rel=1e-12)


def test_braking_and_facility_length(results: dict[str, sim.Result]) -> None:
    m = results["silo_cold"].metrics
    assert abs(m["braking_distance_m"] - D_BRAKE_M) <= D_BRAKE_ABS
    assert abs(m["facility_length_m"] - FACILITY_M) <= D_BRAKE_ABS


def test_failed_ignition_coast(results: dict[str, sim.Result]) -> None:
    r = results["silo_failed"]
    assert r.status == "impact"
    m = r.metrics
    assert abs(m["failed_apex_alt_m"] - FAILED_APEX_M) <= FAILED_APEX_ABS
    assert abs(m["failed_t_apex_s"] - FAILED_T_APEX_S) <= FAILED_T_APEX_ABS
    # Symmetric drag-free coast: back at the mouth at 2 t_apex with the exit speed.
    assert m["failed_t_return_s"] == pytest.approx(2.0 * m["failed_t_apex_s"], rel=1e-9)
    assert abs(m["failed_impact_speed_mps"] - V_EXIT_MPS) <= V_EXIT_ABS


@pytest.mark.parametrize(("delay", "t_ramp"), list(RAMP_SWEEP))
def test_ramp_ignition_loss_matches_the_readme_band(
    results: dict[str, sim.Result], delay: float, t_ramp: float
) -> None:
    """silo_instant minus the delayed variant is g (delay + ramp/2) to within the
    altitude effect, and exactly the gravity-loss difference at identical dv_vac."""
    instant, delayed = results["silo_instant"].metrics, results[f"ramp_{delay}_{t_ramp}"].metrics
    loss = instant["stage1_burnout_speed_mps"] - delayed["stage1_burnout_speed_mps"]
    assert abs(loss - G_EFF_MPS2 * (delay + t_ramp / 2.0)) <= IGNITION_LOSS_ABS_MPS
    assert abs(instant["dv_vac_mps"] - delayed["dv_vac_mps"]) <= EXACT_MPS
    assert abs(instant["speed_at_release_mps"] - delayed["speed_at_release_mps"]) <= EXACT_MPS
    d_grav = delayed["gravity_loss_mps"] - instant["gravity_loss_mps"]
    assert abs(loss - d_grav) <= EXACT_MPS
    assert delayed["drag_loss_mps"] == delayed["steering_loss_mps"] == 0.0
    assert delayed["back_pressure_loss_mps"] == 0.0


def test_lag_ignition_loss(results: dict[str, sim.Result]) -> None:
    """A first-order lag with tau = 1 s after a 0.5 s delay loses g (t_d + tau)."""
    instant, lag = results["silo_instant"].metrics, results["lag_1"].metrics
    loss = instant["stage1_burnout_speed_mps"] - lag["stage1_burnout_speed_mps"]
    assert abs(loss - G_EFF_MPS2 * (LAG_SWEEP_DELAY_S + LAG_SWEEP_TAU_S)) <= IGNITION_LOSS_ABS_MPS
    assert abs(instant["dv_vac_mps"] - lag["dv_vac_mps"]) <= EXACT_MPS
    assert abs(loss - (lag["gravity_loss_mps"] - instant["gravity_loss_mps"])) <= EXACT_MPS
    # The shipped silo_cold_lag variant is this same point.
    assert lag["stage1_burnout_speed_mps"] == pytest.approx(
        results["silo_cold_lag"].metrics["stage1_burnout_speed_mps"], rel=1e-12
    )


def test_identity_closes_and_nothing_beats_its_release_speed(
    results: dict[str, sim.Result], f9_vehicle: Vehicle
) -> None:
    pad, instant = results["pad"], results["silo_instant"]
    for name in VARIANTS:
        r = results[name]
        assert abs(r.metrics["identity_residual_mps"]) < sim.IDENTITY_TOL_MPS, name
        c = sim.compare(r, pad, f9_vehicle, instant)
        assert abs(c["identity_line_residual_mps"]) < sim.IDENTITY_TOL_MPS, name
        if name == "silo_failed":
            assert c["unexplained_gain_mps"] is None  # no stage-1 burnout to compare
            continue
        assert c["identity_point"] == "stage1_burnout", name
        # CLAUDE.md: a gain beyond the release speed, the hold-down credit and the
        # altitude term would be a bug; for these variants it is minus the post-release
        # ignition loss, so it is at most ~0.
        assert c["unexplained_gain_mps"] <= sim.IDENTITY_TOL_MPS, name


@pytest.mark.parametrize("name", sorted(BURNOUT_DELTAS_MPS))
def test_burnout_speed_delta_against_the_pad(results: dict[str, sim.Result], name: str) -> None:
    pad = results["pad"].metrics["stage1_burnout_speed_mps"]
    delta = results[name].metrics["stage1_burnout_speed_mps"] - pad
    assert abs(delta - BURNOUT_DELTAS_MPS[name]) <= BURNOUT_DELTA_ABS_MPS, (name, delta)


def test_hot_start_trades_propellant_for_drive_energy_and_peak_power(
    results: dict[str, sim.Result],
) -> None:
    cold = results["silo_cold"].metrics
    for name, energy in HOT_FULL_ENERGY_J.items():
        m = results[name].metrics
        assert _within(m["drive_energy_J"], energy, HOT_FULL_REL), name
        assert _within(m["drive_power_peak_W"], HOT_FULL_POWER_W[name], HOT_FULL_REL), name
        # Same exit speed and felt g as the cold push: the hot start buys no speed.
        assert m["exit_speed_mps"] == pytest.approx(cold["exit_speed_mps"], rel=1e-12)
        assert m["felt_g_track_peak"] == pytest.approx(cold["felt_g_track_peak"], rel=1e-12)
        assert m["propellant_burned_before_release_kg"] > 0.0
        assert m["stage1_burnout_speed_mps"] < cold["stage1_burnout_speed_mps"]
    hot = results["silo_hot_full"].metrics
    cap = (1.0 - HOT_FULL_POWER_SAVING_MIN) * cold["drive_power_peak_W"]
    assert hot["drive_power_peak_W"] <= cap
    assert hot["drive_energy_J"] < cold["drive_energy_J"]
