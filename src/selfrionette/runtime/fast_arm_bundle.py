"""Compatibility facade for the concrete fast_arm Robot Bundle."""

from selfrionette.plugins.robots.fast_arm.bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.plugins.robots.fast_arm.initial_state import (
    FAST_ARM_INITIAL_STATE_CONTRACT,
    FAST_ARM_INITIAL_STATE_QPOS_RAD,
    FAST_ARM_INITIAL_STATE_TIP_POSITION_M,
    FAST_ARM_INITIAL_STATE_TOOL_ORIENTATION_WXYZ,
)

__all__ = [
    "FAST_ARM_INITIAL_STATE_CONTRACT",
    "FAST_ARM_INITIAL_STATE_QPOS_RAD",
    "FAST_ARM_INITIAL_STATE_TIP_POSITION_M",
    "FAST_ARM_INITIAL_STATE_TOOL_ORIENTATION_WXYZ",
    "FAST_ARM_ROBOT_BUNDLE",
]
