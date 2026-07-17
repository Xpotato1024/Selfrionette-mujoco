"""Temporary compatibility facade for the plugin-owned fast_arm solvers."""

from selfrionette.plugins.robots.fast_arm.kinematics import (
    FAST_ARM_ENDPOINT_BASE_POSITION_M,
    FAST_ARM_ENDPOINT_JOINT_COUNT,
    FAST_ARM_ENDPOINT_LINK_LENGTHS_M,
    FAST_ARM_MUJOCO_MODEL_JOINT_REFS_RAD,
    FAST_ARM_MUJOCO_MODEL_TIP_SITE_NAME,
    FastArmEndpointForwardKinematicsSolver,
    FastArmEndpointInverseKinematicsSolver,
    FastArmMuJoCoModelForwardKinematicsSolver,
)

__all__ = [
    "FAST_ARM_ENDPOINT_BASE_POSITION_M",
    "FAST_ARM_ENDPOINT_JOINT_COUNT",
    "FAST_ARM_ENDPOINT_LINK_LENGTHS_M",
    "FAST_ARM_MUJOCO_MODEL_JOINT_REFS_RAD",
    "FAST_ARM_MUJOCO_MODEL_TIP_SITE_NAME",
    "FastArmEndpointForwardKinematicsSolver",
    "FastArmEndpointInverseKinematicsSolver",
    "FastArmMuJoCoModelForwardKinematicsSolver",
]
