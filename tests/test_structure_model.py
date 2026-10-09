"""The structural station model of both stages (SP7 step S2; docs/physics.md, "Structural
sizing of the push load (first order)", from "The station model"; design 4.2 to 4.2.5).

Inputs are the committed structure file, the gate vehicle file and synthetic pad flights
built in tests/structure_support.py from closed forms (never results/); no offload is
solved (D-SP7-31): every test sizes only. Expected values are hand arithmetic written out
here, the source note's tables (docs/phases/inputs/2026-10-08-SP7-sources.md, sections
named in each test) or an independent evaluation (``structure.envelope_reference``, S1's
scalar primitives on every case at every station).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import math
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd
import pytest

from launchsim import sim
from launchsim import structure as st
from launchsim.constants import G0_MPS2, P_SEA_LEVEL_PA


def _load_support() -> ModuleType:
    """tests/structure_support.py, loaded by path (any pytest import mode)."""
    name = "structure_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ss = _load_support()

REL = 1e-12
"""Relative tolerance of the reduced envelope against the full sample and of closed forms."""


@pytest.fixture(scope="module")
def cfg() -> Any:
    """The gate structure file."""
    return ss.structure_config()


@pytest.fixture(scope="module")
def veh() -> Any:
    """The gate vehicle at the reference payload."""
    return ss.vehicle()


@pytest.fixture(scope="module")
def coarse(cfg: Any, veh: Any) -> tuple[Any, Any]:
    """A coarse synthetic pad (rows every 3 s) and a 30-station layout, for the full-sample
    comparisons."""
    layout = dataclasses.replace(cfg.stack_layout(), stations_per_barrel=30)
    result = ss.synthetic_pad_result(veh, dt_s=3.0)
    return layout, st.pad_load_set(sim.structure_pad_cases(result, veh, layout))


@pytest.fixture(scope="module")
def pad(cfg: Any, veh: Any) -> Any:
    """The synthetic pad at 0.5 s and the file's layout."""
    result = ss.synthetic_pad_result(veh, dt_s=0.5)
    return st.pad_load_set(sim.structure_pad_cases(result, veh, cfg.stack_layout()))


def _coefficient_sets(cfg: Any) -> dict[str, Any]:
    """Central, every range at its low end, every range at its high end, a set where the
    combined mode governs RP-1 envelope stations, and three seeded random sets."""
    ranges = cfg.coefficient_ranges()

    def end(r: Any, high: bool) -> Any:
        if r.kind == "discrete":
            return r.choices[-1 if high else 0]
        return r.high if high else r.low

    sets = {
        "central": cfg.coefficients(),
        "low": cfg.coefficients(overrides={r.path: end(r, False) for r in ranges}),
        "high": cfg.coefficients(overrides={r.path: end(r, True) for r in ranges}),
        "combined": cfg.coefficients(
            overrides={
                "pressures.stage1_rp1.p_meop_bar": 4.0,
                "pressures.stage1_rp1.p_min_fraction": 0.93,
                "buckling.k_stiff": 0.75,
                "materials.E_GPa": 79.6,
            }
        ),
    }
    rng = np.random.default_rng(20261008)
    for k in range(3):
        over: dict[str, Any] = {}
        for r in ranges:
            if r.kind == "continuous":
                over[r.path] = float(rng.uniform(r.low, r.high))
            elif r.kind == "integer":
                over[r.path] = int(rng.integers(r.low, r.high + 1))
            else:
                over[r.path] = r.choices[int(rng.integers(0, len(r.choices)))]
        sets[f"random{k}"] = cfg.coefficients(overrides=over)
    return sets


# ------------------------------------------------------------------ the envelope


def test_reduced_envelope_equals_the_full_sample(cfg: Any, veh: Any, coarse: Any) -> None:
    """``build_envelope`` (each single-driver mode at its driver's exact maximum, the
    combined mode by the exact block bound) equals ``envelope_reference`` (S1's scalar
    primitives on every case at every station) to 1e-12 relative at every station of every
    element of both stages, on seven coefficient sets (central, all low, all high, one where
    the combined mode governs RP-1 envelope stations, three random), with and without a 10%
    margin and a 4.5 g0 cap; the combined set does exercise the combined mode."""
    layout, pad_set = coarse
    masses = sim.stack_masses(veh)
    sets = _coefficient_sets(cfg)
    assert len(sets) >= 6
    combined_seen = False
    for name, coeffs in sets.items():
        geometry = st.build_geometry(masses, layout, coeffs)
        for margin, cap in ((0.0, None), (0.1, 4.5)):
            fast = st.build_envelope(geometry, coeffs, pad_set, margin=margin, envelope_cap_g=cap)
            full = st.envelope_reference(
                geometry, coeffs, pad_set, margin=margin, envelope_cap_g=cap
            )
            for stage in st.STAGE_ROLES:
                for element in (fast.stage1 if stage == st.STAGE1 else fast.stage2) or {}:
                    a = fast.element(stage, element).t_m
                    b = full.element(stage, element).t_m
                    np.testing.assert_allclose(
                        a, b, rtol=REL, atol=0.0, err_msg=f"{name} {element}"
                    )
                    combined_seen |= st.MODE_COMBINED in fast.element(stage, element).modes
            assert fast.upper_stack_nu_kg == full.upper_stack_nu_kg
            assert fast.skirt_load_N == full.skirt_load_N
    assert combined_seen


def test_envelope_margin_scales_loads_not_thickness(cfg: Any, veh: Any, coarse: Any) -> None:
    """Margin multiplies the envelope's loads and pressures (D-SP7-15): the hoop-governed
    stations' thickness grows by exactly the margin factor only where the relief is
    absent (hoop: t proportional to p), the skirt's load and the upper stack's n U by 1 +
    margin, and the cap lowers the stage-1 n U to cap x U."""
    layout, pad_set = coarse
    coeffs = cfg.coefficients()
    geometry = st.build_geometry(sim.stack_masses(veh), layout, coeffs)
    plain = st.build_envelope(geometry, coeffs, pad_set)
    raised = st.build_envelope(geometry, coeffs, pad_set, margin=0.25)
    assert math.isclose(raised.skirt_load_N, 1.25 * plain.skirt_load_N, rel_tol=REL)
    assert math.isclose(raised.upper_stack_nu_kg, 1.25 * plain.upper_stack_nu_kg, rel_tol=REL)
    assert raised.upper_stack_nu_pad_kg == plain.upper_stack_nu_pad_kg
    fwd_plain = plain.element(st.STAGE1, st.FORWARD_DOME).t_m[0]
    fwd_raised = raised.element(st.STAGE1, st.FORWARD_DOME).t_m[0]
    if plain.element(st.STAGE1, st.FORWARD_DOME).modes[0] == st.MODE_MEMBRANE:
        assert math.isclose(fwd_raised, 1.25 * fwd_plain, rel_tol=REL)
    capped = st.build_envelope(geometry, coeffs, pad_set, envelope_cap_g=4.0)
    upper = pad_set.cases[pad_set.meco_case].upper_mass_stage1_kg
    assert math.isclose(capped.upper_stack_nu_kg, 4.0 * upper, rel_tol=REL)
    with pytest.raises(ValueError):
        st.build_envelope(geometry, coeffs, pad_set, envelope_cap_g=1.0)
    with pytest.raises(ValueError):
        st.build_envelope(geometry, coeffs, pad_set, margin=-0.1)


def _as_push(case: st.LoadCase, interface_N: float) -> st.PushLoad:
    """A pad case recast as a quasi-static push resting at its own load (n_rest = n,
    F_rest = F), so its peak is the case itself."""
    values = {k: getattr(case, k) for k in case.__dataclass_fields__}
    values.update(kind=st.PUSH, interface_force_N=interface_N, hold_down_support_N=None)
    push_case = st.LoadCase(**values)
    return st.PushLoad(
        cases=(push_case,),
        n_rest_g=push_case.n_g,
        f_rest_N=interface_N,
        ramp=None,
        rise_time_s=None,
        release=st.ReleaseState(push_case.n_g, push_case.n_g, push_case),
    )


def test_pad_own_cases_give_zero_increment(cfg: Any, veh: Any, pad: Any) -> None:
    """The pad's own load cases, sized as pushes, add exactly 0.000 kg (design 4.2: zero
    inside the envelope, by construction): HOLD rows (the interface force their hold-down
    support), the liftoff, mid-burn and MECO rows (no interface force) through the thrust
    structure; through the aft ring every element but the ring frame is 0.0 and the ring
    (new hardware, no envelope credit) is its own sized mass x nof_barrel x nof_entry_ratio.
    Stage 2's tanks against the stage-2 cases of the envelope give 0.0 too."""
    coeffs = cfg.coefficients()
    layout = cfg.stack_layout()
    geometry = st.build_geometry(sim.stack_masses(veh), layout, coeffs)
    envelope = st.build_envelope(geometry, coeffs, pad)
    picks = [
        int(pad.hold_cases[0]),
        int(pad.hold_cases[-1]),
        int(pad.stage1_cases[len(pad.hold_cases)]),
        int(pad.stage1_cases[len(pad.stage1_cases) // 2]),
        pad.meco_case,
    ]
    for i in picks:
        case = pad.cases[i]
        interface = case.hold_down_support_N if case.kind == st.HOLD else 0.0
        push = _as_push(case, interface)
        through_ts = st.size_increment(
            geometry, coeffs, envelope, push, dynamic="quasi_static", entry="thrust_structure"
        )
        assert through_ts.total_kg == 0.0, (
            case.label,
            [(e.element, e.kg) for e in through_ts.elements],
        )
        ring = st.size_increment(geometry, coeffs, envelope, push, dynamic="quasi_static")
        for element in ring.elements:
            if element.element != st.LOAD_RING:
                assert element.kg == 0.0, (case.label, element.element, element.kg)
        assert ring.ring is not None
        expected = coeffs.nof_barrel * coeffs.nof_entry_ratio * ring.ring.mass_kg
        assert ring.ring_kg == expected
        assert (ring.ring_kg > 0.0) == (interface > 0.0)
        assert ring.stage2_sized is False
        req = st.push_requirement(push, coeffs, "quasi_static")
        stage2 = st._stage_tank_increments(st.STAGE2, geometry.stage2, envelope, req, coeffs)
        assert all(e.kg == 0.0 for e in stage2), case.label


def test_doubling_the_stations_moves_dm_by_less_than_0p1_kg(cfg: Any, veh: Any, pad: Any) -> None:
    """Doubling the stations (200 to 400 per barrel and skirt) moves dm by less than 0.1 kg
    (design 4.2; source note section 2.3): the headline push at central (rise_time), the
    step row (stage 2 sized; the RP-1 barrel's factor switches between nof_stiffened and
    nof_barrel along it, the cell split at the switch), and the plate-limited row."""
    masses = sim.stack_masses(veh)
    layout = cfg.stack_layout()
    push = ss.headline_push(veh, layout)
    assert layout.stations_per_barrel == 200
    cases = (
        ({}, "rise_time"),
        ({}, "step"),
        ({"buckling.gerard_row": "plate_limited"}, "rise_time"),
    )
    for overrides, dynamic in cases:
        coeffs = cfg.coefficients(overrides=overrides)
        coarse_dm = st.size(masses, layout, coeffs, pad, push, dynamic=dynamic).total_kg
        fine = dataclasses.replace(layout, stations_per_barrel=400)
        fine_dm = st.size(masses, fine, coeffs, pad, push, dynamic=dynamic).total_kg
        assert coarse_dm > 0.0
        assert abs(fine_dm - coarse_dm) < 0.1, (overrides, dynamic, coarse_dm, fine_dm)


# ------------------------------------------------------------------ the adapters


def _hand_result(veh: Any) -> sim.Result:
    """A six-row planar Result with hand-chosen n, m and thrust: two HOLD rows, three
    stage-1 flight rows (the last at depletion) and one stage-2 burn row (fairing gone)."""
    s1, s2 = veh.stages
    upper = s2.wet_mass_kg + veh.fairing_mass_kg + veh.payload_mass_kg
    full = s1.wet_mass_kg + upper
    rows = [
        (-2.0, "HOLD", "stage1", 0.996476, full, 0.0),
        (0.0, "HOLD", "stage1", 0.996476, full - 2000.0, 7.6e6),
        (0.0, "VERTICAL_RISE", "stage1", 1.36, full - 2000.0, 7.6e6),
        (80.0, "GRAVITY_TURN", "stage1", 2.3, full - 220_000.0, 8.17e6),
        (150.0, "GRAVITY_TURN", "stage1", 5.2, s1.dry_mass_kg + upper, 8.227e6),
        (200.0, "LTG_BURN", "stage2", 1.0, s2.dry_mass_kg + veh.payload_mass_kg + 50_000.0, 9.81e5),
    ]
    ts = pd.DataFrame(rows, columns=["t_s", "phase", "stage", "felt_axial_g", "m_kg", "thrust_N"])
    events = pd.DataFrame(
        [
            {
                "t_s": 150.0,
                "event": "propellant",
                "phase": "GRAVITY_TURN",
                "stage": "stage1",
                "m_kg": s1.dry_mass_kg + upper,
            },
            {
                "t_s": 150.0,
                "event": "staging",
                "phase": "COAST_STAGING",
                "stage": "stage2",
                "m_kg": upper,
            },
            {
                "t_s": 190.0,
                "event": "fairing",
                "phase": "LTG_BURN",
                "stage": "stage2",
                "m_kg": 120_000.0,
            },
        ]
    )
    return sim.Result(
        metrics={},
        timeseries=ts,
        loss_budget=None,
        assist_budget=None,
        assumptions=[],
        phases=[],
        status="inserted",  # type: ignore[arg-type]
        flags=[],
        events=events,
        model="planar_2d",
    )


def test_station_products_of_survey_05(cfg: Any, veh: Any) -> None:
    """Survey 05's station products recomputed from a synthetic Result against hand
    arithmetic: U = stage 2 wet + fairing + payload, the stage-1 propellant m - dry1 - U
    split by the mixture fraction, and n U, n (U + LOX), n (U + LOX + RP-1), n LOX, n RP-1
    on every stage-1 row; the model's own drivers (``aq_lox``, ``aq_rp1``, ``aq_skirt``,
    ``am_lox``, ``am_rp1``) are those products; the hold-down support m n g0 - T on the
    HOLD rows; the stage-2 row's propellant m - dry2 - payload (the fairing gone)."""
    layout = cfg.stack_layout()
    result = _hand_result(veh)
    cases = sim.structure_pad_cases(result, veh, layout)
    assert [c.kind for c in cases] == ["hold", "hold", "flight", "flight", "flight", "flight"]
    s1, s2 = veh.stages
    upper = s2.wet_mass_kg + veh.fairing_mass_kg + veh.payload_mass_kg
    f1 = layout.stage1.lox_mass_fraction
    pad_set = st.pad_load_set(cases)
    feats = pad_set.features(st.STAGE1, None).arrays
    for j, row in enumerate(result.timeseries.itertuples(index=False)):
        if row.stage != "stage1":
            continue
        n, m = row.felt_axial_g, row.m_kg
        prop = m - s1.dry_mass_kg - upper
        lox, rp1 = f1 * prop, prop - f1 * prop
        case = cases[j]
        assert case.upper_mass_stage1_kg == upper
        assert math.isclose(case.lox_stage1_kg, lox, rel_tol=REL, abs_tol=1e-9)
        assert math.isclose(case.rp1_stage1_kg, rp1, rel_tol=REL, abs_tol=1e-9)
        products = {
            "aq_lox": n * upper,
            "aq_rp1": n * (upper + lox),
            "aq_skirt": n * (upper + lox + rp1),
            "am_lox": n * lox,
            "am_rp1": n * rp1,
        }
        for name, value in products.items():
            assert math.isclose(feats[name][j], value, rel_tol=REL, abs_tol=1e-9), (j, name)
        if row.phase == "HOLD":
            assert math.isclose(
                case.hold_down_support_N, m * n * G0_MPS2 - row.thrust_N, rel_tol=REL
            )
    last = cases[-1]
    assert not last.stage1_attached
    prop2 = 50_000.0
    assert math.isclose(last.lox_stage2_kg + last.rp1_stage2_kg, prop2, rel_tol=REL)
    assert last.upper_mass_stage2_kg == veh.payload_mass_kg
    assert cases[4].lox_stage1_kg == 0.0 and cases[4].rp1_stage1_kg == 0.0


def test_adapter_refuses_a_mismatched_vehicle_or_a_push(cfg: Any, veh: Any) -> None:
    """The adapter refuses a vehicle that is not the one the Result flew (first mass), a
    Result with ASSIST rows and a 1-D Result."""
    layout = cfg.stack_layout()
    result = _hand_result(veh)
    other = ss.vehicle(payload_kg=ss.P_REF_KG + 100.0)
    with pytest.raises(ValueError, match="first mass"):
        sim.structure_pad_cases(result, other, layout)
    ts = result.timeseries.copy()
    ts.loc[2, "phase"] = "ASSIST"
    with pytest.raises(ValueError, match="push"):
        sim.structure_pad_cases(dataclasses.replace(result, timeseries=ts), veh, layout)
    with pytest.raises(ValueError, match="planar"):
        sim.structure_pad_cases(dataclasses.replace(result, model="vertical_1d"), veh, layout)


def test_constant_accel_push_load_cold_and_hot(cfg: Any, veh: Any) -> None:
    """The analytic constant_accel push (design 4.4): cold, n = (a + g_eff)/g0 and F_int =
    m_v (a + g_eff) on the vertical track, the contents at push start, n_rest g_eff/g0 and
    F_rest m_v g_eff, the release from n to 0; hot (lit 2 s before the push start, the
    vehicle's 2 s ramp), F_int = m_v(0) (a + g_eff) - T(0) (its largest over the push),
    the contents less the burn up to the push start, F_rest m_v(0) g_eff - T(0), and the
    release to T/(m_v g0)."""
    layout = cfg.stack_layout()
    a = 3.0 * G0_MPS2
    g = ss.G_EFF_MPS2
    push = ss.headline_push(veh, layout)
    case = push.cases[0]
    m_v = veh.stack_mass_kg(0) - ss.HEADLINE_OFFLOAD_KG
    assert case.n_g == (a + g) / G0_MPS2
    assert math.isclose(case.interface_force_N, m_v * (a + g), rel_tol=REL)
    assert math.isclose(
        case.lox_stage1_kg + case.rp1_stage1_kg, 410_900.0 - ss.HEADLINE_OFFLOAD_KG, rel_tol=REL
    )
    assert math.isclose(push.n_rest_g, g / G0_MPS2, rel_tol=REL)
    assert math.isclose(push.f_rest_N, m_v * g, rel_tol=REL)
    assert push.release.n_after_g == 0.0 and push.release.n_before_g == case.n_g
    assert push.ramp is not None and math.isclose(
        push.ramp.exit_speed_mps**2, 2.0 * a * 100.0, rel_tol=REL
    )
    hot = ss.headline_push(veh, layout, offload_kg=0.0, stage1_ignition_s=-2.0)
    s1 = veh.stages[0]
    mdot = s1.thrust_vac_total_N / (G0_MPS2 * s1.engine.isp_vac_s)
    burned0 = mdot * 2.0 / 2.0  # the 2 s linear ramp, complete at the push start
    thrust0 = s1.thrust_vac_total_N - P_SEA_LEVEL_PA * s1.exit_area_total_m2
    m0 = veh.stack_mass_kg(0) - burned0
    hot_case = hot.cases[0]
    assert math.isclose(hot_case.interface_force_N, m0 * (a + g) - thrust0, rel_tol=REL)
    assert math.isclose(hot_case.vehicle_mass_kg, m0, rel_tol=REL)
    assert math.isclose(hot.f_rest_N, m0 * g - thrust0, rel_tol=REL)
    t_push = math.sqrt(2.0 * 100.0 / a)
    m_rel = m0 - mdot * t_push
    assert math.isclose(hot.release.n_after_g, thrust0 / (m_rel * G0_MPS2), rel_tol=REL)


def test_push_requirement_against_the_closed_forms(cfg: Any, veh: Any) -> None:
    """n_peak = n_rest + DLF (n_q - n_rest) and F_peak likewise (S1's dynamic_load_factor
    and peak_load; design 4.2.1): under rise_time the plateau is raised by a' - a, a' the
    ramped plateau at t_r 0.5 s (central) and DLF 1 + T/(pi t_r) at 5 Hz (1.1273); under
    quasi_static the plain plateau at DLF 1; under step DLF 2 (0.9965 + 2 x 3.0 = 6.9965 g0,
    the source note's 7.0 g0). The cold release (n_after 0) swings from the release's peak,
    n_rest + DLF (n_q - n_rest), the ramp's undamped residual included, to minus that peak
    (D-SP7-39), and from the plateau to -n_q (printed beside); under step from -6.9965 g0."""
    coeffs = cfg.coefficients()
    layout = cfg.stack_layout()
    push = ss.headline_push(veh, layout)
    a, g = 3.0 * G0_MPS2, ss.G_EFF_MPS2
    v_e = math.sqrt(2.0 * a * 100.0)
    t_r = 0.5
    a_p = (100.0 - math.sqrt(100.0**2 - v_e**2 * t_r**2 / 12.0)) / (t_r**2 / 12.0)
    dlf = 1.0 + (1.0 / 5.0) / (math.pi * t_r)
    req = st.push_requirement(push, coeffs, "rise_time")
    n_rest = g / G0_MPS2
    n_q = (a_p + g) / G0_MPS2
    assert math.isclose(req.dlf, dlf, rel_tol=REL) and round(req.dlf, 4) == 1.1273
    assert math.isclose(req.n_quasi_g, n_q, rel_tol=1e-11)
    assert math.isclose(req.n_peak_g, n_rest + dlf * (n_q - n_rest), rel_tol=1e-11)
    m_v = push.cases[0].vehicle_mass_kg
    assert math.isclose(req.f_peak_N, m_v * g + dlf * (m_v * (a_p + g) - m_v * g), rel_tol=1e-11)
    assert math.isclose(req.ramp_cost_rel, (a_p - a) / a, rel_tol=1e-9)
    peak_rel = n_rest + dlf * (n_q - n_rest)
    assert math.isclose(req.release_n_before_g, n_q, rel_tol=1e-11)
    assert math.isclose(req.release_n_peak_g, peak_rel, rel_tol=1e-11)
    assert req.release_n_after_g == 0.0
    assert math.isclose(req.release_swing_g, -peak_rel, rel_tol=1e-11)
    assert math.isclose(req.release_swing_plateau_g, -n_q, rel_tol=1e-11)
    assert req.release_swing_g < req.release_swing_plateau_g
    qs = st.push_requirement(push, coeffs, "quasi_static")
    assert qs.dlf == 1.0 and qs.accel_raise_mps2 == 0.0
    assert math.isclose(qs.n_peak_g, push.cases[0].n_g, rel_tol=1e-15)
    assert math.isclose(qs.release_swing_g, qs.release_swing_plateau_g, rel_tol=1e-15)
    step = st.push_requirement(push, coeffs, "step")
    assert math.isclose(step.n_peak_g, n_rest + 2.0 * 3.0, rel_tol=1e-12)
    assert round(step.n_peak_g, 4) == 6.9965
    assert math.isclose(step.release_swing_g, -step.n_peak_g, rel_tol=1e-12)
    assert math.isclose(step.release_swing_plateau_g, -(n_rest + 3.0), rel_tol=1e-12)


# ------------------------------------------------------------------ monotone, flags


def test_dm_is_non_decreasing_in_n_and_in_the_propellant(cfg: Any, veh: Any, pad: Any) -> None:
    """dm never falls as the push's net acceleration rises (1.0 to 6.0 g0 over the 100 m
    stroke) or as the propellant on board rises (offload 80 t down to 0)."""
    coeffs = cfg.coefficients()
    layout = cfg.stack_layout()
    masses = sim.stack_masses(veh)
    by_n = [
        st.size(masses, layout, coeffs, pad, ss.headline_push(veh, layout, net_accel_g=x)).total_kg
        for x in np.linspace(1.0, 6.0, 11)
    ]
    assert np.all(np.diff(by_n) >= 0.0), by_n
    by_prop = [
        st.size(masses, layout, coeffs, pad, ss.headline_push(veh, layout, offload_kg=x)).total_kg
        for x in np.linspace(80_000.0, 0.0, 9)
    ]
    assert np.all(np.diff(by_prop) >= 0.0), by_prop
    assert by_n[-1] > by_n[0] > 0.0


def test_flags_against_hand_thresholds(cfg: Any, veh: Any, pad: Any) -> None:
    """The flags of design 4.2.2 against hand thresholds on quasi-static cold pushes (DLF 1:
    the release swings from the plateau n to -n): the upper stack is exceeded exactly when
    n U passes the pad's largest n U (MECO's, at n_MECO U), and then stage 2 is sized; the
    payload limit fires when the release swing -n goes below -2.0 g0 or n above 6.0 g0; the
    release flag (D-SP7-39) with the model's head to the dome's crown: the LOX bottom's
    minimum gauge pressure p_min,LOX - g0 n (m_LOX + rho_LOX A b)/A, its absolute value at
    the sea-level release p_atm + that (negative: the column separates), MECO's gauge value
    at its own swing -n_MECO, the same three for both stage-2 tanks (recorded, not fired
    on), the common dome's reverse pressure p_MEOP,RP1 - max(p_min,LOX + that head, -p_atm)
    (the LOX side floored at zero absolute; MECO's floor at its zero ambient), positive
    already at zero swing (p_MEOP,RP1 > p_min,LOX at the central pair) and on the pad's own
    MECO, so it fires only above MECO's; at a 5 g0 swing the floor binds and the reverse
    pressure is exactly p_MEOP,RP1 + p_atm."""
    coeffs = cfg.coefficients()
    layout = cfg.stack_layout()
    masses = sim.stack_masses(veh)
    meco = pad.cases[pad.meco_case]
    g = ss.G_EFF_MPS2

    def size_at(n_target: float, dynamic: str = "quasi_static") -> Any:
        push = ss.headline_push(veh, layout, net_accel_g=(n_target * G0_MPS2 - g) / G0_MPS2)
        return st.size(masses, layout, coeffs, pad, push, dynamic=dynamic)

    below = size_at(meco.n_g * (1.0 - 1e-6))
    above = size_at(meco.n_g * (1.0 + 1e-6))
    assert not below.flag(st.FLAG_UPPER_STACK).fired and not below.stage2_sized
    assert above.flag(st.FLAG_UPPER_STACK).fired and above.stage2_sized
    assert math.isclose(
        above.flag(st.FLAG_UPPER_STACK).value("pad_n_upper_N"),
        meco.n_g * meco.upper_mass_stage1_kg * G0_MPS2,
        rel_tol=REL,
    )
    small, large = size_at(1.9), size_at(2.1)
    assert not small.flag(st.FLAG_PAYLOAD_LIMIT).fired
    assert large.flag(st.FLAG_PAYLOAD_LIMIT).fired
    assert size_at(6.05).flag(st.FLAG_PAYLOAD_LIMIT).value("n_peak_g") > 6.0
    release = large.flag(st.FLAG_RELEASE_UNLOAD)
    rel_case = large.requirement.release_case
    area = math.pi * 1.83**2
    depth = 1.83 / coeffs.dome_axis_ratio

    def head(n: float, m: float, rho: float) -> float:
        return G0_MPS2 * n * (m + rho * area * depth) / area

    p_min_lox = coeffs.p_min_pa("stage1", "lox")
    lox = p_min_lox - head(2.1, rel_case.lox_stage1_kg, coeffs.rho_lox_kgm3)
    rp1 = coeffs.p_min_pa("stage1", "rp1") - head(2.1, rel_case.rp1_stage1_kg, coeffs.rho_rp1_kgm3)
    assert math.isclose(release.value("lox_bottom_pressure_min_gauge_pa"), lox, rel_tol=1e-9)
    assert math.isclose(release.value("rp1_bottom_pressure_min_gauge_pa"), rp1, rel_tol=1e-9)
    assert math.isclose(
        release.value("lox_bottom_pressure_min_abs_pa"), P_SEA_LEVEL_PA + lox, rel_tol=1e-9
    )
    assert release.value("release_p_amb_pa") == P_SEA_LEVEL_PA
    assert release.value("meco_swing_g") == -meco.n_g
    meco_lox = p_min_lox - head(meco.n_g, meco.lox_stage1_kg, coeffs.rho_lox_kgm3)
    assert math.isclose(
        release.value("meco_lox_bottom_pressure_min_gauge_pa"), meco_lox, rel_tol=1e-9
    )
    for tank, rho in (("lox", coeffs.rho_lox_kgm3), ("rp1", coeffs.rho_rp1_kgm3)):
        p_min2 = coeffs.p_min_pa("stage2", tank)
        m_rel = getattr(rel_case, f"{tank}_stage2_kg")
        m_meco = getattr(meco, f"{tank}_stage2_kg")
        gauge2 = p_min2 - head(2.1, m_rel, rho)
        assert math.isclose(
            release.value(f"stage2_{tank}_bottom_pressure_min_gauge_pa"), gauge2, rel_tol=1e-9
        )
        assert math.isclose(
            release.value(f"stage2_{tank}_bottom_pressure_min_abs_pa"),
            P_SEA_LEVEL_PA + gauge2,
            rel_tol=1e-9,
        )
        assert math.isclose(
            release.value(f"meco_stage2_{tank}_bottom_pressure_min_gauge_pa"),
            p_min2 - head(meco.n_g, m_meco, rho),
            rel_tol=1e-9,
        )
    p_meop_rp1 = coeffs.p_meop_pa("stage1", "rp1")
    reverse = p_meop_rp1 - max(lox, -P_SEA_LEVEL_PA)
    reverse_meco = p_meop_rp1 - max(meco_lox, 0.0)
    assert math.isclose(release.value("common_dome_reverse_pressure_pa"), reverse, rel_tol=1e-9)
    assert math.isclose(
        release.value("meco_common_dome_reverse_pressure_pa"), reverse_meco, rel_tol=1e-9
    )
    assert p_meop_rp1 - p_min_lox > 0.0 and reverse_meco > 0.0
    assert release.fired == (
        P_SEA_LEVEL_PA + lox < 0.0
        or P_SEA_LEVEL_PA + rp1 < 0.0
        or reverse > max(0.0, reverse_meco)
        or abs(release.value("upper_stack_swing_N"))
        > abs(release.value("meco_upper_stack_swing_N"))
    )
    deep = size_at(5.0).flag(st.FLAG_RELEASE_UNLOAD)
    assert deep.value("lox_bottom_pressure_min_abs_pa") < 0.0
    assert deep.value("common_dome_reverse_pressure_pa") == p_meop_rp1 + P_SEA_LEVEL_PA


def test_release_swings_from_the_release_peak(cfg: Any, veh: Any, pad: Any) -> None:
    """D-SP7-39: under the undamped single mode the release starts from n_rest + DLF (n_q -
    n_rest), not from the plateau. At the step row (DLF 2) a cold push at a 1.5 g0 plateau
    swings to -(2 x 1.5 - n_rest) = -2.0035 g0 (the plateau's -1.5 g0 printed beside), so the
    payload-limit flag fires on the peak swing though the plateau's would not; the release
    flag's numbers use the same swing."""
    coeffs = cfg.coefficients()
    layout = cfg.stack_layout()
    masses = sim.stack_masses(veh)
    g = ss.G_EFF_MPS2
    n_rest = g / G0_MPS2
    push = ss.headline_push(veh, layout, net_accel_g=(1.5 * G0_MPS2 - g) / G0_MPS2)
    inc = st.size(masses, layout, coeffs, pad, push, dynamic="step")
    req = inc.requirement
    assert math.isclose(req.release_n_peak_g, 2.0 * 1.5 - n_rest, rel_tol=1e-12)
    assert math.isclose(req.release_swing_g, -(2.0 * 1.5 - n_rest), rel_tol=1e-12)
    assert math.isclose(req.release_swing_plateau_g, -1.5, rel_tol=1e-12)
    assert round(req.release_swing_g, 4) == -2.0035
    payload = inc.flag(st.FLAG_PAYLOAD_LIMIT)
    assert payload.fired and payload.value("n_peak_g") < 6.0
    assert payload.value("release_swing_plateau_g") > -2.0 > payload.value("release_swing_g")
    release = inc.flag(st.FLAG_RELEASE_UNLOAD)
    assert release.value("release_swing_g") == req.release_swing_g
    assert release.value("release_n_peak_g") == req.release_n_peak_g


# ------------------------------------------------------------------ relations and the ring


def test_interstage_rule_against_section_5_5(cfg: Any) -> None:
    """The interstage (source note section 5.5): Castellini's relation at 4.5 m, 3.66 m and
    k_SM 0.7 is 934 kg (207.7 kg per metre); at n_peak 7.0 against MECO's 5.195 g0 the
    increment is 934 x (1.347^0.6 - 1) = 183 kg, and exponent 1 gives 1.77 times that;
    inside the envelope it is 0."""
    coeffs = cfg.coefficients()
    m_is = st.interstage_mass_kg(
        4.5, 3.66, coeffs.interstage_k1_kg_per_m2p4856, coeffs.interstage_k2, coeffs.interstage_k_sm
    )
    expected = 0.7 * 13.740 * (math.pi * 3.66 * 4.5) * 3.66**0.4856
    assert math.isclose(m_is, expected, rel_tol=REL)
    assert round(m_is) == 934 and round(m_is / 4.5, 1) == 207.7
    inc = st.interstage_increment_kg(m_is, 7.0, 5.195, 0.6)
    assert math.isclose(inc, m_is * ((7.0 / 5.195) ** 0.6 - 1.0), rel_tol=REL)
    assert round(inc) == 183
    linear = st.interstage_increment_kg(m_is, 7.0, 5.195, 1.0)
    assert round(linear / inc, 2) == 1.77
    assert st.interstage_increment_kg(m_is, 5.0, 5.195, 0.6) == 0.0


def test_thrust_structure_row(cfg: Any) -> None:
    """k_ts max(0, F - T_env) = k_ts T_max max(0, F/T_max - 1) (design 4.2.3): 0.2805
    kg/kN x (20,815 - 8,226.9) kN = 3,531 kg; 0 below T_max."""
    k = cfg.coefficients().k_ts_kg_per_n
    assert math.isclose(k, 0.2805e-3, rel_tol=REL)
    got = st.thrust_structure_increment_kg(k, 20.815e6, 8.2269e6)
    assert math.isclose(got, 0.2805e-3 * 8.2269e6 * (20.815e6 / 8.2269e6 - 1.0), rel_tol=1e-12)
    assert round(got) == 3531
    assert st.thrust_structure_increment_kg(k, 8.0e6, 8.2269e6) == 0.0


RING_TABLE = (
    (3, 1.0, 0.42, None),
    (3, 6.5, 1.54, 1.36),
    (3, 12.0, 2.58, 1.94),
    (4, 1.0, 0.37, None),
    (4, 6.5, 1.23, 1.16),
    (4, 12.0, 2.02, 1.65),
    (6, 1.0, 0.33, None),
    (6, 6.5, 0.96, None),
    (6, 12.0, 1.51, 1.36),
    (8, 1.0, 0.33, None),
    (8, 6.5, 0.85, None),
    (8, 12.0, 1.28, 1.21),
    (12, 1.0, 0.36, None),
    (12, 6.5, 0.78, None),
    (12, 12.0, 1.09, 1.08),
    (16, 1.0, 0.40, None),
    (16, 6.5, 0.78, None),
    (16, 12.0, 1.04, 1.04),
)
"""The source note's section 11 table: (N_p, h/b, peak shear over F_tu/sqrt(3), the mass
factor a section of the same h/b needs to pass it) at the headline's quasi-static 20,815 kN,
FS_u 1.4, fitting factor 1.15, F_tu 558.5 MPa, r 1.83 m."""
RING_TABLE_TOL = 0.006
"""Agreement with the note's two-decimal table: half a unit of its last digit plus 0.001,
because two entries sit on a rounding boundary (4 pads, h/b 6.5: the closed form gives
1.2354, the note prints 1.23 and 1.24 at 520 MPa; 3 pads, h/b 12: 2.5850, printed 2.58)."""
RING_UNITY = ((3, 3.7), (4, 4.9), (6, 6.9), (8, 8.4), (12, 10.3), (16, 11.1))
"""The note's h/b at which the shear ratio reaches 1, per pad count (one decimal)."""


def test_ring_torsion_check_against_the_note_table() -> None:
    """The ring frame's torsion-plus-shear check (source note section 11; section 13 item
    15, D-SP7-37) reproduces the note's table to its two decimals: the ratio at S1's
    bending section, the mass factor of the sized section where it binds (the neutral axis
    governs the boundary's von Mises check there) and the h/b at which the ratio reaches 1;
    where it does not bind the ring is S1's bending ring. Saint-Venant's coefficients: a
    square's alpha 0.208 and beta 0.141, h = 2b's 0.246 and 0.229, and 1/3 as h/b grows."""
    from scipy.optimize import brentq

    args = (20.815e6, 1.83)
    for pads, k, ratio, factor in RING_TABLE:
        got = st.ring_shear_ratio(*args, pads, k, 1.4, 558.5e6, 1.15)
        assert abs(got - ratio) <= RING_TABLE_TOL, (pads, k, got)
        sized = st.ring_frame_section(*args, pads, k, 1.4, 558.5e6, 1.15, 2712.6)
        if factor is None:
            assert sized.governing == st.MODE_RING_BENDING
            assert sized.mass_kg == st.ring_frame_mass_kg(
                *args, pads, k, 1.4, 558.5e6, 1.15, 2712.6
            )
        else:
            assert sized.governing == st.MODE_RING_CHECK
            assert abs(sized.mass_kg / sized.mass_bending_kg - factor) <= RING_TABLE_TOL, (pads, k)
            assert math.isclose(sized.von_mises_ratio, sized.shear_ratio, rel_tol=1e-9)
    for pads, unity in RING_UNITY:
        k1 = brentq(
            lambda k, n=pads: st.ring_shear_ratio(*args, n, k, 1.4, 558.5e6, 1.15) - 1.0,
            1.0,
            20.0,
        )
        assert round(k1, 1) == unity, (pads, k1)
    beta, alpha, _ = st.rectangle_torsion_factors(1.0)
    assert round(alpha, 3) == 0.208 and round(beta, 3) == 0.141
    beta, alpha, _ = st.rectangle_torsion_factors(2.0)
    assert round(alpha, 3) == 0.246 and round(beta, 3) == 0.229
    beta, alpha, _ = st.rectangle_torsion_factors(1000.0)
    assert math.isclose(alpha, 1.0 / 3.0, rel_tol=1e-3) and math.isclose(
        beta, 1.0 / 3.0, rel_tol=1e-3
    )
    with pytest.raises(ValueError):
        st.rectangle_torsion_factors(0.5)


def test_ring_section_starts_from_s1s_bending_ring() -> None:
    """ring_frame_section's bending width is S1's (one shared helper): on 60 random rings
    2 pi r rho k b_bend^2 equals ring_frame_mass_kg to 1e-15 relative, as does the section's
    mass_bending_kg; a ring the check does not bind keeps S1's mass, one it binds is wider
    (b > b_bend) with 2 pi r rho k b^2."""
    rng = np.random.default_rng(11)
    for _ in range(60):
        f = float(rng.uniform(1e6, 6e7))
        r = float(rng.uniform(1.0, 3.0))
        pads = int(rng.integers(3, 17))
        k = float(rng.uniform(1.0, 14.0))
        fs, f_tu, fit, rho = 1.4, float(rng.uniform(4e8, 6e8)), 1.15, 2712.6
        sized = st.ring_frame_section(f, r, pads, k, fs, f_tu, fit, rho)
        s1 = st.ring_frame_mass_kg(f, r, pads, k, fs, f_tu, fit, rho)
        b_bend = sized.width_bending_m
        assert math.isclose(2.0 * math.pi * r * rho * k * b_bend**2, s1, rel_tol=1e-15)
        assert sized.mass_bending_kg == s1
        if sized.governing == st.MODE_RING_BENDING:
            assert sized.mass_kg == s1 and sized.width_m == b_bend
        else:
            assert sized.width_m > b_bend and sized.mass_kg > s1
            assert math.isclose(
                sized.mass_kg, 2.0 * math.pi * r * rho * k * sized.width_m**2, rel_tol=1e-15
            )


def test_vectorized_modes_equal_the_s1_primitives() -> None:
    """The envelope's array forms of hoop, Gerard and the combined mode equal S1's scalar
    primitives on 2,000 random points (1e-15 relative), the combined one sizing net
    compression only (N_d clamped at 0)."""
    rng = np.random.default_rng(5)
    p = rng.uniform(-1e5, 3e6, 2000)
    n_d = rng.uniform(-5e6, 4e7, 2000)
    r, fs, f_tu, eta, e, k_s = 1.83, 1.4, 558.5e6, 0.85, 75.84e9, 0.65
    hoop = st._hoop_array(p, r, fs, f_tu, eta, 2.0e4)
    vm = st._von_mises_array(p, n_d, r, fs, f_tu, eta)
    ger = st._gerard_array(n_d, r, e, k_s, st.GERARD_RING_COMMON_Z)
    for i in range(2000):
        assert math.isclose(
            hoop[i], st.hoop_thickness_m(p[i], r, fs, f_tu, eta, p_relief_pa=2.0e4), rel_tol=1e-15
        )
        assert math.isclose(
            vm[i], st.von_mises_thickness_m(p[i], r, max(n_d[i], 0.0), fs, f_tu, eta), rel_tol=1e-15
        )
        assert math.isclose(
            ger[i], st.gerard_stiffened_thickness_m(n_d[i], r, e, k_s, 6.48, 0.6), rel_tol=1e-15
        )


# ------------------------------------------------------------------ geometry, plausibility


def test_geometry_against_the_source_note(cfg: Any, veh: Any) -> None:
    """The station geometry at the central coefficients against the source note's section
    2.3-2.4 numbers: barrels 14.811 and 22.548 m (stage 1), 3.874 and 5.900 m (stage 2);
    dome depth 1.3725 m and area 17.637 m^2; the physical-length ratios 0.919 and 1.033;
    the implied stack 67.7 m (70 m less the 12.83 m budget plus the 6.045 m skirt and the
    4.5 m interstage); the stations' mass heights f (1 + u) m_full and the structure above
    them from the breakdown."""
    coeffs = cfg.coefficients()
    layout = cfg.stack_layout()
    geo = st.build_geometry(sim.stack_masses(veh), layout, coeffs)
    s1, s2 = geo.stage1, geo.stage2
    assert round(s1.rp1_barrel.length_m, 3) == 14.811 and round(s1.lox_barrel.length_m, 3) == 22.548
    assert round(s2.rp1_barrel.length_m, 3) == 3.874 and round(s2.lox_barrel.length_m, 3) == 5.900
    assert round(s1.dome_depth_m, 4) == 1.3725 and round(s1.dome_area_m2, 3) == 17.637
    assert round(s1.lox_length_physical_m / s1.lox_barrel.length_m, 3) == 0.919
    assert round(s1.rp1_length_physical_m / s1.rp1_barrel.length_m, 3) == 1.033
    assert round(st.implied_stack_length_m(geo, 13.2), 1) == 67.7
    lox = s1.lox_barrel
    f = (np.arange(200) + 0.5) / 200
    np.testing.assert_allclose(lox.mass_height_kg, f * (1.0345 * 0.69944 * 410_900.0), rtol=REL)
    np.testing.assert_allclose(lox.z_m, 6.045 + s1.rp1_barrel.length_m + f * lox.length_m, rtol=REL)
    top = 934.0 + 1000.0 + 221.0
    np.testing.assert_allclose(lox.structure_above_kg, top + 3245.0 * (1.0 - f), rtol=REL)
    np.testing.assert_allclose(
        s1.rp1_barrel.structure_above_kg, top + 3245.0 + 221.0 + 2131.0 * (1.0 - f), rtol=REL
    )
    assert s1.skirt_structure_above_kg == top + 3245.0 + 221.0 + 2131.0 + 221.0
    assert s2.lox_barrel.structure_above_kg[0] > 859.0 + 236.0
    assert s2.z_base_m == s1.top_z_m + 4.5


def test_plausibility_rule_and_its_widening(cfg: Any, veh: Any, pad: Any) -> None:
    """The plausibility rule (D-SP7-33 with the source note's section 7): R = 68.404
    V^0.75 on the combined volume (6,038 kg at central; 7,152 kg per tank), Akin's 4,903 kg,
    the interstage relation's 934 kg, stage 1 less its engines 17,970 kg; M_model the
    tank elements' envelope masses with their factors, the barrels on the physical lengths;
    the widening mechanical: a model below 0.7 R scales the high-mass end by 0.7 R/M, above
    1.3 R the low-mass end by 1.3 R/M, inside neither."""
    coeffs = cfg.coefficients()
    geo = st.build_geometry(sim.stack_masses(veh), cfg.stack_layout(), coeffs)
    env = st.build_envelope(geo, coeffs, pad)
    check = st.plausibility(geo, coeffs, env)
    volume = (287_400.0 / 1253.3 + 123_500.0 / 819.9) * 1.0345
    assert math.isclose(check.relation_kg, 68.404 * volume**0.75, rel_tol=1e-4)
    assert round(check.relation_kg) == 6038 and round(check.relation_per_tank_kg) == 7152
    assert round(check.akin_kg) == 4903 and round(check.interstage_relation_kg) == 934
    assert check.stage1_dry_less_engines_kg == 17_970.0
    assert math.isclose(check.m_model_kg, sum(kg for _, kg in check.element_kg), rel_tol=REL)
    lox_env = env.element("stage1", "lox_barrel")
    nof = [
        coeffs.nof_stiffened if m in st.STIFFENED_MODES else coeffs.nof_barrel
        for m in lox_env.modes
    ]
    lox_mass = sum(
        n * 2.0 * math.pi * 1.83 * coeffs.rho_wall_kgm3 * dz * t
        for n, dz, t in zip(nof, geo.stage1.lox_barrel.dz_m, lox_env.t_m, strict=True)
    )
    assert math.isclose(
        dict(check.element_kg)["lox_barrel"], lox_mass * check.lox_length_ratio, rel_tol=1e-12
    )
    assert st.plausibility_factors(6000.0, 6000.0, 0.3) == (1.0, 1.0)
    assert st.plausibility_factors(3000.0, 6000.0, 0.3) == (0.7 * 6000.0 / 3000.0, 1.0)
    assert st.plausibility_factors(9000.0, 6000.0, 0.3) == (1.0, 1.3 * 6000.0 / 9000.0)
    assert st.plausibility_factors(4200.0, 6000.0, 0.3) == (1.0, 1.0)  # 0.7 R = 4,200 kg
    low = dataclasses.replace(check, adverse_end_factor=1.4, favourable_end_factor=1.0)
    high = dataclasses.replace(check, adverse_end_factor=1.0, favourable_end_factor=0.8)
    assert st.widen_band(1000.0, 4000.0, low) == (1000.0, 4000.0 * 1.4)
    assert st.widen_band(1000.0, 4000.0, high) == (1000.0 * 0.8, 4000.0)
    if check.m_model_kg > check.upper_kg:
        assert math.isclose(
            check.favourable_end_factor, check.upper_kg / check.m_model_kg, rel_tol=REL
        )
        assert check.adverse_end_factor == 1.0
    elif check.m_model_kg < check.lower_kg:
        assert math.isclose(
            check.adverse_end_factor, check.lower_kg / check.m_model_kg, rel_tol=REL
        )
    else:
        assert check.adverse_end_factor == check.favourable_end_factor == 1.0


# ------------------------------------------------------------------ timing


def test_one_full_sizing_timed(cfg: Any, veh: Any, request: pytest.FixtureRequest) -> None:
    """One full sizing with a fresh geometry and envelope (``structure.size``) on a
    synthetic pad of the recorded pad's size (rows every 0.05 s: about 10,500 cases),
    timed and recorded in the test's user_properties (nothing printed): the screened search
    needs about 3,263 sizings within 10 minutes, about 0.18 s each (source note 9.3). The
    pad's drivers are prepared once (the first sizing); the ceiling is generous."""
    layout = cfg.stack_layout()
    result = ss.synthetic_pad_result(veh, dt_s=0.05)
    start = time.perf_counter()
    pad_set = st.pad_load_set(sim.structure_pad_cases(result, veh, layout))
    prepared = time.perf_counter() - start
    masses = sim.stack_masses(veh)
    push = ss.headline_push(veh, layout)
    coeffs = cfg.coefficients()
    start = time.perf_counter()
    st.size(masses, layout, coeffs, pad_set, push)
    first = time.perf_counter() - start
    step = cfg.coefficients(overrides={"materials.E_GPa": 72.0})
    runs = []
    for coeff_set, dynamic in ((coeffs, "rise_time"), (step, "step"), (coeffs, "rise_time")):
        start = time.perf_counter()
        inc = st.size(masses, layout, coeff_set, pad_set, push, dynamic=dynamic)
        runs.append(time.perf_counter() - start)
        assert inc.total_kg > 0.0
    request.node.user_properties.append(("pad_cases", len(pad_set.cases)))
    request.node.user_properties.append(("pad_prepare_s", prepared))
    request.node.user_properties.append(("first_sizing_s", first))
    request.node.user_properties.append(("sizing_s", max(runs)))
    assert len(pad_set.cases) > 10_000
    assert max(runs) < 1.0
