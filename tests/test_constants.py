"""The documented constant values and the site quantities derived from them."""

from __future__ import annotations

import math

from launchsim.constants import (
    EXIT_ALTITUDE_LIMIT_M,
    G0_MPS2,
    MU_EARTH_M3S2,
    OMEGA_EARTH_RADS,
    R_EARTH_M,
    SP8007_KNOCKDOWN_A,
    SP8007_PHI_DIVISOR,
    T_IGN_LIMIT_S,
)


def test_literals_are_the_documented_values() -> None:
    assert MU_EARTH_M3S2 == 3.986004418e14
    assert R_EARTH_M == 6_378_137.0
    assert OMEGA_EARTH_RADS == 7.2921150e-5
    assert G0_MPS2 == 9.80665
    # the KI-030 bounds (SP7 step S4, D-SP7-28), which config.py applies
    assert T_IGN_LIMIT_S == 3600.0
    assert EXIT_ALTITUDE_LIMIT_M == 500.0


def test_surface_gravity_and_equatorial_rotation_speed() -> None:
    # mu / R_E^2 by hand: 3.986004418e14 / 4.0680631590769e13
    assert math.isclose(MU_EARTH_M3S2 / R_EARTH_M**2, 9.7982855, rel_tol=1e-7)
    # omega_E * R_E: the inertial speed of an equatorial pad (CLAUDE.md release test)
    assert math.isclose(OMEGA_EARTH_RADS * R_EARTH_M, 465.101, rel_tol=1e-5)


def test_sp8007_knockdown_constants() -> None:
    """NASA SP-8007 (1968) Eq. 5 / NASA/SP-8007-2020 Eq. 9-10: 0.901 and 1/16 (SP7 S1)."""
    assert SP8007_KNOCKDOWN_A == 0.901
    assert SP8007_PHI_DIVISOR == 16.0
