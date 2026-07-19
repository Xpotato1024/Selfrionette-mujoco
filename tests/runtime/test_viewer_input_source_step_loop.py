from __future__ import annotations

from selfrionette.plugins.robots.fast_arm.adapter.endpoint import extract_fast_arm_tip_site_endpoint_from_state

import asyncio
from math import dist

import pytest

from selfrionette.input_sources import ViewerInputSource
from selfrionette.runtime.execution.input_step_loop import (
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.runtime.control.viewer_control_ingress import ingest_viewer_control_message
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.schemas import ViewerControlKeyboardMessage, ViewerControlMessage
from tests.support.transport_doubles import NoOpStatePublisher


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


def _run_single_viewer_step(plan, *, dt_s: float) -> object:
    return asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=dt_s))[0]


def _build_viewer_plan(clock: _ClockSequence, *, steps: int = 1):
    source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=steps),
        publisher=NoOpStatePublisher(),
        viewer_clock=clock.monotonic,
        viewer_input_source=source,
    )
    return source, plan


def test_viewer_step_loop_accepts_continuous_keyboard_motion_with_small_bounded_qpos_delta() -> None:
    clock = _ClockSequence((0.0, 0.0))
    source, plan = _build_viewer_plan(clock)
    initial_state = plan.pipeline.simulator.snapshot()
    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m

    ingest_viewer_control_message(source, _keyboard_message(1.0, "KeyD"))
    record = _run_single_viewer_step(plan, dt_s=1.0 / 60.0)

    assert record.frame.metadata["intent_kind"] == "local_endpoint_velocity"
    assert record.frame.metadata["input_continuity"] == "continuous"
    assert record.frame.metadata["control_frame"] == "world"
    assert record.frame.metadata["axis_values"] == pytest.approx((1.0, 0.0, 0.0), abs=1e-12)
    assert record.frame.metadata["endpoint_velocity_m_s"] == pytest.approx((0.1, 0.0, 0.0), abs=1e-12)
    assert record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx((0.1, 0.0, 0.0), abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_m"] == pytest.approx((1.0 / 600.0, 0.0, 0.0), abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_requested_m"] == pytest.approx((1.0 / 600.0, 0.0, 0.0), abs=1e-12)
    assert record.motion_command.metadata["local_motion_policy"] == "finite_difference_jacobian"
    assert record.motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert record.motion_command.metadata["qpos_delta_norm_rad"] <= 0.2 + 1e-12
    assert record.motion_command.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert record.state.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert record.motion_command.metadata["endpoint_velocity_m_s"][0] > 0.0
    assert record.state.metadata["actual_tip_delta_m"][0] > 0.0
    assert record.state.metadata["endpoint_progress_status"] == "progressing"
    assert record.state.metadata["motion_status"] == record.motion_command.metadata["motion_status"]
    post_step_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(record.state).position_m
    expected_actual_tip_delta_m = tuple(
        post_step_tip_site_position_m[index] - initial_tip_site_position_m[index]
        for index in range(3)
    )
    assert record.state.metadata["actual_tip_delta_m"] == pytest.approx(
        expected_actual_tip_delta_m,
        abs=0.0,
    )
    assert dist(initial_state.qpos[:4], record.state.qpos[:4]) > 0.0
    assert dist(initial_state.qpos[:4], record.state.qpos[:4]) <= 0.2 + 1e-12
    assert record.state.target_position_m is not None
    assert source.current_endpoint_m == pytest.approx(record.state.target_position_m, abs=1e-12)
    assert record.frame.metadata["current_tip_position_m"] == pytest.approx(initial_tip_site_position_m, abs=1e-12)


@pytest.mark.parametrize(
    ("key_code", "expected_axis_index", "expected_sign"),
    (
        ("KeyD", 0, 1.0),
        ("KeyA", 0, -1.0),
        ("KeyW", 1, 1.0),
        ("KeyS", 1, -1.0),
        ("Space", 2, 1.0),
        ("ShiftLeft", 2, -1.0),
    ),
)
def test_viewer_step_loop_world_frame_preserves_keyboard_axis_mapping(
    key_code: str,
    expected_axis_index: int,
    expected_sign: float,
) -> None:
    clock = _ClockSequence((0.0, 0.0))
    source, plan = _build_viewer_plan(clock)

    ingest_viewer_control_message(source, _keyboard_message(2.0, key_code))
    record = _run_single_viewer_step(plan, dt_s=1.0 / 60.0)

    assert record.frame.metadata["control_frame"] == "world"
    assert record.frame.metadata["axis_values"][expected_axis_index] == pytest.approx(expected_sign, abs=1e-12)
    assert record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"][expected_axis_index] == pytest.approx(
        expected_sign * 0.1,
        abs=1e-12,
    )
    assert record.motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert record.state.metadata["actual_tip_delta_m"][expected_axis_index] * expected_sign > 0.0
    assert record.state.metadata["endpoint_progress_status"] == "progressing"


@pytest.mark.parametrize(
    ("key_code", "expected_z_sign"),
    (
        ("Space", 1.0),
        ("ShiftLeft", -1.0),
        ("ShiftRight", -1.0),
    ),
)
def test_viewer_step_loop_preserves_keyboard_z_axis_binding(
    key_code: str,
    expected_z_sign: float,
) -> None:
    clock = _ClockSequence((0.0, 0.0))
    source, plan = _build_viewer_plan(clock)

    ingest_viewer_control_message(source, _keyboard_message(2.0, key_code))
    record = _run_single_viewer_step(plan, dt_s=1.0 / 60.0)

    assert record.frame.metadata["axis_values"][0] == pytest.approx(0.0, abs=1e-12)
    assert record.frame.metadata["axis_values"][1] == pytest.approx(0.0, abs=1e-12)
    assert record.frame.metadata["axis_values"][2] == pytest.approx(expected_z_sign, abs=1e-12)
    assert record.frame.metadata["control_frame"] == "world"
    assert record.frame.metadata["endpoint_velocity_m_s"][2] == pytest.approx(expected_z_sign * 0.1, abs=1e-12)
    assert record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"][2] == pytest.approx(
        expected_z_sign * 0.1,
        abs=1e-12,
    )
    assert record.motion_command.metadata["endpoint_delta_m"][2] == pytest.approx(expected_z_sign / 600.0, abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_requested_m"][2] == pytest.approx(expected_z_sign / 600.0, abs=1e-12)
    assert record.motion_command.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert record.state.metadata["actual_tip_delta_m"][2] * expected_z_sign > 0.0


def test_viewer_step_loop_dt_scales_endpoint_delta() -> None:
    source_fast, plan_fast = _build_viewer_plan(_ClockSequence((0.0, 0.0)))
    source_slow, plan_slow = _build_viewer_plan(_ClockSequence((0.0, 0.0)))

    ingest_viewer_control_message(source_fast, _keyboard_message(3.0, "KeyW"))
    ingest_viewer_control_message(source_slow, _keyboard_message(3.0, "KeyW"))

    fast_record = _run_single_viewer_step(plan_fast, dt_s=1.0 / 60.0)
    slow_record = _run_single_viewer_step(plan_slow, dt_s=1.0 / 30.0)

    assert fast_record.motion_command.metadata["endpoint_delta_requested_m"][1] == pytest.approx(1.0 / 600.0, abs=1e-12)
    assert slow_record.motion_command.metadata["endpoint_delta_requested_m"][1] == pytest.approx(1.0 / 300.0, abs=1e-12)
    assert slow_record.motion_command.metadata["endpoint_delta_requested_m"][1] == pytest.approx(
        fast_record.motion_command.metadata["endpoint_delta_requested_m"][1] * 2.0,
        abs=1e-12,
    )


@pytest.mark.parametrize("key_code", ("Space", "KeyW", "KeyA", "KeyD"))
def test_viewer_step_loop_holds_motion_without_repeated_keydown_until_keyup(
    key_code: str,
) -> None:
    clock = _ClockSequence((0.0, 0.0, 0.01, 0.02, 0.03, 0.04))
    source, plan = _build_viewer_plan(clock, steps=4)

    ingest_viewer_control_message(source, _keyboard_message(4.0, key_code))
    records = asyncio.run(run_runtime_input_source_step_loop(plan, steps=3, dt_s=1.0 / 60.0))

    assert len(records) == 3
    assert records[0].motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert records[1].motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert records[2].motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert all(
        record.motion_command.metadata["qpos_delta_norm_rad"] <= 0.2 + 1e-12
        for record in records
    )
    assert records[0].state.qpos[:4] != records[1].state.qpos[:4]
    assert records[1].state.qpos[:4] != records[2].state.qpos[:4]
    assert any(abs(component) > 1e-12 for component in records[0].state.metadata["actual_tip_delta_m"])
    assert any(abs(component) > 1e-12 for component in records[1].state.metadata["actual_tip_delta_m"])
    assert any(abs(component) > 1e-12 for component in records[2].state.metadata["actual_tip_delta_m"])

    ingest_viewer_control_message(
        source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=5.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=(),
                key_state={},
                focus_state="focused",
                zero_state=True,
            ),
        ),
    )
    stopped_record = _run_single_viewer_step(plan, dt_s=1.0 / 60.0)

    assert stopped_record.motion_command.metadata["motion_status"] == "accepted"
    assert stopped_record.state.metadata["endpoint_progress_status"] == "not_requested"
    assert stopped_record.motion_command.metadata["endpoint_delta_m"] == (0.0, 0.0, 0.0)
    assert stopped_record.state.metadata["actual_tip_delta_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_viewer_step_loop_scales_large_dt_boundary_motion() -> None:
    clock = _ClockSequence((0.0, 0.0))
    source, plan = _build_viewer_plan(clock)

    ingest_viewer_control_message(source, _keyboard_message(6.0, "KeyD"))
    record = _run_single_viewer_step(plan, dt_s=1.0)

    assert record.frame.metadata["endpoint_velocity_m_s"] == pytest.approx((0.1, 0.0, 0.0), abs=1e-12)
    assert record.frame.metadata["control_frame"] == "world"
    assert record.motion_command.metadata["motion_status"] == "scaled"
    assert record.motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.01, 0.0, 0.0), abs=1e-12)
    assert record.motion_command.metadata["motion_rejection_reason"] is None
