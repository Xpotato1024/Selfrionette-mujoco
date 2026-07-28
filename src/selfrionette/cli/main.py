"""Plugin-aware command-line entry for existing runtime operations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from selfrionette.plugins.robots.catalog import resolve_robot_bundle
from selfrionette.plugins.input_sources.catalog import (
    INPUT_SOURCE_CATALOG,
)
from selfrionette.runtime.composition.robot_bundle import (
    ENDPOINT_COMMAND_V1,
    ENDPOINT_POSE_V1,
    QPOS_FEASIBILITY_V1,
    RESET_INITIAL_STATE_V1,
)
from selfrionette.runtime.runners.dry_run import run_replay_mujoco_dry_run
from selfrionette.runtime.runners.websocket_publisher import (
    SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS,
    run_input_source_websocket_publisher,
    run_replay_mujoco_websocket_publisher,
)
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.runtime.experiment.input_source import InputSourceMode

_RUNTIME_CAPABILITIES = (
    RESET_INITIAL_STATE_V1,
    ENDPOINT_POSE_V1,
    ENDPOINT_COMMAND_V1,
    QPOS_FEASIBILITY_V1,
)
CLI_INPUT_SOURCE_NAMES = (
    "programmed_target",
    "replay",
    "noop",
    "viewer",
)
if any(source_name not in INPUT_SOURCE_CATALOG.aliases for source_name in CLI_INPUT_SOURCE_NAMES):
    raise RuntimeError("CLI input source policy references an unknown source")
REPLAY_INPUT_SOURCE_NAMES = tuple(
    source_name
    for source_name in CLI_INPUT_SOURCE_NAMES
    if INPUT_SOURCE_CATALOG.resolve(source_name).plugin.mode
    in {InputSourceMode.OFFLINE, InputSourceMode.REPLAY}
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0.0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def _port(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 65535:
        raise argparse.ArgumentTypeError("port must be in the range 1..65535")
    return parsed


def _add_robot_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--robot",
        required=True,
        help="Robot Catalog ID; no robot is selected implicitly",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="selfrionette")
    commands = parser.add_subparsers(dest="command", required=True)

    replay = commands.add_parser("replay", help="run the deterministic MuJoCo replay")
    _add_robot_argument(replay)
    replay.add_argument("--steps", type=_positive_int, default=1)
    replay.add_argument("--dt-s", type=_positive_float, default=None)
    replay.add_argument("--preset", choices=("sweep_x",), default=None)
    replay.add_argument("--output", type=Path, default=None)
    replay.add_argument(
        "--input-source",
        choices=REPLAY_INPUT_SOURCE_NAMES,
        default=None,
    )

    viewer = commands.add_parser(
        "viewer",
        help="publish replay payloads to an existing WebSocket viewer client",
    )
    _add_robot_argument(viewer)
    viewer.add_argument("--host", default="127.0.0.1")
    viewer.add_argument("--port", type=_port, default=8766)
    viewer.add_argument("--steps", type=_positive_int, default=1)
    viewer.add_argument("--dt-s", type=_positive_float, default=1.0 / 60.0)
    viewer.add_argument("--interval-s", type=_non_negative_float, default=0.0)
    viewer.add_argument("--grace-period-s", type=_non_negative_float, default=0.05)
    viewer.add_argument(
        "--preset",
        choices=SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS,
        default=None,
    )
    viewer.add_argument(
        "--input-source",
        choices=CLI_INPUT_SOURCE_NAMES,
        default=None,
    )
    return parser


def _resolve_runtime_capabilities(robot_id: str) -> None:
    bundle = resolve_robot_bundle(robot_id)
    for capability in _RUNTIME_CAPABILITIES:
        bundle.provider(capability)


def _run(args: argparse.Namespace) -> int:
    _resolve_runtime_capabilities(args.robot)
    if args.command == "replay":
        output = args.output if args.output is not None else sys.stdout
        if args.input_source is None:
            run_replay_mujoco_dry_run(
                steps=args.steps,
                dt_s=args.dt_s,
                output=output,
                preset=args.preset,
                robot_profile_id=args.robot,
            )
        else:
            selection = select_runtime_input_source(
                args.input_source,
                steps=args.steps,
                preset=args.preset,
            )
            run_kwargs = {
                "steps": args.steps,
                "dt_s": args.dt_s,
                "output": output,
                "robot_profile_id": args.robot,
            }
            adapter = selection.execution_adapter
            if (
                adapter is not None
                and adapter.annotates_target_position
                and not adapter.uses_viewer_endpoint_compatibility
            ):
                run_kwargs["preset"] = "sweep_x"
            else:
                run_kwargs["frames"] = selection.frames
            run_replay_mujoco_dry_run(**run_kwargs)
        return 0
    if args.command == "viewer":
        runner = (
            run_replay_mujoco_websocket_publisher
            if args.input_source is None
            else run_input_source_websocket_publisher
        )
        run_kwargs = {
            "host": args.host,
            "port": args.port,
            "steps": args.steps,
            "dt_s": args.dt_s,
            "interval_s": args.interval_s,
            "grace_period_s": args.grace_period_s,
            "preset": args.preset,
            "robot_profile_id": args.robot,
        }
        if args.input_source is not None:
            run_kwargs["input_source"] = args.input_source
        runner(**run_kwargs)
        return 0
    raise AssertionError(f"unhandled command {args.command!r}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except (RuntimeError, ValueError) as exc:
        print(f"selfrionette: error: {exc}", file=sys.stderr)
        return 1


__all__ = ["build_parser", "main"]
