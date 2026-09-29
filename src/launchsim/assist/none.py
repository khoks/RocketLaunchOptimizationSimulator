"""The pad: no ground assist and no track phase (``assist.base.AssistModel``)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from launchsim.assist.base import AssistForces, TrackGeometry


@dataclass(frozen=True)
class NoAssist:
    """A pad launch. name is the registry key ``none``; there are no extra states, no
    impingement (f_imp = 0), a unit efficiency, a zero push time and a zero facility
    length; ``state_rate`` is never called because the planner issues no track phase
    for this model (calling it raises)."""

    name: str = "none"
    extra_state_names: tuple[str, ...] = ()
    f_imp: float = 0.0
    efficiency: float = 1.0
    carriage_mass_kg: float = 0.0
    allow_negative_drive: bool = False

    def initial_extra(self) -> np.ndarray:
        """No extra states."""
        return np.zeros(0)

    def state_rate(
        self,
        t: float,
        s_m: float,
        sdot_mps: float,
        extra: np.ndarray,
        m_vehicle_kg: float,
        m_carriage_kg: float,
        thrust_axial_N: float,
        g_eff_mps2: float,
        track: TrackGeometry,
    ) -> AssistForces:
        """A pad has no track phase: raises RuntimeError."""
        raise RuntimeError("NoAssist has no track phase; the planner must not integrate one")

    def push_time_estimate(self, track: TrackGeometry) -> float:
        """No push: 0 s."""
        return 0.0

    def braking_distance_m(self, v_mps: float) -> float:
        """No carriage: 0 m."""
        return 0.0

    def facility_length_m(self, track: TrackGeometry, v_exit_mps: float) -> float:
        """No facility: 0 m."""
        return 0.0

    def assumptions(self) -> tuple[str, ...]:
        """No assumptions of its own."""
        return ()
