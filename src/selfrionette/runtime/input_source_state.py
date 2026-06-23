from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from selfrionette.schemas import RawInputFrame


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceState:
    source_kind: str
    source_active: bool = True
    command_age_ms: int | None = 0
    stale_reason: str | None = None


def build_runtime_input_source_state(
    source_kind: str,
    *,
    source_active: bool = True,
    command_age_ms: int | None = 0,
    stale_reason: str | None = None,
) -> RuntimeInputSourceState:
    return RuntimeInputSourceState(
        source_kind=source_kind,
        source_active=source_active,
        command_age_ms=command_age_ms,
        stale_reason=stale_reason,
    )


def runtime_input_source_state_to_metadata(state: RuntimeInputSourceState) -> dict[str, object]:
    metadata: dict[str, object] = {
        "source_kind": state.source_kind,
        "source_active": state.source_active,
    }
    if state.command_age_ms is not None:
        metadata["command_age_ms"] = state.command_age_ms
    if state.stale_reason is not None:
        metadata["stale_reason"] = state.stale_reason
    return metadata


def annotate_runtime_input_source_metadata(
    metadata: Mapping[str, object],
    state: RuntimeInputSourceState,
) -> dict[str, object]:
    annotated_metadata = dict(metadata)
    annotated_metadata.update(runtime_input_source_state_to_metadata(state))
    return annotated_metadata


def annotate_raw_input_frame(frame: RawInputFrame, state: RuntimeInputSourceState) -> RawInputFrame:
    return replace(frame, metadata=annotate_runtime_input_source_metadata(frame.metadata, state))


__all__ = [
    "RuntimeInputSourceState",
    "annotate_raw_input_frame",
    "annotate_runtime_input_source_metadata",
    "build_runtime_input_source_state",
    "runtime_input_source_state_to_metadata",
]
