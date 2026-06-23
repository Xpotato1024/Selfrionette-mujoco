from __future__ import annotations

import asyncio

import pytest

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime import (
    DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS,
    RuntimeInputSourceSelection,
    build_runtime_input_safety_result,
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.runtime.input_source_state import build_runtime_input_source_state
from selfrionette.schemas import MotionCommand, RawInputFrame


class RecordingPublisher:
    def __init__(self) -> None:
        self.states = []

    async def publish(self, state) -> None:
        self.states.append(state)


def _build_replay_selection(frame: RawInputFrame) -> RuntimeInputSourceSelection:
    return RuntimeInputSourceSelection(
        source_name="replay",
        frames=(frame,),
        loop=True,
        initial_metadata=dict(frame.metadata),
    )


def test_fresh_runtime_input_safety_result_leaves_motion_command_unchanged() -> None:
    command = MotionCommand(
        timestamp_s=1.0,
        metadata={
            "source_kind": "replay",
            "desired_endpoint_m": (0.4, 0.0, 0.6),
        },
    )
    source_state = build_runtime_input_source_state(
        "replay",
        source_active=True,
        command_age_ms=0,
    )

    result = build_runtime_input_safety_result(command, source_state=source_state)

    assert result.is_stale is False
    assert result.stale_reason is None
    assert result.command_age_ms == 0
    assert result.motion_command is command


def test_stale_runtime_input_safety_result_holds_current_qpos_deterministically() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    current_state = simulator.snapshot()
    command = MotionCommand(
        timestamp_s=1.0,
        metadata={
            "source_kind": "replay",
            "desired_endpoint_m": (0.7, 0.0, 0.6),
        },
    )
    source_state = build_runtime_input_source_state(
        "replay",
        source_active=True,
        command_age_ms=DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS + 1,
    )

    result = build_runtime_input_safety_result(
        command,
        source_state=source_state,
        current_state=current_state,
    )

    assert result.is_stale is True
    assert result.stale_reason == f"command_age_ms_exceeded_timeout_{DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS}"
    assert result.motion_command is not command
    assert result.motion_command.target is None
    assert result.motion_command.joint is not None
    assert result.motion_command.joint.joint_angles_rad == pytest.approx(current_state.qpos)
    assert result.motion_command.metadata["source_kind"] == "replay"
    assert result.motion_command.metadata["command_age_ms"] == DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS + 1
    assert result.motion_command.metadata["stale_reason"] == result.stale_reason


def test_inactive_source_transitions_to_safe_hold_in_step_loop_metadata() -> None:
    frame = RawInputFrame(
        source="replay",
        timestamp_s=2.0,
        metadata={
            "source_kind": "replay",
            "source_active": False,
            "command_age_ms": 0,
            "desired_endpoint_m": (0.5, 0.0, 0.5),
        },
    )
    selection = _build_replay_selection(frame)
    publisher = RecordingPublisher()
    plan = build_runtime_input_source_step_loop_plan(selection, publisher=publisher)

    records = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))

    assert len(records) == 1
    assert records[0].motion_command.target is None
    assert records[0].motion_command.joint is not None
    assert publisher.states[0].qpos[: len(records[0].motion_command.joint.joint_angles_rad)] == pytest.approx(
        records[0].motion_command.joint.joint_angles_rad
    )
    assert records[0].state.metadata["source_active"] is False
    assert records[0].state.metadata["command_age_ms"] == 0
    assert records[0].state.metadata["stale_reason"] == "source_inactive"
    assert publisher.states[0].metadata["stale_reason"] == "source_inactive"
