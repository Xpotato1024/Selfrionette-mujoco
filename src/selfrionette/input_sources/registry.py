"""Backward-compatible projection of the production input-source catalog.

The plugin catalog is the implementation source of truth.  This module keeps
the historical descriptor import working for existing callers and CLI code.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M
from selfrionette.schemas import RawInputFrame

SUPPORTED_INPUT_SOURCE_NAMES = (
    "programmed_target",
    "replay",
    "noop",
    "viewer",
)


@dataclass(frozen=True, slots=True)
class InputSourceDescriptor:
    name: str
    build_frames: Callable[..., tuple[RawInputFrame, ...]]
    initial_metadata: Mapping[str, object]


def _projected_builder(alias: str) -> Callable[..., tuple[RawInputFrame, ...]]:
    def build_frames(
        *,
        steps: int = 1,
        frames: Sequence[RawInputFrame] | None = None,
        metadata: Mapping[str, object] | None = None,
        **_: object,
    ) -> tuple[RawInputFrame, ...]:
        from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG

        request = INPUT_SOURCE_CATALOG.resolve(alias).request_builder(
            steps=steps,
            frames=frames,
            preset=None,
            replay_initial_metadata=metadata,
        )
        return request.frames

    return build_frames


_INITIAL_METADATA: dict[str, Mapping[str, object]] = {
    "programmed_target": {
        "source_kind": "programmed_target",
        "trajectory_name": "sweep_x",
    },
    "replay": {"preset": "r6-h-p5-default"},
    "noop": {"preset": "noop", "source_kind": "noop"},
    "viewer": {
        "preset": "viewer",
        "source_kind": "viewer",
        "source_active": False,
        "command_age_ms": 0,
        "stale_reason": "no_control_message_received",
        "desired_endpoint_m": DEFAULT_VIEWER_SAFE_ENDPOINT_M,
        "target_position_m": DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    },
}


class _CatalogProjection(Mapping[str, InputSourceDescriptor]):
    """Lazy mapping to avoid package-root import cycles during contract loading."""

    def __iter__(self):
        return iter(SUPPORTED_INPUT_SOURCE_NAMES)

    def __len__(self) -> int:
        return len(SUPPORTED_INPUT_SOURCE_NAMES)

    def __getitem__(self, source_name: str) -> InputSourceDescriptor:
        if source_name not in SUPPORTED_INPUT_SOURCE_NAMES:
            raise KeyError(source_name)
        return InputSourceDescriptor(
            name=source_name,
            build_frames=_projected_builder(source_name),
            initial_metadata=_INITIAL_METADATA[source_name],
        )


INPUT_SOURCE_REGISTRY: Mapping[str, InputSourceDescriptor] = _CatalogProjection()


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
