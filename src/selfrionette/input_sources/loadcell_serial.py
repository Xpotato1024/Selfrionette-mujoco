"""Load-cell serial acquisition with a mapping compatibility facade."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from math import isfinite
from typing import cast

from selfrionette.schemas import InputIntent
from selfrionette.schemas import MotionCommand
from selfrionette.schemas import RawInputFrame
from selfrionette.plugins.mappings.loadcell import (
    LoadcellEndpointMappingConfig,
    LoadcellEndpointMotionCommandConverter,
    build_motion_command_from_normalized_loadcell_intent,
    build_r7_a_lite_smoke_endpoint_mapping_config,
)


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
class LoadcellSerialDryRunSmokeResult:
    frames_read: int
    vectors_read: int
    diagnostics: tuple[SerialDiagnosticEvent, ...]
    raw_frame: RawInputFrame | None
    normalized_intent: NormalizedLoadcellInputIntent | None
    motion_command: MotionCommand | None


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


def _normalize_channel_value(raw_value: float, config: LoadcellNormalizationConfig) -> float:
    normalized_value = raw_value / config.scale
    if abs(normalized_value) < config.deadzone:
        return 0.0

    if normalized_value > config.clamp_abs:
        return config.clamp_abs
    if normalized_value < -config.clamp_abs:
        return -config.clamp_abs

    return normalized_value


def run_loadcell_serial_dry_run_smoke(
    lines: Iterable[str],
    *,
    max_vectors: int = 1,
    normalization_config: LoadcellNormalizationConfig | None = None,
    endpoint_config: LoadcellEndpointMappingConfig | None = None,
    current_tip_position_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
    mapping_plugin: object | None = None,
    mapping_parameters: Mapping[str, object] | None = None,
) -> LoadcellSerialDryRunSmokeResult:
    """Run the recorded-frame smoke through the canonical mapping when supplied.

    ``mapping_plugin=None`` preserves the public recorded-fixture compatibility
    helper and delegates to the canonical mapping converter. Production runner
    entry points resolve and pass the versioned Control Mapping Plugin.
    """

    if max_vectors < 1:
        raise ValueError("max_vectors must be a positive integer")

    source = SerialInputSource.from_lines(lines)
    normalized_converter = LoadcellNormalizedInputIntentConverter(normalization_config)
    endpoint_converter = LoadcellEndpointMotionCommandConverter(endpoint_config)
    selected_mapping_parameters = (
        {
            "mapping_config": endpoint_config or {},
            "current_tip_position_m": current_tip_position_m,
        }
        if mapping_parameters is None
        else mapping_parameters
    )

    frames_read = 0
    vectors_read = 0
    last_raw_frame: RawInputFrame | None = None
    last_normalized_intent: NormalizedLoadcellInputIntent | None = None
    last_motion_command: MotionCommand | None = None

    while vectors_read < max_vectors:
        try:
            raw_frame = source.read_frame()
        except StopIteration:
            break

        frames_read += 1
        vectors_read += 1
        last_raw_frame = raw_frame
        last_normalized_intent = normalized_converter.convert(raw_frame)
        if mapping_plugin is None:
            last_motion_command = endpoint_converter.convert(
                last_normalized_intent,
                current_tip_position_m=current_tip_position_m,
            )
        else:
            strategy = getattr(mapping_plugin, "strategy", None)
            map_input = getattr(strategy, "map_input", None)
            if not callable(map_input):
                raise TypeError("loadcell mapping plugin must expose strategy.map_input")
            mapped_intent = map_input(
                last_normalized_intent,
                selected_mapping_parameters,
            )
            if not isinstance(mapped_intent, InputIntent):
                raise TypeError("loadcell mapping strategy returned an invalid input intent")
            last_motion_command = MotionCommand(
                timestamp_s=mapped_intent.timestamp_s,
                metadata=mapped_intent.metadata,
            )

    return LoadcellSerialDryRunSmokeResult(
        frames_read=frames_read,
        vectors_read=vectors_read,
        diagnostics=source.diagnostics,
        raw_frame=last_raw_frame,
        normalized_intent=last_normalized_intent,
        motion_command=last_motion_command,
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


def normalize_loadcell_frame_for_mapping(
    frame: RawInputFrame,
) -> NormalizedLoadcellInputIntent:
    """Adapt one raw source frame at the explicit source-to-mapping boundary."""

    return LoadcellNormalizedInputIntentConverter().convert(frame)


__all__ = [
    "LoadcellNormalizationConfig",
    "LoadcellEndpointMappingConfig",
    "LoadcellEndpointMotionCommandConverter",
    "build_motion_command_from_normalized_loadcell_intent",
    "build_r7_a_lite_smoke_endpoint_mapping_config",
    "LoadcellNormalizedInputIntentConverter",
    "normalize_loadcell_frame_for_mapping",
    "LoadcellSerialDryRunSmokeResult",
    "NormalizedLoadcellInputIntent",
    "RawLoadcellVectorRecord",
    "SerialDiagnosticEvent",
    "SerialFrameParseError",
    "SerialInputSource",
    "parse_serial_frame_line",
    "run_loadcell_serial_dry_run_smoke",
]
