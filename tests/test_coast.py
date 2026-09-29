"""Unpowered vertical coast to apex and fall back to the start altitude.

Constant g (analytic device):  apex = z0 + v0^2/(2g) at t = v0/g; back at z0 at
t = 2 v0/g with |v| = v0.

Inverse-square gravity mu/r^2 (the run model): the motion is a degenerate (radial)
Kepler orbit with specific energy E = v^2/2 - mu/r conserved. Starting at r = R_E
(z0 = 0) with speed v0 upward, the apex radius is where v = 0:

    1/r_a = 1/R_E - v0^2/(2 mu)

A radial orbit is the e -> 1 limit of an ellipse with semi-major axis a = r_a/2 and
r = a (1 - cos E), t = sqrt(a^3/mu) (E - sin E) measured from the centre (E = 0).
At r = R_E, cos E0 = 1 - R_E/a; at the apex E = pi, so

    t_up = sqrt(a^3/mu) [pi - (E0 - sin E0)]

and by time symmetry the vehicle is back at R_E after 2 t_up with |v| = v0.
Cases: v0 = 76.707 m/s (the README silo exit speed) and 2000 m/s.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from launchsim.constants import G0_MPS2, MU_EARTH_M3S2, R_EARTH_M
from launchsim.dynamics import (
    VERTICAL_LAYOUT,
    VERTICAL_STATE_NAMES,
    ConstantGravity,
    Gravity,
    InverseSquareGravity,
    VerticalParams,
    rhs_vertical,
)
from launchsim.phases import (
    IntegratorSettings,
    PhaseResult,
    PhaseSpec,
    atol_for,
    ev_apex,
    ev_impact,
    integrate_phase,
)

G = G0_MPS2
M_KG = 1234.5
V0_CASES = [76.707, 2000.0]


def _coast_and_fall(
    gravity: Gravity, g_ref: float, z0: float, v0: float, settings: IntegratorSettings
) -> tuple[PhaseResult, PhaseResult]:
    """COAST (sigma +1, ends at apex) then FALL (sigma -1, ends at impact on z0).

    The FALL lists only the impact, the planner pattern (docs/physics.md, "Event
    rules": never list the event that ended the previous phase), so this validation
    does not lean on the disarm backstop; that backstop is exercised in test_events.
    """
    atol = atol_for(VERTICAL_STATE_NAMES)
    up = PhaseSpec(
        kind="COAST",
        stage_index=0,
        t0=0.0,
        t_end=None,
        rhs=rhs_vertical,
        params=VerticalParams(gravity=gravity, g_ref_mps2=g_ref, schedule=None, v_sign=1),
        events=(ev_apex(), ev_impact(z0)),
        atol=atol,
        sigma=1,
    )
    res_up = integrate_phase(up, VERTICAL_LAYOUT.build(z_m=z0, v_mps=v0, m_kg=M_KG), settings)
    down = PhaseSpec(
        kind="FALL",
        stage_index=0,
        t0=res_up.t_end,
        t_end=None,
        rhs=rhs_vertical,
        params=VerticalParams(gravity=gravity, g_ref_mps2=g_ref, schedule=None, v_sign=-1),
        events=(ev_impact(z0),),
        atol=atol,
        sigma=-1,
    )
    res_down = integrate_phase(down, res_up.y_end, settings)
    assert res_up.notes == () and res_down.notes == ()
    return res_up, res_down


@pytest.mark.parametrize("v0", V0_CASES)
def test_constant_g_apex_and_return(v0: float, tight_settings: IntegratorSettings) -> None:
    z0 = 50.0
    t_apex = v0 / G
    z_apex = z0 + v0 * v0 / (2.0 * G)

    res_up, res_down = _coast_and_fall(ConstantGravity(G), G, z0, v0, tight_settings)

    assert res_up.ended_by == "apex"
    assert [name for name, _ in res_up.event_times] == ["apex"]
    assert math.isclose(res_up.t_end, t_apex, rel_tol=1e-9)
    assert math.isclose(float(VERTICAL_LAYOUT.get(res_up.y_end, "z_m")), z_apex, rel_tol=1e-9)
    assert abs(float(VERTICAL_LAYOUT.get(res_up.y_end, "v_mps"))) < 1e-9
    assert math.isclose(float(VERTICAL_LAYOUT.get(res_up.y_end, "J_grav_mps")), v0, rel_tol=1e-9)

    assert res_down.ended_by == "impact"
    assert [name for name, _ in res_down.event_times] == ["impact"]
    assert math.isclose(res_down.t_end, 2.0 * t_apex, rel_tol=1e-9)
    assert math.isclose(float(VERTICAL_LAYOUT.get(res_down.y_end, "v_mps")), -v0, rel_tol=1e-9)
    assert abs(float(VERTICAL_LAYOUT.get(res_down.y_end, "z_m")) - z0) < 1e-6
    # Falling with sigma = -1 the gravity quadrature runs backwards: speed is regained.
    j_grav_total = float(VERTICAL_LAYOUT.get(res_down.y_end, "J_grav_mps"))
    assert abs(j_grav_total) < 1e-7


@pytest.mark.parametrize("v0", V0_CASES)
def test_inverse_square_apex_time_and_energy(v0: float, tight_settings: IntegratorSettings) -> None:
    mu = MU_EARTH_M3S2
    r_a = 1.0 / (1.0 / R_EARTH_M - v0 * v0 / (2.0 * mu))
    a = 0.5 * r_a
    e0 = math.acos(1.0 - R_EARTH_M / a)
    t_up = math.sqrt(a**3 / mu) * (math.pi - (e0 - math.sin(e0)))
    energy0 = 0.5 * v0 * v0 - mu / R_EARTH_M
    g_ref = mu / R_EARTH_M**2

    res_up, res_down = _coast_and_fall(InverseSquareGravity(mu), g_ref, 0.0, v0, tight_settings)

    assert res_up.ended_by == "apex"
    assert res_down.ended_by == "impact"
    assert abs(float(VERTICAL_LAYOUT.get(res_up.y_end, "z_m")) - (r_a - R_EARTH_M)) < 1e-5
    assert math.isclose(res_up.t_end, t_up, rel_tol=1e-9)
    assert math.isclose(res_down.t_end, 2.0 * t_up, rel_tol=1e-9)
    assert math.isclose(abs(float(VERTICAL_LAYOUT.get(res_down.y_end, "v_mps"))), v0, rel_tol=1e-9)

    for res in (res_up, res_down):
        z = np.asarray(VERTICAL_LAYOUT.get(res.y, "z_m"))
        v = np.asarray(VERTICAL_LAYOUT.get(res.y, "v_mps"))
        energy = 0.5 * v * v - mu / (R_EARTH_M + z)
        assert np.all(np.abs(energy - energy0) <= 1e-10 * abs(energy0))

    # J_grav = integral of g sigma dt; the altitude part is negative above the datum.
    j_alt_up = float(VERTICAL_LAYOUT.get(res_up.y_end, "J_alt_mps"))
    assert j_alt_up < 0.0
    assert math.isclose(float(VERTICAL_LAYOUT.get(res_up.y_end, "J_grav_mps")), v0, rel_tol=1e-9)
