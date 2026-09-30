"""Stage-1 guidance (docs/physics.md, "Stage-1 guidance and events (planar)" and "gamma*
inner solve"): the steering laws, the guidance spec, the typed failures, and the kick
angle delta that reaches a target gamma_rel at MECO, with the false-root guard of
amendment 7.

The inner-solve tests fly the gate fork (generic_f9_class_2d.yaml) from the pad: 28.5
deg east, rotation, ICAO atmosphere, Braeunig drag, v_k = 50 m/s, rtol 1e-10 (the
recorded-run tolerance) with dense output off (the search mode; event states come
from y_events), the shipped 2 s planar max_step cap (IntegratorSettings default,
integrator.planar_max_step_s of the shipped experiments) and the shipped delta
settings.
"""

from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import yaml

from launchsim.atmosphere import ambient_scalar
from launchsim.config import GuidanceConfig, KickConfig, SearchConfig, VehicleConfig
from launchsim.constants import MU_EARTH_M3S2
from launchsim.dynamics import (
    PLANAR_LAYOUT,
    InverseSquareGravity,
    planar_kinematics,
    planar_rotation_rate,
)
from launchsim.guidance import (
    GUIDANCE_FAILURE_KINDS,
    IMPACT_GAMMA_RAD,
    TIMEOUT_GAMMA_RAD,
    AlongVrel,
    DeltaSolution,
    DeltaSolveSettings,
    FixedTilt,
    GuidanceFailure,
    GuidanceSpec,
    Radial,
    pitch_rad,
    solve_delta_for_gamma,
)
from launchsim.phases import IgnitionSpec, IntegratorSettings
from launchsim.phases.planar import Handover, KickPoint, PlanarEnvironment, PlanarPlanner
from launchsim.vehicle import Vehicle

P2 = PLANAR_LAYOUT
LAT_RAD = math.radians(28.5)
V_KICK_MPS = 50.0
RTOL = 1e-10
PLANAR_MAX_STEP_S = 2.0
"""The shipped integrator.planar_max_step_s [s] (test_config_planar pins it in every
planar experiment)."""
GAMMA_TOL_RAD = 3e-7
"""|gamma_rel(MECO; delta*) - gamma*| allowed [rad] (1.7e-5 deg); the plan asks 1e-9 rad.
User decision of 2026-09-30: the planar flight phases fly a 2 s max_step cap and this
acceptance is tightened from 3e-6 rad (the uncapped floor) to three times the capped
jitter bound NOISE_MAX_RAD (docs/physics.md, "gamma* inner solve", Noise floor).
Without a cap DOP853 sometimes accepts one long step (up to 3.6 s) across the clustered
C1 knots of the transonic PCHIP C_D table (M 0.95, 1.0, 1.05), and whether it does
changes with delta, so the global error jumps (6.7e-7 rad at rtol 1e-10). With the 2 s
cap gamma_MECO(delta) still jitters from flight to flight by up to NOISE_MAX_RAD, and
brentq can only land on a sign change of that map, so its residual is bounded by about
the single-flight jitter; the tolerance is about 3.5x the largest capped step jump
measured (8.6e-8 rad), far below the 0.01 deg root guard. Even a noise-free map could
not meet 1e-9 rad: brentq stops at delta_xtol 1e-10 rad, and the slope of about 14
rad/rad leaves up to 1.4e-9 rad. Measured residuals at the three roots: 1.0e-10 to
3.3e-10 rad; at 12 more gamma* (6 to 34 deg) at most 1.4e-9 rad (rtol 1e-10) and 5.7e-9
rad (search setting)."""
NOISE_MAX_RAD = 1e-7
"""Bound [rad] on the flight-to-flight jitter of gamma_MECO(delta) on the gate pad at
rtol 1e-10 with the 2 s cap (docs/physics.md, "gamma* inner solve", Noise floor). The
jitter is heavy-tailed and sensitive at the ulp level, so a window maximum depends on
where it is sampled: the largest values measured are 8.1e-8 rad deviation from a local
linear fit and 8.6e-8 rad step jump (at 3.8375 deg, 60 half-step angles), 7.9e-8 rad
single-flight |gamma - median| over 2,250 flights, and 9.9e-8 rad spread over 120
flights 1 ulp apart (median single-flight deviation about 3e-10 rad, 99th percentile
about 8e-9 rad). GAMMA_TOL_RAD keeps a margin of three above this bound."""
XTOL_RAD = 1e-10
"""delta tolerance [rad]: the shipped search.delta_xtol_rad."""
ROOT_TOL_RAD = math.radians(0.01)
BRACKET_RAD = (math.radians(0.1), math.radians(45.0))
STEP_RAD = math.radians(0.25)
BRENTQ_RTOL = 4.0 * np.finfo(float).eps


@pytest.fixture(scope="module")
def gate_vehicle(repo_root: Path) -> Vehicle:
    """The gate fork generic_f9_class_2d.yaml."""
    path = repo_root / "configs" / "vehicles" / "generic_f9_class_2d.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return VehicleConfig.model_validate(raw).to_vehicle()


@pytest.fixture(scope="module")
def pad_kick(gate_vehicle: Vehicle) -> tuple[PlanarPlanner, KickPoint]:
    """The gate pad (stage 1 lit at -2 s, 2 s ramp) flown to the kick trigger, search
    mode (dense output off)."""
    env = PlanarEnvironment(
        InverseSquareGravity(MU_EARTH_M3S2),
        planar_rotation_rate(LAT_RAD, 0.5 * math.pi),
        ambient_scalar,
    )
    planner = PlanarPlanner(
        gate_vehicle,
        {"stage1": IgnitionSpec(-2.0), "stage2": IgnitionSpec(0.0)},
        GuidanceSpec(V_KICK_MPS, 60.0, 60.0),
        env,
        "insertion",
        IntegratorSettings(rtol=RTOL, dense_output=False, planar_max_step_s=PLANAR_MAX_STEP_S),
    )
    return planner, planner.to_kick(planner.start())


def _settings() -> DeltaSolveSettings:
    return DeltaSolveSettings(BRACKET_RAD, STEP_RAD, XTOL_RAD, BRENTQ_RTOL, ROOT_TOL_RAD)


# ----------------------------------------------------------------------------- laws


def test_steering_laws() -> None:
    """Radial is (1, 0) at pitch pi/2; FixedTilt(delta) is (cos delta, sin delta) at
    pitch pi/2 - delta; AlongVrel is the unit v_rel (sin_g, cos_g), radial at the
    V = 0 fallback; only AlongVrel is flagged along_vrel."""
    omega = planar_rotation_rate(LAT_RAD, 0.5 * math.pi)
    r = 6.4e6
    y = P2.build(r_m=r, v_r_mps=300.0, v_theta_mps=omega * r + 400.0, m_kg=1.0)
    kin = planar_kinematics(y, omega)
    assert Radial().direction(0.0, y, kin) == (1.0, 0.0)
    assert pitch_rad(*Radial().direction(0.0, y, kin)) == 0.5 * math.pi
    delta = math.radians(3.0)
    e = FixedTilt(delta).direction(0.0, y, kin)
    assert e == (math.cos(delta), math.sin(delta))
    assert pitch_rad(*e) == pytest.approx(0.5 * math.pi - delta, abs=1e-15)
    e_r, e_t = AlongVrel().direction(0.0, y, kin)
    assert (e_r, e_t) == pytest.approx((0.6, 0.8), abs=1e-15)
    pad = P2.build(r_m=r, v_theta_mps=omega * r, m_kg=1.0)
    assert AlongVrel().direction(0.0, pad, planar_kinematics(pad, omega)) == (1.0, 0.0)
    assert [law.along_vrel for law in (Radial(), FixedTilt(delta), AlongVrel())] == [
        False,
        False,
        True,
    ]
    with pytest.raises(ValueError, match="finite"):
        FixedTilt(math.nan)


def test_guidance_spec_and_failures() -> None:
    """GuidanceSpec from the config's kick block; vertical_only never kicks; a kicking
    spec needs finite limits. GuidanceFailure is typed, refuses unknown kinds and
    pickles with its kind and message (all args passed to RuntimeError)."""
    spec = GuidanceSpec.from_config(
        GuidanceConfig(kick=KickConfig(v_kick_mps=80.0, max_duration_s=30.0, deadline_s=45.0))
    )
    assert (spec.v_kick_mps, spec.kick_max_s, spec.kick_deadline_s) == (80.0, 30.0, 45.0)
    assert spec.kicks and not GuidanceSpec.vertical_only().kicks
    with pytest.raises(ValueError, match="finite"):
        GuidanceSpec(50.0, math.inf, 60.0)
    with pytest.raises(ValueError, match="no kick deadline"):
        GuidanceSpec(math.inf, math.inf, 60.0)
    with pytest.raises(ValueError, match="> 0"):
        GuidanceSpec(0.0, 60.0, 60.0)
    for kind in GUIDANCE_FAILURE_KINDS:
        exc = GuidanceFailure(kind, "why")
        back = pickle.loads(pickle.dumps(exc))
        assert (back.kind, back.message, back.args) == (kind, "why", (kind, "why"))
        assert str(back) == f"{kind}: why"
    with pytest.raises(ValueError, match="unknown guidance failure kind"):
        GuidanceFailure("dive")


def test_delta_settings_from_config() -> None:
    """DeltaSolveSettings reads the search block's radian properties."""
    cfg = SearchConfig()
    s = DeltaSolveSettings.from_config(cfg)
    assert s.bracket_rad == pytest.approx((math.radians(0.1), math.radians(45.0)), rel=1e-15)
    assert s.step_rad == pytest.approx(math.radians(0.25), rel=1e-15)
    assert s.xtol_rad == cfg.delta_xtol_rad
    assert s.rtol == cfg.brentq_rtol
    assert s.root_tol_rad == pytest.approx(math.radians(0.01), rel=1e-15)
    with pytest.raises(ValueError, match="bracket"):
        DeltaSolveSettings((0.0, 0.5), STEP_RAD, XTOL_RAD, BRENTQ_RTOL, ROOT_TOL_RAD)


# ------------------------------------------------------------- inner solve (vehicle)


def test_gamma_meco_is_monotone_in_delta(pad_kick: tuple[PlanarPlanner, KickPoint]) -> None:
    """gamma_rel at MECO decreases strictly with the kick angle on 10 points from 1 to
    5.5 deg (the map the inner solve brackets), and impacts start beyond (7 deg)."""
    planner, kick = pad_kick
    deltas = np.radians(np.linspace(1.0, 5.5, 10))
    gammas = [
        planner.from_kick(float(d), kick, through_staging=False).gamma_meco_rad for d in deltas
    ]
    assert all(np.diff(gammas) < 0.0), gammas
    with pytest.raises(GuidanceFailure) as info:
        planner.from_kick(math.radians(7.0), kick, through_staging=False)
    assert info.value.kind == "impact"


@pytest.fixture(scope="module")
def cold_20(pad_kick: tuple[PlanarPlanner, KickPoint]) -> DeltaSolution:
    """The inner solve for gamma* = 20 deg from a cold start (both bracket ends)."""
    planner, kick = pad_kick
    return solve_delta_for_gamma(
        lambda d: planner.from_kick(d, kick), math.radians(20.0), _settings()
    )


def test_inner_solve_cold(
    pad_kick: tuple[PlanarPlanner, KickPoint], cold_20: DeltaSolution
) -> None:
    """gamma* = 20 deg from a cold start (a 0.1 deg kick times out, a 45 deg kick hits
    the ground: the two sentinels bracket the root) reaches gamma_rel(MECO) = gamma*
    within GAMMA_TOL_RAD. The handover is the flight at delta* (stage-2 ignition after the
    11 s staging coast), and a re-flight at delta* reproduces it bit for bit."""
    planner, kick = pad_kick
    assert abs(cold_20.gamma_meco_rad - math.radians(20.0)) < GAMMA_TOL_RAD
    assert cold_20.bracket_rad == BRACKET_RAD
    assert GAMMA_TOL_RAD >= 3.0 * NOISE_MAX_RAD
    ho = cold_20.handover
    assert ho.delta_rad == cold_20.delta_rad
    assert ho.t_ign2_s == pytest.approx(ho.meco["t_s"] + 11.0, abs=1e-12)
    assert ho.gamma_meco_rad == cold_20.gamma_meco_rad
    again = planner.from_kick(cold_20.delta_rad, kick)
    assert again.gamma_meco_rad == cold_20.gamma_meco_rad
    assert np.array_equal(again.y_ign2, ho.y_ign2)


def test_inner_solve_warm(
    pad_kick: tuple[PlanarPlanner, KickPoint], cold_20: DeltaSolution
) -> None:
    """gamma* = 10 and 30 deg warm-started from the 20 deg kick reach gamma_rel(MECO) =
    gamma* within GAMMA_TOL_RAD in fewer flights than the cold solve; a shallower MECO needs
    a harder kick (delta(10) > delta(20) > delta(30))."""
    planner, kick = pad_kick
    deltas = {}
    for g_deg in (10.0, 30.0):
        warm = solve_delta_for_gamma(
            lambda d: planner.from_kick(d, kick),
            math.radians(g_deg),
            _settings(),
            warm=cold_20.delta_rad,
        )
        assert abs(warm.gamma_meco_rad - math.radians(g_deg)) < GAMMA_TOL_RAD
        assert warm.flights < cold_20.flights
        deltas[g_deg] = warm.delta_rad
    assert deltas[10.0] > cold_20.delta_rad > deltas[30.0]


def test_impact_gap_false_root_is_rejected(pad_kick: tuple[PlanarPlanner, KickPoint]) -> None:
    """gamma* = -45 deg lies in the impact gap: the shallowest flight that still reaches
    MECO flies about -12 deg or higher (a 6.76 deg kick), the next harder kick hits the
    ground (-90 deg by the sentinel). f changes sign across that jump, brentq converges
    onto it, and the guard (|gamma_MECO(delta*) - gamma*| <= 0.01 deg) rejects the root.
    The bracket (6, 8) deg and the delta tolerance 1e-6 rad only shorten the bisection
    onto the jump (about 15 flights); the guard depends on neither."""
    planner, kick = pad_kick
    settings = DeltaSolveSettings(
        (math.radians(6.0), math.radians(8.0)), STEP_RAD, 1e-6, BRENTQ_RTOL, ROOT_TOL_RAD
    )
    flights: list[float] = []

    def fly(delta: float) -> Handover:
        flights.append(delta)
        return planner.from_kick(delta, kick, through_staging=False)

    with pytest.raises(GuidanceFailure) as info:
        solve_delta_for_gamma(fly, math.radians(-45.0), settings)
    assert info.value.kind == "false_root"
    assert math.radians(6.5) < flights[-1] < math.radians(7.0)


# ---------------------------------------------------------------- inner solve (toys)


@dataclass(frozen=True)
class _Flight:
    gamma_meco_rad: float


def _toy(delta: float) -> _Flight:
    """gamma = 0.5 - 3 delta for 0.01 <= delta < 0.2; a kick timeout below, an impact
    from 0.2 on (the gap is (-pi/2, -0.1))."""
    if delta < 0.01:
        raise GuidanceFailure("kick_timeout", "toy")
    if delta >= 0.2:
        raise GuidanceFailure("impact", "toy")
    return _Flight(0.5 - 3.0 * delta)


def _toy_steep(delta: float) -> _Flight:
    """Aligned flights that reach above pi/2 just past the timeout, as the gate pad's do
    past the Coriolis stall (90.96 deg): gamma = 1.8 - 3 (delta - 0.01) for 0.01 <=
    delta < 0.3; a kick timeout below 0.01, an impact from 0.3 on."""
    if delta < 0.01:
        raise GuidanceFailure("kick_timeout", "toy")
    if delta >= 0.3:
        raise GuidanceFailure("impact", "toy")
    return _Flight(1.8 - 3.0 * (delta - 0.01))


def test_timeout_sentinel_lies_above_every_real_gamma() -> None:
    """The timeout sentinel is pi, the top of gamma_rel's range, so it lies above
    aligned flights that end steeper than pi/2: gamma* = 1.7 rad (above pi/2) is solved
    from a cold start (a bracket whose low end times out) and from a warm start below
    the timeout, at delta = 0.01 + 0.1/3. With a pi/2 sentinel the low end would lie
    below gamma* and the target would be reported unattainable."""
    assert TIMEOUT_GAMMA_RAD == math.pi
    s = DeltaSolveSettings((0.001, 0.5), 0.01, 1e-14, BRENTQ_RTOL, 1e-6)
    for warm in (None, 0.002):
        sol = solve_delta_for_gamma(_toy_steep, 1.7, s, warm=warm)
        assert sol.delta_rad == pytest.approx(0.01 + 0.1 / 3.0, abs=1e-12)
        assert sol.gamma_meco_rad == pytest.approx(1.7, abs=1e-12)


def test_toy_inner_solve_roots_gaps_and_propagation() -> None:
    """On a toy map with a timeout below delta = 0.01 and impacts from 0.2: a reachable
    gamma* is solved cold and warm (the sentinels bracket it); gamma* in the impact gap
    or above the timeout jump is a false root; gamma* beyond both sentinels is
    unattainable; a bracket that never changes sign from a warm start is unattainable;
    no_kick propagates untouched."""
    s = DeltaSolveSettings((0.001, 0.5), 0.01, 1e-14, BRENTQ_RTOL, 1e-6)
    for warm in (None, 0.05, 0.3, 0.002):
        sol = solve_delta_for_gamma(_toy, 0.2, s, warm=warm)
        assert sol.delta_rad == pytest.approx(0.1, abs=1e-12)
        assert sol.handover.gamma_meco_rad == pytest.approx(0.2, abs=1e-12)
    for gamma_star in (-0.5, 0.49999):
        with pytest.raises(GuidanceFailure) as info:
            solve_delta_for_gamma(_toy, gamma_star, s)
        assert info.value.kind == "false_root", gamma_star
    for gamma_star in (TIMEOUT_GAMMA_RAD + 0.1, IMPACT_GAMMA_RAD - 0.1):
        with pytest.raises(GuidanceFailure) as info:
            solve_delta_for_gamma(_toy, gamma_star, s)
        assert info.value.kind == "gamma_unattainable"
    narrow = DeltaSolveSettings((0.02, 0.1), 0.01, 1e-14, BRENTQ_RTOL, 1e-6)
    with pytest.raises(GuidanceFailure) as info:
        solve_delta_for_gamma(_toy, 0.0, narrow, warm=0.05)
    assert info.value.kind == "gamma_unattainable"

    def no_kick(delta: float) -> _Flight:
        raise GuidanceFailure("no_kick", "toy")

    with pytest.raises(GuidanceFailure) as info:
        solve_delta_for_gamma(no_kick, 0.2, s)
    assert info.value.kind == "no_kick"
