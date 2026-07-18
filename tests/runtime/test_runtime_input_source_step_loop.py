from __future__ import annotations

import asyncio
from math import dist

import pytest

import selfrionette.runtime.execution.input_step_loop as input_step_loop
from selfrionette.input_sources import ViewerInputSource
from selfrionette.plugins.catalog import resolve_robot_bundle
from selfrionette.plugins.robots.fast_arm.endpoint import extract_fast_arm_tip_site_endpoint_from_state
from selfrionette.plugins.robots.fast_arm.profile import FAST_ARM_ROBOT_PROFILE
from selfrionette.runtime.execution.input_step_loop import (
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.runtime.control.viewer_control_ingress import ingest_viewer_control_message
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.runtime.composition.robot_bundle import (
    ENDPOINT_COMMAND_V1,
    ENDPOINT_POSE_V1,
    QPOS_FEASIBILITY_V1,
)
from selfrionette.schemas import (
    RawInputFrame,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
)


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


def test_runtime_first_state_payload_rebase_and_marker_share_canonical_pose() -> None:
    clock = _ClockSequence((0.0,))
    source = ViewerInputSource(clock=clock.monotonic)
    publisher = RecordingPublisher()
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=1),
        publisher=publisher,
        viewer_clock=clock.monotonic,
        viewer_input_source=source,
    )
    initial_state = plan.pipeline.simulator.snapshot()
    canonical_qpos = tuple(
        plan.pipeline.simulator.model.key(FAST_ARM_ROBOT_PROFILE.initial_keyframe_name).qpos
    )
    initial_tip = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m

    records = asyncio.run(
        run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0)
    )

    assert initial_state.qpos == pytest.approx(canonical_qpos)
    assert records[0].state.qpos == pytest.approx(canonical_qpos)
    assert records[0].state.target_position_m == pytest.approx(initial_tip)
    assert source.current_endpoint_m == pytest.approx(initial_tip)
    assert publisher.states[0].qpos == pytest.approx(canonical_qpos)
    assert publisher.states[0].target_position_m == pytest.approx(initial_tip)


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
    assert records[0].frame.metadata["endpoint_velocity_m_s"] == pytest.approx(
        (0.0, 0.0, 0.1), abs=1e-12
    )
    assert records[0].motion_command.metadata[
        "local_endpoint_velocity_m_s"
    ] == pytest.approx((0.0, 0.0, 0.1), abs=1e-12)
    assert records[0].motion_command.metadata[
        "resolved_world_endpoint_velocity_m_s"
    ] == pytest.approx((0.0, 0.0, 0.1), abs=1e-12)
    assert records[0].motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.0, 0.0, 1.0 / 600.0), abs=1e-12)
    assert records[0].motion_command.metadata[
        "endpoint_delta_requested_m"
    ] == pytest.approx((0.0, 0.0, 1.0 / 600.0), abs=1e-12)
    assert records[0].motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert records[0].state.metadata["endpoint_progress_status"] == "progressing"
    assert records[0].state.metadata["endpoint_progress_ratio"] > 0.5
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
    assert record_b.frame.metadata[
        "resolved_world_endpoint_velocity_m_s"
    ][1] == pytest.approx(0.1, abs=1e-12)
    assert record_a.frame.metadata["control_frame"] == "world"
    assert record_b.frame.metadata["control_frame"] == "world"
    assert record_a.motion_command.metadata["endpoint_delta_m"][1] == pytest.approx(1.0 / 600.0, abs=1e-12)
    assert record_b.motion_command.metadata["endpoint_delta_m"][1] == pytest.approx(1.0 / 300.0, abs=1e-12)
    assert record_b.motion_command.metadata["endpoint_delta_m"][1] == pytest.approx(
        record_a.motion_command.metadata["endpoint_delta_m"][1] * 2.0,
        abs=1e-12,
    )


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
    assert record.motion_command.metadata[
        "resolved_world_endpoint_velocity_m_s"
    ] == pytest.approx((0.0, 0.0, -0.1), abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.0, 0.0, -1.0 / 600.0), abs=1e-12)
    assert record.motion_command.metadata["endpoint_delta_requested_m"][2] < 0.0
    assert record.motion_command.metadata["qpos_before_rad"] == pytest.approx(
        tuple(initial_state.qpos[:4]), abs=1e-12
    )
    assert len(record.motion_command.metadata["current_tip_position_m"]) == 3
    assert record.motion_command.metadata["motion_status"] in {"accepted", "scaled"}
    assert record.motion_command.metadata["motion_rejection_reason"] is None
    assert record.motion_command.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert record.state.metadata["actual_tip_delta_m"][2] < 0.0
    assert record.state.metadata["endpoint_progress_status"] == "progressing"
    assert record.state.target_position_m == pytest.approx(
        record.motion_command.metadata["desired_endpoint_m"], abs=1e-12
    )
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
    assert any(
        abs(component) > 1e-12
        for component in record.motion_command.metadata[
            "resolved_world_endpoint_velocity_m_s"
        ]
    )
    assert record.motion_command.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx(
        record.motion_command.metadata["endpoint_velocity_m_s"],
        abs=1e-12,
    )
    assert record.motion_command.metadata["qpos_delta_norm_rad"] <= 0.2 + 1e-12
    assert dist(initial_state.qpos[:4], record.state.qpos[:4]) > 0.0
    assert record.state.metadata["actual_tip_delta_m"] != pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_runtime_step_loop_holds_when_tool_orientation_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)
    initial_state = plan.pipeline.simulator.snapshot()

    monkeypatch.setattr(
        input_step_loop,
        "_extract_endpoint_orientation_wxyz_from_state",
        lambda state, plugin: None,
    )
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

    assert record.motion_command.metadata["requested_control_frame"] == "tool"
    assert record.motion_command.metadata["resolved_control_frame"] is None
    assert record.motion_command.metadata["control_frame_resolution_status"] == "tool_orientation_unavailable"
    assert record.motion_command.metadata["motion_status"] == "held"
    assert record.motion_command.metadata["motion_rejection_reason"] == "tip_orientation_missing"
    assert record.motion_command.metadata["candidate_qpos_rad"] == pytest.approx(initial_state.qpos, abs=1e-12)
    assert "resolved_world_endpoint_velocity_m_s" not in record.motion_command.metadata
    assert record.motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)
    assert record.state.metadata["actual_tip_delta_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_runtime_step_loop_converts_scalar_tool_orientation_to_safe_hold(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)
    initial_state = plan.pipeline.simulator.snapshot()

    monkeypatch.setattr(
        input_step_loop,
        "_extract_endpoint_orientation_wxyz_from_state",
        lambda state, plugin: 7.0,
    )
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

    assert record.motion_command.metadata["control_frame_resolution_status"] == "tool_orientation_unavailable"
    assert record.motion_command.metadata["control_frame_resolution_reason"] == "tip_orientation_shape_invalid"
    assert record.motion_command.metadata["motion_status"] == "held"
    assert record.motion_command.metadata["candidate_qpos_rad"] == pytest.approx(initial_state.qpos, abs=1e-12)
    assert "resolved_world_endpoint_velocity_m_s" not in record.motion_command.metadata
    assert "endpoint_velocity_m_s" not in record.motion_command.metadata
    assert "endpoint_velocity_frame" not in record.motion_command.metadata
    assert record.motion_command.metadata["endpoint_delta_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)
    assert record.state.metadata["motion_status"] == "held"
    assert "resolved_world_endpoint_velocity_m_s" not in record.state.metadata
    assert "endpoint_velocity_m_s" not in record.state.metadata
    assert "endpoint_velocity_frame" not in record.state.metadata


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
    assert stopped_record.state.metadata["endpoint_progress_status"] == "not_requested"
    assert stopped_record.state.metadata["source_active"] is False
    assert stopped_record.state.metadata["actual_tip_delta_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_runtime_step_loop_does_not_fabricate_progress_for_programmed_target_path() -> None:
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("programmed_target", steps=1),
        publisher=RecordingPublisher(),
    )

    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1))[0]

    assert "endpoint_progress_status" not in record.state.metadata
    assert "endpoint_progress_measurement_available" not in record.state.metadata
    assert "actual_tip_delta_m" not in record.state.metadata


def test_replay_step_loop_injects_typed_providers_and_protects_profile_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    original = input_step_loop.resolve_robot_bundle

    def recording_resolver(profile_id: str, **kwargs):  # noqa: ANN202
        calls.append(f"{profile_id}/v{kwargs['robot_logical_version']}")
        return original(profile_id, **kwargs)

    monkeypatch.setattr(input_step_loop, "resolve_robot_bundle", recording_resolver)
    spoofed = {
        "robot_profile_id": "spoofed",
        "model_contract_version": "spoofed/v9",
        "robot_joint_names": ("wrong",),
        "robot_qpos_dimension": 999,
    }
    frame = RawInputFrame(source="replay", timestamp_s=0.0, metadata=spoofed)
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("replay", steps=1, frames=(frame,)),
        publisher=RecordingPublisher(),
    )
    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1))[0]
    bundle = resolve_robot_bundle("fast_arm")

    assert calls == ["fast_arm/v1"]
    assert not hasattr(plan, "resolved_robot_runtime")
    assert plan.endpoint_pose_provider is bundle.provider(ENDPOINT_POSE_V1)
    assert plan.endpoint_command_provider is bundle.provider(ENDPOINT_COMMAND_V1)
    assert plan.qpos_feasibility_provider is bundle.provider(QPOS_FEASIBILITY_V1)
    assert record.state.metadata["robot_profile_id"] == "fast_arm"
    assert record.state.metadata["model_contract_version"] == FAST_ARM_ROBOT_PROFILE.model_contract_version
    assert record.state.metadata["robot_joint_names"] == FAST_ARM_ROBOT_PROFILE.canonical_joint_names
    assert record.state.metadata["robot_qpos_dimension"] == 4


def test_runtime_step_order_publishes_annotated_state_before_viewer_rebase(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)
    ingest_viewer_control_message(viewer_input_source, _keyboard_message(6.0, "Space"))

    original_measure = input_step_loop.measure_post_step_endpoint
    original_annotate = input_step_loop.annotate_runtime_input_state
    published_states = []

    class SimulatorRecorder:
        def __init__(self, simulator):
            self.simulator = simulator
            self.snapshot_count = 0
            self.stepped = False

        def snapshot(self):
            self.snapshot_count += 1
            if self.snapshot_count == 1:
                events.append("pre_snapshot")
            elif self.stepped:
                events.append("post_snapshot")
            return self.simulator.snapshot()

        def apply_command(self, command):
            events.append("apply")
            return self.simulator.apply_command(command)

        def step(self, dt_s):
            events.append("step")
            result = self.simulator.step(dt_s)
            self.stepped = True
            return result

        def __getattr__(self, name):
            return getattr(self.simulator, name)

    class PublisherRecorder:
        def __init__(self, publisher):
            self.publisher = publisher

        async def publish(self, state):
            events.append("publish")
            published_states.append(state)
            await self.publisher.publish(state)

    class InputSourceRecorder:
        def read_frame(self):
            return viewer_input_source.read_frame()

        def rebase_current_endpoint_m(self, endpoint_m):
            events.append("rebase")
            return viewer_input_source.rebase_current_endpoint_m(endpoint_m)

    def measure(pre_state, post_state, *, site_name):
        events.append("measure")
        return original_measure(pre_state, post_state, site_name=site_name)

    def annotate(**kwargs):
        events.append("annotate")
        return original_annotate(**kwargs)

    plan.pipeline.simulator = SimulatorRecorder(plan.pipeline.simulator)
    plan.pipeline.publisher = PublisherRecorder(plan.pipeline.publisher)
    plan.pipeline.input_source = InputSourceRecorder()
    monkeypatch.setattr(input_step_loop, "measure_post_step_endpoint", measure)
    monkeypatch.setattr(input_step_loop, "annotate_runtime_input_state", annotate)

    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))[0]

    assert events == [
        "pre_snapshot",
        "apply",
        "step",
        "post_snapshot",
        "measure",
        "annotate",
        "publish",
        "rebase",
    ], events
    assert published_states[0] == record.state


def test_runtime_step_loop_continues_publish_when_tip_measurement_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = _ClockSequence((0.0, 0.0))
    viewer_input_source, plan = _build_plan(clock)
    ingest_viewer_control_message(viewer_input_source, _keyboard_message(7.0, "Space"))
    monkeypatch.setattr(
        input_step_loop,
        "measure_post_step_endpoint",
        lambda pre_state, post_state, *, site_name: (
            input_step_loop.PostStepMeasurement(None, None, None)
        ),
        raising=False,
    )

    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1, dt_s=1.0 / 60.0))[0]

    assert record.state.metadata["endpoint_progress_status"] == "measurement_unavailable"
    assert record.state.metadata["endpoint_progress_measurement_available"] is False
    assert "actual_tip_delta_m" not in record.state.metadata
    assert plan.pipeline.publisher.publisher.states


def test_no_input_and_continuous_held_input_use_the_same_live_pacer_contract() -> None:
    class RecordingPacer:
        def __init__(self) -> None:
            self.start_count = 0
            self.pace_count = 0

        def start(self) -> None:
            self.start_count += 1

        async def pace(self) -> None:
            self.pace_count += 1

    async def run_case(*, held: bool) -> RecordingPacer:
        source = ViewerInputSource(clock=lambda: 0.0)
        if held:
            ingest_viewer_control_message(source, _keyboard_message(0.0, "ShiftRight"))
        plan = build_runtime_input_source_step_loop_plan(
            select_runtime_input_source("viewer", steps=3),
            publisher=RecordingPublisher(),
            viewer_input_source=source,
        )
        pacer = RecordingPacer()
        await run_runtime_input_source_step_loop(
            plan,
            steps=3,
            dt_s=1.0 / 60.0,
            interval_s=1.0 / 60.0,
            pacer=pacer,
            collect_records=False,
        )
        return pacer

    no_input, held_input = asyncio.run(_run_two_cases(run_case))

    assert no_input.start_count == held_input.start_count == 1
    assert no_input.pace_count == held_input.pace_count == 3


async def _run_two_cases(run_case):
    return await run_case(held=False), await run_case(held=True)


def test_publish_exception_exits_before_pacing_without_background_work() -> None:
    class FailingPublisher:
        async def publish(self, state) -> None:
            raise RuntimeError("publish failed")

    class RecordingPacer:
        def __init__(self) -> None:
            self.pace_count = 0

        def start(self) -> None:
            return None

        async def pace(self) -> None:
            self.pace_count += 1

    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=2),
        publisher=FailingPublisher(),
        viewer_input_source=ViewerInputSource(clock=lambda: 0.0),
    )
    pacer = RecordingPacer()

    with pytest.raises(RuntimeError, match="publish failed"):
        asyncio.run(
            run_runtime_input_source_step_loop(
                plan,
                steps=2,
                dt_s=1.0 / 60.0,
                interval_s=1.0 / 60.0,
                pacer=pacer,
            )
        )

    assert pacer.pace_count == 0
