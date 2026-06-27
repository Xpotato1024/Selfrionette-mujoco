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


def _format_value(value: object) -> str:
    if hasattr(value, "__dataclass_fields__"):
        items = {
            field_name: getattr(value, field_name)
            for field_name in value.__dataclass_fields__  # type: ignore[attr-defined]
        }
        return _format_value(items)
    if isinstance(value, tuple):
        formatted_components: list[str] = []
        for component in value:
            if isinstance(component, float):
                formatted_components.append(f"{component:.6f}")
            else:
                formatted_components.append(_format_value(component))
        return "[" + ", ".join(formatted_components) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}={_format_value(item)}" for key, item in value.items()) + "}"
    return str(value)


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
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="print structured backend diagnostics for command, solver, qpos, and MuJoCo tip alignment",
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
        fields = (
            f"case_label={result.command_label}",
            f"axis={result.command_label}",
            f"status={result.status}",
            f"reason={result.reason}",
            f"base_endpoint_source={result.base_endpoint_source}",
            f"base_endpoint_m={_format_vector3(result.base_endpoint_m)}",
            f"commanded_delta_m={_format_vector3(result.commanded_delta_m)}",
            f"actual_delta_m={_format_vector3(result.actual_delta_m)}",
            f"initial_tip_position_m={_format_vector3(result.initial_tip_position_m)}",
            f"final_tip_position_m={_format_vector3(result.final_tip_position_m)}",
            f"desired_endpoint_m={_format_vector3(result.desired_endpoint_m)}",
            f"target_position_m={_format_vector3(result.target_position_m)}",
            f"target_rejected={result.target_rejected}",
            f"target_rejection_reason={result.target_rejection_reason}",
            f"target_rejection_message={result.target_rejection_message}",
            f"qpos_before={list(result.qpos_before[:4])}",
            f"qpos_after={list(result.qpos_after[:4])}",
            f"direction_dot={result.direction_dot}",
        )
        if args.diagnostics:
            fields = fields + (
                f"solver_input_endpoint_m={_format_value(result.solver_input_endpoint_m)}",
                f"solver_seed_qpos={_format_value(result.solver_seed_qpos)}",
                f"solver_result_qpos={_format_value(result.solver_result_qpos)}",
                f"reachable_workspace_summary={_format_value(result.reachable_workspace_summary)}",
                f"distance_from_solver_base_m={_format_value(result.distance_from_solver_base_m)}",
                f"target_constraints_summary={_format_value(result.target_constraints_summary)}",
                f"frame_mapping_summary={_format_value(result.frame_mapping_summary)}",
                f"rejected_desired_endpoint_m={_format_value(result.rejected_desired_endpoint_m)}",
                f"last_valid_target_position_m={_format_value(result.last_valid_target_position_m)}",
                f"mujoco_base_link_position_m={_format_value(result.mujoco_base_link_position_m)}",
                f"mujoco_base_link_frame={result.mujoco_base_link_frame}",
                f"mujoco_tip_position_m={_format_value(result.mujoco_tip_position_m)}",
                f"tip_relative_to_base_link_m={_format_value(result.tip_relative_to_base_link_m)}",
                f"tip_relative_to_solver_base_m={_format_value(result.tip_relative_to_solver_base_m)}",
                f"solver_base_world_position_m={_format_value(result.solver_base_world_position_m)}",
                f"solver_local_target_m={_format_value(result.solver_local_target_m)}",
                f"world_target_m={_format_value(result.world_target_m)}",
                f"frame_transform_status={result.frame_transform_status}",
                f"qpos_ref_summary={_format_value(result.qpos_ref_summary)}",
                f"joint_axis_mapping_summary={_format_value(result.joint_axis_mapping_summary)}",
                f"qpos_perturbation_results={_format_value(result.qpos_perturbation_results)}",
                f"solver_to_mujoco_mapping={_format_value(result.solver_to_mujoco_mapping)}",
                f"mujoco_to_solver_mapping={_format_value(result.mujoco_to_solver_mapping)}",
                f"mapping_status={result.mapping_status}",
                f"solver_fk_endpoint_m={_format_value(result.solver_fk_endpoint_m)}",
                f"transformed_solver_fk_world_m={_format_value(result.transformed_solver_fk_world_m)}",
                f"diagnosis={result.diagnosis}",
            )
        print(" ".join(fields))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
