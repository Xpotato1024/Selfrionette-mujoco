from __future__ import annotations

import json

import pytest

from selfrionette.runtime import run_replay_mujoco_dry_run
from selfrionette.schemas import RawInputFrame


def _assert_endpoint_evaluation(payload: dict[str, object]) -> None:
    endpoint_evaluation = payload["endpoint_evaluation"]
    assert isinstance(endpoint_evaluation, dict)
    assert endpoint_evaluation["unit"] == "meter"
    assert endpoint_evaluation["desired_endpoint_coordinate_frame"] == "command-side endpoint frame"
    assert endpoint_evaluation["fk_endpoint_coordinate_frame"] == "solver-defined frame"
    assert endpoint_evaluation["site_endpoint_coordinate_frame"] == "MuJoCo world / scene frame"
    assert "diagnostic only" in endpoint_evaluation["frame_mismatch_note"]
    assert len(endpoint_evaluation["desired_endpoint_m"]) == 3
    assert len(endpoint_evaluation["qpos_like_joint_angles_rad"]) >= 2
    assert len(endpoint_evaluation["fk_endpoint_m"]) == 3
    assert len(endpoint_evaluation["site_endpoint_m"]) == 3
    assert len(endpoint_evaluation["desired_to_fk_error_vector_m"]) == 3
    assert len(endpoint_evaluation["desired_to_site_error_vector_m"]) == 3
    assert len(endpoint_evaluation["fk_to_site_error_vector_m"]) == 3


def test_run_replay_mujoco_dry_run_returns_single_payload_line() -> None:
    lines = run_replay_mujoco_dry_run(steps=1)

    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["version"] == 0
    assert payload["frame_index"] == 1
    assert payload["time_s"] > 0.0
    assert payload["qpos"][:4] != [0.0, 0.0, 0.0, 0.0]
    assert payload["target_position_m"] is None
    _assert_endpoint_evaluation(payload)


def test_run_replay_mujoco_dry_run_emits_ndjson_for_multiple_steps() -> None:
    lines = run_replay_mujoco_dry_run(steps=3)

    assert len(lines) == 3

    frame_indices = [json.loads(line)["frame_index"] for line in lines]
    assert frame_indices == [1, 2, 3]


def test_run_replay_mujoco_dry_run_keeps_canonical_bodies_and_sites() -> None:
    payload = json.loads(run_replay_mujoco_dry_run(steps=1)[0])

    assert any(site["name"] == "tip" for site in payload["sites"])
    assert any(body["name"] == "base_link" for body in payload["bodies"])


def test_run_replay_mujoco_dry_run_rejects_invalid_steps() -> None:
    with pytest.raises(ValueError, match="steps must be a positive integer"):
        run_replay_mujoco_dry_run(steps=0)

    with pytest.raises(ValueError, match="steps must be a positive integer"):
        run_replay_mujoco_dry_run(steps=-1)


def test_run_replay_mujoco_dry_run_writes_ndjson_output_file(tmp_path) -> None:
    output_path = tmp_path / "payload.ndjson"

    lines = run_replay_mujoco_dry_run(steps=2, output=output_path)

    file_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert file_lines == lines
    assert len(file_lines) == 2

    payloads = [json.loads(line) for line in file_lines]
    assert [payload["version"] for payload in payloads] == [0, 0]
    assert [payload["frame_index"] for payload in payloads] == [1, 2]


def test_run_replay_mujoco_dry_run_sweep_x_preset_keeps_delta_and_feedback_separate() -> None:
    lines = run_replay_mujoco_dry_run(steps=3, preset="sweep_x")

    assert len(lines) == 3

    payloads = [json.loads(line) for line in lines]
    assert [payload["metadata"]["preset"] for payload in payloads] == ["sweep_x", "sweep_x", "sweep_x"]
    assert [payload["metadata"]["source_kind"] for payload in payloads] == ["programmed_target"] * 3
    assert [payload["metadata"]["trajectory_name"] for payload in payloads] == ["sweep_x"] * 3
    assert [payload["metadata"]["phase"] for payload in payloads] == ["initial_hold", "initial_hold", "initial_hold"]

    for payload in payloads:
        assert payload["metadata"]["desired_endpoint_m"] == payload["target_position_m"]
        assert len(payload["metadata"]["target_position_m"]) == 3
        assert len(payload["qpos"]) >= 4
        _assert_endpoint_evaluation(payload)


def test_run_replay_mujoco_dry_run_sweep_x_preset_remains_visual_smoke_compatibility_path() -> None:
    lines = run_replay_mujoco_dry_run(steps=1, preset="sweep_x")

    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["metadata"]["preset"] == "sweep_x"
    assert payload["metadata"]["source_kind"] == "programmed_target"
    assert payload["metadata"]["trajectory_name"] == "sweep_x"
    assert payload["metadata"]["phase"] == "initial_hold"
    assert payload["metadata"]["desired_endpoint_m"] == payload["target_position_m"]
    assert len(payload["qpos"]) >= 4
    _assert_endpoint_evaluation(payload)


def test_run_replay_mujoco_dry_run_rejects_unknown_preset() -> None:
    with pytest.raises(ValueError, match="unsupported dry-run preset"):
        run_replay_mujoco_dry_run(steps=1, preset="unknown")


def test_run_replay_mujoco_dry_run_rejects_preset_with_custom_frames() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=0.0)

    with pytest.raises(ValueError, match="preset and custom frames are mutually exclusive"):
        run_replay_mujoco_dry_run(steps=1, preset="sweep_x", frames=(frame,))
