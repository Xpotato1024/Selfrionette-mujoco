from __future__ import annotations

from selfrionette.runtime import run_fast_arm_endpoint_trajectory_diagnostics


def test_endpoint_trajectory_diagnostics_cover_all_axis_commands() -> None:
    diagnostics = run_fast_arm_endpoint_trajectory_diagnostics(
        trajectory_steps=5,
        trajectory_delta_m=0.005,
    )

    assert [result.command_label for result in diagnostics] == ["+x", "-x", "+y", "-y", "+z", "-z"]
    for result in diagnostics:
        assert result.step_count == 5
        assert len(result.initial_tip_position_m) == 3
        assert len(result.initial_qpos) == 4
        assert len(result.records) == 5
        assert result.summary.step_count == 5
        assert result.summary.saturation_step is None or result.summary.saturation_step >= 1
        assert result.summary.first_rejection_step is None or result.summary.first_rejection_step >= 1
        assert result.summary.first_off_plane_step is None or result.summary.first_off_plane_step >= 1
        assert result.summary.safe_hold_step is None or result.summary.safe_hold_step >= 1
        for record in result.records:
            assert len(record.desired_endpoint_m) == 3
            assert len(record.qpos_before) == 4
            assert len(record.qpos_after) == 4
            assert len(record.tip_before_m) == 3
            assert len(record.tip_after_m) == 3
            assert len(record.actual_delta_m) == 3
            assert len(record.cumulative_actual_delta_m) == 3
            assert record.status in {"pass", "limitation", "rejected", "unavailable"}
            assert record.reason


def test_xy_trajectory_records_dof_allocation_limitation_without_rejection() -> None:
    diagnostics = {
        result.command_label: result
        for result in run_fast_arm_endpoint_trajectory_diagnostics(
            trajectory_steps=5,
            trajectory_delta_m=0.005,
        )
    }

    for label in ["+x", "-x", "+y", "-y"]:
        summary = diagnostics[label].summary
        assert summary.final_status == "limitation"
        assert summary.final_reason == "off_plane"
        assert summary.first_off_plane_step == 1
        assert summary.first_rejection_step is None
        assert summary.safe_hold_step is None
        assert summary.decision == "current_solver_dof_allocation_limitation"
        assert all(record.target_rejected is False for record in diagnostics[label].records)


def test_z_trajectory_starts_aligned_then_degrades_under_repeated_commands() -> None:
    diagnostics = {
        result.command_label: result
        for result in run_fast_arm_endpoint_trajectory_diagnostics(
            trajectory_steps=5,
            trajectory_delta_m=0.005,
        )
    }

    for label in ["+z", "-z"]:
        records = diagnostics[label].records
        summary = diagnostics[label].summary
        assert records[0].status == "pass"
        assert records[0].reason == "aligned"
        assert summary.first_rejection_step is None
        assert summary.first_opposite_direction_step == 3
        assert summary.final_status == "limitation"
        assert summary.final_reason == "opposite_direction"
        assert summary.decision == "z_primary_but_degrades_over_repeated_commands"


def test_trajectory_summary_contains_cumulative_drift_metrics() -> None:
    diagnostics = run_fast_arm_endpoint_trajectory_diagnostics(
        trajectory_steps=5,
        trajectory_delta_m=0.005,
    )

    for result in diagnostics:
        summary = result.summary
        assert len(summary.cumulative_commanded_delta_m) == 3
        assert len(summary.cumulative_actual_delta_m) == 3
        assert summary.mean_direction_dot is not None
        assert summary.orthogonal_drift_m >= 0.0
        assert summary.drift_from_command_axis_m != 0.0
