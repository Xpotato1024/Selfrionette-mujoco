"""Backward-compatible low-level input-source descriptor registry.

The production runtime selection source of truth is
``selfrionette.plugins.input_sources.catalog``.  This module intentionally
remains independent from ``plugins`` and ``runtime`` so existing low-level
callers keep their historical frame-builder signatures without reversing the
canonical layer dependency.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from selfrionette.input_sources.programmed_target import build_sweep_x_input_source
from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M
from selfrionette.schemas import RawInputFrame
from selfrionette.schemas.types import Vector3


@dataclass(frozen=True, slots=True)
class InputSourceDescriptor:
    name: str
    build_frames: Callable[..., tuple[RawInputFrame, ...]]
    initial_metadata: Mapping[str, object]


def _build_programmed_target_frames(
    *,
    steps: int,
    initial_position_m: Vector3,
) -> tuple[RawInputFrame, ...]:
    if steps < 1:
        raise ValueError("steps must be a positive integer")

    source = build_sweep_x_input_source(
        initial_position_m=initial_position_m,
        loop=False,
    )
    return tuple(source.read_frame() for _ in range(steps))


def _build_replay_frames(
    *,
    frames: Sequence[RawInputFrame] | None = None,
    metadata: Mapping[str, object] | None = None,
) -> tuple[RawInputFrame, ...]:
    if frames is not None:
        replay_frames = tuple(frames)
        if not replay_frames:
            raise ValueError("replay input source requires at least one frame")
        return replay_frames

    return (
        RawInputFrame(
            source="replay",
            timestamp_s=0.0,
            metadata={} if metadata is None else dict(metadata),
        ),
    )


def _build_noop_frames(*, metadata: Mapping[str, object]) -> tuple[RawInputFrame, ...]:
    return (
        RawInputFrame(
            source="noop",
            timestamp_s=0.0,
            metadata=dict(metadata),
        ),
    )


def _build_viewer_frames(*, metadata: Mapping[str, object]) -> tuple[RawInputFrame, ...]:
    return (
        RawInputFrame(
            source="viewer",
            timestamp_s=0.0,
            values=(),
            buttons=(),
            metadata=dict(metadata),
        ),
    )


INPUT_SOURCE_REGISTRY: dict[str, InputSourceDescriptor] = {
    "programmed_target": InputSourceDescriptor(
        name="programmed_target",
        build_frames=_build_programmed_target_frames,
        initial_metadata={
            "source_kind": "programmed_target",
            "trajectory_name": "sweep_x",
        },
    ),
    "replay": InputSourceDescriptor(
        name="replay",
        build_frames=_build_replay_frames,
        initial_metadata={
            "preset": "r6-h-p5-default",
        },
    ),
    "noop": InputSourceDescriptor(
        name="noop",
        build_frames=_build_noop_frames,
        initial_metadata={
            "preset": "noop",
            "source_kind": "noop",
        },
    ),
    "viewer": InputSourceDescriptor(
        name="viewer",
        build_frames=_build_viewer_frames,
        initial_metadata={
            "preset": "viewer",
            "source_kind": "viewer",
            "source_active": False,
            "command_age_ms": 0,
            "stale_reason": "no_control_message_received",
            "desired_endpoint_m": DEFAULT_VIEWER_SAFE_ENDPOINT_M,
            "target_position_m": DEFAULT_VIEWER_SAFE_ENDPOINT_M,
        },
    ),
}

SUPPORTED_INPUT_SOURCE_NAMES = tuple(INPUT_SOURCE_REGISTRY)


def get_input_source_descriptor(source_name: str) -> InputSourceDescriptor:
    try:
        return INPUT_SOURCE_REGISTRY[source_name]
    except KeyError as exc:
        raise ValueError(f"unsupported input source: {source_name!r}") from exc


__all__ = [
    "INPUT_SOURCE_REGISTRY",
    "InputSourceDescriptor",
    "SUPPORTED_INPUT_SOURCE_NAMES",
    "get_input_source_descriptor",
]
