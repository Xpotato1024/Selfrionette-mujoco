"""Fixed discovery entry point for the first-party fast_arm Robot Plugin."""

from selfrionette.plugins.robots.registration import (
    ROBOT_ONBOARDING_CONTRACT_VERSION,
    RobotPluginRegistration,
    RobotResourceDeclaration,
)
from selfrionette.plugins.robots.fast_arm.adapter.bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.plugins.robots.fast_arm.adapter.resources import (
    FAST_ARM_JOINT_LIMIT_RESOURCE,
    FAST_ARM_MODEL_BUNDLE,
    FAST_ARM_MODEL_VFS_RESOURCES,
    FAST_ARM_SCENE_RESOURCE,
    FAST_ARM_VIEWER_DECLARATION_RESOURCE,
    FAST_ARM_VIEWER_FIXTURE_RESOURCE,
)
from selfrionette.plugins.robots.fast_arm.adapter.viewer import FAST_ARM_VIEWER_DECLARATION


ROBOT_PLUGIN = RobotPluginRegistration(
    identity=FAST_ARM_ROBOT_BUNDLE.identity,
    onboarding_contract_version=ROBOT_ONBOARDING_CONTRACT_VERSION,
    bundle=FAST_ARM_ROBOT_BUNDLE,
    viewer=FAST_ARM_VIEWER_DECLARATION,
    resources=RobotResourceDeclaration(
        model=FAST_ARM_MODEL_BUNDLE,
        configurations=(FAST_ARM_JOINT_LIMIT_RESOURCE,),
        viewer_declaration=FAST_ARM_VIEWER_DECLARATION_RESOURCE,
        viewer_fixture=FAST_ARM_VIEWER_FIXTURE_RESOURCE,
        viewer_vfs_resources=FAST_ARM_MODEL_VFS_RESOURCES,
    ),
)


__all__ = ["ROBOT_PLUGIN"]
