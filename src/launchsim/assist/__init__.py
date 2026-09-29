"""Swappable ground-assist models and the registry that builds them from configuration.

``ASSIST_MODELS`` maps a ``config.AssistConfig`` discriminator value (``model:`` in the
YAML) to the model class that builds itself from that config through its
``from_config(config, g_eff_mps2) -> (model, track | None)`` classmethod;
``build_assist`` is the only place a validated config becomes an ``AssistModel`` and
its ``TrackGeometry``, and it dispatches through the registry alone, so a Phase 3
model becomes buildable by registering its class here (and its config in
``config.AssistConfig``). The units are already SI on the config's properties. The
models themselves (``none``, ``constant_accel``) are pure.
"""

from __future__ import annotations

from launchsim.assist.base import (
    AssistBuilder,
    AssistForces,
    AssistModel,
    TrackGeometry,
    normal_load_N,
)
from launchsim.assist.constant_accel import ConstantAccelAssist
from launchsim.assist.none import NoAssist
from launchsim.assist.track import VERTICAL, StraightTrack
from launchsim.config import AssistConfig

ASSIST_MODELS: dict[str, type[AssistBuilder]] = {
    NoAssist.name: NoAssist,
    ConstantAccelAssist.name: ConstantAccelAssist,
}
"""Registry key (the ``model`` discriminator of ``config.AssistConfig``, equal to the
class's ``name``) -> model class satisfying ``assist.base.AssistBuilder`` (a
``from_config`` classmethod)."""


def build_assist(
    config: AssistConfig, g_eff_mps2: float
) -> tuple[AssistModel, TrackGeometry | None]:
    """The assist model and its track for a validated assist config.

    Inputs: the config (``NoAssistConfig`` or ``ConstantAccelConfig``; the planned
    Phase 3 models are rejected at validation); g_eff_mps2, the track's effective
    gravity [m/s^2], quoted in the model's assumptions. Output: (model, track), the
    track None for the pad, from ``ASSIST_MODELS[config.model].from_config``. A
    registered class without ``from_config`` raises TypeError.
    """
    model_cls = ASSIST_MODELS.get(config.model)
    if model_cls is None:
        raise ValueError(f"no assist model registered for {config.model!r}")
    if not callable(getattr(model_cls, "from_config", None)):
        raise TypeError(f"{model_cls.__name__} is registered without a from_config classmethod")
    return model_cls.from_config(config, g_eff_mps2)


__all__ = [
    "ASSIST_MODELS",
    "VERTICAL",
    "AssistBuilder",
    "AssistForces",
    "AssistModel",
    "ConstantAccelAssist",
    "NoAssist",
    "StraightTrack",
    "TrackGeometry",
    "build_assist",
    "normal_load_N",
]
