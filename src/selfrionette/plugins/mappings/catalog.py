"""Deterministic production Control Mapping Plugin catalog."""

from __future__ import annotations

from selfrionette.plugins.mappings.analog_fixture import ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN
from selfrionette.plugins.mappings.loadcell import LOADCELL_ENDPOINT_MAPPING_PLUGIN
from selfrionette.plugins.mappings.replay import REPLAY_CONTROL_MAPPING_PLUGIN
from selfrionette.plugins.mappings.viewer import VIEWER_CONTROL_MAPPING_PLUGIN
from selfrionette.runtime.experiment.contracts import ControlMappingPlugin, PluginSelection
from selfrionette.runtime.experiment.registry import VersionedPluginRegistry


CONTROL_MAPPING_PLUGINS: tuple[ControlMappingPlugin, ...] = (
    ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN,
    LOADCELL_ENDPOINT_MAPPING_PLUGIN,
    REPLAY_CONTROL_MAPPING_PLUGIN,
    VIEWER_CONTROL_MAPPING_PLUGIN,
)
CONTROL_MAPPING_REGISTRY = VersionedPluginRegistry(
    CONTROL_MAPPING_PLUGINS,
    kind="control mapping plugin",
)


def resolve_control_mapping_plugin(selection: PluginSelection) -> ControlMappingPlugin:
    return CONTROL_MAPPING_REGISTRY.resolve(selection)


__all__ = [
    "CONTROL_MAPPING_PLUGINS",
    "CONTROL_MAPPING_REGISTRY",
    "resolve_control_mapping_plugin",
]
