"""Public compatibility re-exports for analog source and mapping symbols."""

from selfrionette.plugins.input_sources.analog_fixture.source import (
    AnalogFixtureSample,
    parse_analog_fixture_sample,
)
from selfrionette.plugins.mappings.analog_fixture import (
    AnalogFixtureMappingConfig,
    map_analog_fixture_sample,
)

__all__ = [
    "AnalogFixtureMappingConfig",
    "AnalogFixtureSample",
    "map_analog_fixture_sample",
    "parse_analog_fixture_sample",
]
