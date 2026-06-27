from __future__ import annotations

import pytest

from selfrionette.runtime import run_fast_arm_endpoint_motion_sanity


def test_initial_tip_workspace_diagnostics_are_structured_for_all_axes() -> None:
    results = run_fast_arm_endpoint_motion_sanity()

    assert [result.command_label for result in results] == ["+x", "-x", "+y", "-y", "+z", "-z"]
    for result in results:
        assert result.base_endpoint_source == "initial_tip"
        assert result.initial_tip_position_m == pytest.approx((0.622, 0.0, 0.7), abs=1e-9)
        assert result.solver_input_endpoint_m == pytest.approx(result.desired_endpoint_m, abs=1e-9)
        assert result.reachable_workspace_summary != "unavailable"
        assert isinstance(result.reachable_workspace_summary, dict)
        assert result.reachable_workspace_summary["solver_base_position_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)
        assert result.reachable_workspace_summary["max_radius_m"] == pytest.approx(0.73, abs=1e-9)
        assert result.distance_from_solver_base_m != "unavailable"
        assert float(result.distance_from_solver_base_m) > float(result.reachable_workspace_summary["max_radius_m"])
        assert result.target_constraints_summary != "unavailable"
        assert result.frame_mapping_summary != "unavailable"
        assert isinstance(result.frame_mapping_summary, dict)
        assert result.frame_mapping_summary["mapping_status"] == "not transformed in endpoint_motion_sanity"
        assert result.diagnosis == "initial_tip_target_outside_solver_reachable_workspace"


def test_initial_tip_workspace_diagnostics_keep_rejection_details_without_crashing() -> None:
    results = run_fast_arm_endpoint_motion_sanity()

    for result in results:
        assert result.status == "rejected"
        assert result.target_rejected is True
        assert result.target_rejection_reason == "target_unreachable"
        assert result.target_rejection_message == "target_position_m is outside the reachable workspace"
        assert result.rejected_desired_endpoint_m == pytest.approx(result.desired_endpoint_m, abs=1e-9)
        assert result.solver_seed_qpos == "unavailable"
        assert result.solver_result_qpos == "unavailable"
        assert len(result.qpos_before) == 4
        assert len(result.qpos_after) == 4
