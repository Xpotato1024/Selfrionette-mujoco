"""Explicit registry of supported production runtime plugins."""

from __future__ import annotations

from selfrionette.robot_registry import ImmutableRegistry
from selfrionette.runtime.fast_arm_plugin import FAST_ARM_RUNTIME_PLUGIN
from selfrionette.runtime.robot_plugin import RobotRuntimePlugin

ROBOT_RUNTIME_PLUGIN_REGISTRY: ImmutableRegistry[RobotRuntimePlugin] = ImmutableRegistry(
    (FAST_ARM_RUNTIME_PLUGIN,), kind="robot runtime plugin"
)


def resolve_robot_runtime_plugin(profile_id: str) -> RobotRuntimePlugin:
    return ROBOT_RUNTIME_PLUGIN_REGISTRY.resolve(profile_id)


def registered_robot_runtime_plugin_ids() -> tuple[str, ...]:
    return ROBOT_RUNTIME_PLUGIN_REGISTRY.ids


__all__ = ["registered_robot_runtime_plugin_ids", "resolve_robot_runtime_plugin"]
