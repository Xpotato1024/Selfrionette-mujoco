"""Compatibility facade for production Robot Runtime Plugin resolution."""

from selfrionette.plugins.catalog import (
    ROBOT_RUNTIME_PLUGIN_REGISTRY,
    registered_robot_runtime_plugin_ids,
    resolve_robot_runtime,
    resolve_robot_runtime_plugin,
)
from selfrionette.runtime.robot_resolution import (
    ResolvedRobotRuntime,
    validate_robot_profile_plugin_consistency,
)

__all__ = [
    "ResolvedRobotRuntime",
    "registered_robot_runtime_plugin_ids",
    "resolve_robot_runtime",
    "resolve_robot_runtime_plugin",
    "validate_robot_profile_plugin_consistency",
]
