"""Control-mapping plugin namespace."""

from selfrionette.plugins.mappings.analog_fixture import ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN
from selfrionette.plugins.mappings.loadcell import LOADCELL_ENDPOINT_MAPPING_PLUGIN
from selfrionette.plugins.mappings.replay import REPLAY_CONTROL_MAPPING_PLUGIN
from selfrionette.plugins.mappings.viewer import (
    VIEWER_CONTROL_MAPPING_PLUGIN,
    ViewerKeyboardGamepadMappingStrategy,
)

__all__ = [
    "ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN",
    "LOADCELL_ENDPOINT_MAPPING_PLUGIN",
    "REPLAY_CONTROL_MAPPING_PLUGIN",
    "VIEWER_CONTROL_MAPPING_PLUGIN",
    "ViewerKeyboardGamepadMappingStrategy",
]
