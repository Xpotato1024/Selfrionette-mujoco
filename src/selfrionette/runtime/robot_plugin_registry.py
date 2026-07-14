"""Explicit registry of supported production runtime plugins."""

from __future__ import annotations

from dataclasses import dataclass

from selfrionette.robot_profile import RobotProfile
from selfrionette.robot_registry import ImmutableRegistry, ROBOT_PROFILE_REGISTRY
from selfrionette.runtime.fast_arm_plugin import FAST_ARM_RUNTIME_PLUGIN
from selfrionette.runtime.robot_plugin import RobotRuntimePlugin

ROBOT_RUNTIME_PLUGIN_REGISTRY: ImmutableRegistry[RobotRuntimePlugin] = ImmutableRegistry(
    (FAST_ARM_RUNTIME_PLUGIN,), kind="robot runtime plugin"
)


@dataclass(frozen=True, slots=True)
class ResolvedRobotRuntime:
    profile: RobotProfile
    plugin: RobotRuntimePlugin


def validate_robot_profile_plugin_consistency(
    requested_profile_id: str,
    profile: RobotProfile,
    plugin: RobotRuntimePlugin,
) -> None:
    if profile.profile_id != requested_profile_id:
        raise ValueError(
            "robot profile registry identity mismatch: "
            f"requested {requested_profile_id!r}, got {profile.profile_id!r}"
        )
    if plugin.profile_id != requested_profile_id:
        raise ValueError(
            "robot runtime plugin registry identity mismatch: "
            f"requested {requested_profile_id!r}, got {plugin.profile_id!r}"
        )
    if plugin.profile.profile_id != requested_profile_id:
        raise ValueError(
            "robot runtime plugin profile identity mismatch: "
            f"requested {requested_profile_id!r}, got {plugin.profile.profile_id!r}"
        )
    if plugin.profile.profile_contract_version != profile.profile_contract_version:
        raise ValueError("robot profile/plugin profile contract version mismatch")
    if plugin.profile.model_contract_version != profile.model_contract_version:
        raise ValueError("robot profile/plugin model contract version mismatch")
    if plugin.profile != profile:
        raise ValueError("robot profile/plugin declarative contract mismatch")
    if plugin.profile is not profile:
        raise ValueError("robot runtime plugin does not reference the registered profile object")


def resolve_robot_runtime(
    profile_id: str,
    *,
    profile_registry: ImmutableRegistry[RobotProfile] = ROBOT_PROFILE_REGISTRY,
    plugin_registry: ImmutableRegistry[RobotRuntimePlugin] = ROBOT_RUNTIME_PLUGIN_REGISTRY,
) -> ResolvedRobotRuntime:
    if frozenset(profile_registry.ids) != frozenset(plugin_registry.ids):
        raise ValueError(
            "robot profile/runtime plugin registry ID mismatch: "
            f"profiles={profile_registry.ids}, plugins={plugin_registry.ids}"
        )
    profile = profile_registry.resolve(profile_id)
    plugin = plugin_registry.resolve(profile_id)
    validate_robot_profile_plugin_consistency(profile_id, profile, plugin)
    return ResolvedRobotRuntime(profile=profile, plugin=plugin)


def resolve_robot_runtime_plugin(profile_id: str) -> RobotRuntimePlugin:
    return ROBOT_RUNTIME_PLUGIN_REGISTRY.resolve(profile_id)


def registered_robot_runtime_plugin_ids() -> tuple[str, ...]:
    return ROBOT_RUNTIME_PLUGIN_REGISTRY.ids


__all__ = [
    "ResolvedRobotRuntime",
    "registered_robot_runtime_plugin_ids",
    "resolve_robot_runtime",
    "resolve_robot_runtime_plugin",
    "validate_robot_profile_plugin_consistency",
]
