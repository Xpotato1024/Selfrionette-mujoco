"""Typed Input Source Plugin registration contract."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from selfrionette.runtime.execution.input_source_adapters import (
    RuntimeInputSourceExecutionAdapter,
)
from selfrionette.runtime.experiment.contracts import PluginSelection
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
    generic_cli_exposed: bool
    request_builder: RequestBuilder
    execution_adapter: RuntimeInputSourceExecutionAdapter
    default_control_mapping_selection: PluginSelection | None = None
    control_mapping_parameters: Mapping[str, object] = field(default_factory=dict)
    catalog_order: int = 0
    generic_cli_order: int | None = None

    def __post_init__(self) -> None:
        if not self.cli_aliases:
            raise ValueError("input source registration requires at least one CLI alias")
        if len(set(self.cli_aliases)) != len(self.cli_aliases):
            raise ValueError("input source registration aliases must be unique")
        if not isinstance(self.execution_adapter, RuntimeInputSourceExecutionAdapter):
            raise TypeError(
                "input source registration requires a typed execution adapter"
            )
        if self.default_control_mapping_selection is not None and not isinstance(
            self.default_control_mapping_selection, PluginSelection
        ):
            raise TypeError(
                "input source registration default mapping must use PluginSelection"
            )
        if self.generic_cli_exposed:
            if type(self.generic_cli_order) is not int or self.generic_cli_order < 0:
                raise ValueError(
                    "generic CLI input source requires a non-negative explicit order"
                )
        elif self.generic_cli_order is not None:
            raise ValueError(
                "non-generic input source must not declare a generic CLI order"
            )
        if type(self.catalog_order) is not int or self.catalog_order < 0:
            raise ValueError(
                "input source registration requires a non-negative catalog order"
            )


__all__ = [
    "InputSourcePluginRegistration",
    "InputSourcePluginRequest",
    "RequestBuilder",
]
