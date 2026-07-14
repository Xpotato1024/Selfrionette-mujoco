from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from time import monotonic

from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M, ViewerInputSource
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.input_step_diagnostics import (
    PostStepMeasurement,
    annotate_runtime_input_state,
    measure_post_step_endpoint,
)
from selfrionette.runtime.input_source_selection import RuntimeInputSourceSelection
from selfrionette.runtime.input_source_state import (
    build_runtime_input_source_state_from_metadata,
)
from selfrionette.runtime.input_safety import build_runtime_input_safety_result
from selfrionette.runtime.viewer_motion_policy import build_viewer_local_motion_metadata
from selfrionette.runtime.robot_plugin import RobotRuntimePlugin
from selfrionette.runtime.robot_plugin_registry import ResolvedRobotRuntime, resolve_robot_runtime
from selfrionette.robot_profile import robot_profile_runtime_metadata
from selfrionette.runtime.robot_profile_metadata import merge_runtime_metadata
from selfrionette.runtime.mujoco_pipeline import build_mujoco_pipeline
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.runtime.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.schemas import InputIntent, MotionCommand, MuJoCoState, RawInputFrame
from selfrionette.transport import StatePublisher
from selfrionette.transport.stubs import NoOpStatePublisher

VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD = 0.2


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceStepLoopPlan:
    selection: RuntimeInputSourceSelection
    pipeline: RuntimePipeline
    annotate_target_position_m: bool
    resolved_robot_runtime: ResolvedRobotRuntime


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceStepLoopRecord:
    frame: RawInputFrame
    intent: InputIntent
    motion_command: MotionCommand
    state: MuJoCoState


def _resolve_model_path(
    *, model_path: str | Path | None, config: RuntimeConfig, resolved_runtime: ResolvedRobotRuntime
) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return resolved_runtime.profile.mujoco_model_asset


def _coerce_viewer_endpoint_m(value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return DEFAULT_VIEWER_SAFE_ENDPOINT_M

    endpoint_m = tuple(float(component) for component in value)
    if len(endpoint_m) != 3:
        return DEFAULT_VIEWER_SAFE_ENDPOINT_M

    return endpoint_m


def _extract_current_endpoint_m(
    pipeline: RuntimePipeline, plugin: RobotRuntimePlugin
) -> tuple[float, float, float] | None:
    return plugin.endpoint_position_from_state(pipeline.simulator.snapshot())


def _extract_endpoint_orientation_wxyz_from_state(
    state: MuJoCoState, plugin: RobotRuntimePlugin
) -> tuple[float, float, float, float] | None:
    return plugin.endpoint_orientation_from_state(state)


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
    if runtime_config.robot_profile_id is None:
        raise ValueError("production input step-loop requires robot_profile_id")
    resolved_runtime = resolve_robot_runtime(runtime_config.robot_profile_id)
    plugin = resolved_runtime.plugin
    resolved_model_path = _resolve_model_path(
        model_path=model_path, config=runtime_config, resolved_runtime=resolved_runtime
    )

    if viewer_input_source is not None and selection.source_name != "viewer":
        raise ValueError("viewer_input_source can only be supplied when selection.source_name == 'viewer'")

    if selection.source_name == "programmed_target":
        pipeline = build_concrete_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            model_path=resolved_model_path,
            loop=selection.loop,
            publisher=publisher if publisher is not None else NoOpStatePublisher(),
        )
        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=True,
            resolved_robot_runtime=resolved_runtime,
        )

    if selection.source_name == "replay":
        pipeline = build_replay_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            model_path=resolved_model_path,
            loop=selection.loop,
            publisher=publisher,
            initial_keyframe_name=plugin.profile.initial_keyframe_name,
            robot_profile_metadata=robot_profile_runtime_metadata(resolved_runtime.profile),
        )
        plugin.validate_model(pipeline.simulator.model)
        pipeline.qpos_feasibility_guard = plugin.build_qpos_feasibility_guard(
            model=pipeline.simulator.model,
            config_path=runtime_config.joint_limit_config_path,
        )
        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=False,
            resolved_robot_runtime=resolved_runtime,
        )

    if selection.source_name == "noop":
        pipeline = build_mujoco_pipeline(
            frame=selection.frames[0] if selection.frames else RawInputFrame(source="noop", timestamp_s=0.0),
            config=runtime_config,
            model_path=resolved_model_path,
            initial_keyframe_name=plugin.profile.initial_keyframe_name,
            robot_profile_metadata=robot_profile_runtime_metadata(resolved_runtime.profile),
        )
        plugin.validate_model(pipeline.simulator.model)
        if publisher is not None:
            pipeline.publisher = publisher

        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=False,
            resolved_robot_runtime=resolved_runtime,
        )

    if selection.source_name == "viewer":
        pipeline_input_source = viewer_input_source
        if pipeline_input_source is None:
            initial_endpoint_m = _coerce_viewer_endpoint_m(
                selection.initial_metadata.get("desired_endpoint_m", selection.initial_metadata.get("target_position_m"))
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
            publisher=publisher if publisher is not None else NoOpStatePublisher(),
            discontinuity_threshold_rad=VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD,
            discontinuity_threshold_label="viewer endpoint continuity threshold",
        )
        pipeline.input_source = pipeline_input_source
        pipeline.motion_generator = plugin.build_local_endpoint_motion_generator()
        initial_tip_site_position_m = _extract_current_endpoint_m(pipeline, plugin)
        if initial_tip_site_position_m is not None:
            _sync_viewer_input_source_endpoint(
                pipeline.input_source,
                endpoint_m=initial_tip_site_position_m,
            )

        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=True,
            resolved_robot_runtime=resolved_runtime,
        )

    raise ValueError(f"unsupported input source for step loop: {selection.source_name!r}")


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
) -> tuple[RuntimeInputSourceStepLoopRecord, ...]:
    if steps < 1:
        raise ValueError("steps must be a positive integer")

    dt = plan.pipeline.config.dt_s if dt_s is None else dt_s
    records: list[RuntimeInputSourceStepLoopRecord] = []
    last_valid_endpoint_m: tuple[float, float, float] | None = None
    if plan.selection.source_name == "viewer":
        plugin = plan.resolved_robot_runtime.plugin
        last_valid_endpoint_m = _extract_current_endpoint_m(plan.pipeline, plugin)
        if last_valid_endpoint_m is None:
            last_valid_endpoint_m = _coerce_viewer_endpoint_m(
                plan.selection.initial_metadata.get("desired_endpoint_m", plan.selection.initial_metadata.get("target_position_m"))
            )

    for index in range(steps):
        frame = plan.pipeline.input_source.read_frame()
        intent = plan.pipeline.input_interpreter.interpret(frame)
        source_state = build_runtime_input_source_state_from_metadata(
            frame.metadata,
            default_source_kind=plan.selection.source_name,
        )
        pre_step_state = plan.pipeline.simulator.snapshot()
        pre_step_tip_site_orientation_wxyz = None
        if plan.selection.source_name == "viewer":
            plugin = plan.resolved_robot_runtime.plugin
            pre_step_tip_site_orientation_wxyz = _extract_endpoint_orientation_wxyz_from_state(
                pre_step_state, plugin
            )
        motion_intent = intent
        if plan.selection.source_name == "viewer":
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
        if not safety_result.motion_command.metadata.get("target_rejected", False) and not safety_result.qpos_feasibility_rejected:
            desired_endpoint_m = safety_result.motion_command.metadata.get("desired_endpoint_m")
            if desired_endpoint_m is not None:
                step_endpoint_m = _coerce_viewer_endpoint_m(desired_endpoint_m)

        plan.pipeline.simulator.apply_command(safety_result.motion_command)
        plan.pipeline.simulator.step(dt)

        state = plan.pipeline.simulator.snapshot()
        state = replace(
            state,
            metadata=merge_runtime_metadata(
                state.metadata,
                plan.pipeline.state_metadata,
                authoritative_profile_metadata=plan.pipeline.robot_profile_metadata,
            ),
        )
        measurement = PostStepMeasurement(None, None, None)
        if plan.selection.source_name == "viewer":
            plugin = plan.resolved_robot_runtime.plugin
            site_name = plugin.profile.endpoint.site_name
            if site_name is not None:
                measurement = measure_post_step_endpoint(
                    pre_step_state,
                    state,
                    site_name=site_name,
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
        await plan.pipeline.publisher.publish(annotated_state)
        if plan.selection.source_name == "viewer":
            if step_endpoint_m is None:
                step_endpoint_m = annotated_state.target_position_m or last_valid_endpoint_m
            if step_endpoint_m is not None:
                last_valid_endpoint_m = step_endpoint_m
            _sync_viewer_input_source_endpoint(
                plan.pipeline.input_source,
                endpoint_m=step_endpoint_m,
            )

        records.append(
            RuntimeInputSourceStepLoopRecord(
                frame=frame,
                intent=intent,
                motion_command=safety_result.motion_command,
                state=annotated_state,
            )
        )

        if interval_s > 0.0 and index + 1 < steps:
            await asyncio.sleep(interval_s)

    return tuple(records)


__all__ = [
    "RuntimeInputSourceStepLoopPlan",
    "RuntimeInputSourceStepLoopRecord",
    "build_runtime_input_source_step_loop_plan",
    "run_runtime_input_source_step_loop",
]
