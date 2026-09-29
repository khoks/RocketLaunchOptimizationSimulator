"""Mass bookkeeping and the ideal-rocket-equation screening.

The README table (25 ... 300 m/s -> +220 ... +2790 kg; 14 / 18 / 53 t of stage-1 propellant
saved) is reproduced with an independent rocket-equation model and brentq written here,
never with the package's own functions. Labelled: reproduces README hand numbers, which
is a screening yardstick and not a trajectory result.
"""

from __future__ import annotations

import math

import pytest
from scipy.optimize import brentq

from launchsim.constants import G0_MPS2
from launchsim.vehicle import (
    Engine,
    Stage,
    Startup,
    Vehicle,
    ideal_dv_mps,
    payload_gain_kg,
    payload_per_mps_kg,
    stage1_propellant_saved_kg,
    with_payload,
    with_stage_propellant,
)

# README hand numbers: assist speed -> (payload gain [kg], stage-1 propellant saved as
# (whole tonnes, fraction of the 395.7 t load) or None). The README rounds the tonnes to
# integers (13.5% of 395.7 t is 53.4 t, printed as 53 t), so the fraction is the sharper check.
README_TABLE = {
    25.0: (220.0, None),
    50.0: (440.0, None),
    77.0: (690.0, (14.0, 0.036)),
    99.0: (890.0, (18.0, 0.046)),
    150.0: (1360.0, None),
    300.0: (2790.0, (53.0, 0.135)),
}

# Independent copy of the generic F9-class numbers (README), SI
DRY1, PROP1, DRY2, PROP2, FAIRING, PAYLOAD = (
    25_600.0,
    395_700.0,
    3_900.0,
    92_670.0,
    1_900.0,
    22_800.0,
)
ISP1_EFF, ISP2_EFF = 295.0, 348.0


def _dv_independent(payload: float, prop1: float = PROP1, carry_fairing: bool = False) -> float:
    """Two-stage ideal delta-v with the fairing dropped at staging (or carried)."""
    m0 = DRY1 + prop1 + DRY2 + PROP2 + FAIRING + payload
    m_bo1 = m0 - prop1
    m_ign2 = DRY2 + PROP2 + payload + (FAIRING if carry_fairing else 0.0)
    m_bo2 = m_ign2 - PROP2
    return G0_MPS2 * ISP1_EFF * math.log(m0 / m_bo1) + G0_MPS2 * ISP2_EFF * math.log(m_ign2 / m_bo2)


def test_mass_bookkeeping_two_stage_toy(two_stage_toy: Vehicle) -> None:
    v = two_stage_toy
    assert v.liftoff_mass_kg() == 1000.0 + 300.0 + 50.0 + 10.0
    assert v.stack_mass_kg(0) == 1360.0
    assert v.stack_dry_mass_kg(0) == 560.0
    assert v.mass_after_staging_kg(0) == 350.0
    assert v.stack_mass_kg(1) == 350.0  # fairing gone at staging
    assert v.stack_mass_kg(1) == v.mass_after_staging_kg(0)
    assert v.stack_dry_mass_kg(1) == 200.0
    assert v.mass_after_staging_kg(1) == 50.0  # only the payload remains
    assert v.stage_index("stage2") == 1 and v.stage_names == ("stage1", "stage2")
    with pytest.raises(KeyError):
        v.stage_index("stage3")
    with pytest.raises(IndexError):
        v.stack_mass_kg(2)
    carried = Vehicle(v.stages, v.fairing_mass_kg, v.payload_mass_kg, "never", v.screening_isp_s)
    assert carried.stack_mass_kg(1) == 360.0 and carried.mass_after_staging_kg(0) == 360.0
    assert math.isclose(v.stages[0].burn_time_s, 160.0, rel_tol=1e-12)
    assert math.isclose(v.stages[0].c_mps, 3000.0, rel_tol=1e-12)


def test_toy_ideal_dv_is_the_rocket_equation(two_stage_toy: Vehicle) -> None:
    expect = 3000.0 * math.log(1360.0 / 560.0) + 3000.0 * math.log(350.0 / 200.0)
    assert math.isclose(ideal_dv_mps(two_stage_toy), expect, rel_tol=1e-12)
    assert math.isclose(
        ideal_dv_mps(two_stage_toy, 100.0),
        3000.0 * math.log(1410.0 / 610.0) + 3000.0 * math.log(400.0 / 250.0),
        rel_tol=1e-12,
    )
    assert with_payload(two_stage_toy, 100.0).payload_mass_kg == 100.0
    assert with_stage_propellant(two_stage_toy, 0, 700.0).stages[0].propellant_mass_kg == 700.0
    assert two_stage_toy.stages[0].propellant_mass_kg == 800.0  # originals untouched


def test_f9_bookkeeping_matches_independent_model(f9_vehicle: Vehicle) -> None:
    assert math.isclose(f9_vehicle.liftoff_mass_kg(), 542_570.0, rel_tol=1e-12)
    assert math.isclose(f9_vehicle.stack_dry_mass_kg(0), 542_570.0 - PROP1, rel_tol=1e-12)
    assert math.isclose(f9_vehicle.mass_after_staging_kg(0), DRY2 + PROP2 + PAYLOAD, rel_tol=1e-12)
    assert math.isclose(ideal_dv_mps(f9_vehicle), _dv_independent(PAYLOAD), rel_tol=1e-12)
    # stage-1 c ln(m0/mf) with the real vacuum Isp, quoted in the plan's rocket-equation test
    c1 = f9_vehicle.stages[0].c_mps
    assert math.isclose(c1 * math.log(542_570.0 / 146_870.0), 3985.4, rel_tol=1e-4)


@pytest.mark.parametrize("v_assist", sorted(README_TABLE))
def test_payload_gain_matches_independent_brentq(f9_vehicle: Vehicle, v_assist: float) -> None:
    target = _dv_independent(PAYLOAD) - v_assist
    expect = (
        brentq(lambda p: _dv_independent(p) - target, PAYLOAD, 10 * PAYLOAD, xtol=1e-12, rtol=1e-15)
        - PAYLOAD
    )
    got = payload_gain_kg(f9_vehicle, v_assist)
    assert math.isclose(got, expect, rel_tol=1e-6)


@pytest.mark.parametrize("v_assist", sorted(README_TABLE))
def test_readme_screening_table(f9_vehicle: Vehicle, v_assist: float) -> None:
    """Reproduces README hand numbers (screening yardstick, not a trajectory result)."""
    gain_kg, saved = README_TABLE[v_assist]
    assert abs(payload_gain_kg(f9_vehicle, v_assist) - gain_kg) < 5.0
    if saved is not None:
        saved_t_rounded, saved_fraction = saved
        got_t = stage1_propellant_saved_kg(f9_vehicle, v_assist) / 1000.0
        assert abs(got_t - saved_fraction * PROP1 / 1000.0) < 0.3
        assert abs(got_t - saved_t_rounded) < 0.5  # README prints whole tonnes


def test_propellant_saved_matches_independent_brentq(f9_vehicle: Vehicle) -> None:
    for v_assist in (77.0, 99.0, 300.0):
        target = _dv_independent(PAYLOAD) - v_assist
        expect = PROP1 - brentq(
            lambda p1, target=target: _dv_independent(PAYLOAD, prop1=p1) - target,
            1.0,
            PROP1,
            xtol=1e-12,
            rtol=1e-15,
        )
        assert math.isclose(stage1_propellant_saved_kg(f9_vehicle, v_assist), expect, rel_tol=1e-6)


def test_payload_per_mps_about_nine_kg(f9_vehicle: Vehicle) -> None:
    for v_assist in (25.0, 77.0, 300.0):
        per = payload_per_mps_kg(f9_vehicle, v_assist)
        assert 8.5 < per < 9.5
    assert payload_gain_kg(f9_vehicle, 0.0) == 0.0
    assert stage1_propellant_saved_kg(f9_vehicle, 0.0) == 0.0
    with pytest.raises(ValueError):
        payload_gain_kg(f9_vehicle, -1.0)
    with pytest.raises(ValueError):
        payload_per_mps_kg(f9_vehicle, 0.0)


def test_carrying_the_fairing_raises_the_77_mps_gain(f9_vehicle: Vehicle) -> None:
    """README: carrying the fairing into stage-2 flight raises the 77 m/s gain to ~740 kg."""
    carried = Vehicle(
        f9_vehicle.stages,
        f9_vehicle.fairing_mass_kg,
        f9_vehicle.payload_mass_kg,
        "never",
        f9_vehicle.screening_isp_s,
    )
    target = _dv_independent(PAYLOAD, carry_fairing=True) - 77.0
    expect = (
        brentq(
            lambda p: _dv_independent(p, carry_fairing=True) - target,
            PAYLOAD,
            10 * PAYLOAD,
            xtol=1e-12,
            rtol=1e-15,
        )
        - PAYLOAD
    )
    got = payload_gain_kg(carried, 77.0)
    assert math.isclose(got, expect, rel_tol=1e-6)
    assert abs(got - 740.0) < 10.0


def test_screening_needs_isps() -> None:
    engine = Engine(thrust_vac_N=1.0e4, isp_vac_s=300.0)
    stage = Stage("s", 100.0, 900.0, engine, 1, Startup("step"))
    bare = Vehicle(stages=(stage,))
    with pytest.raises(ValueError, match="screening_isp_s"):
        ideal_dv_mps(bare)
    with pytest.raises(ValueError, match="one entry per stage"):
        Vehicle(stages=(stage,), screening_isp_s=(300.0, 300.0))


def test_screening_isp_must_be_positive(two_stage_toy: Vehicle) -> None:
    v = two_stage_toy
    for bad in ((-5.0, 300.0), (0.0, 300.0)):
        with pytest.raises(ValueError, match="> 0"):
            Vehicle(v.stages, v.fairing_mass_kg, v.payload_mass_kg, "staging", bad)
