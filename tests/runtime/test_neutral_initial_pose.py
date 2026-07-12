from __future__ import annotations

import math

import pytest

import selfrionette.runtime.neutral_initial_pose as neutral_initial_pose
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime.neutral_initial_pose import (
    HISTORICAL_RAISED_BASELINE_QPOS_RAD,
    evaluate_fast_arm_neutral_initial_pose_candidates,
    format_neutral_pose_ranking,
    generate_fast_arm_neutral_pose_candidates,
    validate_candidate_qpos,
)


@pytest.mark.parametrize(
    ("value", "message"),
    (
        ((0.0, 0.0), "length mismatch"),
        ((0.0, False, 0.0, 0.0), "bool is not numeric"),
        ((0.0, math.nan, 0.0, 0.0), "must be finite"),
        ((0.0, math.inf, 0.0, 0.0), "must be finite"),
        ("0 0 0 0", "numeric sequence"),
    ),
)
def test_candidate_validation_rejects_invalid_values(value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_candidate_qpos(value, expected_length=4)


def test_candidate_generation_is_deterministic_and_duplicate_free() -> None:
    first = generate_fast_arm_neutral_pose_candidates(
        HeadlessMuJoCoSimulator.from_default_fast_arm()
    )
    second = generate_fast_arm_neutral_pose_candidates(
        HeadlessMuJoCoSimulator.from_default_fast_arm()
    )

    assert first == second
    assert first[0].baseline is True
    assert first[0].qpos_rad == pytest.approx(HISTORICAL_RAISED_BASELINE_QPOS_RAD)
    assert len({candidate.qpos_rad for candidate in first}) == len(first)
    assert {candidate.category for candidate in first} >= {
        "baseline",
        "shoulder_lowered",
        "elbow_bent",
        "shoulder_elbow_combined",
        "symmetric_sign_comparison",
    }


def test_evaluator_selects_only_a_lower_bent_valid_candidate() -> None:
    result = evaluate_fast_arm_neutral_initial_pose_candidates()
    by_id = {candidate.candidate_id: candidate for candidate in result.candidates}
    baseline = by_id["historical_raised_baseline"]
    selected = by_id[result.selected_candidate_id]  # type: ignore[index]

    assert result.candidate_count > 20
    assert result.eligible_count > 1
    assert selected.eligible
    assert selected.tip_height_m < baseline.tip_height_m
    assert selected.shoulder_to_tip_extension_m < baseline.shoulder_to_tip_extension_m
    assert selected.contact_count == 0
    assert selected.penetration_count == 0
    assert selected.fk_site_residual_m <= result.selection_contract["fk_site_tolerance_m"]
    assert selected.nearby_sensitivity.evaluated_count == 8
    assert len(selected.directions) == 6
    assert {direction.label for direction in selected.directions} == {
        "+X",
        "-X",
        "+Y",
        "-Y",
        "+Z",
        "-Z",
    }
    assert result.selection_contract["rank_three_required"] is False
    assert "six_direction_progressing_count_desc" in result.selection_contract["ranking_order"]


def test_machine_and_human_outputs_are_deterministic() -> None:
    first = evaluate_fast_arm_neutral_initial_pose_candidates()
    second = evaluate_fast_arm_neutral_initial_pose_candidates()

    assert first.to_json() == second.to_json()
    ranking = format_neutral_pose_ranking(first, limit=3)
    assert f"selected={first.selected_candidate_id}" in ranking
    assert "progressing" in ranking


def test_joint_limit_margin_rejects_out_of_range_candidate() -> None:
    margins, minimum, failures = neutral_initial_pose._joint_margins(
        (1.1, 0.0, 0.0, 0.0),
        (
            {"name": "limited", "limited": True, "range": (-1.0, 1.0)},
            {"name": "u1", "limited": False, "range": (0.0, 0.0)},
            {"name": "u2", "limited": False, "range": (0.0, 0.0)},
            {"name": "u3", "limited": False, "range": (0.0, 0.0)},
        ),
    )

    assert margins[0] == 0.0
    assert minimum == 0.0
    assert failures == ("joint_limit:limited",)


def test_contact_and_penetration_candidates_are_hard_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        neutral_initial_pose,
        "_contact_metrics",
        lambda simulator: (1, 1, -0.001),
    )

    result = evaluate_fast_arm_neutral_initial_pose_candidates()

    assert result.selected_candidate_id is None
    assert result.eligible_count == 0
    assert result.rejection_counts["startup_contact"] == result.candidate_count
    assert result.rejection_counts["startup_penetration"] == result.candidate_count
