"""Programmed-target Input Source Plugin implementation."""

from collections.abc import Mapping

from selfrionette.input_sources.programmed_target import build_sweep_x_input_source
from selfrionette.plugins.input_sources._common import FrameHealthReader
from selfrionette.runtime.experiment.input_source import InputSourceHealth, InputSourceHealthStatus
from selfrionette.schemas import RawInputFrame


def build_frames(parameters: Mapping[str, object]) -> tuple[RawInputFrame, ...]:
    steps = parameters["steps"]
    initial_position_m = parameters["initial_position_m"]
    source = build_sweep_x_input_source(initial_position_m=initial_position_m, loop=False)
    return tuple(source.read_frame() for _ in range(steps))


def build_reader(parameters: Mapping[str, object]) -> FrameHealthReader:
    frames = build_frames(parameters)

    class Reader:
        def __init__(self) -> None:
            self._frames = iter(frames)

        def read_frame(self) -> RawInputFrame:
            return next(self._frames)

        def current_health(self) -> InputSourceHealth:
            return InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0)

    return FrameHealthReader(Reader(), InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0))


__all__ = ["build_frames", "build_reader"]
