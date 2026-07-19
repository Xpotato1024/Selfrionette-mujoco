"""Explicit deterministic noop Input Source Plugin."""

from collections.abc import Mapping

from selfrionette.plugins.input_sources._common import NoopInputSource
from selfrionette.runtime.experiment.input_source import InputSourceHealth, InputSourceHealthStatus
from selfrionette.schemas import RawInputFrame


def build_frames(parameters: Mapping[str, object]) -> tuple[RawInputFrame, ...]:
    return (RawInputFrame(source="noop", timestamp_s=0.0, metadata=dict(parameters["metadata"])),)


def build_reader(parameters: Mapping[str, object]) -> NoopInputSource:
    return NoopInputSource(build_frames(parameters))


__all__ = ["build_frames", "build_reader"]
