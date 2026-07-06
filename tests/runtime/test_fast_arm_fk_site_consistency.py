from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, extract_fast_arm_tip_site_endpoint_from_state
from selfrionette.mujoco_backend.endpoint_extraction import RuntimeMuJoCoSiteEndpointEvaluation
from selfrionette.runtime.endpoint_motion_sanity import (
    _build_fast_arm_fk_site_consistency_diagnostic,
    _fast_arm_fk_site_consistency_qpos_fixtures,
    _vector_norm_m,
    build_fast_arm_fk_site_consistency_log_rows,
    run_fast_arm_fk_site_consistency_diagnostics,
    write_fast_arm_fk_site_consistency_log_jsonl,
)


def test_fast_arm_fk_site_consistency_records_include_qpos_fk_endpoint_tip_site_error_vector_and_norm() -> None:
    records = run_fast_arm_fk_site_consistency_diagnostics()

    assert [record.fixture_label for record in records] == [
        "default_qpos",
        "small_positive_perturbation",
        "small_negative_perturbation",
        "representative_endpoint_motion_sanity_qpos",
    ]

    for record in records:
        assert len(record.qpos) == 4
        assert len(record.fk_endpoint_m) == 3
        assert len(record.mujoco_tip_site_position_m) == 3
        assert len(record.fk_site_error_m) == 3
        assert record.fk_site_error_norm_m == pytest.approx(_vector_norm_m(record.fk_site_error_m), abs=1e-12)
        assert record.status == "mismatch"
        assert record.reason == "fk_endpoint_does_not_match_tip_site_world_position"
        assert record.site_name == "tip"
        assert len(record.joint_names) == 4


def test_fast_arm_fk_site_consistency_default_qpos_fixture_is_deterministic_and_non_default_fixtures_exist() -> None:
    fixtures = _fast_arm_fk_site_consistency_qpos_fixtures()

    assert fixtures[0][0] == "default_qpos"
    assert fixtures[0][1] == pytest.approx((0.0, -math.pi / 2.0, 0.0, 0.0), abs=1e-12)
    assert any(label != "default_qpos" and qpos != fixtures[0][1] for label, qpos in fixtures)

    diagnostic = _build_fast_arm_fk_site_consistency_diagnostic(
        fixture_label="default_qpos",
        qpos=fixtures[0][1],
    )
    assert diagnostic.qpos == pytest.approx(fixtures[0][1], abs=1e-12)
    assert diagnostic.fk_site_error_norm_m > 1.0


def test_fast_arm_fk_site_consistency_tip_site_is_primary_and_body_reference_is_not_treated_as_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    state = simulator.snapshot()

    tip_evaluation = extract_fast_arm_tip_site_endpoint_from_state(state)
    assert tip_evaluation.kind == "site"
    assert tip_evaluation.name == "tip"

    fake_body_reference = RuntimeMuJoCoSiteEndpointEvaluation(
        role="tip",
        kind="body",
        name="fore_arm_link",
        position_m=tip_evaluation.position_m,
    )

    monkeypatch.setattr(
        "selfrionette.runtime.endpoint_motion_sanity.extract_fast_arm_tip_site_endpoint_from_state",
        lambda state: fake_body_reference,
    )

    qpos = tuple(float(value) for value in state.qpos[:4])
    diagnostic = _build_fast_arm_fk_site_consistency_diagnostic(
        fixture_label="default_qpos",
        qpos=qpos,
    )

    assert diagnostic.status == "mismatch"
    assert diagnostic.reason == "tip_site_reference_is_not_primary"


def test_fast_arm_fk_site_consistency_jsonl_export_writes_records(tmp_path: Path) -> None:
    records = run_fast_arm_fk_site_consistency_diagnostics()
    output_path = tmp_path / "fk_site_consistency.jsonl"

    exported_path = write_fast_arm_fk_site_consistency_log_jsonl(records, output_path)

    assert exported_path == output_path
    assert exported_path.exists()

    rows = build_fast_arm_fk_site_consistency_log_rows(records)
    assert len(rows) == len(records)

    lines = exported_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(records)

    first_row = json.loads(lines[0])
    assert first_row["fixture_label"] == "default_qpos"
    assert len(first_row["qpos"]) == 4
    assert len(first_row["fk_endpoint_m"]) == 3
    assert len(first_row["mujoco_tip_site_position_m"]) == 3
    assert len(first_row["fk_site_error_m"]) == 3
    assert first_row["fk_site_error_norm_m"] >= 0.0
