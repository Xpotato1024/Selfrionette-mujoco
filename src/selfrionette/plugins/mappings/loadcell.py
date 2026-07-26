"""Canonical loadcell mapping from source-normalized intent to endpoint target."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol, cast, runtime_checkable

from selfrionette.runtime.experiment.contracts import (
    ControlMappingPlugin,
    ParameterContract,
    ParameterField,
    VersionedIdentity,
)
from selfrionette.schemas import InputIntent, MotionCommand


Vector3 = tuple[float, float, float]
LOADCELL_VECTOR_SAMPLE_SCHEMA = VersionedIdentity("loadcell_vector_sample", 1)
LOADCELL_NORMALIZED_SAMPLE_SCHEMA = VersionedIdentity(
    "loadcell_normalized_input_intent", 1
)
LOADCELL_ENDPOINT_MAPPING_IDENTITY = VersionedIdentity("loadcell_endpoint_mapping", 1)
LOADCELL_MAPPING_SEMANTICS_IDENTITY = VersionedIdentity(
    "loadcell_endpoint_delta", 1
)


@runtime_checkable
class NormalizedLoadcellInputIntentLike(Protocol):
    source: str
    timestamp_s: float
    values: tuple[float, ...]
    active_channels: tuple[int, ...]
    metadata: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class LoadcellEndpointMappingConfig:
    channel_axis_weights: tuple[
        Vector3,
        Vector3,
        Vector3,
        Vector3,
        Vector3,
        Vector3,
        Vector3,
    ] = (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )
    max_delta_m: float = 0.03
    gain_m: float = 0.01

    def __post_init__(self) -> None:
        if len(self.channel_axis_weights) != 7:
            raise ValueError("channel_axis_weights must contain exactly 7 channel weights")
        for channel_index, weight in enumerate(self.channel_axis_weights):
            _coerce_vector3(f"channel_axis_weights[{channel_index}]", weight)
        if not isfinite(self.gain_m):
            raise ValueError("gain_m must be finite")
        if self.gain_m < 0.0:
            raise ValueError("gain_m must be non-negative")
        if not isfinite(self.max_delta_m):
            raise ValueError("max_delta_m must be finite")
        if self.max_delta_m <= 0.0:
            raise ValueError("max_delta_m must be positive")


def _coerce_vector3(name: str, value: object) -> Vector3:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")
    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    for component_index, component in enumerate(components):
        if not isfinite(component):
            raise ValueError(f"{name} must contain only finite values at index {component_index}")
    return cast(Vector3, components)


def _coerce_normalized_values(
    values: tuple[float, ...],
) -> tuple[float, float, float, float, float, float, float]:
    if len(values) != 7:
        raise ValueError("loadcell vector must contain exactly 7 values")
    coerced_values = []
    for channel_index, raw_value in enumerate(values):
        if not isfinite(raw_value):
            raise ValueError(f"non-finite loadcell value at index {channel_index}")
        coerced_values.append(float(raw_value))
    return cast(tuple[float, float, float, float, float, float, float], tuple(coerced_values))


def _clamp_vector3_components(value: Vector3, *, limit: float) -> Vector3:
    return cast(Vector3, tuple(max(-limit, min(limit, component)) for component in value))


def _add_vector3(left: Vector3, right: Vector3) -> Vector3:
    return cast(Vector3, tuple(left[index] + right[index] for index in range(3)))


def _compute_endpoint_delta_m(
    values: tuple[float, float, float, float, float, float, float],
    config: LoadcellEndpointMappingConfig,
) -> Vector3:
    endpoint_delta_m = [0.0, 0.0, 0.0]
    for channel_value, channel_weights in zip(values, config.channel_axis_weights, strict=True):
        endpoint_delta_m[0] += channel_value * channel_weights[0]
        endpoint_delta_m[1] += channel_value * channel_weights[1]
        endpoint_delta_m[2] += channel_value * channel_weights[2]
    scaled_delta_m = cast(
        Vector3,
        tuple(component * config.gain_m for component in endpoint_delta_m),
    )
    return _clamp_vector3_components(scaled_delta_m, limit=config.max_delta_m)


def _build_loadcell_motion_metadata(
    *,
    intent: NormalizedLoadcellInputIntentLike,
    current_tip_position_m: Vector3,
    endpoint_delta_m: Vector3,
    desired_endpoint_m: Vector3,
) -> dict[str, object]:
    metadata = dict(intent.metadata)
    metadata["active_channels"] = intent.active_channels
    metadata["current_tip_position_m"] = current_tip_position_m
    metadata["endpoint_delta_m"] = endpoint_delta_m
    metadata["desired_endpoint_m"] = desired_endpoint_m
    return metadata


def build_r7_a_lite_smoke_endpoint_mapping_config(
    *,
    gain_m: float,
    max_delta_m: float,
) -> LoadcellEndpointMappingConfig:
    return LoadcellEndpointMappingConfig(
        channel_axis_weights=(
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
        gain_m=gain_m,
        max_delta_m=max_delta_m,
    )


def build_motion_command_from_normalized_loadcell_intent(
    intent: NormalizedLoadcellInputIntentLike,
    *,
    current_tip_position_m: Vector3,
    config: LoadcellEndpointMappingConfig | None = None,
) -> MotionCommand:
    endpoint_config = LoadcellEndpointMappingConfig() if config is None else config
    normalized_values = _coerce_normalized_values(intent.values)
    current_tip_position_m = _coerce_vector3("current_tip_position_m", current_tip_position_m)
    endpoint_delta_m = _compute_endpoint_delta_m(normalized_values, endpoint_config)
    desired_endpoint_m = _add_vector3(current_tip_position_m, endpoint_delta_m)
    return MotionCommand(
        timestamp_s=intent.timestamp_s,
        metadata=_build_loadcell_motion_metadata(
            intent=intent,
            current_tip_position_m=current_tip_position_m,
            endpoint_delta_m=endpoint_delta_m,
            desired_endpoint_m=desired_endpoint_m,
        ),
    )


class LoadcellEndpointMotionCommandConverter:
    """Convert normalized loadcell intent into a desired-endpoint MotionCommand."""

    def __init__(self, config: LoadcellEndpointMappingConfig | None = None) -> None:
        self._config = LoadcellEndpointMappingConfig() if config is None else config

    @property
    def config(self) -> LoadcellEndpointMappingConfig:
        return self._config

    def convert(
        self,
        intent: NormalizedLoadcellInputIntentLike,
        *,
        current_tip_position_m: Vector3,
    ) -> MotionCommand:
        return build_motion_command_from_normalized_loadcell_intent(
            intent,
            current_tip_position_m=current_tip_position_m,
            config=self._config,
        )


def _config_from_parameters(parameters: Mapping[str, object]) -> LoadcellEndpointMappingConfig:
    value = parameters.get("mapping_config")
    if isinstance(value, LoadcellEndpointMappingConfig):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("loadcell mapping requires mapping_config")
    return LoadcellEndpointMappingConfig(**dict(value))


def _current_tip_from_parameters(parameters: Mapping[str, object]) -> Vector3:
    return _coerce_vector3("current_tip_position_m", parameters.get("current_tip_position_m"))


class LoadcellEndpointMappingStrategy:
    mapping_semantics_identity = LOADCELL_MAPPING_SEMANTICS_IDENTITY

    def map_input(self, input_intent: object, parameters: Mapping[str, object]) -> InputIntent:
        if not isinstance(input_intent, NormalizedLoadcellInputIntentLike):
            raise TypeError(
                "loadcell endpoint mapping requires the source-normalized intent boundary"
            )
        command = build_motion_command_from_normalized_loadcell_intent(
            input_intent,
            current_tip_position_m=_current_tip_from_parameters(parameters),
            config=_config_from_parameters(parameters),
        )
        return InputIntent(
            source=input_intent.source,
            timestamp_s=input_intent.timestamp_s,
            values=input_intent.values,
            metadata=command.metadata,
        )


LOADCELL_ENDPOINT_MAPPING_PLUGIN = ControlMappingPlugin(
    identity=LOADCELL_ENDPOINT_MAPPING_IDENTITY,
    strategy=LoadcellEndpointMappingStrategy(),
    accepted_input_sample_schemas=frozenset({LOADCELL_VECTOR_SAMPLE_SCHEMA}),
    parameter_contract=ParameterContract(
        (
            ParameterField("mapping_config", object),
            ParameterField("current_tip_position_m", tuple),
        )
    ),
    comparison_family_identity=VersionedIdentity("loadcell_comparison", 1),
    mapping_semantics_identity=LOADCELL_MAPPING_SEMANTICS_IDENTITY,
)


__all__ = [
    "LOADCELL_ENDPOINT_MAPPING_IDENTITY",
    "LOADCELL_ENDPOINT_MAPPING_PLUGIN",
    "LOADCELL_MAPPING_SEMANTICS_IDENTITY",
    "LOADCELL_NORMALIZED_SAMPLE_SCHEMA",
    "LOADCELL_VECTOR_SAMPLE_SCHEMA",
    "LoadcellEndpointMappingConfig",
    "LoadcellEndpointMappingStrategy",
    "LoadcellEndpointMotionCommandConverter",
    "NormalizedLoadcellInputIntentLike",
    "build_motion_command_from_normalized_loadcell_intent",
    "build_r7_a_lite_smoke_endpoint_mapping_config",
]
