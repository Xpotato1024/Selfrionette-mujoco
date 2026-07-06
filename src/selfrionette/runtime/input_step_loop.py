from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from time import monotonic

from selfrionette.input_sources.viewer import DEFAULT_VIEWER_SAFE_ENDPOINT_M, ViewerInputSource
from selfrionette.mujoco_backend import default_fast_arm_scene_path
from selfrionette.mujoco_backend.endpoint_extraction import (
    extract_fast_arm_base_link_position_from_state,
    extract_fast_arm_tip_site_endpoint_from_state,
)
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

VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD = 0.2


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


def _extract_current_tip_site_endpoint_m(pipeline: RuntimePipeline) -> tuple[float, float, float] | None:
    try:
        return extract_fast_arm_tip_site_endpoint_from_state(
            pipeline.simulator.snapshot()
        ).position_m
    except ValueError:
        return None


def _extract_current_solver_base_world_position_m(
    pipeline: RuntimePipeline,
) -> tuple[float, float, float] | None:
    try:
        return extract_fast_arm_base_link_position_from_state(
            pipeline.simulator.snapshot()
        )
    except ValueError:
        return None


def _vector_subtract(lhs_m: Sequence[float], rhs_m: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(lhs_m[index]) - float(rhs_m[index]) for index in range(3))


def _build_viewer_ik_target_metadata(
    *,
    desired_endpoint_m: Sequence[float],
    solver_base_world_position_m: Sequence[float],
) -> dict[str, object]:
    ik_target_endpoint_m = _vector_subtract(desired_endpoint_m, solver_base_world_position_m)
    return {
        "ik_target_endpoint_m": ik_target_endpoint_m,
        "ik_target_coordinate_frame": "solver-local fast_arm endpoint frame",
        "desired_endpoint_coordinate_frame": "MuJoCo world / scene frame",
        "solver_base_world_position_m": tuple(float(component) for component in solver_base_world_position_m),
    }


def build_runtime_input_source_step_loop_plan(
    selection: RuntimeInputSourceSelection,
    *,
    config: RuntimeConfig | None = None,
    publisher: StatePublisher | None = None,
    model_path: str | Path | None = None,
    viewer_clock: Callable[[], float] | None = None,
    viewer_input_source: ViewerInputSource | None = None,
) -> RuntimeInputSourceStepLoopPlan:
    runtime_config = RuntimeConfig() if config is None else config
    resolved_model_path = _resolve_model_path(model_path=model_path, config=runtime_config)

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
        initial_tip_site_position_m = _extract_current_tip_site_endpoint_m(pipeline)
        if initial_tip_site_position_m is not None:
            _sync_viewer_input_source_endpoint(
                pipeline.input_source,
                endpoint_m=initial_tip_site_position_m,
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
    last_valid_endpoint_m: tuple[float, float, float] | None,
    previous_state: MuJoCoState,
    state: MuJoCoState,
    annotate_target_position_m: bool,
    safety_result: RuntimeInputSafetyResult,
) -> MuJoCoState:
    target_rejected = bool(motion_command.metadata.get("target_rejected", False))
    should_publish_target = safety_result.should_update_target_position_m and not target_rejected
    metadata = {
        **state.metadata,
        **frame.metadata,
        **intent.metadata,
        **motion_command.metadata,
    }

    if not should_publish_target:
        metadata.pop("desired_endpoint_m", None)
        metadata.pop("target_position_m", None)
        metadata["runtime_input_safety_applied"] = True
        metadata["endpoint_evaluation"] = None

    target_position_m = state.target_position_m
    resolved_desired_endpoint = None
    if annotate_target_position_m and should_publish_target:
        try:
            resolved_desired_endpoint = resolve_desired_endpoint_from_motion_command(motion_command)
        except ValueError:
            resolved_desired_endpoint = None

        if resolved_desired_endpoint is not None:
            target_position_m = resolved_desired_endpoint.desired_endpoint_m
            metadata["desired_endpoint_m"] = resolved_desired_endpoint.desired_endpoint_m
            metadata["target_position_m"] = resolved_desired_endpoint.desired_endpoint_m
    elif not should_publish_target:
        if last_valid_endpoint_m is not None:
            target_position_m = last_valid_endpoint_m

    metadata.update(runtime_input_source_state_to_metadata(source_state))

    return replace(state, target_position_m=target_position_m, metadata=metadata)


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
        last_valid_endpoint_m = _extract_current_tip_site_endpoint_m(plan.pipeline)
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
        motion_intent = intent
        if plan.selection.source_name == "viewer":
            desired_endpoint_m = frame.metadata.get("desired_endpoint_m")
            solver_base_world_position_m = _extract_current_solver_base_world_position_m(plan.pipeline)
            if desired_endpoint_m is not None and solver_base_world_position_m is not None:
                motion_intent = replace(
                    intent,
                    metadata={
                        **intent.metadata,
                        **_build_viewer_ik_target_metadata(
                            desired_endpoint_m=_coerce_viewer_endpoint_m(desired_endpoint_m),
                            solver_base_world_position_m=solver_base_world_position_m,
                        ),
                        "viewer_endpoint_continuity_threshold_rad": VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD,
                        "accepted_small_motion_threshold_rad": VIEWER_ENDPOINT_CONTINUITY_THRESHOLD_RAD,
                    },
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
        )
        step_endpoint_m = last_valid_endpoint_m
        if not safety_result.motion_command.metadata.get("target_rejected", False):
            desired_endpoint_m = safety_result.motion_command.metadata.get("desired_endpoint_m")
            if desired_endpoint_m is not None:
                step_endpoint_m = _coerce_viewer_endpoint_m(desired_endpoint_m)

        plan.pipeline.simulator.apply_command(safety_result.motion_command)
        plan.pipeline.simulator.step(dt)

        state = plan.pipeline.simulator.snapshot()
        annotated_state = _annotate_state(
            source_state=safety_result.source_state,
            frame=frame,
            intent=intent,
            motion_command=safety_result.motion_command,
            last_valid_endpoint_m=last_valid_endpoint_m,
            previous_state=pre_step_state,
            state=state,
            annotate_target_position_m=plan.annotate_target_position_m,
            safety_result=safety_result,
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
