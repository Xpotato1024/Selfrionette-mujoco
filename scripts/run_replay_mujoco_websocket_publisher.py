from __future__ import annotations

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from selfrionette.input_sources.registry import SUPPORTED_INPUT_SOURCE_NAMES
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.input_step_loop import (
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.runtime.viewer_control_ingress import (
    build_viewer_input_source,
    ingest_viewer_control_message_json,
)
from selfrionette.runtime.input_source_selection import select_runtime_input_source
from selfrionette.runtime.live_timing import AbsoluteDeadlinePacer, LiveRuntimeTimingMetrics
from selfrionette.runtime.live_websocket_delivery import LiveLatestStateWebSocketPublisher
from selfrionette.runtime import run_replay_mujoco_websocket_publisher
from selfrionette.runtime.websocket_publisher_runner import SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS
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
    runtime_config = RuntimeConfig(dt_s=dt_s, robot_profile_id="fast_arm")

    if input_source == "viewer":
        viewer_input_source = build_viewer_input_source()

        def handle_viewer_message(message: str) -> None:
            ingest_viewer_control_message_json(viewer_input_source, message)

        async with WebSocketPublisherServer(host=host, port=port, on_message=handle_viewer_message) as server:
            _log(f"serving on ws://{server.host}:{server.bound_port}")
            _log(f"Waiting for viewer during grace period ({grace_period_s:.2f}s)")

            has_client = await server.wait_for_client(timeout_s=grace_period_s)
            if not has_client:
                _log("No viewer connected during grace period; no payloads published.")
                _log("Completed without publishing because no viewer connected.")
                return

            _log("Viewer connected; publishing started.")

            timing_metrics = LiveRuntimeTimingMetrics()
            pacer = None
            if interval_s > 0.0:
                pacer = AbsoluteDeadlinePacer(interval_s, metrics=timing_metrics)
            async with LiveLatestStateWebSocketPublisher(server) as publisher:
                selection = select_runtime_input_source(input_source, steps=steps, preset=preset)
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

            _log(f"Completed after publishing {steps} frame(s).")
        return

    async with WebSocketPublisherServer(host=host, port=port) as server:
        _log(f"serving on ws://{server.host}:{server.bound_port}")
        _log(f"Waiting for viewer during grace period ({grace_period_s:.2f}s)")

        has_client = await server.wait_for_client(timeout_s=grace_period_s)
        if not has_client:
            _log("No viewer connected during grace period; no payloads published.")
            _log("Completed without publishing because no viewer connected.")
            return

        _log("Viewer connected; publishing started.")

        selection = select_runtime_input_source(input_source, steps=steps, preset=preset)
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
    parser.add_argument(
        "--interval-s",
        type=_non_negative_float,
        default=0.0,
        help=(
            "step interval in seconds; viewer live mode uses it as an absolute cadence period, "
            "zero disables pacing"
        ),
    )
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
