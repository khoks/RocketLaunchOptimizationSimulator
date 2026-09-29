"""Swappable ground-assist models and the registry that builds them from configuration.

``build_assist`` is the only place a validated ``config.AssistConfig`` becomes an
``AssistModel`` and its ``TrackGeometry``; the units are already SI on the config's
properties. The models themselves (``none``, ``constant_accel``) are pure.
"""

from __future__ import annotations

import math

from launchsim.assist.base import AssistForces, AssistModel, TrackGeometry, normal_load_N
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.none import NoAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import AssistConfig, ConstantAccelConfig, NoAssistConfig

ASSIST_MODELS: dict[str, type] = {"none": NoAssist, "constant_accel": ConstantAccelAssist}
"""Registry key -> model class (the keys of ``config.AssistConfig``'s discriminator)."""


def build_assist(
    config: AssistConfig, g_eff_mps2: float
) -> tuple[AssistModel, TrackGeometry | None]:
    """The assist model and its track for a validated assist config.

    Inputs: the config (``NoAssistConfig`` or ``ConstantAccelConfig``; the planned
    Phase 3 models are rejected at validation); g_eff_mps2, the track's effective
    gravity [m/s^2], quoted in the model's assumptions. Output: (model, track), the
    track None for the pad. The track starts at exit_altitude - L sin phi so that its
    exit sits at the configured altitude in the datum frame (a buried silo starts at
    -L).
    """
    if isinstance(config, NoAssistConfig):
        return NoAssist(), None
    if isinstance(config, ConstantAccelConfig):
        phi = config.track.phi_rad
        track = StraightTrack(
            length_m=config.stroke_m,
            phi_rad=phi,
            start_altitude_m=config.track.exit_altitude_m - config.stroke_m * math.sin(phi),
        )
        model = ConstantAccelAssist(
            net_accel_mps2=config.net_accel_mps2,
            carriage_mass_kg=config.carriage_mass_kg,
            brake_decel_mps2=config.brake_decel_mps2,
            efficiency=config.drive_efficiency,
            f_imp=config.exhaust_impingement_fraction,
            allow_negative_drive=config.allow_negative_drive_force,
            g_eff_mps2=g_eff_mps2,
        )
        return model, track
    raise ValueError(f"no assist model for config {type(config).__name__}")


__all__ = [
    "ASSIST_MODELS",
    "VERTICAL",
    "AssistForces",
    "AssistModel",
    "ConstantAccelAssist",
    "NoAssist",
    "StraightTrack",
    "TrackGeometry",
    "build_assist",
    "normal_load_N",
]
