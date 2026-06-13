from __future__ import annotations

import asyncio

from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.replay_mujoco_pipeline import build_replay_mujoco_pipeline
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
        metadata={"preset": "r6-c-p1-default"},
    )


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
) -> None:
    runtime_config = RuntimeConfig(dt_s=dt_s)

    async with WebSocketPublisherServer(host=host, port=port) as server:
        pipeline = build_replay_mujoco_pipeline(
            frames=(_default_replay_frame(),),
            config=runtime_config,
            loop=True,
            publisher=WebSocketStatePublisher(server),
        )

        if grace_period_s > 0.0:
            await server.wait_for_client(timeout_s=grace_period_s)

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
) -> None:
    _validate_host(host)
    _validate_port(port)
    _validate_steps(steps)
    _validate_dt_s(dt_s)
    _validate_interval_s(interval_s)
    _validate_grace_period_s(grace_period_s)

    asyncio.run(
        _run_replay_mujoco_websocket_publisher_async(
            host=host,
            port=port,
            steps=steps,
            dt_s=dt_s,
            interval_s=interval_s,
            grace_period_s=grace_period_s,
        )
    )


__all__ = ["run_replay_mujoco_websocket_publisher"]
