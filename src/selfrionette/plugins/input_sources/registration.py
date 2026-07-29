"""Typed axis-local Input Source Plugin registration contract."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from selfrionette.runtime.execution.input_source_adapters import (
    RuntimeInputSourceExecutionAdapter,
)
from selfrionette.runtime.experiment.input_source import (
    InputSourcePlugin,
    InputSourceRuntimeDependencies,
)
from selfrionette.schemas import RawInputFrame


@dataclass(frozen=True, slots=True)
class InputSourcePluginRequest:
    parameters: Mapping[str, object]
    frames: tuple[RawInputFrame, ...]
    loop: bool
    initial_metadata: Mapping[str, object]
    runtime_dependencies: InputSourceRuntimeDependencies | None = None


RequestBuilder = Callable[..., InputSourcePluginRequest]


@dataclass(frozen=True, slots=True)
class InputSourcePluginRegistration:
    plugin: InputSourcePlugin
    cli_aliases: tuple[str, ...]
    request_builder: RequestBuilder
    execution_adapter: RuntimeInputSourceExecutionAdapter

    def __post_init__(self) -> None:
        if not self.cli_aliases:
            raise ValueError("input source registration requires at least one CLI alias")
        if len(set(self.cli_aliases)) != len(self.cli_aliases):
            raise ValueError("input source registration aliases must be unique")
        if not isinstance(self.execution_adapter, RuntimeInputSourceExecutionAdapter):
            raise TypeError(
                "input source registration requires a typed execution adapter"
            )


__all__ = [
    "InputSourcePluginRegistration",
    "InputSourcePluginRequest",
    "RequestBuilder",
]
