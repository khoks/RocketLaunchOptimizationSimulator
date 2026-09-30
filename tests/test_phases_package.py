"""The phases package (engine, trace, prelude, vertical) and the engine features added
for Phase 2 searches.

- Search-mode event states: with ``IntegratorSettings.dense_output = False`` the engine
  keeps no dense output, and ``event_state`` reads every event occurrence from
  ``PhaseResult.y_events`` (scipy's ``sol.y_events``). A toy vertical burn under a
  constant g_test with a non-terminal altitude mark and the terminal propellant event
  must give the same steps, event times and event states as the dense run, and the
  mark's state must match the closed form

      v(t) = v0 - g t + c ln(m0 / (m0 - mdot t))
      z(t) = z0 + v0 t - g t^2/2 + c [t - ((m0 - mdot t)/mdot) ln(m0 / (m0 - mdot t))]

  (the same closed form as ``test_vertical_burn.py``). Events that fire several
  times in one phase keep their occurrences in time order: a harmonic oscillator
  x = A cos(w t) crosses x = 1 at t = (+-acos(1/A) + 2 pi k)/w and has v = 0 at
  t = pi k / w, with states (A cos w t, -A w sin w t), and ``event_state`` must return
  the k-th closed-form state for the k-th root, dense output on or off. The track
  prelude (``fly_track``, whose events are all terminal) logs the same events and exit
  with dense output off as with it on. A pass-through lists every event of its spec.
- Dense output off is for search evaluations only: ``VerticalPlanner`` refuses it,
  ``PhaseResult.dense_off`` marks such a phase and ``RunTrace.require_dense`` raises
  on a trace that has one.
- ``PhaseResult.nfev`` equals the number of right-hand-side calls solve_ivp made (a
  counting RHS), 0 for a pass-through; ``RunTrace.nfev_total`` sums the phases.
- ``atol_for`` maps ``_rad`` to ATOL_M / R_E; ``atol_scale`` scales every atol.
- The prelude on a layout other than the 1-D one: a clamped hold burns T/c per second
  and holds every other entry; the liftoff of a TWR < 1 hold is at
  t = (m0 - T/g)/mdot; a tilted straight track exits at x = L cos phi,
  z = z0 + L sin phi with sdot = sqrt(2 a L) after t = sqrt(2 L / a); a quarter-circle
  arc of radius r = 2 L / pi (a geometry without x(s)) exits vertical at z0 + r with
  the same sdot and t and an unknown downrange offset (None), and the 1-D planner
  still runs it; a builder whose view reads another layout is refused.
- The 1-D StateView keeps z_m and the signed v_mps exactly; event records are frozen
  and hashable, with their values stored as Python floats; every name the Phase 1
  ``phases.py`` defined or imported from
  launchsim is still importable from ``launchsim.phases``; the package's public
  functions and classes carry docstrings (the scaffold rule, applied to the package's
  modules).
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import math
from pathlib import Path

import numpy as np
import pytest

import launchsim.phases as phases
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import IntegratorConfig
from launchsim.constants import G0_MPS2, R_EARTH_M
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    ConstantGravity,
    StateLayout,
    VerticalParams,
    rhs_vertical,
)
from launchsim.phases import (
    ATOL_M,
    ATOL_RAD,
    VERTICAL_VIEW,
    EventRecord,
    EventSpec,
    HoldParams,
    IgnitionSpec,
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    RhsFn,
    TraceBuilder,
    TrackExit,
    VerticalPlanner,
    atol_for,
    ev_propellant,
    event_state,
    fly_track,
    hold_closed_form,
    hold_rhs_for,
    hold_until_liftoff,
    integrate_phase,
)
from launchsim.vehicle import Stage, Vehicle

G_TEST = 9.81
"""Constant gravity of the analytic cases [m/s^2] (a named test value, not g0)."""
Z0 = 12.5
V0 = 30.0
Z_MARK = 2_000.0
"""Altitude [m] of the non-terminal event the toy burn crosses on its way up."""

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "launchsim" / "phases"

PHASE1_NAMES = (
    "EventFn",
    "RhsFn",
    "ZERO_SPAN_S",
    "EVENT_ZERO_TOL",
    "SUPPORTED_METHODS",
    "SAMPLE_GRID_REL_EPS",
    "VERTICAL_TRACK_TOL_RAD",
    "ATOL_M",
    "ATOL_MPS",
    "ATOL_KG",
    "ATOL_J",
    "_ATOL_BY_SUFFIX",
    "IntegratorSettings",
    "EventSpec",
    "PhaseSpec",
    "PhaseResult",
    "atol_for",
    "_already_past",
    "_would_fire",
    "_guard_value",
    "_event_callable",
    "_predict_state",
    "_pass_through",
    "integrate_phase",
    "_terminal_event_at",
    "ev_propellant",
    "ev_apex",
    "ev_turnaround",
    "ev_impact",
    "ev_liftoff",
    "ev_track_end",
    "ev_drive_limit",
    "MAX_PHASES_PER_RUN",
    "END_KINDS",
    "IGNITION_REFERENCES",
    "HOLD_KIND",
    "ASSIST_KIND",
    "RELEASE_LABEL",
    "ASCENT_KINDS",
    "_IZ",
    "_IV",
    "_IM",
    "IgnitionSpec",
    "_DEFAULT_IGNITION",
    "AscentStart",
    "HoldParams",
    "rhs_hold",
    "EventRecord",
    "HoldSummary",
    "RunTrace",
    "TraceBuilder",
    "map_release",
    "map_staging",
    "sample_grid",
    "VerticalPlanner",
)
"""Every top-level name the single-module ``phases.py`` defined at d8d6951."""

PHASE1_IMPORTED_NAMES = (
    "R_EARTH_M",
    "VERTICAL_LAYOUT",
    "VERTICAL_STATE_NAMES",
    "Gravity",
    "StateLayout",
    "TrackParams",
    "VerticalParams",
    "rhs_track",
    "rhs_vertical",
    "track_state_names",
    "track_to_vertical",
    "Startup",
    "ThrustSchedule",
    "Vehicle",
    "propellant_burned_kg",
)
"""The launchsim names the single-module ``phases.py`` imported at d8d6951 (reachable
as ``launchsim.phases.<name>`` then, so still re-exported)."""

PLANAR_LIKE = StateLayout(("r_m", "theta_rad", "v_r_mps", "v_theta_mps", "m_kg", "J_vac_mps"))
"""A state layout other than the 1-D one, for the layout-parameterised prelude."""
A_TRACK = 3.0 * G_TEST
"""Net track acceleration of the prelude cases [m/s^2]."""
L_TRACK = 100.0
"""Track length of the prelude cases [m]."""
OSC_AMPLITUDE_M = 5.0
"""Amplitude A [m] of the oscillator used for repeated event occurrences."""
OSC_OMEGA_RADPS = 2.0 * math.pi / 3.0
"""Angular frequency w [rad/s] of that oscillator (period 3 s)."""
OSC_T0_S = 0.1
"""Start time [s] of the oscillator phase (off the v = 0 root at t = 0)."""
OSC_T1_S = 10.0
"""End time [s] of the oscillator phase."""


@dataclasses.dataclass(frozen=True)
class Arc:
    """A quarter-circle track of length L_TRACK satisfying the TrackGeometry protocol
    but not a StraightTrack: phi(s) = (pi/2) s / L from horizontal to vertical, radius
    r = 2 L / pi, z(s) = r (1 - cos(s / r))."""

    length_m: float = L_TRACK
    start_altitude_m: float = 0.0

    def phi(self, s_m: float) -> float:
        """Track angle [rad] at arc length s_m [m]."""
        return 0.5 * math.pi * s_m / self.length_m

    def kappa(self, s_m: float) -> float:
        """Curvature [1/m] (constant)."""
        return 0.5 * math.pi / self.length_m

    def z(self, s_m: float) -> float:
        """Height [m] above the track start at arc length s_m [m]."""
        r = 2.0 * self.length_m / math.pi
        return r * (1.0 - math.cos(s_m / r))


@dataclasses.dataclass(frozen=True)
class ToyView:
    """A StateView of PLANAR_LIKE for the prelude tests: r_m and m_kg, read as floats."""

    model: str = "toy_planar"
    layout: StateLayout = PLANAR_LIKE
    columns: tuple[str, ...] = ("r_m", "m_kg")
    ascent_kinds: tuple[str, ...] = ("FLIGHT",)

    def row(self, t: float, y: np.ndarray, phase: str) -> dict[str, float]:
        """r_m and m_kg of a PLANAR_LIKE state."""
        return {c: float(self.layout.get(y, c)) for c in self.columns}


def _toy_burn_spec(
    toy_stage: Stage, *, with_mark: bool = True, rhs: RhsFn = rhs_vertical
) -> PhaseSpec:
    """The toy stage lit (step) at t = 0 under constant G_TEST from (Z0, V0): the
    terminal propellant event and, optionally, a non-terminal mark at Z_MARK."""
    params = VerticalParams(
        gravity=ConstantGravity(G_TEST),
        g_ref_mps2=G_TEST,
        schedule=toy_stage.schedule(0.0),
        v_sign=1,
    )
    i_z = VERTICAL_LAYOUT.index("z_m")
    mark = EventSpec(
        "mark", lambda t, y: y[i_z] - Z_MARK, terminal=False, direction=1, zero_tol=ATOL_M
    )
    events = (mark, ev_propellant(toy_stage.dry_mass_kg)) if with_mark else ()
    return PhaseSpec(
        kind="BURN",
        stage_index=0,
        t0=0.0,
        t_end=None if with_mark else 50.0,
        rhs=rhs,
        params=params,
        events=events,
        atol=atol_for(VERTICAL_STATE_NAMES),
    )


def _toy_y0(toy_stage: Stage) -> np.ndarray:
    m0 = toy_stage.dry_mass_kg + toy_stage.propellant_mass_kg
    return VERTICAL_LAYOUT.build(z_m=Z0, v_mps=V0, m_kg=m0)


# ------------------------------------------------------------------ search-mode events


def test_dense_output_off_gives_identical_event_states(toy_stage: Stage) -> None:
    spec = _toy_burn_spec(toy_stage)
    y0 = _toy_y0(toy_stage)
    on = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-10))
    off = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-10, dense_output=False))

    assert on.dense is not None and off.dense is None
    assert on.ended_by == off.ended_by == "propellant"
    assert np.array_equal(on.t, off.t) and np.array_equal(on.y, off.y)
    assert on.event_times == off.event_times
    assert [n for n, _ in off.event_times] == ["mark", "propellant"]
    # scipy builds a step's interpolant for the event search only in steps where an
    # event is active; with dense output on it builds one in every step
    assert 0 < off.nfev < on.nfev

    for name, te in off.event_times:
        y_off = event_state(off, name, te)
        y_on = event_state(on, name, te)
        assert np.array_equal(y_off, y_on)
        assert np.allclose(y_off, np.asarray(on.dense(te)), rtol=1e-12, atol=0.0)
    assert np.array_equal(event_state(off, "propellant", off.t_end), off.y_end)

    # The mark's state against the closed form of a constant-g vertical burn.
    t_mark = dict(off.event_times)["mark"]
    y_mark = event_state(off, "mark", t_mark)
    c = G0_MPS2 * toy_stage.engine.isp_vac_s
    mdot = toy_stage.engine.thrust_vac_N / c
    m0 = float(y0[VERTICAL_LAYOUT.index("m_kg")])
    u = m0 - mdot * t_mark
    v_cf = V0 - G_TEST * t_mark + c * math.log(m0 / u)
    z_rocket = c * (t_mark - (u / mdot) * math.log(m0 / u))
    z_cf = Z0 + V0 * t_mark - 0.5 * G_TEST * t_mark**2 + z_rocket
    assert abs(float(VERTICAL_LAYOUT.get(y_mark, "z_m")) - Z_MARK) <= ATOL_M
    assert math.isclose(z_cf, Z_MARK, rel_tol=1e-8)
    assert math.isclose(float(VERTICAL_LAYOUT.get(y_mark, "v_mps")), v_cf, rel_tol=1e-9)
    assert math.isclose(float(VERTICAL_LAYOUT.get(y_mark, "m_kg")), u, rel_tol=1e-12)


def test_event_state_rejects_an_unknown_occurrence(toy_stage: Stage) -> None:
    res = integrate_phase(
        _toy_burn_spec(toy_stage), _toy_y0(toy_stage), IntegratorSettings(dense_output=False)
    )
    with pytest.raises(ValueError, match="no event states"):
        event_state(res, "apex", res.t_end)
    with pytest.raises(ValueError, match="did not occur"):
        event_state(res, "mark", res.t_end)


def test_already_past_event_state_is_the_start_state(toy_stage: Stage) -> None:
    """A terminal event already past at t0 ends the phase there; its y_events entry is
    the state at t0 and nothing is integrated (nfev 0)."""
    y0 = _toy_y0(toy_stage)
    m0 = float(VERTICAL_LAYOUT.get(y0, "m_kg"))
    spec = dataclasses.replace(_toy_burn_spec(toy_stage), events=(ev_propellant(m0 + 1.0),))
    res = integrate_phase(spec, y0, IntegratorSettings(dense_output=False))
    assert res.ended_by == "propellant" and res.t_end == 0.0 and res.nfev == 0
    assert np.array_equal(event_state(res, "propellant", 0.0), y0)


def _rhs_oscillator(t: float, y: np.ndarray, omega: float) -> np.ndarray:
    """x' = v, v' = -omega^2 x (state (x_m, v_mps))."""
    return np.array([y[1], -(omega**2) * y[0]])


def test_repeated_event_occurrences_keep_their_order() -> None:
    """Two non-terminal direction-0 events that fire several times in one phase: every
    occurrence's state from ``event_state`` is the closed-form state at that root, in
    time order, with dense output on and off (a lookup that ignored te, or reversed
    y_events, would give the wrong sign of v at alternate x = 1 crossings)."""
    a, w = OSC_AMPLITUDE_M, OSC_OMEGA_RADPS
    events = (
        EventSpec("xmark", lambda t, y: y[0] - 1.0, terminal=False, direction=0, zero_tol=ATOL_M),
        EventSpec("vzero", lambda t, y: y[1], terminal=False, direction=0, zero_tol=ATOL_M),
    )
    y0 = np.array([a * math.cos(w * OSC_T0_S), -a * w * math.sin(w * OSC_T0_S)])
    spec = PhaseSpec("COAST", 0, OSC_T0_S, OSC_T1_S, _rhs_oscillator, w, events, np.full(2, 1e-12))

    phase = math.acos(1.0 / a)
    k_max = 4
    x_roots = sorted(
        t
        for k in range(k_max)
        for t in ((phase + 2.0 * math.pi * k) / w, (2.0 * math.pi * (k + 1) - phase) / w)
        if OSC_T0_S < t < OSC_T1_S
    )
    v_roots = [math.pi * k / w for k in range(1, 2 * k_max) if math.pi * k / w < OSC_T1_S]
    assert (len(x_roots), len(v_roots)) == (7, 6)

    results = [
        integrate_phase(spec, y0, IntegratorSettings(rtol=1e-12, dense_output=dense))
        for dense in (True, False)
    ]
    for res in results:
        assert res.ended_by == "t_end"
        for name, roots in (("xmark", x_roots), ("vzero", v_roots)):
            times = [te for n, te in res.event_times if n == name]
            assert len(times) == len(roots) and res.y_events[name].shape == (len(roots), 2)
            for te, t_cf in zip(times, roots, strict=True):
                assert abs(te - t_cf) <= 1e-9
                y_cf = np.array([a * math.cos(w * t_cf), -a * w * math.sin(w * t_cf)])
                assert np.allclose(event_state(res, name, te), y_cf, rtol=0.0, atol=1e-8)
    on, off = results
    assert on.event_times == off.event_times
    for name, te in on.event_times:
        assert np.array_equal(event_state(on, name, te), event_state(off, name, te))
        assert np.allclose(event_state(on, name, te), on.dense(te), rtol=0.0, atol=1e-11)


def _silo_exit(
    vehicle: Vehicle, settings: IntegratorSettings, track: StraightTrack, t_ign_s: float
) -> tuple[TraceBuilder, TrackExit | None]:
    """fly_track of the toy vehicle on a constant-acceleration track (a = A_TRACK,
    300 kg carriage) under G_TEST, stage 1 lit t_ign_s after the release estimate."""
    assist = ConstantAccelAssist(A_TRACK, 300.0, 5.0 * G_TEST)
    tr = TraceBuilder(vehicle.stage_names)
    exit_ = fly_track(
        tr,
        assist,
        track,
        IgnitionSpec(t_ign_s),
        vehicle=vehicle,
        settings=settings,
        g_eff_mps2=G_TEST,
        p_amb_pa=0.0,
    )
    return tr, exit_


def test_track_prelude_with_dense_output_off_logs_the_same_events(
    two_stage_toy: Vehicle,
) -> None:
    """A hot push lit mid-track with dense output off records exactly the events and
    the exit of the dense run: every track event is terminal, so the Phase 1 lookup
    returns the phase's last state either way (physics.md, Event rules, rule 4)."""
    track = StraightTrack(L_TRACK, VERTICAL, -L_TRACK)
    tr_on, on = _silo_exit(two_stage_toy, IntegratorSettings(rtol=1e-10), track, -1.0)
    tr_off, off = _silo_exit(
        two_stage_toy, IntegratorSettings(rtol=1e-10, dense_output=False), track, -1.0
    )
    assert on is not None and off is not None
    assert [e.name for e in tr_on.events] == ["push_start", "ignition"]
    assert tr_on.events == tr_off.events
    assert on.t_release_s == off.t_release_s and np.array_equal(on.y_track, off.y_track)
    assert all(p.dense_off for p in tr_off.phases) and not any(p.dense_off for p in tr_on.phases)
    assert math.isclose(on.sdot_mps, math.sqrt(2.0 * A_TRACK * L_TRACK), rel_tol=1e-10)


def test_dense_output_off_is_refused_for_recorded_runs(
    two_stage_toy: Vehicle, toy_stage: Stage
) -> None:
    """The 1-D planner produces recorded runs only; a trace with a dense-off phase
    fails ``require_dense``; one whose phases lack dense output only because there is
    nothing to resample (closed-form hold, pass-through) passes."""
    ignition = {s.name: IgnitionSpec() for s in two_stage_toy.stages}
    with pytest.raises(ValueError, match="dense_output = False"):
        VerticalPlanner(
            two_stage_toy,
            ignition,
            ConstantGravity(G_TEST),
            G_TEST,
            "impact",
            IntegratorSettings(dense_output=False),
        )

    spec = _toy_burn_spec(toy_stage)
    y0 = _toy_y0(toy_stage)
    tr = TraceBuilder(("stage1",))
    hold_closed_form(
        tr,
        HoldParams(toy_stage.schedule(-1.0), G_TEST),
        -1.0,
        0.0,
        y0,
        vehicle=two_stage_toy,
        settings=IntegratorSettings(),
    )
    tr.add_phase(
        integrate_phase(
            dataclasses.replace(spec, t0=0.0, t_end=0.0), y0, IntegratorSettings(dense_output=False)
        )
    )
    tr.add_phase(integrate_phase(spec, y0, IntegratorSettings()))
    dense = tr.finish()
    assert not dense.dense_off
    dense.require_dense("test")

    tr.add_phase(integrate_phase(spec, y0, IntegratorSettings(dense_output=False)))
    sparse = tr.finish()
    assert sparse.dense_off and sparse.phases[-1].dense_off
    with pytest.raises(ValueError, match=r"report: .*BURN.*search evaluations only"):
        sparse.require_dense("report")


def test_pass_through_lists_every_event(toy_stage: Stage) -> None:
    """A pass-through maps every listed event to its states, as an integrated phase
    does: (0, n) for the events that did not fire, (1, n) = y0 for the one that did."""
    y0 = _toy_y0(toy_stage)
    n = y0.size
    spec = _toy_burn_spec(toy_stage)
    zero = integrate_phase(dataclasses.replace(spec, t_end=0.0), y0, IntegratorSettings())
    assert zero.ended_by == "zero_span"
    assert {k: v.shape for k, v in zero.y_events.items()} == {
        "mark": (0, n),
        "propellant": (0, n),
    }
    m0 = float(VERTICAL_LAYOUT.get(y0, "m_kg"))
    past_events = (spec.events[0], ev_propellant(m0 + 1.0))
    past = integrate_phase(dataclasses.replace(spec, events=past_events), y0, IntegratorSettings())
    assert past.ended_by == "propellant"
    assert past.y_events["mark"].shape == (0, n)
    assert np.array_equal(past.y_events["propellant"], y0.reshape(1, -1))


# ------------------------------------------------------------------------------ nfev


def test_nfev_counts_the_solver_rhs_calls(toy_stage: Stage) -> None:
    calls = [0]

    def counting_rhs(t: float, y: np.ndarray, p: VerticalParams) -> np.ndarray:
        calls[0] += 1
        return rhs_vertical(t, y, p)

    for dense in (True, False):
        calls[0] = 0
        spec = _toy_burn_spec(toy_stage, rhs=counting_rhs)
        res = integrate_phase(spec, _toy_y0(toy_stage), IntegratorSettings(dense_output=dense))
        assert res.nfev == calls[0] > 0  # no event at zero at t0: no Heun prediction
    zero = PhaseSpec("COAST", 0, 1.0, 1.0, rhs_vertical, None, (), atol_for(VERTICAL_STATE_NAMES))
    assert integrate_phase(zero, _toy_y0(toy_stage), IntegratorSettings()).nfev == 0


def test_dense_output_off_saves_rhs_calls_without_events(toy_stage: Stage) -> None:
    """With no events DOP853 builds its interpolant only for the dense output, so
    turning it off changes nothing (same steps, same end state) and saves RHS calls."""
    spec = _toy_burn_spec(toy_stage, with_mark=False)
    y0 = _toy_y0(toy_stage)
    on = integrate_phase(spec, y0, IntegratorSettings())
    off = integrate_phase(spec, y0, IntegratorSettings(dense_output=False))
    assert np.array_equal(on.t, off.t) and np.array_equal(on.y_end, off.y_end)
    assert 0 < off.nfev < on.nfev
    assert dict(off.y_events) == {} and off.event_times == ()


# ---------------------------------------------------------------------- tolerances


def test_rad_suffix_and_atol_scale(toy_stage: Stage) -> None:
    assert ATOL_RAD == ATOL_M / R_EARTH_M
    assert math.isclose(ATOL_RAD, 1.5678e-13, rel_tol=1e-4)
    names = ("r_m", "theta_rad", "v_r_mps", "m_kg", "E_drive_J")
    atol = atol_for(names)
    assert atol[1] == ATOL_RAD and atol[0] == ATOL_M
    with pytest.raises(ValueError, match="unit suffix"):
        atol_for(("theta_deg",))

    y0 = _toy_y0(toy_stage)
    spec = _toy_burn_spec(toy_stage)
    scaled = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-8, atol_scale=10.0))
    manual = integrate_phase(
        dataclasses.replace(spec, atol=spec.atol * 10.0), y0, IntegratorSettings(rtol=1e-8)
    )
    unscaled = integrate_phase(spec, y0, IntegratorSettings(rtol=1e-8))
    assert np.array_equal(scaled.t, manual.t) and np.array_equal(scaled.y, manual.y)
    assert not np.array_equal(scaled.t, unscaled.t)
    for bad in (0.0, -1.0, math.inf, math.nan):
        with pytest.raises(ValueError, match="atol_scale"):
            IntegratorSettings(atol_scale=bad)


def test_method_comes_from_the_config() -> None:
    """``from_config`` takes the config's ``method`` when the config model carries it
    (a stand-in here; ``IntegratorConfig`` gains the field with the Phase 2 schema)
    and DOP853 otherwise; dense_output and atol_scale have no YAML key."""

    @dataclasses.dataclass(frozen=True)
    class WithMethod:
        method: str = "RK45"
        rtol: float = 1e-9
        first_step_s: float = 1e-3
        ramp_steps: int = 10
        lag_steps_per_tau: int = 4
        push_steps: int = 50
        planar_max_step_s: float = 2.0
        t_max_s: float = 3600.0
        sample_dt_s: float = 0.05

    settings = IntegratorSettings.from_config(WithMethod())  # type: ignore[arg-type]
    assert settings.method == "RK45" and settings.rtol == 1e-9
    assert settings.dense_output is True and settings.atol_scale == 1.0
    assert IntegratorSettings.from_config(IntegratorConfig()).method == "DOP853"
    with pytest.raises(ValueError, match="method"):
        IntegratorSettings.from_config(WithMethod(method="LSODA"))  # type: ignore[arg-type]


# --------------------------------------------------------------------- trace records


def test_vertical_view_keeps_z_and_signed_v() -> None:
    y = VERTICAL_LAYOUT.build(z_m=123.25, v_mps=-1.4e-12, m_kg=5_000.5)
    assert VERTICAL_VIEW.columns == ("z_m", "v_mps", "m_kg")
    row = VERTICAL_VIEW.row(0.0, y, "FALL")
    assert row == {"z_m": 123.25, "v_mps": -1.4e-12, "m_kg": 5_000.5}
    assert VERTICAL_VIEW.layout == VERTICAL_LAYOUT
    assert all(type(v) is float for v in row.values())

    tr = TraceBuilder(("stage1",))
    tr.add_event("apex", 3.0, "FALL", 0, VERTICAL_LAYOUT.build(z_m=7.0, v_mps=-0.0, m_kg=2.0))
    rec = tr.events[0]
    assert (rec.name, rec.t_s, rec.phase, rec.stage) == ("apex", 3.0, "FALL", "stage1")
    assert rec.z_m == 7.0 and rec.m_kg == 2.0 and rec.value("m_kg") == 2.0
    assert math.copysign(1.0, rec.v_mps) == -1.0  # the sign of zero survives
    assert tr.finish().model == "vertical_1d"


def test_records_and_views_outside_the_1d_columns() -> None:
    rec = EventRecord("mark", 1.0, "X", "stage1", 3.0, {"alt_m": 4.0})
    assert rec.value("alt_m") == 4.0 and rec.values == (("alt_m", 4.0),)
    coerced = EventRecord("mark", 1.0, "X", "stage1", 3.0, [("a_m", np.float64(-0.0)), ("n", 2)])
    assert all(type(v) is float for _, v in coerced.values)
    assert coerced.value("n") == 2.0 and math.copysign(1.0, coerced.value("a_m")) == -1.0
    with pytest.raises(AttributeError, match="z_m"):
        _ = rec.z_m
    with pytest.raises(KeyError, match="v_x"):
        rec.value("v_x")
    with pytest.raises(ValueError, match="duplicate"):
        EventRecord("mark", 1.0, "X", "stage1", 3.0, (("a_m", 1.0), ("a_m", 2.0)))

    alt_layout = StateLayout(("alt_m",))

    @dataclasses.dataclass(frozen=True)
    class NoMass:
        model: str = "toy"
        layout: StateLayout = alt_layout
        columns: tuple[str, ...] = ("alt_m",)
        ascent_kinds: tuple[str, ...] = ()

        def row(self, t: float, y: np.ndarray, phase: str) -> dict[str, float]:
            return {"alt_m": float(y[0])}

    with pytest.raises(ValueError, match="m_kg"):
        TraceBuilder(("stage1",), view=NoMass())


def test_event_records_are_frozen_and_hashable() -> None:
    tr = TraceBuilder(("stage1",))
    y = VERTICAL_LAYOUT.build(z_m=7.0, v_mps=-2.0, m_kg=3.0)
    tr.add_event("apex", 1.0, "FALL", 0, y)
    tr.add_event("apex", 1.0, "FALL", 0, y)
    a, b = tr.events
    assert a == b and hash(a) == hash(b) and len({a, b}) == 1
    assert a.values == (("z_m", 7.0), ("v_mps", -2.0)) and a.columns == ("z_m", "v_mps")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.values = ()  # type: ignore[misc]


def test_builder_refuses_a_state_of_another_layout() -> None:
    """A state is recorded only through a view of its own layout: the 1-D view refuses
    a PLANAR_LIKE state instead of writing r into z_m; a view rebinds only to one of
    the same model, layout and columns."""
    tr = TraceBuilder(("stage1",))
    with pytest.raises(ValueError, match="view reads 8 states"):
        tr.add_event("ignition", -2.0, "HOLD", 0, PLANAR_LIKE.build(r_m=R_EARTH_M, m_kg=5.0))
    assert tr.events == []
    tr.rebind_view(VERTICAL_VIEW)
    with pytest.raises(ValueError, match="rebind_view"):
        tr.rebind_view(ToyView())

    toy = TraceBuilder(("stage1",), view=ToyView())
    toy.rebind_view(ToyView(ascent_kinds=("FLIGHT", "COAST")))
    y = PLANAR_LIKE.build(r_m=R_EARTH_M, m_kg=5.0)
    toy.add_event("mark", 0.5, "FLIGHT", 0, y)
    rec = toy.events[0]
    assert rec.m_kg == 5.0 and rec.value("r_m") == R_EARTH_M
    hold = PhaseSpec(
        "HOLD", 0, 0.0, 1.0, hold_rhs_for(PLANAR_LIKE), None, (), atol_for(PLANAR_LIKE.names)
    )
    fl = dataclasses.replace(hold, kind="COAST")
    for spec in (hold, fl):
        toy.add_phase(PhaseResult(spec, np.array([0.0]), y.reshape(-1, 1), None, "t_end", 0.0, y))
    trace = toy.finish()
    assert trace.model == "toy_planar"
    assert [p.spec.kind for p in trace.ascent_phases()] == ["COAST"]


# ------------------------------------------------------------------------- prelude


def test_hold_on_another_layout_burns_only_the_mass(two_stage_toy: Vehicle) -> None:
    """A clamped hold on PLANAR_LIKE: m drops by mdot dt (T/c = 5 kg/s, 2 s: 10 kg)
    and every other entry, position, velocity and quadrature alike, is held."""
    stage = two_stage_toy.stages[0]
    mdot = stage.engine.thrust_vac_N / (G0_MPS2 * stage.engine.isp_vac_s)
    rhs = hold_rhs_for(PLANAR_LIKE)
    assert rhs is not phases.rhs_hold and hold_rhs_for(VERTICAL_LAYOUT) is phases.rhs_hold
    params = HoldParams(stage.schedule(0.0), G_TEST)
    y0 = PLANAR_LIKE.build(r_m=R_EARTH_M, v_theta_mps=408.0, m_kg=two_stage_toy.liftoff_mass_kg())
    dy = rhs(1.0, y0, params)
    assert math.isclose(float(PLANAR_LIKE.get(dy, "m_kg")), -mdot, rel_tol=1e-15)
    assert np.count_nonzero(dy) == 1

    tr = TraceBuilder(two_stage_toy.stage_names, view=ToyView())
    y1, force_min = hold_closed_form(
        tr,
        params,
        0.0,
        2.0,
        y0,
        vehicle=two_stage_toy,
        settings=IntegratorSettings(),
        layout=PLANAR_LIKE,
    )
    burned = float(PLANAR_LIKE.get(y0 - y1, "m_kg"))
    assert math.isclose(burned, 2.0 * mdot, rel_tol=1e-12)
    keep = [i for i, n in enumerate(PLANAR_LIKE.names) if n != "m_kg"]
    assert np.array_equal(y1[keep], y0[keep])
    m1 = float(PLANAR_LIKE.get(y1, "m_kg"))
    assert math.isclose(force_min, m1 * G_TEST - stage.engine.thrust_vac_N, rel_tol=1e-12)
    with pytest.raises(ValueError, match="hold_closed_form"):
        hold_closed_form(
            TraceBuilder(two_stage_toy.stage_names),
            params,
            0.0,
            2.0,
            y0,
            vehicle=two_stage_toy,
            settings=IntegratorSettings(),
            layout=PLANAR_LIKE,
        )


def test_liftoff_on_another_layout_matches_the_closed_form(two_stage_toy: Vehicle) -> None:
    """A step-lit hold with weight above thrust (g = 12.5 m/s^2: 1360 kg weighs 17 kN
    against 15 kN) lifts off when m g = T, i.e. at t = (m0 - T/g)/mdot = 32 s; a
    builder with the 1-D view is refused."""
    g_hold = 12.5
    stage = two_stage_toy.stages[0]
    thrust = stage.engine.thrust_vac_N
    mdot = thrust / (G0_MPS2 * stage.engine.isp_vac_s)
    m0 = two_stage_toy.liftoff_mass_kg()
    t_cf = (m0 - thrust / g_hold) / mdot
    params = HoldParams(stage.schedule(0.0), g_hold)
    y0 = PLANAR_LIKE.build(r_m=R_EARTH_M, m_kg=m0)
    settings = IntegratorSettings(rtol=1e-10)

    tr = TraceBuilder(two_stage_toy.stage_names, view=ToyView())
    t_lift, y_lift, force_min = hold_until_liftoff(
        tr, params, 0.0, y0, vehicle=two_stage_toy, settings=settings, layout=PLANAR_LIKE
    )
    assert abs(t_lift - t_cf) < 1e-8
    assert math.isclose(float(PLANAR_LIKE.get(y_lift, "m_kg")), thrust / g_hold, rel_tol=1e-10)
    assert float(PLANAR_LIKE.get(y_lift, "r_m")) == R_EARTH_M
    assert [e.name for e in tr.events] == ["ignition", "liftoff"]
    assert tr.events[1].value("r_m") == R_EARTH_M
    assert abs(force_min) < 1e-3
    with pytest.raises(ValueError, match="hold_until_liftoff"):
        hold_until_liftoff(
            TraceBuilder(two_stage_toy.stage_names),
            params,
            0.0,
            y0,
            vehicle=two_stage_toy,
            settings=settings,
            layout=PLANAR_LIKE,
        )


def test_tilted_track_exit_closed_form(two_stage_toy: Vehicle) -> None:
    """A cold push up a straight track at 60 deg from z0 = 5 m: the exit at
    x = L cos phi, z = z0 + L sin phi, sdot = sqrt(2 a L) after t = sqrt(2 L / a),
    with nothing burned (ignition 1 s after release)."""
    phi = math.pi / 3.0
    z0 = 5.0
    track = StraightTrack(L_TRACK, phi, z0)
    tr, exit_ = _silo_exit(two_stage_toy, IntegratorSettings(rtol=1e-10), track, 1.0)
    assert exit_ is not None
    assert math.isclose(exit_.x_exit_m, L_TRACK * math.cos(phi), rel_tol=1e-15)
    assert math.isclose(exit_.z_exit_m, z0 + L_TRACK * math.sin(phi), rel_tol=1e-15)
    assert exit_.phi_rad == phi
    assert math.isclose(exit_.sdot_mps, math.sqrt(2.0 * A_TRACK * L_TRACK), rel_tol=1e-10)
    assert math.isclose(exit_.t_release_s, math.sqrt(2.0 * L_TRACK / A_TRACK), rel_tol=1e-10)
    assert exit_.m_kg == two_stage_toy.liftoff_mass_kg()
    assert [e.name for e in tr.events] == ["push_start"]

    _tr_v, vertical = _silo_exit(
        two_stage_toy, IntegratorSettings(), StraightTrack(L_TRACK, VERTICAL, -L_TRACK), 1.0
    )
    assert vertical is not None and vertical.x_exit_m == 0.0


def test_curved_track_has_no_x_and_still_runs_in_1d(two_stage_toy: Vehicle) -> None:
    """A quarter-circle arc (no x(s)) ending vertical: fly_track exits at
    z = z0 + r with r = 2 L / pi, phi = pi/2, sdot = sqrt(2 a L) after t = sqrt(2 L / a)
    and x_exit_m None (unknown, not a guess). The 1-D planner, which needs only phi(L)
    and z(L), runs it to apex and releases at z0 + r with sdot = sqrt(2 a L) (stage 1
    lit at release this time, so the push is split at the ignition kink)."""
    r = 2.0 * L_TRACK / math.pi
    arc = Arc(start_altitude_m=-r)
    assist = ConstantAccelAssist(A_TRACK, 300.0, 5.0 * G_TEST)
    tr = TraceBuilder(two_stage_toy.stage_names)
    exit_ = fly_track(
        tr,
        assist,
        arc,  # type: ignore[arg-type]
        IgnitionSpec(1.0),
        vehicle=two_stage_toy,
        settings=IntegratorSettings(rtol=1e-10),
        g_eff_mps2=G_TEST,
        p_amb_pa=0.0,
    )
    v_cf = math.sqrt(2.0 * A_TRACK * L_TRACK)
    assert exit_ is not None and exit_.x_exit_m is None
    assert exit_.phi_rad == 0.5 * math.pi
    assert abs(exit_.z_exit_m) <= 1e-12 * r
    assert math.isclose(exit_.sdot_mps, v_cf, rel_tol=1e-10)
    assert math.isclose(exit_.t_release_s, math.sqrt(2.0 * L_TRACK / A_TRACK), rel_tol=1e-10)

    planner = VerticalPlanner(
        two_stage_toy,
        {s.name: IgnitionSpec() for s in two_stage_toy.stages},
        ConstantGravity(G_TEST),
        G_TEST,
        "apex",
        IntegratorSettings(rtol=1e-10),
    )
    trace = planner.run_track(assist, arc)  # type: ignore[arg-type]
    assert trace.status == "nominal"
    release = trace.first_event("release")
    assert release is not None
    assert math.isclose(release.t_s, math.sqrt(2.0 * L_TRACK / A_TRACK), rel_tol=1e-10)
    assert math.isclose(release.v_mps, v_cf, rel_tol=1e-10)
    assert abs(release.z_m) <= 1e-12 * r


def test_fly_track_refuses_a_foreign_view(two_stage_toy: Vehicle) -> None:
    with pytest.raises(ValueError, match="fly_track"):
        fly_track(
            TraceBuilder(two_stage_toy.stage_names, view=ToyView()),
            ConstantAccelAssist(A_TRACK, 300.0, 5.0 * G_TEST),
            StraightTrack(L_TRACK, VERTICAL, -L_TRACK),
            IgnitionSpec(1.0),
            vehicle=two_stage_toy,
            settings=IntegratorSettings(),
            g_eff_mps2=G_TEST,
            p_amb_pa=0.0,
        )


def test_pass_through_result_defaults() -> None:
    res = PhaseResult(
        PhaseSpec("HOLD", 0, 0.0, 1.0, rhs_vertical, None, (), atol_for(VERTICAL_STATE_NAMES)),
        np.array([0.0, 1.0]),
        np.zeros((len(VERTICAL_STATE_NAMES), 2)),
        None,
        "t_end",
        1.0,
        np.zeros(len(VERTICAL_STATE_NAMES)),
    )
    assert res.nfev == 0 and dict(res.y_events) == {}


# -------------------------------------------------------------------------- package


def test_every_phase1_name_is_still_importable() -> None:
    missing = [n for n in PHASE1_NAMES + PHASE1_IMPORTED_NAMES if not hasattr(phases, n)]
    assert not missing, missing
    assert phases.VERTICAL_LAYOUT is VERTICAL_LAYOUT and phases.R_EARTH_M == R_EARTH_M
    assert not set(PHASE1_IMPORTED_NAMES) & set(phases.__all__)
    assert set(PHASE1_NAMES) <= set(phases.__all__)
    assert len(set(phases.__all__)) == len(phases.__all__)
    for name in phases.__all__:
        owners = [
            m
            for m in ("engine", "trace", "prelude", "vertical")
            if getattr(importlib.import_module(f"launchsim.phases.{m}"), name, None)
            is getattr(phases, name)
        ]
        assert owners, name


@pytest.mark.parametrize("module", ["__init__", "engine", "trace", "prelude", "vertical"])
def test_public_package_functions_have_docstrings(module: str) -> None:
    path = PACKAGE_DIR / f"{module}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree), f"{module}: module docstring"
    missing = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and not node.name.startswith("_"):
            if ast.get_docstring(node) is None:
                missing.append(node.name)
            if isinstance(node, ast.ClassDef):
                missing += [
                    f"{node.name}.{m.name}"
                    for m in node.body
                    if isinstance(m, ast.FunctionDef)
                    and not m.name.startswith("_")
                    and ast.get_docstring(m) is None
                ]
    assert not missing, missing


def test_old_single_module_is_gone() -> None:
    assert not (PACKAGE_DIR.parent / "phases.py").exists()
    assert Path(phases.__file__).name == "__init__.py"
