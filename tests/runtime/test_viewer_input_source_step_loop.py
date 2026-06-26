from __future__ import annotations

import asyncio
from math import dist

import pytest

from selfrionette.input_sources import ViewerInputSource
from selfrionette.runtime import (
    build_runtime_input_source_step_loop_plan,
    ingest_viewer_control_message,
    run_runtime_input_source_step_loop,
    select_runtime_input_source,
)
from selfrionette.schemas import (
    ViewerControlGamepadButtonMessage,
    ViewerControlGamepadMessage,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
)


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


def _build_gamepad_message(timestamp_s: float, *, axes: tuple[float, float, float]) -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="gamepad",
        gamepad=ViewerControlGamepadMessage(
            connected=True,
            index=0,
            id="pad-1",
            axes=axes,
            buttons=(
                ViewerControlGamepadButtonMessage(pressed=False, value=0.0),
                ViewerControlGamepadButtonMessage(pressed=False, value=0.0),
            ),
            stale=False,
            zero_state=False,
        ),
    )


def _run_single_viewer_step(plan) -> tuple[object, ...]:
    return asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))


def test_viewer_step_loop_accepts_ingested_message_and_updates_endpoint_state() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    assert plan.pipeline.input_source is viewer_input_source
    ingest_viewer_control_message(viewer_input_source, _build_keyboard_message(timestamp_s=1.0))
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
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    ingest_viewer_control_message(viewer_input_source, _build_keyboard_message(timestamp_s=1.0))
    clock.advance(0.30)
    records = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))

    assert len(records) == 1
    assert records[0].motion_command.target is None
    assert records[0].motion_command.joint is not None
    assert records[0].motion_command.metadata["stale_reason"] == "command_age_ms_exceeded_timeout_250"
    assert records[0].motion_command.metadata["runtime_input_safety_applied"] is True
    assert "desired_endpoint_m" not in records[0].state.metadata
    assert "target_position_m" not in records[0].state.metadata
    assert records[0].state.metadata["source_kind"] == "viewer_keyboard"
    assert records[0].state.metadata["source_active"] is False
    assert records[0].state.metadata["stale_reason"] == "command_age_ms_exceeded_timeout_250"


def test_viewer_step_loop_accepts_off_plane_keyboard_input_without_crashing() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=1.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyW",),
                key_state={"KeyW": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )

    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )
    records = _run_single_viewer_step(plan)

    state = records[0].state
    command = records[0].motion_command

    assert len(records) == 1
    assert command.target is None
    assert command.joint is not None
    assert command.metadata.get("target_rejected") is not True
    assert "target_rejection_reason" not in command.metadata
    assert "target_rejection_message" not in command.metadata
    assert state.metadata.get("target_rejected") is not True
    assert state.metadata["desired_endpoint_m"] == state.target_position_m
    assert state.metadata["target_position_m"] == state.target_position_m
    assert state.target_position_m is not None


def test_viewer_step_loop_rejects_space_shift_boundary_without_crashing() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    rejected_record = None
    for step_index in range(40):
        clock.advance(0.01)
        ingest_viewer_control_message(
            viewer_input_source,
            ViewerControlMessage(
                type="viewer_control_message",
                timestamp_s=1.0 + step_index,
                source_kind="keyboard",
                keyboard=ViewerControlKeyboardMessage(
                    active_key_codes=("Space",),
                    key_state={"Space": True},
                    focus_state="focused",
                    zero_state=False,
                ),
            ),
        )
        records = _run_single_viewer_step(plan)
        if records[0].motion_command.metadata.get("target_rejected"):
            rejected_record = records[0]
            break

    assert rejected_record is not None
    assert rejected_record.motion_command.metadata["target_rejection_reason"] in {
        "invalid_target",
        "target_discontinuous",
    }
    assert rejected_record.state.metadata["target_rejected"] is True
    assert "desired_endpoint_m" not in rejected_record.state.metadata
    assert "target_position_m" not in rejected_record.state.metadata


def test_viewer_step_loop_rejects_repeated_ad_boundary_without_crashing() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    rejected_record = None
    for step_index in range(30):
        clock.advance(0.01)
        ingest_viewer_control_message(
            viewer_input_source,
            ViewerControlMessage(
                type="viewer_control_message",
                timestamp_s=2.0 + step_index,
                source_kind="keyboard",
                keyboard=ViewerControlKeyboardMessage(
                    active_key_codes=("KeyD",),
                    key_state={"KeyD": True},
                    focus_state="focused",
                    zero_state=False,
                ),
            ),
        )
        records = _run_single_viewer_step(plan)
        if records[0].motion_command.metadata.get("target_rejected"):
            rejected_record = records[0]
            break

    assert rejected_record is not None
    assert rejected_record.motion_command.metadata["target_rejected"] is True
    assert rejected_record.state.metadata["target_rejected"] is True
    assert "desired_endpoint_m" not in rejected_record.state.metadata
    assert "target_position_m" not in rejected_record.state.metadata


def test_viewer_step_loop_rejects_gamepad_boundary_without_crashing() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    rejected_record = None
    for step_index in range(30):
        clock.advance(0.01)
        ingest_viewer_control_message(
            viewer_input_source,
            _build_gamepad_message(timestamp_s=3.0 + step_index, axes=(1.0, 0.0, 0.0)),
        )
        records = _run_single_viewer_step(plan)
        if records[0].motion_command.metadata.get("target_rejected"):
            rejected_record = records[0]
            break

    assert rejected_record is not None
    assert rejected_record.state.metadata["source_kind"] == "viewer_gamepad"
    assert rejected_record.motion_command.metadata["target_rejected"] is True
    assert rejected_record.state.metadata["target_rejected"] is True


def test_viewer_step_loop_keeps_first_input_qpos_continuous() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )
    pre_step_state = plan.pipeline.simulator.snapshot()

    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=4.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyA",),
                key_state={"KeyA": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )
    records = _run_single_viewer_step(plan)

    post_step_state = records[0].state

    assert records[0].motion_command.metadata.get("target_rejected") is not True
    assert dist(pre_step_state.qpos[:2], post_step_state.qpos[:2]) < 1.0
    assert post_step_state.metadata["source_kind"] == "viewer_keyboard"
    assert "target_rejected" not in post_step_state.metadata


def test_viewer_step_loop_publishes_active_target_for_keyboard_input() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)

    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=5.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyW",),
                key_state={"KeyW": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )
    records = _run_single_viewer_step(plan)

    state = records[0].state

    assert state.metadata.get("target_rejected") is not True
    assert state.metadata["desired_endpoint_m"] == state.target_position_m
    assert state.metadata["target_position_m"] == state.target_position_m
    assert "rejected_desired_endpoint_m" not in state.metadata


def test_viewer_step_loop_recovers_after_rejected_repeated_ad_input() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    rejected_record = None
    last_valid_endpoint_m = viewer_input_source.current_endpoint_m
    for step_index in range(40):
        clock.advance(0.01)
        ingest_viewer_control_message(
            viewer_input_source,
            ViewerControlMessage(
                type="viewer_control_message",
                timestamp_s=6.0 + step_index,
                source_kind="keyboard",
                keyboard=ViewerControlKeyboardMessage(
                    active_key_codes=("KeyD",),
                    key_state={"KeyD": True},
                    focus_state="focused",
                    zero_state=False,
                ),
            ),
        )
        records = _run_single_viewer_step(plan)
        if records[0].motion_command.metadata.get("target_rejected"):
            rejected_record = records[0]
            break
        last_valid_endpoint_m = records[0].state.target_position_m

    assert rejected_record is not None
    assert viewer_input_source.current_endpoint_m != rejected_record.motion_command.metadata["rejected_desired_endpoint_m"]
    assert viewer_input_source.current_endpoint_m in {(0.6, 0.0, 0.1), last_valid_endpoint_m}

    clock.advance(0.01)
    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=60.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyA",),
                key_state={"KeyA": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )
    recovery_records = _run_single_viewer_step(plan)

    assert recovery_records[0].motion_command.metadata.get("target_rejected") is not True
    assert recovery_records[0].state.target_position_m is not None
    assert recovery_records[0].state.target_position_m != last_valid_endpoint_m
    assert viewer_input_source.current_endpoint_m == recovery_records[0].state.target_position_m


def test_viewer_step_loop_recovers_after_rejected_vertical_input() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    rejected_record = None
    for step_index in range(40):
        clock.advance(0.01)
        ingest_viewer_control_message(
            viewer_input_source,
            ViewerControlMessage(
                type="viewer_control_message",
                timestamp_s=7.0 + step_index,
                source_kind="keyboard",
                keyboard=ViewerControlKeyboardMessage(
                    active_key_codes=("Space",),
                    key_state={"Space": True},
                    focus_state="focused",
                    zero_state=False,
                ),
            ),
        )
        records = _run_single_viewer_step(plan)
        if records[0].motion_command.metadata.get("target_rejected"):
            rejected_record = records[0]
            break

    assert rejected_record is not None
    rejected_endpoint_m = rejected_record.motion_command.metadata["rejected_desired_endpoint_m"]
    assert viewer_input_source.current_endpoint_m != rejected_endpoint_m

    clock.advance(0.01)
    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=8.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyD",),
                key_state={"KeyD": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )
    recovery_records = _run_single_viewer_step(plan)

    assert recovery_records[0].motion_command.metadata.get("target_rejected") is not True
    assert recovery_records[0].state.target_position_m is not None
    assert viewer_input_source.current_endpoint_m == recovery_records[0].state.target_position_m
    assert recovery_records[0].state.target_position_m != rejected_record.state.target_position_m


def test_viewer_step_loop_rejects_external_viewer_source_for_non_viewer_selection() -> None:
    selection = select_runtime_input_source("programmed_target", steps=1)
    viewer_input_source = ViewerInputSource(clock=lambda: 0.0)

    with pytest.raises(ValueError, match="viewer_input_source can only be supplied"):
        build_runtime_input_source_step_loop_plan(
            selection,
            viewer_input_source=viewer_input_source,
        )
