"""Recorded analog-fixture acquisition and strict sample validation."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence

Vector3 = tuple[float, float, float]


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _numbers(name: str, value: object) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"{name} must be a non-empty sequence of JSON numbers")
    return tuple(_number(f"{name}[{index}]", item) for index, item in enumerate(value))


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


__all__ = [
    "AnalogFixtureSample",
    "parse_analog_fixture_sample",
]
