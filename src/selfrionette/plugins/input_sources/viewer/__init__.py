"""Backend viewer bridge compatibility Input Source Plugin."""

from collections.abc import Mapping
from time import monotonic

from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M, ViewerInputSource
from selfrionette.plugins.input_sources._common import ManagedFrameHealthReader
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceRuntimeDependencies,
)
from selfrionette.schemas import RawInputFrame


def build_frames(parameters: Mapping[str, object]) -> tuple[RawInputFrame, ...]:
    return (RawInputFrame(source="viewer", timestamp_s=0.0, metadata=dict(parameters["metadata"])),)


def build_reader(parameters: Mapping[str, object], *, runtime_dependencies: InputSourceRuntimeDependencies | None = None) -> ManagedFrameHealthReader:
    endpoint = parameters.get("initial_endpoint_m", DEFAULT_VIEWER_SAFE_ENDPOINT_M)
    clock = monotonic if runtime_dependencies is None or runtime_dependencies.clock is None else runtime_dependencies.clock
    delegate = ViewerInputSource(initial_endpoint_m=endpoint, clock=clock)
    initial = InputSourceHealth(
        InputSourceHealthStatus.STALE,
        reason="no_control_message_received",
        age_ms=0,
    )
    return ManagedFrameHealthReader(
        delegate,
        initial,
        viewer_bridge_capability=delegate,
    )


__all__ = ["build_frames", "build_reader"]
