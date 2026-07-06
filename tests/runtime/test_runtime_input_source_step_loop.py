from __future__ import annotations

import asyncio
from math import dist

import pytest

from selfrionette.input_sources import ViewerInputSource
from selfrionette.mujoco_backend import (
    extract_fast_arm_base_link_position_from_state,
    extract_fast_arm_tip_site_endpoint_from_state,
)
from selfrionette.runtime import (
    build_runtime_input_source_step_loop_plan,
    ingest_viewer_control_message,
    run_runtime_input_source_step_loop,
    select_runtime_input_source,
)
from selfrionette.schemas import ViewerControlKeyboardMessage, ViewerControlMessage
from selfrionette.transport.stubs import NoOpStatePublisher


class _FakeClock:
    def __init__(self, current_s: float = 0.0) -> None:
        self.current_s = current_s

    def monotonic(self) -> float:
        return self.current_s


def _keyboard_message(key_code: str) -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=1.0,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=(key_code,),
            key_state={key_code: True},
            focus_state="focused",
            zero_state=False,
        ),
    )


def _run_one_step(plan) -> object:
    return asyncio.run(
        run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0)
    )[0]


def test_viewer_runtime_loop_rebases_first_input_to_initial_tip_site_position() -> None:
    clock = _FakeClock()
    source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=1),
        publisher=NoOpStatePublisher(),
        viewer_clock=clock.monotonic,
        viewer_input_source=source,
    )
    initial_state = plan.pipeline.simulator.snapshot()
    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(
        initial_state
    ).position_m
    initial_base_link_position_m = extract_fast_arm_base_link_position_from_state(initial_state)

    ingest_viewer_control_message(source, _keyboard_message("Space"))
    record = _run_one_step(plan)

    assert tuple(initial_state.qpos[:4]) == pytest.approx(
        (0.0, -1.5707963267948966, 0.0, 0.0),
        abs=1e-12,
    )
    assert initial_tip_site_position_m == pytest.approx((0.622, 0.0, 0.7), abs=1e-9)
    assert record.frame.metadata["current_tip_position_m"] == pytest.approx(
        initial_tip_site_position_m,
        abs=1e-9,
    )
    assert record.frame.metadata["desired_endpoint_m"] == pytest.approx(
        (initial_tip_site_position_m[0], initial_tip_site_position_m[1], initial_tip_site_position_m[2] + 0.01),
        abs=1e-12,
    )
    assert record.frame.metadata["desired_endpoint_m"] != (0.6, 0.0, 0.11)
    assert record.motion_command.metadata["ik_target_endpoint_m"] == pytest.approx(
        (
            initial_tip_site_position_m[0] - initial_base_link_position_m[0],
            initial_tip_site_position_m[1] - initial_base_link_position_m[1],
            initial_tip_site_position_m[2] - initial_base_link_position_m[2] + 0.01,
        ),
        abs=1e-12,
    )
    assert record.motion_command.metadata["target_rejected"] is True
    assert record.motion_command.metadata["target_rejection_reason"] == "target_discontinuous"
    assert record.motion_command.metadata["target_rejection_message"].startswith(
        "candidate qpos exceeds the viewer endpoint continuity threshold"
    )
    assert record.motion_command.metadata["qpos_before_ik_rad"] == pytest.approx(
        tuple(initial_state.qpos[:4]),
        abs=1e-12,
    )
    assert record.motion_command.metadata["ik_output_qpos_rad"] == pytest.approx(
        (-3.5811621840715073e-13, -0.4201823747665194, 0.585645549824969, 0.17374725940673852),
        abs=1e-9,
    )
    assert record.motion_command.metadata["qpos_discontinuity_norm_rad"] > 1.0
    assert record.motion_command.metadata["qpos_discontinuity_norm_rad"] == pytest.approx(1.3027207247846728, abs=1e-9)
    assert record.motion_command.metadata["target_discontinuity_threshold_rad"] == pytest.approx(0.2, abs=1e-12)
    assert dist(initial_state.qpos[:4], record.state.qpos[:4]) == pytest.approx(0.0, abs=1e-12)
    assert record.state.target_position_m == pytest.approx(
        initial_tip_site_position_m,
        abs=1e-12,
    )


@pytest.mark.parametrize(
    ("key_code", "expected_z_delta_m"),
    (
        ("Space", 0.01),
        ("ShiftLeft", -0.01),
        ("ShiftRight", -0.01),
    ),
)
def test_viewer_runtime_loop_preserves_keyboard_z_axis_delta(
    key_code: str,
    expected_z_delta_m: float,
) -> None:
    clock = _FakeClock()
    source = ViewerInputSource(clock=clock.monotonic)
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=1),
        publisher=NoOpStatePublisher(),
        viewer_clock=clock.monotonic,
        viewer_input_source=source,
    )
    initial_tip_site_position_m = extract_fast_arm_tip_site_endpoint_from_state(
        plan.pipeline.simulator.snapshot()
    ).position_m
    initial_base_link_position_m = extract_fast_arm_base_link_position_from_state(
        plan.pipeline.simulator.snapshot()
    )

    ingest_viewer_control_message(source, _keyboard_message(key_code))
    record = _run_one_step(plan)

    assert record.frame.metadata["endpoint_delta_m"] == (0.0, 0.0, expected_z_delta_m)
    assert record.motion_command.metadata["ik_target_endpoint_m"] == pytest.approx(
        (
            initial_tip_site_position_m[0] - initial_base_link_position_m[0],
            initial_tip_site_position_m[1] - initial_base_link_position_m[1],
            initial_tip_site_position_m[2] - initial_base_link_position_m[2] + expected_z_delta_m,
        ),
        abs=1e-12,
    )
    if record.motion_command.metadata.get("target_rejected"):
        assert record.motion_command.metadata["target_rejection_reason"] == "target_discontinuous"
        assert record.motion_command.metadata["qpos_discontinuity_norm_rad"] > 0.2
        assert record.state.target_position_m == pytest.approx(initial_tip_site_position_m, abs=1e-12)
    else:
        assert record.motion_command.metadata["qpos_discontinuity_norm_rad"] <= 0.2
        assert record.state.target_position_m == pytest.approx(
            record.frame.metadata["desired_endpoint_m"],
            abs=1e-12,
        )
    assert record.motion_command.metadata["endpoint_delta_m"] == (0.0, 0.0, expected_z_delta_m)
    assert record.motion_command.metadata["qpos_discontinuity_norm_rad"] > 0.0
