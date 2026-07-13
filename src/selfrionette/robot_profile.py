"""Immutable declarative robot model contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EndpointReference:
    site_name: str | None
    body_name: str | None

    def __post_init__(self) -> None:
        if self.site_name is None and self.body_name is None:
            raise ValueError("endpoint reference requires a site_name or body_name")


@dataclass(frozen=True, slots=True)
class CoordinateUnitContract:
    position_unit: str
    angle_unit: str
    coordinate_frame: str
    quaternion_order: str


@dataclass(frozen=True, slots=True)
class RobotProfile:
    """Versioned declarations only; executable factories belong to a runtime plugin."""

    profile_id: str
    profile_contract_version: int
    model_contract_version: str
    backend_kind: str
    mujoco_model_asset: Path
    canonical_joint_names: tuple[str, ...]
    qpos_dimension: int
    qvel_dimension: int
    initial_keyframe_name: str
    endpoint: EndpointReference
    joint_limit_config_asset: Path | None
    coordinate_units: CoordinateUnitContract
    viewer_profile_id: str
    supported_capabilities: frozenset[str]

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        if self.profile_contract_version < 1:
            raise ValueError("profile_contract_version must be positive")
        if not self.model_contract_version:
            raise ValueError("model_contract_version must not be empty")
        if not self.backend_kind:
            raise ValueError("backend_kind must not be empty")
        if len(self.canonical_joint_names) != len(set(self.canonical_joint_names)):
            raise ValueError("canonical_joint_names must be unique")
        if self.qpos_dimension < 1 or self.qvel_dimension < 1:
            raise ValueError("qpos_dimension and qvel_dimension must be positive")
        if len(self.canonical_joint_names) != self.qpos_dimension:
            raise ValueError("canonical_joint_names must match qpos_dimension")
        if not self.initial_keyframe_name:
            raise ValueError("initial_keyframe_name must not be empty")
        if not self.viewer_profile_id:
            raise ValueError("viewer_profile_id must not be empty")


def robot_profile_runtime_metadata(profile: RobotProfile) -> dict[str, object]:
    return {
        "robot_profile_id": profile.profile_id,
        "model_contract_version": profile.model_contract_version,
        "robot_joint_names": profile.canonical_joint_names,
        "robot_qpos_dimension": profile.qpos_dimension,
    }


__all__ = [
    "CoordinateUnitContract",
    "EndpointReference",
    "RobotProfile",
    "robot_profile_runtime_metadata",
]
