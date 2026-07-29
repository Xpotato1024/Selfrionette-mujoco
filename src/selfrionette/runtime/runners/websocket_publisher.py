from __future__ import annotations

import asyncio
import json

from selfrionette.plugins.input_sources.catalog import get_input_source_registration
from selfrionette.plugins.input_sources.programmed_target import build_sweep_x_input_source
from selfrionette.mujoco_backend import snapshot_mujoco_state
from selfrionette.runtime.composition.concrete_mujoco_pipeline import DEFAULT_CONCRETE_TARGET_POSITION_M, build_concrete_mujoco_pipeline
from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.runtime.control.input_source_state import (
    build_runtime_input_source_state_from_metadata,
)
from selfrionette.runtime.control.viewer_control_ingress import (
    build_viewer_input_source,
    ingest_viewer_control_message_json,
)
from selfrionette.runtime.execution.input_step_loop import (
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.runtime.execution.live_timing import (
    AbsoluteDeadlinePacer,
    LiveRuntimeTimingMetrics,
)
from selfrionette.runtime.runners.live_websocket_delivery import (
    LiveLatestStateWebSocketPublisher,
)
from selfrionette.runtime.safety.input_safety import RuntimeInputSafetyResult
from selfrionette.runtime.composition.robot_profile_metadata import merge_runtime_metadata
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import WebSocketPublisherServer, WebSocketStatePublisher

DEFAULT_WEBSOCKET_PUBLISHER_HOST = "127.0.0.1"
DEFAULT_WEBSOCKET_PUBLISHER_PORT = 8766
DEFAULT_WEBSOCKET_PUBLISHER_STEPS = 1
DEFAULT_WEBSOCKET_PUBLISHER_DT_S = 1.0 / 60.0
DEFAULT_WEBSOCKET_PUBLISHER_INTERVAL_S = 0.0
DEFAULT_WEBSOCKET_PUBLISHER_GRACE_PERIOD_S = 0.05
SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS = ("sweep_x",)


def _default_replay_frame() -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={
            "preset": "r6-c-p1-default",
            "target_position_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
            "desired_endpoint_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
        },
    )


def _sweep_x_replay_frames(steps: int) -> tuple[RawInputFrame, ...]:
    source = build_sweep_x_input_source(initial_position_m=DEFAULT_CONCRETE_TARGET_POSITION_M, loop=False)
    return tuple(source.read_frame() for _ in range(steps))


def _validate_host(host: str) -> None:
    if not host:
        raise ValueError("host must not be empty")


def _validate_port(port: int) -> None:
    if port < 1 or port > 65535:
        raise ValueError("port must be in the range 1..65535")


def _validate_steps(steps: int) -> None:
    if steps < 1:
        raise ValueError("steps must be a positive integer")


def _validate_dt_s(dt_s: float) -> None:
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive")


def _validate_interval_s(interval_s: float) -> None:
    if interval_s < 0.0:
        raise ValueError("interval_s must be non-negative")


def _validate_grace_period_s(grace_period_s: float) -> None:
    if grace_period_s < 0.0:
        raise ValueError("grace_period_s must be non-negative")


def _log(message: str) -> None:
    print(message, flush=True)


def _annotate_sweep_x_state(
    pipeline,
    state,
    intent,
    safety_result: RuntimeInputSafetyResult,
):
    command = safety_result.motion_command
    qpos_rejected = safety_result.qpos_feasibility_rejected
    metadata = merge_runtime_metadata(
        state.metadata,
        pipeline.state_metadata,
        intent.metadata,
        None if command is None else command.metadata,
        {"preset": "sweep_x"},
        authoritative_profile_metadata=pipeline.robot_profile_metadata,
    )
    if qpos_rejected:
        metadata["endpoint_evaluation"] = None
        metadata = merge_runtime_metadata(
            metadata,
            authoritative_profile_metadata=pipeline.robot_profile_metadata,
        )
    return snapshot_mujoco_state(
        pipeline.simulator.model,
        pipeline.simulator.data,
        frame_index=state.frame_index,
        target_position_m=None if qpos_rejected else tuple(intent.metadata["desired_endpoint_m"]),
        metadata=metadata,
    )


async def _run_input_source_websocket_publisher_async(
    *,
    host: str,
    port: int,
    steps: int,
    dt_s: float,
    interval_s: float,
    grace_period_s: float,
    preset: str | None,
    input_source: str,
    robot_profile_id: str,
) -> None:
    runtime_config = RuntimeConfig(
        dt_s=dt_s,
        robot_profile_id=robot_profile_id,
    )
    registration = get_input_source_registration(input_source)
    viewer_input_source = None
    on_message = None
    if registration.execution_adapter.uses_viewer_endpoint_compatibility:
        viewer_input_source = build_viewer_input_source()

        def handle_viewer_message(message: str) -> None:
            assert viewer_input_source is not None
            ingest_viewer_control_message_json(viewer_input_source, message)

        on_message = handle_viewer_message

    server_kwargs = {"host": host, "port": port}
    if on_message is not None:
        server_kwargs["on_message"] = on_message
    async with WebSocketPublisherServer(**server_kwargs) as server:
        _log(f"serving on ws://{server.host}:{server.bound_port}")
        _log(f"Waiting for viewer during grace period ({grace_period_s:.2f}s)")

        has_client = await server.wait_for_client(timeout_s=grace_period_s)
        if not has_client:
            _log("No viewer connected during grace period; no payloads published.")
            _log("Completed without publishing because no viewer connected.")
            return

        _log("Viewer connected; publishing started.")
        selection = select_runtime_input_source(
            input_source,
            steps=steps,
            preset=preset,
        )

        if viewer_input_source is not None:
            timing_metrics = LiveRuntimeTimingMetrics()
            pacer = (
                AbsoluteDeadlinePacer(interval_s, metrics=timing_metrics)
                if interval_s > 0.0
                else None
            )
            async with LiveLatestStateWebSocketPublisher(server) as publisher:
                plan = build_runtime_input_source_step_loop_plan(
                    selection,
                    config=runtime_config,
                    publisher=publisher,
                    viewer_input_source=viewer_input_source,
                )
                await run_runtime_input_source_step_loop(
                    plan,
                    steps=steps,
                    dt_s=dt_s,
                    interval_s=interval_s,
                    pacer=pacer,
                    timing_metrics=timing_metrics,
                    collect_records=False,
                )
                await publisher.drain()
                delivery_summary = publisher.summary().to_dict()
            _log(
                "live runtime timing summary: "
                + json.dumps(
                    {
                        **timing_metrics.summary(dt_s=dt_s).to_dict(),
                        **delivery_summary,
                    },
                    sort_keys=True,
                )
            )
        else:
            plan = build_runtime_input_source_step_loop_plan(
                selection,
                config=runtime_config,
                publisher=WebSocketStatePublisher(server),
            )
            await run_runtime_input_source_step_loop(
                plan,
                steps=steps,
                dt_s=dt_s,
                interval_s=interval_s,
            )

        _log(f"Completed after publishing {steps} frame(s).")


def run_input_source_websocket_publisher(
    *,
    input_source: str,
    host: str = DEFAULT_WEBSOCKET_PUBLISHER_HOST,
    port: int = DEFAULT_WEBSOCKET_PUBLISHER_PORT,
    steps: int = DEFAULT_WEBSOCKET_PUBLISHER_STEPS,
    dt_s: float = DEFAULT_WEBSOCKET_PUBLISHER_DT_S,
    interval_s: float = DEFAULT_WEBSOCKET_PUBLISHER_INTERVAL_S,
    grace_period_s: float = DEFAULT_WEBSOCKET_PUBLISHER_GRACE_PERIOD_S,
    preset: str | None = None,
    robot_profile_id: str = "fast_arm",
) -> None:
    _validate_host(host)
    _validate_port(port)
    _validate_steps(steps)
    _validate_dt_s(dt_s)
    _validate_interval_s(interval_s)
    _validate_grace_period_s(grace_period_s)
    get_input_source_registration(input_source)
    asyncio.run(
        _run_input_source_websocket_publisher_async(
            host=host,
            port=port,
            steps=steps,
            dt_s=dt_s,
            interval_s=interval_s,
            grace_period_s=grace_period_s,
            preset=preset,
            input_source=input_source,
            robot_profile_id=robot_profile_id,
        )
    )


async def _run_replay_mujoco_websocket_publisher_async(
    *,
    host: str,
    port: int,
    steps: int,
    dt_s: float,
    interval_s: float,
    grace_period_s: float,
    preset: str | None,
    robot_profile_id: str,
) -> None:
    runtime_config = RuntimeConfig(dt_s=dt_s, robot_profile_id=robot_profile_id)

    async with WebSocketPublisherServer(host=host, port=port) as server:
        _log(f"serving on ws://{server.host}:{server.bound_port}")
        _log(f"Waiting for viewer during grace period ({grace_period_s:.2f}s)")

        has_client = await server.wait_for_client(timeout_s=grace_period_s)
        if not has_client:
            _log("No viewer connected during grace period; no payloads published.")
            _log("Completed without publishing because no viewer connected.")
            return

        _log("Viewer connected; publishing started.")

        pipeline = build_concrete_mujoco_pipeline(
            frames=_sweep_x_replay_frames(steps) if preset == "sweep_x" else (_default_replay_frame(),),
            config=runtime_config,
            loop=False if preset == "sweep_x" else True,
            publisher=WebSocketStatePublisher(server),
        )

        if preset == "sweep_x":
            for index in range(steps):
                frame = pipeline.input_source.read_frame()
                intent = pipeline.map_input(frame)
                pre_step_state = pipeline.simulator.snapshot()
                safety_result = pipeline.execute_intent(
                    intent,
                    dt_s=dt_s,
                    pre_step_state=pre_step_state,
                    source_state=build_runtime_input_source_state_from_metadata(
                        frame.metadata,
                        default_source_kind=frame.source,
                    ),
                )
                pipeline.simulator.step(dt_s)

                state = pipeline.simulator.snapshot()
                annotated_state = _annotate_sweep_x_state(
                    pipeline,
                    state,
                    intent,
                    safety_result,
                )
                await pipeline.publisher.publish(annotated_state)

                if interval_s > 0.0 and index + 1 < steps:
                    await asyncio.sleep(interval_s)
            _log(f"Completed after publishing {steps} frame(s).")
            return

        for index in range(steps):
            await pipeline.run_once(dt_s=dt_s)
            if interval_s > 0.0 and index + 1 < steps:
                await asyncio.sleep(interval_s)

        _log(f"Completed after publishing {steps} frame(s).")


def run_replay_mujoco_websocket_publisher(
    *,
    host: str = DEFAULT_WEBSOCKET_PUBLISHER_HOST,
    port: int = DEFAULT_WEBSOCKET_PUBLISHER_PORT,
    steps: int = DEFAULT_WEBSOCKET_PUBLISHER_STEPS,
    dt_s: float = DEFAULT_WEBSOCKET_PUBLISHER_DT_S,
    interval_s: float = DEFAULT_WEBSOCKET_PUBLISHER_INTERVAL_S,
    grace_period_s: float = DEFAULT_WEBSOCKET_PUBLISHER_GRACE_PERIOD_S,
    preset: str | None = None,
    robot_profile_id: str = "fast_arm",
) -> None:
    _validate_host(host)
    _validate_port(port)
    _validate_steps(steps)
    _validate_dt_s(dt_s)
    _validate_interval_s(interval_s)
    _validate_grace_period_s(grace_period_s)
    if preset is not None and preset not in SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS:
        raise ValueError("unsupported websocket publisher preset")

    asyncio.run(
        _run_replay_mujoco_websocket_publisher_async(
            host=host,
            port=port,
            steps=steps,
            dt_s=dt_s,
            interval_s=interval_s,
            grace_period_s=grace_period_s,
            preset=preset,
            robot_profile_id=robot_profile_id,
        )
    )


__all__ = [
    "SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS",
    "run_input_source_websocket_publisher",
    "run_replay_mujoco_websocket_publisher",
]
