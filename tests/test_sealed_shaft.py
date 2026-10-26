"""The sealed shaft and the piston-work record (SP7 step S5; docs/physics.md, "The sealed
shaft"; design 4.8, D-SP7-26, D-SP7-27, the S5 row of section 5).

Every closed-form expectation is computed here from the test's own formulas, never from
the package's. With the bore d (A = pi d^2/4), the gap h_0 below the carriage, the ratio
of specific heats gamma and the push-start pressure p_0 (the ICAO atmosphere at the track
start, 100 m below the mouth: ``atmosphere.ambient_scalar``, validated against ambiance in
tests/test_atmosphere.py), V_0 = A h_0 and V = A (h_0 + s):

- p(s) = p_0 (h_0/(h_0 + s))^gamma, F_p(s) = max(0, p_0 - p(s)) A <= p_0 A, and the work
  done against the column W_p(s) = p_0 A s - p_0 V_0 [1 - (V_0/V)^(gamma - 1)]/(gamma -
  1), against an adaptive quadrature of F_p (1e-9 relative), with the hand numbers of
  survey 07 section 9.2 at sea level (p_atm A = 1.0895 MN; at L = 100 m: 1.088, 1.074 and
  1.001 MN and 107, 99 and 81 MJ for 1, 5 and 20 m gaps);
- a step force-law push (t_r = 0, the power limit never reached), cold, with M = m_v +
  m_c constant: M sddot = F_max - M g sin phi - F_p(s), so (1/2) M v^2 = (F_max - M g sin
  phi) s - W_p(s) at every integrator step, vertical and horizontal; the W_piston_J state
  equals W_p(s) at every step; cold, E_drive = (1/2) M v_e^2 + M g L + W_p(L);
- at the same state (t, s, sdot, m_v, T) the sealed and the vented drive give the same
  drive force under the force law and F_int lower by (m_v/M) F_p (the felt g by F_p/(M
  g0)): every integrator step of the sealed push, cold and hot (both on a 20 t carriage,
  the hot one with f_imp 0.5); under the acceleration law, where no cap binds, the drive
  force higher by F_p and F_int unchanged (cold, no carriage; hot, a step command on a
  20 t carriage with f_imp 0.5), and where both commands sit at the same cap, the drive
  force the same (bit for bit) and F_int lower by (m_v/M) F_p (the cold push's power cap;
  the hot push capped by F_max from push start); at 1e-9;
- the assist energy identity with the column, work_drive + work_thrust = delta_mech +
  massflow + dissipated + W_p, < 1e-9 (CLAUDE.md 1e-6), cold and hot, both laws, through
  ``sim.simulate``; the budget's own residual is W_p, and AssistEnergyBudget keeps its
  five fields;
- a stall against the column at push start (F_max + (1 - f_imp) T(0) <= M_0 g + F_p(L));
- a power-limited push whose speed peaks where P_max / sdot = M g + F_p(s) and falls
  after it, and a release speed just below that peak passed over;
- the metrics, summary rows, assumption lines, config, refusals (sealed keys on a vented
  shaft, a bore at or below the body, a sealed shaft with the force law's stop taper, a
  sealed track starting below the ICAO atmosphere's floor);
- vented linear-motor runs and a constant_accel run byte-identical to the code before
  S5 (tests/vented_pins_support.py, tests/data/vented_pins.json, captured from that
  code: exact in the capture environment, the metric keys everywhere; the planar pin
  covers the flown push's states, events, flags, status, lines, track metrics, time
  series and budget).

Closed forms at 1e-9 relative with rtol 1e-11 (CLAUDE.md: <= 1e-9).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import itertools
import math
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, get_args

import numpy as np
import pytest
import yaml
from pydantic import ValidationError
from scipy.integrate import quad
from scipy.optimize import minimize_scalar

from launchsim import config, sim, summary
from launchsim.assist import build_assist
from launchsim.assist.linear_motor import (
    SEALED_TAPER_REFUSAL,
    WORK_STATE,
    LinearMotorAssist,
    SealedShaft,
    ShaftKind,
)
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.atmosphere import ambient_scalar, standard_atmosphere
from launchsim.config import ConstantAccelConfig, LinearMotorConfig, resolve_run
from launchsim.constants import (
    ALT_AMBIANCE_MIN_M,
    G0_MPS2,
    MU_EARTH_M3S2,
    OMEGA_EARTH_RADS,
    R_EARTH_M,
)
from launchsim.dynamics import InverseSquareGravity, StateLayout, track_observables
from launchsim.guidance import GuidanceSpec
from launchsim.losses import (
    AssistEnergyBudget,
    PistonWork,
    assist_energy_budget,
    piston_work,
)
from launchsim.metrics import LINEAR_MOTOR_METRICS, SEALED_SHAFT_METRICS
from launchsim.phases import ASSIST_KIND, IgnitionSpec, IntegratorSettings, PhaseResult
from launchsim.phases.planar import PlanarEnvironment, PlanarPlanner
from launchsim.phases.prelude import DRIVE_STALL, TrackExit, fly_track
from launchsim.phases.trace import RunTrace
from launchsim.phases.vertical import VerticalPlanner
from launchsim.vehicle import Vehicle

REPO = Path(__file__).resolve().parents[1]
G = MU_EARTH_M3S2 / R_EARTH_M**2
"""The 1-D track's g_eff [m/s^2] (omega_p = 0)."""
L = 100.0
SILO = StraightTrack(L, VERTICAL, -L)
FLAT = StraightTrack(L, 0.0, 0.0)
SETTINGS = IntegratorSettings(rtol=1e-11)
REL = 1e-9
A_BRAKE = 5.0 * G0_MPS2
ETA = 0.5
M_C = 20_000.0
"""The carriage mass [kg] of force_cold, force_hot and accel_hot_uncapped."""
COLD = IgnitionSpec(0.5)
"""Stage 1 lit 0.5 s after the release: the push is cold."""
HOT = IgnitionSpec(-2.0, reference="push_start")
"""Lit 2 s (the F9's own ramp) before the push start: full thrust on the whole push."""
BORE_M = 3.7
GAP_M = 5.0
GAMMA = 1.4
P0_PA = ambient_scalar(-L)[0]
"""The ICAO pressure at the silo's track start, 100 m below the mouth [Pa]."""
AREA_M2 = math.pi * BORE_M**2 / 4.0
SHAFT = SealedShaft(BORE_M, GAP_M, GAMMA, P0_PA)


def p_closed(s: float, p0: float = P0_PA, h0: float = GAP_M) -> float:
    """p_0 (h_0/(h_0 + s))^gamma [Pa]."""
    return p0 * (h0 / (h0 + s)) ** GAMMA


def f_closed(s: float, p0: float = P0_PA, h0: float = GAP_M, area: float = AREA_M2) -> float:
    """max(0, p_0 - p(s)) A [N]."""
    return max(0.0, p0 - p_closed(s, p0, h0)) * area


def w_closed(s: float, p0: float = P0_PA, h0: float = GAP_M, area: float = AREA_M2) -> float:
    """p_0 A s - p_0 V_0 [1 - (V_0/V)^(gamma - 1)]/(gamma - 1) [J]."""
    v0, v = area * h0, area * (h0 + s)
    return p0 * area * s - p0 * v0 * (1.0 - (v0 / v) ** (GAMMA - 1.0)) / (GAMMA - 1.0)


def _load(name: str) -> ModuleType:
    """A tests/ support module loaded by path (any pytest import mode)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _model(
    control: str = "force",
    *,
    f_max: float,
    p_max: float,
    t_r: float = 0.5,
    m_c: float = 0.0,
    a_cmd: float | None = None,
    taper: float | None = None,
    f_imp: float = 0.0,
    shaft: SealedShaft | None = SHAFT,
) -> LinearMotorAssist:
    """A linear motor with the test's brake (5 g0) and efficiency (0.5), sealed by
    default."""
    return LinearMotorAssist(
        control=control,
        force_max_N=f_max,
        power_max_W=p_max,
        rise_time_s=t_r,
        carriage_mass_kg=m_c,
        brake_decel_mps2=A_BRAKE,
        accel_command_mps2=a_cmd,
        stop_taper_m=taper,
        efficiency=ETA,
        f_imp=f_imp,
        g_eff_mps2=G,
        shaft=shaft,
    )


def _specs(vehicle: Vehicle, first: IgnitionSpec) -> dict[str, IgnitionSpec]:
    specs = {name: IgnitionSpec() for name in vehicle.stage_names}
    specs[vehicle.stage_names[0]] = first
    return specs


def _simulate(
    vehicle: Vehicle,
    model: LinearMotorAssist,
    first: IgnitionSpec = COLD,
    track: StraightTrack = SILO,
) -> sim.Result:
    """The 1-D run of the track to stage-1 burnout (rtol 1e-11)."""
    return sim.simulate(
        vehicle=vehicle,
        ignition=_specs(vehicle, first),
        gravity=InverseSquareGravity(MU_EARTH_M3S2),
        g_eff_mps2=G,
        assist=model,
        track=track,
        start=None,
        end="stage1_burnout",
        settings=SETTINGS,
    )


def _push(
    vehicle: Vehicle, model: LinearMotorAssist, track: StraightTrack
) -> tuple[TrackExit | None, RunTrace]:
    """The push alone: ``fly_track`` in the 1-D layout (no release map, so a horizontal
    track flies too), cold, vacuum thrust."""
    planner = VerticalPlanner(
        vehicle,
        _specs(vehicle, COLD),
        InverseSquareGravity(MU_EARTH_M3S2),
        G,
        "stage1_burnout",
        SETTINGS,
    )
    tr = planner.new_builder()
    exit_ = fly_track(
        tr, model, track, COLD, vehicle=vehicle, settings=SETTINGS, g_eff_mps2=G, p_amb_pa=0.0
    )
    return exit_, tr.finish()


def _assist_phases(result: sim.Result) -> list[PhaseResult]:
    return [p for p in result.phases if p.spec.kind == ASSIST_KIND]


def _steps(phases: list[PhaseResult]) -> list[tuple[float, np.ndarray, PhaseResult]]:
    """(t, state, phase) at every integrator step of the ASSIST phases."""
    return [
        (float(t), np.asarray(res.y[:, i], dtype=float), res)
        for res in phases
        for i, t in enumerate(res.t)
    ]


def _get(res: PhaseResult, y: np.ndarray, name: str) -> float:
    return float(res.spec.params.layout.get(y, name))


# ------------------------------------------------------------------ the closed forms


@pytest.mark.parametrize("gap", [0.5, 1.0, 5.0, 20.0])
def test_pressure_force_and_work_against_their_closed_forms(gap: float) -> None:
    """p(s), F_p(s) and W_p(s) against the test's formulas: p at 1e-13, F_p at 1e-13 of
    its bound p_0 A (the expm1 form keeps the digits the plain difference loses near s =
    0), W_p against the adaptive quadrature of F_p from 0 to s at 1e-9 relative for s >=
    1e-3 m (and the plain closed form at 1e-11 for s >= 0.1 m; below 1e-3 m the series
    W_p = p_0 A gamma s^2/(2 h_0) [1 - (gamma + 1) s/(3 h_0)] within 1e-15 p_0 A s), F_p
    <= p_0 A and increasing, W_p increasing, and 0 at and below s = 0 (the column is
    never compressed: p_0 there)."""
    shaft = SealedShaft(BORE_M, gap, GAMMA, P0_PA)
    bound = P0_PA * AREA_M2
    assert math.isclose(shaft.area_m2, AREA_M2, rel_tol=1e-15)
    assert math.isclose(shaft.force_bound_N, bound, rel_tol=1e-15)
    previous_f = previous_w = 0.0
    for s in (1e-6, 1e-3, 0.1, 0.5, 3.0, 10.0, 37.3, 76.0, 100.0, 300.0, 1e4):
        assert math.isclose(shaft.pressure_pa(s), p_closed(s, h0=gap), rel_tol=1e-13)
        f = shaft.force_N(s)
        assert abs(f - f_closed(s, h0=gap)) <= 1e-13 * bound
        assert 0.0 < f < bound and f > previous_f
        w = shaft.work_J(s)
        if s < 1e-3:
            # the plain difference p_0 - p(s) keeps too few digits here for a quadrature
            # at 1e-9: the series W = p_0 A gamma s^2/(2 h_0) [1 - (gamma + 1) s/(3 h_0)]
            # is good to (s/h_0)^2 <= 4e-12; the closed form W = p_0 A [s - h_0 (1 -
            # (h_0/(h_0 + s))^(gamma - 1))/(gamma - 1)] cancels to s/h_0 relative here, so
            # its error is held absolute, below 1e-15 p_0 A s (1e-15 J at s = 1 um)
            x = s / gap
            series = bound * GAMMA * s * x / 2.0 * (1.0 - (GAMMA + 1.0) * x / 3.0)
            assert abs(w - series) <= 1e-15 * bound * s
        else:
            integral, err = quad(
                lambda u: f_closed(u, h0=gap), 0.0, s, epsabs=0.0, epsrel=1e-12, limit=200
            )
            assert math.isclose(w, integral, rel_tol=REL) and err <= 1e-10 * integral
            if s >= 0.1:  # the plain closed form's own cancellation below
                assert math.isclose(w, w_closed(s, h0=gap), rel_tol=1e-11)
        assert w > previous_w
        previous_f, previous_w = f, w
    for s in (0.0, -1e-9, -1.0):
        assert shaft.force_N(s) == 0.0 and shaft.work_J(s) == 0.0
        assert shaft.pressure_pa(s) == P0_PA


def test_hand_numbers_of_the_trapped_column_at_sea_level() -> None:
    """Survey 07 section 9.2 (sea level, 3.7 m bore, L = 100 m): p_atm A = 1.0895 MN (the
    README's 1.1 MN), and for 1, 5 and 20 m gaps p_end/p_0 = 0.0016, 0.014 and 0.081,
    the force at the exit 1.088, 1.074 and 1.001 MN, the work 107, 99 and 81 MJ (the
    quoted digits)."""
    p_sl = ambient_scalar(0.0)[0]
    assert f"{SealedShaft(BORE_M, 1.0, GAMMA, p_sl).force_bound_N / 1e6:.4f}" == "1.0895"
    table = {
        1.0: ("0.0016", "1.088", "107"),
        5.0: ("0.014", "1.074", "99"),
        20.0: ("0.081", "1.001", "81"),
    }
    for gap, (ratio, force, work) in table.items():
        shaft = SealedShaft(BORE_M, gap, GAMMA, p_sl)
        digits = len(ratio.split(".")[1])
        assert f"{shaft.pressure_pa(L) / p_sl:.{digits}f}" == ratio
        assert f"{shaft.force_N(L) / 1e6:.3f}" == force
        assert f"{shaft.work_J(L) / 1e6:.0f}" == work


def test_sealed_shaft_and_model_refusals(f9_vehicle: Vehicle) -> None:
    """SealedShaft refuses a bore, gap or p_0 not finite and > 0 and a gamma not finite
    and > 1; the model refuses a shaft that is not a SealedShaft and a sealed shaft under
    the force law with a stop taper (SEALED_TAPER_REFUSAL), and accepts one with a zero
    taper and under the acceleration law's taper; the vented model has no extra state,
    the sealed one W_piston_J, starting at 0 J."""
    for kw in (
        {"bore_m": 0.0},
        {"gap_m": -1.0},
        {"p0_pa": math.inf},
        {"bore_m": math.nan},
        {"gamma": 1.0},
        {"gamma": math.nan},
    ):
        with pytest.raises(ValueError, match="sealed shaft"):
            dataclasses.replace(SHAFT, **kw)
    f = f9_vehicle.liftoff_mass_kg() * 4.0 * G
    with pytest.raises(ValueError, match="shaft must be a SealedShaft or None"):
        _model(f_max=f, p_max=f * 100.0, shaft="sealed")  # type: ignore[arg-type]
    with pytest.raises(ValueError) as info:
        _model(f_max=f, p_max=f * 100.0, taper=10.0)
    assert str(info.value) == SEALED_TAPER_REFUSAL
    _model(f_max=f, p_max=f * 100.0, taper=0.0)
    accel = _model("acceleration", f_max=f, p_max=f * 100.0, a_cmd=G0_MPS2, taper=10.0)
    assert accel.extra_state_names == (WORK_STATE,) and accel.sealed
    assert list(accel.initial_extra()) == [0.0]
    vented = _model(f_max=f, p_max=f * 100.0, shaft=None, taper=10.0)
    assert vented.extra_state_names == () and not vented.sealed
    assert vented.initial_extra().shape == (0,) and vented.piston_force_N(50.0) == 0.0


# ----------------------------------------------------------------- the flown push


@pytest.mark.parametrize("track", [SILO, FLAT], ids=["vertical", "horizontal"])
def test_step_push_follows_the_energy_closed_form(
    track: StraightTrack, f9_vehicle: Vehicle
) -> None:
    """Cold, the force law stepping to F_max at push start (t_r = 0), P_max never
    reached: M sddot = F_max - M g sin phi - F_p(s), so (1/2) M v^2 = (F_max - M g sin
    phi) s - W_p(s) at every integrator step (v at 1e-9 of the exit speed), the release
    at L at v_e from the same form; the W_piston_J state is W_p(s) at every step (1e-9 of
    W_p(L)); F_p <= p_0 A at every step; cold, E_drive = (1/2) M v_e^2 + M g sin phi L +
    W_p(L) (1e-9)."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    model = _model(f_max=f_max, p_max=f_max * 1e3, t_r=0.0)
    exit_, trace = _push(f9_vehicle, model, track)
    assert exit_ is not None and trace.status == "nominal" and trace.flags == ()
    g_axial = G * math.sin(track.phi(0.0))
    v_e = math.sqrt(2.0 * ((f_max - m * g_axial) * L - w_closed(L)) / m)
    assert math.isclose(exit_.sdot_mps, v_e, rel_tol=REL)
    phases = trace.assist_phases()
    count = 0
    for t, y, res in _steps(phases):
        s, sdot = _get(res, y, "s_m"), _get(res, y, "sdot_mps")
        v = math.sqrt(max(0.0, 2.0 * ((f_max - m * g_axial) * s - w_closed(s)) / m))
        assert abs(sdot - v) <= REL * v_e, (t, sdot, v)
        assert abs(_get(res, y, WORK_STATE) - w_closed(s)) <= REL * w_closed(L)
        assert res.spec.params.assist.piston_force_N(s) <= SHAFT.force_bound_N
        count += 1
    assert count > 20
    b = assist_energy_budget(phases, phases[0].spec.params.layout, 0.0, G)
    expected = 0.5 * m * v_e**2 + m * g_axial * L + w_closed(L)
    assert math.isclose(b.work_drive, expected, rel_tol=REL)


def _limit_cases(m: float) -> dict[str, tuple[LinearMotorAssist, IgnitionSpec]]:
    """Sealed pushes of the identity and the interface test: the force law cold (20 t
    carriage, power phase) and hot (20 t carriage, f_imp 0.5, power phase); the
    acceleration law cold (no carriage), capped by its power limit late in the push; hot
    with a step command capped by F_max from push start (no carriage, f_imp 0: a rising
    command would ask for a negative drive force at push start under the full thrust,
    ``drive_limit``, as in tests/test_linear_motor.py); and hot with a step command that
    no cap reaches (20 t carriage, f_imp 0.5: F_max twice the reference and P_max far
    above the push's power, the command M (a_cmd + g) - T_sys + F_p positive)."""
    f_max = m * (3.0 * G0_MPS2 + G)
    return {
        "force_cold": (_model(f_max=f_max, p_max=f_max * 50.0, m_c=M_C), COLD),
        "force_hot": (_model(f_max=f_max, p_max=f_max * 40.0, m_c=M_C, f_imp=0.5), HOT),
        "accel_cold": (
            _model("acceleration", f_max=2 * f_max, p_max=f_max * 50.0, a_cmd=3 * G0_MPS2),
            COLD,
        ),
        "accel_hot": (
            _model(
                "acceleration", f_max=0.6 * f_max, p_max=f_max * 1e3, a_cmd=3 * G0_MPS2, t_r=0.0
            ),
            HOT,
        ),
        "accel_hot_uncapped": (
            _model(
                "acceleration",
                f_max=2 * f_max,
                p_max=f_max * 1e3,
                a_cmd=3 * G0_MPS2,
                t_r=0.0,
                m_c=M_C,
                f_imp=0.5,
            ),
            HOT,
        ),
    }


CASES = ["force_cold", "force_hot", "accel_cold", "accel_hot", "accel_hot_uncapped"]


@pytest.mark.parametrize("case", CASES)
def test_assist_energy_identity_with_the_column(case: str, f9_vehicle: Vehicle) -> None:
    """work_drive + work_thrust = delta_mech + massflow + dissipated + W_p closes to 1e-9
    (recomputed from the fields; CLAUDE.md 1e-6) with the sealed model through
    ``sim.simulate``, cold and hot, both laws (the five pushes of ``_limit_cases``); the
    budget's own residual is W_p (the record holds the term the budget does not: 1e-9 of
    W_p), dissipated is 0, the PistonWork quadrature equals its closed form W_p(s_end) to
    1e-9, the metric assist_energy_residual_rel is the record's identity residual, and
    the column's force stays below p_0 A at every step."""
    model, first = _limit_cases(f9_vehicle.liftoff_mass_kg())[case]
    result = _simulate(f9_vehicle, model, first)
    assert result.status == "nominal"
    b = result.assist_budget
    assert b is not None and b.dissipated == 0.0
    phases = _assist_phases(result)
    pw = piston_work(phases, phases[0].spec.params.layout, SHAFT)
    lhs = b.work_drive + b.work_thrust
    residual = lhs - b.delta_mech - b.massflow_term - b.dissipated - pw.work_J
    assert abs(residual) / lhs < REL
    assert pw.identity_residual_rel(b) < REL and pw.closed_form_residual_rel() < REL
    assert math.isclose(b.residual_J(), pw.work_J, rel_tol=REL)
    assert result.metrics["assist_energy_residual_rel"] == pw.identity_residual_rel(b)
    s_end = _get(phases[-1], phases[-1].y_end, "s_m")
    assert math.isclose(pw.closed_form_J, w_closed(s_end), rel_tol=1e-12)
    assert 0.03 < pw.work_J / lhs < 0.06  # about 4% of the push energy (survey 07: 4.4%)
    assert all(
        res.spec.params.assist.piston_force_N(_get(res, y, "s_m")) < SHAFT.force_bound_N
        for _t, y, res in _steps(phases)
    )
    if first is HOT:
        assert b.work_thrust > 0.0 and b.massflow_term > 0.0


@pytest.mark.parametrize("case", CASES)
def test_column_share_of_the_interface_force(case: str, f9_vehicle: Vehicle) -> None:
    """At every integrator step of the sealed push the sealed drive and the same drive
    vented, evaluated at the same state (t, s, sdot, m_v, the thrust): under the force
    law the drive force is the same (bit for bit) and F_int and the felt g are lower by
    (m_v/M) F_p and F_p/(M g0) (1e-9 of F_max and of the felt g); under the acceleration
    law, at every step where the sealed command (the vented one plus F_p) is flown
    uncapped, the drive force is higher by F_p and F_int is unchanged, and at every step
    where the vented command already exceeds the cap min(F_max, P_max/sdot), so both
    sit at it, the drive force is the same (bit for bit) and F_int is lower by (m_v/M)
    F_p, as under the force law (1e-9 of F_max). Each acceleration-law push but
    accel_hot has more than five uncapped steps (accel_hot, capped from push start,
    none), and accel_cold (late) and accel_hot (throughout) more than five steps at the
    cap; the extra rate is F_p sdot (1e-12 relative, 1e-6 W absolute)."""
    model, first = _limit_cases(f9_vehicle.liftoff_mass_kg())[case]
    result = _simulate(f9_vehicle, model, first)
    assert result.status == "nominal"
    uncapped = at_cap = 0
    for t, y, res in _steps(_assist_phases(result)):
        params = res.spec.params
        sealed = params.assist
        vented = dataclasses.replace(sealed, shaft=None)
        s, sdot, m_v = _get(res, y, "s_m"), _get(res, y, "sdot_mps"), _get(res, y, "m_kg")
        thrust = params.thrust_N(t)
        m_c = params.carriage_mass_kg
        fs = sealed.state_rate(t, s, sdot, params.extra(y), m_v, m_c, thrust, G, SILO)
        fv = vented.state_rate(t, s, sdot, np.zeros(0), m_v, m_c, thrust, G, SILO)
        total = m_v + params.carriage_mass_kg
        piston = f_closed(s)
        scale = model.force_max_N
        assert fs.extra_rate.shape == (1,) and fs.extra_rate[0] == pytest.approx(
            piston * sdot, rel=1e-12, abs=1e-6
        )
        if model.control == "force":
            assert fs.drive_force_N == fv.drive_force_N
            expected = fv.interface_force_N - (m_v / total) * piston
            assert abs(fs.interface_force_N - expected) <= REL * scale
            felt_s = track_observables(t, y, params)["felt_g"]
            felt_v = (fv.interface_force_N + thrust) / m_v / G0_MPS2
            assert abs(felt_s - (felt_v - piston / (total * G0_MPS2))) <= REL * felt_v
        else:
            command = vented.command_force_N(t, s, total, (1 - model.f_imp) * thrust, G, L)
            cap = min(model.force_max_N, model.power_max_W / max(sdot, 1e-300))
            if command + piston < cap * (1 - 1e-9):
                uncapped += 1
                assert abs(fs.drive_force_N - (fv.drive_force_N + piston)) <= REL * scale
                assert abs(fs.interface_force_N - fv.interface_force_N) <= REL * scale
            elif command > cap * (1 + 1e-9):
                at_cap += 1
                assert fs.drive_force_N == fv.drive_force_N
                expected = fv.interface_force_N - (m_v / total) * piston
                assert abs(fs.interface_force_N - expected) <= REL * scale
    if case == "accel_hot":
        assert uncapped == 0 and at_cap > 5
    elif model.control == "acceleration":
        assert uncapped > 5
    if case == "accel_cold":
        assert at_cap > 5


def test_metrics_of_a_sealed_push_and_none_on_a_vented_one(f9_vehicle: Vehicle) -> None:
    """The sealed run's metric keys are the vented run's with SEALED_SHAFT_METRICS
    appended, in order, after LINEAR_MOTOR_METRICS; piston_work_J the record's work done
    against the column, piston_force_peak_N F_p at the release (its largest; below p_0 A)
    and bore_pressure_release_pa p(s_release), from the test's formulas; the vented run
    (the same drive, shaft None) carries none of them. Under the force law the sealed
    push exits slower and its interface-force peak is lower."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    sealed = _model(f_max=f_max, p_max=f_max * 50.0)
    vented = dataclasses.replace(sealed, shaft=None)
    rs, rv = _simulate(f9_vehicle, sealed), _simulate(f9_vehicle, vented)
    assert list(rs.metrics) == [*rv.metrics, *SEALED_SHAFT_METRICS]
    assert not set(SEALED_SHAFT_METRICS) & set(rv.metrics)
    keys = list(rs.metrics)
    assert keys.index(LINEAR_MOTOR_METRICS[-1]) < keys.index(SEALED_SHAFT_METRICS[0])
    phases = _assist_phases(rs)
    pw = piston_work(phases, phases[0].spec.params.layout, SHAFT)
    s_rel = _get(phases[-1], phases[-1].y_end, "s_m")
    assert abs(s_rel - L) <= 1e-9
    met = rs.metrics
    assert met["piston_work_J"] == pw.work_J
    assert math.isclose(met["piston_force_peak_N"], f_closed(s_rel), rel_tol=1e-12)
    assert met["piston_force_peak_N"] < P0_PA * AREA_M2
    assert math.isclose(met["bore_pressure_release_pa"], p_closed(s_rel), rel_tol=1e-12)
    assert met["exit_speed_mps"] < rv.metrics["exit_speed_mps"]
    assert met["interface_force_peak_N"] < rv.metrics["interface_force_peak_N"]
    assert met["assist_energy_residual_rel"] < REL
    assert rv.metrics["assist_energy_residual_rel"] == rv.assist_budget.residual_rel()  # type: ignore[union-attr]


@pytest.mark.parametrize("m_c", [0.0, M_C], ids=["no_carriage", "carriage_20t"])
def test_a_sealed_push_released_at_a_target_speed(m_c: float, f9_vehicle: Vehicle) -> None:
    """The force law, cold, released at 50 m/s on the 100 m silo (F_max = m0 (3 g0 + g),
    P_max = 50 F_max; no carriage, and a 20 t carriage): the column acts from push start
    to that release, so the release state is the last ASSIST phase's end (trigger
    target_speed, s_release < L, the exit speed the release speed at 1e-9);
    piston_force_peak_N = F_p(s_release) and bore_pressure_release_pa = p(s_release) at
    1e-12, piston_work_J = W_p(s_release) < W_p(L) at 1e-9, the identity with the column
    < 1e-9, the facility max(L, s_release + v^2/(2 a_b)); the stall guard, which uses
    F_p(L), lets this push fly. The same drive vented releases at the same speed nearer
    the track start and sooner: the sealed release position and push time are larger,
    as the sealed column line says, and the line names them, not the exit speed."""
    v_release = 50.0
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    base = _model(f_max=f_max, p_max=f_max * 50.0, m_c=m_c)
    sealed = dataclasses.replace(base, release_speed_mps=v_release)
    vented = dataclasses.replace(sealed, shaft=None)
    rs, rv = _simulate(f9_vehicle, sealed), _simulate(f9_vehicle, vented)
    assert rs.status == rv.status == "nominal" and rs.flags == []
    met = rs.metrics
    assert met["release_trigger"] == rv.metrics["release_trigger"] == "target_speed"
    phases = _assist_phases(rs)
    s_rel = _get(phases[-1], phases[-1].y_end, "s_m")
    assert abs(met["release_position_m"] - s_rel) <= 1e-12 * L and 0.0 < s_rel < L - 1.0
    assert math.isclose(met["exit_speed_mps"], v_release, rel_tol=REL)
    assert math.isclose(met["piston_force_peak_N"], f_closed(s_rel), rel_tol=1e-12)
    assert math.isclose(met["bore_pressure_release_pa"], p_closed(s_rel), rel_tol=1e-12)
    assert math.isclose(met["piston_work_J"], w_closed(s_rel), rel_tol=REL)
    assert met["piston_work_J"] < 0.9 * w_closed(L)
    pw = piston_work(phases, phases[0].spec.params.layout, SHAFT)
    budget = rs.assist_budget
    assert budget is not None and pw.identity_residual_rel(budget) < REL
    assert met["assist_energy_residual_rel"] == pw.identity_residual_rel(budget)
    assert met["facility_length_m"] == max(L, s_rel + v_release**2 / (2.0 * A_BRAKE))
    # the vented twin: the same release speed, reached nearer the start and sooner
    assert math.isclose(rv.metrics["exit_speed_mps"], v_release, rel_tol=REL)
    assert met["release_position_m"] > rv.metrics["release_position_m"]
    assert met["push_time_s"] > rv.metrics["push_time_s"]
    column = next(line for line in rs.assumptions if line.startswith("linear_motor: sealed shaft:"))
    assert "the release position and the push time are larger than in a vented shaft" in column
    assert "the exit speed is lower" not in column


def _dense_speed_peak(phases: list[PhaseResult]) -> tuple[float, float]:
    """(the largest sdot [m/s], s there [m]) on each ASSIST phase's dense output: the
    largest of 4001 points, refined between its neighbours by a bounded scalar search
    (time tolerance 1e-12 s)."""
    best = (-math.inf, math.nan)
    for res in phases:
        dense = res.dense
        assert dense is not None
        layout = res.spec.params.layout
        tt = np.linspace(res.t[0], res.t[-1], 4001)
        k = int(np.asarray(layout.get(dense(tt), "sdot_mps")).argmax())
        lo, hi = tt[max(k - 1, 0)], tt[min(k + 1, tt.size - 1)]

        def minus_speed(t: float, dense: Any = dense, layout: StateLayout = layout) -> float:
            return -float(layout.get(dense(t), "sdot_mps"))

        top = minimize_scalar(
            minus_speed, bounds=(lo, hi), method="bounded", options={"xatol": 1e-12}
        )
        y_top = dense(float(top.x))
        v_top = float(layout.get(y_top, "sdot_mps"))
        if v_top > best[0]:
            best = (v_top, float(layout.get(y_top, "s_m")))
    return best


def test_a_sealed_push_s_speed_can_peak_and_fall_inside_the_track(f9_vehicle: Vehicle) -> None:
    """The force law, cold, no carriage, a power corner P_max / F_max of 2 m/s on the 100
    m silo (review pass 3, P3-m1): in the power phase the speed rises to the terminal
    speed P_max / (M g + F_p(s)), which falls as the column grows, so the speed peaks
    inside the track (at s of about 12 m, where P_max / sdot = M g + F_p(s), 1e-8) and
    falls to the exit, more than 0.1 m/s below the peak, with steps where it falls.
    With a release speed 1e-3 m/s below that peak the push releases there (trigger
    target_speed); 1e-6 m/s below it the upward crossing lies inside one integrator step
    and is passed over, so the push releases at the track end with the flag
    release_speed_not_reached although it reached the release speed: the miss the
    sealed column line states (docs/physics.md, "The sealed shaft", Speed along the
    stroke). The column line itself is written out in ``test_sealed_assumption_lines``."""
    m = f9_vehicle.liftoff_mass_kg()
    f_max = m * (3.0 * G0_MPS2 + G)
    p_max = 2.0 * f_max
    model = _model(f_max=f_max, p_max=p_max)
    exit_, trace = _push(f9_vehicle, model, SILO)
    assert exit_ is not None and trace.status == "nominal" and trace.flags == ()
    phases = trace.assist_phases()
    v_peak, s_peak = _dense_speed_peak(phases)
    assert 1.0 < s_peak < 0.5 * L and v_peak > exit_.sdot_mps + 0.1
    assert math.isclose(p_max / v_peak, m * G + f_closed(s_peak), rel_tol=1e-8)
    speeds = [_get(res, y, "sdot_mps") for _t, y, res in _steps(phases)]
    assert sum(b < a for a, b in itertools.pairwise(speeds)) > 10
    found = dataclasses.replace(model, release_speed_mps=v_peak - 1e-3)
    exit_found, trace_found = _push(f9_vehicle, found, SILO)
    assert exit_found is not None and exit_found.release_trigger == "target_speed"
    assert math.isclose(exit_found.sdot_mps, v_peak - 1e-3, rel_tol=REL)
    assert exit_found.release_position_m < s_peak and trace_found.flags == ()
    missed = dataclasses.replace(model, release_speed_mps=v_peak - 1e-6)
    exit_missed, trace_missed = _push(f9_vehicle, missed, SILO)
    assert exit_missed is not None and exit_missed.release_trigger == "track_end"
    assert exit_missed.sdot_mps == exit_.sdot_mps
    assert len(trace_missed.flags) == 1
    assert trace_missed.flags[0].startswith("release_speed_not_reached: the push reached")


def test_stall_against_the_column_at_push_start(f9_vehicle: Vehicle) -> None:
    """F_max + (1 - f_imp) T(0) <= M_0 g + F_p(L) with F_max above M_0 g: the sealed push
    stops at push start with status drive_stall and the column's flag (written out: the
    stack's momentum, a rising thrust and a falling mass not credited), its sealed
    metrics a zero work and peak force and no release pressure; the same drive vented
    flies; F_max just above M_0 g + F_p(L) pushes the sealed stack to the track end
    (slowly: about 5.7 m/s, so the run then falls back). The guard is conservative: a
    step push with F_max - M_0 g = 0.95 F_p(L), between W_p(L)/L and F_p(L), would reach L
    on its momentum (docs/physics.md, "Stall against the column", measured with the guard
    removed), and it is refused all the same; with a release speed of 3 m/s, which that
    push would reach at s = 3.61 m, it is refused too, and the flag adds the early
    release to what the rule does not credit."""
    m = f9_vehicle.liftoff_mass_kg()
    column = f_closed(L)
    f_max = m * G + 0.5 * column
    model = _model(f_max=f_max, p_max=f_max * 1e3)
    result = _simulate(f9_vehicle, model)
    assert result.status == DRIVE_STALL
    bound = SHAFT.force_bound_N
    assert result.flags == [
        "drive_stall: the drive at F_max and the thrust at push start cannot hold the stack "
        "against the sealed shaft's trapped column at the track end: F_max + (1 - f_imp) "
        f"T(0) = {f_max:.6g} N <= M_0 g_eff sin phi + F_p(L) = {m * G + column:.6g} N "
        f"(F_max = {f_max:.6g} N, T(0) = 0 N, f_imp = 0, M_0 = {m:.6g} kg, F_p(L) = "
        f"{column:.6g} N of the bound p_0 A = {bound:.6g} N); the push could stop in the "
        "shaft (the stack's momentum, a rising thrust and a falling mass are not "
        "credited), so the run stopped on the track at push start (nothing moved; the felt "
        "g and interface-force metrics are None)"
    ]
    met = result.metrics
    assert met["piston_work_J"] == 0.0 and met["piston_force_peak_N"] == 0.0
    assert met["bore_pressure_release_pa"] is None and met["interface_force_peak_N"] is None
    assert _simulate(f9_vehicle, dataclasses.replace(model, shaft=None)).status == "nominal"
    above = _model(f_max=(m * G + column) * (1.0 + 1e-3), p_max=f_max * 1e3)
    flown = _simulate(f9_vehicle, above)  # released slowly at L, it then falls back
    assert flown.status != DRIVE_STALL and flown.metrics["release_trigger"] == "track_end"
    inside = m * G + 0.95 * column  # (F_max - M g) L > W_p(L): it would reach L; refused
    assert (inside - m * G) * L > w_closed(L)
    refused = _simulate(f9_vehicle, _model(f_max=inside, p_max=inside * 1e3, t_r=0.0))
    assert refused.status == DRIVE_STALL
    # with a release speed the flag also names the early release it does not credit
    # (review pass 3, P3H-m2: 3 m/s would be reached at s = 3.61 m, the guard removed)
    early = dataclasses.replace(
        _model(f_max=inside, p_max=inside * 1e3, t_r=0.0), release_speed_mps=3.0
    )
    stalled = _simulate(f9_vehicle, early)
    assert stalled.status == DRIVE_STALL and len(stalled.flags) == 1
    assert (
        "the push could stop in the shaft (the stack's momentum, a rising thrust, a falling "
        "mass and a release at the release speed before the track end, where the column is "
        "below F_p(L), are not credited), so the run stopped on the track at push start"
    ) in stalled.flags[0]


def test_assist_energy_budget_keeps_its_fields() -> None:
    """D-SP7-26 and D-SP7-27: AssistEnergyBudget keeps exactly its five fields (the 1-D
    golden dump compares them; tests/test_golden_dump_fields.py pins them too); the
    column's work lives in PistonWork, a separate frozen record (work_J, closed_form_J),
    not a subclass; sim.Result gains no field."""
    names = tuple(f.name for f in dataclasses.fields(AssistEnergyBudget))
    assert names == ("work_drive", "work_thrust", "delta_mech", "massflow_term", "dissipated")
    assert tuple(f.name for f in dataclasses.fields(PistonWork)) == ("work_J", "closed_form_J")
    assert not issubclass(PistonWork, AssistEnergyBudget)
    assert PistonWork.__dataclass_params__.frozen  # type: ignore[attr-defined]
    assert "piston" not in " ".join(f.name for f in dataclasses.fields(sim.Result))
    assert piston_work([], StateLayout(("s_m", WORK_STATE)), SHAFT) == PistonWork(0.0, 0.0)


# -------------------------------------------------------------- the planar prelude


def test_a_planar_sealed_push_closes_its_identity_and_writes_its_metrics(
    f9_vehicle: Vehicle,
) -> None:
    """The planar prelude (28.5 deg site, the track's g_eff = g_ref) of a sealed cold
    force-law push: the identity with the column < 1e-9, the W_piston_J state on W_p(s)
    at every step, and ``planar_track_metrics`` writes SEALED_SHAFT_METRICS after the
    linear motor's metrics with the residual of the identity with the column."""
    from launchsim.metrics_planar import planar_track_metrics, sample_trace_planar

    omega = OMEGA_EARTH_RADS * math.cos(math.radians(28.5))
    env = PlanarEnvironment(InverseSquareGravity(MU_EARTH_M3S2), omega, ambient_scalar)
    f_max = f9_vehicle.liftoff_mass_kg() * (3.0 * G0_MPS2 + env.g_ref_mps2)
    model = _model(f_max=f_max, p_max=f_max * 50.0)
    planner = PlanarPlanner(
        f9_vehicle,
        _specs(f9_vehicle, COLD),
        GuidanceSpec(50.0, 60.0, 60.0),
        env,
        "stage1_burnout",
        SETTINGS,
    )
    start = planner.start(model, SILO)
    assert start.status == "nominal"
    trace = planner.to_kick(start).prefix
    phases = trace.assist_phases()
    layout = phases[0].spec.params.layout
    budget = assist_energy_budget(phases, layout, 0.0, env.g_ref_mps2)
    pw = piston_work(phases, layout, SHAFT)
    assert pw.identity_residual_rel(budget) < REL and pw.closed_form_residual_rel() < REL
    for _t, y, res in _steps(phases):
        assert abs(_get(res, y, WORK_STATE) - w_closed(_get(res, y, "s_m"))) <= REL * w_closed(L)
    frame = sample_trace_planar(trace, f9_vehicle, 0.05)
    met = planar_track_metrics(trace, model, SILO, budget, frame)
    keys = list(met)
    assert keys[-len(SEALED_SHAFT_METRICS) :] == list(SEALED_SHAFT_METRICS)
    assert met["piston_work_J"] == pw.work_J
    assert met["assist_energy_residual_rel"] == pw.identity_residual_rel(budget)
    assert math.isclose(met["piston_force_peak_N"], f_closed(L), rel_tol=1e-12)


# --------------------------------------------------------------- config and readers


LM_BLOCK: dict[str, Any] = {
    "model": "linear_motor",
    "stroke_m": 100,
    "control": "force",
    "force_max_kN": 22000,
    "power_max_MW": 1100.5,
    "force_rise_time_s": 0.5,
    "brake_decel_g": 5,
}
"""A valid force-law block as YAML gives it (vented by default)."""
SEALED_KEYS: dict[str, Any] = {
    "shaft": "sealed",
    "shaft_bore_m": BORE_M,
    "shaft_gap_m": 5,
    "shaft_gamma": GAMMA,
}
"""The sealed shaft of lm_fixed_sealed (sources section 10: 3.7 m, 5 m, 1.4)."""


def test_sealed_config_validates_dumps_and_builds() -> None:
    """A sealed block validates (a YAML integer gap accepted), dumps its three keys and
    validates again to an equal model; a vented block's dump has no shaft_* key (the
    dump of S4a); the shaft sets are the same at the YAML boundary and in the model;
    ``build_assist`` traps the column at the ICAO pressure of the track start (exit 0 m,
    L 100 m: -100 m; exit 20 m, L 30 m: -10 m) with the given bore, gap and gamma; the
    acceleration law's taper is accepted with a sealed shaft. At the ICAO floor (a 5,004
    m stroke) the column takes the floor's pressure; below it the model raises
    (``atmosphere.standard_atmosphere``, never the clamp of ``ambient_scalar``) where the
    config has not refused first, and a vented track that deep validates."""
    assert get_args(config.ShaftKind) == get_args(ShaftKind) == ("vented", "sealed")
    cfg = LinearMotorConfig.model_validate({**LM_BLOCK, **SEALED_KEYS})
    dump = cfg.model_dump()
    assert {k: dump[k] for k in SEALED_KEYS} == {**SEALED_KEYS, "shaft_gap_m": 5.0}
    assert LinearMotorConfig.model_validate(dump) == cfg
    vented = LinearMotorConfig.model_validate(LM_BLOCK).model_dump()
    assert vented["shaft"] == "vented" and not any(k.startswith("shaft_") for k in vented)
    model, track = build_assist(cfg, G)
    assert isinstance(model, LinearMotorAssist) and model.shaft is not None
    assert model.shaft == SealedShaft(BORE_M, 5.0, GAMMA, ambient_scalar(-100.0)[0])
    assert track.start_altitude_m == -100.0
    high = LinearMotorConfig.model_validate(
        {**LM_BLOCK, **SEALED_KEYS, "stroke_m": 30, "track": {"exit_altitude_m": 20}}
    )
    model_high, _ = build_assist(high, G)
    assert isinstance(model_high, LinearMotorAssist) and model_high.shaft is not None
    assert model_high.shaft.p0_pa == ambient_scalar(-10.0)[0]
    vented_model, _ = build_assist(LinearMotorConfig.model_validate(LM_BLOCK), G)
    assert isinstance(vented_model, LinearMotorAssist) and vented_model.shaft is None
    accel = {**LM_BLOCK, **SEALED_KEYS, "control": "acceleration", "accel_command_g": 3}
    LinearMotorConfig.model_validate({**accel, "stop_taper_m": 10})
    # the ICAO floor (-5,004 m): a sealed track starting at it builds with the floor's
    # pressure; below it the config refuses (test_sealed_config_refusals) and the model
    # would raise rather than clamp; a vented track that deep validates
    deepest = LinearMotorConfig.model_validate({**LM_BLOCK, **SEALED_KEYS, "stroke_m": 5004})
    model_deep, track_deep = build_assist(deepest, G)
    assert isinstance(model_deep, LinearMotorAssist) and model_deep.shaft is not None
    assert track_deep.start_altitude_m == ALT_AMBIANCE_MIN_M
    assert model_deep.shaft.p0_pa == standard_atmosphere(ALT_AMBIANCE_MIN_M).p_pa
    with pytest.raises(ValueError, match="below the ICAO atmosphere floor"):
        LinearMotorAssist.from_config(
            deepest.model_copy(update={"stroke_m": 6000.0}), G
        )  # model_copy skips validation: the model's own refusal
    LinearMotorConfig.model_validate({**LM_BLOCK, "stroke_m": 6000})


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        ({"shaft_bore_m": 3.7}, "shaft vented takes no shaft_bore_m"),
        (
            {"shaft_gap_m": 5.0, "shaft_gamma": 1.4},
            "shaft vented takes no shaft_gap_m, shaft_gamma",
        ),
        ({"shaft_gap_m": None}, "shaft_gap_m is null"),
        ({"shaft": "sealed", "shaft_bore_m": 3.7, "shaft_gap_m": 5.0}, "(missing: shaft_gamma)"),
        ({**SEALED_KEYS, "shaft_gamma": None}, "shaft_gamma is null"),
        ({**SEALED_KEYS, "shaft_gamma": 1.0}, "greater_than"),
        ({**SEALED_KEYS, "shaft_gamma": True}, "float_type"),
        ({**SEALED_KEYS, "shaft_bore_m": "3.7"}, "float_type"),
        ({**SEALED_KEYS, "shaft_bore_m": 0}, "greater_than"),
        ({**SEALED_KEYS, "shaft_gap_m": math.nan}, "finite_number"),
        ({**SEALED_KEYS, "shaft_gap_m": math.inf}, "finite_number"),
        ({**SEALED_KEYS, "shaft_gap_m": -1.0}, "greater_than"),
        ({**SEALED_KEYS, "stop_taper_m": 10}, "shaft sealed is refused together with stop_taper_m"),
        (
            {**SEALED_KEYS, "stroke_m": 6000},
            "shaft sealed is refused with its track start below the ICAO atmosphere's floor "
            "of -5004 m: exit_altitude_m - stroke_m sin(angle_deg) = -6000 m",
        ),
        ({"shaft": "closed"}, "literal_error"),
    ],
)
def test_sealed_config_refusals(edit: dict[str, Any], match: str) -> None:
    """Refused: a sealed shaft's key on a vented shaft (given at all, a null included), a
    sealed shaft missing a key, a key not strict, finite and in range (gamma > 1), a
    sealed shaft with the force law's stop taper, a sealed track starting below the ICAO
    atmosphere's floor (review pass 3, C3-m1: p_0 would be clamped), an unknown
    shaft."""
    with pytest.raises(ValidationError) as info:
        LinearMotorConfig.model_validate({**LM_BLOCK, **edit})
    text = str(info.value)
    assert match in text or any(e["type"] == match for e in info.value.errors()), text


def test_constant_accel_keeps_its_vented_shaft() -> None:
    """constant_accel's shaft stays Literal['vented'] (a sealed shaft or a shaft key is
    refused there) and its shaft line is unchanged."""
    silo = {"model": "constant_accel", "net_accel_g": 3, "stroke_m": 100, "brake_decel_g": 5}
    with pytest.raises(ValidationError, match=r"Input should be 'vented'"):
        ConstantAccelConfig.model_validate({**silo, "shaft": "sealed"})
    with pytest.raises(ValidationError, match=r"Extra inputs are not permitted"):
        ConstantAccelConfig.model_validate({**silo, "shaft_bore_m": 3.7})
    model, _ = build_assist(ConstantAccelConfig.model_validate(silo), G)
    assert "constant_accel: shaft vented (no air column), no friction" in model.assumptions()


def _vehicle_with_aero(f9_vehicle_dict: dict[str, Any]) -> dict[str, Any]:
    """The generic F9's dict with the gate vehicle's aero block (A_ref 10.52 m^2, the 3.66
    m body)."""
    gate = yaml.safe_load(
        (REPO / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text(encoding="utf-8")
    )
    return {**f9_vehicle_dict, "aero": gate["aero"]}


def test_a_bore_at_or_below_the_body_is_refused(f9_vehicle_dict: dict[str, Any]) -> None:
    """``resolve_run`` refuses a sealed bore at or below the diameter sqrt(4 A_ref / pi)
    of the run's A_ref, 3.6598 m for the main body (exactly at it, and 3.6 m; the message
    names that section and says a section wider than it elsewhere, such as a fairing, is
    not checked), and a sealed shaft on a vehicle without an aero block (no body
    diameter); 3.7 m resolves, and so does 3.66 m, the nominal body that A_ref's source
    rounds (the check uses the diameter derived from A_ref as given); a run whose A_ref
    is set to the 5.2 m fairing's section (21.24 m^2, silo_screening_2d's aero_bound)
    refuses the 3.7 m bore against that section, with the same message; a vented run on
    that vehicle resolves."""
    veh = _vehicle_with_aero(f9_vehicle_dict)
    body = math.sqrt(4.0 * 10.52 / math.pi)
    assert config.body_diameter_m(config.VehicleConfig.model_validate(veh)) == body
    assert f"{body:.4f}" == "3.6598"
    for bore in (body, 3.6):
        block = {**LM_BLOCK, **SEALED_KEYS, "shaft_bore_m": bore}
        with pytest.raises(ValueError) as info:
            resolve_run("lm", {"assist": block}, veh)
        text = str(info.value)
        assert (
            r"must exceed the diameter sqrt(4 A_ref / pi) = 3.65985 m of the run's A_ref = "
            "10.52 m^2 (the main-body section in the vehicle files, or the section an "
            "override sets)" in text
        )
        assert "a fairing wider than the main body, is not checked" in text
        assert "body diameter" not in text
    fairing = {
        **veh,
        "aero": {
            **veh["aero"],
            "reference_area_m2": {**veh["aero"]["reference_area_m2"], "value": 21.24},
        },
    }
    with pytest.raises(ValueError, match=r"sqrt\(4 A_ref / pi\) = 5\.20035 m of the run's A_ref"):
        resolve_run("lm", {"assist": {**LM_BLOCK, **SEALED_KEYS}}, fairing)
    resolve_run("lm", {"assist": {**LM_BLOCK, **SEALED_KEYS, "shaft_bore_m": 3.66}}, veh)
    run = resolve_run("lm", {"assist": {**LM_BLOCK, **SEALED_KEYS}}, veh)
    assert run.run.assist.shaft == "sealed"  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="has no aero block"):
        resolve_run("lm", {"assist": {**LM_BLOCK, **SEALED_KEYS}}, f9_vehicle_dict)
    resolve_run("lm", {"assist": LM_BLOCK}, f9_vehicle_dict)


def test_sealed_assumption_lines(f9_vehicle: Vehicle) -> None:
    """The sealed drive's lines are the vented drive's ten with the shaft line's opening
    naming the sealed shaft (pointing to its three lines by their opening words, which
    hold in a summary that merges runs' lines; and reading the vented shaft that a
    planar run's track-push line names, and with a release speed an early-release line,
    as the shaft open above the carriage) and three lines after it: the column (bore,
    gap, p_0, gamma, the pressure law, the bound, the law's effect with its conditions,
    the felt g falling on a cold force-law plateau, the work done against it); what is
    not modelled on the push (the air pushed out of the mouth, survey 08's case at 3 g0;
    the hydrostatic drop, F_p biased high; the non-uniform, unsteady expansion of the gas
    cooled to 35 to 110 K, first order, F_p biased low; the exhaust of an engine lit on
    the track, its pressure inferred); what is not modelled after the release and in the
    geometry (the column after the release, the braking metrics upper bounds; the bore
    checked against the run's A_ref section only, the 5.2 m fairing, more than 1.975
    times the area; the vents a vented shaft needs, inferred). With a release speed the
    force law's column line compares the release position and the push time, not the
    exit speed; under either law the column line adds that the speed can peak and fall
    inside the track and a release speed just below the peak be passed over, and the
    third line the cavity under a vehicle released before the track end (both written
    out). Under the acceleration law the control line's force carries + F_p(s) and a
    stop taper's holding force at L the column's F_p(L); gamma other than the ICAO air's
    is called assumed. The vented drive's lines are unchanged (byte pins in
    ``test_vented_runs_match_their_pins``)."""
    f = f9_vehicle.liftoff_mass_kg() * 4.0 * G
    sealed = _model(f_max=f, p_max=f * 50.0)
    vented = dataclasses.replace(sealed, shaft=None)
    ls, lv = sealed.assumptions(), vented.assumptions()
    assert len(lv) == 10 and len(ls) == 13
    i = next(k for k, line in enumerate(lv) if line.startswith("linear_motor: shaft vented"))
    assert ls[:i] == lv[:i] and ls[i + 4 :] == lv[i + 1 :]
    bridge = (
        "shaft sealed below the carriage (its trapped air column: the three lines that "
        "start 'linear_motor: sealed shaft'; above the carriage the shaft is open at the "
        "mouth: the vented shaft named by the track-push line of a planar run{} is, for "
        "this run, that open shaft above the carriage)"
    )
    assert sum(line.startswith("linear_motor: sealed shaft") for line in ls) == 3
    assert ls[i] == lv[i].replace("shaft vented (no air column)", bridge.format(""))
    assert "early-release" not in ls[i]
    column, push, after = ls[i + 1], ls[i + 2], ls[i + 3]
    assert column.startswith(
        f"linear_motor: sealed shaft: the carriage seals the 3.7 m bore (A = {AREA_M2:.6g} "
        f"m^2) above a 5 m gap of air trapped at p_0 = {P0_PA:.6g} Pa (the ICAO standard "
        "atmosphere at the track start), which expands adiabatically with gamma = 1.4 (the "
        "bore and the gap assumed; gamma that of air in the ICAO standard atmosphere)"
    )
    assert f"below its bound p_0 A = {P0_PA * AREA_M2:.6g} N" in column
    assert "the interface force is lower by (m_v / M) F_p" in column
    measured = (
        "on every push S5's tests and probes measured (docs/physics.md, \"The sealed "
        'shaft"; not guaranteed'
    )
    assert f"and the exit speed is lower {measured}" in column
    assert "on a cold push's F_max plateau the felt g falls as F_p grows" in column
    assert "measured here" not in column
    assert "p_0 A s - p_0 V_0 [1 - (V_0 / V)^(gamma - 1)] / (gamma - 1)" in column
    assert "is the work done against the column, drive work the stack does not receive" in column
    assert "not as dissipated" in column and "reversible" not in column
    for phrase in (
        "survey 08's reference case",
        "about 77 kN, plus 4 to 23 kN at 3 g0",
        "0.4% to 0.5% of a 20.81 MN interface force",
        "hydrostatic drop",
        "F_p is biased high",
        "the non-uniform, unsteady expansion near the end of a small-gap stroke",
        "the gas has cooled to 35 to 110 K, from about 288 K",
        "118 to 211 m/s, is only 1.5 to 3 times the carriage's 76.7 m/s",
        "first order",
        "F_p is biased low there",
        "for an engine lit on the track, its exhaust",
        "which would dominate the push (inferred, not computed)",
    ):
        assert phrase in push, phrase
    for phrase in (
        "after the release",
        f"up to p_0 A = {P0_PA * AREA_M2:.6g} N",
        "the brake force, the brake energy and the facility length are upper bounds",
        "a massless carriage leaves the column no mass to act on",
        "the bore is checked against the diameter sqrt(4 A_ref / pi) of the run's A_ref only",
        "5.2 m fairing",
        "more than (5.2 / 3.7)^2 = 1.975 times the area (3.58 times",
        "so more than 1.975 times p_0 A and W_p at the same gap",
        "vents of about the bore area (inferred, survey 07's case",
    ):
        assert phrase in after, phrase
    open_mouth = (
        "the trapped column after the release (the carriage brakes by its own closed form "
        "with no column force on it, and the vehicle above it sees the shaft open at the "
        "mouth, flown as the vented shaft's flight model flies it); the column's pull"
    )
    assert open_mouth in after and "cavity" not in after
    assert "passed over" not in column
    # a release speed: the bridge names the early-release line, and the force law's
    # column line compares the release position and the push time, not the exit speed
    target = dataclasses.replace(sealed, release_speed_mps=50.0)
    lt, ltv = target.assumptions(), dataclasses.replace(target, shaft=None).assumptions()
    assert lt[:i] == ltv[:i] and lt[i + 4 :] == ltv[i + 1 :]
    early = " and the early-release line of a release before the track end"
    assert lt[i] == ltv[i].replace("shaft vented (no air column)", bridge.format(early))
    assert lt[i + 2] == ls[i + 2]
    # the third line: what a release before the track end leaves out (review pass 3,
    # P3-m2: the cavity under the departing vehicle, closed below by the carriage)
    cavity = (
        "the trapped column after the release (the carriage brakes by its own closed form "
        "with no column force on it, and the vehicle above it is flown as the vented "
        "shaft's flight model flies it: in the shaft open at the mouth after a release at "
        "the track end, while after a release before the track end the braking carriage "
        "still seals the bore below the departing vehicle, and the cavity that opens "
        "between the vehicle's base and the carriage, fed only through the annulus between "
        "the bore and the vehicle, is left out: a suction on the vehicle's base section "
        "A_body of up to about p_0 A_body (inferred; the vehicle's speed in the shaft after "
        "the release is biased high), and the exhaust of a stage lit before its base clears "
        "the mouth, trapped in that cavity (inferred; the other way)); the column's pull"
    )
    assert lt[i + 3] == ls[i + 3].replace(open_mouth, cavity)
    # the column line: the speed can peak and fall, and a release speed just below the
    # peak can be passed over (review pass 3, P3-m1; test_a_sealed_push_s_speed_can_...)
    passed = (
        "; the speed of a sealed push can peak inside the track and then fall, where the "
        "drive's force and the thrust's share fall below the weight and the column (under "
        "a power cap once P_max / sdot drops below M g_eff sin phi + F_p(s) - (1 - f_imp) "
        "T; under the force law also in a slow rise against a gap far below the sources' 1 "
        "to 20 m), and a release speed just below such a peak can be passed over inside one "
        "integrator step (up to 2e-5 m/s below it on the pushes measured): the push then "
        "releases at the track end with the flag release_speed_not_reached although it "
        'reached the release speed (docs/physics.md, "The sealed shaft"); W_p = int'
    )
    assert passed in lt[i + 1]
    assert "the exit speed is lower" not in lt[i + 1]
    assert (
        "; with the release speed the stack reaches it later along the track: the release "
        f"position and the push time are larger than in a vented shaft {measured}"
    ) in lt[i + 1]
    assert (
        "the speed at release stays the release speed while the push still reaches it "
        "before the track end, and is below it when the push reaches the track end first "
        "(flag release_speed_not_reached)"
    ) in lt[i + 1]
    # the acceleration law: its own effect, the column in its force and its taper
    accel = _model("acceleration", f_max=f, p_max=f * 50.0, a_cmd=G0_MPS2, taper=20.0)
    la = accel.assumptions()
    accel_vented = dataclasses.replace(accel, shaft=None).assumptions()
    assert "the drive supplies F_p too" in la[i + 1]
    assert "while no cap binds on the whole push the drive work rises by W_p" in la[i + 1]
    assert la[0] == accel_vented[0].replace(
        "the drive force M (a + g_eff sin phi) - (1 - f_imp) T, capped",
        "the drive force M (a + g_eff sin phi) - (1 - f_imp) T + F_p(s) (the sealed shaft's "
        "column), capped",
    )
    assert la[0] != accel_vented[0]
    taper = next(k for k, line in enumerate(la) if "after a stop taper" in line)
    hold = "the holding force M g_eff sin phi - (1 - f_imp) T"
    assert la[taper] == accel_vented[taper].replace(
        hold, f"{hold} plus the sealed shaft's column force F_p(L) at the track end"
    )
    assert la[taper] != accel_vented[taper]
    assert "passed over" not in la[i + 1] and "cavity" not in la[i + 3]
    # with a release speed the acceleration law's lines carry the same two additions
    accel_target = dataclasses.replace(
        _model("acceleration", f_max=f, p_max=f * 50.0, a_cmd=G0_MPS2), release_speed_mps=50.0
    )
    lat = accel_target.assumptions()
    assert passed in lat[i + 1] and "the drive supplies F_p too" in lat[i + 1]
    assert lat[i + 3] == ls[i + 3].replace(open_mouth, cavity)
    # a gamma other than the ICAO air's is assumed
    other = dataclasses.replace(sealed, shaft=dataclasses.replace(SHAFT, gamma=1.3))
    assert (
        "with gamma = 1.3 (the bore, the gap and gamma assumed; air in the ICAO standard "
        "atmosphere has 1.4)" in other.assumptions()[i + 1]
    )


def test_summary_rows_of_a_sealed_shaft_run() -> None:
    """SEALED_SHAFT_ROWS (every SEALED_SHAFT_METRICS key) follow the linear motor's rows
    of the 1-D and the planar tables when a sealed-shaft run is in the table: '-' for the
    pad and a vented linear-motor run, the metric for the sealed run, n/a for its
    release pressure when it never released, as the first row's n/a key says (every row:
    no push record; the pressure row: no release); a table without a sealed run gains no
    row."""
    lm = {"facility_length_m": 120.0, "push_force_max_N": 2.2e7}
    sealed = {
        **lm,
        "piston_work_J": 1.0e8,
        "piston_force_peak_N": 1.087e6,
        "bore_pressure_release_pa": None,
    }

    def run(name: str, metrics: dict[str, Any]) -> SimpleNamespace:
        return SimpleNamespace(
            name=name,
            result=SimpleNamespace(metrics=metrics, status="nominal", flags=[]),
            resolved=SimpleNamespace(
                run=SimpleNamespace(ignition_for=lambda _s: SimpleNamespace(ramp_start=("time",))),
                vehicle_dict={"stages": [{"name": "stage1"}]},
            ),
        )

    def er(runs: dict[str, dict[str, Any]]) -> SimpleNamespace:
        fakes = {n: run(n, m) for n, m in runs.items()}
        return SimpleNamespace(runs=fakes, baseline=next(iter(fakes.values())), comparison={})

    table = er({"pad": {"facility_length_m": 0.0}, "lm": lm, "lm_sealed": sealed})
    plain = er({"pad": {"facility_length_m": 0.0}, "lm": lm})
    keys = [key for _label, _source, key in summary.SEALED_SHAFT_ROWS]
    assert keys == list(SEALED_SHAFT_METRICS)
    for rows_of in (summary.variant_rows, summary.planar_variant_rows):
        rows = list(rows_of(table))  # type: ignore[arg-type]
        at = rows.index(summary.LINEAR_MOTOR_ROWS[-1])
        assert rows[at + 1 : at + 1 + len(keys)] == list(summary.SEALED_SHAFT_ROWS)
        assert not set(summary.SEALED_SHAFT_ROWS) & set(rows_of(plain))  # type: ignore[arg-type]
    cell = summary._variant_cell
    cells = {
        key: tuple(cell(table, n, source, key) for n in ("pad", "lm", "lm_sealed"))  # type: ignore[arg-type]
        for _label, source, key in summary.SEALED_SHAFT_ROWS
    }
    assert cells["piston_work_J"] == ("-", "-", "1e+08")
    assert cells["piston_force_peak_N"] == ("-", "-", "1.087e+06")
    assert cells["bore_pressure_release_pa"] == ("-", "-", "n/a")
    labels = " ".join(label for label, _s, _k in summary.SEALED_SHAFT_ROWS)
    assert (
        "n/a in every row: a sealed-shaft run with no push record; n/a in the pressure row: "
        "no release" in labels
    )
    assert "work done against the trapped column W_p [J] (drive work the stack does" in labels
    assert "not dissipated in the model" in labels and "reversible" not in labels
    assert "below p_0 A_bore" in labels
    # a sealed run without a push record (its guidance failed): the rows, n/a in each
    failed = run("lm_failed", {"facility_length_m": None})
    failed.resolved.run.assist = LinearMotorConfig.model_validate({**LM_BLOCK, **SEALED_KEYS})
    no_record = er({"pad": {"facility_length_m": 0.0}})
    no_record.runs["lm_failed"] = failed
    assert set(summary.SEALED_SHAFT_ROWS) <= set(summary.variant_rows(no_record))  # type: ignore[arg-type]
    assert {
        cell(no_record, "lm_failed", source, key)  # type: ignore[arg-type]
        for _label, source, key in summary.SEALED_SHAFT_ROWS
    } == {"n/a"}


# ------------------------------------------------------------- byte identity (pins)


def test_vented_runs_keep_their_metric_keys() -> None:
    """The metric keys, in order, of the five pinned 1-D runs (vented linear-motor and
    constant_accel) and of the planar flown push's track metrics are those captured
    before S5 (tests/data/vented_pins.json), in any environment: no run without a sealed
    shaft gains a key. The pins name the commit they were captured from (e12e524, the
    last before S5), which a re-capture uses in place of HEAD."""
    vp = _load("vented_pins_support")
    pins = vp.read_pins()
    assert pins["source_commit"] == vp.SOURCE_COMMIT and vp.SOURCE_COMMIT.startswith("e12e524")
    assert vp.metric_keys() == pins["metric_keys"]


def test_vented_runs_match_their_pins() -> None:
    """Vented linear-motor runs and a constant_accel run are byte-identical to the commit
    before S5, their sha256 digests equal to tests/data/vented_pins.json: the five 1-D
    runs (the force law cold and hot, the acceleration law with a taper, a release speed,
    constant_accel) in their integrator states, metrics, time series, events, assumption
    lines, flags, status and assist budget; the planar flown push through the config in
    its phases' states, events, flags, status and the drive's assumption lines, and its
    planar track metrics (``planar_track_metrics`` on the push), sampled time series and
    assist budget. Exact only in the capture environment (the golden tier's
    EXACT_ENV_KEYS); skipped elsewhere unless LAUNCHSIM_REQUIRE_EXACT_GOLDEN=1."""
    vp = _load("vented_pins_support")
    gs = _load("golden_1d_support")
    pins = vp.read_pins()
    status, reason = gs.exact_tier_status(pins["environment"], os.environ)
    if status == "skip":
        pytest.skip(reason)
    assert status == "run", reason
    assert vp.all_digests() == pins["digests"]
