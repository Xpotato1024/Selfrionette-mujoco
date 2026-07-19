from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from time import monotonic

from selfrionette.input_sources.viewer import (
    DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    ViewerInputSource,
)
from selfrionette.plugins.catalog import resolve_robot_bundle, resolve_robot_profile
from selfrionette.runtime.composition.robot_profile import robot_profile_runtime_metadata
from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.composition.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.control.input_step_diagnostics import (
    PostStepMeasurement,
    annotate_runtime_input_state,
    measure_post_step_endpoint,
)
from selfrionette.runtime.control.input_source_selection import RuntimeInputSourceSelection
from selfrionette.runtime.control.input_source_state import (
    build_runtime_input_source_state_from_metadata,
    build_runtime_input_source_state_from_health,
)
from selfrionette.runtime.safety.input_safety import build_runtime_input_safety_result
from selfrionette.runtime.execution.live_timing import (
    AbsoluteDeadlinePacer,
    LiveRuntimeTimingMetrics,
)
from selfrionette.runtime.composition.robot_bundle import (
    ENDPOINT_COMMAND_V1,
    ENDPOINT_POSE_V1,
    QPOS_FEASIBILITY_V1,
    RESET_INITIAL_STATE_V1,
    EndpointCommandProvider,
    EndpointPoseProvider,
    QposFeasibilityProvider,
    ResetInitialStateProvider,
    RobotBundle,
)
from selfrionette.runtime.composition.robot_profile_metadata import merge_runtime_metadata
from selfrionette.runtime.control.viewer_motion_policy import build_viewer_local_motion_metadata
from selfrionette.runtime.execution.pipeline import RuntimePipeline
from selfrionette.runtime.execution.input_source_adapters import (
    compatibility_execution_adapter,
)
from selfrionette.runtime.composition.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.schemas import InputIntent, MotionCommand, MuJoCoState, RawInputFrame
from selfrionette.transport import StatePublisher

VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD = 0.2


class _InputLoopStatePublisher:
    """Retain the latest local state when no external publisher is configured."""

    def __init__(self) -> None:
        self.last_state: MuJoCoState | None = None

    async def publish(self, state: MuJoCoState) -> None:
        self.last_state = state


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceStepLoopPlan:
    selection: RuntimeInputSourceSelection
    pipeline: RuntimePipeline
    annotate_target_position_m: bool
    endpoint_pose_provider: EndpointPoseProvider
    endpoint_command_provider: EndpointCommandProvider
    qpos_feasibility_provider: QposFeasibilityProvider
    endpoint_site_name: str | None
    execution_adapter: object


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceStepLoopRecord:
    frame: RawInputFrame
    intent: InputIntent
    motion_command: MotionCommand
    state: MuJoCoState


def _resolve_model_path(
    *, model_path: str | Path | None, config: RuntimeConfig, robot_bundle: RobotBundle
) -> Path | None:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return None


def _coerce_viewer_endpoint_m(value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return DEFAULT_VIEWER_SAFE_ENDPOINT_M

    endpoint_m = tuple(float(component) for component in value)
    if len(endpoint_m) != 3:
        return DEFAULT_VIEWER_SAFE_ENDPOINT_M

    return endpoint_m


def _extract_current_endpoint_m(
    pipeline: RuntimePipeline, provider: EndpointPoseProvider
) -> tuple[float, float, float] | None:
    return provider.observe_endpoint_pose(pipeline.simulator.snapshot()).position_m


def _extract_endpoint_orientation_wxyz_from_state(
    state: MuJoCoState, provider: EndpointPoseProvider
) -> tuple[float, float, float, float] | None:
    return provider.observe_endpoint_pose(state).quaternion_wxyz


def build_runtime_input_source_step_loop_plan(
    selection: RuntimeInputSourceSelection,
    *,
    config: RuntimeConfig | None = None,
    publisher: StatePublisher | None = None,
    model_path: str | Path | None = None,
    viewer_clock: Callable[[], float] | None = None,
    viewer_input_source: ViewerInputSource | None = None,
) -> RuntimeInputSourceStepLoopPlan:
    runtime_config = RuntimeConfig(robot_profile_id="fast_arm") if config is None else config
    execution_adapter = selection.execution_adapter or compatibility_execution_adapter(selection.source_name)
    if runtime_config.robot_profile_id is None:
        raise ValueError("production input step-loop requires robot_profile_id")
    profile = resolve_robot_profile(
        runtime_config.robot_profile_id,
        robot_logical_version=runtime_config.robot_logical_version,
    )
    robot_bundle = resolve_robot_bundle(
        runtime_config.robot_profile_id,
        robot_logical_version=runtime_config.robot_logical_version,
    )
    if robot_bundle.profile is not profile:
        raise ValueError("Robot Bundle/profile catalog consistency mismatch")
    plugin = robot_bundle.runtime_plugin
    endpoint_pose_provider = robot_bundle.provider(ENDPOINT_POSE_V1)
    endpoint_command_provider = robot_bundle.provider(ENDPOINT_COMMAND_V1)
    qpos_feasibility_provider = robot_bundle.provider(QPOS_FEASIBILITY_V1)
    initial_state_provider = robot_bundle.provider(RESET_INITIAL_STATE_V1)
    assert isinstance(endpoint_pose_provider, EndpointPoseProvider)
    assert isinstance(endpoint_command_provider, EndpointCommandProvider)
    assert isinstance(qpos_feasibility_provider, QposFeasibilityProvider)
    assert isinstance(initial_state_provider, ResetInitialStateProvider)
    initial_state = initial_state_provider.resolve_initial_state()
    if initial_state.source_kind != "named_keyframe":
        raise ValueError("production input step-loop requires a named-keyframe initial state")
    resolved_model_path = _resolve_model_path(
        model_path=model_path, config=runtime_config, robot_bundle=robot_bundle
    )
    plan_providers = {
        "endpoint_pose_provider": endpoint_pose_provider,
        "endpoint_command_provider": endpoint_command_provider,
        "qpos_feasibility_provider": qpos_feasibility_provider,
        "endpoint_site_name": robot_bundle.profile.endpoint.site_name,
    }

    if viewer_input_source is not None and not execution_adapter.uses_viewer_endpoint_compatibility:
        raise ValueError(
            "viewer_input_source can only be supplied for the viewer endpoint compatibility adapter"
        )

    if execution_adapter.annotates_target_position and not execution_adapter.uses_viewer_endpoint_compatibility:
        pipeline = build_concrete_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            model_path=resolved_model_path,
            loop=selection.loop,
            publisher=publisher if publisher is not None else _InputLoopStatePublisher(),
        )
        if selection.runtime_reader is not None:
            pipeline.input_source = selection.runtime_reader
        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=True,
            **plan_providers,
            execution_adapter=execution_adapter,
        )

    if execution_adapter.uses_replay_pipeline:
        simulator = plugin.build_simulator(
            model_path=resolved_model_path,
            initial_keyframe_name=initial_state.source_id,
        )
        pipeline = build_replay_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            simulator=simulator,
            loop=selection.loop,
            publisher=publisher,
            initial_keyframe_name=initial_state.source_id,
            robot_profile_metadata=robot_profile_runtime_metadata(robot_bundle.profile),
        )
        plugin.validate_model(pipeline.simulator.model)
        pipeline.qpos_feasibility_guard = qpos_feasibility_provider.build_guard(
            model=pipeline.simulator.model,
            config_path=runtime_config.joint_limit_config_path,
        )
        if selection.runtime_reader is not None:
            pipeline.input_source = selection.runtime_reader
        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=False,
            **plan_providers,
            execution_adapter=execution_adapter,
        )

    if execution_adapter.uses_viewer_endpoint_compatibility:
        pipeline_input_source = viewer_input_source or selection.runtime_reader
        if pipeline_input_source is None:
            initial_endpoint_m = _coerce_viewer_endpoint_m(
                selection.initial_metadata.get(
                    "desired_endpoint_m",
                    selection.initial_metadata.get("target_position_m"),
                )
            )
            pipeline_input_source = ViewerInputSource(
                clock=viewer_clock if viewer_clock is not None else monotonic,
                initial_endpoint_m=initial_endpoint_m,
            )

        pipeline = build_concrete_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            model_path=resolved_model_path,
            loop=selection.loop,
            publisher=publisher if publisher is not None else _InputLoopStatePublisher(),
            discontinuity_threshold_rad=VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD,
            discontinuity_threshold_label="viewer endpoint continuity threshold",
        )
        pipeline.input_source = pipeline_input_source
        pipeline.motion_generator = (
            endpoint_command_provider.build_local_endpoint_motion_generator()
        )
        initial_tip_site_position_m = _extract_current_endpoint_m(
            pipeline, endpoint_pose_provider
        )
        if initial_tip_site_position_m is not None:
            _sync_viewer_input_source_endpoint(
                pipeline.input_source,
                endpoint_m=initial_tip_site_position_m,
            )

        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=True,
            **plan_providers,
            execution_adapter=execution_adapter,
        )

    raise ValueError(f"unsupported input source execution adapter: {execution_adapter!r}")


def _sync_viewer_input_source_endpoint(
    input_source: object,
    *,
    endpoint_m: tuple[float, float, float] | None,
) -> None:
    rebase_current_endpoint_m = getattr(input_source, "rebase_current_endpoint_m", None)
    if not callable(rebase_current_endpoint_m):
        return

    if endpoint_m is None:
        endpoint_m = DEFAULT_VIEWER_SAFE_ENDPOINT_M

    rebase_current_endpoint_m(endpoint_m)


async def run_runtime_input_source_step_loop(
    plan: RuntimeInputSourceStepLoopPlan,
    *,
    steps: int,
    dt_s: float | None = None,
    interval_s: float = 0.0,
    pacer: AbsoluteDeadlinePacer | None = None,
    timing_metrics: LiveRuntimeTimingMetrics | None = None,
    collect_records: bool = True,
) -> tuple[RuntimeInputSourceStepLoopRecord, ...]:
    reader = plan.pipeline.input_source
    start = getattr(reader, "start", None)
    close = getattr(reader, "close", None)
    attempted_start = False
    try:
        if callable(start):
            attempted_start = True
            start()
        return await _run_runtime_input_source_step_loop(
            plan,
            steps=steps,
            dt_s=dt_s,
            interval_s=interval_s,
            pacer=pacer,
            timing_metrics=timing_metrics,
            collect_records=collect_records,
        )
    except BaseException as failure:
        if attempted_start and callable(close):
            try:
                close()
            except BaseException as cleanup_failure:
                failure.add_note(f"input source cleanup failed: {cleanup_failure!r}")
        raise failure
    finally:
        if not attempted_start and callable(close):
            close()


async def _run_runtime_input_source_step_loop(
    plan: RuntimeInputSourceStepLoopPlan,
    *,
    steps: int,
    dt_s: float | None = None,
    interval_s: float = 0.0,
    pacer: AbsoluteDeadlinePacer | None = None,
    timing_metrics: LiveRuntimeTimingMetrics | None = None,
    collect_records: bool = True,
) -> tuple[RuntimeInputSourceStepLoopRecord, ...]:
    if steps < 1:
        raise ValueError("steps must be a positive integer")

    dt = plan.pipeline.config.dt_s if dt_s is None else dt_s
    if timing_metrics is not None:
        timing_metrics.start()
    if pacer is not None:
        pacer.start()
    records: list[RuntimeInputSourceStepLoopRecord] = []
    last_valid_endpoint_m: tuple[float, float, float] | None = None
    if plan.execution_adapter.uses_viewer_endpoint_compatibility:
        last_valid_endpoint_m = _extract_current_endpoint_m(
            plan.pipeline, plan.endpoint_pose_provider
        )
        if last_valid_endpoint_m is None:
            last_valid_endpoint_m = _coerce_viewer_endpoint_m(
                plan.selection.initial_metadata.get(
                    "desired_endpoint_m",
                    plan.selection.initial_metadata.get("target_position_m"),
                )
            )

    for index in range(steps):
        compute_started_s = timing_metrics.clock() if timing_metrics is not None else 0.0
        frame = plan.pipeline.input_source.read_frame()
        intent = plan.pipeline.input_interpreter.interpret(frame)
        health_provider = getattr(plan.pipeline.input_source, "current_health", None)
        if callable(health_provider):
            health = health_provider()
            source_state = build_runtime_input_source_state_from_health(
                health, source_kind=plan.selection.source_name
            )
            frame_active = frame.metadata.get("source_active")
            if isinstance(frame_active, bool) and frame_active != source_state.source_active:
                raise ValueError("input source frame metadata and typed health disagree")
            frame_reason = frame.metadata.get("stale_reason")
            if frame_reason is not None and frame_reason != source_state.stale_reason:
                raise ValueError("input source frame stale reason and typed health disagree")
        else:
            source_state = build_runtime_input_source_state_from_metadata(
                frame.metadata,
                default_source_kind=plan.selection.source_name,
            )
        pre_step_state = plan.pipeline.simulator.snapshot()
        pre_step_tip_site_orientation_wxyz = None
        if plan.execution_adapter.uses_viewer_endpoint_compatibility:
            pre_step_tip_site_orientation_wxyz = _extract_endpoint_orientation_wxyz_from_state(
                pre_step_state, plan.endpoint_pose_provider
            )
        motion_intent = intent
        if plan.execution_adapter.uses_viewer_endpoint_compatibility:
            motion_intent_metadata = {
                **frame.metadata,
                **intent.metadata,
            }
            if pre_step_tip_site_orientation_wxyz is not None:
                motion_intent_metadata["current_tip_orientation_wxyz"] = pre_step_tip_site_orientation_wxyz
            motion_intent = replace(
                intent,
                metadata=build_viewer_local_motion_metadata(motion_intent_metadata, dt_s=dt),
            )
        current_qpos_rad = tuple(pre_step_state.qpos)
        set_current_qpos = getattr(plan.pipeline.motion_generator, "set_current_qpos_rad", None)
        if callable(set_current_qpos):
            set_current_qpos(current_qpos_rad)
        motion_command = plan.pipeline.motion_generator.update(motion_intent, dt)
        safety_result = build_runtime_input_safety_result(
            motion_command,
            source_state=source_state,
            current_state=pre_step_state,
            qpos_feasibility_guard=plan.pipeline.qpos_feasibility_guard,
        )
        step_endpoint_m = last_valid_endpoint_m
        if (
            not safety_result.motion_command.metadata.get("target_rejected", False)
            and not safety_result.qpos_feasibility_rejected
        ):
            desired_endpoint_m = safety_result.motion_command.metadata.get("desired_endpoint_m")
            if desired_endpoint_m is not None:
                step_endpoint_m = _coerce_viewer_endpoint_m(desired_endpoint_m)

        compute_finished_s = timing_metrics.clock() if timing_metrics is not None else 0.0
        simulation_started_s = compute_finished_s
        plan.pipeline.simulator.apply_command(safety_result.motion_command)
        plan.pipeline.simulator.step(dt)

        state = plan.pipeline.simulator.snapshot()
        simulation_finished_s = timing_metrics.clock() if timing_metrics is not None else 0.0
        annotation_started_s = simulation_finished_s
        state = replace(
            state,
            metadata=merge_runtime_metadata(
                state.metadata,
                plan.pipeline.state_metadata,
                authoritative_profile_metadata=plan.pipeline.robot_profile_metadata,
            ),
        )
        measurement = PostStepMeasurement(None, None, None)
        if plan.execution_adapter.uses_viewer_endpoint_compatibility and plan.endpoint_site_name is not None:
            measurement = measure_post_step_endpoint(
                pre_step_state,
                state,
                site_name=plan.endpoint_site_name,
            )
        annotated_state = annotate_runtime_input_state(
            source_state=safety_result.source_state,
            frame=frame,
            intent=intent,
            motion_command=safety_result.motion_command,
            last_valid_endpoint_m=last_valid_endpoint_m,
            state=state,
            measurement=measurement,
            annotate_target_position_m=plan.annotate_target_position_m,
            safety_result=safety_result,
            authoritative_profile_metadata=plan.pipeline.robot_profile_metadata,
        )
        annotation_finished_s = timing_metrics.clock() if timing_metrics is not None else 0.0
        publish_started_s = annotation_finished_s
        await plan.pipeline.publisher.publish(annotated_state)
        publish_finished_s = timing_metrics.clock() if timing_metrics is not None else 0.0
        if plan.execution_adapter.uses_viewer_endpoint_compatibility:
            if step_endpoint_m is None:
                step_endpoint_m = annotated_state.target_position_m or last_valid_endpoint_m
            if step_endpoint_m is not None:
                last_valid_endpoint_m = step_endpoint_m
            _sync_viewer_input_source_endpoint(
                plan.pipeline.input_source,
                endpoint_m=step_endpoint_m,
            )
        post_publish_finished_s = timing_metrics.clock() if timing_metrics is not None else 0.0

        if collect_records:
            records.append(
                RuntimeInputSourceStepLoopRecord(
                    frame=frame,
                    intent=intent,
                    motion_command=safety_result.motion_command,
                    state=annotated_state,
                )
            )

        if timing_metrics is not None:
            timing_metrics.record_frame(
                compute_time_s=compute_finished_s - compute_started_s,
                simulation_step_time_s=simulation_finished_s - simulation_started_s,
                annotation_time_s=(annotation_finished_s - annotation_started_s)
                + (post_publish_finished_s - publish_finished_s),
                publish_wait_or_enqueue_time_s=publish_finished_s - publish_started_s,
            )

        if pacer is not None:
            await pacer.pace()
        elif interval_s > 0.0 and index + 1 < steps:
            await asyncio.sleep(interval_s)

    return tuple(records)


__all__ = [
    "RuntimeInputSourceStepLoopPlan",
    "RuntimeInputSourceStepLoopRecord",
    "build_runtime_input_source_step_loop_plan",
    "run_runtime_input_source_step_loop",
]
