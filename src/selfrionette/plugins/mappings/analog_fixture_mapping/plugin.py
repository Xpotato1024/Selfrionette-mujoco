"""Fixed discovery entry point for analog_fixture_mapping/v1."""

from .implementation import ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN


CONTROL_MAPPING_PLUGIN = ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN

__all__ = ["CONTROL_MAPPING_PLUGIN"]
