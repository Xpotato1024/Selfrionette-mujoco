"""Declarative fast_arm Robot Profile implementation."""

from __future__ import annotations

from pathlib import Path

from selfrionette.mujoco_backend.model_contract import (
    FAST_ARM_END_EFFECTOR_BODY_NAME,
    FAST_ARM_END_EFFECTOR_SITE_NAME,
)
from selfrionette.robot_profile import (
    CoordinateUnitContract,
    EndpointReference,
    RobotProfile,
)

FAST_ARM_PROFILE_ID = "fast_arm"
FAST_ARM_MODEL_CONTRACT_VERSION = "fast_arm-mujoco-model/v1"
FAST_ARM_JOINT_NAMES: tuple[str, ...] = (
    "sholder_joint_1",
    "sholder_joint_2",
    "sholder_joint_3",
    "elbow_joint",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]

FAST_ARM_ROBOT_PROFILE = RobotProfile(
    profile_id=FAST_ARM_PROFILE_ID,
    profile_contract_version=1,
    model_contract_version=FAST_ARM_MODEL_CONTRACT_VERSION,
    backend_kind="mujoco",
    mujoco_model_asset=(
        _REPOSITORY_ROOT / "assets" / "mujoco" / "fast_arm" / "scene.xml"
    ),
    canonical_joint_names=FAST_ARM_JOINT_NAMES,
    qpos_dimension=4,
    qvel_dimension=4,
    initial_keyframe_name="home",
    endpoint=EndpointReference(
        site_name=FAST_ARM_END_EFFECTOR_SITE_NAME,
        body_name=FAST_ARM_END_EFFECTOR_BODY_NAME,
    ),
    joint_limit_config_asset=(
        _REPOSITORY_ROOT / "configs" / "fast_arm" / "joint_limits.toml"
    ),
    coordinate_units=CoordinateUnitContract(
        position_unit="meter",
        angle_unit="rad",
        coordinate_frame="MuJoCo world / scene frame",
        quaternion_order="wxyz",
    ),
    viewer_profile_id=FAST_ARM_PROFILE_ID,
    supported_capabilities=frozenset(
        {
            "endpoint_ik",
            "physical_fk",
            "local_endpoint_motion",
            "qpos_feasibility_guard",
            "viewer_qpos_rendering",
        }
    ),
)


__all__ = [
    "FAST_ARM_JOINT_NAMES",
    "FAST_ARM_MODEL_CONTRACT_VERSION",
    "FAST_ARM_PROFILE_ID",
    "FAST_ARM_ROBOT_PROFILE",
]
