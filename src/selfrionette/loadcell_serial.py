from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from math import isfinite
from typing import cast

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


__all__ = [
    "RawLoadcellVectorRecord",
    "SerialDiagnosticEvent",
    "SerialFrameParseError",
    "SerialInputSource",
    "parse_serial_frame_line",
]
