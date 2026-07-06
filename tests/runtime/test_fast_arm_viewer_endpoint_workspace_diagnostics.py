from __future__ import annotations

import pytest

from selfrionette.runtime import sample_fast_arm_viewer_endpoint_workspace


def test_fast_arm_viewer_endpoint_workspace_diagnostics_cover_required_samples() -> None:
    diagnostics = sample_fast_arm_viewer_endpoint_workspace()
    by_label = {diagnostic.sample_label: diagnostic for diagnostic in diagnostics}

    assert {
        "default_qpos",
        "joint_1_positive_small",
        "joint_1_negative_small",
        "joint_2_positive_small",
        "joint_2_negative_small",
        "joint_3_positive_small",
        "joint_3_negative_small",
        "elbow_positive_small",
        "elbow_negative_small",
        "desired_initial_tip_x_positive_small",
        "desired_initial_tip_x_negative_small",
        "desired_initial_tip_y_positive_small",
        "desired_initial_tip_y_negative_small",
        "desired_initial_tip_z_positive_small",
        "desired_initial_tip_z_negative_small",
        "safe_endpoint",
        "initial_mujoco_tip",
    }.issubset(by_label)

    default = by_label["default_qpos"]
    assert default.sample_kind == "qpos_sample"
    assert default.qpos_sample == pytest.approx((0.0, -1.5707963267948966, 0.0, 0.0), abs=1e-12)
    assert default.mujoco_tip_site_world_position_m == pytest.approx((0.622, 0.0, 0.7), abs=1e-9)
    assert len(default.solver_local_fk_endpoint_m) == 3
    assert len(default.model_aligned_fk_endpoint_m) == 3
    assert len(default.solver_local_ik_target_m) == 3


def test_fast_arm_viewer_endpoint_workspace_diagnostics_record_ik_candidate_continuity() -> None:
    diagnostics = sample_fast_arm_viewer_endpoint_workspace()
    by_label = {diagnostic.sample_label: diagnostic for diagnostic in diagnostics}

    first_space_like = by_label["desired_initial_tip_z_positive_small"]

    assert first_space_like.sample_kind == "desired_world_endpoint_sample"
    assert first_space_like.desired_world_endpoint_m == pytest.approx((0.622, 0.0, 0.71), abs=1e-9)
    assert first_space_like.solver_local_ik_target_m == pytest.approx((0.6910000000000001, 0.0, 0.01), abs=1e-9)
    assert first_space_like.ik_success is True
    assert first_space_like.ik_output_qpos_rad is not None
    assert len(first_space_like.ik_output_qpos_rad) == 4
    assert first_space_like.qpos_delta_norm_from_seed_rad is not None
    assert first_space_like.qpos_delta_norm_from_seed_rad > 1.0
    assert first_space_like.rejection_reason is None

    safe_endpoint = by_label["safe_endpoint"]
    assert safe_endpoint.desired_world_endpoint_m == pytest.approx((0.6, 0.0, 0.1), abs=1e-12)
    assert safe_endpoint.solver_local_ik_target_m == pytest.approx((0.669, 0.0, -0.6), abs=1e-9)
    assert safe_endpoint.ik_success in {True, False}
