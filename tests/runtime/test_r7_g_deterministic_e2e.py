from __future__ import annotations

import json
from pathlib import Path

import pytest

from selfrionette.runtime.experiment.r7_g_e2e import (
    R7_G_E2E_MOTION_LOG_NAME,
    R7_G_E2E_TOOL_ARTIFACT_NAME,
    R7_G_E2E_WORLD_ARTIFACT_NAME,
    _summary,
    main,
    run_r7_g_deterministic_e2e,
)


def test_r7_g_e2e_repeats_execution_evidence_metrics_and_artifacts(
    tmp_path: Path,
) -> None:
    result = run_r7_g_deterministic_e2e(output_dir=tmp_path)

    assert result.negative_controls == (
        "readiness_mismatch",
        "malformed_log",
        "held",
        "rejected",
        "stale",
        "measurement_unavailable",
        "technical_invalid",
        "artifact_identity_mismatch",
    )
    assert result.run.motion_log_bytes == (
        tmp_path / R7_G_E2E_MOTION_LOG_NAME
    ).read_bytes()
    assert [
        (item.condition_id, item.execution.classification.value, item.execution.step_count)
        for item in result.run.conditions
    ] == [("world", "success", 57), ("tool", "failure", 250)]
    assert result.run.condition("world").execution.final_elapsed_time_s == pytest.approx(1.14)
    assert result.run.condition("tool").execution.final_elapsed_time_s == pytest.approx(5.0)
    assert [len(item.artifact_bytes) for item in result.run.conditions] == [3045, 3112]
    assert (
        tmp_path / R7_G_E2E_WORLD_ARTIFACT_NAME
    ).read_bytes() == result.run.condition("world").artifact_bytes
    assert (
        tmp_path / R7_G_E2E_TOOL_ARTIFACT_NAME
    ).read_bytes() == result.run.condition("tool").artifact_bytes
    assert (tmp_path / f".{R7_G_E2E_WORLD_ARTIFACT_NAME}.lock").exists()
    assert (tmp_path / f".{R7_G_E2E_TOOL_ARTIFACT_NAME}.lock").exists()


def test_r7_g_e2e_installable_entrypoint_reports_only_canonical_names(
    tmp_path: Path,
    capsys,
) -> None:
    assert main(["--output-dir", str(tmp_path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["outputs"] == [
        R7_G_E2E_MOTION_LOG_NAME,
        R7_G_E2E_WORLD_ARTIFACT_NAME,
        R7_G_E2E_TOOL_ARTIFACT_NAME,
    ]
    assert "AppData" not in json.dumps(summary)
    assert [item["step_count"] for item in summary["conditions"]] == [57, 250]


def test_r7_g_e2e_summary_is_stable_and_excludes_paths() -> None:
    first = run_r7_g_deterministic_e2e()
    second = run_r7_g_deterministic_e2e()
    assert _summary(first) == _summary(second)
    assert all(
        value not in json.dumps(_summary(first))
        for value in ("AppData", "worktree", "process", "uuid")
    )
