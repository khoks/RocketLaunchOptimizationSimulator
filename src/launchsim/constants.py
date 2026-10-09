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

# Recorded SP1 values the SP7 structural model places on (results of the model, not physical
# constants: kept here because structure.py is pure and the project allows numbers only here
# and in configs; each with the record it is copied from, written unrounded). The headline
# offload is SP1_PENALTY_OFFLOAD_KG[0]. The rows equal tests/data/silo_offload_2d_record.json
# (D-SP7-30; copied once from the run's untracked metrics.json) exactly, a fast test; the
# values only tests use (P_ref, the README-loads fork's) are read from that record by
# tests/structure_support.py.

SP1_PENALTY_DRY_MASS_KG: tuple[float, ...] = (0.0, 2_000.0, 4_000.0, 8_100.0)
"""The stage-1 dry mass SP1 added for its penalty rows [kg] (silo_cold_s1 and
silo_cold_s1_dry+2t, +4t, +8.1t): results/silo_offload_2d/20261003T112934Z/metrics.json
(git b3150c1754ee, clean), offload.cases, stage1_dry_mass_added_kg; pinned by
tests/data/silo_offload_2d_record.json."""

SP1_PENALTY_OFFLOAD_KG: tuple[float, ...] = (
    41_262.90803733282,
    32_285.203295407457,
    22_875.96053288855,
    1_980.4767886165673,
)
"""SP1's solved stage-1 offload x* [kg] at each SP1_PENALTY_DRY_MASS_KG: the same record,
offload.cases, offload_kg (the coupled placement's curve, survey 08 section 8). Concave:
its segment slopes steepen, -4.489, -4.705 and -5.096 kg/kg."""

OFFLOAD_PER_KG_STAGE1_DRY: float = 4.381
"""SP1's stage-1 offload lost per kg of added stage-1 dry mass at the headline [kg/kg]
(SP7 survey 03, docs/phases/inputs/2026-10-08-SP7-survey/03-offload-pipeline.md, measured
at x = 41,262.9 kg)."""

OFFLOAD_PER_KG_STAGE2_DRY: float = 24.0
"""The stage-1 offload lost per kg of stage-2 dry mass [kg/kg], "about 24" (SP7 design
docs/phases/inputs/2026-10-08-SP7-design.md section 4.2.4, citing RQ1/RQ3): with
OFFLOAD_PER_KG_STAGE1_DRY it converts a stage-2 increment into an equivalent stage-1 one for
the coupled placement only (an estimate)."""
