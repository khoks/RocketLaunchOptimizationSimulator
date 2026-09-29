"""Shared fixtures. Physics fixtures are added as the modules they exercise appear.

Toy numbers are chosen for closed forms: c = 3000 m/s exactly (Isp = 3000 / g0),
stage 1 = 1000 kg at liftoff with 800 kg of propellant, 15 kN (mdot = 5 kg/s, 160 s burn).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import matplotlib
import pytest
import yaml

from launchsim import sim
from launchsim.config import VehicleConfig
from launchsim.constants import G0_MPS2
from launchsim.dynamics import Gravity
from launchsim.phases import AscentStart, IgnitionSpec, IntegratorSettings
from launchsim.vehicle import Engine, Stage, Startup, Vehicle

matplotlib.use("Agg")

REPO_ROOT = Path(__file__).resolve().parents[1]
TOY_C_MPS = 3000.0


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root directory."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def f9_vehicle_dict(repo_root: Path) -> dict:
    """Raw dict of configs/vehicles/generic_f9_class.yaml."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def f9_vehicle(f9_vehicle_dict: dict) -> Vehicle:
    """The generic Falcon 9-class vehicle loaded through config.py."""
    return VehicleConfig.model_validate(f9_vehicle_dict).to_vehicle()


def _toy_engine(thrust_n: float) -> Engine:
    return Engine(thrust_vac_N=thrust_n, isp_vac_s=TOY_C_MPS / G0_MPS2, exit_area_m2=0.0)


@pytest.fixture(scope="session")
def tight_settings() -> IntegratorSettings:
    """Integrator settings for validation tests: DOP853, rtol 1e-10, per-state atol."""
    return IntegratorSettings(rtol=1e-10)


@pytest.fixture(scope="session")
def toy_stage() -> Stage:
    """Single toy stage: 200 kg dry + 800 kg propellant, 15 kN, c = 3000 m/s, step start."""
    return Stage(
        name="stage1",
        dry_mass_kg=200.0,
        propellant_mass_kg=800.0,
        engine=_toy_engine(15_000.0),
        n_engines=1,
        startup=Startup("step"),
        coast_before_ignition_s=0.0,
    )


@pytest.fixture(scope="session")
def two_stage_toy(toy_stage: Stage) -> Vehicle:
    """Two-stage toy: stage 2 = 150 kg dry + 150 kg propellant, 3 kN, c = 3000 m/s;
    payload 50 kg; fairing 10 kg dropped at staging; liftoff 1360 kg."""
    stage2 = Stage(
        name="stage2",
        dry_mass_kg=150.0,
        propellant_mass_kg=150.0,
        engine=_toy_engine(3_000.0),
        n_engines=1,
        startup=Startup("step"),
        coast_before_ignition_s=0.0,
    )
    return Vehicle(
        stages=(toy_stage, stage2),
        fairing_mass_kg=10.0,
        payload_mass_kg=50.0,
        fairing_drop="staging",
        screening_isp_s=(TOY_C_MPS / G0_MPS2, TOY_C_MPS / G0_MPS2),
    )


class RunVertical(Protocol):
    """Signature of the ``run_vertical`` fixture (see its docstring)."""

    def __call__(
        self,
        vehicle: Vehicle,
        ignition: Mapping[str, IgnitionSpec],
        gravity: Gravity,
        g_eff: float,
        start: AscentStart | None = None,
        end: str = "stage1_burnout",
        settings: IntegratorSettings | None = None,
    ) -> sim.Result: ...


@pytest.fixture(scope="session")
def run_vertical(tight_settings: IntegratorSettings) -> RunVertical:
    """``sim.simulate`` on the pad (no track) with an injected gravity model and start.

    run_vertical(vehicle, ignition, gravity, g_eff, start=AscentStart(), end=
    "stage1_burnout", settings=tight_settings) -> Result. ``ignition`` is an
    IgnitionSpec per stage name; stages absent from it get IgnitionSpec() (lit at
    release, step or the stage's own startup). ``gravity`` is the Gravity model
    (ConstantGravity in analytic tests, InverseSquareGravity for the run model) and
    ``g_eff`` the pad gravity and the g_ref of the gravity-loss split.
    """

    def _run(
        vehicle: Vehicle,
        ignition: Mapping[str, IgnitionSpec],
        gravity: Gravity,
        g_eff: float,
        start: AscentStart | None = None,
        end: str = "stage1_burnout",
        settings: IntegratorSettings | None = None,
    ) -> sim.Result:
        specs = {name: ignition.get(name, IgnitionSpec()) for name in vehicle.stage_names}
        return sim.simulate(
            vehicle=vehicle,
            ignition=specs,
            gravity=gravity,
            g_eff_mps2=g_eff,
            assist=sim.NoAssist(),
            track=None,
            start=AscentStart() if start is None else start,
            end=end,
            settings=tight_settings if settings is None else settings,
        )

    return _run
