from __future__ import annotations

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from selfrionette.input_sources.programmed_target import build_sweep_x_input_source
from selfrionette.input_sources.registry import SUPPORTED_INPUT_SOURCE_NAMES
from selfrionette.mujoco_backend import snapshot_mujoco_state
from selfrionette.runtime.concrete_mujoco_pipeline import DEFAULT_CONCRETE_TARGET_POSITION_M, build_concrete_mujoco_pipeline
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.input_source_selection import select_runtime_input_source
from selfrionette.runtime import run_replay_mujoco_websocket_publisher
from selfrionette.runtime.websocket_publisher_runner import SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import WebSocketPublisherServer, WebSocketStatePublisher

DEFAULT_WEBSOCKET_PUBLISHER_HOST = "127.0.0.1"
DEFAULT_WEBSOCKET_PUBLISHER_PORT = 8766
DEFAULT_WEBSOCKET_PUBLISHER_STEPS = 1
DEFAULT_WEBSOCKET_PUBLISHER_DT_S = 1.0 / 60.0
DEFAULT_WEBSOCKET_PUBLISHER_INTERVAL_S = 0.0
DEFAULT_WEBSOCKET_PUBLISHER_GRACE_PERIOD_S = 0.05


def _log(message: str) -> None:
    print(message, flush=True)


def _host(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("host must not be empty")
    return value


def _port(value: str) -> int:
    parsed = int(value)
    if parsed < 1 or parsed > 65535:
        raise argparse.ArgumentTypeError("port must be in the range 1..65535")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("steps must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("dt-s must be positive")
    return parsed


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


def _annotate_sweep_x_state(pipeline, state, intent):
    return snapshot_mujoco_state(
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
) -> None:
    runtime_config = RuntimeConfig(dt_s=dt_s)

    async with WebSocketPublisherServer(host=host, port=port) as server:
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
            replay_initial_metadata=_default_replay_frame().metadata,
        )
        pipeline = build_concrete_mujoco_pipeline(
            frames=selection.frames,
            config=runtime_config,
            loop=selection.loop,
            publisher=WebSocketStatePublisher(server),
        )

        if selection.source_name == "programmed_target":
            for index in range(steps):
                frame = pipeline.input_source.read_frame()
                intent = pipeline.input_interpreter.interpret(frame)
                command = pipeline.motion_generator.update(intent, dt_s)
                pipeline.simulator.apply_command(command)
                pipeline.simulator.step(dt_s)

                state = pipeline.simulator.snapshot()
                annotated_state = _annotate_sweep_x_state(pipeline, state, intent)
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


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0.0:
        raise argparse.ArgumentTypeError("interval-s must be non-negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local WebSocket publisher for replayed MuJoCo payloads.")
    parser.add_argument("--host", type=_host, default="127.0.0.1", help="loopback host to bind")
    parser.add_argument("--port", type=_port, default=8766, help="TCP port to bind")
    parser.add_argument("--steps", type=_positive_int, default=1, help="number of replay steps to run")
    parser.add_argument("--dt-s", type=_positive_float, default=1.0 / 60.0, help="step duration in seconds")
    parser.add_argument("--interval-s", type=_non_negative_float, default=0.0, help="delay between steps in seconds")
    parser.add_argument(
        "--grace-period-s",
        type=_non_negative_float,
        default=0.05,
        help="seconds to wait for a viewer WebSocket connection before publishing",
    )
    parser.add_argument(
        "--input-source",
        choices=SUPPORTED_INPUT_SOURCE_NAMES,
        default=None,
        help="optional runtime input source registry selection",
    )
    parser.add_argument(
        "--preset",
        choices=SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS,
        default=None,
        help="optional replay preset to publish",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input_source is None:
        run_replay_mujoco_websocket_publisher(
            host=args.host,
            port=args.port,
            steps=args.steps,
            dt_s=args.dt_s,
            interval_s=args.interval_s,
            grace_period_s=args.grace_period_s,
            preset=args.preset,
        )
        return 0

    asyncio.run(
        _run_input_source_websocket_publisher_async(
            host=args.host,
            port=args.port,
            steps=args.steps,
            dt_s=args.dt_s,
            interval_s=args.interval_s,
            grace_period_s=args.grace_period_s,
            preset=args.preset,
            input_source=args.input_source,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
