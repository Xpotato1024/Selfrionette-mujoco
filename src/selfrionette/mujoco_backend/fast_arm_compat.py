"""Explicit legacy convenience composition for the default fast_arm simulator."""

from __future__ import annotations

from typing import Any

from selfrionette.robots.fast_arm import FAST_ARM_ROBOT_PROFILE


def build_default_fast_arm_simulator(simulator_type: Any) -> Any:
    return simulator_type.from_model_path(
        FAST_ARM_ROBOT_PROFILE.mujoco_model_asset,
        initial_keyframe_name=FAST_ARM_ROBOT_PROFILE.initial_keyframe_name,
    )


__all__ = ["build_default_fast_arm_simulator"]
