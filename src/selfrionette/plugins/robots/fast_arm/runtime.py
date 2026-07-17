"""fast_arm production implementation of the Robot Runtime Plugin contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from selfrionette.plugins.robots.fast_arm.kinematics import (
    FAST_ARM_ENDPOINT_LINK_LENGTHS_M,
    FastArmEndpointForwardKinematicsSolver,
    FastArmEndpointInverseKinematicsSolver,
    FastArmMuJoCoModelForwardKinematicsSolver,
)
from selfrionette.motion import LocalEndpointMotionGenerator, TargetToJointMotionGenerator
from selfrionette.mujoco_backend.model_contract import validate_fast_arm_model_name_contract
from selfrionette.mujoco_backend.model_info import inspect_mujoco_model
from selfrionette.plugins.robots.fast_arm.feasibility import (
    FastArmJointLimitGuard,
    load_and_validate_fast_arm_joint_limit_config,
)
from selfrionette.plugins.robots.fast_arm.profile import FAST_ARM_ROBOT_PROFILE
from selfrionette.robot_profile import RobotProfile
from selfrionette.runtime.robot_plugin import state_transform_by_name, validate_profile_model_dimensions
from selfrionette.runtime.viewer_motion_policy import (
    DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING,
    DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD,
    DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M,
    DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD,
)
from selfrionette.schemas import MuJoCoState


@dataclass(frozen=True, slots=True)
class FastArmRuntimePlugin:
    profile: RobotProfile = FAST_ARM_ROBOT_PROFILE

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id

    def validate_model(self, model: object) -> None:
        if self.profile.canonical_joint_names != FAST_ARM_ROBOT_PROFILE.canonical_joint_names:
            raise ValueError("fast_arm profile joint order mismatch")
        if self.profile.qpos_dimension != 4 or self.profile.qvel_dimension != 4:
            raise ValueError("fast_arm profile requires qpos/qvel dimensions 4/4")
        validate_profile_model_dimensions(self.profile, model)
        info = inspect_mujoco_model(model)
        if info.joint_names != self.profile.canonical_joint_names:
            raise ValueError(
                "robot profile/model joint order mismatch for fast_arm: "
                f"expected {self.profile.canonical_joint_names}, got {info.joint_names}"
            )
        validate_fast_arm_model_name_contract(model)

    def build_inverse_kinematics(self) -> FastArmEndpointInverseKinematicsSolver:
        return FastArmEndpointInverseKinematicsSolver(link_lengths_m=FAST_ARM_ENDPOINT_LINK_LENGTHS_M)

    def build_forward_kinematics(self) -> FastArmEndpointForwardKinematicsSolver:
        return FastArmEndpointForwardKinematicsSolver(link_lengths_m=FAST_ARM_ENDPOINT_LINK_LENGTHS_M)

    def build_target_motion_generator(
        self,
        *,
        seed_joint_angles_rad: tuple[float, ...] | None,
        discontinuity_threshold_rad: float | None,
        discontinuity_threshold_label: str,
    ) -> TargetToJointMotionGenerator:
        return TargetToJointMotionGenerator(
            self.build_inverse_kinematics(),
            seed_joint_angles_rad=seed_joint_angles_rad,
            qpos_joint_count=self.profile.qpos_dimension,
            **(
                {}
                if discontinuity_threshold_rad is None
                else {
                    "discontinuity_threshold_rad": discontinuity_threshold_rad,
                    "discontinuity_threshold_label": discontinuity_threshold_label,
                }
            ),
        )

    def build_local_endpoint_motion_generator(self) -> LocalEndpointMotionGenerator:
        return LocalEndpointMotionGenerator(
            endpoint_kinematics=FastArmMuJoCoModelForwardKinematicsSolver(
                tip_site_name=self.profile.endpoint.site_name or ""
            ),
            endpoint_model="mujoco_model_aligned_tip_site",
            fd_epsilon_rad=DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD,
            damping=DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING,
            max_qpos_delta_norm_rad=DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD,
            max_endpoint_delta_per_tick_m=DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M,
        )

    def build_qpos_feasibility_guard(
        self,
        *,
        model: object,
        config_path: str | Path | None,
    ) -> FastArmJointLimitGuard:
        resolved_path = self.profile.joint_limit_config_asset if config_path is None else Path(config_path)
        if resolved_path is None:
            raise ValueError("fast_arm profile requires a joint-limit configuration asset")
        return FastArmJointLimitGuard(
            load_and_validate_fast_arm_joint_limit_config(resolved_path, model=model)
        )

    def endpoint_position_from_state(self, state: MuJoCoState) -> tuple[float, float, float] | None:
        site_name = self.profile.endpoint.site_name
        if site_name is None:
            return None
        transform = state_transform_by_name(state.sites, site_name)
        return None if transform is None else tuple(getattr(transform, "position_m"))

    def endpoint_orientation_from_state(
        self, state: MuJoCoState
    ) -> tuple[float, float, float, float] | None:
        site_name = self.profile.endpoint.site_name
        if site_name is None:
            return None
        transform = state_transform_by_name(state.sites, site_name)
        return None if transform is None else tuple(getattr(transform, "quaternion_wxyz"))


FAST_ARM_RUNTIME_PLUGIN = FastArmRuntimePlugin()


__all__ = ["FAST_ARM_RUNTIME_PLUGIN", "FastArmRuntimePlugin"]
