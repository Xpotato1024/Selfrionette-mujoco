from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from time import monotonic

from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M, ViewerInputSource
from selfrionette.mujoco_backend import default_fast_arm_scene_path
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.desired_endpoint_resolver import resolve_desired_endpoint_from_motion_command
from selfrionette.runtime.input_source_selection import RuntimeInputSourceSelection
from selfrionette.runtime.input_source_state import (
    build_runtime_input_source_state_from_metadata,
    RuntimeInputSourceState,
    runtime_input_source_state_to_metadata,
)
from selfrionette.runtime.input_safety import RuntimeInputSafetyResult, build_runtime_input_safety_result
from selfrionette.runtime.mujoco_pipeline import build_mujoco_pipeline
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.runtime.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.schemas import InputIntent, MotionCommand, MuJoCoState, RawInputFrame
from selfrionette.transport import StatePublisher
from selfrionette.transport.stubs import NoOpStatePublisher


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceStepLoopPlan:
    selection: RuntimeInputSourceSelection
    pipeline: RuntimePipeline
    annotate_target_position_m: bool


@dataclass(frozen=True, slots=True)
class RuntimeInputSourceStepLoopRecord:
    frame: RawInputFrame
    intent: InputIntent
    motion_command: MotionCommand
    state: MuJoCoState


def _resolve_model_path(*, model_path: str | Path | None, config: RuntimeConfig) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return default_fast_arm_scene_path()


def _coerce_viewer_endpoint_m(value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return DEFAULT_VIEWER_SAFE_ENDPOINT_M

    endpoint_m = tuple(float(component) for component in value)
    if len(endpoint_m) != 3:
        return DEFAULT_VIEWER_SAFE_ENDPOINT_M

    return endpoint_m


def build_runtime_input_source_step_loop_plan(
    selection: RuntimeInputSourceSelection,
    *,
    config: RuntimeConfig | None = None,
    publisher: StatePublisher | None = None,
    model_path: str | Path | None = None,
    viewer_clock: Callable[[], float] | None = None,
) -> RuntimeInputSourceStepLoopPlan:
    runtime_config = RuntimeConfig() if config is None else config
    resolved_model_path = _resolve_model_path(model_path=model_path, config=runtime_config)

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
        )

    if selection.source_name == "replay":
        pipeline = build_replay_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            model_path=resolved_model_path,
            loop=selection.loop,
            publisher=publisher,
        )
        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=False,
        )

    if selection.source_name == "noop":
        pipeline = build_mujoco_pipeline(
            frame=selection.frames[0] if selection.frames else RawInputFrame(source="noop", timestamp_s=0.0),
            config=runtime_config,
            model_path=resolved_model_path,
        )
        if publisher is not None:
            pipeline.publisher = publisher

        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=False,
        )

    if selection.source_name == "viewer":
        pipeline = build_concrete_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            model_path=resolved_model_path,
            loop=selection.loop,
            publisher=publisher if publisher is not None else NoOpStatePublisher(),
        )
        initial_endpoint_m = _coerce_viewer_endpoint_m(
            selection.initial_metadata.get("desired_endpoint_m", selection.initial_metadata.get("target_position_m"))
        )

        pipeline.input_source = ViewerInputSource(
            clock=viewer_clock if viewer_clock is not None else monotonic,
            initial_endpoint_m=initial_endpoint_m,
        )

        return RuntimeInputSourceStepLoopPlan(
            selection=selection,
            pipeline=pipeline,
            annotate_target_position_m=True,
        )

    raise ValueError(f"unsupported input source for step loop: {selection.source_name!r}")


def _annotate_state(
    *,
    source_state: RuntimeInputSourceState,
    frame: RawInputFrame,
    intent: InputIntent,
    motion_command: MotionCommand,
    state: MuJoCoState,
    annotate_target_position_m: bool,
    safety_result: RuntimeInputSafetyResult,
) -> MuJoCoState:
    metadata = {
        **state.metadata,
        **frame.metadata,
        **intent.metadata,
        **motion_command.metadata,
    }

    if not safety_result.should_update_target_position_m:
        metadata.pop("desired_endpoint_m", None)
        metadata.pop("target_position_m", None)
        metadata["runtime_input_safety_applied"] = True
        metadata["endpoint_evaluation"] = None

    target_position_m = state.target_position_m
    resolved_desired_endpoint = None
    if annotate_target_position_m and safety_result.should_update_target_position_m:
        try:
            resolved_desired_endpoint = resolve_desired_endpoint_from_motion_command(motion_command)
        except ValueError:
            resolved_desired_endpoint = None

        if resolved_desired_endpoint is not None:
            target_position_m = resolved_desired_endpoint.desired_endpoint_m
            metadata["desired_endpoint_m"] = resolved_desired_endpoint.desired_endpoint_m
            metadata["target_position_m"] = resolved_desired_endpoint.desired_endpoint_m

    metadata.update(runtime_input_source_state_to_metadata(source_state))

    return replace(state, target_position_m=target_position_m, metadata=metadata)


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

    for index in range(steps):
        frame = plan.pipeline.input_source.read_frame()
        intent = plan.pipeline.input_interpreter.interpret(frame)
        source_state = build_runtime_input_source_state_from_metadata(
            frame.metadata,
            default_source_kind=plan.selection.source_name,
        )
        pre_step_state = plan.pipeline.simulator.snapshot()
        motion_command = plan.pipeline.motion_generator.update(intent, dt)
        safety_result = build_runtime_input_safety_result(
            motion_command,
            source_state=source_state,
            current_state=pre_step_state,
        )
        plan.pipeline.simulator.apply_command(safety_result.motion_command)
        plan.pipeline.simulator.step(dt)

        state = plan.pipeline.simulator.snapshot()
        annotated_state = _annotate_state(
            source_state=safety_result.source_state,
            frame=frame,
            intent=intent,
            motion_command=safety_result.motion_command,
            state=state,
            annotate_target_position_m=plan.annotate_target_position_m,
            safety_result=safety_result,
        )
        await plan.pipeline.publisher.publish(annotated_state)

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
