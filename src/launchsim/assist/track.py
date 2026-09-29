"""Track geometries (``assist.base.TrackGeometry`` implementations).

Phase 1 has the straight track only; a vertical silo is a straight track at phi = pi/2.
Curved arcs (the cable-pulled ramp) are Phase 3. SI and radians; the track frame of
``assist/base.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

VERTICAL = 0.5 * math.pi
"""Track angle [rad] of a vertical silo."""


@dataclass(frozen=True)
class StraightTrack:
    """A straight track of length length_m [m] at the constant angle phi_rad [rad] above
    horizontal, starting at altitude start_altitude_m [m] in the +z-up datum frame.

    Geometry: phi(s) = phi_rad, kappa(s) = 0, z(s) = s sin phi (height above the track
    start), exit altitude = start_altitude_m + L sin phi. A buried vertical silo whose
    mouth is the pad datum starts at -L.
    """

    length_m: float
    phi_rad: float = VERTICAL
    start_altitude_m: float = 0.0

    def __post_init__(self) -> None:
        if self.length_m <= 0.0:
            raise ValueError("length_m must be > 0")
        if not 0.0 <= self.phi_rad <= VERTICAL:
            raise ValueError("phi_rad must lie in [0, pi/2] (horizontal to vertical)")

    def phi(self, s_m: float) -> float:
        """Track angle above horizontal [rad] at s_m [m]: constant."""
        return self.phi_rad

    def kappa(self, s_m: float) -> float:
        """Curvature [1/m] at s_m [m]: zero on a straight track."""
        return 0.0

    def z(self, s_m: float) -> float:
        """Height [m] above the track start at arc length s_m [m]: s sin phi."""
        return s_m * math.sin(self.phi_rad)

    @property
    def exit_altitude_m(self) -> float:
        """Altitude [m] of the track exit (s = L) in the datum frame."""
        return self.start_altitude_m + self.z(self.length_m)
