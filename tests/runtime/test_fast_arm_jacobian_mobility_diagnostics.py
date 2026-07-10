from __future__ import annotations

import json
import math

import pytest

from selfrionette.runtime.jacobian_mobility_diagnostics import run_fast_arm_jacobian_mobility_diagnostics


def test_fast_arm_diagnostic_has_explicit_mapping_and_deterministic_pose_sweep() -> None:
    first = run_fast_arm_jacobian_mobility_diagnostics()
    second = run_fast_arm_jacobian_mobility_diagnostics()
    assert first.to_json() == second.to_json()
    assert [pose.label for pose in first.poses] == [
        "default_pose", "sholder_joint_1_positive_nearby", "sholder_joint_1_negative_nearby",
        "sholder_joint_2_positive_nearby", "sholder_joint_2_negative_nearby",
        "sholder_joint_3_positive_nearby", "sholder_joint_3_negative_nearby",
        "elbow_joint_positive_nearby", "elbow_joint_negative_nearby",
    ]
    assert [item["joint_name"] for item in first.controlled_dof_mapping] == [
        "sholder_joint_1", "sholder_joint_2", "sholder_joint_3", "elbow_joint"
    ]
    assert all(len(pose.finite_difference.jacobian) == 3 and len(pose.finite_difference.jacobian[0]) == 4 for pose in first.poses)


def test_fast_arm_default_pose_records_native_comparison_and_axis_metrics() -> None:
    result = run_fast_arm_jacobian_mobility_diagnostics()
    default = result.poses[0]
    assert default.qpos_rad == pytest.approx((0.0, -math.pi / 2.0, 0.0, 0.0), abs=1e-12)
    assert default.jacobian_difference_norm < 1e-3
    assert default.finite_difference.rank == default.native.rank
    assert default.finite_difference.row_norms[0] < default.finite_difference.row_norms[1]
    assert default.finite_difference.row_norms[0] < default.finite_difference.row_norms[2]
    assert len(default.directions) == 6
    assert default.directions[0].label == "+X"
    assert default.directions[0].delta.requested_delta_m[0] > 0.0


def test_fast_arm_sensitivity_contains_lower_current_upper_points_and_json_is_finite_safe() -> None:
    result = run_fast_arm_jacobian_mobility_diagnostics()
    for points in (result.epsilon_sensitivity, result.damping_sensitivity, result.qpos_cap_sensitivity):
        assert len(points) == 3
        assert points[1].value > points[0].value
        assert points[2].value > points[1].value
    payload = json.loads(result.to_json())
    assert payload["schema_version"] == "r7-e-p9-v1"
    assert payload["poses"][0]["finite_difference"]["condition_number"] in ("Infinity", None) or math.isfinite(payload["poses"][0]["finite_difference"]["condition_number"])
