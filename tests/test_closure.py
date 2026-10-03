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

The cross-vehicle decomposition (``compare.cross_vehicle_decomposition``, docs/physics.md,
"Cross-vehicle decomposition"; SP1 step 6): with d = variant - baseline, two runs at one
payload on their own vehicles,

    D_id(base) - D_id(var) = dV_0 - dV_f - dJ_grav - dJ_drag - dJ_steer - dJ_bp - d pre
                             - d fair - d dv_margin

checked on hand-built planar traces (zero gravity field, vacuum, omega_p = 0, radial, so
|v_rel| = v_r; each burn leg books J_vac = c ln(m_start/m_end) and the loss increments
given here, and v_r follows the loss identity): a lossless pair, where a stage-1 offload
x = m0 (1 - exp(-V0/c1)) makes the ideal delta-v change equal to the release-speed term
V0 and every loss term zero; a pair with given loss, pre-flight, fairing, margin and
final-speed differences, where every term equals the difference written here and their
sum equals c1 ln(m0/(m0 - x)); the D_id change of each offload mode on the gate fork's
masses (stage 1: c1 ln(m0/(m0 - x)); stage 2 and both with the stage-2 and fairing terms
written out); the start-mass guard (a vehicle labelled with the wrong stage-1 load still
closes, because D_id and pre share c1 ln m0, but its trace's first event logs another
mass: bug_suspect; recorded pad and silo traces log their first event at m0); the
screening items of a pad variant and of a stage-2 offload (not
applicable); and, slow, the gate fork's pad at its P* against silo_cold offloaded at its
solved stage-1 x*.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from launchsim.assist import build_assist
from launchsim.atmosphere import ambient_scalar
from launchsim.cli import load_experiment
from launchsim.compare import (
    ATTRIBUTION_KEYS,
    ATTRIBUTION_TERMS,
    BUG_SUSPECT,
    CHECK_FAIL,
    CHECK_PASS,
    CROSS_VEHICLE_KEYS,
    CROSS_VEHICLE_TERMS,
    DECOMPOSITION_EXPLAINED,
    START_MASS_UNKNOWN_REASON,
    MatchedRun,
    cross_vehicle_decomposition,
    evaluation_matched_run,
    matched_attribution,
    offload_matched_run,
)
from launchsim.config import (
    ChecksConfig,
    ConstantAccelConfig,
    LtgConfig,
    SearchConfig,
    VehicleConfig,
)
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    PLANAR_STATE_NAMES,
    InverseSquareGravity,
    rhs_planar,
)
from launchsim.guidance import (
    DeltaSolveSettings,
    GuidanceSpec,
    LtgSettings,
    LtgSolution,
    solve_delta_for_gamma,
)
from launchsim.losses import rocket_equation_closure
from launchsim.offload import OffloadResult, planar_problem_factory, solve_offload
from launchsim.orbit import TargetOrbit
from launchsim.phases import (
    HOLD_KIND,
    EventRecord,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    RunTrace,
)
from launchsim.phases.engine import atol_for
from launchsim.phases.planar import (
    COAST_STAGING,
    FAIRING_EVENT,
    GRAVITY_TURN,
    LTG_BURN,
    PlanarEnvironment,
    PlanarPlanner,
    PlanarView,
    Stage2Result,
)
from launchsim.search import OK_STATUS, ResidualResult, SearchBudget, SearchContext, run_search
from launchsim.vehicle import (
    HEATING_TRIGGER,
    Engine,
    FairingDrop,
    Stage,
    Startup,
    Vehicle,
    with_offload,
    with_payload,
)

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


# ------------------------------------------------- cross-vehicle decomposition: toys

TOY_C1_MPS, TOY_C2_MPS = 3_000.0, 3_400.0
"""Exhaust velocities of the toy's stage 1 and stage 2 [m/s]; the screening Isp equals
the engine Isp."""
TOY_M_D1, TOY_M_P1 = 20_000.0, 300_000.0
"""Toy stage 1: dry and propellant mass [kg]."""
TOY_M_D2, TOY_M_P2 = 4_000.0, 90_000.0
"""Toy stage 2: dry and propellant mass [kg]."""
TOY_THRUST_N = 1.0e6
"""Vacuum thrust of each toy engine [N]; it enters no toy number (the traces are built by
hand, not flown)."""
TOY_PAYLOAD_KG = 15_000.0
"""Payload of every toy run [kg]."""
TOY_FAIRING_KG = 1_500.0
"""Fairing of the toy with a fairing [kg], carried into stage 2 under the heating rule."""
TOY_HEATING_LIMIT_W_M2 = 1_135.0
"""Heating limit of the toy's fairing rule [W/m^2]; it enters no toy number (the drop
mass is given)."""
TOY_V0_MPS = 80.0
"""The toy variant's head start [m/s]: |v_rel| at its release and flight start."""
TOY_LEG_S = 10.0
"""Duration of each hand-built phase [s]; it enters no number."""
TOY_TOL_MPS = 1e-9
"""Tolerance [m/s] of the toy terms and residuals: rounding of logarithms of masses up to
5.5e5 kg (about 1e-12 m/s), far below closure_tol_mps."""
LOSS_QUADRATURES = ("J_grav_mps", "J_drag_mps", "J_steer_mps", "J_bp_mps")
"""The loss quadratures a hand-built burn leg books."""


def _toy_stage(name: str, dry_kg: float, prop_kg: float, c_mps: float) -> Stage:
    """A toy stage: dry_kg and prop_kg [kg], one engine of TOY_THRUST_N with exhaust
    velocity c_mps [m/s] (Isp = c/g0), no exit area, step startup."""
    engine = Engine(thrust_vac_N=TOY_THRUST_N, isp_vac_s=c_mps / G0_MPS2, exit_area_m2=0.0)
    return Stage(name, dry_kg, prop_kg, engine, 1, Startup("step"), 0.0)


def _toy_vehicle(fairing_kg: float) -> Vehicle:
    """The toy two-stage vehicle at TOY_PAYLOAD_KG with fairing_kg [kg] of fairing (the
    heating rule when > 0, else staging) and the screening Isp equal to the engine Isp."""
    rule = (
        FairingDrop(HEATING_TRIGGER, TOY_HEATING_LIMIT_W_M2)
        if fairing_kg > 0.0
        else FairingDrop("staging")
    )
    return Vehicle(
        stages=(
            _toy_stage("stage1", TOY_M_D1, TOY_M_P1, TOY_C1_MPS),
            _toy_stage("stage2", TOY_M_D2, TOY_M_P2, TOY_C2_MPS),
        ),
        fairing_mass_kg=fairing_kg,
        payload_mass_kg=TOY_PAYLOAD_KG,
        fairing_drop=rule,
        screening_isp_s=(TOY_C1_MPS / G0_MPS2, TOY_C2_MPS / G0_MPS2),
    )


@dataclasses.dataclass(frozen=True)
class _ToyFlight:
    """One hand-built flight: v0_mps [m/s] radial at the flight start; the masses [kg] at
    stage-1 ignition (m0, logged by the trace's first event), the flight start (m_fs;
    below m0 after a hold-down burn), stage-1 burnout (m_meco), stage-2 ignition
    (m_ign2), just before the fairing drop in the stage-2 burn (m_fairing; None: no drop
    event) and at the cutoff (m_cut); the fairing mass dropped there [kg]; the loss
    increments [m/s] booked on stage 1 and stage 2 (quadrature name -> value)."""

    v0_mps: float
    m0_kg: float
    m_fs_kg: float
    m_meco_kg: float
    m_ign2_kg: float
    m_fairing_kg: float | None
    fairing_kg: float
    m_cut_kg: float
    losses_s1: Mapping[str, float] = dataclasses.field(default_factory=dict)
    losses_s2: Mapping[str, float] = dataclasses.field(default_factory=dict)


def _toy_state(v_mps: float, m_kg: float, quads: Mapping[str, float]) -> np.ndarray:
    """A PLANAR_LAYOUT state at R_E, radial speed v_mps [m/s], mass m_kg [kg], the given
    quadratures, everything else 0."""
    y = P2.zeros()
    y[P2.index("r_m")] = R_EARTH_M
    y[P2.index("v_r_mps")] = v_mps
    y[P2.index("m_kg")] = m_kg
    for name, value in quads.items():
        y[P2.index(name)] = value
    return y


def _toy_phase(
    kind: str, stage_index: int, t0: float, y0: np.ndarray, y1: np.ndarray
) -> PhaseResult:
    """A hand-built phase of kind from y0 to y1 over TOY_LEG_S (two samples, no dense
    output; the RHS is never called)."""
    t1 = t0 + TOY_LEG_S
    spec = PhaseSpec(kind, stage_index, t0, t1, rhs_planar, None, (), atol_for(PLANAR_STATE_NAMES))
    return PhaseResult(spec, np.array([t0, t1]), np.column_stack([y0, y1]), None, "t_end", t1, y1)


def _toy_burn(
    kind: str,
    stage_index: int,
    t0: float,
    y0: np.ndarray,
    m_end_kg: float,
    c_mps: float,
    losses: Mapping[str, float],
) -> PhaseResult:
    """A burn leg from y0 down to m_end_kg: J_vac grows by c ln(m_start/m_end), each loss
    quadrature by its given increment, and v_r by the J_vac increment minus the losses
    (the loss identity, |v_rel| = v_r here)."""
    dj_vac = c_mps * math.log(float(P2.get(y0, "m_kg")) / m_end_kg)
    quads = {name: float(P2.get(y0, name)) + losses.get(name, 0.0) for name in LOSS_QUADRATURES}
    quads["J_vac_mps"] = float(P2.get(y0, "J_vac_mps")) + dj_vac
    v_end = float(P2.get(y0, "v_r_mps")) + dj_vac - math.fsum(losses.values())
    return _toy_phase(kind, stage_index, t0, y0, _toy_state(v_end, m_end_kg, quads))


def _toy_trace(f: _ToyFlight, c1_mps: float, c2_mps: float) -> RunTrace:
    """The RunTrace of a hand-built flight: GRAVITY_TURN (stage 1, its losses),
    COAST_STAGING (the drop to m_ign2, nothing else changes), LTG_BURN to the fairing
    event (no losses) and LTG_BURN from m_fairing - fairing to the cutoff (stage-2
    losses), or one LTG_BURN without a fairing event; release = flight start at t = 0.
    The first event is the stage-1 ignition at m0, as a flown trace logs it before any
    propellant burns: in the HOLD at t = -TOY_LEG_S after a hold-down burn (m_fs < m0;
    no HOLD phase is built, the closure reads the flight start), else at t = 0. Frame:
    planar ECI with omega_p = 0."""
    y_fs = _toy_state(f.v0_mps, f.m_fs_kg, {})
    burn1 = _toy_burn(GRAVITY_TURN, 0, 0.0, y_fs, f.m_meco_kg, c1_mps, f.losses_s1)
    y = burn1.y_end.copy()
    y[P2.index("m_kg")] = f.m_ign2_kg
    coast = _toy_phase(COAST_STAGING, 1, burn1.t_end, y, y)
    held = f.m0_kg > f.m_fs_kg
    ignition = EventRecord(
        "ignition",
        -TOY_LEG_S if held else 0.0,
        HOLD_KIND if held else GRAVITY_TURN,
        "stage1",
        f.m0_kg,
        {},
    )
    phases, events, t = [burn1, coast], [ignition], coast.t_end
    if f.m_fairing_kg is not None:
        leg = _toy_burn(LTG_BURN, 1, t, y, f.m_fairing_kg, c2_mps, {})
        events.append(EventRecord(FAIRING_EVENT, leg.t_end, LTG_BURN, "stage2", f.m_fairing_kg, {}))
        y = leg.y_end.copy()
        y[P2.index("m_kg")] = f.m_fairing_kg - f.fairing_kg
        phases.append(leg)
        t = leg.t_end
    last = _toy_burn(LTG_BURN, 1, t, y, f.m_cut_kg, c2_mps, f.losses_s2)
    phases.append(last)
    return RunTrace(
        phases=tuple(phases),
        events=tuple(events),
        status="inserted",
        flags=(),
        assumptions=(),
        t_release_s=0.0,
        y_release=y_fs,
        t_flight_start_s=0.0,
        y_flight_start=y_fs,
        hold=None,
        t_ign_abs_s={},
        burnouts={"stage1": (burn1.t_end, burn1.y_end), "stage2": (last.t_end, last.y_end)},
        view=PlanarView(0.0),
    )


def _toy_flight(
    vehicle: Vehicle,
    *,
    v0_mps: float,
    m_fs_kg: float,
    m_fairing_kg: float | None,
    dv_margin_mps: float,
    losses_s1: Mapping[str, float] | None = None,
    losses_s2: Mapping[str, float] | None = None,
) -> _ToyFlight:
    """A flight of vehicle: lit at its liftoff mass m0, stage 1 burns to m1, stage 2 is
    lit at m2 (+ F when the fairing rides into stage 2, i.e. a drop mass is given) and
    cut at m3 exp(dv_margin / c2), so its margin c2 ln(m_c/m3) is dv_margin_mps; masses
    from ``_masses``."""
    k = _masses(vehicle)
    carried = vehicle.fairing_mass_kg if m_fairing_kg is not None else 0.0
    return _ToyFlight(
        v0_mps=v0_mps,
        m0_kg=k["m0"],
        m_fs_kg=m_fs_kg,
        m_meco_kg=k["m1"],
        m_ign2_kg=k["m2"] + carried,
        m_fairing_kg=m_fairing_kg,
        fairing_kg=carried,
        m_cut_kg=k["m3"] * math.exp(dv_margin_mps / k["c2"]),
        losses_s1=dict(losses_s1 or {}),
        losses_s2=dict(losses_s2 or {}),
    )


def _toy_matched(name: str, vehicle: Vehicle, flight: _ToyFlight) -> MatchedRun:
    """The MatchedRun of a hand-built flight of vehicle at its payload (omega_p = 0)."""
    c1, c2 = (s.c_mps for s in vehicle.stages)
    trace = _toy_trace(flight, c1, c2)
    return MatchedRun(name, vehicle.payload_mass_kg, GAMMA_STAR_RAD, trace, vehicle, 0.0, R_EARTH_M)


def _toy_v_end(f: _ToyFlight, c1_mps: float, c2_mps: float) -> float:
    """The cutoff speed [m/s] of a hand-built flight, written here: v0 + J_vac - the
    losses, J_vac = c1 ln(m_fs/m_meco) + c2 [ln(m_ign2/m_fairing) + ln((m_fairing -
    F)/m_cut)] (one stage-2 log without a drop)."""
    j_vac = c1_mps * math.log(f.m_fs_kg / f.m_meco_kg)
    if f.m_fairing_kg is None:
        j_vac += c2_mps * math.log(f.m_ign2_kg / f.m_cut_kg)
    else:
        j_vac += c2_mps * math.log(f.m_ign2_kg / f.m_fairing_kg)
        j_vac += c2_mps * math.log((f.m_fairing_kg - f.fairing_kg) / f.m_cut_kg)
    losses = math.fsum([*f.losses_s1.values(), *f.losses_s2.values()])
    return f.v0_mps + j_vac - losses


def test_lossless_offload_equals_the_release_speed_term() -> None:
    """No losses, no hold, no fairing, both runs at zero margin: the pad from rest at full
    load, the variant with the head start V0 = 80 m/s on the vehicle offloaded in stage 1
    by x = m0 (1 - exp(-V0/c1)) (closed form here). The release-speed term is V0 exactly,
    every loss term exactly 0, the final-speed, pre-flight, fairing and margin terms 0 to
    rounding; the ideal delta-v change c1 ln(m0/(m0 - x)) equals V0 and the decomposition
    closes (residual below 1e-9 m/s); the offload is x and its kg split puts all of it on
    the release speed; the ideal-screening offload (``vehicle.stage1_propellant_saved_kg``,
    screening Isp = engine Isp) is the same x, ratio 1; status explained."""
    full = _toy_vehicle(0.0)
    k = _masses(full)
    x = k["m0"] * (1.0 - math.exp(-TOY_V0_MPS / k["c1"]))
    offloaded = with_offload(full, "stage1", x)
    pad = _toy_matched(
        "pad",
        full,
        _toy_flight(
            full, v0_mps=0.0, m_fs_kg=full.liftoff_mass_kg(), m_fairing_kg=None, dv_margin_mps=0.0
        ),
    )
    flight = _toy_flight(
        offloaded,
        v0_mps=TOY_V0_MPS,
        m_fs_kg=offloaded.liftoff_mass_kg(),
        m_fairing_kg=None,
        dv_margin_mps=0.0,
    )
    out = cross_vehicle_decomposition(
        _toy_matched("silo", offloaded, flight), pad, checks=ChecksConfig()
    )
    assert tuple(out) == CROSS_VEHICLE_KEYS
    assert out["xv_release_speed_mps"] == TOY_V0_MPS
    for term in ("gravity", "drag", "steering", "back_pressure"):
        assert out[f"xv_{term}_mps"] == 0.0, term
    assert out["xv_gravity_stage1_mps"] == 0.0
    for term in ("final_speed", "preflight", "fairing", "margin"):
        assert abs(out[f"xv_{term}_mps"]) < TOY_TOL_MPS, term
    reduction = k["c1"] * math.log(k["m0"] / (k["m0"] - x))
    assert reduction == pytest.approx(TOY_V0_MPS, abs=TOY_TOL_MPS)
    assert out["xv_ideal_dv_reduction_mps"] == pytest.approx(reduction, abs=TOY_TOL_MPS)
    assert abs(out["xv_residual_mps"]) < TOY_TOL_MPS
    assert abs(out["xv_beyond_release_mps"]) < TOY_TOL_MPS
    assert out["xv_offload_kg"] == pytest.approx(x, abs=1e-9)
    assert out["xv_stage2_offload_kg"] == 0.0 and out["xv_dry_mass_delta_kg"] == 0.0
    assert out["xv_release_speed_kg"] == pytest.approx(x, rel=1e-9)
    for term in CROSS_VEHICLE_TERMS[1:]:
        assert abs(out[f"xv_{term}_kg"]) < 1e-6, term
    assert out["xv_speed_at_release_mps"] == TOY_V0_MPS
    assert out["xv_screening_offload_kg"] == pytest.approx(x, rel=1e-9)
    assert out["xv_offload_to_screening_ratio"] == pytest.approx(1.0, rel=1e-9)
    for side in ("variant", "baseline"):
        assert abs(out[f"xv_{side}_start_mass_error_kg"]) < 1e-6, side
    assert out["xv_check"]["status"] == CHECK_PASS
    assert out["xv_check"]["worst_start_mass_mps"] < TOY_TOL_MPS
    assert out["xv_status"] == DECOMPOSITION_EXPLAINED


@pytest.mark.parametrize("label_error_kg", [5_000.0, -5_000.0])
def test_a_wrong_stage1_load_closes_but_fails_the_start_mass_guard(label_error_kg: float) -> None:
    """The closure cannot see the stage-1 load: D_id = c1 ln(m0/m1) + c2 ln(m2/m3) and
    pre = c1 ln(m0/m_fs) both read m0 from the vehicle, and a stage-1 offload leaves m1
    unchanged, so D_id - pre (hence the closure residual) is the same whatever stage-1
    load the vehicle is labelled with. The lossless pair of the test above, with the
    variant's vehicle labelled offloaded by x + label_error_kg while its trace was flown
    at x: the variant's closure residual stays below 1e-9 m/s, the D_id change moves by
    c1 ln((m0 - x)/(m0 - x - e)) and the pre-flight term by the same amount (closed form
    here), but the trace's first event logs m0 - x, so the start-mass error is -e [kg]
    and the guard (c1 |ln(m0'/m_start)| below checks.closure_tol_mps) fails the check:
    bug_suspect."""
    full = _toy_vehicle(0.0)
    k = _masses(full)
    x = k["m0"] * (1.0 - math.exp(-TOY_V0_MPS / k["c1"]))
    pad = _toy_matched(
        "pad",
        full,
        _toy_flight(
            full, v0_mps=0.0, m_fs_kg=full.liftoff_mass_kg(), m_fairing_kg=None, dv_margin_mps=0.0
        ),
    )
    flown = with_offload(full, "stage1", x)
    flight = _toy_flight(
        flown,
        v0_mps=TOY_V0_MPS,
        m_fs_kg=flown.liftoff_mass_kg(),
        m_fairing_kg=None,
        dv_margin_mps=0.0,
    )
    labelled = with_offload(full, "stage1", x + label_error_kg)
    run = dataclasses.replace(_toy_matched("silo", flown, flight), vehicle=labelled)
    checks = ChecksConfig()
    out = cross_vehicle_decomposition(run, pad, checks=checks)
    assert abs(out["xv_variant_closure_residual_mps"]) < TOY_TOL_MPS
    assert abs(out["xv_residual_mps"]) < TOY_TOL_MPS
    shift = k["c1"] * math.log((k["m0"] - x) / (k["m0"] - x - label_error_kg))
    assert out["xv_ideal_dv_reduction_mps"] == pytest.approx(TOY_V0_MPS + shift, abs=TOY_TOL_MPS)
    assert out["xv_preflight_mps"] == pytest.approx(shift, abs=TOY_TOL_MPS)
    assert out["xv_offload_kg"] == pytest.approx(x + label_error_kg, abs=1e-9)
    assert out["xv_variant_start_mass_error_kg"] == pytest.approx(-label_error_kg, abs=1e-6)
    assert abs(out["xv_baseline_start_mass_error_kg"]) < 1e-6
    assert out["xv_check"]["worst_start_mass_mps"] == pytest.approx(abs(shift), abs=TOY_TOL_MPS)
    assert out["xv_check"]["worst_start_mass_mps"] > 1e3 * checks.closure_tol_mps
    assert out["xv_check"]["status"] == CHECK_FAIL
    assert out["xv_status"] == BUG_SUSPECT


def test_a_trace_without_events_fails_the_start_mass_guard() -> None:
    """A trace with no logged event has no start mass: the start-mass error is None and
    the check fails with START_MASS_UNKNOWN_REASON (bug_suspect), though the closure and
    the identity close."""
    full = _toy_vehicle(0.0)
    pad = _toy_matched(
        "pad",
        full,
        _toy_flight(
            full, v0_mps=0.0, m_fs_kg=full.liftoff_mass_kg(), m_fairing_kg=None, dv_margin_mps=0.0
        ),
    )
    bare = dataclasses.replace(pad, name="bare", trace=dataclasses.replace(pad.trace, events=()))
    out = cross_vehicle_decomposition(bare, pad, checks=ChecksConfig())
    assert abs(out["xv_residual_mps"]) < TOY_TOL_MPS
    assert out["xv_variant_start_mass_error_kg"] is None
    assert out["xv_check"]["status"] == CHECK_FAIL
    assert out["xv_check"]["reason"] == START_MASS_UNKNOWN_REASON
    assert out["xv_status"] == BUG_SUSPECT


def test_recorded_traces_start_at_the_liftoff_mass(gate_vehicle: Vehicle) -> None:
    """The guard's premise on recorded traces of the gate fork at its own payload (gamma*
    20 deg): the pad (lit 2 s before release, clamped), silo_cold (lit 0.5 s after
    release) and silo_hot_full (lit 2 s before the push, clamped to the carriage) each
    log their first event at m0, the stack from the vehicle's numbers (1e-6 kg); for
    silo_hot_full it is the ignition in the HOLD, before the track burn. Against the pad
    (one vehicle: D_id change 0) both start-mass errors are 0 and the row is explained.
    silo_cold's trace paired with the vehicle offloaded by 1 kg in stage 1 still closes
    (closure residual below closure_tol_mps), but its start-mass error is -1 kg (c1/m0,
    about 5e-3 m/s, above closure_tol_mps): bug_suspect."""
    k = _masses(gate_vehicle)
    p = gate_vehicle.payload_mass_kg
    traces = {
        "pad": _fly(gate_vehicle, IgnitionSpec(-2.0)),
        "silo_cold": _fly(gate_vehicle, IgnitionSpec(0.5), silo=True),
        "silo_hot_full": _fly(gate_vehicle, IgnitionSpec(-2.0, reference="push_start"), silo=True),
    }

    def matched(name: str, vehicle: Vehicle) -> MatchedRun:
        return MatchedRun(name, p, GAMMA_STAR_RAD, traces[name], vehicle, OMEGA_P, R_EARTH_M)

    first = {name: min(t.events, key=lambda e: e.t_s) for name, t in traces.items()}
    for name, event in first.items():
        assert event.m_kg == pytest.approx(k["m0"], abs=1e-6), name
    assert (first["silo_hot_full"].name, first["silo_hot_full"].phase) == ("ignition", HOLD_KIND)
    checks = ChecksConfig()
    pad = matched("pad", gate_vehicle)
    for name in ("silo_cold", "silo_hot_full"):
        out = cross_vehicle_decomposition(matched(name, gate_vehicle), pad, checks=checks)
        for side in ("variant", "baseline"):
            assert abs(out[f"xv_{side}_start_mass_error_kg"]) < 1e-6, (name, side)
        assert out["xv_ideal_dv_reduction_mps"] == 0.0
        assert out["xv_status"] == DECOMPOSITION_EXPLAINED, name
    wrong = matched("silo_cold", with_offload(gate_vehicle, "stage1", 1.0))
    out = cross_vehicle_decomposition(wrong, pad, checks=checks)
    assert abs(out["xv_variant_closure_residual_mps"]) < checks.closure_tol_mps
    assert out["xv_variant_start_mass_error_kg"] == pytest.approx(-1.0, abs=1e-6)
    assert out["xv_check"]["worst_start_mass_mps"] > checks.closure_tol_mps
    assert out["xv_status"] == BUG_SUSPECT


def test_screening_items_need_a_head_start_and_a_stage1_offload() -> None:
    """The yardstick is a stage-1 quantity at the release speed, so the ratio and the
    beat flag are None (not applicable) for (a) a pad offloaded in stage 1 by 10 t from
    rest against the full pad (step 7's paired pad): speed at release 0, yardstick 0;
    lossless, flying P_ref with the margin -c1 ln(m0/(m0 - x)) that leaves both at one
    cutoff speed, so the margin term carries the whole D_id change c1 ln(m0/(m0 - x))
    and the row is explained; and (b) a stage-2 offload of 5 t with the 80 m/s head
    start, both runs at zero margin: the yardstick m0 (1 - exp(-V0/c1)) is still
    reported (closed form), the ratio and the beat flag are None, explained."""
    full = _toy_vehicle(0.0)
    k = _masses(full)
    pad = _toy_matched(
        "pad",
        full,
        _toy_flight(
            full, v0_mps=0.0, m_fs_kg=full.liftoff_mass_kg(), m_fairing_kg=None, dv_margin_mps=0.0
        ),
    )
    x = 10_000.0
    reduction = k["c1"] * math.log(k["m0"] / (k["m0"] - x))
    paired = with_offload(full, "stage1", x)
    flight = _toy_flight(
        paired,
        v0_mps=0.0,
        m_fs_kg=paired.liftoff_mass_kg(),
        m_fairing_kg=None,
        dv_margin_mps=-reduction,
    )
    out = cross_vehicle_decomposition(
        _toy_matched("paired_pad", paired, flight), pad, checks=ChecksConfig()
    )
    assert out["xv_release_speed_mps"] == 0.0 and out["xv_speed_at_release_mps"] == 0.0
    assert out["xv_margin_mps"] == pytest.approx(reduction, abs=TOY_TOL_MPS)
    assert out["xv_ideal_dv_reduction_mps"] == pytest.approx(reduction, abs=TOY_TOL_MPS)
    assert abs(out["xv_final_speed_mps"]) < TOY_TOL_MPS
    assert out["xv_screening_offload_kg"] == 0.0
    assert out["xv_offload_to_screening_ratio"] is None
    assert out["xv_beats_screening"] is None
    assert out["xv_status"] == DECOMPOSITION_EXPLAINED

    stage2 = with_offload(full, "stage2", 5_000.0)
    flight2 = _toy_flight(
        stage2,
        v0_mps=TOY_V0_MPS,
        m_fs_kg=stage2.liftoff_mass_kg(),
        m_fairing_kg=None,
        dv_margin_mps=0.0,
    )
    out2 = cross_vehicle_decomposition(
        _toy_matched("silo_stage2", stage2, flight2), pad, checks=ChecksConfig()
    )
    assert out2["xv_stage1_offload_kg"] == 0.0
    assert out2["xv_stage2_offload_kg"] == pytest.approx(5_000.0, abs=1e-9)
    yardstick = k["m0"] * (1.0 - math.exp(-TOY_V0_MPS / k["c1"]))
    assert out2["xv_screening_offload_kg"] == pytest.approx(yardstick, rel=1e-9)
    assert out2["xv_offload_to_screening_ratio"] is None
    assert out2["xv_beats_screening"] is None
    assert out2["xv_status"] == DECOMPOSITION_EXPLAINED


def test_known_differences_explain_an_offload_beyond_the_screening() -> None:
    """The toy with a 1.5 t fairing carried into stage 2 (heating rule). Pad: from rest
    after burning 2,700 kg on the hold-down, losses (gravity, drag, steering,
    back-pressure) 1,100/30/60/70 m/s on stage 1 and 330/0/60/0 on stage 2, the fairing
    dropped 15.5 t into the stage-2 burn, margin +4 mm/s. Variant: the head start V0 = 80
    m/s, no pre-flight burn, losses 1,060/26/40/55 and 320/0/45/0, the fairing dropped
    10.5 t in, margin +1 mm/s, cutoff 2 mm/s faster than the pad (inside an LTG
    acceptance), on the vehicle offloaded in stage 1 by the x that makes its cutoff speed
    so (solved here in closed form). Every term equals the difference written here
    (pre-flight c1 ln(m0/(m0 - 2,700)); fairing c2 ln[(1 + F/m_f+)/(1 + F/m2)] of the pad
    minus the variant's; margin +3 mm/s; final speed -2 mm/s); their sum equals the
    closed-form ideal delta-v change c1 ln(m0/(m0 - x)) and the code's (1e-9 m/s); the kg
    split is x times each term over the sum; the stage-1 gravity part is 40 m/s. The
    offload is about 2.5 times the ideal-screening one m0 (1 - exp(-V0/c1)) (closed form)
    and the decomposition explains it: ratio x / that, beats True, status explained."""
    full = _toy_vehicle(TOY_FAIRING_KG)
    k = _masses(full)
    hold_kg = 2_700.0
    pad_s1 = {"J_grav_mps": 1_100.0, "J_drag_mps": 30.0, "J_steer_mps": 60.0, "J_bp_mps": 70.0}
    pad_s2 = {"J_grav_mps": 330.0, "J_steer_mps": 60.0}
    var_s1 = {"J_grav_mps": 1_060.0, "J_drag_mps": 26.0, "J_steer_mps": 40.0, "J_bp_mps": 55.0}
    var_s2 = {"J_grav_mps": 320.0, "J_steer_mps": 45.0}
    drop_pad = k["m2"] + k["F"] - 15_500.0
    drop_var = k["m2"] + k["F"] - 10_500.0
    margin_pad, margin_var, dv_f = 4e-3, 1e-3, 2e-3
    pad_flight = _toy_flight(
        full,
        v0_mps=0.0,
        m_fs_kg=k["m0"] - hold_kg,
        m_fairing_kg=drop_pad,
        dv_margin_mps=margin_pad,
        losses_s1=pad_s1,
        losses_s2=pad_s2,
    )
    v_star = _toy_v_end(pad_flight, k["c1"], k["c2"])
    # the variant's stage-1 J_vac that ends it at v_star + dv_f, hence its liftoff mass
    m_cut_var = k["m3"] * math.exp(margin_var / k["c2"])
    j2_var = k["c2"] * (
        math.log((k["m2"] + k["F"]) / drop_var) + math.log((drop_var - k["F"]) / m_cut_var)
    )
    losses_var = math.fsum([*var_s1.values(), *var_s2.values()])
    j1_var = (v_star + dv_f) - TOY_V0_MPS + losses_var - j2_var
    x = k["m0"] - k["m1"] * math.exp(j1_var / k["c1"])
    offloaded = with_offload(full, "stage1", x)
    var_flight = _toy_flight(
        offloaded,
        v0_mps=TOY_V0_MPS,
        m_fs_kg=offloaded.liftoff_mass_kg(),
        m_fairing_kg=drop_var,
        dv_margin_mps=margin_var,
        losses_s1=var_s1,
        losses_s2=var_s2,
    )
    pad = _toy_matched("pad", full, pad_flight)
    out = cross_vehicle_decomposition(
        _toy_matched("silo", offloaded, var_flight), pad, checks=ChecksConfig()
    )

    def fair(m_plus: float) -> float:
        return k["c2"] * math.log((1.0 + k["F"] / m_plus) / (1.0 + k["F"] / k["m2"]))

    expected = {
        "release_speed": TOY_V0_MPS,
        "final_speed": -dv_f,
        "gravity": (1_100.0 + 330.0) - (1_060.0 + 320.0),
        "drag": 30.0 - 26.0,
        "steering": (60.0 + 60.0) - (40.0 + 45.0),
        "back_pressure": 70.0 - 55.0,
        "preflight": k["c1"] * math.log(k["m0"] / (k["m0"] - hold_kg)),
        "fairing": fair(drop_pad - k["F"]) - fair(drop_var - k["F"]),
        "margin": margin_pad - margin_var,
    }
    assert tuple(expected) == CROSS_VEHICLE_TERMS
    for term, value in expected.items():
        assert out[f"xv_{term}_mps"] == pytest.approx(value, abs=TOY_TOL_MPS), term
    total = math.fsum(expected.values())
    reduction = k["c1"] * math.log(k["m0"] / (k["m0"] - x))
    assert total == pytest.approx(reduction, abs=TOY_TOL_MPS)
    assert out["xv_ideal_dv_reduction_mps"] == pytest.approx(reduction, abs=TOY_TOL_MPS)
    assert abs(out["xv_residual_mps"]) < TOY_TOL_MPS
    for side in ("variant", "baseline"):
        for kind in ("closure", "identity"):
            assert abs(out[f"xv_{side}_{kind}_residual_mps"]) < TOY_TOL_MPS, (side, kind)
    assert out["xv_beyond_release_mps"] == pytest.approx(total - TOY_V0_MPS, abs=TOY_TOL_MPS)
    assert out["xv_gravity_stage1_mps"] == pytest.approx(1_100.0 - 1_060.0, abs=TOY_TOL_MPS)
    joint = expected["gravity"] + expected["steering"]
    assert out["xv_gravity_steering_mps"] == pytest.approx(joint, abs=TOY_TOL_MPS)
    assert out["xv_d_dv_margin_mps"] == pytest.approx(margin_var - margin_pad, abs=TOY_TOL_MPS)
    assert out["xv_offload_kg"] == pytest.approx(x, abs=1e-9)
    kg_tol = x * TOY_TOL_MPS / total  # a term's m/s rounding, in kg of the split
    for term, value in expected.items():
        assert out[f"xv_{term}_kg"] == pytest.approx(x * value / total, abs=kg_tol), term
    split = [out[f"xv_{term}_kg"] for term in CROSS_VEHICLE_TERMS]
    assert math.fsum(split) == pytest.approx(x, rel=1e-12)
    screening = k["m0"] * (1.0 - math.exp(-TOY_V0_MPS / k["c1"]))
    assert out["xv_screening_offload_kg"] == pytest.approx(screening, rel=1e-9)
    assert out["xv_offload_to_screening_ratio"] == pytest.approx(x / screening, rel=1e-9)
    assert x / screening > 2.0 and out["xv_beats_screening"] is True
    # the pad's hold-down burn (m_fs < m0) is not a start-mass error: its trace starts at m0
    for side in ("variant", "baseline"):
        assert abs(out[f"xv_{side}_start_mass_error_kg"]) < 1e-6, side
    assert out["xv_status"] == DECOMPOSITION_EXPLAINED


@pytest.mark.parametrize(
    ("mode", "x_kg"), [("stage1", 20_000.0), ("stage2", 5_000.0), ("both", 25_000.0)]
)
def test_ideal_dv_change_of_an_offload_by_mode(
    gate_vehicle: Vehicle, mode: str, x_kg: float
) -> None:
    """The D_id change of each offload mode on the gate fork's masses (heating rule, so m2
    = m1 - m_d1 - F as the closure counts it), lossless hand-built flights with the
    fairing dropped 10 t into stage 2: with x1 from stage 1 and x2 from stage 2 (both: x1
    = x m_p1/(m_p1 + m_p2)), D_id(full) - D_id(offloaded) = c1 ln(m0/m1) - c1 ln((m0 -
    x)/(m1 - x2)) + c2 ln(m2/(m2 - x2)), for stage 1 exactly c1 ln(m0/(m0 - x)) (the
    fairing and stage-2 terms cancel); 1e-8 m/s. The decomposition closes and the
    per-stage offloads are x1 and x2."""
    full = gate_vehicle
    k = _masses(full)
    m_p1, m_p2 = (s.propellant_mass_kg for s in full.stages)
    x1 = {"stage1": x_kg, "stage2": 0.0, "both": x_kg * m_p1 / (m_p1 + m_p2)}[mode]
    x2 = x_kg - x1
    offloaded = with_offload(full, mode, x_kg)

    def lossless(name: str, v: Vehicle) -> MatchedRun:
        kv = _masses(v)
        flight = _toy_flight(
            v,
            v0_mps=0.0,
            m_fs_kg=v.liftoff_mass_kg(),
            m_fairing_kg=kv["m2"] + kv["F"] - 10_000.0,
            dv_margin_mps=10.0,
        )
        return _toy_matched(name, v, flight)

    out = cross_vehicle_decomposition(
        lossless(mode, offloaded), lossless("full", full), checks=ChecksConfig()
    )
    expected = (
        k["c1"] * math.log(k["m0"] / k["m1"])
        - k["c1"] * math.log((k["m0"] - x_kg) / (k["m1"] - x2))
        + k["c2"] * math.log(k["m2"] / (k["m2"] - x2))
    )
    if mode == "stage1":
        assert expected == pytest.approx(k["c1"] * math.log(k["m0"] / (k["m0"] - x_kg)), abs=1e-8)
    assert out["xv_ideal_dv_reduction_mps"] == pytest.approx(expected, abs=1e-8)
    assert abs(out["xv_residual_mps"]) < TOY_TOL_MPS
    assert out["xv_stage1_offload_kg"] == pytest.approx(x1, abs=1e-9)
    assert out["xv_stage2_offload_kg"] == pytest.approx(x2, abs=1e-9)
    assert out["xv_offload_kg"] == pytest.approx(x_kg, abs=1e-9)
    assert out["xv_status"] == DECOMPOSITION_EXPLAINED


def test_decomposition_refuses_two_payloads_and_flags_a_bookkeeping_error() -> None:
    """Two runs at different payloads are refused. A variant whose trace is checked
    against its vehicle with a payload 100 kg lighter (labelled with the same payload)
    breaks its closure (about 0.8 m/s, far above closure_tol_mps 1e-5): the check fails
    and the status is bug_suspect. With that non-zero per-run residual the
    decomposition's residual is still exactly (identity - closure residual) of the
    variant minus that of the baseline (1e-9 m/s), and the start-mass error is the
    100 kg the label lacks."""
    full = _toy_vehicle(0.0)
    k = _masses(full)
    pad = _toy_matched(
        "pad",
        full,
        _toy_flight(
            full, v0_mps=0.0, m_fs_kg=full.liftoff_mass_kg(), m_fairing_kg=None, dv_margin_mps=0.0
        ),
    )
    heavier = dataclasses.replace(pad, name="heavier", payload_kg=pad.payload_kg + 1.0)
    with pytest.raises(ValueError, match="one payload"):
        cross_vehicle_decomposition(heavier, pad, checks=ChecksConfig())
    x = k["m0"] * (1.0 - math.exp(-TOY_V0_MPS / k["c1"]))
    offloaded = with_offload(full, "stage1", x)
    flight = _toy_flight(
        offloaded,
        v0_mps=TOY_V0_MPS,
        m_fs_kg=offloaded.liftoff_mass_kg(),
        m_fairing_kg=None,
        dv_margin_mps=0.0,
    )
    good = _toy_matched("silo", offloaded, flight)
    wrong = dataclasses.replace(good, vehicle=with_payload(offloaded, TOY_PAYLOAD_KG - 100.0))
    checks = ChecksConfig()
    out = cross_vehicle_decomposition(wrong, pad, checks=checks)
    assert abs(out["xv_variant_closure_residual_mps"]) > 1e3 * checks.closure_tol_mps
    per_run = (out["xv_variant_identity_residual_mps"] - out["xv_variant_closure_residual_mps"]) - (
        out["xv_baseline_identity_residual_mps"] - out["xv_baseline_closure_residual_mps"]
    )
    assert abs(out["xv_residual_mps"]) > 1e3 * checks.closure_tol_mps
    assert out["xv_residual_mps"] == pytest.approx(per_run, abs=TOY_TOL_MPS)
    assert out["xv_variant_start_mass_error_kg"] == pytest.approx(-100.0, abs=1e-6)
    assert out["xv_check"]["status"] == CHECK_FAIL
    assert out["xv_status"] == BUG_SUSPECT


def _offload_result(
    status: str, at_offload: ResidualResult | None, offloaded: Vehicle | None
) -> OffloadResult:
    """An OffloadResult with the given status, final evaluation and offloaded vehicle,
    every other field a placeholder (only the adapter's inputs matter here)."""
    nan = math.nan
    return OffloadResult(
        mode="stage1",
        reference_payload_kg=nan if at_offload is None else at_offload.payload_kg,
        load_kg=TOY_M_P1,
        status=status,
        offload_kg=nan,
        root_kg=nan,
        gamma_star_rad=nan,
        m_res_kg=nan,
        dv_margin_mps=nan,
        dv_shortfall_mps=nan,
        at_offload=at_offload,
        recorded=None,
        offloaded_vehicle=offloaded,
        evaluations=(),
        n_evaluations=0,
        grid=(),
        verification=None,
        flags=(),
    )


def test_matched_runs_from_an_evaluation_and_an_offload_result() -> None:
    """``evaluation_matched_run``: the shot's prefix trace, the evaluation's payload and
    gamma*, the vehicle at that payload, the given frame, no neighbours; None without a
    shot. ``offload_matched_run``: the same on the offloaded vehicle (its own payload
    replaced by P_ref); None for a search_failed result. Nothing is flown."""
    full = _toy_vehicle(0.0)
    trace = _toy_matched(
        "any",
        full,
        _toy_flight(
            full, v0_mps=0.0, m_fs_kg=full.liftoff_mass_kg(), m_fairing_kg=None, dv_margin_mps=0.0
        ),
    ).trace
    p_ref, gamma, omega_p = 12_345.0, 0.4, 7.0e-5
    evaluation = ResidualResult(
        p_ref,
        gamma,
        0.01,
        0.002,
        0.05,
        (1.0, 0.01),
        gamma,
        "nominal",
        1,
        1,
        "final",
        shot=SimpleNamespace(prefix=trace),  # type: ignore[arg-type]
    )
    m = evaluation_matched_run("pad", evaluation, full, omega_p, R_EARTH_M)
    assert m is not None and m.name == "pad" and m.trace is trace
    assert (m.payload_kg, m.gamma_star_rad, m.omega_p_rads, m.r_datum_m) == (
        p_ref,
        gamma,
        omega_p,
        R_EARTH_M,
    )
    assert m.vehicle == with_payload(full, p_ref) and m.neighbours is None
    no_shot = dataclasses.replace(evaluation, shot=None)
    assert evaluation_matched_run("pad", no_shot, full, omega_p, R_EARTH_M) is None
    offloaded = with_offload(full, "stage1", 1_000.0)
    mo = offload_matched_run(
        "silo", _offload_result(OK_STATUS, evaluation, offloaded), omega_p, R_EARTH_M
    )
    assert mo is not None and mo.trace is trace and mo.payload_kg == p_ref
    assert mo.vehicle == with_payload(offloaded, p_ref)
    failed = _offload_result("search_failed", None, None)
    assert offload_matched_run("silo", failed, omega_p, R_EARTH_M) is None


# ------------------------------------------- cross-vehicle decomposition: gate fork

GATE_EXPERIMENT = Path("experiments") / "silo_screening_2d.yaml"
"""The gate fork's shipped planar experiment (pad and silo_cold)."""
TEST_SEARCH_RTOL = 1.0e-9
"""Search-mode rtol of the gate test (CLAUDE.md: rtol <= 1e-9 in tests; the final rtol
stays the shipped 1e-10), as in tests/test_offload.py."""


def _gate_context(repo_root: Path, name: str) -> SearchContext:
    """The SearchContext of run name of the gate fork's silo_screening_2d experiment with
    its shared search block at search_rtol = TEST_SEARCH_RTOL."""
    rr = load_experiment(repo_root / GATE_EXPERIMENT).runs[name]
    ctx = SearchContext.from_run(rr.run, rr.to_vehicle())
    planar = rr.run.planar
    assert planar is not None
    cfg = planar.search.model_copy(update={"search_rtol": TEST_SEARCH_RTOL})
    return dataclasses.replace(ctx, budget=SearchBudget.from_config(cfg, planar.checks))


@pytest.mark.slow
def test_cross_vehicle_decomposition_on_the_gate_fork(repo_root: Path) -> None:
    """The gate fork at the test budget: the pad at its own P* (P_ref; its final
    evaluation, as ``sim.matched_run`` takes a baseline) against silo_cold offloaded in
    stage 1 by its solved x* at P_ref (the solve's final evaluation, through
    ``offload_matched_run``). The residual is below checks.closure_tol_mps and the check
    passes (status explained); the terms sum to the ideal delta-v change, which equals
    c1 ln(m0/(m0 - x*)) with m0 the pad's stack at P_ref from the vehicle's numbers
    (1e-8 m/s); both traces start at their own vehicle's liftoff mass (start-mass errors
    below 1e-6 kg), silo_cold's flight starts at m0 - x* (a cold start burns nothing
    before it) and the pre-flight term is the pad's c1 ln(m0/m_fs) read from the pad's
    trace (1e-8 m/s); the release-speed term and the speed at release equal sqrt(2 a L) for the
    3 g, 100 m push (1e-9 relative; the pad starts from rest); the offload is x* with
    nothing from stage 2; the kg split adds up to x*; the yardstick equals m0 (1 -
    exp(-v/c1s)) with c1s = g0 x the stage-1 screening Isp (1e-9 relative) and the ratio
    (1 - exp(-dD_id/c1)) / (1 - exp(-v/c1s)). The term values are a validation
    measurement (docs/physics.md), not a finding."""
    pad_ctx = _gate_context(repo_root, "pad")
    silo_ctx = _gate_context(repo_root, "silo_cold")
    record = run_search(pad_ctx)
    assert record.status == OK_STATUS and record.final is not None
    p_ref = record.payload_kg
    offload = solve_offload(
        planar_problem_factory(silo_ctx), silo_ctx.vehicle, "stage1", p_ref, verify=False
    )
    assert offload.status == OK_STATUS, (offload.failure_kind, offload.failure_message)
    env, env_silo = pad_ctx.env, silo_ctx.env
    pad = evaluation_matched_run(
        "pad", record.final.at_final, pad_ctx.vehicle, env.omega_p_rads, env.r_datum_m
    )
    silo = offload_matched_run("silo_cold", offload, env_silo.omega_p_rads, env_silo.r_datum_m)
    assert pad is not None and silo is not None and pad.payload_kg == p_ref
    planar = load_experiment(repo_root / GATE_EXPERIMENT).baseline.run.planar
    assert planar is not None
    checks = planar.checks
    out = cross_vehicle_decomposition(silo, pad, checks=checks)
    assert abs(out["xv_residual_mps"]) < checks.closure_tol_mps
    assert out["xv_check"]["status"] == CHECK_PASS
    assert out["xv_status"] == DECOMPOSITION_EXPLAINED
    total = math.fsum(out[f"xv_{term}_mps"] for term in CROSS_VEHICLE_TERMS)
    assert abs(out["xv_ideal_dv_reduction_mps"] - total) < checks.closure_tol_mps
    x = offload.offload_kg
    k = _masses(with_payload(pad_ctx.vehicle, p_ref))
    closed = k["c1"] * math.log(k["m0"] / (k["m0"] - x))
    assert out["xv_ideal_dv_reduction_mps"] == pytest.approx(closed, abs=1e-8)
    # the pairing of trace and vehicle (the closure cannot see the stage-1 load): both
    # traces start at their own vehicle's liftoff mass, silo_cold's at m0 - x* (from the
    # pad's masses); its cold start burns nothing before the flight (m_fs = m0 - x*,
    # pre = 0), so the pre-flight term is the pad's c1 ln(m0/m_fs) from the pad's trace
    for side in ("variant", "baseline"):
        assert abs(out[f"xv_{side}_start_mass_error_kg"]) < 1e-6, side
    assert out["xv_check"]["worst_start_mass_mps"] < checks.closure_tol_mps
    assert silo.trace.y_flight_start is not None and pad.trace.y_flight_start is not None
    m_fs_silo = _m(silo.trace.y_flight_start)
    assert m_fs_silo == pytest.approx(k["m0"] - x, abs=1e-6)
    assert m_fs_silo == pytest.approx(silo.vehicle.liftoff_mass_kg(), abs=1e-6)
    pre_pad = k["c1"] * math.log(k["m0"] / _m(pad.trace.y_flight_start))
    assert out["xv_preflight_mps"] == pytest.approx(pre_pad, abs=1e-8)
    v_exit = math.sqrt(2.0 * SILO_ACCEL_G * G0_MPS2 * SILO_STROKE_M)
    assert out["xv_release_speed_mps"] == pytest.approx(v_exit, rel=1e-9)
    assert out["xv_speed_at_release_mps"] == pytest.approx(v_exit, rel=1e-9)
    assert out["xv_offload_kg"] == pytest.approx(x, abs=1e-6)
    assert out["xv_stage2_offload_kg"] == 0.0 and out["xv_dry_mass_delta_kg"] == 0.0
    split = [out[f"xv_{term}_kg"] for term in CROSS_VEHICLE_TERMS]
    assert math.fsum(split) == pytest.approx(x, rel=1e-12)
    # the yardstick in closed form: the screening's stage-1 term c1s ln(m0/m1) with the
    # loss-averaged Isp, the heating-rule fairing counted as dropped at staging (so the
    # stage-2 term does not move), hence m0 (1 - exp(-v/c1s)); the ratio is then
    # (1 - exp(-dD_id/c1)) / (1 - exp(-v/c1s)) since x* = m0 (1 - exp(-dD_id/c1))
    c1_screening = G0_MPS2 * pad.vehicle.screening_isp_s[0]
    v_rel = out["xv_speed_at_release_mps"]
    yardstick = k["m0"] * (1.0 - math.exp(-v_rel / c1_screening))
    assert out["xv_screening_offload_kg"] == pytest.approx(yardstick, rel=1e-9)
    ratio = (1.0 - math.exp(-closed / k["c1"])) / (1.0 - math.exp(-v_rel / c1_screening))
    assert out["xv_offload_to_screening_ratio"] == pytest.approx(ratio, rel=1e-9)
