from __future__ import annotations

import pytest

from selfrionette.runtime import (
    run_fast_arm_endpoint_motion_sanity,
    run_fast_arm_local_jacobian_diagnostics,
)


def test_local_jacobian_diagnostics_cover_qpos_0_to_3_for_nearby_poses() -> None:
    diagnostics = run_fast_arm_local_jacobian_diagnostics()

    assert [pose.pose_label for pose in diagnostics] == [
        "initial",
        "q1_offset",
        "q3_offset",
        "q1_q3_offset",
    ]
    for pose in diagnostics:
        assert len(pose.qpos) == 4
        assert len(pose.tip_position_m) == 3
        assert len(pose.jacobian_matrix) == 3
        assert all(len(row) == 4 for row in pose.jacobian_matrix)
        assert [column.qpos_index for column in pose.columns] == [0, 1, 2, 3]
        assert [column.joint_name for column in pose.columns] == [
            "sholder_joint_1",
            "sholder_joint_2",
            "sholder_joint_3",
            "elbow_joint",
        ]
        for column in pose.columns:
            assert len(column.plus_tip_delta_m) == 3
            assert len(column.minus_tip_delta_m) == 3
            assert len(column.central_difference_column) == 3
            assert column.norm >= 0.0


def test_local_jacobian_pins_initial_q1_z_and_q3_y_contribution() -> None:
    initial = run_fast_arm_local_jacobian_diagnostics()[0]
    columns = {column.qpos_index: column for column in initial.columns}

    assert columns[0].dominant_axis == "none"
    assert columns[1].dominant_axis == "z"
    assert columns[1].dominant_sign == -1
    assert columns[1].central_difference_column[2] < -0.5
    assert columns[2].dominant_axis == "none"
    assert columns[3].dominant_axis == "y"
    assert columns[3].dominant_sign == 1
    assert columns[3].central_difference_column[1] > 0.2


def test_nearby_pose_jacobian_shows_q0_q2_are_singular_or_pose_dependent() -> None:
    diagnostics = {pose.pose_label: pose for pose in run_fast_arm_local_jacobian_diagnostics()}

    initial_columns = {column.qpos_index: column for column in diagnostics["initial"].columns}
    q1_offset_columns = {column.qpos_index: column for column in diagnostics["q1_offset"].columns}
    q3_offset_columns = {column.qpos_index: column for column in diagnostics["q3_offset"].columns}

    assert initial_columns[0].norm == pytest.approx(0.0, abs=1e-9)
    assert initial_columns[2].norm == pytest.approx(0.0, abs=1e-9)
    assert q1_offset_columns[0].norm > 0.05
    assert q3_offset_columns[2].norm > 0.02
    assert diagnostics["initial"].joint_contribution_summary["z"] == ("sholder_joint_2:-z",)
    assert "elbow_joint:+y" in diagnostics["initial"].joint_contribution_summary["y"]


def test_short_step_sanity_keeps_z_aligned_and_xy_as_limitations() -> None:
    results = {result.command_label: result for result in run_fast_arm_endpoint_motion_sanity()}

    assert results["+z"].status == "pass"
    assert results["+z"].reason == "aligned"
    assert results["-z"].status == "pass"
    assert results["-z"].reason == "aligned"
    for label in ["+x", "-x", "+y", "-y"]:
        assert results[label].status == "limitation"
        assert results[label].reason == "off_plane"
        assert results[label].target_rejected is False
