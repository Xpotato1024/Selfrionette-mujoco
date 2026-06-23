from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from selfrionette.runtime.input_source_state import RuntimeInputSourceState, runtime_input_source_state_to_metadata
from selfrionette.schemas import JointCommand, MotionCommand, MuJoCoState

DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS = 250


@dataclass(frozen=True, slots=True)
class RuntimeInputSafetyResult:
    motion_command: MotionCommand
    source_state: RuntimeInputSourceState
    is_stale: bool
    stale_reason: str | None
    command_age_ms: int | None


def _coerce_current_qpos(current_qpos: Sequence[float] | None) -> tuple[float, ...] | None:
    if current_qpos is None:
        return None

    qpos = tuple(float(value) for value in current_qpos)
    if not qpos:
        return None

    return qpos


def _derive_stale_reason(
    source_state: RuntimeInputSourceState,
    *,
    timeout_ms: int,
) -> str | None:
    if not source_state.source_active:
        return "source_inactive"

    if source_state.stale_reason is not None:
        return source_state.stale_reason

    if source_state.command_age_ms is not None and source_state.command_age_ms > timeout_ms:
        return f"command_age_ms_exceeded_timeout_{timeout_ms}"

    return None


def _build_hold_motion_command(
    command: MotionCommand,
    *,
    current_qpos: Sequence[float] | None,
    source_state: RuntimeInputSourceState,
    stale_reason: str,
) -> MotionCommand:
    qpos = _coerce_current_qpos(current_qpos)
    metadata = {
        **dict(command.metadata),
        **runtime_input_source_state_to_metadata(
            RuntimeInputSourceState(
                source_kind=source_state.source_kind,
                source_active=source_state.source_active,
                command_age_ms=source_state.command_age_ms,
                stale_reason=stale_reason,
            )
        ),
    }

    return replace(
        command,
        target=None,
        joint=None if qpos is None else JointCommand(joint_angles_rad=qpos),
        metadata=metadata,
    )


def build_runtime_input_safety_result(
    command: MotionCommand,
    *,
    source_state: RuntimeInputSourceState,
    current_state: MuJoCoState | None = None,
    timeout_ms: int = DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS,
) -> RuntimeInputSafetyResult:
    if timeout_ms < 0:
        raise ValueError("timeout_ms must be non-negative")

    stale_reason = _derive_stale_reason(source_state, timeout_ms=timeout_ms)
    is_stale = stale_reason is not None

    if is_stale:
        safe_motion_command = _build_hold_motion_command(
            command,
            current_qpos=None if current_state is None else current_state.qpos,
            source_state=source_state,
            stale_reason=stale_reason,
        )
    else:
        safe_motion_command = command

    safe_source_state = RuntimeInputSourceState(
        source_kind=source_state.source_kind,
        source_active=source_state.source_active,
        command_age_ms=source_state.command_age_ms,
        stale_reason=stale_reason,
    )

    return RuntimeInputSafetyResult(
        motion_command=safe_motion_command,
        source_state=safe_source_state,
        is_stale=is_stale,
        stale_reason=stale_reason,
        command_age_ms=source_state.command_age_ms,
    )


__all__ = [
    "DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS",
    "RuntimeInputSafetyResult",
    "build_runtime_input_safety_result",
]
