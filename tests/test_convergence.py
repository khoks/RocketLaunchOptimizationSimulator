"""Convergence of the 1-D runs under tightened integrator settings.

CLAUDE.md requires that tightening the tolerances 10x changes payload and margins by
less than 0.1 %. Phase 1 has no orbit, so no payload capacity and no propellant margin
exist yet; this test stands in for the Phase 2 payload/margin convergence test with the
1-D figures of merit (docs/physics.md, "Figures of merit in 1-D"): the stage-1 burnout
state, its delta against the pad, the loss terms, the drive energy, the failed-ignition
coast, and every event's time and mass. The shipped ``pad`` baseline and the
``silo_cold``, ``silo_cold_lag``, ``silo_hot_full`` and ``silo_failed`` variants of
experiments/silo_screening_1d.yaml are run through ``sim.run`` (mu/r^2, the run model)
twice: at the experiment's own settings (rtol 1e-10, ramp_steps 10, lag_steps_per_tau 4,
push_steps 50, sample_dt 0.05 s) and with rtol 1e-11, every max_step cap halved
(ramp_steps 20, lag_steps_per_tau 8, push_steps 100) and sample_dt 0.01 s. The lag run
exercises the lag cap, the hot-full run is the one where every assist-energy term
(drive work, thrust work, mass-flow term, dense-output power extrema) is non-zero, and
the failed run covers the apex and impact events.

Tolerances: every scalar is asserted at 1e-8 relative and the delta against the pad
within 1e-5 m/s absolute, 100x above the measured agreement (1.3e-10 relative at
worst, 4e-8 m/s on the delta; docs/physics.md, "Convergence") so that a genuinely
looser solver is caught: the plan's 1e-6 / 1e-3 m/s bounds are implied, and the 0.1 %
rule itself is asserted explicitly beside them. A quadrature that integrates to about
zero (the failed run's gravity loss over its symmetric coast, ~1e-9 m/s) is compared
against the velocity atol instead of relatively.

Altitudes are compared with an absolute allowance of ``ATOL_M`` (1e-6 m) as well as
relatively: the altitude reached at a burnout or apex carries an absolute error of
order 1e-6 m at rtol 1e-10 that is set by the step sequence and the dense-output event
root, not by the altitude state's atol alone (docs/physics.md, "Gravity"), so a
micrometre-level altitude change is not a convergence signal.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

from launchsim import sim
from launchsim.config import RunConfig, resolve_experiment
from launchsim.phases import ATOL_M, ATOL_MPS
from launchsim.vehicle import Vehicle

REL_TOL = 1e-8
"""Relative agreement asserted for every scalar (measured <= 1.3e-10; CLAUDE.md < 0.1 %)."""
DELTA_ABS_TOL_MPS = 1e-5
"""Absolute agreement [m/s] asserted for the burnout-speed delta against the pad
(measured <= 4e-8 m/s), independently of the relative bound."""
CLAUDE_MD_REL = 1e-3
"""The 0.1 % rule itself, checked explicitly beside the tighter assertion."""
TIME_ABS_TOL_S = 1e-9
"""Absolute floor [s] for event times at or near t = 0, where a relative test is moot."""

NOMINAL_INTEGRATOR: dict[str, Any] = {
    "rtol": 1e-10,
    "ramp_steps": 10,
    "lag_steps_per_tau": 4,
    "push_steps": 50,
    "sample_dt_s": 0.05,
}
TIGHT_INTEGRATOR: dict[str, Any] = {
    "rtol": 1e-11,
    "ramp_steps": 20,
    "lag_steps_per_tau": 8,
    "push_steps": 100,
    "sample_dt_s": 0.01,
}
RUN_NAMES = ("pad", "silo_cold", "silo_cold_lag", "silo_hot_full", "silo_failed")
BURNOUT_RUNS = ("pad", "silo_cold", "silo_cold_lag", "silo_hot_full")
"""Runs that end at stage-1 burnout (the figure-of-merit point); the rest end at impact."""
SILO_RUNS = ("silo_cold", "silo_cold_lag", "silo_hot_full", "silo_failed")
EXPECTED_STATUS = {name: "nominal" for name in BURNOUT_RUNS} | {"silo_failed": "impact"}

COMMON_METRICS = (
    "final_t_s",
    "final_speed_mps",
    "dv_vac_mps",
    "gravity_loss_mps",
    "gravity_loss_duration_mps",
    "gravity_loss_alt_mps",
    "speed_start_mps",
    "speed_end_mps",
    "peak_felt_g_flight",
    "mass_at_release_kg",
    "t_release_s",
    "speed_at_release_mps",
)
BURNOUT_METRICS = (
    "stage1_burnout_t_s",
    "stage1_burnout_speed_mps",
    "stage1_burnout_mass_kg",
    "stage1_burnout_alt_m",
)
TRACK_METRICS = (
    "exit_speed_mps",
    "push_time_s",
    "drive_energy_J",
    "drive_work_in_J",
    "electrical_energy_J",
    "drive_power_peak_W",
    "drive_power_peak_t_s",
    "interface_force_peak_N",
    "interface_force_min_N",
    "felt_g_track_peak",
    "facility_length_m",
    "propellant_burned_before_release_kg",
    "dv_vac_equiv_before_release_mps",
    "preflight_burn_cost_mps",
)
FAILED_METRICS = (
    "apex_alt_m",
    "apex_t_s",
    "impact_t_s",
    "impact_speed_mps",
    "failed_apex_alt_m",
    "failed_t_apex_s",
    "failed_t_return_s",
    "failed_t_carriage_s",
    "failed_speed_at_carriage_mps",
    "failed_impact_speed_mps",
    "failed_speed_at_shaft_bottom_mps",
)
ABS_FLOORS: dict[str, float] = {
    "stage1_burnout_alt_m": ATOL_M,
    "apex_alt_m": ATOL_M,
    "failed_apex_alt_m": ATOL_M,
    "gravity_loss_mps": ATOL_MPS,
    "gravity_loss_duration_mps": ATOL_MPS,
    "gravity_loss_alt_mps": ATOL_MPS,
}
"""Absolute allowances: altitudes (module docstring) and the loss quadratures, which
integrate to ~1e-9 m/s over the failed run's symmetric coast."""
DELTA_KEYS = (
    "stage1_burnout_speed_delta_mps",
    "d_speed_mps",
    "d_speed_release_mps",
    "d_dv_vac_mps",
    "d_gravity_duration_mps",
    "d_gravity_alt_mps",
)


def _metric_keys(run: str) -> tuple[str, ...]:
    """The metrics compared for one run: common, plus burnout, track and failed sets."""
    keys = COMMON_METRICS
    if run in BURNOUT_RUNS:
        keys += BURNOUT_METRICS
    if run in SILO_RUNS:
        keys += TRACK_METRICS
    if run == "silo_failed":
        keys += FAILED_METRICS
    return keys


def _resolved_runs(repo_root: Path, vehicle_dict: dict[str, Any]) -> dict[str, RunConfig]:
    """The shipped baseline and variants named in RUN_NAMES, validated through config.py."""
    exp = yaml.safe_load(
        (repo_root / "experiments" / "silo_screening_1d.yaml").read_text(encoding="utf-8")
    )
    resolved = resolve_experiment(exp, vehicle_dict)
    runs = {name: resolved.runs[name].run for name in RUN_NAMES}
    nominal = runs["pad"].integrator
    for key, value in NOMINAL_INTEGRATOR.items():
        assert getattr(nominal, key) == value, f"the shipped experiment's {key} is not {value}"
    return runs


def _with_integrator(cfg: RunConfig, integrator: dict[str, Any]) -> RunConfig:
    """The run config with its integrator block replaced (the rest unchanged)."""
    return RunConfig.model_validate({**cfg.model_dump(), "integrator": integrator})


def _run_both(cfg: RunConfig, vehicle: Vehicle) -> tuple[sim.Result, sim.Result]:
    """(nominal, tight) results of one run config through ``sim.run``."""
    return (
        sim.run(_with_integrator(cfg, NOMINAL_INTEGRATOR), vehicle),
        sim.run(_with_integrator(cfg, TIGHT_INTEGRATOR), vehicle),
    )


def _assert_close(name: str, a: float, b: float, *, abs_tol: float = 0.0) -> None:
    """|a - b| <= max(REL_TOL |b|, abs_tol), and the CLAUDE.md 0.1 % rule as well."""
    assert math.isfinite(a) and math.isfinite(b), name
    assert math.isclose(a, b, rel_tol=REL_TOL, abs_tol=abs_tol), (
        f"{name}: nominal {a!r} vs tight {b!r} differ by {a - b!r}"
    )
    assert math.isclose(a, b, rel_tol=CLAUDE_MD_REL, abs_tol=abs_tol), name


def _assert_events_agree(nominal: pd.DataFrame, tight: pd.DataFrame, run: str) -> None:
    """Same event sequence; every event's time and mass agree to REL_TOL (times near
    zero to TIME_ABS_TOL_S); altitudes to REL_TOL or ATOL_M, whichever is looser."""
    assert list(nominal["event"]) == list(tight["event"]), run
    assert list(nominal["phase"]) == list(tight["phase"]), run
    for (_, a), (_, b) in zip(nominal.iterrows(), tight.iterrows(), strict=True):
        label = f"{run}: event {a['event']} ({a['phase']})"
        _assert_close(f"{label} time", float(a["t_s"]), float(b["t_s"]), abs_tol=TIME_ABS_TOL_S)
        _assert_close(f"{label} mass", float(a["m_kg"]), float(b["m_kg"]))
        _assert_close(f"{label} altitude", float(a["z_m"]), float(b["z_m"]), abs_tol=ATOL_M)


@pytest.fixture(scope="module")
def results(
    repo_root: Path, f9_vehicle_dict: dict[str, Any], f9_vehicle: Vehicle
) -> dict[str, tuple[sim.Result, sim.Result]]:
    """(nominal, tight) results per run name, computed once for the module."""
    runs = _resolved_runs(repo_root, f9_vehicle_dict)
    return {name: _run_both(cfg, f9_vehicle) for name, cfg in runs.items()}


@pytest.mark.parametrize("run", RUN_NAMES)
def test_scalar_metrics_converge(
    results: dict[str, tuple[sim.Result, sim.Result]], run: str
) -> None:
    nominal, tight = results[run]
    assert nominal.status == tight.status == EXPECTED_STATUS[run]
    assert nominal.flags == tight.flags
    if run == "silo_failed":
        # The shipped variant inherits the baseline's t_ign_s = -2, which the failed
        # ignition ignores and flags; nothing else may be flagged.
        assert all(f.startswith("ignition_failed") for f in nominal.flags)
    else:
        assert nominal.flags == []
    for key in _metric_keys(run):
        a, b = nominal.metrics[key], tight.metrics[key]
        assert a is not None and b is not None, f"{run}: {key} missing"
        _assert_close(f"{run}: {key}", float(a), float(b), abs_tol=ABS_FLOORS.get(key, 0.0))
    # Both settings close the loss identity to rounding (CLAUDE.md allows 0.01 m/s).
    for res in (nominal, tight):
        assert abs(float(res.metrics["identity_residual_mps"])) < 1e-6
        if run in SILO_RUNS:
            assert float(res.metrics["assist_energy_residual_rel"]) < 1e-9


@pytest.mark.parametrize("run", RUN_NAMES)
def test_event_times_and_masses_converge(
    results: dict[str, tuple[sim.Result, sim.Result]], run: str
) -> None:
    nominal, tight = results[run]
    _assert_events_agree(nominal.events, tight.events, run)


@pytest.mark.parametrize("run", ("silo_cold", "silo_cold_lag", "silo_hot_full"))
def test_delta_against_the_pad_converges(
    results: dict[str, tuple[sim.Result, sim.Result]], f9_vehicle: Vehicle, run: str
) -> None:
    """The figure of merit: the stage-1 burnout speed delta against the pad, and its
    identity decomposition, computed at both settings (each variant against the pad
    run at the same settings). The absolute and the relative bound are asserted
    separately, so neither can stand in for the other."""
    pad_nominal, pad_tight = results["pad"]
    var_nominal, var_tight = results[run]
    cmp_nominal = sim.compare(var_nominal, pad_nominal, f9_vehicle)
    cmp_tight = sim.compare(var_tight, pad_tight, f9_vehicle)
    for key in DELTA_KEYS:
        a, b = float(cmp_nominal[key]), float(cmp_tight[key])
        assert abs(a - b) < DELTA_ABS_TOL_MPS, f"{run}: {key} {a!r} vs {b!r}"
        _assert_close(f"{run}: {key}", a, b)
    assert cmp_nominal["identity_point"] == cmp_tight["identity_point"] == "stage1_burnout"
    for cmp in (cmp_nominal, cmp_tight):
        assert abs(float(cmp["identity_line_residual_mps"])) < sim.IDENTITY_TOL_MPS
    # The payload equivalent (the kg form of the same delta) moves by far less than 0.1 %.
    _assert_close(
        f"{run}: ideal_screening_payload_equiv_kg",
        float(cmp_nominal["ideal_screening_payload_equiv_kg"]),
        float(cmp_tight["ideal_screening_payload_equiv_kg"]),
    )


def test_tight_settings_are_actually_tighter(
    results: dict[str, tuple[sim.Result, sim.Result]],
) -> None:
    """The tightened run resamples at 0.01 s (about five times as many rows), so the
    comparison above is between two genuinely different solver configurations."""
    for run in RUN_NAMES:
        nominal, tight = results[run]
        assert len(tight.timeseries) > 4 * len(nominal.timeseries), run
    assert math.isclose(TIGHT_INTEGRATOR["rtol"], NOMINAL_INTEGRATOR["rtol"] / 10.0, rel_tol=1e-12)
    for key in ("ramp_steps", "lag_steps_per_tau", "push_steps"):
        assert TIGHT_INTEGRATOR[key] == 2 * NOMINAL_INTEGRATOR[key]
