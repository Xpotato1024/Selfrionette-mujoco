"""Replay Input Source Plugin implementation."""

from collections.abc import Mapping

from selfrionette.input_sources.replay import ReplayInputSource
from selfrionette.plugins.input_sources._common import FrameHealthReader
from selfrionette.runtime.experiment.input_source import InputSourceHealth, InputSourceHealthStatus, InputSourceRuntimeDependencies
from selfrionette.schemas import RawInputFrame


def build_frames(parameters: Mapping[str, object]) -> tuple[RawInputFrame, ...]:
    frames = parameters.get("frames")
    if frames is None:
        return (RawInputFrame(source="replay", timestamp_s=0.0, metadata=dict(parameters["metadata"])),)
    return tuple(frames)


def build_reader(parameters: Mapping[str, object], *, runtime_dependencies: InputSourceRuntimeDependencies | None = None) -> FrameHealthReader:
    frames = (
        runtime_dependencies.replay_frames
        if runtime_dependencies is not None and runtime_dependencies.replay_frames is not None
        else build_frames(parameters)
    )
    delegate = ReplayInputSource(frames, loop=bool(parameters.get("loop", True)))
    initial = InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0)
    return FrameHealthReader(delegate, initial)


__all__ = ["build_frames", "build_reader"]
