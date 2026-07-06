from __future__ import annotations

import asyncio
from math import dist

import pytest

from selfrionette.input_sources import ViewerInputSource
from selfrionette.mujoco_backend import extract_fast_arm_tip_site_endpoint_from_state
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


def _build_keyboard_message(timestamp_s: float, key_code: str = "KeyD") -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=(key_code,),
            key_state={key_code: True},
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

    desired_endpoint_m = records[0].frame.metadata["desired_endpoint_m"]

    assert len(records) == 1
    assert records[0].frame.metadata["source_kind"] == "viewer_keyboard"
    assert records[0].motion_command.metadata["source_kind"] == "viewer_keyboard"
    assert records[0].frame.metadata["current_tip_position_m"] == pytest.approx((0.622, 0.0, 0.7), abs=1e-9)
    assert desired_endpoint_m == pytest.approx((0.632, 0.0, 0.7), abs=1e-9)
    assert records[0].motion_command.metadata["target_rejected"] is True
    assert records[0].motion_command.metadata["target_rejection_reason"] == "target_unreachable"
    assert records[0].motion_command.metadata["rejected_desired_endpoint_m"] == desired_endpoint_m
    assert publisher.states[0].target_position_m == pytest.approx((0.622, 0.0, 0.7), abs=1e-9)


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
    assert records[0].frame.metadata["current_tip_position_m"] == (0.6, 0.0, 0.1)
    assert command.joint is not None
    assert command.metadata.get("target_rejected") is not True
    assert command.metadata["endpoint_delta_m"] == (0.0, 0.01, 0.0)
    assert command.metadata["qpos_before_ik_rad"] == pytest.approx((0.0, -1.5707963267948966, 0.0, 0.0), abs=1e-12)
    assert len(command.metadata["ik_output_qpos_rad"]) == 4
    assert command.metadata["qpos_discontinuity_norm_rad"] < 2.0
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
        "target_unreachable",
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

    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(pre_step_state).position_m
    assert viewer_input_source.current_endpoint_m == pytest.approx(initial_tip_site_position_m, abs=1e-9)
    assert records[0].frame.metadata["current_tip_position_m"] == pytest.approx(initial_tip_site_position_m, abs=1e-9)
    assert records[0].frame.metadata["desired_endpoint_m"] != (0.59, 0.0, 0.1)
    assert records[0].motion_command.metadata["target_rejected"] is True
    assert records[0].motion_command.metadata["target_rejection_reason"] == "target_unreachable"
    assert dist(pre_step_state.qpos[:4], post_step_state.qpos[:4]) == pytest.approx(0.0, abs=1e-12)
    assert post_step_state.metadata["source_kind"] == "viewer_keyboard"
    assert post_step_state.metadata["target_rejected"] is True


@pytest.mark.parametrize(
    ("key_code", "expected_z_delta_m"),
    (
        ("Space", 0.01),
        ("ShiftLeft", -0.01),
        ("ShiftRight", -0.01),
    ),
)
def test_viewer_step_loop_preserves_keyboard_z_axis_delta_after_initial_tip_rebase(
    key_code: str,
    expected_z_delta_m: float,
) -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=1)
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=RecordingPublisher(),
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )
    initial_state = plan.pipeline.simulator.snapshot()
    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m

    ingest_viewer_control_message(
        viewer_input_source,
        _build_keyboard_message(timestamp_s=4.5, key_code=key_code),
    )
    records = _run_single_viewer_step(plan)
    record = records[0]

    assert viewer_input_source.current_endpoint_m == pytest.approx(initial_tip_site_position_m, abs=1e-9)
    assert record.frame.metadata["current_tip_position_m"] == pytest.approx(initial_tip_site_position_m, abs=1e-9)
    assert record.frame.metadata["endpoint_delta_m"] == (0.0, 0.0, expected_z_delta_m)
    assert record.frame.metadata["desired_endpoint_m"][2] == pytest.approx(
        initial_tip_site_position_m[2] + expected_z_delta_m,
        abs=1e-12,
    )
    assert record.motion_command.metadata["endpoint_delta_m"] == (0.0, 0.0, expected_z_delta_m)
    assert record.motion_command.metadata["rejected_desired_endpoint_m"][2] == pytest.approx(
        initial_tip_site_position_m[2] + expected_z_delta_m,
        abs=1e-12,
    )
    assert record.motion_command.metadata["target_rejection_reason"] == "target_unreachable"
    assert dist(initial_state.qpos[:4], record.state.qpos[:4]) == pytest.approx(0.0, abs=1e-12)


def test_viewer_step_loop_keeps_repeated_small_inputs_continuous_and_nonzero_fast_arm_qpos() -> None:
    clock = _FakeClock()
    selection = select_runtime_input_source("viewer", steps=3)
    publisher = RecordingPublisher()
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        selection,
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )

    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=9.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyD",),
                key_state={"KeyD": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )

    previous_qpos = plan.pipeline.simulator.snapshot().qpos
    for _ in range(3):
        clock.advance(0.01)
        records = _run_single_viewer_step(plan)
        state = records[0].state

        assert records[0].motion_command.metadata["target_rejected"] is True
        assert len(state.qpos[:4]) == 4
        assert dist(previous_qpos[:4], state.qpos[:4]) == pytest.approx(0.0, abs=1e-12)
        previous_qpos = state.qpos


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

    assert records[0].frame.metadata["current_tip_position_m"] == (0.6, 0.0, 0.1)
    assert state.metadata.get("target_rejected") is not True
    assert state.metadata["desired_endpoint_m"] == state.target_position_m
    assert state.metadata["target_position_m"] == state.target_position_m
    assert "rejected_desired_endpoint_m" not in state.metadata


def test_viewer_step_loop_keeps_rebased_endpoint_after_rejected_repeated_ad_input() -> None:
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

    assert recovery_records[0].motion_command.metadata["target_rejected"] is True
    assert recovery_records[0].state.target_position_m == last_valid_endpoint_m
    assert viewer_input_source.current_endpoint_m == last_valid_endpoint_m


def test_viewer_step_loop_keeps_rebased_endpoint_after_rejected_vertical_input() -> None:
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

    assert recovery_records[0].motion_command.metadata["target_rejected"] is True
    assert viewer_input_source.current_endpoint_m == rejected_record.state.target_position_m
    assert recovery_records[0].state.target_position_m == rejected_record.state.target_position_m


def test_viewer_step_loop_rejects_external_viewer_source_for_non_viewer_selection() -> None:
    selection = select_runtime_input_source("programmed_target", steps=1)
    viewer_input_source = ViewerInputSource(clock=lambda: 0.0)

    with pytest.raises(ValueError, match="viewer_input_source can only be supplied"):
        build_runtime_input_source_step_loop_plan(
            selection,
            viewer_input_source=viewer_input_source,
        )
