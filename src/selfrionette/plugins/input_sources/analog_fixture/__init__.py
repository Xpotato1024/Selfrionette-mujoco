"""Analog fixture acquisition; mapping is selected from plugins.mappings."""

from collections.abc import Mapping

from selfrionette.plugins.input_sources._common import AnalogFixtureInputSource


def build_reader(parameters: Mapping[str, object]) -> AnalogFixtureInputSource:
    samples = parameters.get("samples")
    if not isinstance(samples, tuple):
        raise ValueError("analog_fixture plugin requires tuple samples")
    return AnalogFixtureInputSource(samples)


__all__ = ["build_reader"]
