"""Production known-ID Robot Bundle registry."""

from __future__ import annotations

from selfrionette.runtime.experiment_contracts import PluginSelection
from selfrionette.runtime.experiment_registry import VersionedPluginRegistry
from selfrionette.runtime.fast_arm_bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.runtime.robot_bundle import RobotBundle


ROBOT_BUNDLE_REGISTRY: VersionedPluginRegistry[RobotBundle] = VersionedPluginRegistry(
    (FAST_ARM_ROBOT_BUNDLE,), kind="Robot Bundle"
)


def resolve_robot_bundle(
    bundle_id: str, *, contract_version: int = 1
) -> RobotBundle:
    return ROBOT_BUNDLE_REGISTRY.resolve(
        PluginSelection(bundle_id, contract_version)
    )


def registered_robot_bundle_ids() -> tuple[str, ...]:
    return ROBOT_BUNDLE_REGISTRY.ids


__all__ = [
    "ROBOT_BUNDLE_REGISTRY",
    "registered_robot_bundle_ids",
    "resolve_robot_bundle",
]
