"""Fixed discovery entry point for the first-party fast_arm Robot Plugin."""

from selfrionette.plugins.robot_registration import (
    ROBOT_ONBOARDING_CONTRACT_VERSION,
    RepositoryResource,
    RobotPluginRegistration,
    RobotResourceDeclaration,
)
from selfrionette.plugins.robots.fast_arm.bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.plugins.robots.fast_arm.viewer import FAST_ARM_VIEWER_DECLARATION


ROBOT_PLUGIN = RobotPluginRegistration(
    identity=FAST_ARM_ROBOT_BUNDLE.identity,
    onboarding_contract_version=ROBOT_ONBOARDING_CONTRACT_VERSION,
    bundle=FAST_ARM_ROBOT_BUNDLE,
    viewer=FAST_ARM_VIEWER_DECLARATION,
    resources=RobotResourceDeclaration(
        model=RepositoryResource("assets/mujoco/fast_arm/scene.xml"),
        configurations=(
            RepositoryResource("configs/fast_arm/joint_limits.toml"),
        ),
        viewer_vfs_resources=tuple(
            RepositoryResource(item.resource_path)
            for item in FAST_ARM_VIEWER_DECLARATION.vfs_assets
        ),
    ),
)


__all__ = ["ROBOT_PLUGIN"]
