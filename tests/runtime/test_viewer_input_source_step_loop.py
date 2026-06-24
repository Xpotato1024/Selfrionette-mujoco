from __future__ import annotations

import asyncio

from selfrionette.runtime import (
    build_runtime_input_source_step_loop_plan,
    ingest_viewer_control_message,
    run_runtime_input_source_step_loop,
    select_runtime_input_source,
)
from selfrionette.schemas import ViewerControlKeyboardMessage, ViewerControlMessage


class RecordingPublisher:
    def __init__(self) -> None:
        self.states = []

    async def publish(self, state) -> None:
        self.states.append(state)


class _FakeClock:
    def __init__(self, current_s: float = 0.0) -> None:
        self.current_s = current_s

    def monotonic(self) -> float:
        return self.current_s

    def advance(self, delta_s: float) -> None:
        self.current_s += delta_s


def _build_keyboard_message(timestamp_s: float) -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=("KeyD",),
            key_state={"KeyD": True},
            focus_state="focused",
            zero_state=False,
        ),
    )


def test_viewer_step_loop_accepts_ingested_message_and_updates_endpoint_state() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    plan = build_runtime_input_source_step_loop_plan(selection, publisher=publisher, viewer_clock=clock.monotonic)

    ingest_viewer_control_message(plan.pipeline.input_source, _build_keyboard_message(timestamp_s=1.0))
    records = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))

    desired_endpoint_m = records[0].motion_command.metadata["desired_endpoint_m"]

    assert len(records) == 1
    assert records[0].frame.metadata["source_kind"] == "viewer_keyboard"
    assert records[0].motion_command.metadata["source_kind"] == "viewer_keyboard"
    assert records[0].state.target_position_m == desired_endpoint_m
    assert publisher.states[0].target_position_m == desired_endpoint_m
    assert publisher.states[0].metadata["endpoint_evaluation"]["desired_endpoint_m"] == list(desired_endpoint_m)
    assert publisher.states[0].metadata["endpoint_evaluation"]["fk_endpoint_coordinate_frame"] == "solver-defined frame"


def test_viewer_step_loop_holds_on_stale_source_state() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    plan = build_runtime_input_source_step_loop_plan(selection, publisher=publisher, viewer_clock=clock.monotonic)

    ingest_viewer_control_message(plan.pipeline.input_source, _build_keyboard_message(timestamp_s=1.0))
    clock.advance(0.30)
    records = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))

    assert len(records) == 1
    assert records[0].motion_command.target is None
    assert records[0].motion_command.joint is not None
    assert records[0].motion_command.metadata["stale_reason"] == "source_inactive"
    assert records[0].motion_command.metadata["runtime_input_safety_applied"] is True
    assert "desired_endpoint_m" not in records[0].state.metadata
    assert "target_position_m" not in records[0].state.metadata
    assert records[0].state.metadata["source_kind"] == "viewer_keyboard"
    assert records[0].state.metadata["source_active"] is False
    assert records[0].state.metadata["stale_reason"] == "source_inactive"
