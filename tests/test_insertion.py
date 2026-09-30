"""Insertion into the 200 km circular target and the stage-2 burn (docs/physics.md,
"Orbital elements and the circular target" and "Stage 2 and insertion (planar)").

The runs fly the gate fork (generic_f9_class_2d.yaml) from the pad at 28.5 deg east
with rotation, the ICAO atmosphere and the Braeunig drag, v_k = 50 m/s, gamma* = 20
deg (delta solved), stage 2 on the LTG pair solved by shooting, rtol 1e-10. Closed
forms are written here: E* = -mu/(2 r_t), v_c = sqrt(mu/r_t), V_rel,f = v_c - omega_p
r_t; the heating rate 0.5 rho V^3 with rho from the isothermal extension written in the
test (the fairing drops above 81 km, beyond ambiance's table).
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from ambiance import CONST as ICAO_CONST
from ambiance import Atmosphere

from launchsim.atmosphere import ALT_AMBIANCE_MAX_M, ambient_scalar
from launchsim.config import LtgConfig, SearchConfig, VehicleConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity
from launchsim.guidance import (
    DeltaSolveSettings,
    GuidanceFailure,
    GuidanceSpec,
    LtgSettings,
    LtgSolution,
    solve_delta_for_gamma,
)
from launchsim.orbit import TargetOrbit, orbit_elements, specific_energy_Jkg
from launchsim.phases import EventSpec, IgnitionSpec, IntegratorSettings, RunTrace
from launchsim.phases import planar as planar_module
from launchsim.phases.planar import (
    LTG_BURN,
    Handover,
    PlanarEnvironment,
    PlanarPlanner,
    Stage2Result,
    ev_mass_floor,
)
from launchsim.vehicle import Vehicle, with_payload

P2 = PLANAR_LAYOUT
LAT_RAD = math.radians(28.5)
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)  # azimuth 90 deg
ALT_TARGET_M = 200.0e3
R_TARGET_M = R_EARTH_M + ALT_TARGET_M
GAMMA_STAR_RAD = math.radians(20.0)
RTOL = 1e-10
FAIRING_LIMIT_W_M2 = 1135.0
"""The gate fork's heating limit (Falcon User's Guide 2021 p.38)."""


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml (payload 22.8 t)."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _planner(
    vehicle: Vehicle, *, dense: bool = False, ltg: LtgSettings | None = None
) -> PlanarPlanner:
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
    return PlanarPlanner(
        vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "insertion",
        IntegratorSettings(rtol=RTOL, dense_output=dense),
        target=TargetOrbit(R_TARGET_M),
        ltg=LtgSettings.from_config(LtgConfig(), final=False) if ltg is None else ltg,
    )


@pytest.fixture(scope="module")
def inserted(
    gate_vehicle: Vehicle,
) -> tuple[float, Handover, LtgSolution[Stage2Result], RunTrace]:
    """(delta, hand-over, LTG solution, recorded trace) of the gate pad at gamma* 20 deg:
    the search-mode stage 1 and shooting, then the recorded run (dense output on) at
    the solved delta and (a, b)."""
    planner = _planner(gate_vehicle)
    kick = planner.to_kick(planner.start())
    sol = solve_delta_for_gamma(
        lambda d: planner.from_kick(d, kick),
        GAMMA_STAR_RAD,
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    ltg = planner.solve_stage2(sol.handover)
    trace = _planner(gate_vehicle, dense=True).run(sol.delta_rad, ltg=(ltg.a, ltg.b_per_s))
    return sol.delta_rad, sol.handover, ltg, trace


def test_target_orbit_numbers() -> None:
    """The 200 km circular target at 28.5 deg east: E* = -mu/(2 r_t) = -30,297,365.5
    J/kg, v_c = sqrt(mu/r_t) = 7,784.2617 m/s and the planar V_rel at insertion
    v_c - omega_p r_t = 7,362.7061 m/s (computed here; the quoted digits to their last
    place); the specific energy of a state is (v_r^2 + v_theta^2)/2 - mu/r."""
    target = TargetOrbit(R_TARGET_M)
    e_star = -MU_EARTH_M3S2 / (2.0 * R_TARGET_M)
    v_c = math.sqrt(MU_EARTH_M3S2 / R_TARGET_M)
    assert target.energy_Jkg(MU_EARTH_M3S2) == pytest.approx(e_star, rel=1e-15)
    assert target.speed_rel_mps(MU_EARTH_M3S2, OMEGA_P) == pytest.approx(
        v_c - OMEGA_P * R_TARGET_M, rel=1e-15
    )
    assert e_star == pytest.approx(-30_297_365.5, abs=0.05)
    assert v_c == pytest.approx(7_784.2617, abs=5e-5)
    assert v_c - OMEGA_P * R_TARGET_M == pytest.approx(7_362.7061, abs=5e-5)
    assert target.altitude_m(R_EARTH_M) == pytest.approx(ALT_TARGET_M, abs=1e-9)
    energy = specific_energy_Jkg(R_TARGET_M, 3.0, 7_000.0, MU_EARTH_M3S2)
    assert energy == pytest.approx(0.5 * (9.0 + 4.9e7) - MU_EARTH_M3S2 / R_TARGET_M, rel=1e-15)


def test_recorded_run_inserts(
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
) -> None:
    """The recorded run ends with status inserted at the energy cutoff: E = E* within
    1e-9 relative, |r - r_t| < 1 m, |v_r| < 1e-3 m/s, e < 1e-6 and perigee and apogee
    within 10 m of 200 km (measured 2.5 cm, 1.2e-4 m/s, 1.6e-8 and 0.1 m), V_rel within
    1e-2 m/s of v_c - omega_p r_t; it reproduces the search-mode shot bit for bit (same
    steps with dense output on and off), and its events end ignition (stage 2),
    fairing, cutoff, end."""
    _delta, _ho, ltg, trace = inserted
    assert trace.status == "inserted"
    names = [e.name for e in trace.events]
    assert names[-4:] == ["ignition", "fairing", "cutoff", "end"]
    assert trace.events[-4].stage == "stage2" and trace.events[-4].phase == LTG_BURN
    t_cut, y = trace.burnouts["stage2"]
    np.testing.assert_array_equal(y, ltg.shot.y_cut)
    assert t_cut == ltg.shot.t_cut_s
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    energy = 0.5 * (v_r * v_r + v_t * v_t) - MU_EARTH_M3S2 / r
    assert energy == pytest.approx(-MU_EARTH_M3S2 / (2.0 * R_TARGET_M), rel=1e-9)
    assert abs(r - R_TARGET_M) < 1.0 and abs(v_r) < 1e-3
    elements = orbit_elements(r, v_r, v_t, MU_EARTH_M3S2)
    assert elements.e < 1e-6
    assert abs(elements.r_p_m - R_TARGET_M) < 10.0 and abs(elements.r_a_m - R_TARGET_M) < 10.0
    v_rel = math.hypot(v_r, v_t - OMEGA_P * r)
    v_c = math.sqrt(MU_EARTH_M3S2 / R_TARGET_M)
    assert v_rel == pytest.approx(v_c - OMEGA_P * R_TARGET_M, abs=1e-2)
    assert ltg.shot.m_res_kg > 0.0 and ltg.shot.dv_margin_mps > 0.0


def _extension_rho(alt_m: float) -> float:
    """Density [kg/m^3] of the isothermal extension above the ICAO table top, written
    here: p = p_top exp(-(h - h_top)/H_s), rho = p/(R_air T_top), with the top state
    from ambiance and H_s = R_air T_top (R_E + h_top)^2 / mu."""
    top = Atmosphere(ALT_AMBIANCE_MAX_M)
    p_top, t_top = float(top.pressure[0]), float(top.temperature[0])
    h_s = ICAO_CONST.R * t_top * (R_EARTH_M + ALT_AMBIANCE_MAX_M) ** 2 / MU_EARTH_M3S2
    return p_top * math.exp(-(alt_m - ALT_AMBIANCE_MAX_M) / h_s) / (ICAO_CONST.R * t_top)


def test_fairing_event_and_map(
    gate_vehicle: Vehicle,
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
) -> None:
    """The fairing drops inside LTG_BURN where 0.5 rho V^3 (V = |v_rel|, rho of the
    isothermal extension written here) equals 1,135 W/m^2 within 1e-9 relative (it
    lies above 81 km: measured 111.5 km, 46.6 s after stage-2 ignition, inside the
    100 to 130 km of the sanity table); the FAIRING map removes exactly the fairing mass
    and leaves r, theta, v_r, v_theta and every quadrature bit-equal; the burn then
    continues with the same law."""
    _delta, _ho, ltg, trace = inserted
    burns = [p for p in trace.phases if p.spec.kind == LTG_BURN]
    i = next(k for k, p in enumerate(burns) if p.ended_by == "fairing")
    before, after = burns[i], burns[i + 1]
    y0, y1 = before.y_end, np.asarray(after.y[:, 0])
    assert after.spec.t0 == before.t_end
    i_m = P2.index("m_kg")
    assert y0[i_m] - y1[i_m] == pytest.approx(gate_vehicle.fairing_mass_kg, rel=1e-12)
    others = [k for k in range(len(P2)) if k != i_m]
    np.testing.assert_array_equal(y0[others], y1[others])
    assert "fairing" not in {e.name for e in after.spec.events}
    assert after.spec.params.steering == before.spec.params.steering
    r, v_r, v_t = (float(P2.get(y0, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    alt = r - R_EARTH_M
    assert ALT_AMBIANCE_MAX_M < alt
    rate = 0.5 * _extension_rho(alt) * math.hypot(v_r, v_t - OMEGA_P * r) ** 3
    assert rate == pytest.approx(FAIRING_LIMIT_W_M2, rel=1e-9)
    assert ltg.shot.t_fairing_s == before.t_end and not ltg.shot.fairing_on
    assert ltg.shot.m_after_fairing_kg == pytest.approx(float(y1[i_m]), rel=1e-15)


def test_heating_rule_carries_the_fairing_into_stage2(
    gate_vehicle: Vehicle,
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
) -> None:
    """Under the heating rule (not met at the 66 km MECO) stage 2 ignites carrying the
    fairing: its mass is m_p2 + m_d2 + P + F (the stage-1 burnout mass less m_d1 only),
    not the screening helpers' mass without F."""
    _delta, ho, _ltg, _trace = inserted
    assert ho.fairing_on and ho.y_ign2 is not None
    s2 = gate_vehicle.stages[1]
    expected = s2.propellant_mass_kg + s2.dry_mass_kg + gate_vehicle.payload_mass_kg
    expected += gate_vehicle.fairing_mass_kg
    assert float(P2.get(ho.y_ign2, "m_kg")) == pytest.approx(expected, abs=1e-5)
    _t, y_meco = ho.prefix.burnouts["stage1"]
    staged = float(P2.get(y_meco, "m_kg")) - gate_vehicle.stages[0].dry_mass_kg
    assert float(P2.get(ho.y_ign2, "m_kg")) == staged


def test_virtual_propellant_depletion_and_limits(
    gate_vehicle: Vehicle,
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 30 t payload (above capacity): the search shots burn virtual propellant past
    the real load, so the shooting still inserts, with m_res = m_c - (m_d2 + P) < 0 and
    a negative dv margin c2 ln(m_c/(m_d2 + P)) (measured -5.1 t, -555 m/s). The same
    (a, b) in the final mode ends at the real depletion (ended_by propellant, m_res 0
    within 1e-6 kg, tau = tau_b = m_p2 g0 Isp / T2_vac computed here) and the recorded
    run reports short_of_orbit. Every search shot arms the mass floor at exactly 0.5
    (m_d2 + P), without the fairing still carried (the factory's argument, recorded by a
    spy). With the mass floor raised to 0.99 (m_d2 + P) the shot raises GuidanceFailure
    mass_floor; with tau_max_factor 1.01 it raises no_cutoff (a guard the shipped
    settings never reach first: docs/physics.md, "Stage 2 and insertion (planar)")."""
    delta, _ho, _ltg, _trace = inserted
    heavy = with_payload(gate_vehicle, 30_000.0)
    planner = _planner(heavy)
    ho = planner.stage1(delta, planner.start())
    floors: list[float] = []

    def spy(m_floor_kg: float) -> EventSpec:
        floors.append(m_floor_kg)
        return ev_mass_floor(m_floor_kg)

    monkeypatch.setattr(planar_module, "ev_mass_floor", spy)
    sol = planner.solve_stage2(ho)
    s2 = heavy.stages[1]
    # the floor is k (m_d2 + P), without the fairing (still on at stage-2 ignition)
    assert ho.fairing_on
    assert floors and set(floors) == {0.5 * (s2.dry_mass_kg + heavy.payload_mass_kg)}
    shot = sol.shot
    m_empty = heavy.stages[1].dry_mass_kg + heavy.payload_mass_kg
    assert shot.m_empty_kg == m_empty and shot.virtual_propellant
    assert shot.m_res_kg == pytest.approx(shot.m_cut_kg - m_empty, rel=1e-15)
    assert shot.m_res_kg < -1000.0
    c2 = heavy.stages[1].c_mps
    assert shot.dv_margin_mps == pytest.approx(c2 * math.log(shot.m_cut_kg / m_empty), rel=1e-14)
    real = planner.stage2(ho, sol.a, sol.b_per_s, virtual_propellant=False)
    assert real.ended_by == "propellant" and abs(real.m_res_kg) < 1e-6
    tau_b = s2.propellant_mass_kg * G0_MPS2 * s2.engine.isp_vac_s
    tau_b /= s2.n_engines * s2.engine.thrust_vac_N
    assert real.tau_cut_s == pytest.approx(tau_b, rel=1e-9)
    recorded = _planner(heavy, dense=True).run(delta, ltg=(sol.a, sol.b_per_s))
    assert recorded.status == "short_of_orbit"
    assert [e.name for e in recorded.events][-2:] == ["propellant", "end"]
    base = LtgSettings.from_config(LtgConfig(), final=False)
    for field, value, kind in (
        ("mass_floor_factor", 0.99, "mass_floor"),
        ("tau_max_factor", 1.01, "no_cutoff"),
    ):
        limited = _planner(heavy, ltg=dataclasses.replace(base, **{field: value}))
        with pytest.raises(GuidanceFailure) as info:
            limited.stage2(ho, sol.a, sol.b_per_s, virtual_propellant=True)
        assert info.value.kind == kind


def test_lofted_overshoot_and_missing_inputs_are_refused(
    gate_vehicle: Vehicle,
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
) -> None:
    """A hand-over already at orbital energy (v_theta raised to 9 km/s: E > E*) raises
    GuidanceFailure lofted_overshoot from the shooting and from a single shot; a lit
    stage 2 without the LTG pair, and a planner without target and LTG settings, are
    refused (ValueError)."""
    delta, ho, _ltg, _trace = inserted
    assert ho.y_ign2 is not None
    y = ho.y_ign2.copy()
    y[P2.index("v_theta_mps")] = 9_000.0
    lofted = dataclasses.replace(ho, y_ign2=y)
    planner = _planner(gate_vehicle)
    for call in (
        lambda: planner.solve_stage2(lofted),
        lambda: planner.stage2(lofted, 0.7, 0.002, virtual_propellant=True),
    ):
        with pytest.raises(GuidanceFailure) as info:
            call()
        assert info.value.kind == "lofted_overshoot"
    with pytest.raises(ValueError, match="linear-tangent pair"):
        planner.run(delta)
    bare = PlanarPlanner(
        gate_vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        planner.env,
        "insertion",
        planner.settings,
    )
    with pytest.raises(ValueError, match="target and ltg"):
        bare.stage2(ho, 0.7, 0.002, virtual_propellant=True)


@pytest.mark.parametrize("end", ["apex", "impact"])
def test_apex_and_impact_ends_stop_at_the_cutoff_after_insertion(
    gate_vehicle: Vehicle,
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
    end: str,
) -> None:
    """End apex or impact with a lit stage 2 that reaches the energy cutoff: an orbit
    has no impact and its apex is the apogee, so the run ends at the cutoff exactly
    like end insertion (status inserted, events ending cutoff, end at the same time
    and state) with one flag naming the end, and no terminal COAST phase."""
    delta, _ho, ltg, trace = inserted
    planner = _planner(gate_vehicle, dense=True)
    planner.end = end
    other = planner.run(delta, ltg=(ltg.a, ltg.b_per_s))
    assert other.status == "inserted"
    assert [e.name for e in other.events][-2:] == ["cutoff", "end"]
    assert other.events[-1] == trace.events[-1]
    assert "COAST" not in {p.spec.kind for p in other.phases}
    flagged = [f for f in other.flags if f.startswith(f"end {end}: stage 2 reached the target")]
    assert len(flagged) == 1 and len(other.flags) == len(trace.flags) + 1


@pytest.mark.parametrize(
    ("scale_a", "scale_b", "end"),
    [(1.05, 1.0, "insertion"), (0.8, 1.2, "insertion"), (1.0, 0.9, "impact")],
)
def test_a_cutoff_off_the_acceptance_is_not_inserted(
    gate_vehicle: Vehicle,
    inserted: tuple[float, Handover, LtgSolution[Stage2Result], RunTrace],
    scale_a: float,
    scale_b: float,
    end: str,
) -> None:
    """A recorded run at a pair that is not a converged root (the solved (a, b) scaled)
    still reaches the energy cutoff (E = E*, 1e-9 relative), but its cutoff state misses
    the LTG acceptance (|r_c - r_t| >= 1 m or |v_r,c| >= 1e-3 m/s, checked here), so the
    run reports status off_target, not inserted, with one flag naming the misses; it ends
    at the cutoff (events cutoff, end; no terminal COAST) for end insertion and impact
    alike. Measured: 1.05 a gives dr +18.9 km and e 0.020; 0.8 a with 1.2 b a suborbital
    perigee."""
    delta, _ho, ltg, _trace = inserted
    planner = _planner(gate_vehicle, dense=True)
    planner.end = end
    trace = planner.run(delta, ltg=(scale_a * ltg.a, scale_b * ltg.b_per_s))
    assert trace.status == "off_target"
    assert [e.name for e in trace.events][-2:] == ["cutoff", "end"]
    assert "COAST" not in {p.spec.kind for p in trace.phases}
    _t, y = trace.burnouts["stage2"]
    r, v_r, v_t = (float(P2.get(y, n)) for n in ("r_m", "v_r_mps", "v_theta_mps"))
    energy = 0.5 * (v_r * v_r + v_t * v_t) - MU_EARTH_M3S2 / r
    assert energy == pytest.approx(-MU_EARTH_M3S2 / (2.0 * R_TARGET_M), rel=1e-9)
    accept = LtgConfig()
    assert abs(r - R_TARGET_M) >= accept.accept_r_m or abs(v_r) >= accept.accept_vr_mps
    off = [f for f in trace.flags if f.startswith("off target: ")]
    assert len(off) == 1
    ended = [f for f in trace.flags if f.startswith(f"end {end}: ")]
    assert len(ended) == (0 if end == "insertion" else 1)
    assert all("reached the target orbit" not in f for f in ended)
