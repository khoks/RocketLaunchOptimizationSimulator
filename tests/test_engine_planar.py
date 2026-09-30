"""Planar event states in search mode and the stage-2 event factories (docs/physics.md,
"Event rules", rule 4, and "Stage 2 and insertion (planar)").

- Dense output off (the search mode) against on (a recorded run): a full insertion run
  of the gate pad (hold, rise, kick, turn, staging coast, the fairing event, the energy
  cutoff) logs the same EventRecords, burnouts and final state, bit for bit (the plan
  asks 1e-9 relative): the solver takes the same steps, and event states come from
  ``PhaseResult.y_events`` either way.
- The factories against the functions written here: the energy cutoff E - E* with
  E = (v_r^2 + v_theta^2)/2 - mu/r, the mass floor m - m_floor, the fairing criterion
  ln(0.5 rho |v_rel|^3 / q_fmh).
- A heating criterion first met during the staging coast drops the fairing at stage-2
  ignition, with a flag.
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.atmosphere import ambient_scalar
from launchsim.config import LtgConfig, SearchConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity
from launchsim.guidance import DeltaSolveSettings, GuidanceSpec, LtgSettings, solve_delta_for_gamma
from launchsim.orbit import TargetOrbit
from launchsim.phases import IgnitionSpec, IntegratorSettings
from launchsim.phases.engine import ATOL_KG, ATOL_MPS, EVENT_ZERO_TOL
from launchsim.phases.planar import (
    LTG_BURN,
    PlanarEnvironment,
    PlanarPlanner,
    ev_energy_cutoff,
    ev_fmh,
    ev_mass_floor,
    fmh_rate_W_m2,
)
from launchsim.vehicle import FairingDrop, Vehicle

P2 = PLANAR_LAYOUT
LAT_RAD = math.radians(28.5)
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)  # azimuth 90 deg
R_TARGET_M = R_EARTH_M + 200.0e3
ENV = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml (payload 22.8 t)."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _planner(vehicle: Vehicle, *, dense: bool) -> PlanarPlanner:
    return PlanarPlanner(
        vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        ENV,
        "insertion",
        IntegratorSettings(rtol=1e-10, dense_output=dense),
        target=TargetOrbit(R_TARGET_M),
        ltg=LtgSettings.from_config(LtgConfig(), final=False),
    )


@pytest.fixture(scope="module")
def guidance_inputs(gate_vehicle: Vehicle) -> tuple[float, float, float]:
    """(delta, a, b) of the gate pad at gamma* = 20 deg (search mode)."""
    planner = _planner(gate_vehicle, dense=False)
    kick = planner.to_kick(planner.start())
    sol = solve_delta_for_gamma(
        lambda d: planner.from_kick(d, kick),
        math.radians(20.0),
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    ltg = planner.solve_stage2(sol.handover)
    return sol.delta_rad, ltg.a, ltg.b_per_s


def test_dense_off_logs_the_same_events_to_insertion(
    gate_vehicle: Vehicle, guidance_inputs: tuple[float, float, float]
) -> None:
    """The full run with dense output off and on: equal EventRecords (the fairing event
    and the cutoff included), burnouts and status; only the dense-on trace can be
    resampled, and the dense-off trace says so."""
    delta, a, b = guidance_inputs
    on = _planner(gate_vehicle, dense=True).run(delta, ltg=(a, b))
    off = _planner(gate_vehicle, dense=False).run(delta, ltg=(a, b))
    assert on.status == off.status == "inserted"
    assert on.events == off.events
    assert {"fairing", "cutoff"} <= {e.name for e in on.events}
    for stage in ("stage1", "stage2"):
        assert on.burnouts[stage][0] == off.burnouts[stage][0]
        np.testing.assert_array_equal(on.burnouts[stage][1], off.burnouts[stage][1])
    assert off.dense_off and not on.dense_off
    assert all(o.nfev <= n.nfev for o, n in zip(off.phases, on.phases, strict=True))
    with pytest.raises(ValueError, match="dense output off"):
        off.require_dense("test")


def test_stage2_event_factories() -> None:
    """ev_energy_cutoff: E - E* written here (1e-12 relative of mu/r), direction +1,
    terminal, named cutoff, zero_tol = ATOL_MPS v_c; ev_mass_floor: m - m_floor,
    direction -1, ATOL_KG, refuses a floor <= 0; ev_fmh: ln(0.5 rho V^3 / limit) with
    rho from the atmosphere at h and V = |v_rel| written here (1e-12), direction -1,
    -inf at zero density, refuses a limit <= 0."""
    target = TargetOrbit(R_TARGET_M)
    cutoff = ev_energy_cutoff(target, MU_EARTH_M3S2)
    assert (cutoff.name, cutoff.direction, cutoff.terminal) == ("cutoff", 1, True)
    assert cutoff.zero_tol == pytest.approx(ATOL_MPS * math.sqrt(MU_EARTH_M3S2 / R_TARGET_M))
    rng = np.random.default_rng(221)
    for r, v_r, v_t in zip(
        rng.uniform(R_EARTH_M, R_TARGET_M + 1e5, 20),
        rng.uniform(-200.0, 1500.0, 20),
        rng.uniform(2000.0, 8000.0, 20),
        strict=True,
    ):
        y = P2.build(r_m=r, v_r_mps=v_r, v_theta_mps=v_t, m_kg=1e4)
        expected = (
            0.5 * (v_r * v_r + v_t * v_t) - MU_EARTH_M3S2 / r + MU_EARTH_M3S2 / (2 * R_TARGET_M)
        )
        assert cutoff.fn(0.0, y) == pytest.approx(expected, abs=1e-12 * MU_EARTH_M3S2 / r)
        alt = r - R_EARTH_M
        rho = ambient_scalar(alt)[1]
        rate = 0.5 * rho * math.hypot(v_r, v_t - OMEGA_P * r) ** 3
        assert ev_fmh(1135.0, ENV).fn(0.0, y) == pytest.approx(math.log(rate / 1135.0), rel=1e-12)
    fmh = ev_fmh(1135.0, ENV)
    assert (fmh.name, fmh.direction, fmh.zero_tol) == ("fairing", -1, EVENT_ZERO_TOL)
    vacuum = dataclasses.replace(ENV, atmosphere=lambda h: (0.0, 0.0, math.inf))
    assert ev_fmh(1135.0, vacuum).fn(0.0, P2.build(r_m=R_TARGET_M, v_theta_mps=7e3, m_kg=1.0)) == (
        -math.inf
    )
    floor = ev_mass_floor(13_400.0)
    assert (floor.name, floor.direction, floor.zero_tol) == ("mass_floor", -1, ATOL_KG)
    assert floor.fn(0.0, P2.build(r_m=R_TARGET_M, m_kg=20_000.0)) == 6_600.0
    for bad in (lambda: ev_mass_floor(0.0), lambda: ev_fmh(-1.0, ENV)):
        with pytest.raises(ValueError):
            bad()


def test_fairing_criterion_met_in_the_staging_coast(
    gate_vehicle: Vehicle, guidance_inputs: tuple[float, float, float]
) -> None:
    """A heating limit between the rates at MECO and at stage-2 ignition (their
    geometric mean): the fairing stays on at staging and drops at stage-2 ignition, logged
    there (phase LTG_BURN) with a flag, and the burn runs without the fairing event."""
    delta, a, b = guidance_inputs
    probe = _planner(gate_vehicle, dense=False)
    ho = probe.stage1(delta, probe.start())
    assert ho.y_ign2 is not None and ho.t_ign2_s is not None
    rate_meco = fmh_rate_W_m2(ho.prefix.burnouts["stage1"][1], ENV)
    rate_ign = fmh_rate_W_m2(ho.y_ign2, ENV)
    assert rate_ign < rate_meco
    rule = FairingDrop("free_molecular_heating", math.sqrt(rate_meco * rate_ign))
    vehicle = dataclasses.replace(gate_vehicle, fairing_drop=rule)
    planner = _planner(vehicle, dense=False)
    ho = planner.stage1(delta, planner.start())
    assert ho.fairing_on
    burn = planner.stage2(ho, a, b, virtual_propellant=True)
    assert burn.t_fairing_s == ho.t_ign2_s and not burn.fairing_on
    assert burn.m_after_fairing_kg == pytest.approx(
        float(P2.get(ho.y_ign2, "m_kg")) - vehicle.fairing_mass_kg, rel=1e-15
    )
    event = burn.prefix.first_event("fairing")
    assert event is not None and event.phase == LTG_BURN and event.t_s == ho.t_ign2_s
    assert any("staging coast" in f for f in burn.prefix.flags)
    lit = [p for p in burn.prefix.phases if p.spec.kind == LTG_BURN]
    assert all("fairing" not in {e.name for e in p.spec.events} for p in lit)
