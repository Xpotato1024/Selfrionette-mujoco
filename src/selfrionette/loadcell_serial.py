from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import cast


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
