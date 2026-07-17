"""Single production catalog for concrete Robot Bundle registration."""

from __future__ import annotations

from selfrionette.plugins.robots.fast_arm.bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.robot_profile import RobotProfile
from selfrionette.runtime.experiment_contracts import PluginSelection
from selfrionette.runtime.experiment_registry import VersionedPluginRegistry
from selfrionette.runtime.robot_bundle import RobotBundle
from selfrionette.runtime.robot_plugin import RobotRuntimePlugin
from selfrionette.runtime.robot_resolution import (
    ProfileIdRegistry,
    ResolvedRobotRuntime,
    resolve_robot_runtime_from_registries,
    validate_robot_profile_plugin_consistency,
)


ROBOT_BUNDLE_REGISTRY: VersionedPluginRegistry[RobotBundle] = (
    VersionedPluginRegistry((FAST_ARM_ROBOT_BUNDLE,), kind="Robot Bundle")
)


def resolve_robot_bundle(
    bundle_id: str, *, contract_version: int = 1
) -> RobotBundle:
    return ROBOT_BUNDLE_REGISTRY.resolve(
        PluginSelection(bundle_id, contract_version)
    )


def registered_robot_bundle_ids() -> tuple[str, ...]:
    return ROBOT_BUNDLE_REGISTRY.ids


def _require_registered_profile_id(profile_id: str, *, kind: str) -> None:
    if profile_id not in ROBOT_BUNDLE_REGISTRY.ids:
        raise ValueError(
            f"unknown {kind} ID {profile_id!r}; "
            f"available: {ROBOT_BUNDLE_REGISTRY.ids}"
        )


class _RobotProfileProjectionRegistry:
    """Read-only projection over the single concrete Robot Bundle catalog."""

    @property
    def ids(self) -> tuple[str, ...]:
        return ROBOT_BUNDLE_REGISTRY.ids

    def resolve(self, profile_id: str) -> RobotProfile:
        return resolve_robot_profile(profile_id)


class _RobotRuntimePluginProjectionRegistry:
    """Read-only projection over the single concrete Robot Bundle catalog."""

    @property
    def ids(self) -> tuple[str, ...]:
        return ROBOT_BUNDLE_REGISTRY.ids

    def resolve(self, profile_id: str) -> RobotRuntimePlugin:
        return resolve_robot_runtime_plugin(profile_id)


ROBOT_PROFILE_REGISTRY: ProfileIdRegistry[RobotProfile] = (
    _RobotProfileProjectionRegistry()
)
ROBOT_RUNTIME_PLUGIN_REGISTRY: ProfileIdRegistry[RobotRuntimePlugin] = (
    _RobotRuntimePluginProjectionRegistry()
)


def resolve_robot_profile(profile_id: str) -> RobotProfile:
    _require_registered_profile_id(profile_id, kind="robot profile")
    return resolve_robot_bundle(profile_id).profile


def registered_robot_profile_ids() -> tuple[str, ...]:
    return ROBOT_BUNDLE_REGISTRY.ids


def resolve_robot_runtime_plugin(profile_id: str) -> RobotRuntimePlugin:
    _require_registered_profile_id(profile_id, kind="robot runtime plugin")
    return resolve_robot_bundle(profile_id).runtime_plugin


def registered_robot_runtime_plugin_ids() -> tuple[str, ...]:
    return ROBOT_BUNDLE_REGISTRY.ids


def resolve_robot_runtime(
    profile_id: str,
    *,
    profile_registry: ProfileIdRegistry[RobotProfile] | None = None,
    plugin_registry: ProfileIdRegistry[RobotRuntimePlugin] | None = None,
) -> ResolvedRobotRuntime:
    if profile_registry is None and plugin_registry is None:
        _require_registered_profile_id(profile_id, kind="robot profile")
        bundle = resolve_robot_bundle(profile_id)
        validate_robot_profile_plugin_consistency(
            profile_id, bundle.profile, bundle.runtime_plugin
        )
        return ResolvedRobotRuntime(
            profile=bundle.profile,
            plugin=bundle.runtime_plugin,
        )
    return resolve_robot_runtime_from_registries(
        profile_id,
        profile_registry=(
            ROBOT_PROFILE_REGISTRY
            if profile_registry is None
            else profile_registry
        ),
        plugin_registry=(
            ROBOT_RUNTIME_PLUGIN_REGISTRY
            if plugin_registry is None
            else plugin_registry
        ),
    )


__all__ = [
    "ROBOT_BUNDLE_REGISTRY",
    "ROBOT_PROFILE_REGISTRY",
    "ROBOT_RUNTIME_PLUGIN_REGISTRY",
    "registered_robot_bundle_ids",
    "registered_robot_profile_ids",
    "registered_robot_runtime_plugin_ids",
    "resolve_robot_bundle",
    "resolve_robot_profile",
    "resolve_robot_runtime",
    "resolve_robot_runtime_plugin",
]
