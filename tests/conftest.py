"""Shared fixtures. Physics fixtures are added as the modules they exercise appear.

Toy numbers are chosen for closed forms: c = 3000 m/s exactly (Isp = 3000 / g0),
stage 1 = 1000 kg at liftoff with 800 kg of propellant, 15 kN (mdot = 5 kg/s, 160 s burn).

Planar fixtures (build step 20; plan section 4) are factories for the analytic tests of
the planar model: ``large_R_params`` (a flat-Earth PlanarParams with mu = g_test R^2 at
a huge datum radius R), ``const_accel_schedule`` (a thrust schedule with c = 1e30 m/s,
so the mass is constant to rounding and T/m is a constant acceleration),
``exp_atmosphere`` (rho0 exp(-h/H), p = 0) and ``const_atmosphere`` (constant p,
rho = 0). ``run_planar``, ``test_budget`` and ``toy_two_stage`` need the planar planner
and the search and arrive with build steps 21 and 23.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Protocol

import matplotlib
import pytest
import yaml

from launchsim import sim
from launchsim.config import VehicleConfig
from launchsim.constants import G0_MPS2
from launchsim.dynamics import (
    AtmosphereFn,
    Gravity,
    InverseSquareGravity,
    PlanarParams,
    SteeringLaw,
    vacuum_atmosphere,
)
from launchsim.phases import AscentStart, IgnitionSpec, IntegratorSettings
from launchsim.vehicle import DragModel, Engine, Stage, Startup, ThrustSchedule, Vehicle

matplotlib.use("Agg")

REPO_ROOT = Path(__file__).resolve().parents[1]
TOY_C_MPS = 3000.0
HUGE_C_MPS = 1e30
"""Exhaust velocity [m/s] of ``const_accel_schedule``: the mass flow T/c is ~1e-30 of the
thrust, so the mass (and T/m) is constant to rounding."""
TEST_SOUND_SPEED_MPS = 340.0
"""Speed of sound [m/s] of the test atmospheres (only the Mach number of a drag table
reads it)."""


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root directory."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def planar_pins() -> ModuleType:
    """tests/planar_pin_support.py (the planar regression pins of SP1 step 1: resolved
    digests and the output capture), loaded by path so the tests that use it collect
    under any pytest import mode."""
    name = "planar_pin_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


# ------------------------------------------------------------------ planar (step 20)


class LargeRParams(Protocol):
    """Signature of the ``large_R_params`` fixture (see its docstring)."""

    def __call__(
        self,
        R_m: float,
        g_mps2: float,
        schedule: ThrustSchedule | None = None,
        steering: SteeringLaw | None = None,
        drag: DragModel | None = None,
        atmosphere: AtmosphereFn = vacuum_atmosphere,
    ) -> PlanarParams: ...


@pytest.fixture(scope="session")
def large_R_params() -> LargeRParams:
    """Flat-Earth planar parameters: large_R_params(R, g_test, schedule=None,
    steering=None, drag=None, atmosphere=vacuum_atmosphere) -> PlanarParams with
    gravity mu/r^2 for mu = g_test R^2 (so g = g_test at the datum and changes by
    2 h/R relative at altitude h), no rotation, g_ref = g_test and the altitude datum at
    radius R [m].

    The state carries altitude inside r = R + h, so h is quantised at ulp(R): about
    1.9e-9 m at R = 1e7, 1.2e-4 m at R = 1e12 and 1.6e-2 m at R = 1e14, and the dense
    output carries relative q noise near 1e-10 at R = 1e12 (review of step 20: the
    max-Q time t* then lands 3.5e-4 s off at R = 1e9 to 1e12, 1.6e-6 s at R = 1e7). Use
    the smallest R the test allows: with zero gravity (the max-Q closed form) radial
    motion is flat for any R, so a PlanarParams with ConstantGravity(0.0) and
    r_datum_m <= 1e7 (or R_E) serves (this factory needs g_test > 0, since
    InverseSquareGravity refuses mu = 0); a large R is needed only where the 2 h/R
    change of g must vanish."""

    def _params(
        R_m: float,
        g_mps2: float,
        schedule: ThrustSchedule | None = None,
        steering: SteeringLaw | None = None,
        drag: DragModel | None = None,
        atmosphere: AtmosphereFn = vacuum_atmosphere,
    ) -> PlanarParams:
        return PlanarParams(
            gravity=InverseSquareGravity(g_mps2 * R_m * R_m),
            omega_p_rads=0.0,
            g_ref_mps2=g_mps2,
            schedule=schedule,
            drag=drag,
            atmosphere=atmosphere,
            steering=steering,
            r_datum_m=R_m,
        )

    return _params


@pytest.fixture(scope="session")
def const_accel_schedule() -> Callable[..., ThrustSchedule]:
    """const_accel_schedule(A, m_kg=1.0, t_ign_s=0.0) -> ThrustSchedule: a step start
    at t_ign_s [s] of the thrust A m_kg [N] with c = HUGE_C_MPS and no exit area, i.e. a
    constant thrust acceleration A [m/s^2] on a vehicle of mass m_kg (the mass flow is
    ~1e-30 of the thrust)."""

    def _schedule(a_mps2: float, m_kg: float = 1.0, t_ign_s: float = 0.0) -> ThrustSchedule:
        return ThrustSchedule(
            thrust_vac_total_N=a_mps2 * m_kg,
            c_mps=HUGE_C_MPS,
            exit_area_total_m2=0.0,
            t_ign_abs_s=t_ign_s,
            startup=Startup("step"),
        )

    return _schedule


@pytest.fixture(scope="session")
def exp_atmosphere() -> Callable[[float, float], AtmosphereFn]:
    """exp_atmosphere(rho0, H) -> atmosphere function h -> (0 Pa, rho0 exp(-h/H),
    TEST_SOUND_SPEED_MPS): an exponential density profile [kg/m^3] with scale height H
    [m] and no pressure (so no back-pressure)."""

    def _factory(rho0_kgm3: float, scale_height_m: float) -> AtmosphereFn:
        def _atm(alt_m: float) -> tuple[float, float, float]:
            return 0.0, rho0_kgm3 * math.exp(-alt_m / scale_height_m), TEST_SOUND_SPEED_MPS

        return _atm

    return _factory


@pytest.fixture(scope="session")
def const_atmosphere() -> Callable[[float], AtmosphereFn]:
    """const_atmosphere(p) -> atmosphere function h -> (p [Pa], 0 kg/m^3,
    TEST_SOUND_SPEED_MPS): a constant ambient pressure for the thrust clamp (the 1-D
    model's constant p_amb) and no density (no drag)."""

    def _factory(p_pa: float) -> AtmosphereFn:
        def _atm(alt_m: float) -> tuple[float, float, float]:
            return p_pa, 0.0, TEST_SOUND_SPEED_MPS

        return _atm

    return _factory
