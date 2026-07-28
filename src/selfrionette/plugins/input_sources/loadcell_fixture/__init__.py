"""Recorded loadcell fixture using the canonical serial parser."""

from collections.abc import Mapping

from selfrionette.plugins.input_sources._loadcell import SerialInputSource
from selfrionette.plugins.input_sources._common import ManagedFrameHealthReader
from selfrionette.runtime.experiment.input_source import InputSourceHealth, InputSourceHealthStatus, InputSourceRuntimeDependencies


def build_reader(parameters: Mapping[str, object], *, runtime_dependencies: InputSourceRuntimeDependencies | None = None) -> ManagedFrameHealthReader:
    lines = runtime_dependencies.line_source if runtime_dependencies is not None and runtime_dependencies.line_source is not None else parameters.get("lines")
    if not isinstance(lines, tuple):
        raise ValueError("loadcell_fixture plugin requires tuple lines")
    return ManagedFrameHealthReader(
        SerialInputSource.from_lines(lines),
        InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0),
    )

__all__ = ["build_reader"]
