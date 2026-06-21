from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from math import isfinite
from typing import cast

from selfrionette.schemas import MotionCommand
from selfrionette.schemas import RawInputFrame


@dataclass(frozen=True, slots=True)
class RawLoadcellVectorRecord:
    timestamp_ms: int
    channels: tuple[float, float, float, float, float, float, float]
    raw_line: str


@dataclass(frozen=True, slots=True)
class SerialDiagnosticEvent:
    prefix: str
    fields: tuple[str, ...]
    raw_line: str


@dataclass(frozen=True, slots=True)
class LoadcellNormalizationConfig:
    channel_count: int = 7
    deadzone: float = 0.0
    scale: float = 1.0
    clamp_abs: float = 1.0

    def __post_init__(self) -> None:
        if self.channel_count != 7:
            raise ValueError("channel_count must be exactly 7")
        if self.scale <= 0.0:
            raise ValueError("scale must be positive")
        if self.deadzone < 0.0:
            raise ValueError("deadzone must be non-negative")
        if self.clamp_abs <= 0.0:
            raise ValueError("clamp_abs must be positive")


@dataclass(frozen=True, slots=True)
class NormalizedLoadcellInputIntent:
    source: str
    timestamp_s: float
    values: tuple[float, float, float, float, float, float, float]
    active_channels: tuple[int, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LoadcellEndpointMappingConfig:
    channel_axis_weights: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
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


class SerialFrameParseError(ValueError):
    def __init__(self, line: str, reason: str) -> None:
        self.line = line
        self.reason = reason
        super().__init__(f"{reason}: {line!r}")


def _raise_parse_error(line: str, reason: str) -> None:
    raise SerialFrameParseError(line, reason)


def _parse_timestamp_ms(text: str, *, line: str) -> int:
    try:
        timestamp_ms = int(text)
    except ValueError as exc:
        raise SerialFrameParseError(line, "malformed timestamp") from exc

    if timestamp_ms < 0:
        raise SerialFrameParseError(line, "negative timestamp")

    return timestamp_ms


def _parse_channel_value(text: str, *, line: str, channel_index: int) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise SerialFrameParseError(line, f"malformed channel value at index {channel_index}") from exc

    if not isfinite(value):
        raise SerialFrameParseError(line, f"non-finite channel value at index {channel_index}")

    return value


def parse_serial_frame_line(line: str) -> RawLoadcellVectorRecord | SerialDiagnosticEvent:
    stripped_line = line.strip()
    if not stripped_line:
        _raise_parse_error(line, "empty line")

    parts = stripped_line.split(",")
    prefix = parts[0]

    if prefix == "vector":
        if len(parts) != 9:
            _raise_parse_error(line, "vector frame must contain exactly 9 fields")

        timestamp_ms = _parse_timestamp_ms(parts[1], line=line)
        channels = cast(
            tuple[float, float, float, float, float, float, float],
            tuple(
                _parse_channel_value(parts[index], line=line, channel_index=index - 2)
                for index in range(2, 9)
            ),
        )
        return RawLoadcellVectorRecord(
            timestamp_ms=timestamp_ms,
            channels=channels,
            raw_line=stripped_line,
        )

    if prefix in {"status", "warn"}:
        return SerialDiagnosticEvent(
            prefix=prefix,
            fields=tuple(parts[1:]),
            raw_line=stripped_line,
        )

    return SerialDiagnosticEvent(
        prefix=prefix,
        fields=tuple(parts[1:]),
        raw_line=stripped_line,
    )


def _iterable_to_line_reader(lines: Iterable[str] | Iterator[str]) -> Callable[[], str]:
    iterator = iter(lines)

    def read_line() -> str:
        return next(iterator)

    return read_line


class SerialInputSource:
    """Injected-line serial source that yields parsed loadcell vector frames.

    The source collects diagnostic frames locally and only surfaces vector
    records as RawInputFrame objects. It does not open a serial port.
    """

    def __init__(self, line_reader: Iterable[str] | Iterator[str] | Callable[[], str]) -> None:
        if callable(line_reader):
            self._read_line = line_reader
        else:
            self._read_line = _iterable_to_line_reader(line_reader)

        self._diagnostics: list[SerialDiagnosticEvent] = []

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "SerialInputSource":
        return cls(lines)

    @property
    def diagnostics(self) -> tuple[SerialDiagnosticEvent, ...]:
        return tuple(self._diagnostics)

    def _read_next_line(self) -> str:
        try:
            return self._read_line()
        except StopIteration as exc:
            raise StopIteration("SerialInputSource reached end of injected lines") from exc

    def _read_next_vector_record(self) -> RawLoadcellVectorRecord:
        while True:
            line = self._read_next_line()
            record_or_event = parse_serial_frame_line(line)

            if isinstance(record_or_event, SerialDiagnosticEvent):
                self._diagnostics.append(record_or_event)
                continue

            return record_or_event

    def read_frame(self) -> RawInputFrame:
        vector_record = self._read_next_vector_record()
        return RawInputFrame(
            source="loadcell_serial",
            timestamp_s=float(vector_record.timestamp_ms) / 1000.0,
            values=vector_record.channels,
            metadata={
                "source_kind": "loadcell_serial",
                "timestamp_ms": vector_record.timestamp_ms,
                "raw_line": vector_record.raw_line,
            },
        )


def _coerce_loadcell_values(
    values: tuple[float, ...],
    *,
    expected_channel_count: int,
) -> tuple[float, float, float, float, float, float, float]:
    if len(values) != expected_channel_count:
        raise ValueError(f"loadcell vector must contain exactly {expected_channel_count} values")

    coerced_values = []
    for channel_index, raw_value in enumerate(values):
        if not isfinite(raw_value):
            raise ValueError(f"non-finite loadcell value at index {channel_index}")
        coerced_values.append(float(raw_value))

    return cast(
        tuple[float, float, float, float, float, float, float],
        tuple(coerced_values),
    )


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    for component_index, component in enumerate(components):
        if not isfinite(component):
            raise ValueError(f"{name} must contain only finite values at index {component_index}")

    return components


def _normalize_channel_value(raw_value: float, config: LoadcellNormalizationConfig) -> float:
    normalized_value = raw_value / config.scale
    if abs(normalized_value) < config.deadzone:
        return 0.0

    if normalized_value > config.clamp_abs:
        return config.clamp_abs
    if normalized_value < -config.clamp_abs:
        return -config.clamp_abs

    return normalized_value


def _clamp_vector3_components(value: tuple[float, float, float], *, limit: float) -> tuple[float, float, float]:
    return cast(
        tuple[float, float, float],
        tuple(
            max(-limit, min(limit, component))
            for component in value
        ),
    )


def _add_vector3(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return cast(
        tuple[float, float, float],
        tuple(left[index] + right[index] for index in range(3)),
    )


def _compute_endpoint_delta_m(
    values: tuple[float, float, float, float, float, float, float],
    config: LoadcellEndpointMappingConfig,
) -> tuple[float, float, float]:
    endpoint_delta_m = [0.0, 0.0, 0.0]
    for channel_value, channel_weights in zip(values, config.channel_axis_weights):
        endpoint_delta_m[0] += channel_value * channel_weights[0]
        endpoint_delta_m[1] += channel_value * channel_weights[1]
        endpoint_delta_m[2] += channel_value * channel_weights[2]

    scaled_delta_m = cast(
        tuple[float, float, float],
        tuple(component * config.gain_m for component in endpoint_delta_m),
    )
    return _clamp_vector3_components(scaled_delta_m, limit=config.max_delta_m)


def _build_loadcell_motion_metadata(
    *,
    intent: NormalizedLoadcellInputIntent,
    current_tip_position_m: tuple[float, float, float],
    endpoint_delta_m: tuple[float, float, float],
    desired_endpoint_m: tuple[float, float, float],
) -> dict[str, object]:
    metadata = dict(intent.metadata)
    metadata["active_channels"] = intent.active_channels
    metadata["current_tip_position_m"] = current_tip_position_m
    metadata["endpoint_delta_m"] = endpoint_delta_m
    metadata["desired_endpoint_m"] = desired_endpoint_m
    return metadata


def build_motion_command_from_normalized_loadcell_intent(
    intent: NormalizedLoadcellInputIntent,
    *,
    current_tip_position_m: tuple[float, float, float],
    config: LoadcellEndpointMappingConfig | None = None,
) -> MotionCommand:
    endpoint_config = LoadcellEndpointMappingConfig() if config is None else config
    normalized_values = _coerce_loadcell_values(intent.values, expected_channel_count=7)
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
        intent: NormalizedLoadcellInputIntent,
        *,
        current_tip_position_m: tuple[float, float, float],
    ) -> MotionCommand:
        return build_motion_command_from_normalized_loadcell_intent(
            intent,
            current_tip_position_m=current_tip_position_m,
            config=self._config,
        )


class LoadcellNormalizedInputIntentConverter:
    """Convert raw 7ch loadcell values into a normalized intent."""

    def __init__(
        self,
        config: LoadcellNormalizationConfig | None = None,
        *,
        source: str = "loadcell_serial",
    ) -> None:
        self._config = LoadcellNormalizationConfig() if config is None else config
        self._source = source

    @property
    def config(self) -> LoadcellNormalizationConfig:
        return self._config

    def convert(self, frame: RawInputFrame | RawLoadcellVectorRecord) -> NormalizedLoadcellInputIntent:
        if isinstance(frame, RawInputFrame):
            source = frame.source
            timestamp_s = frame.timestamp_s
            raw_values = frame.values
            metadata = dict(frame.metadata)
        else:
            source = self._source
            timestamp_s = float(frame.timestamp_ms) / 1000.0
            raw_values = frame.channels
            metadata = {}

        values = _coerce_loadcell_values(raw_values, expected_channel_count=self._config.channel_count)
        normalized_values = tuple(
            _normalize_channel_value(raw_value, self._config)
            for raw_value in values
        )
        active_channels = tuple(
            channel_index
            for channel_index, normalized_value in enumerate(normalized_values)
            if normalized_value != 0.0
        )

        return NormalizedLoadcellInputIntent(
            source=source,
            timestamp_s=timestamp_s,
            values=cast(
                tuple[float, float, float, float, float, float, float],
                normalized_values,
            ),
            active_channels=active_channels,
            metadata=metadata,
        )


__all__ = [
    "LoadcellNormalizationConfig",
    "LoadcellEndpointMappingConfig",
    "LoadcellEndpointMotionCommandConverter",
    "build_motion_command_from_normalized_loadcell_intent",
    "LoadcellNormalizedInputIntentConverter",
    "NormalizedLoadcellInputIntent",
    "RawLoadcellVectorRecord",
    "SerialDiagnosticEvent",
    "SerialFrameParseError",
    "SerialInputSource",
    "parse_serial_frame_line",
]
