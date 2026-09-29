"""Shared fixtures. Physics fixtures are added as the modules they exercise appear.

Toy numbers are chosen for closed forms: c = 3000 m/s exactly (Isp = 3000 / g0),
stage 1 = 1000 kg at liftoff with 800 kg of propellant, 15 kN (mdot = 5 kg/s, 160 s burn).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pytest
import yaml

from launchsim.config import VehicleConfig
from launchsim.constants import G0_MPS2
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
