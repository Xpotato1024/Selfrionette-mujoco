"""Pure recorded-analog-fixture mapping into the P16 input contract."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence

from selfrionette.input_sources.continuous_endpoint_velocity import (
    build_normalized_analog_fixture_intent,
)
from selfrionette.schemas import ContinuousEndpointVelocityIntent


Vector3 = tuple[float, float, float]


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _vector3(name: str, value: object) -> Vector3:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise ValueError(f"{name} must contain exactly three JSON numbers")
    return tuple(_number(name, item) for item in value)  # type: ignore[return-value]


def _numbers(name: str, value: object) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"{name} must be a non-empty sequence of JSON numbers")
    return tuple(_number(f"{name}[{index}]", item) for index, item in enumerate(value))


def _weight_matrix(value: object) -> tuple[Vector3, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("channel_axis_weights must be a non-empty N x 3 matrix")
    return tuple(_vector3(f"channel_axis_weights[{index}]", row) for index, row in enumerate(value))


@dataclass(frozen=True, slots=True)
class AnalogFixtureSample:
    """One already-recorded sample; no device or filesystem access is performed."""

    timestamp_s: float
    raw_values: tuple[float, ...]
    active: bool
    stale_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp_s", _number("timestamp_s", self.timestamp_s))
        object.__setattr__(self, "raw_values", _numbers("raw_values", self.raw_values))
        if type(self.active) is not bool:
            raise ValueError("active must be a JSON boolean")
        if self.stale_reason is not None and (
            not isinstance(self.stale_reason, str) or not self.stale_reason.strip()
        ):
            raise ValueError("stale_reason must be a non-empty string or null")
        if self.active and self.stale_reason is not None:
            raise ValueError("an active fixture sample cannot be stale")


@dataclass(frozen=True, slots=True)
class AnalogFixtureMappingConfig:
    """Immutable and fully explicit raw-channel mapping configuration."""

    centers: tuple[float, ...]
    half_ranges: tuple[float, ...]
    channel_axis_weights: tuple[Vector3, ...]
    signs: tuple[int, int, int] = (1, 1, 1)
    scales: Vector3 = (1.0, 1.0, 1.0)
    deadzone: float = 0.0
    speed_m_s: float = 0.1
    max_delta_m: float = 0.01
    control_frame: str = "world"
    source_kind: str = "analog_fixture"

    def __post_init__(self) -> None:
        centers = _numbers("centers", self.centers)
        ranges = _numbers("half_ranges", self.half_ranges)
        weights = _weight_matrix(self.channel_axis_weights)
        if len(centers) != len(ranges) or len(centers) != len(weights):
            raise ValueError("centers, half_ranges, and channel_axis_weights must have equal channel counts")
        object.__setattr__(self, "centers", centers)
        if any(value <= 0.0 for value in ranges):
            raise ValueError("half_ranges must be positive")
        object.__setattr__(self, "half_ranges", ranges)
        object.__setattr__(self, "channel_axis_weights", weights)
        if not isinstance(self.signs, Sequence) or isinstance(self.signs, (str, bytes)):
            raise ValueError("signs must contain exactly three integer -1 or 1 values")
        signs = tuple(self.signs)
        if len(signs) != 3 or any(type(value) is not int or value not in (-1, 1) for value in signs):
            raise ValueError("signs must contain only integer -1 or 1")
        object.__setattr__(self, "signs", signs)
        scales = _vector3("scales", self.scales)
        if any(value < 0.0 for value in scales):
            raise ValueError("scales must be non-negative")
        object.__setattr__(self, "scales", scales)
        for name in ("deadzone", "speed_m_s", "max_delta_m"):
            value = _number(name, getattr(self, name))
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)
        if self.control_frame not in {"world", "tool"}:
            raise ValueError("control_frame must be 'world' or 'tool'")
        if not isinstance(self.source_kind, str) or not self.source_kind.strip():
            raise ValueError("source_kind must be a non-empty string")


def parse_analog_fixture_sample(value: Mapping[str, object]) -> AnalogFixtureSample:
    """Strictly parse the small JSON-compatible recorded fixture format."""

    if not isinstance(value, Mapping):
        raise ValueError("fixture sample must be an object")
    expected = {"timestamp_s", "raw_values", "active", "stale_reason"}
    if set(value) != expected:
        raise ValueError(f"fixture sample fields must be exactly {sorted(expected)!r}")
    return AnalogFixtureSample(
        timestamp_s=value["timestamp_s"],  # type: ignore[arg-type]
        raw_values=value["raw_values"],  # type: ignore[arg-type]
        active=value["active"],  # type: ignore[arg-type]
        stale_reason=value["stale_reason"],  # type: ignore[arg-type]
    )


def map_analog_fixture_sample(
    sample: AnalogFixtureSample,
    config: AnalogFixtureMappingConfig,
) -> ContinuousEndpointVelocityIntent:
    """Normalize, clamp, project, sign and scale one recorded sample."""

    if len(sample.raw_values) != len(config.centers):
        raise ValueError("fixture raw_values channel count must match mapping configuration")
    normalized_channels = tuple(
        max(
            -1.0,
            min(
                1.0,
                (sample.raw_values[index] - config.centers[index]) / config.half_ranges[index],
            ),
        )
        for index in range(len(config.centers))
    )
    weighted_axes = tuple(
        sum(
            value * config.channel_axis_weights[channel][axis]
            for channel, value in enumerate(normalized_channels)
        )
        for axis in range(3)
    )
    axes = tuple(weighted_axes[axis] * config.signs[axis] * config.scales[axis] for axis in range(3))
    return build_normalized_analog_fixture_intent(
        axes,
        source_timestamp_s=sample.timestamp_s,
        source_active=sample.active,
        stale_reason=sample.stale_reason,
        control_frame=config.control_frame,
        source_kind=config.source_kind,
        speed_m_s=config.speed_m_s,
        deadzone=config.deadzone,
        max_delta_m=config.max_delta_m,
        source_diagnostics={"raw_values": sample.raw_values},
    )


__all__ = [
    "AnalogFixtureMappingConfig",
    "AnalogFixtureSample",
    "map_analog_fixture_sample",
    "parse_analog_fixture_sample",
]
