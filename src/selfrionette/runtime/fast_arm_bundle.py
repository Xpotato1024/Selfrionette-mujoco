"""Production fast_arm Robot Bundle that delegates to existing behavior."""

from __future__ import annotations

from selfrionette.robots.fast_arm import FAST_ARM_ROBOT_PROFILE
from selfrionette.runtime.default_robot_providers import (
    NamedKeyframeInitialStateProvider,
    ProfileEndpointSceneRoleProvider,
    RuntimeEndpointCommandProvider,
    RuntimeEndpointPoseProvider,
    RuntimeQposFeasibilityProvider,
)
from selfrionette.runtime.experiment_contracts import VersionedIdentity
from selfrionette.runtime.fast_arm_plugin import FAST_ARM_RUNTIME_PLUGIN
from selfrionette.runtime.robot_bundle import (
    ENDPOINT_COMMAND_V1,
    ENDPOINT_POSE_V1,
    QPOS_FEASIBILITY_V1,
    RESET_INITIAL_STATE_V1,
    SCENE_ROLE_BINDING_V1,
    CapabilityProviderBinding,
    RobotBundle,
)


FAST_ARM_ROBOT_BUNDLE = RobotBundle(
    identity=VersionedIdentity("fast_arm", 1),
    profile=FAST_ARM_ROBOT_PROFILE,
    runtime_plugin=FAST_ARM_RUNTIME_PLUGIN,
    capability_providers=(
        CapabilityProviderBinding(
            RESET_INITIAL_STATE_V1,
            NamedKeyframeInitialStateProvider(FAST_ARM_ROBOT_PROFILE),
        ),
        CapabilityProviderBinding(
            ENDPOINT_POSE_V1,
            RuntimeEndpointPoseProvider(FAST_ARM_RUNTIME_PLUGIN),
        ),
        CapabilityProviderBinding(
            ENDPOINT_COMMAND_V1,
            RuntimeEndpointCommandProvider(FAST_ARM_RUNTIME_PLUGIN),
        ),
        CapabilityProviderBinding(
            QPOS_FEASIBILITY_V1,
            RuntimeQposFeasibilityProvider(FAST_ARM_RUNTIME_PLUGIN),
        ),
        CapabilityProviderBinding(
            SCENE_ROLE_BINDING_V1,
            ProfileEndpointSceneRoleProvider(FAST_ARM_ROBOT_PROFILE),
        ),
    ),
)


__all__ = ["FAST_ARM_ROBOT_BUNDLE"]
