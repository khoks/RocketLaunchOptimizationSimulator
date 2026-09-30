"""Rocket-equation closure of a planar run (docs/physics.md, "Rocket-equation closure
(planar)"):

    D_id(P) = c1 ln(m0/m1) + c2 ln(m2/m3)
            = J_vac + c1 ln(m0/m_fs) + c2 ln[(1 + F2/m_f+)/(1 + F2/m2)] + dv_margin

with m0 the stack at stage-1 ignition, m1 = m0 - m_p1, m2 = m1 - m_d1 - F, m3 = m_d2 +
P, m_fs the mass at the flight start, F2 the fairing carried into stage 2 (F unless it
dropped at staging), m_f+ the mass just after its drop (m3 when never dropped) and
dv_margin = c2 ln(m_c/(m3 + F2 if still on)). Every mass and c = g0 Isp_vac is computed
here from the vehicle's numbers; the per-stage J_vac = c ln(m_start/m_end) closed forms
use the masses the trace logged. Gate fork, pad and silo_hot_full, gamma* = 20 deg,
the LTG pair solved, recorded runs at rtol 1e-10. Also the matched-payload attribution
of pad against silo_cold (``compare.matched_attribution``, docs/physics.md,
"Screening-beat rule (2-D)").
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import pytest
import yaml

from launchsim.assist import build_assist
from launchsim.atmosphere import ambient_scalar
from launchsim.compare import (
    ATTRIBUTION_KEYS,
    ATTRIBUTION_TERMS,
    MatchedRun,
    matched_attribution,
)
from launchsim.config import ConstantAccelConfig, LtgConfig, SearchConfig, VehicleConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import PLANAR_LAYOUT, InverseSquareGravity
from launchsim.guidance import (
    DeltaSolveSettings,
    GuidanceSpec,
    LtgSettings,
    LtgSolution,
    solve_delta_for_gamma,
)
from launchsim.losses import rocket_equation_closure
from launchsim.orbit import TargetOrbit
from launchsim.phases import IgnitionSpec, IntegratorSettings, RunTrace
from launchsim.phases.planar import PlanarEnvironment, PlanarPlanner, Stage2Result
from launchsim.vehicle import Vehicle, with_payload

P2 = PLANAR_LAYOUT
LAT_RAD = math.radians(28.5)
OMEGA_P = OMEGA_EARTH_RADS * math.cos(LAT_RAD)  # azimuth 90 deg
R_TARGET_M = R_EARTH_M + 200.0e3
GAMMA_STAR_RAD = math.radians(20.0)
CLOSURE_TOL_MPS = 1e-5
"""checks.closure_tol_mps of the shipped experiments."""
SILO_ACCEL_G = 3.0
SILO_STROKE_M = 100.0


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml (payload 22.8 t, heating fairing rule)."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


def _planner(vehicle: Vehicle, ign1: IgnitionSpec, dense: bool) -> PlanarPlanner:
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), OMEGA_P, ambient_scalar)
    return PlanarPlanner(
        vehicle,
        {"stage1": ign1, "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "insertion",
        IntegratorSettings(rtol=1e-10, dense_output=dense),
        target=TargetOrbit(R_TARGET_M),
        ltg=LtgSettings.from_config(LtgConfig(), final=False),
    )


def _silo() -> tuple[object, object]:
    cfg = ConstantAccelConfig(
        model="constant_accel",
        net_accel_g=SILO_ACCEL_G,
        stroke_m=SILO_STROKE_M,
        brake_decel_g=5.0,
        drive_efficiency=0.5,
    )
    return build_assist(cfg, MU_EARTH_M3S2 / R_EARTH_M**2 - OMEGA_P**2 * R_EARTH_M)


_SOLVED: dict[tuple[str, str, bool], tuple[float, LtgSolution[Stage2Result]]] = {}
"""Search-mode solutions already computed in this module, keyed by (repr of the
vehicle, repr of the stage-1 ignition, whether on the silo): the solves are pure, so a
test that needs the same one reuses it instead of re-flying it."""


def _solve(
    vehicle: Vehicle, ign1: IgnitionSpec, assist: object = None, track: object = None
) -> tuple[float, LtgSolution[Stage2Result]]:
    """Search mode: delta for gamma* = 20 deg, then the LTG pair; (delta, solution),
    memoised in _SOLVED."""
    key = (repr(vehicle), repr(ign1), assist is not None)
    if key not in _SOLVED:
        _SOLVED[key] = _solve_uncached(vehicle, ign1, assist, track)
    return _SOLVED[key]


def _solve_uncached(
    vehicle: Vehicle, ign1: IgnitionSpec, assist: object, track: object
) -> tuple[float, LtgSolution[Stage2Result]]:
    """The search-mode solve behind ``_solve``."""
    search = _planner(vehicle, ign1, dense=False)
    kick = search.to_kick(search.start(assist, track))  # type: ignore[arg-type]
    sol = solve_delta_for_gamma(
        lambda d: search.from_kick(d, kick),
        GAMMA_STAR_RAD,
        DeltaSolveSettings.from_config(SearchConfig()),
    )
    assert sol.delta_rad is not None
    return sol.delta_rad, search.solve_stage2(sol.handover)


def _fly(vehicle: Vehicle, ign1: IgnitionSpec, silo: bool = False) -> RunTrace:
    """Solve delta (gamma* 20 deg) and the LTG pair in search mode, then record."""
    assist, track = _silo() if silo else (None, None)
    delta, ltg = _solve(vehicle, ign1, assist, track)
    recorder = _planner(vehicle, ign1, dense=True)
    trace = recorder.run(delta, assist, track, ltg=(ltg.a, ltg.b_per_s))  # type: ignore[arg-type]
    assert trace.status == "inserted"
    return trace


def _masses(v: Vehicle) -> dict[str, float]:
    """m0, m1, m2, m3, F and c1, c2, computed from the vehicle's inputs."""
    s1, s2 = v.stages
    fairing, payload = v.fairing_mass_kg, v.payload_mass_kg
    m0 = s1.dry_mass_kg + s1.propellant_mass_kg + s2.dry_mass_kg + s2.propellant_mass_kg
    m0 += fairing + payload
    m1 = m0 - s1.propellant_mass_kg
    return {
        "m0": m0,
        "m1": m1,
        "m2": m1 - s1.dry_mass_kg - fairing,
        "m3": s2.dry_mass_kg + payload,
        "F": fairing,
        "c1": G0_MPS2 * s1.engine.isp_vac_s,
        "c2": G0_MPS2 * s2.engine.isp_vac_s,
    }


def _j_vac(y: object) -> float:
    return float(P2.get(y, "J_vac_mps"))  # type: ignore[arg-type]


def _m(y: object) -> float:
    return float(P2.get(y, "m_kg"))  # type: ignore[arg-type]


def test_pad_closure_and_stage_rocket_equations(gate_vehicle: Vehicle) -> None:
    """The pad (heating rule: the fairing rides into stage 2 and drops at 111 km):
    D_id from the vehicle's masses (1e-14); J_vac of stage 1 = c1 ln(m_fs/m1) and of
    stage 2 = c2 [ln(m2'/m_f-) + ln(m_f+/m_c)] with the logged masses (m2' at stage-2
    ignition, m_f- at the fairing event, m_f+ = m_f- - F, m_c at the cutoff; 1e-9
    relative); pre = c1 ln(m0/m_fs) (the 2,697 kg burned on the hold-down), fair and
    dv_margin as written here; the residual below 1e-5 m/s (measured -7.7e-8), and a
    trace checked against a vehicle 100 kg lighter in payload fails it."""
    trace = _fly(gate_vehicle, IgnitionSpec(-2.0))
    k = _masses(gate_vehicle)
    closure = rocket_equation_closure(trace, gate_vehicle)
    d_id = k["c1"] * math.log(k["m0"] / k["m1"]) + k["c2"] * math.log(k["m2"] / k["m3"])
    assert closure.d_id_mps == pytest.approx(d_id, rel=1e-14)
    assert trace.y_flight_start is not None
    m_fs = _m(trace.y_flight_start)
    _t1, y_meco = trace.burnouts["stage1"]
    _t2, y_cut = trace.burnouts["stage2"]
    assert _m(y_meco) == pytest.approx(k["m1"], abs=1e-5)
    assert _j_vac(y_meco) == pytest.approx(k["c1"] * math.log(m_fs / k["m1"]), rel=1e-9)
    ign2 = next(e for e in trace.events if e.name == "ignition" and e.stage == "stage2")
    fairing = trace.first_event("fairing")
    assert fairing is not None and fairing.phase == "LTG_BURN"
    m_minus, m_c = fairing.m_kg, _m(y_cut)
    m_plus = m_minus - k["F"]
    j2 = k["c2"] * (math.log(ign2.m_kg / m_minus) + math.log(m_plus / m_c))
    assert _j_vac(y_cut) - _j_vac(y_meco) == pytest.approx(j2, rel=1e-9)
    assert closure.j_vac_mps == pytest.approx(_j_vac(y_cut), rel=1e-15)
    assert closure.pre_mps == pytest.approx(k["c1"] * math.log(k["m0"] / m_fs), rel=1e-14)
    assert k["m0"] - m_fs == pytest.approx(2_697.0, abs=1.0)
    fair = k["c2"] * math.log((1.0 + k["F"] / m_plus) / (1.0 + k["F"] / k["m2"]))
    assert closure.fair_mps == pytest.approx(fair, rel=1e-12) and closure.fair_mps > 0.0
    assert closure.dv_margin_mps == pytest.approx(k["c2"] * math.log(m_c / k["m3"]), rel=1e-12)
    assert abs(closure.residual_mps) < CLOSURE_TOL_MPS
    # a bookkeeping error is caught: the same trace against a payload 100 kg lighter
    # (measured residual 0.58 m/s, 5e4 times the tolerance)
    wrong = rocket_equation_closure(trace, with_payload(gate_vehicle, 22_700.0))
    assert abs(wrong.residual_mps) > 1e3 * CLOSURE_TOL_MPS


@pytest.mark.parametrize("rule", ["staging", "never"])
def test_closure_under_the_other_fairing_rules(gate_vehicle: Vehicle, rule: str) -> None:
    """Rule staging: F drops with stage 1 (F2 = 0, fair term exactly 0). Rule never: F
    stays on to the cutoff (F2 = F, m_f+ = m3, dv_margin = c2 ln(m_c/(m3 + F))) and the
    run is flagged. Both close below 1e-5 m/s."""
    vehicle = dataclasses.replace(gate_vehicle, fairing_drop=rule)
    trace = _fly(vehicle, IgnitionSpec(-2.0))
    k = _masses(vehicle)
    closure = rocket_equation_closure(trace, vehicle)
    m_c = _m(trace.burnouts["stage2"][1])
    if rule == "staging":
        assert closure.fair_mps == 0.0
        assert closure.dv_margin_mps == pytest.approx(k["c2"] * math.log(m_c / k["m3"]), rel=1e-12)
    else:
        fair = k["c2"] * math.log((1.0 + k["F"] / k["m3"]) / (1.0 + k["F"] / k["m2"]))
        assert closure.fair_mps == pytest.approx(fair, rel=1e-12)
        margin = k["c2"] * math.log(m_c / (k["m3"] + k["F"]))
        assert closure.dv_margin_mps == pytest.approx(margin, rel=1e-12)
        assert trace.first_event("fairing") is None
    still_on = [f for f in trace.flags if f.startswith("fairing: still on")]
    assert len(still_on) == (1 if rule == "never" else 0)
    assert abs(closure.residual_mps) < CLOSURE_TOL_MPS


def test_a_fairing_still_on_is_empty_mass(gate_vehicle: Vehicle) -> None:
    """Rule never (the fairing rides to the cutoff): the search shot's m_empty is m_d2 +
    P + F and m_res = m_c - (m_d2 + P + F), with the masses computed here. At 30 t
    (above capacity) the same rule's final-mode shot at its solved (a, b) burns only
    the real load: it ends at the depletion (ended_by propellant) at m = m_d2 + P + F
    (1e-6 kg) after tau_b = m_p2 c2 / T2_vac (1e-9 relative, computed here), so m_res
    is 0 and no fairing mass is burned as propellant."""
    never = dataclasses.replace(gate_vehicle, fairing_drop="never")
    k = _masses(never)
    delta, ltg = _solve(never, IgnitionSpec(-2.0))
    shot = ltg.shot
    assert shot.fairing_on and shot.t_fairing_s is None and shot.virtual_propellant
    assert shot.m_empty_kg == pytest.approx(k["m3"] + k["F"], rel=1e-15)
    assert shot.m_res_kg == pytest.approx(shot.m_cut_kg - (k["m3"] + k["F"]), abs=1e-9)
    assert shot.dv_margin_mps == pytest.approx(
        k["c2"] * math.log(shot.m_cut_kg / (k["m3"] + k["F"])), rel=1e-12
    )
    heavy = with_payload(never, 30_000.0)
    kh = _masses(heavy)
    planner = _planner(heavy, IgnitionSpec(-2.0), dense=False)
    ho = planner.stage1(delta, planner.start())
    sol = planner.solve_stage2(ho)
    assert sol.shot.m_res_kg < 0.0
    real = planner.stage2(ho, sol.a, sol.b_per_s, virtual_propellant=False)
    assert real.ended_by == "propellant" and real.fairing_on
    assert real.m_cut_kg == pytest.approx(kh["m3"] + kh["F"], abs=1e-6)
    assert abs(real.m_res_kg) < 1e-6
    s2 = heavy.stages[1]
    tau_b = s2.propellant_mass_kg * kh["c2"] / (s2.n_engines * s2.engine.thrust_vac_N)
    assert real.tau_cut_s == pytest.approx(tau_b, rel=1e-9)


def test_silo_hot_full_books_the_track_burn_as_pre(gate_vehicle: Vehicle) -> None:
    """silo_hot_full (lit 2 s before the push, 2 s ramp, full thrust over the push
    t_push = sqrt(2 L / a) with a = 3 g0): stage 1 burns mdot (t_r/2 + t_push) before
    release (closed form here, 1e-6 kg), so pre = c1 ln(m0/m_fs) > 0, and the closure
    holds below 1e-5 m/s."""
    trace = _fly(gate_vehicle, IgnitionSpec(-2.0, reference="push_start"), silo=True)
    k = _masses(gate_vehicle)
    s1 = gate_vehicle.stages[0]
    mdot = s1.n_engines * s1.engine.thrust_vac_N / k["c1"]
    t_push = math.sqrt(2.0 * SILO_STROKE_M / (SILO_ACCEL_G * G0_MPS2))
    burned = mdot * (0.5 * s1.startup.t_ramp_s + t_push)
    assert trace.y_flight_start is not None
    m_fs = _m(trace.y_flight_start)
    assert k["m0"] - m_fs == pytest.approx(burned, abs=1e-6)
    closure = rocket_equation_closure(trace, gate_vehicle)
    assert closure.pre_mps == pytest.approx(k["c1"] * math.log(k["m0"] / m_fs), rel=1e-14)
    assert abs(closure.residual_mps) < CLOSURE_TOL_MPS


def test_closure_needs_a_stage2_burn(gate_vehicle: Vehicle) -> None:
    """A run that stops at MECO has no stage-2 burnout: ValueError."""
    planner = _planner(gate_vehicle, IgnitionSpec(-2.0), dense=True)
    planner.end = "stage1_burnout"
    trace = planner.run(math.radians(3.0))
    with pytest.raises(ValueError, match="burned stage 2"):
        rocket_equation_closure(trace, gate_vehicle)


def _terms_here(trace: RunTrace, k: dict[str, float]) -> dict[str, float]:
    """The attribution terms of one run written here from its trace: V = |v_rel| =
    hypot(v_r, v_theta - omega_p r) at the flight start and at the stage-2 end, the
    quadratures' increments over the flight, pre = c1 ln(m0/m_fs), the fairing term
    c2 ln[(1 + F/m_f+)/(1 + F/m2)] (dropped in the burn) and c2 ln(m_c/m3)."""
    phases = trace.ascent_phases()
    y0, yf = phases[0].y[:, 0], phases[-1].y_end

    def speed(y: object) -> float:
        r = float(P2.get(y, "r_m"))  # type: ignore[arg-type]
        w = float(P2.get(y, "v_r_mps"))  # type: ignore[arg-type]
        return math.hypot(w, float(P2.get(y, "v_theta_mps")) - OMEGA_P * r)  # type: ignore[arg-type]

    def dj(name: str) -> float:
        return float(P2.get(yf, name)) - float(P2.get(y0, name))

    assert trace.y_flight_start is not None
    fairing = trace.first_event("fairing")
    assert fairing is not None and fairing.phase == "LTG_BURN"
    m_plus = fairing.m_kg - k["F"]
    m_c = _m(trace.burnouts["stage2"][1])
    return {
        "V_0": speed(y0),
        "V_f": speed(yf),
        "J_grav": dj("J_grav_mps"),
        "J_drag": dj("J_drag_mps"),
        "J_steer": dj("J_steer_mps"),
        "J_bp": dj("J_bp_mps"),
        "pre": k["c1"] * math.log(k["m0"] / _m(trace.y_flight_start)),
        "fair": k["c2"] * math.log((1.0 + k["F"] / m_plus) / (1.0 + k["F"] / k["m2"])),
        "dv_margin": k["c2"] * math.log(m_c / k["m3"]),
    }


def test_matched_payload_attribution(gate_vehicle: Vehicle) -> None:
    """Pad against silo_cold (3 g, 100 m, lit 0.5 s after release) at one payload (the
    vehicle's 22.8 t) and gamma* 20 deg (plan section 8; each run's own gamma* in the
    pipeline): ``compare.matched_attribution`` gives every term as written here, and
    d dv_margin = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d pre - d fair
    within 1e-5 m/s. dV_f is carried explicitly: V_f equals the target's V_rel,f only
    within the LTG acceptance (measured -3.3e-5 m/s here, docs/physics.md). A dP* of
    1,000 kg is split in proportion to the terms and adds up to it; two runs at
    different payloads are refused."""
    k = _masses(gate_vehicle)
    pad = _fly(gate_vehicle, IgnitionSpec(-2.0))
    silo = _fly(gate_vehicle, IgnitionSpec(0.5), silo=True)
    p = gate_vehicle.payload_mass_kg

    def matched(name: str, trace: RunTrace) -> MatchedRun:
        return MatchedRun(name, p, GAMMA_STAR_RAD, trace, gate_vehicle, OMEGA_P, R_EARTH_M)

    d_payload = 1_000.0
    out = matched_attribution(matched("silo_cold", silo), matched("pad", pad), d_payload)
    assert tuple(out) == ATTRIBUTION_KEYS
    tv, tb = _terms_here(silo, k), _terms_here(pad, k)
    expected = {
        "release_speed": tv["V_0"] - tb["V_0"],
        "final_speed": -(tv["V_f"] - tb["V_f"]),
        "gravity": -(tv["J_grav"] - tb["J_grav"]),
        "drag": -(tv["J_drag"] - tb["J_drag"]),
        "steering": -(tv["J_steer"] - tb["J_steer"]),
        "back_pressure": -(tv["J_bp"] - tb["J_bp"]),
        "preflight": -(tv["pre"] - tb["pre"]),
        "fairing": -(tv["fair"] - tb["fair"]),
    }
    for term, value in expected.items():
        assert out[f"attr_{term}_mps"] == pytest.approx(value, abs=1e-9), term
    d_margin = tv["dv_margin"] - tb["dv_margin"]
    assert out["attr_d_dv_margin_mps"] == pytest.approx(d_margin, abs=1e-9)
    assert abs(d_margin - math.fsum(expected.values())) < CLOSURE_TOL_MPS
    assert abs(out["attr_residual_mps"]) < CLOSURE_TOL_MPS
    assert 0.0 < abs(out["attr_final_speed_mps"]) < 1e-2  # carried, not assumed zero
    assert tb["V_0"] == 0.0 and tv["V_0"] > 0.0
    split = [out[f"attr_{term}_kg"] for term in expected]
    assert math.fsum(split) == pytest.approx(d_payload, rel=1e-12)
    total = math.fsum(expected.values())
    assert out["attr_gravity_kg"] == pytest.approx(d_payload * expected["gravity"] / total)
    joint = expected["gravity"] + expected["steering"]
    assert out["attr_gravity_steering_mps"] == pytest.approx(joint, abs=1e-9)
    assert out["attr_gravity_steering_kg"] == pytest.approx(d_payload * joint / total)
    assert out["attr_gamma_step_rad"] is None and out["attr_neighbours"] is None
    heavier = MatchedRun(
        "pad", p + 1.0, GAMMA_STAR_RAD, pad, with_payload(gate_vehicle, p + 1.0), OMEGA_P, R_EARTH_M
    )
    with pytest.raises(ValueError, match="one payload"):
        matched_attribution(matched("silo_cold", silo), heavier, d_payload)


def test_gamma_sensitivity_bookkeeping(gate_vehicle: Vehicle) -> None:
    """The gamma*-sensitivity items of the attribution: with the pad's own run as the
    variant's -h neighbour (every contribution 0 against the pad) and silo_cold's as
    its +h neighbour, each d(term)/d(gamma*) is the silo_cold contribution (written
    here) over 2 h, the neighbours' contributions are 0 and the silo_cold ones, and
    beyond_release is their sum without the release speed."""
    k = _masses(gate_vehicle)
    pad = _fly(gate_vehicle, IgnitionSpec(-2.0))
    silo = _fly(gate_vehicle, IgnitionSpec(0.5), silo=True)
    p = gate_vehicle.payload_mass_kg
    h = 0.01

    def matched(name: str, trace: RunTrace, gamma: float) -> MatchedRun:
        return MatchedRun(name, p, gamma, trace, gate_vehicle, OMEGA_P, R_EARTH_M)

    near = (matched("pad", pad, GAMMA_STAR_RAD - h), matched("silo", silo, GAMMA_STAR_RAD + h))
    variant = MatchedRun(
        "silo", p, GAMMA_STAR_RAD, silo, gate_vehicle, OMEGA_P, R_EARTH_M, neighbours=near
    )
    out = matched_attribution(variant, matched("pad", pad, GAMMA_STAR_RAD), 1_000.0)
    tv, tb = _terms_here(silo, k), _terms_here(pad, k)
    gravity = -(tv["J_grav"] - tb["J_grav"])
    steering = -(tv["J_steer"] - tb["J_steer"])
    assert out["attr_gamma_step_rad"] == pytest.approx(h, rel=1e-12)
    assert out["attr_gravity_dgamma_mps_per_rad"] == pytest.approx(gravity / (2 * h), rel=1e-9)
    assert out["attr_steering_dgamma_mps_per_rad"] == pytest.approx(steering / (2 * h), rel=1e-9)
    assert out["attr_gravity_steering_dgamma_mps_per_rad"] == pytest.approx(
        (gravity + steering) / (2 * h), rel=1e-9
    )
    minus, plus = out["attr_neighbours"]["minus"], out["attr_neighbours"]["plus"]
    assert all(v == 0.0 for v in minus.values())
    assert plus["gravity"] == pytest.approx(gravity, abs=1e-9)
    beyond = (
        math.fsum(v for key, v in plus.items() if key in ATTRIBUTION_TERMS)
        - (plus["release_speed"])
    )
    assert plus["beyond_release"] == pytest.approx(beyond, abs=1e-9)
