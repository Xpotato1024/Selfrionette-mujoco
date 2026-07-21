"""First-party input-source registrations and source-local request builders."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from selfrionette.plugins.input_sources import analog_fixture, loadcell_fixture, loadcell_serial, noop, programmed_target, replay, viewer
from selfrionette.plugins.mappings.viewer import VIEWER_CONTROL_MAPPING_PLUGIN
from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M
from selfrionette.runtime.execution.input_source_adapters import (
    ANALOG_FIXTURE_EXECUTION_ADAPTER,
    LOADCELL_EXECUTION_ADAPTER,
    REPLAY_COMPATIBILITY_EXECUTION_ADAPTER,
    TARGET_METADATA_EXECUTION_ADAPTER,
    VIEWER_LOCAL_ENDPOINT_EXECUTION_ADAPTER,
    RuntimeInputSourceExecutionAdapter,
)
from selfrionette.runtime.experiment.contracts import ParameterContract, ParameterField, VersionedIdentity
from selfrionette.runtime.experiment.contracts import ControlMappingPlugin
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourcePlugin,
    InputSourceMode,
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
    control_mapping: ControlMappingPlugin | None = None
    control_mapping_parameters: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.cli_aliases:
            raise ValueError("input source registration requires at least one CLI alias")
        if len(set(self.cli_aliases)) != len(self.cli_aliases):
            raise ValueError("input source registration aliases must be unique")
        if self.control_mapping is not None and not isinstance(self.control_mapping, ControlMappingPlugin):
            raise TypeError("input source registration control_mapping must be a ControlMappingPlugin")


_TARGET_POSITION = (0.6, 0.0, 0.1)
_VIEWER_SAFE_ENDPOINT = DEFAULT_VIEWER_SAFE_ENDPOINT_M


def _programmed_request(*, steps: int, frames: Sequence[RawInputFrame] | None, preset: str | None, replay_initial_metadata: Mapping[str, object] | None = None, **_: object) -> InputSourcePluginRequest:
    if type(steps) is not int or steps < 1:
        raise ValueError("steps must be a positive integer")
    if preset not in (None, "sweep_x"):
        raise ValueError("unsupported programmed_target preset")
    if frames is not None:
        raise ValueError("programmed_target input source does not accept custom frames")
    parameters = {"steps": steps, "initial_position_m": _TARGET_POSITION, "preset": "sweep_x", "loop": False}
    selected = programmed_target.build_frames(parameters)
    return InputSourcePluginRequest(
        parameters=parameters,
        frames=selected,
        loop=False,
        initial_metadata={"source_kind": "programmed_target", "trajectory_name": "sweep_x"},
    )


def _replay_request(*, steps: int, frames: Sequence[RawInputFrame] | None, preset: str | None, replay_initial_metadata: Mapping[str, object] | None = None, **_: object) -> InputSourcePluginRequest:
    if preset is not None:
        raise ValueError("preset is not supported for replay input source")
    metadata = {"preset": "r6-h-p5-default", "target_position_m": _TARGET_POSITION, "desired_endpoint_m": _TARGET_POSITION}
    if replay_initial_metadata is not None:
        metadata = dict(replay_initial_metadata)
    parameters: dict[str, object] = {"metadata": metadata, "loop": True}
    runtime_dependencies = None
    if frames is not None:
        runtime_dependencies = InputSourceRuntimeDependencies(replay_frames=tuple(frames))
    selected = tuple(frames) if frames is not None else replay.build_frames(parameters)
    return InputSourcePluginRequest(parameters=parameters, frames=selected, loop=True, initial_metadata=metadata, runtime_dependencies=runtime_dependencies)


def _noop_request(*, steps: int, frames: Sequence[RawInputFrame] | None, preset: str | None, **_: object) -> InputSourcePluginRequest:
    if preset is not None:
        raise ValueError("preset is not supported for noop input source")
    if frames is not None:
        raise ValueError("noop input source does not accept custom frames")
    metadata = {"preset": "noop", "source_kind": "noop", "target_position_m": _TARGET_POSITION, "desired_endpoint_m": _TARGET_POSITION}
    parameters = {"metadata": metadata}
    return InputSourcePluginRequest(parameters=parameters, frames=noop.build_frames(parameters), loop=True, initial_metadata=metadata)


def _viewer_request(*, steps: int, frames: Sequence[RawInputFrame] | None, preset: str | None, **_: object) -> InputSourcePluginRequest:
    if preset is not None:
        raise ValueError("preset is not supported for viewer input source")
    if frames is not None:
        raise ValueError("viewer input source does not accept custom frames")
    metadata = {"preset": "viewer", "source_kind": "viewer", "target_position_m": _VIEWER_SAFE_ENDPOINT, "desired_endpoint_m": _VIEWER_SAFE_ENDPOINT, "source_active": False, "command_age_ms": 0, "stale_reason": "no_control_message_received"}
    parameters = {"metadata": metadata, "initial_endpoint_m": _VIEWER_SAFE_ENDPOINT}
    return InputSourcePluginRequest(parameters=parameters, frames=viewer.build_frames(parameters), loop=True, initial_metadata=metadata)


def _loadcell_request(*, steps: int, frames: Sequence[RawInputFrame] | None, preset: str | None, line_source: Sequence[str] | None = None, **_: object) -> InputSourcePluginRequest:
    if preset is not None:
        raise ValueError("preset is not supported for loadcell input source")
    if line_source is None:
        raise ValueError("loadcell input source requires injected fixture lines")
    parameters = {"lines": tuple(line_source)}
    return InputSourcePluginRequest(parameters=parameters, frames=(), loop=False, initial_metadata={"source_kind": "loadcell_serial"})


def _analog_request(*, steps: int, frames: Sequence[RawInputFrame] | None, preset: str | None, samples: Sequence[Mapping[str, object]] | None = None, **_: object) -> InputSourcePluginRequest:
    if preset is not None:
        raise ValueError("preset is not supported for analog_fixture input source")
    if samples is None:
        raise ValueError("analog_fixture input source requires fixture samples")
    parameters = {"samples": tuple(dict(sample) for sample in samples)}
    return InputSourcePluginRequest(parameters=parameters, frames=(), loop=False, initial_metadata={"source_kind": "analog_fixture"})


def _active_health() -> InputSourceHealth:
    return InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0)


def _stale_health() -> InputSourceHealth:
    return InputSourceHealth(InputSourceHealthStatus.STALE, reason="no_control_message_received", age_ms=0)


def _disconnected_health() -> InputSourceHealth:
    return InputSourceHealth(InputSourceHealthStatus.DISCONNECTED, reason="not_started", age_ms=0)


def _plugin(name: str, schema: str, mode: InputSourceMode, factory, contract: ParameterContract, health: InputSourceHealth, metadata: Mapping[str, object]) -> InputSourcePlugin:
    return InputSourcePlugin(
        identity=VersionedIdentity(name, 1),
        produced_sample_schema=VersionedIdentity(schema, 1),
        mode=mode,
        factory=factory,
        parameter_contract=contract,
        initial_health=health,
        initial_metadata=metadata,
    )


PROGRAMMED_TARGET_PLUGIN = _plugin(
    "programmed_target", "programmed_target_sample", InputSourceMode.OFFLINE,
    programmed_target.build_reader,
    ParameterContract((ParameterField("steps", int), ParameterField("initial_position_m", tuple), ParameterField("preset", str, required=False), ParameterField("loop", bool, required=False))),
    _active_health(), {"source_kind": "programmed_target", "trajectory_name": "sweep_x"},
)
REPLAY_PLUGIN = _plugin(
    "replay", "replay_raw_input_frame", InputSourceMode.REPLAY,
    replay.build_reader,
    ParameterContract((ParameterField("metadata", dict), ParameterField("loop", bool))),
    _active_health(), {"preset": "r6-h-p5-default"},
)
NOOP_PLUGIN = _plugin(
    "noop", "noop_sample", InputSourceMode.OFFLINE, noop.build_reader,
    ParameterContract((ParameterField("metadata", dict),)), _active_health(), {"preset": "noop", "source_kind": "noop"},
)
VIEWER_PLUGIN = _plugin(
    "viewer", "viewer_control_sample", InputSourceMode.VIEWER_BRIDGE, viewer.build_reader,
    ParameterContract((ParameterField("metadata", dict), ParameterField("initial_endpoint_m", tuple))), _stale_health(), {"preset": "viewer", "source_kind": "viewer", "source_active": False, "command_age_ms": 0, "stale_reason": "no_control_message_received"},
)
LOADCELL_SERIAL_PLUGIN = _plugin(
    "loadcell_serial", "loadcell_vector_sample", InputSourceMode.LIVE, loadcell_serial.build_reader,
    ParameterContract((ParameterField("port", str, required=False), ParameterField("baud_rate", int, required=False), ParameterField("lines", tuple, required=False))), _disconnected_health(), {"source_kind": "loadcell_serial", "baud_rate": 115200},
)
LOADCELL_FIXTURE_PLUGIN = _plugin(
    "loadcell_fixture", "loadcell_vector_sample", InputSourceMode.REPLAY, loadcell_fixture.build_reader,
    ParameterContract((ParameterField("lines", tuple),)), _active_health(), {"source_kind": "loadcell_serial", "fixture": True},
)
ANALOG_FIXTURE_PLUGIN = _plugin(
    "analog_fixture", "analog_fixture_sample", InputSourceMode.REPLAY, analog_fixture.build_reader,
    ParameterContract((ParameterField("samples", tuple),)), _active_health(), {"source_kind": "analog_fixture", "fixture": True},
)


INPUT_SOURCE_REGISTRATIONS = (
    InputSourcePluginRegistration(PROGRAMMED_TARGET_PLUGIN, ("programmed_target",), True, _programmed_request, TARGET_METADATA_EXECUTION_ADAPTER),
    InputSourcePluginRegistration(REPLAY_PLUGIN, ("replay",), True, _replay_request, REPLAY_COMPATIBILITY_EXECUTION_ADAPTER),
    InputSourcePluginRegistration(NOOP_PLUGIN, ("noop",), True, _noop_request, REPLAY_COMPATIBILITY_EXECUTION_ADAPTER),
    InputSourcePluginRegistration(
        VIEWER_PLUGIN,
        ("viewer",),
        True,
        _viewer_request,
        VIEWER_LOCAL_ENDPOINT_EXECUTION_ADAPTER,
        VIEWER_CONTROL_MAPPING_PLUGIN,
    ),
    InputSourcePluginRegistration(LOADCELL_SERIAL_PLUGIN, ("loadcell_serial",), False, _loadcell_request, LOADCELL_EXECUTION_ADAPTER),
    InputSourcePluginRegistration(LOADCELL_FIXTURE_PLUGIN, ("loadcell_fixture",), False, _loadcell_request, LOADCELL_EXECUTION_ADAPTER),
    InputSourcePluginRegistration(ANALOG_FIXTURE_PLUGIN, ("analog_fixture",), False, _analog_request, ANALOG_FIXTURE_EXECUTION_ADAPTER),
)


__all__ = ["INPUT_SOURCE_REGISTRATIONS", "InputSourcePluginRegistration", "InputSourcePluginRequest"]
