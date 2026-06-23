from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from selfrionette.input_sources.programmed_target import build_sweep_x_input_source
from selfrionette.input_sources.registry import SUPPORTED_INPUT_SOURCE_NAMES, get_input_source_descriptor
from selfrionette.schemas import RawInputFrame

DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M: tuple[float, float, float] = (0.6, 0.0, 0.1)

_DEFAULT_REPLAY_INITIAL_METADATA: dict[str, object] = {
    "preset": "r6-h-p5-default",
    "target_position_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
    "desired_endpoint_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
}

_DEFAULT_NOOP_INITIAL_METADATA: dict[str, object] = {
    "preset": "noop",
    "source_kind": "noop",
    "target_position_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
    "desired_endpoint_m": DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M,
}


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceSelection:
    source_name: str
    frames: tuple[RawInputFrame, ...]
    loop: bool
    initial_metadata: Mapping[str, object]


def _build_programmed_target_frames(*, steps: int) -> tuple[RawInputFrame, ...]:
    if steps < 1:
        raise ValueError("steps must be a positive integer")

    source = build_sweep_x_input_source(initial_position_m=DEFAULT_RUNTIME_SELECTION_TARGET_POSITION_M, loop=False)
    return tuple(source.read_frame() for _ in range(steps))


def _build_replay_frames(
    frames: Sequence[RawInputFrame] | None,
    *,
    metadata: Mapping[str, object] | None = None,
) -> tuple[RawInputFrame, ...]:
    descriptor = get_input_source_descriptor("replay")
    return descriptor.build_frames(
        frames=frames,
        metadata=_DEFAULT_REPLAY_INITIAL_METADATA if metadata is None else metadata,
    )


def _build_noop_frames() -> tuple[RawInputFrame, ...]:
    descriptor = get_input_source_descriptor("noop")
    return descriptor.build_frames(metadata=_DEFAULT_NOOP_INITIAL_METADATA)


def select_runtime_input_source(
    source_name: str,
    *,
    steps: int,
    frames: Sequence[RawInputFrame] | None = None,
    preset: str | None = None,
    replay_initial_metadata: Mapping[str, object] | None = None,
) -> RuntimeInputSourceSelection:
    descriptor = get_input_source_descriptor(source_name)

    if source_name == "programmed_target":
        if preset not in (None, "sweep_x"):
            raise ValueError("unsupported programmed_target preset")
        if frames is not None:
            raise ValueError("programmed_target input source does not accept custom frames")

        selected_frames = _build_programmed_target_frames(steps=steps)
        loop = False
    elif source_name == "replay":
        if preset is not None:
            raise ValueError("preset is not supported for replay input source")

        selected_frames = _build_replay_frames(
            frames,
            metadata=_DEFAULT_REPLAY_INITIAL_METADATA if replay_initial_metadata is None else replay_initial_metadata,
        )
        loop = True
    elif source_name == "noop":
        if preset is not None:
            raise ValueError("preset is not supported for noop input source")
        if frames is not None:
            raise ValueError("noop input source does not accept custom frames")

        selected_frames = _build_noop_frames()
        loop = True
    else:
        raise ValueError(f"unsupported input source: {source_name!r}")

    return RuntimeInputSourceSelection(
        source_name=descriptor.name,
        frames=selected_frames,
        loop=loop,
        initial_metadata=dict(descriptor.initial_metadata),
    )


__all__ = [
    "RuntimeInputSourceSelection",
    "SUPPORTED_INPUT_SOURCE_NAMES",
    "select_runtime_input_source",
]
