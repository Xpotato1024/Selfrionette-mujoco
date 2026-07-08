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
from selfrionette.schemas import ViewerControlKeyboardMessage, ViewerControlMessage


class _ClockSequence:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = iter(values)

    def monotonic(self) -> float:
        return next(self._values)


def _keyboard_message(timestamp_s: float, *key_codes: str) -> ViewerControlMessage:
    key_state = {key_code: True for key_code in key_codes}
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=key_codes,
            key_state=key_state,
            focus_state="focused",
            zero_state=False,
        ),
    )


class RecordingPublisher:
    def __init__(self) -> None:
        self.states = []

    async def publish(self, state) -> None:
        self.states.append(state)


def _build_plan(clock: _ClockSequence):
    viewer_input_source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=1),
        publisher=RecordingPublisher(),
        viewer_clock=clock.monotonic,
        viewer_input_source=viewer_input_source,
    )
    return viewer_input_source, plan


def test_runtime_step_loop_rebases_viewer_source_to_initial_tip_site_position() -> None:
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)

    initial_state = plan.pipeline.simulator.snapshot()
    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m

    assert viewer_input_source.current_endpoint_m == pytest.approx(initial_tip_site_position_m, abs=1e-12)

    ingest_viewer_control_message(viewer_input_source, _keyboard_message(1.0, "Space"))
    records = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))

    assert records[0].frame.metadata["current_tip_position_m"] == pytest.approx(initial_tip_site_position_m, abs=1e-12)
    assert records[0].frame.metadata["control_frame"] == "world"
    assert records[0].motion_command.metadata["control_frame"] == "world"
    assert records[0].frame.metadata["endpoint_velocity_m_s"] == pytest.approx((0.0, 0.0, 0.1), abs=1e-12)
    assert records[0].motion_command.metadata["local_endpoint_velocity_m_s"] == pytest.approx((0.0, 0.0, 0.1), abs=1e-12)
    assert records[0].motion_command.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx((0.0, 0.0, 0.1), abs=1e-12)
    assert records[0].motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.0, 0.0, 1.0 / 600.0), abs=1e-12)
    assert records[0].motion_command.metadata["endpoint_delta_requested_m"] == pytest.approx((0.0, 0.0, 1.0 / 600.0), abs=1e-12)
    assert records[0].motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert records[0].motion_command.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert records[0].state.metadata["actual_tip_delta_m"][2] > 0.0
    assert dist(initial_state.qpos[:4], records[0].state.qpos[:4]) > 0.0


def test_runtime_step_loop_dt_scales_viewer_endpoint_delta() -> None:
    clock_a = _ClockSequence((0.0, 0.0))
    clock_b = _ClockSequence((0.0, 0.0))
    source_a, plan_a = _build_plan(clock_a)
    source_b, plan_b = _build_plan(clock_b)

    ingest_viewer_control_message(source_a, _keyboard_message(2.0, "KeyW"))
    ingest_viewer_control_message(source_b, _keyboard_message(2.0, "KeyW"))

    record_a = asyncio.run(run_runtime_input_source_step_loop(plan_a, steps=1, dt_s=1.0 / 60.0))[0]
    record_b = asyncio.run(run_runtime_input_source_step_loop(plan_b, steps=1, dt_s=1.0 / 30.0))[0]

    assert record_a.frame.metadata["endpoint_velocity_m_s"][1] == pytest.approx(0.1, abs=1e-12)
    assert record_b.frame.metadata["endpoint_velocity_m_s"][1] == pytest.approx(0.1, abs=1e-12)
    assert record_a.frame.metadata["resolved_world_endpoint_velocity_m_s"][1] == pytest.approx(0.1, abs=1e-12)
    assert record_b.frame.metadata["resolved_world_endpoint_velocity_m_s"][1] == pytest.approx(0.1, abs=1e-12)
    assert record_a.frame.metadata["control_frame"] == "world"
    assert record_b.frame.metadata["control_frame"] == "world"
    assert record_a.motion_command.metadata["endpoint_delta_m"][1] == pytest.approx(1.0 / 600.0, abs=1e-12)
    assert record_b.motion_command.metadata["endpoint_delta_m"][1] == pytest.approx(1.0 / 300.0, abs=1e-12)
    assert record_b.motion_command.metadata["endpoint_delta_m"][1] == pytest.approx(record_a.motion_command.metadata["endpoint_delta_m"][1] * 2.0, abs=1e-12)


def test_runtime_step_loop_holds_keyboard_z_binding_and_updates_target_metadata() -> None:
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)
    initial_state = plan.pipeline.simulator.snapshot()
    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m

    ingest_viewer_control_message(viewer_input_source, _keyboard_message(3.0, "ShiftLeft"))
    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))[0]

    assert record.frame.metadata["axis_values"] == (0.0, 0.0, -1.0)
    assert record.frame.metadata["control_frame"] == "world"
    assert record.frame.metadata["endpoint_velocity_m_s"] == pytest.approx((0.0, 0.0, -0.1), abs=1e-12)
    assert record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx((0.0, 0.0, -0.1), abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.0, 0.0, -1.0 / 600.0), abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_requested_m"][2] < 0.0
    assert record.motion_command.metadata["qpos_before_rad"] == pytest.approx(tuple(initial_state.qpos[:4]), abs=1e-12)
    assert len(record.motion_command.metadata["current_tip_position_m"]) == 3
    assert record.motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert record.motion_command.metadata["motion_rejection_reason"] is None
    assert record.motion_command.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert record.state.metadata["actual_tip_delta_m"][2] < 0.0
    assert record.state.target_position_m == pytest.approx(record.motion_command.metadata["desired_endpoint_m"], abs=1e-12)
    assert record.state.metadata.get("target_rejected") is not True
    assert record.state.metadata["local_motion_policy"] == "finite_difference_jacobian"
    assert record.state.metadata["source_kind"] == "viewer_keyboard"
    assert record.state.metadata["viewer_control_message"]["keyboard"]["active_key_codes"] == ("ShiftLeft",)


def test_runtime_step_loop_uses_tool_frame_when_explicitly_requested() -> None:
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)
    initial_state = plan.pipeline.simulator.snapshot()

    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=5.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyD",),
                key_state={"KeyD": True},
                focus_state="focused",
                zero_state=False,
            ),
            metadata={"control_frame": "tool"},
        ),
    )
    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))[0]

    assert record.frame.metadata["control_frame"] == "tool"
    assert record.motion_command.metadata["control_frame"] == "tool"
    assert record.motion_command.metadata["local_endpoint_velocity_frame"] == "tool"
    assert any(abs(component) > 1e-12 for component in record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"])
    assert record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx(
        record.motion_command.metadata["endpoint_velocity_m_s"],
        abs=1e-12,
    )
    assert record.motion_command.metadata["qpos_delta_norm_rad"] <= 0.2 + 1e-12
    assert dist(initial_state.qpos[:4], record.state.qpos[:4]) > 0.0
    assert record.state.metadata["actual_tip_delta_m"] != pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_runtime_step_loop_stops_after_zero_state_update() -> None:
    clock = _ClockSequence((0.0, 0.0, 0.01, 0.02))
    viewer_input_source, plan = _build_plan(clock)

    ingest_viewer_control_message(viewer_input_source, _keyboard_message(4.0, "KeyD"))
    active_record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))[0]

    ingest_viewer_control_message(
        viewer_input_source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=4.5,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=(),
                key_state={},
                focus_state="focused",
                zero_state=True,
            ),
        ),
    )
    stopped_record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))[0]

    assert active_record.motion_command.metadata["endpoint_delta_m"] != (0.0, 0.0, 0.0)
    assert stopped_record.motion_command.metadata["endpoint_delta_m"] == (0.0, 0.0, 0.0)
    assert stopped_record.motion_command.metadata["motion_status"] == "accepted"
    assert stopped_record.state.metadata["source_active"] is False
    assert stopped_record.state.metadata["actual_tip_delta_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)
