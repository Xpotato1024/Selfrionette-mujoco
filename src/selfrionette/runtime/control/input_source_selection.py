from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from selfrionette.plugins.input_sources.catalog import (
    INPUT_SOURCE_CATALOG,
    SUPPORTED_INPUT_SOURCE_NAMES,
)
from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M
from selfrionette.runtime.experiment.contracts import PluginSelection, VersionedIdentity
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceMode,
    InputSourcePlugin,
    InputSourceRuntimeDependencies,
    ValidatedInputSourceReader,
    ValidatedManagedInputSourceReader,
)
from selfrionette.runtime.execution.input_source_adapters import (
    RuntimeInputSourceExecutionAdapter,
)
from selfrionette.runtime.control.input_source_state import (
    annotate_raw_input_frame,
    build_runtime_input_source_state,
    build_runtime_input_source_state_from_health,
    runtime_input_source_state_to_metadata,
)
from selfrionette.schemas import RawInputFrame

DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M: tuple[float, float, float] = (0.6, 0.0, 0.1)

_DEFAULT_REPLAY_INITIAL_METADATA: dict[str, object] = {
    "preset": "r6-h-p5-default",
    "target_position_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
    "desired_endpoint_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
}

_DEFAULT_NOOP_INITIAL_METADATA: dict[str, object] = {
    "preset": "noop",
    "source_kind": "noop",
    "target_position_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
    "desired_endpoint_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
}

_DEFAULT_VIEWER_INITIAL_METADATA: dict[str, object] = {
    "preset": "viewer",
    "source_kind": "viewer",
    "target_position_m": DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    "desired_endpoint_m": DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    "source_active": False,
    "command_age_ms": 0,
    "stale_reason": "no_control_message_received",
}


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceSelection:
    source_name: str
    frames: tuple[RawInputFrame, ...]
    loop: bool
    initial_metadata: Mapping[str, object]
    plugin_selection: PluginSelection | None = None
    resolved_plugin: InputSourcePlugin | None = None
    produced_sample_schema: VersionedIdentity | None = None
    source_mode: InputSourceMode | None = None
    runtime_reader: ValidatedInputSourceReader | ValidatedManagedInputSourceReader | None = None
    initial_health: InputSourceHealth | None = None
    execution_adapter: RuntimeInputSourceExecutionAdapter | None = None
    validated_parameters: Mapping[str, object] | None = None

    @property
    def plugin(self) -> InputSourcePlugin | None:
        return self.resolved_plugin

    @property
    def produced_sample_schema_identity(self) -> VersionedIdentity | None:
        return self.produced_sample_schema

    @property
    def runtime_execution_adapter(self) -> RuntimeInputSourceExecutionAdapter | None:
        return self.execution_adapter

    @property
    def reader(self) -> ValidatedInputSourceReader | ValidatedManagedInputSourceReader | None:
        return self.runtime_reader


def select_runtime_input_source(
    source_name: str,
    *,
    steps: int,
    frames: Sequence[RawInputFrame] | None = None,
    preset: str | None = None,
    replay_initial_metadata: Mapping[str, object] | None = None,
) -> RuntimeInputSourceSelection:
    registration = INPUT_SOURCE_CATALOG.resolve(source_name)
    plugin_selection = PluginSelection(
        registration.plugin.identity.name,
        registration.plugin.identity.version,
    )
    plugin = INPUT_SOURCE_CATALOG.resolve_plugin(plugin_selection)
    request = registration.request_builder(
        steps=steps,
        frames=frames,
        preset=preset,
        replay_initial_metadata=replay_initial_metadata,
    )
    source_state = build_runtime_input_source_state_from_health(
        plugin.initial_health,
        source_kind=plugin.identity.name,
    )
    selected_frames = tuple(annotate_raw_input_frame(frame, source_state) for frame in request.frames)
    runtime_dependencies = request.runtime_dependencies
    if runtime_dependencies is not None and runtime_dependencies.replay_frames is not None:
        runtime_dependencies = replace(
            runtime_dependencies,
            replay_frames=selected_frames,
        )
    reader = plugin.create_runtime_reader(
        request.parameters,
        runtime_dependencies=runtime_dependencies,
    )
    initial_metadata = {
        **plugin.initial_metadata,
        **request.initial_metadata,
        **runtime_input_source_state_to_metadata(source_state),
    }

    return RuntimeInputSourceSelection(
        source_name=registration.cli_aliases[0],
        frames=selected_frames,
        loop=request.loop,
        initial_metadata=initial_metadata,
        plugin_selection=plugin_selection,
        resolved_plugin=plugin,
        produced_sample_schema=plugin.produced_sample_schema_identity,
        source_mode=plugin.source_mode,
        runtime_reader=reader,
        initial_health=plugin.initial_health,
        execution_adapter=registration.execution_adapter,
        validated_parameters=request.parameters,
    )


__all__ = [
    "RuntimeInputSourceSelection",
    "SUPPORTED_INPUT_SOURCE_NAMES",
    "select_runtime_input_source",
]
