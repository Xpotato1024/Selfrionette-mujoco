from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from selfrionette.runtime import run_replay_mujoco_websocket_publisher


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
        help="delay after server start before the first payload is published",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_replay_mujoco_websocket_publisher(
        host=args.host,
        port=args.port,
        steps=args.steps,
        dt_s=args.dt_s,
        interval_s=args.interval_s,
        grace_period_s=args.grace_period_s,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
