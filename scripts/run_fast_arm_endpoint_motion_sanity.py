from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from selfrionette.runtime import run_fast_arm_endpoint_motion_sanity


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _format_vector3(value: tuple[float, float, float] | None) -> str:
    if value is None:
        return "None"
    return "[" + ", ".join(f"{component:.6f}" for component in value) + "]"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fast_arm endpoint motion sanity check.")
    parser.add_argument(
        "--base-desired-endpoint-m",
        nargs=3,
        type=float,
        default=None,
        metavar=("X", "Y", "Z"),
        help="explicit command-side base endpoint in meters; omitted uses the initial tip position",
    )
    parser.add_argument(
        "--command-delta-m",
        type=_positive_float,
        default=0.02,
        help="small offset applied along each axis in meters",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="optional MuJoCo model path override",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = run_fast_arm_endpoint_motion_sanity(
        base_desired_endpoint_m=(
            None
            if args.base_desired_endpoint_m is None
            else tuple(args.base_desired_endpoint_m)
        ),
        command_delta_m=args.command_delta_m,
        model_path=args.model_path,
    )

    for result in results:
        print(
            " ".join(
                (
                    f"axis={result.command_label}",
                    f"status={result.status}",
                    f"reason={result.reason}",
                    f"base_endpoint_source={result.base_endpoint_source}",
                    f"base_endpoint_m={_format_vector3(result.base_endpoint_m)}",
                    f"commanded_delta={_format_vector3(result.commanded_delta_m)}",
                    f"actual_delta={_format_vector3(result.actual_delta_m)}",
                    f"initial_tip={_format_vector3(result.initial_tip_position_m)}",
                    f"final_tip={_format_vector3(result.final_tip_position_m)}",
                    f"desired_endpoint_m={_format_vector3(result.desired_endpoint_m)}",
                    f"target_position_m={_format_vector3(result.target_position_m)}",
                    f"qpos_before={list(result.qpos_before[:4])}",
                    f"qpos_after={list(result.qpos_after[:4])}",
                    f"direction_dot={result.direction_dot}",
                )
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
