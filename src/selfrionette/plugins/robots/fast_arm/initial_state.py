"""Canonical fast_arm initial-state declaration."""

from __future__ import annotations

from selfrionette.runtime.experiment_contracts import VersionedIdentity
from selfrionette.runtime.robot_bundle import InitialStateContract

FAST_ARM_INITIAL_STATE_QPOS_RAD = (
    0.0,
    -0.5235987755982989,
    0.0,
    -1.0471975511965976,
)
FAST_ARM_INITIAL_STATE_TIP_POSITION_M = (0.240000, -0.245951, 0.284308)
FAST_ARM_INITIAL_STATE_TOOL_ORIENTATION_WXYZ = (
    0.8365163037378079,
    0.1294095225512604,
    0.4829629131445341,
    0.22414386804201347,
)
FAST_ARM_INITIAL_STATE_CONTRACT = InitialStateContract(
    identity=VersionedIdentity("fast_arm_initial_state", 1),
    source_kind="named_keyframe",
    source_id="home",
    qpos_rad=FAST_ARM_INITIAL_STATE_QPOS_RAD,
    tip_position_m=FAST_ARM_INITIAL_STATE_TIP_POSITION_M,
    tool_orientation_wxyz=FAST_ARM_INITIAL_STATE_TOOL_ORIENTATION_WXYZ,
    frame="MuJoCo world / scene frame",
    position_unit="meter",
    orientation_unit="unit_quaternion",
    quaternion_order="wxyz",
)


__all__ = [
    "FAST_ARM_INITIAL_STATE_CONTRACT",
    "FAST_ARM_INITIAL_STATE_QPOS_RAD",
    "FAST_ARM_INITIAL_STATE_TIP_POSITION_M",
    "FAST_ARM_INITIAL_STATE_TOOL_ORIENTATION_WXYZ",
]
