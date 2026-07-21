"""Small source-plugin adapters shared by first-party registrations.

The adapters keep the existing ``RawInputFrame`` implementations as the
compatibility behavior while adding the P2 health and lifecycle boundary.
They do not interpret frames or create robot commands.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
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
    age_ms = age if type(age) is int and age >= 0 else 0
    health_metadata: dict[str, object] = {"source": frame.source}
    if "source_kind" in metadata:
        health_metadata["source_kind"] = metadata["source_kind"]
    if reason is not None:
        return InputSourceHealth(
            InputSourceHealthStatus.STALE,
            reason=str(reason),
            age_ms=age_ms,
            metadata=health_metadata,
        )
    if active is False:
        return InputSourceHealth(
            InputSourceHealthStatus.INACTIVE,
            age_ms=age_ms,
            metadata=health_metadata,
        )
    return InputSourceHealth(
        default_status,
        age_ms=age_ms,
        metadata=health_metadata,
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


class _ManagedLifecycleState(str, Enum):
    NEW = "new"
    STARTING = "starting"
    STARTED = "started"
    START_FAILED = "start_failed"
    CLOSING = "closing"
    CLOSED = "closed"


class ManagedFrameHealthReader(FrameHealthReader):
    """Health adapter with retry-safe managed lifecycle forwarding."""

    def __init__(
        self,
        delegate: Any,
        initial_health: InputSourceHealth,
        *,
        viewer_bridge_capability: ViewerBridgeRuntimeCapability | None = None,
        started_health: InputSourceHealth | None = None,
        start_failure_health: InputSourceHealth | None = None,
        closed_health: InputSourceHealth | None = None,
    ) -> None:
        super().__init__(delegate, initial_health)
        self._viewer_bridge_capability = viewer_bridge_capability
        self._started_health = started_health
        self._start_failure_health = start_failure_health
        self._closed_health = closed_health
        self._lifecycle_state = _ManagedLifecycleState.NEW

    def start(self) -> None:
        if self._lifecycle_state is _ManagedLifecycleState.STARTED:
            return
        if self._lifecycle_state is _ManagedLifecycleState.START_FAILED:
            raise RuntimeError(
                "managed input source must be closed after a failed start before retry"
            )
        if self._lifecycle_state in (
            _ManagedLifecycleState.STARTING,
            _ManagedLifecycleState.CLOSING,
        ):
            raise RuntimeError(
                f"managed input source cannot start while {self._lifecycle_state.value}"
            )

        self._lifecycle_state = _ManagedLifecycleState.STARTING
        callback = getattr(self._delegate, "start", None)
        try:
            if callable(callback):
                callback()
        except BaseException:
            self._lifecycle_state = _ManagedLifecycleState.START_FAILED
            if self._start_failure_health is not None:
                self._health = self._start_failure_health
            raise
        self._lifecycle_state = _ManagedLifecycleState.STARTED
        if self._started_health is not None:
            self._health = self._started_health

    def close(self) -> None:
        if self._lifecycle_state in (
            _ManagedLifecycleState.NEW,
            _ManagedLifecycleState.CLOSED,
        ):
            return
        if self._lifecycle_state is _ManagedLifecycleState.CLOSING:
            return
        if self._lifecycle_state is _ManagedLifecycleState.STARTING:
            raise RuntimeError("managed input source cannot close while starting")

        previous_state = self._lifecycle_state
        self._lifecycle_state = _ManagedLifecycleState.CLOSING
        callback = getattr(self._delegate, "close", None)
        try:
            if callable(callback):
                callback()
        except BaseException:
            self._lifecycle_state = previous_state
            raise
        self._lifecycle_state = _ManagedLifecycleState.CLOSED
        if self._closed_health is not None:
            self._health = self._closed_health

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
        from selfrionette.input_sources.analog_fixture import (
            parse_analog_fixture_sample,
        )

        self._samples = tuple(
            parse_analog_fixture_sample(sample) for sample in samples
        )
        if not self._samples:
            raise ValueError(
                "analog_fixture input source requires at least one sample"
            )
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
        if self._last.stale_reason is None:
            return InputSourceHealth(
                InputSourceHealthStatus.INACTIVE,
                age_ms=0,
            )
        return InputSourceHealth(
            InputSourceHealthStatus.STALE,
            reason=self._last.stale_reason,
            age_ms=0,
        )


__all__ = [
    "AnalogFixtureInputSource",
    "FrameHealthReader",
    "ManagedFrameHealthReader",
    "NoopInputSource",
    "health_from_frame",
]
