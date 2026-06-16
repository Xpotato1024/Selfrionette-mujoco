from __future__ import annotations

import asyncio

from selfrionette.input_sources import build_sweep_x_input_source
from selfrionette.mujoco_backend import snapshot_mujoco_state
from selfrionette.runtime.concrete_mujoco_pipeline import DEFAULT_CONCRETE_TARGET_POSITION_M, build_concrete_mujoco_pipeline
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import WebSocketPublisherServer, WebSocketStatePublisher

DEFAULT_WEBSOCKET_PUBLISHER_HOST = "127.0.0.1"
DEFAULT_WEBSOCKET_PUBLISHER_PORT = 8766
DEFAULT_WEBSOCKET_PUBLISHER_STEPS = 1
DEFAULT_WEBSOCKET_PUBLISHER_DT_S = 1.0 / 60.0
DEFAULT_WEBSOCKET_PUBLISHER_INTERVAL_S = 0.0
DEFAULT_WEBSOCKET_PUBLISHER_GRACE_PERIOD_S = 0.05


def _default_replay_frame() -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={
            "preset": "r6-c-p1-default",
            "target_position_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
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


async def _run_replay_mujoco_websocket_publisher_async(
    *,
    host: str,
    port: int,
    steps: int,
    dt_s: float,
    interval_s: float,
    grace_period_s: float,
    preset: str | None,
) -> None:
    runtime_config = RuntimeConfig(dt_s=dt_s)

    async with WebSocketPublisherServer(host=host, port=port) as server:
        pipeline = build_concrete_mujoco_pipeline(
            frames=_sweep_x_replay_frames(steps) if preset == "sweep_x" else (_default_replay_frame(),),
            config=runtime_config,
            loop=False if preset == "sweep_x" else True,
            publisher=WebSocketStatePublisher(server),
        )

        if grace_period_s > 0.0:
            await server.wait_for_client(timeout_s=grace_period_s)

        if preset == "sweep_x":
            for index in range(steps):
                frame = pipeline.input_source.read_frame()
                intent = pipeline.input_interpreter.interpret(frame)
                command = pipeline.motion_generator.update(intent, dt_s)
                pipeline.simulator.apply_command(command)
                pipeline.simulator.step(dt_s)

                state = pipeline.simulator.snapshot()
                annotated_state = snapshot_mujoco_state(
                    pipeline.simulator.model,
                    pipeline.simulator.data,
                    frame_index=state.frame_index,
                    target_position_m=tuple(intent.metadata["desired_endpoint_m"]),
                    metadata={
                        **state.metadata,
                        **intent.metadata,
                        "preset": "sweep_x",
                    },
                )
                await pipeline.publisher.publish(annotated_state)

                if interval_s > 0.0 and index + 1 < steps:
                    await asyncio.sleep(interval_s)
            return

        for index in range(steps):
            await pipeline.run_once(dt_s=dt_s)
            if interval_s > 0.0 and index + 1 < steps:
                await asyncio.sleep(interval_s)


def run_replay_mujoco_websocket_publisher(
    *,
    host: str = DEFAULT_WEBSOCKET_PUBLISHER_HOST,
    port: int = DEFAULT_WEBSOCKET_PUBLISHER_PORT,
    steps: int = DEFAULT_WEBSOCKET_PUBLISHER_STEPS,
    dt_s: float = DEFAULT_WEBSOCKET_PUBLISHER_DT_S,
    interval_s: float = DEFAULT_WEBSOCKET_PUBLISHER_INTERVAL_S,
    grace_period_s: float = DEFAULT_WEBSOCKET_PUBLISHER_GRACE_PERIOD_S,
    preset: str | None = None,
) -> None:
    _validate_host(host)
    _validate_port(port)
    _validate_steps(steps)
    _validate_dt_s(dt_s)
    _validate_interval_s(interval_s)
    _validate_grace_period_s(grace_period_s)
    if preset is not None and preset != "sweep_x":
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
        )
    )


__all__ = ["run_replay_mujoco_websocket_publisher"]
