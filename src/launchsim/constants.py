"""Earth and physical constants, and the published empirical coefficients the physics
modules use: the only place mu, R_E, omega_E and g0 are defined.

All values are SI. Earth parameters follow WGS84 / IERS; g0 and sea-level pressure
follow the ICAO standard atmosphere. The structural coefficients are empirical fits from
NASA SP-8007 (the knockdown of an unstiffened cylinder in axial compression, 1968 Eq. 5
and 2020 Eq. 9-10), each with its source in its docstring; structure.py uses them. A
published table whose rows are used whole (Gerard & Lakshmikantham's Table 2) lives with
its module instead.
"""

MU_EARTH_M3S2: float = 3.986004418e14
"""Earth gravitational parameter GM [m^3/s^2]."""

R_EARTH_M: float = 6_378_137.0
"""Earth equatorial radius [m]; the reference radius for altitude and the track g_eff."""

OMEGA_EARTH_RADS: float = 7.2921150e-5
"""Earth sidereal rotation rate [rad/s]."""

G0_MPS2: float = 9.80665
"""Standard gravity [m/s^2].

Converts Isp to exhaust velocity (c = g0 * Isp) and defines the unit "g" for ``_g``
inputs and load reports (see units.py). It is never a gravity model: ascent gravity is
mu/r^2 and the track phase uses the constant g_eff = mu/R_E^2 - omega_p^2 R_E.
"""

P_SEA_LEVEL_PA: float = 101_325.0
"""ICAO sea-level pressure [Pa]; used to derive nozzle exit area from vacuum and
sea-level thrust."""

R_AIR_JKGK: float = 287.05287
"""Specific gas constant of air [J/(kg K)], ICAO value; used by the atmosphere extension."""

J_PER_KWH: float = 3.6e6
"""Joules per kilowatt-hour."""

V_REL_EPS_MPS: float = 1e-9
"""Below this Earth-relative speed [m/s] the flight-path angle falls back to local vertical."""

ALT_AMBIANCE_MIN_M: float = -5_004.0
"""Lowest geometric altitude [m] the ambiance ICAO atmosphere accepts."""

ALT_AMBIANCE_MAX_M: float = 81_020.0
"""Highest geometric altitude [m] the ambiance ICAO atmosphere accepts; above it
atmosphere.py applies its documented isothermal extension."""

SP8007_KNOCKDOWN_A: float = 0.901
"""Coefficient [-] of the SP-8007 knockdown of an unstiffened isotropic cylinder in axial
compression, gamma = 1 - 0.901 (1 - exp(-phi)), phi = sqrt(r/t)/16: NASA SP-8007 (1968),
"Buckling of Thin-Walled Circular Cylinders", Eq. 5; NASA/SP-8007-2020/REV 2, Eq. 9-10
(stated there for r/t < 1500 as a lower bound to the test data). Used by structure.py."""

SP8007_PHI_DIVISOR: float = 16.0
"""Divisor [-] of sqrt(r/t) in the SP-8007 knockdown exponent phi = sqrt(r/t)/16 (the
1/16 of NASA SP-8007 (1968) Eq. 5 and NASA/SP-8007-2020/REV 2 Eq. 10)."""
