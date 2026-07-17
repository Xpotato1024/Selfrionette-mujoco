from __future__ import annotations

from pathlib import Path

import selfrionette.plugins.robots.fast_arm.feasibility as new_feasibility
import selfrionette.runtime.default_robot_providers as old_providers
import selfrionette.runtime.fast_arm_bundle as old_bundle_module
import selfrionette.runtime.fast_arm_joint_limits as old_feasibility
import selfrionette.runtime.fast_arm_plugin as old_runtime_module
from selfrionette.plugins.catalog import (
    registered_robot_plugin_ids,
    registered_robot_bundle_ids,
    registered_robot_profile_ids,
    registered_robot_runtime_plugin_ids,
    resolve_robot_bundle,
    resolve_robot_plugin_registration,
    resolve_robot_profile,
    resolve_robot_runtime,
    resolve_robot_runtime_plugin,
)
from selfrionette.plugins.robots.fast_arm.bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.plugins.robots.fast_arm.initial_state import (
    FAST_ARM_INITIAL_STATE_CONTRACT,
)
from selfrionette.plugins.robots.fast_arm.profile import FAST_ARM_ROBOT_PROFILE
from selfrionette.plugins.robots.fast_arm.runtime import (
    FAST_ARM_RUNTIME_PLUGIN,
    FastArmRuntimePlugin,
)
from selfrionette.plugins.robots.fast_arm.plugin import ROBOT_PLUGIN
from selfrionette.plugins.robots.fast_arm.viewer import FAST_ARM_VIEWER_DECLARATION
from selfrionette.robot_registry import (
    registered_robot_profile_ids as old_registered_robot_profile_ids,
)
from selfrionette.robot_profile import robot_profile_runtime_metadata
from selfrionette.robot_registry import resolve_robot_profile as old_resolve_robot_profile
from selfrionette.robots.fast_arm import (
    FAST_ARM_ROBOT_PROFILE as OLD_FAST_ARM_ROBOT_PROFILE,
)
from selfrionette.runtime import resolve_robot_bundle as root_resolve_robot_bundle
from selfrionette.runtime import resolve_robot_runtime as root_resolve_robot_runtime
from selfrionette.runtime.robot_bundle_registry import (
    resolve_robot_bundle as old_resolve_robot_bundle,
)
from selfrionette.runtime.robot_plugin_registry import (
    resolve_robot_runtime as old_resolve_robot_runtime,
)
from selfrionette.runtime.robot_plugin_registry import (
    resolve_robot_runtime_plugin as old_resolve_robot_runtime_plugin,
)
from selfrionette.runtime.robot_provider_adapters import (
    NamedKeyframeInitialStateProvider,
    ProfileEndpointSceneRoleProvider,
    RuntimeEndpointCommandProvider,
    RuntimeEndpointPoseProvider,
    RuntimeQposFeasibilityProvider,
)


def test_catalog_resolvers_project_one_canonical_bundle() -> None:
    bundle = resolve_robot_bundle("fast_arm")
    resolved = resolve_robot_runtime("fast_arm")

    assert bundle is FAST_ARM_ROBOT_BUNDLE
    assert resolve_robot_profile("fast_arm") is bundle.profile
    assert resolve_robot_runtime_plugin("fast_arm") is bundle.runtime_plugin
    assert resolved.profile is bundle.profile
    assert resolved.plugin is bundle.runtime_plugin
    assert bundle.profile is FAST_ARM_ROBOT_PROFILE
    assert bundle.runtime_plugin is FAST_ARM_RUNTIME_PLUGIN
    assert resolve_robot_plugin_registration("fast_arm") is ROBOT_PLUGIN
    assert ROBOT_PLUGIN.bundle is bundle
    assert ROBOT_PLUGIN.viewer is FAST_ARM_VIEWER_DECLARATION
    assert bundle.profile.viewer_declaration is FAST_ARM_VIEWER_DECLARATION
    assert registered_robot_plugin_ids() == ("fast_arm",)
    assert registered_robot_bundle_ids() == ("fast_arm",)
    assert registered_robot_profile_ids() == registered_robot_bundle_ids()
    assert registered_robot_runtime_plugin_ids() == registered_robot_bundle_ids()


def test_profile_keeps_repository_asset_and_configuration_references() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    assert FAST_ARM_ROBOT_PROFILE.mujoco_model_asset == (
        repository_root / "assets" / "mujoco" / "fast_arm" / "scene.xml"
    )
    assert FAST_ARM_ROBOT_PROFILE.joint_limit_config_asset == (
        repository_root / "configs" / "fast_arm" / "joint_limits.toml"
    )
    assert ROBOT_PLUGIN.resources.model.repository_path == (
        "assets/mujoco/fast_arm/scene.xml"
    )
    assert FAST_ARM_VIEWER_DECLARATION.model_resource_path == (
        ROBOT_PLUGIN.resources.model.repository_path
    )
    assert tuple(
        item.repository_path for item in ROBOT_PLUGIN.resources.viewer_vfs_resources
    ) == tuple(item.resource_path for item in FAST_ARM_VIEWER_DECLARATION.vfs_assets)


def test_runtime_metadata_delivers_the_registered_viewer_declaration() -> None:
    metadata = robot_profile_runtime_metadata(FAST_ARM_ROBOT_PROFILE)

    assert metadata["viewer_robot_declaration"] == (
        FAST_ARM_VIEWER_DECLARATION.to_document()
    )


def test_old_and_new_public_paths_share_identical_objects() -> None:
    assert OLD_FAST_ARM_ROBOT_PROFILE is FAST_ARM_ROBOT_PROFILE
    assert old_runtime_module.FastArmRuntimePlugin is FastArmRuntimePlugin
    assert old_runtime_module.FAST_ARM_RUNTIME_PLUGIN is FAST_ARM_RUNTIME_PLUGIN
    assert old_bundle_module.FAST_ARM_ROBOT_BUNDLE is FAST_ARM_ROBOT_BUNDLE
    assert (
        old_bundle_module.FAST_ARM_INITIAL_STATE_CONTRACT
        is FAST_ARM_INITIAL_STATE_CONTRACT
    )
    assert old_feasibility.FastArmJointLimitGuard is new_feasibility.FastArmJointLimitGuard
    assert (
        old_feasibility.load_and_validate_fast_arm_joint_limit_config
        is new_feasibility.load_and_validate_fast_arm_joint_limit_config
    )
    assert (
        old_providers.NamedKeyframeInitialStateProvider
        is NamedKeyframeInitialStateProvider
    )
    assert (
        old_providers.ProfileEndpointSceneRoleProvider
        is ProfileEndpointSceneRoleProvider
    )
    assert old_providers.RuntimeEndpointCommandProvider is RuntimeEndpointCommandProvider
    assert old_providers.RuntimeEndpointPoseProvider is RuntimeEndpointPoseProvider
    assert old_providers.RuntimeQposFeasibilityProvider is RuntimeQposFeasibilityProvider


def test_compatibility_and_runtime_root_resolvers_share_catalog_objects() -> None:
    bundle = resolve_robot_bundle("fast_arm")

    assert old_resolve_robot_profile("fast_arm") is bundle.profile
    assert old_registered_robot_profile_ids() == registered_robot_bundle_ids()
    assert old_resolve_robot_bundle("fast_arm") is bundle
    assert root_resolve_robot_bundle("fast_arm") is bundle
    assert old_resolve_robot_runtime_plugin("fast_arm") is bundle.runtime_plugin
    assert old_resolve_robot_runtime("fast_arm") == resolve_robot_runtime("fast_arm")
    assert root_resolve_robot_runtime("fast_arm") == resolve_robot_runtime("fast_arm")
