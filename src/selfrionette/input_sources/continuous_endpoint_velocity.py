"""Compatibility facade for the canonical Control Mapping primitive."""

from selfrionette.plugins.mappings.continuous_endpoint_velocity import (
    build_continuous_endpoint_velocity_intent,
    build_normalized_analog_fixture_intent,
)

__all__ = [
    "build_continuous_endpoint_velocity_intent",
    "build_normalized_analog_fixture_intent",
]
