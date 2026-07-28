"""Deterministic production Control Mapping Plugin catalog."""

from __future__ import annotations

from selfrionette.plugins.mappings.discovery import (
    discover_production_control_mapping_plugins,
)
from selfrionette.runtime.experiment.contracts import ControlMappingPlugin, PluginSelection


CONTROL_MAPPING_REGISTRY = discover_production_control_mapping_plugins()
CONTROL_MAPPING_PLUGINS: tuple[ControlMappingPlugin, ...] = (
    CONTROL_MAPPING_REGISTRY.entries
)


def resolve_control_mapping_plugin(selection: PluginSelection) -> ControlMappingPlugin:
    return CONTROL_MAPPING_REGISTRY.resolve(selection)


__all__ = [
    "CONTROL_MAPPING_PLUGINS",
    "CONTROL_MAPPING_REGISTRY",
    "resolve_control_mapping_plugin",
]
