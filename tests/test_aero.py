"""Aero data layer: the C_D(M) PCHIP table, the drag model, back-pressure with the 2-D
vehicle forks' exit areas, the ``ambient_scalar`` RHS fast path, the fairing rule, the
config blocks that build them, and the three 2-D vehicle forks.

Expected values are computed here from closed forms and independent oracles:
``scipy.interpolate.PchipInterpolator`` for the table, the Fritsch-Butland slope formula
written out below for the knot derivatives, ``ambiance.Atmosphere`` for rho and a, and
the raw YAML numbers for the forks' masses and exit areas.
"""

from __future__ import annotations

import copy
import itertools
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from ambiance import CONST as ICAO_CONST
from ambiance import Atmosphere
from pydantic import ValidationError
from scipy.interpolate import PchipInterpolator

from launchsim.atmosphere import (
    ATMOSPHERE_ASSUMPTIONS,
    ambient_scalar,
    standard_atmosphere,
)
from launchsim.config import (
    AeroConfig,
    CdMachConfig,
    FairingDropConfig,
    QuantityList,
    VehicleConfig,
    resolve_run,
)
from launchsim.constants import (
    ALT_AMBIANCE_MAX_M,
    ALT_AMBIANCE_MIN_M,
    MU_EARTH_M3S2,
    P_SEA_LEVEL_PA,
    R_EARTH_M,
)
from launchsim.vehicle import (
    CdTable,
    DragModel,
    FairingDrop,
    Vehicle,
    ideal_dv_mps,
    with_cd_scale,
    with_payload,
)

# Braeunig 2020 ballpark launcher C_D(M) (plan section 7), typed here independently of
# the vehicle files.
BRAEUNIG_MACH = (
    0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15,
    1.2, 1.3, 1.5, 1.75, 2.0, 2.5, 3.0, 3.25, 3.5, 4.0, 4.5,
)  # fmt: skip
BRAEUNIG_CD = (
    0.460, 0.404, 0.387, 0.385, 0.388, 0.400, 0.450, 0.510, 0.589, 0.660, 0.710, 0.730,
    0.722, 0.680, 0.606, 0.527, 0.460, 0.350, 0.273, 0.250, 0.236, 0.222, 0.220,
)  # fmt: skip

P0_ICAO_PA = 101_325.0
"""ICAO sea-level pressure [Pa] (ICAO Doc 7488 table value)."""
BODY_DIAMETER_M = 3.66
"""Falcon 9 body diameter [m] (User's Guide 2021 Table 2-1)."""

FORKS = (
    "generic_f9_class_2d",
    "generic_f9_class_2d_readme_loads",
    "generic_f9_class_2d_recorded_scope",
)
# (stage1 dry, stage1 propellant, stage2 dry, stage2 propellant, fairing) [t], and the
# launch mass without payload [t] the fork header states.
FORK_MASSES_T = {
    "generic_f9_class_2d": ((22.2, 410.9, 4.0, 107.5, 1.7), 546.3),
    "generic_f9_class_2d_readme_loads": ((25.6, 395.7, 3.9, 92.67, 1.9), 519.77),
    "generic_f9_class_2d_recorded_scope": ((25.6, 410.9, 4.0, 107.5, 1.9), 549.9),
}
MASS_PATHS = (
    ("stages", 0, "dry_mass_t"),
    ("stages", 0, "propellant_mass_t"),
    ("stages", 1, "dry_mass_t"),
    ("stages", 1, "propellant_mass_t"),
    ("fairing_mass_t",),
)

KNOT_TOL = 1e-15
C1_TOL = 1e-10
SCIPY_TOL = 1e-14
FORCE_REL = 1e-12
ORACLE_REL = 1e-12
THRUST_REL = 1e-12


def _extension_rho_a(alt_m: float) -> tuple[float, float]:
    """Closed-form isothermal extension above the ICAO table top: (rho [kg/m^3], a [m/s]).

    p = p_top exp(-(h - h_top) / H_s), rho = p / (R_air T_top), a = a_top, with the top
    state from ``ambiance.Atmosphere(h_top)`` and H_s = R_air T_top (R_E + h_top)^2 / mu.
    """
    h_top = ALT_AMBIANCE_MAX_M
    top = Atmosphere(h_top)
    p_top, t_top = float(top.pressure[0]), float(top.temperature[0])
    scale_height_m = ICAO_CONST.R * t_top * (R_EARTH_M + h_top) ** 2 / MU_EARTH_M3S2
    p = p_top * math.exp(-(alt_m - h_top) / scale_height_m)
    return p / (ICAO_CONST.R * t_top), float(top.speed_of_sound[0])


def _load(repo_root: Path, name: str) -> dict[str, Any]:
    path = repo_root / "configs" / "vehicles" / f"{name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _get(node: Any, path: tuple[Any, ...]) -> Any:
    for key in path:
        node = node[key]
    return node


@pytest.fixture(scope="module")
def table() -> CdTable:
    return CdTable.pchip(BRAEUNIG_MACH, BRAEUNIG_CD)


@pytest.fixture(scope="module")
def oracle() -> PchipInterpolator:
    return PchipInterpolator(BRAEUNIG_MACH, BRAEUNIG_CD)


@pytest.fixture(scope="module")
def fork_dicts(repo_root: Path) -> dict[str, dict[str, Any]]:
    return {name: _load(repo_root, name) for name in FORKS}


@pytest.fixture(scope="module")
def fork_vehicles(fork_dicts: dict[str, dict[str, Any]]) -> dict[str, Vehicle]:
    return {n: VehicleConfig.model_validate(d).to_vehicle() for n, d in fork_dicts.items()}


# ----------------------------------------------------------------------- C_D table


def _slopes(x: tuple[float, ...], y: tuple[float, ...]) -> list[float]:
    """PCHIP knot slopes written out: Fritsch-Butland weighted harmonic mean inside
    (zero at a local extremum), the three-point shape-preserving rule at the ends."""
    h = [b - a for a, b in itertools.pairwise(x)]
    delta = [(y[i + 1] - y[i]) / h[i] for i in range(len(h))]
    d = [0.0] * len(x)
    for k in range(1, len(x) - 1):
        if delta[k - 1] * delta[k] <= 0.0:
            continue
        w1 = 2.0 * h[k] + h[k - 1]
        w2 = h[k] + 2.0 * h[k - 1]
        d[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])

    def end(h0: float, h1: float, m0: float, m1: float) -> float:
        slope = ((2.0 * h0 + h1) * m0 - h0 * m1) / (h0 + h1)
        if math.copysign(1.0, slope) != math.copysign(1.0, m0):
            return 0.0
        if math.copysign(1.0, m0) != math.copysign(1.0, m1) and abs(slope) > 3.0 * abs(m0):
            return 3.0 * m0
        return slope

    d[0] = end(h[0], h[1], delta[0], delta[1])
    d[-1] = end(h[-1], h[-2], delta[-1], delta[-2])
    return d


def test_table_passes_through_every_knot(table: CdTable) -> None:
    for m, cd in zip(BRAEUNIG_MACH, BRAEUNIG_CD, strict=True):
        assert abs(table(m) - cd) <= KNOT_TOL


def test_table_is_c1_with_the_pchip_slopes(table: CdTable) -> None:
    slopes = _slopes(BRAEUNIG_MACH, BRAEUNIG_CD)
    for i, (c3, c2, c1, _) in enumerate(table.coeffs):
        h = BRAEUNIG_MACH[i + 1] - BRAEUNIG_MACH[i]
        left_end = 3.0 * c3 * h * h + 2.0 * c2 * h + c1  # slope at knot i+1 from the left
        assert abs(c1 - slopes[i]) <= C1_TOL
        assert abs(left_end - slopes[i + 1]) <= C1_TOL
        if i + 1 < len(table.coeffs):
            assert abs(left_end - table.coeffs[i + 1][2]) <= C1_TOL


def test_table_equals_scipy_pchip(table: CdTable, oracle: PchipInterpolator) -> None:
    grid = np.linspace(BRAEUNIG_MACH[0], BRAEUNIG_MACH[-1], 9_001)
    worst = max(abs(table(float(m)) - float(oracle(m))) for m in grid)
    assert worst <= SCIPY_TOL


def test_table_holds_the_end_values(table: CdTable) -> None:
    for m in (-1e-3, -1.0):
        assert table(m) == BRAEUNIG_CD[0]
    for m in (4.5, 4.500001, 7.0, 25.0, math.inf):
        assert table(m) == BRAEUNIG_CD[-1]
    assert math.isnan(table(math.nan))


def test_table_rejects_bad_knots() -> None:
    with pytest.raises(ValueError, match="strictly increase"):
        CdTable.pchip([0.0, 1.0, 1.0], [0.4, 0.5, 0.6])
    with pytest.raises(ValueError, match="one C_D per knot"):
        CdTable.pchip([0.0, 1.0], [0.4])
    with pytest.raises(ValueError, match=">= 0"):
        CdTable.pchip([0.0, 1.0], [0.4, -0.1])
    with pytest.raises(ValueError, match="finite"):
        CdTable.pchip([0.0, math.nan], [0.4, 0.5])
    good = CdTable.pchip([0.0, 1.0], [0.4, 0.5])
    with pytest.raises(ValueError, match="start at its knot"):
        CdTable(mach=good.mach, cd=good.cd, coeffs=((0.0, 0.0, 0.1, 0.41),))
    with pytest.raises(ValueError, match="one cubic per interval"):
        CdTable(mach=good.mach, cd=good.cd, coeffs=())
    with pytest.raises(TypeError, match="must be numbers"):
        CdTable(mach=[0.0, True], cd=[0.4, 0.5], coeffs=((0.0, 0.0, 0.1, 0.4),))


def test_hand_built_table_is_stored_as_tuples() -> None:
    table = CdTable(mach=[0, 1.0], cd=[0.4, 0.5], coeffs=[[0.0, 0.0, 0.1, 0.4]])
    assert table.mach == (0.0, 1.0) and table.cd == (0.4, 0.5)
    assert table.coeffs == ((0.0, 0.0, 0.1, 0.4),)
    assert all(type(v) is float for v in table.mach)
    assert hash(table) == hash(CdTable(mach=(0.0, 1.0), cd=(0.4, 0.5), coeffs=table.coeffs))
    assert table(0.5) == 0.45


# ---------------------------------------------------------------------------- drag

# (altitude [m], w [m/s], u [m/s]) through subsonic, transonic, supersonic and the
# isothermal extension, including a descending and a westward-leaning state.
DRAG_STATES = (
    (0.0, 50.0, -3.0),
    (3_000.0, 250.0, 40.0),
    (9_000.0, 280.0, 120.0),
    (11_500.0, 300.0, 180.0),
    (25_000.0, 600.0, 700.0),
    (60_000.0, 900.0, 2_000.0),
    (78_000.0, -20.0, 1_500.0),
    (95_000.0, 400.0, 3_000.0),
)


@pytest.mark.parametrize(("alt_m", "w", "u"), DRAG_STATES)
def test_drag_vector_against_ambiance_and_scipy(
    table: CdTable, oracle: PchipInterpolator, alt_m: float, w: float, u: float
) -> None:
    area, scale = 10.52, 1.07
    model = DragModel(table, reference_area_m2=area, cd_scale=scale)
    if alt_m <= ALT_AMBIANCE_MAX_M:
        ref = Atmosphere(alt_m)
        rho, a = float(ref.density[0]), float(ref.speed_of_sound[0])
        p_amb, rho_mine, a_mine = ambient_scalar(alt_m)
        assert rho_mine == pytest.approx(rho, rel=ORACLE_REL)
        assert a_mine == pytest.approx(a, rel=ORACLE_REL)
        assert p_amb == pytest.approx(float(ref.pressure[0]), rel=ORACLE_REL)
    else:
        rho, a = _extension_rho_a(alt_m)
        _, rho_mine, a_mine = ambient_scalar(alt_m)
        assert rho_mine == pytest.approx(rho, rel=ORACLE_REL)
        assert a_mine == pytest.approx(a, rel=ORACLE_REL)
    speed = math.hypot(w, u)
    mach = speed / a
    cd = scale * float(oracle(min(mach, BRAEUNIG_MACH[-1])))
    expected = (-0.5 * rho * speed * cd * area * w, -0.5 * rho * speed * cd * area * u)
    d_r, d_t = model.components_N(rho, a, w, u)
    assert d_r == pytest.approx(expected[0], rel=FORCE_REL)
    assert d_t == pytest.approx(expected[1], rel=FORCE_REL)
    q = 0.5 * rho * speed * speed
    assert model.force_N(q, mach) == pytest.approx(math.hypot(d_r, d_t), rel=FORCE_REL)
    assert model.force_N(q, mach) == pytest.approx(q * cd * area, rel=FORCE_REL)
    # drag opposes v_rel exactly: zero cross product, negative dot product
    assert d_r * u - d_t * w == pytest.approx(0.0, abs=FORCE_REL * abs(d_r * u))
    assert d_r * w + d_t * u < 0.0


def test_drag_is_exactly_zero_at_rest(table: CdTable) -> None:
    model = DragModel(table, reference_area_m2=10.52)
    assert model.components_N(1.225, 340.0, 0.0, 0.0) == (0.0, 0.0)
    assert model.force_N(0.0, 0.0) == 0.0


def test_cd_scale_is_exact_and_with_cd_scale_keeps_the_rest(
    table: CdTable, fork_vehicles: dict[str, Vehicle]
) -> None:
    for scale in (0.9, 1.0, 1.1):
        model = DragModel(table, reference_area_m2=10.52, cd_scale=scale)
        for m in (0.0, 0.45, 1.0, 1.17, 3.3, 9.0):
            assert model.cd(m) == scale * table(m)
    vehicle = fork_vehicles["generic_f9_class_2d"]
    scaled = with_cd_scale(vehicle, 1.1)
    assert scaled.aero is not None and vehicle.aero is not None
    assert scaled.aero.cd_scale == 1.1
    assert scaled.aero.table == vehicle.aero.table
    assert scaled.aero.reference_area_m2 == vehicle.aero.reference_area_m2
    assert scaled.stages == vehicle.stages and scaled.fairing_drop == vehicle.fairing_drop
    assert with_payload(vehicle, 1_000.0).aero == vehicle.aero
    with pytest.raises(ValueError, match="no drag model"):
        with_cd_scale(Vehicle(stages=vehicle.stages), 1.1)


def test_drag_model_rejects_bad_parameters(table: CdTable) -> None:
    for area in (0.0, -1.0, math.inf):
        with pytest.raises(ValueError, match="reference area"):
            DragModel(table, reference_area_m2=area)
    for scale in (0.0, -0.1, math.nan):
        with pytest.raises(ValueError, match="cd_scale"):
            DragModel(table, reference_area_m2=10.52, cd_scale=scale)


# ------------------------------------------------------------------ atmosphere path

# 50 altitudes: floor, layer bases (geometric), sea level, dense interior points, the
# top seam and the isothermal extension.
ATMOSPHERE_ALTITUDES_M = sorted(
    {
        ALT_AMBIANCE_MIN_M,
        -5_000.0,
        -1_000.0,
        0.0,
        1.0,
        11_019.1,
        20_063.1,
        32_161.9,
        47_350.1,
        51_412.5,
        71_802.0,
        ALT_AMBIANCE_MAX_M - 1e-6,
        ALT_AMBIANCE_MAX_M,
        ALT_AMBIANCE_MAX_M + 1e-6,
        110_000.0,
        200_000.0,
        *np.linspace(-4_000.0, 300_000.0, 34).tolist(),
    }
)


def test_fifty_altitudes() -> None:
    assert len(ATMOSPHERE_ALTITUDES_M) == 50


@pytest.mark.parametrize("alt_m", ATMOSPHERE_ALTITUDES_M)
def test_ambient_scalar_equals_standard_atmosphere(alt_m: float) -> None:
    state = standard_atmosphere(alt_m)
    assert ambient_scalar(alt_m) == (state.p_pa, state.rho_kgm3, state.a_mps)  # 0 ulp
    assert ambient_scalar(np.float64(alt_m)) == ambient_scalar(alt_m)
    assert all(type(x) is float for x in ambient_scalar(np.float64(alt_m)))


def test_ambient_scalar_clamps_below_the_floor() -> None:
    floor = standard_atmosphere(ALT_AMBIANCE_MIN_M)
    held = (floor.p_pa, floor.rho_kgm3, floor.a_mps)
    for alt in (ALT_AMBIANCE_MIN_M - 1e-9, -6_000.0, -1e6, -math.inf):
        assert ambient_scalar(alt) == held
        if math.isfinite(alt):
            with pytest.raises(ValueError, match="floor"):
                standard_atmosphere(alt)
    assert all(math.isnan(x) for x in ambient_scalar(math.nan))


def test_sea_level_pressure_is_the_constant() -> None:
    assert P_SEA_LEVEL_PA == P0_ICAO_PA
    assert standard_atmosphere(0.0).p_pa == P_SEA_LEVEL_PA
    assert ambient_scalar(0.0)[0] == P_SEA_LEVEL_PA


def test_atmosphere_assumptions_are_ascii_strings() -> None:
    assert isinstance(ATMOSPHERE_ASSUMPTIONS, tuple) and len(ATMOSPHERE_ASSUMPTIONS) >= 3
    for text in ATMOSPHERE_ASSUMPTIONS:
        assert text.startswith("atmosphere: ") and text.isascii()
    joined = " ".join(ATMOSPHERE_ASSUMPTIONS)
    for fragment in ("6,356,766 m", "81,020 m", "-5,004 m", "not US76", "v_rel"):
        assert fragment in joined


# ------------------------------------------------------------------- back-pressure


def test_stage1_sea_level_thrust_with_back_pressure(
    fork_dicts: dict[str, dict[str, Any]], fork_vehicles: dict[str, Vehicle]
) -> None:
    for name, raw in fork_dicts.items():
        engine = raw["stages"][0]["engine"]
        n = engine["count"]["value"]
        t_vac = engine["thrust_vac_kN"]["value"] * 1e3
        t_sl = engine["thrust_sl_kN"]["value"] * 1e3
        area = n * (t_vac - t_sl) / P0_ICAO_PA
        expected = n * t_vac - P0_ICAO_PA * area
        stage = fork_vehicles[name].stages[0]
        assert stage.exit_area_total_m2 == pytest.approx(area, rel=THRUST_REL)
        sched = stage.schedule(0.0)
        t_full = stage.startup.t_ramp_s + 1.0
        thrust = sched.thrust_N(t_full, ambient_scalar(0.0)[0])
        assert thrust == pytest.approx(expected, rel=THRUST_REL)
        assert round(thrust / 1e2) / 10.0 == 7_606.8  # kN, the published 7,607 kN


def test_stage2_back_pressure_at_70_km(
    fork_dicts: dict[str, dict[str, Any]], fork_vehicles: dict[str, Vehicle]
) -> None:
    for name, raw in fork_dicts.items():
        engine = raw["stages"][1]["engine"]
        area = engine["exit_area_m2"]["value"]
        t_vac = engine["thrust_vac_kN"]["value"] * 1e3
        p70 = float(Atmosphere(70_000.0).pressure[0])
        sched = fork_vehicles[name].stages[1].schedule(0.0)
        thrust = sched.thrust_N(1.0, ambient_scalar(70_000.0)[0])
        assert thrust == pytest.approx(t_vac - p70 * area, rel=THRUST_REL)
        assert round(t_vac - thrust) == 45  # N, the fork note's p A_e at 70 km


def test_clamp_region_burns_at_full_vacuum_rate(fork_vehicles: dict[str, Vehicle]) -> None:
    """While p0 A_e exceeds the ramping T_vac, T = 0, so the back-pressure integrand
    (T_vac - T)/m equals T_vac/m; the clamp ends at t = t_r p0 A_e / T_full."""
    stage = fork_vehicles["generic_f9_class_2d"].stages[0]
    sched = stage.schedule(0.0)
    p0 = ambient_scalar(0.0)[0]
    t_r = stage.startup.t_ramp_s
    t_end = t_r * p0 * stage.exit_area_total_m2 / stage.thrust_vac_total_N
    m = stage.wet_mass_kg
    for t in np.linspace(1e-6, t_end * (1.0 - 1e-9), 7):
        t_vac = sched.thrust_vac_N(float(t))
        assert t_vac > 0.0 and sched.thrust_N(float(t), p0) == 0.0
        assert (t_vac - sched.thrust_N(float(t), p0)) / m == t_vac / m
    assert sched.thrust_N(t_end * (1.0 + 1e-6), p0) > 0.0


# ------------------------------------------------------------------- fairing rule


def test_fairing_rule_and_string_shim(two_stage_toy: Vehicle) -> None:
    heating = FairingDrop("free_molecular_heating", 1_135.0)
    for trigger in ("staging", "never"):
        v = Vehicle(stages=two_stage_toy.stages, fairing_drop=FairingDrop(trigger))
        assert v.fairing_drop == trigger and isinstance(v.fairing_drop, str)
        assert v == Vehicle(stages=two_stage_toy.stages, fairing_drop=trigger)
        assert v.fairing_rule == FairingDrop(trigger)
    v = Vehicle(stages=two_stage_toy.stages, fairing_drop=heating)
    assert v.fairing_drop == heating and v.fairing_rule == heating
    with pytest.raises(ValueError, match="needs a finite limit"):
        FairingDrop("free_molecular_heating")
    with pytest.raises(ValueError, match="takes no limit"):
        FairingDrop("staging", 1_135.0)
    with pytest.raises(ValueError, match="unknown fairing"):
        Vehicle(stages=two_stage_toy.stages, fairing_drop="jettison")  # type: ignore[arg-type]


def test_screening_counts_the_heating_rule_as_a_drop_at_staging(two_stage_toy: Vehicle) -> None:
    heating = Vehicle(
        stages=two_stage_toy.stages,
        fairing_mass_kg=two_stage_toy.fairing_mass_kg,
        payload_mass_kg=two_stage_toy.payload_mass_kg,
        fairing_drop=FairingDrop("free_molecular_heating", 1_135.0),
        screening_isp_s=two_stage_toy.screening_isp_s,
    )
    assert two_stage_toy.fairing_drop == "staging"
    assert ideal_dv_mps(heating) == ideal_dv_mps(two_stage_toy)
    assert heating.stack_mass_kg(1) == two_stage_toy.stack_mass_kg(1)
    assert heating.mass_after_staging_kg(0) == two_stage_toy.mass_after_staging_kg(0)


# -------------------------------------------------------------------- config blocks


def _cd_block(**extra: Any) -> dict[str, Any]:
    return {"mach": [0, 1, 2], "cd": [0.4, 0.6, 0.3], "assumed": True, **extra}


def test_quantity_list_rules() -> None:
    assert isinstance(CdMachConfig.model_validate(_cd_block()), QuantityList)
    with pytest.raises(ValidationError, match="exactly one"):
        CdMachConfig.model_validate({"mach": [0, 1], "cd": [0.4, 0.5]})
    with pytest.raises(ValidationError, match="exactly one"):
        CdMachConfig.model_validate(_cd_block(source="x"))
    with pytest.raises(ValidationError, match="blank"):
        CdMachConfig.model_validate({"mach": [0, 1], "cd": [0.4, 0.5], "source": " "})
    for bad in ([0, True], [0, "1"], [0, None]):
        with pytest.raises(ValidationError, match="must be a number"):
            CdMachConfig.model_validate(_cd_block(mach=bad, cd=[0.4, 0.5]))
    with pytest.raises(ValidationError):
        CdMachConfig.model_validate(_cd_block(cd=[0.4, math.nan, 0.3]))
    with pytest.raises(ValidationError, match="bare value"):
        CdMachConfig.model_validate([0, 1, 2])
    with pytest.raises(ValidationError, match="one C_D per knot"):
        CdMachConfig.model_validate(_cd_block(cd=[0.4, 0.6]))
    with pytest.raises(ValidationError, match="strictly increase"):
        CdMachConfig.model_validate(_cd_block(mach=[0, 2, 1]))
    with pytest.raises(ValidationError, match="Extra inputs"):
        CdMachConfig.model_validate(_cd_block(value=1.0))


def test_aero_config_builds_the_drag_model() -> None:
    raw = {
        "reference_area_m2": {"value": 10.52, "assumed": True},
        "cd_scale": {"value": 1.0, "assumed": True},
        "cd_mach": _cd_block(),
    }
    model = AeroConfig.model_validate(raw).to_drag_model()
    assert model.cd_scale == 1.0 and model.reference_area_m2 == 10.52
    assert model.table == CdTable.pchip([0.0, 1.0, 2.0], [0.4, 0.6, 0.3])
    scaled = AeroConfig.model_validate({**raw, "cd_scale": {"value": 0.9, "assumed": True}})
    assert scaled.to_drag_model().cd_scale == 0.9
    with pytest.raises(ValidationError, match="cd_scale"):
        AeroConfig.model_validate({k: v for k, v in raw.items() if k != "cd_scale"})
    with pytest.raises(ValidationError, match="Input should be 'pchip'"):
        AeroConfig.model_validate({**raw, "interpolation": "linear"})
    with pytest.raises(ValidationError, match="bare value"):
        AeroConfig.model_validate({**raw, "reference_area_m2": 10.52})


def test_fairing_drop_config_rules(f9_vehicle_dict: dict[str, Any]) -> None:
    heating = {"trigger": "free_molecular_heating", "limit_W_m2": {"value": 1135, "source": "s"}}
    assert FairingDropConfig.model_validate(heating).to_fairing_drop() == FairingDrop(
        "free_molecular_heating", 1_135.0
    )
    with pytest.raises(ValidationError, match="needs a finite limit"):
        FairingDropConfig.model_validate({"trigger": "free_molecular_heating"})
    with pytest.raises(ValidationError, match="takes no limit"):
        FairingDropConfig.model_validate({**heating, "trigger": "staging"})
    for value in ("staging", "never", {"trigger": "never"}):
        raw = {**copy.deepcopy(f9_vehicle_dict), "fairing_drop": value}
        vehicle = VehicleConfig.model_validate(raw).to_vehicle()
        assert isinstance(vehicle.fairing_drop, str)
    with pytest.raises(ValidationError):
        VehicleConfig.model_validate({**copy.deepcopy(f9_vehicle_dict), "fairing_drop": "x"})


def test_one_d_run_refuses_the_heating_rule(fork_dicts: dict[str, dict[str, Any]]) -> None:
    for raw in fork_dicts.values():
        with pytest.raises(ValueError, match=r"planar_2d feature.*staging and never"):
            resolve_run("pad", {"name": "pad"}, raw)
        staging = {**copy.deepcopy(raw), "fairing_drop": "staging"}
        assert resolve_run("pad", {"name": "pad"}, staging).to_vehicle().aero is not None


# --------------------------------------------------------------------- vehicle forks


def _unsourced_numbers(node: Any, path: str = "") -> list[str]:
    """Paths of numbers that no provenance covers: a number counts as sourced inside a
    Quantity dict (has ``value``) or a table dict that carries source or assumed."""
    if isinstance(node, dict):
        if "value" in node or "source" in node or node.get("assumed") is True:
            return []
        return [p for k, v in node.items() for p in _unsourced_numbers(v, f"{path}.{k}")]
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in _unsourced_numbers(v, f"{path}.{i}")]
    if isinstance(node, int | float) and not isinstance(node, bool):
        return [path]
    return []


@pytest.mark.parametrize("name", FORKS)
def test_fork_numbers_all_have_provenance(fork_dicts: dict[str, dict[str, Any]], name: str) -> None:
    raw = fork_dicts[name]
    assert raw["name"] == name
    assert _unsourced_numbers(raw) == []


@pytest.mark.parametrize("name", FORKS)
def test_fork_masses_and_launch_mass_closure(
    fork_dicts: dict[str, dict[str, Any]], fork_vehicles: dict[str, Vehicle], name: str
) -> None:
    masses_t, closure_t = FORK_MASSES_T[name]
    raw = fork_dicts[name]
    assert tuple(_get(raw, p)["value"] for p in MASS_PATHS) == masses_t
    vehicle = fork_vehicles[name]
    without_payload_kg = vehicle.liftoff_mass_kg() - vehicle.payload_mass_kg
    assert without_payload_kg == pytest.approx(sum(masses_t) * 1e3, rel=1e-12)
    assert without_payload_kg == pytest.approx(closure_t * 1e3, rel=1e-12)
    assert vehicle.payload_mass_kg == pytest.approx(22_800.0, rel=1e-12)


def test_readme_fork_masses_are_the_one_d_files(
    fork_dicts: dict[str, dict[str, Any]], f9_vehicle_dict: dict[str, Any]
) -> None:
    readme = fork_dicts["generic_f9_class_2d_readme_loads"]
    for path in MASS_PATHS:
        mine, theirs = _get(readme, path), _get(f9_vehicle_dict, path)
        assert mine["value"] == theirs["value"]
        assert mine.get("assumed", False) == theirs.get("assumed", False)


def test_forks_differ_only_in_masses(fork_dicts: dict[str, dict[str, Any]]) -> None:
    def strip(raw: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(raw)
        for key in ("name", "description"):
            out.pop(key)
        for path in MASS_PATHS:
            _get(out, path[:-1]).pop(path[-1])
        return out

    gate = strip(fork_dicts["generic_f9_class_2d"])
    for name in FORKS[1:]:
        assert strip(fork_dicts[name]) == gate


def test_gate_fork_inputs(
    fork_dicts: dict[str, dict[str, Any]], fork_vehicles: dict[str, Vehicle]
) -> None:
    raw = fork_dicts["generic_f9_class_2d"]
    aero = raw["aero"]
    assert tuple(aero["cd_mach"]["mach"]) == BRAEUNIG_MACH
    assert tuple(aero["cd_mach"]["cd"]) == BRAEUNIG_CD
    assert aero["cd_mach"]["assumed"] is True and "Braeunig" in aero["cd_mach"]["note"]
    assert aero["interpolation"] == "pchip"
    area = aero["reference_area_m2"]["value"]
    assert area == round(math.pi * BODY_DIAMETER_M**2 / 4.0, 2)
    vehicle = fork_vehicles["generic_f9_class_2d"]
    assert vehicle.aero == DragModel(CdTable.pchip(BRAEUNIG_MACH, BRAEUNIG_CD), area, 1.0)
    assert vehicle.fairing_rule == FairingDrop("free_molecular_heating", 1_135.0)
    assert vehicle.stages[1].coast_before_ignition_s == 11.0
    assert vehicle.stages[1].exit_area_total_m2 == 8.6
    assert raw["stages"][1]["engine"].get("thrust_sl_kN") is None
