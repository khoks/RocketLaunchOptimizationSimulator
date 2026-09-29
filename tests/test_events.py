"""Event-engine robustness: exact event landing, the guard against re-firing an event
that sits at zero when a phase starts, phases already past a terminal event, zero-length
and very short phases, the t_max guard, and the rotation-rate helpers.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from launchsim import sim
from launchsim.config import IntegratorConfig
from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, OMEGA_EARTH_RADS, R_EARTH_M
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    ConstantGravity,
    Gravity,
    InverseSquareGravity,
    StateLayout,
    VerticalDynamics1D,
    VerticalParams,
    g_eff_track,
    planar_rotation_rate,
    rhs_vertical,
)
from launchsim.phases import (
    AscentStart,
    EventSpec,
    IgnitionSpec,
    IntegratorSettings,
    PhaseSpec,
    atol_for,
    ev_apex,
    ev_impact,
    ev_liftoff,
    ev_propellant,
    ev_turnaround,
    integrate_phase,
    map_release,
)
from launchsim.vehicle import Stage, Startup, ThrustSchedule, Vehicle

G = G0_MPS2
ATOL = atol_for(VERTICAL_STATE_NAMES)


def _params(
    schedule: ThrustSchedule | None = None, v_sign: int = 1, gravity: Gravity | None = None
) -> VerticalParams:
    return VerticalParams(
        gravity=ConstantGravity(G) if gravity is None else gravity,
        g_ref_mps2=G,
        schedule=schedule,
        v_sign=v_sign,
    )


def _spec(
    kind: str,
    params: VerticalParams,
    events: tuple[EventSpec, ...],
    t0: float = 0.0,
    t_end: float | None = None,
    sigma: int = 1,
) -> PhaseSpec:
    return PhaseSpec(
        kind=kind,
        stage_index=0,
        t0=t0,
        t_end=t_end,
        rhs=rhs_vertical,
        params=params,
        events=events,
        atol=ATOL,
        sigma=sigma,
    )


def _v(y: np.ndarray) -> float:
    return float(VERTICAL_LAYOUT.get(y, "v_mps"))


def _z(y: np.ndarray) -> float:
    return float(VERTICAL_LAYOUT.get(y, "z_m"))


# ------------------------------------------------------------------ event landing


def test_propellant_event_lands_on_dry_mass(
    toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    spec = _spec("BURN", _params(toy_stage.schedule(0.0)), (ev_propellant(toy_stage.dry_mass_kg),))
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(m_kg=m0), tight_settings)
    assert res.ended_by == "propellant"
    assert abs(float(VERTICAL_LAYOUT.get(res.y_end, "m_kg")) - toy_stage.dry_mass_kg) < 1e-6
    assert res.t[-1] == res.t_end
    assert res.y.shape == (len(VERTICAL_STATE_NAMES), len(res.t))
    assert res.dense is not None
    assert np.allclose(res.dense(res.t_end), res.y_end, rtol=0, atol=1e-9)


# ------------------------------------------------------- events at zero at t0


def test_apex_does_not_refire_at_the_start_of_a_fall(tight_settings: IntegratorSettings) -> None:
    """Engine robustness check, not a planner pattern: a FALL phase lists ev_turnaround
    and ev_impact (a thrusting fall re-crosses v = 0 upward), never the apex that ended
    the previous phase. If a planner mistake lists ev_apex anyway, the stale zero at t0
    must not end the phase; the disarm is reported in the notes."""
    z0 = 100.0
    spec = _spec("FALL", _params(v_sign=-1), (ev_apex(), ev_impact(0.0)), sigma=-1)
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(z_m=z0, m_kg=1.0), tight_settings)
    assert res.ended_by == "impact"
    assert [name for name, _ in res.event_times] == ["impact"]
    assert any("apex" in note and "disarmed" in note for note in res.notes)
    assert math.isclose(res.t_end, math.sqrt(2.0 * z0 / G), rel_tol=1e-9)
    assert math.isclose(_v(res.y_end), -math.sqrt(2.0 * G * z0), rel_tol=1e-9)


@pytest.mark.parametrize("v0", [2e-12, -2e-12, 1e-10, -1e-10])
def test_apex_residue_within_atol_does_not_end_a_fall(
    v0: float, tight_settings: IntegratorSettings
) -> None:
    """The root scipy leaves at an apex is not an exact zero: the residue can sit on
    either side, up to a few ulp of the state (measured up to 1.4e-12 m/s at t = 3000 s).
    A residue below the velocity atol (1e-9 m/s) must count as "on the surface": neither
    the already-past rule (negative residue) nor scipy's first-step sign test (positive
    residue) may end the fall at t0."""
    z0 = 100.0
    spec = _spec("FALL", _params(v_sign=-1), (ev_apex(), ev_impact(0.0)), sigma=-1)
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(z_m=z0, v_mps=v0, m_kg=1.0), tight_settings)
    assert res.ended_by == "impact"
    assert res.span_s > 0.0
    assert [name for name, _ in res.event_times] == ["impact"]
    assert math.isclose(res.t_end, math.sqrt(2.0 * z0 / G), rel_tol=1e-9)


@pytest.mark.parametrize("ulps", [-1, 0, 1])
def test_propellant_residue_within_atol_does_not_end_the_next_phase(
    ulps: int, f9_vehicle: Vehicle, tight_settings: IntegratorSettings
) -> None:
    """After an F9 stage-1 burnout the mass sits at m_dry +/- one ulp (2.9e-11 kg,
    above any absolute 1e-12 test). A following coast that (wrongly) still lists the
    propellant event must not end at t0 as "propellant": the residue is below the
    mass atol (1e-6 kg) and the mass does not move, so the event is disarmed and the
    coast ends at its apex."""
    m_dry = f9_vehicle.stack_dry_mass_kg(0)
    m0 = m_dry + ulps * math.ulp(m_dry)
    assert abs(m0 - m_dry) < 1e-6
    v0 = 50.0
    spec = _spec("COAST", _params(), (ev_propellant(m_dry), ev_apex()), t0=247.0)
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(v_mps=v0, m_kg=m0), tight_settings)
    assert res.ended_by == "apex"
    assert [name for name, _ in res.event_times] == ["apex"]
    assert math.isclose(res.t_end - 247.0, v0 / G, rel_tol=1e-9)
    if ulps <= 0:
        assert any("propellant" in note and "disarmed" in note for note in res.notes)


def test_fall_from_a_late_apex_root_reaches_impact(tight_settings: IntegratorSettings) -> None:
    """scipy locates roots to ~4 eps in time, so the stale velocity at an apex found at
    a large run time is ~g * 4 eps * t (about 1e-12 m/s at t = 3000 s). A FALL started
    from that root with turnaround and apex listed must integrate to impact, not be
    classified as already past or fire on the first step."""
    mu = MU_EARTH_M3S2
    gravity = InverseSquareGravity(mu)
    g_ref = mu / R_EARTH_M**2
    t0 = 3000.0
    v0 = 2000.0
    up = PhaseSpec(
        "COAST",
        0,
        t0,
        None,
        rhs_vertical,
        VerticalParams(gravity=gravity, g_ref_mps2=g_ref, schedule=None, v_sign=1),
        (ev_apex(), ev_impact(0.0)),
        ATOL,
        sigma=1,
    )
    res_up = integrate_phase(up, VERTICAL_LAYOUT.build(v_mps=v0, m_kg=1.0), tight_settings)
    assert res_up.ended_by == "apex"
    assert abs(_v(res_up.y_end)) < 1e-9
    down = PhaseSpec(
        "FALL",
        0,
        res_up.t_end,
        None,
        rhs_vertical,
        VerticalParams(gravity=gravity, g_ref_mps2=g_ref, schedule=None, v_sign=-1),
        (ev_turnaround(), ev_apex(), ev_impact(0.0)),
        ATOL,
        sigma=-1,
    )
    res_down = integrate_phase(down, res_up.y_end, tight_settings)
    assert res_down.ended_by == "impact"
    assert [name for name, _ in res_down.event_times] == ["impact"]
    # Radial Kepler time symmetry: the fall takes as long as the rise.
    assert math.isclose(res_down.span_s, res_up.span_s, rel_tol=1e-9)
    assert math.isclose(_v(res_down.y_end), -v0, rel_tol=1e-9)


def test_persistent_zero_never_fires(tight_settings: IntegratorSettings) -> None:
    """scipy fires a direction-matched event when g and g_new are both exactly zero.
    A disarmed event keeps reporting its guard value while |g| <= zero_tol, so an event
    function that never moves (the propellant event with no thrust and m = m_dry
    exactly) cannot end the phase at the end of the first step."""
    m_dry = 200.0
    spec = _spec("COAST", _params(), (ev_propellant(m_dry), ev_apex()))
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(v_mps=50.0, m_kg=m_dry), tight_settings)
    assert res.ended_by == "apex"
    assert [name for name, _ in res.event_times] == ["apex"]
    assert math.isclose(res.t_end, 50.0 / G, rel_tol=1e-9)


@pytest.mark.parametrize("v0", [0.0, -1e-13, -1e-15])
def test_turnaround_does_not_fire_at_the_start_of_a_fall(
    v0: float, tight_settings: IntegratorSettings
) -> None:
    spec = _spec("FALL", _params(v_sign=-1), (ev_turnaround(), ev_impact(0.0)), sigma=-1)
    y0 = VERTICAL_LAYOUT.build(z_m=100.0, v_mps=v0, m_kg=1.0)
    res = integrate_phase(spec, y0, tight_settings)
    assert res.ended_by == "impact"
    assert [name for name, _ in res.event_times] == ["impact"]


def test_twr_above_one_pad_start_does_not_trigger_apex(
    toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    """A burn from rest with TWR > 1 has v = 0 at t0; the apex event (direction -1)
    must stay armed (the Heun prediction gives v > 0, so scipy would not fire either)
    and never fire."""
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    assert toy_stage.engine.thrust_vac_N > m0 * G
    spec = _spec(
        "BURN", _params(toy_stage.schedule(0.0)), (ev_apex(), ev_propellant(toy_stage.dry_mass_kg))
    )
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(m_kg=m0), tight_settings)
    assert res.ended_by == "propellant"
    assert [name for name, _ in res.event_times] == ["propellant"]
    assert res.notes == ()


def test_turnaround_fires_for_a_real_crossing_after_a_guarded_start(
    toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    """Start at v = 0 with the engine off (the turnaround event is at zero at t0 but
    moving away from its firing side, so it stays armed), then light a ramp at t = 1 s:
    the vehicle falls, turns around, so the turnaround event fires once at the real
    crossing, not at t0."""
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    schedule = toy_stage.schedule(1.0, startup=Startup("ramp", t_ramp_s=1.0))
    spec = _spec("FALL", _params(schedule, v_sign=-1), (ev_turnaround(), ev_impact(-1e4)), sigma=-1)
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(z_m=0.0, m_kg=m0), tight_settings)
    assert res.ended_by == "turnaround"
    assert res.t_end > 1.0
    assert abs(_v(res.y_end)) < 1e-9
    assert _z(res.y_end) < 0.0


# ------------------------------------------------------------- already past


def test_phase_already_past_a_terminal_event_ends_at_t0(
    tight_settings: IntegratorSettings,
) -> None:
    y0 = VERTICAL_LAYOUT.build(z_m=10.0, v_mps=-3.0, m_kg=1.0)
    spec = _spec("COAST", _params(), (ev_apex(), ev_impact(0.0)), t0=4.0)
    res = integrate_phase(spec, y0, tight_settings)
    assert res.ended_by == "apex"
    assert res.t_end == 4.0
    assert res.t.tolist() == [4.0]
    assert res.event_times == (("apex", 4.0),)
    assert np.array_equal(res.y_end, y0)
    assert res.dense is None
    assert any("already past" in note for note in res.notes)


def test_direction_zero_convention(tight_settings: IntegratorSettings) -> None:
    """A two-sided event (direction 0) is written positive while the phase may continue:
    a negative value at t0 means already past; an exact zero at t0 is disarmed."""
    layout = VERTICAL_LAYOUT

    def height(t: float, y: np.ndarray) -> float:
        return float(layout.get(y, "z_m"))

    ev = EventSpec("ground", height, terminal=True, direction=0)
    past = integrate_phase(
        _spec("FALL", _params(v_sign=-1), (ev,), sigma=-1),
        layout.build(z_m=-1.0, m_kg=1.0),
        tight_settings,
    )
    assert past.ended_by == "ground" and past.t_end == 0.0
    at_zero = integrate_phase(
        _spec("FALL", _params(v_sign=-1), (ev, ev_impact(-50.0)), sigma=-1),
        layout.build(z_m=0.0, m_kg=1.0),
        tight_settings,
    )
    assert at_zero.ended_by == "impact"
    assert any("ground" in note and "disarmed" in note for note in at_zero.notes)


# --------------------------------------------------------------- short phases


def test_zero_length_phase_passes_the_state_through(tight_settings: IntegratorSettings) -> None:
    y0 = VERTICAL_LAYOUT.build(z_m=5.0, v_mps=2.0, m_kg=3.0)
    spec = _spec("COAST", _params(), (ev_apex(),), t0=1.5, t_end=1.5)
    res = integrate_phase(spec, y0, tight_settings)
    assert res.ended_by == "zero_span"
    assert res.t_end == 1.5 and res.span_s == 0.0
    assert np.array_equal(res.y_end, y0)
    assert res.y.shape == (len(VERTICAL_STATE_NAMES), 1)


def test_very_short_phase_integrates(tight_settings: IntegratorSettings) -> None:
    """A 1e-4 s phase is shorter than the configured first step (1e-3 s), which scipy
    would reject; the engine caps the first step at half the span."""
    dt = 1e-4
    v0 = 20.0
    z0 = 3.0
    spec = _spec("COAST", _params(), (ev_apex(),), t0=2.0, t_end=2.0 + dt)
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(z_m=z0, v_mps=v0, m_kg=1.0), tight_settings)
    assert res.ended_by == "t_end"
    assert res.t_end == 2.0 + dt
    assert math.isclose(_z(res.y_end), z0 + v0 * dt - 0.5 * G * dt * dt, rel_tol=1e-12)
    assert math.isclose(_v(res.y_end), v0 - G * dt, rel_tol=1e-12)


def test_open_ended_phase_without_terminal_event_raises_at_t_max() -> None:
    settings = IntegratorSettings(t_max_s=0.5)
    spec = _spec("COAST", _params(), (), t0=0.0, t_end=None)
    with pytest.raises(RuntimeError, match=r"COAST.*t_max"):
        integrate_phase(spec, VERTICAL_LAYOUT.build(z_m=1e6, v_mps=1.0, m_kg=1.0), settings)


def test_non_terminal_events_are_logged_but_do_not_end_the_phase(
    tight_settings: IntegratorSettings,
) -> None:
    marker = EventSpec("halfway", lambda t, y: t - 1.0, terminal=False, direction=+1)
    spec = _spec("COAST", _params(), (marker, ev_apex()))
    res = integrate_phase(spec, VERTICAL_LAYOUT.build(v_mps=3.0 * G, m_kg=1.0), tight_settings)
    assert res.ended_by == "apex"
    assert [name for name, _ in res.event_times] == ["halfway", "apex"]
    assert math.isclose(res.event_times[0][1], 1.0, rel_tol=1e-12)
    assert math.isclose(res.t_end, 3.0, rel_tol=1e-9)


# ------------------------------------------------------------- helpers, specs


def test_liftoff_event_is_thrust_minus_weight(toy_stage: Stage) -> None:
    t_ramp = 2.0
    schedule = toy_stage.schedule(0.0, startup=Startup("ramp", t_ramp_s=t_ramp))
    ev = ev_liftoff(schedule, G)
    assert ev.terminal and ev.direction == +1
    m = 900.0
    t = 0.75
    expected = toy_stage.engine.thrust_vac_N * (t / t_ramp) - m * G
    assert math.isclose(ev.fn(t, VERTICAL_LAYOUT.build(m_kg=m)), expected, rel_tol=1e-12)
    assert ev.fn(-1.0, VERTICAL_LAYOUT.build(m_kg=m)) == -m * G
    # Phase 2 hook: with an ambient pressure the event uses the delivered thrust
    # T_vac - p_amb A_e (clamped at 0), not the vacuum thrust. The toy stage has no
    # exit area, so build a schedule whose back-pressure deficit is a quarter of T_full.
    t_full, a_e, p_amb = 15_000.0, 0.5, 7_500.0
    sea_level = ThrustSchedule(t_full, 3000.0, a_e, 0.0, Startup("ramp", t_ramp_s=t_ramp))
    ev_sl = ev_liftoff(sea_level, G, p_amb_pa=p_amb)
    expected_sl = t_full * (t / t_ramp) - p_amb * a_e - m * G
    assert math.isclose(ev_sl.fn(t, VERTICAL_LAYOUT.build(m_kg=m)), expected_sl, rel_tol=1e-12)
    assert ev_sl.fn(0.1, VERTICAL_LAYOUT.build(m_kg=m)) == -m * G  # thrust clamped at 0
    with pytest.raises(ValueError, match="p_amb_pa"):
        ev_liftoff(sea_level, G, p_amb_pa=-1.0)


def test_atol_by_unit_suffix() -> None:
    atol = atol_for(("z_m", "v_mps", "m_kg", "J_vac_mps", "E_drive_J"))
    assert atol.tolist() == [1e-6, 1e-9, 1e-6, 1e-9, 1e-3]
    with pytest.raises(ValueError, match="unit suffix"):
        atol_for(("z_m", "J_mass"))


def test_state_layout_and_model() -> None:
    layout = StateLayout(("a_m", "b_mps"))
    y = layout.build(b_mps=2.0)
    assert y.tolist() == [0.0, 2.0]
    assert layout.index("b_mps") == 1 and len(layout) == 2
    with pytest.raises(KeyError):
        layout.index("c_kg")
    with pytest.raises(ValueError):
        StateLayout(("a_m", "a_m"))
    model = VerticalDynamics1D()
    assert model.state_names == VERTICAL_STATE_NAMES
    assert model.i_mass == VERTICAL_LAYOUT.index("m_kg")
    y = VERTICAL_LAYOUT.build(z_m=7.0, v_mps=-2.0, m_kg=1.0)
    assert model.altitude(y) == 7.0 and model.speed(y) == 2.0
    p = _params(v_sign=-1, gravity=InverseSquareGravity(MU_EARTH_M3S2))
    dy = model.rhs(0.0, y, p)
    assert dy[VERTICAL_LAYOUT.index("z_m")] == -2.0
    g = MU_EARTH_M3S2 / (R_EARTH_M + 7.0) ** 2
    assert math.isclose(dy[VERTICAL_LAYOUT.index("v_mps")], -g, rel_tol=1e-15)
    assert math.isclose(dy[VERTICAL_LAYOUT.index("J_grav_mps")], -g, rel_tol=1e-15)
    assert math.isclose(dy[VERTICAL_LAYOUT.index("J_alt_mps")], -(g - G), rel_tol=1e-12)


def test_integrator_settings_from_config() -> None:
    settings = IntegratorSettings.from_config(IntegratorConfig())
    assert settings == IntegratorSettings()
    assert settings.method == "DOP853" and settings.rtol == 1e-10
    assert IntegratorSettings(method="RK45").method == "RK45"
    with pytest.raises(ValueError, match="method"):
        IntegratorSettings(method="DOP854")
    with pytest.raises(ValueError):
        VerticalParams(gravity=ConstantGravity(G), g_ref_mps2=G, schedule=None, v_sign=0)
    with pytest.raises(ValueError):
        PhaseSpec("X", 0, 1.0, 0.5, rhs_vertical, None, (), ATOL)
    with pytest.raises(ValueError):
        EventSpec("bad", lambda t, y: 0.0, terminal=True, direction=-1, zero_tol=-1.0)


def test_sigma_must_match_params_v_sign() -> None:
    """The RHS reads params.v_sign; a PhaseSpec whose sigma disagrees is refused so a
    planner cannot silently flip the sign of J_grav, J_alt and J_steer for a phase."""
    with pytest.raises(ValueError, match=r"sigma 1 != params.v_sign -1"):
        _spec("COAST", _params(v_sign=-1), (ev_apex(),), sigma=1)
    with pytest.raises(ValueError, match=r"sigma -1 != params.v_sign 1"):
        _spec("FALL", _params(v_sign=1), (ev_impact(0.0),), sigma=-1)
    # params without a v_sign (None here; track params later) are not checked.
    PhaseSpec("X", 0, 0.0, 1.0, rhs_vertical, None, (), ATOL, sigma=-1)


def test_rotation_rate_and_track_gravity() -> None:
    """omega_p = omega_E cos(lat) sin(az); g_eff = mu/R_E^2 - omega_p^2 R_E."""
    assert math.isclose(planar_rotation_rate(0.0, math.pi / 2) * R_EARTH_M, 465.101, rel_tol=1e-5)
    lat = math.radians(28.5)
    az = math.radians(90.0)
    omega_p = OMEGA_EARTH_RADS * math.cos(lat) * math.sin(az)
    assert math.isclose(planar_rotation_rate(lat, az), 6.408435e-5, rel_tol=1e-7)
    assert math.isclose(planar_rotation_rate(lat, az), omega_p, rel_tol=1e-15)
    g_pad = MU_EARTH_M3S2 / R_EARTH_M**2
    assert math.isclose(g_eff_track(0.0), 9.7982855, rel_tol=1e-7)
    assert math.isclose(g_eff_track(0.0), g_pad, rel_tol=1e-15)
    assert math.isclose(g_eff_track(6.408435e-5), 9.7720917, rel_tol=1e-7)
    assert math.isclose(g_eff_track(omega_p), g_pad - omega_p**2 * R_EARTH_M, rel_tol=1e-15)


# -------------------------------------------------------------- release mapping


def test_release_map_1d() -> None:
    """(s = L, sdot, m) on a vertical track -> z = exit altitude, v = sdot, m; quadratures
    zero. A tilted exit is refused: projecting sdot onto the vertical is not a physical
    reduction (it would discard the downrange component), so the 1-D map is exact only
    for phi = pi/2 and a tilted track is the planar branch of Phase 2."""
    y = map_release(76.707, 539_000.0, math.pi / 2, 0.0)
    assert y.tolist() == VERTICAL_LAYOUT.build(v_mps=76.707, m_kg=539_000.0).tolist()
    y = map_release(50.0, 1000.0, math.pi / 2, 12.0)
    assert _v(y) == 50.0 and _z(y) == 12.0
    assert all(y[VERTICAL_LAYOUT.index(n)] == 0.0 for n in VERTICAL_STATE_NAMES if n[0] == "J")
    with pytest.raises(ValueError, match="vertical track"):
        map_release(50.0, 1000.0, math.pi / 6, 12.0)
    with pytest.raises(ValueError, match="vertical track"):
        map_release(50.0, 1000.0, math.pi / 2 - 1e-6, 0.0)


@pytest.mark.parametrize("v0", [0.0, 77.0])
def test_pad_start_through_simulate_is_the_release_state(
    v0: float, toy_stage: Stage, tight_settings: IntegratorSettings
) -> None:
    """A pad start through ``simulate``: the release state is (z = 0, v = v0) with every
    quadrature zero, t_release = 0 and speed_start = |v0| for v0 = 0 and v0 != 0."""
    vehicle = Vehicle(stages=(toy_stage,))
    result = sim.simulate(
        vehicle,
        {"stage1": IgnitionSpec(0.0)},
        ConstantGravity(G),
        G,
        sim.NoAssist(),
        None,
        AscentStart(0.0, v0),
        "stage1_burnout",
        tight_settings,
    )
    m = result.metrics
    assert m["t_release_s"] == 0.0 and m["alt_at_release_m"] == 0.0
    assert m["speed_at_release_mps"] == v0 and m["speed_start_mps"] == v0
    assert m["propellant_burned_before_release_kg"] == 0.0
    release = result.events[result.events["event"] == "release"].iloc[0]
    assert float(release["t_s"]) == 0.0 and float(release["z_m"]) == 0.0
    assert float(release["v_mps"]) == v0
    assert float(release["m_kg"]) == vehicle.liftoff_mass_kg()
    first = result.timeseries.iloc[0]
    assert first["t_s"] == 0.0 and first["z_m"] == 0.0 and first["v_mps"] == v0
    assert all(first[n] == 0.0 for n in VERTICAL_STATE_NAMES if n.startswith("J_"))
    assert result.phases[0].spec.t0 == 0.0 and result.phases[0].spec.kind == "BURN"
    assert result.loss_budget is not None and result.loss_budget.speed_start == v0
