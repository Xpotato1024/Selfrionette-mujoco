from __future__ import annotations

import json

import pytest

from selfrionette.runtime import run_replay_mujoco_dry_run


def test_run_replay_mujoco_dry_run_returns_single_payload_line() -> None:
    lines = run_replay_mujoco_dry_run(steps=1)

    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["version"] == 0
    assert payload["frame_index"] == 1
    assert payload["time_s"] > 0.0
    assert payload["target_position_m"] is None


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
