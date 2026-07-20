"""Small source-plugin adapters shared by first-party registrations.

The adapters keep the existing ``RawInputFrame`` implementations as the
compatibility behavior while adding the P2 health and lifecycle boundary.
They do not interpret frames or create robot commands.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    ViewerBridgeRuntimeCapability,
)
from selfrionette.schemas import RawInputFrame


def health_from_frame(
    frame: RawInputFrame,
    *,
    default_status: InputSourceHealthStatus = InputSourceHealthStatus.ACTIVE,
) -> InputSourceHealth:
    metadata = frame.metadata
    active = metadata.get("source_active")
    reason = metadata.get("stale_reason")
    age = metadata.get("command_age_ms")
    if active is False or reason is not None:
        return InputSourceHealth(
            InputSourceHealthStatus.STALE,
            reason=str(reason) if reason else "source_inactive",
            age_ms=age if type(age) is int and age >= 0 else 0,
            metadata={"source": frame.source},
        )
    return InputSourceHealth(
        default_status,
        age_ms=age if type(age) is int and age >= 0 else 0,
        metadata={"source": frame.source},
    )


class FrameHealthReader:
    """Add typed health to an existing frame reader without changing frames."""

    def __init__(self, delegate: Any, initial_health: InputSourceHealth) -> None:
        self._delegate = delegate
        self._initial_health = initial_health
        self._health = initial_health

    def read_frame(self) -> RawInputFrame:
        frame = self._delegate.read_frame()
        self._health = health_from_frame(
            frame,
            default_status=InputSourceHealthStatus.ACTIVE,
        )
        return frame

    def current_health(self) -> InputSourceHealth:
        return self._health


class ManagedFrameHealthReader(FrameHealthReader):
    """Health adapter with idempotent managed lifecycle forwarding."""

    def __init__(
        self,
        delegate: Any,
        initial_health: InputSourceHealth,
        *,
        viewer_bridge_capability: ViewerBridgeRuntimeCapability | None = None,
    ) -> None:
        super().__init__(delegate, initial_health)
        self._viewer_bridge_capability = viewer_bridge_capability
        self._started = False
        self._closed = False

    def start(self) -> None:
        if self._started:
            return
        callback = getattr(self._delegate, "start", None)
        if callable(callback):
            callback()
        self._started = True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        callback = getattr(self._delegate, "close", None)
        if callable(callback):
            callback()

    @property
    def viewer_bridge_capability(self) -> ViewerBridgeRuntimeCapability | None:
        return self._viewer_bridge_capability


class NoopInputSource:
    def __init__(self, frame: RawInputFrame) -> None:
        self._frame = frame

    def read_frame(self) -> RawInputFrame:
        return self._frame

    def current_health(self) -> InputSourceHealth:
        return InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0)


class AnalogFixtureInputSource:
    def __init__(self, samples: tuple[Mapping[str, object], ...]) -> None:
        from selfrionette.input_sources.analog_fixture import parse_analog_fixture_sample

        self._samples = tuple(parse_analog_fixture_sample(sample) for sample in samples)
        if not self._samples:
            raise ValueError("analog_fixture input source requires at least one sample")
        self._index = 0
        self._last = None

    def read_frame(self) -> RawInputFrame:
        sample = self._samples[min(self._index, len(self._samples) - 1)]
        self._index += 1
        self._last = sample
        return RawInputFrame(
            source="analog_fixture",
            timestamp_s=sample.timestamp_s,
            values=tuple(float(value) for value in sample.raw_values),
            metadata={
                "source_kind": "analog_fixture",
                "source_active": sample.active,
                "stale_reason": sample.stale_reason,
            },
        )

    def current_health(self) -> InputSourceHealth:
        if self._last is None or self._last.active:
            return InputSourceHealth(
                InputSourceHealthStatus.ACTIVE,
                age_ms=0,
            )
        return InputSourceHealth(
            InputSourceHealthStatus.STALE,
            reason=self._last.stale_reason or "recording_stale",
            age_ms=0,
        )


__all__ = [
    "AnalogFixtureInputSource",
    "FrameHealthReader",
    "ManagedFrameHealthReader",
    "NoopInputSource",
    "health_from_frame",
]
