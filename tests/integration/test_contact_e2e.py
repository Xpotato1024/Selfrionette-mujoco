from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from selfrionette.runtime.contact.log import decode_contact_task_log


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = ROOT / "scripts" / "viewer" / "generate_contact_e2e_artifacts.py"
TEST_SOFTWARE_REVISION = "test-only-contact-e2e-v1"


@pytest.fixture(scope="module")
def generator():
    spec = importlib.util.spec_from_file_location(
        "issue_417_contact_e2e_generator",
        GENERATOR_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous_bytecode_policy = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_bytecode_policy
    return module


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_contact_e2e_cli_requires_explicit_software_revision(
    generator,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "missing-revision"
    output_dir.mkdir()

    with pytest.raises(SystemExit) as raised:
        generator.main(["--output-dir", str(output_dir)])

    assert raised.value.code == 2
    assert tuple(output_dir.iterdir()) == ()


def test_contact_e2e_generates_bound_deterministic_log_and_viewer_payload(
    generator,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()

    assert (
        generator.main(
            [
                "--output-dir",
                str(output_dir),
                "--software-revision",
                TEST_SOFTWARE_REVISION,
            ]
        )
        == 0
    )

    log_paths = tuple(output_dir.glob("contact-task-log-v1-*.jsonl"))
    assert len(log_paths) == 1
    payload_path = output_dir / "contact-e2e-payload-v0.json"
    summary_path = output_dir / "contact-e2e-summary-v1.json"
    assert {path.name for path in output_dir.iterdir()} == {
        log_paths[0].name,
        payload_path.name,
        summary_path.name,
    }

    log_bytes = log_paths[0].read_bytes()
    log = decode_contact_task_log(log_bytes)
    assert log.to_jsonl() == log_bytes
    summary = _read_json(summary_path)
    assert generator.decode_contact_e2e_summary(summary_path.read_bytes()) == summary

    header = json.loads(log_bytes.splitlines()[0])
    assert header["manifest"]["software_revision_identity"] == summary["fixture"][
        "manifest_software_revision_identity"
    ]
    assert summary["fixture"]["software_revision"] == TEST_SOFTWARE_REVISION
    assert log.header.context.manifest_digest == summary["valid_run"][
        "contact_manifest_digest"
    ]

    valid_run = summary["valid_run"]
    assert valid_run["classification"] == "success"
    assert valid_run["phase_sequence"] == [
        "approach",
        "approach",
        "first_contact",
        "press",
        "hold",
        "success",
    ]
    assert valid_run["task_uses_raw_evidence_only"] is True
    assert valid_run["raw_force_band_n"] == [5.0, 15.0]
    assert valid_run["raw_force_range_n"][0] >= 5.0
    assert valid_run["raw_force_range_n"][1] <= 15.0
    assert valid_run["derived_force_clamp_n"] == 2.0
    assert valid_run["derived_force_peak_magnitude_n"] == 2.0
    assert valid_run["derived_force_below_raw_task_minimum"] is True

    assert summary["determinism"] == {
        "log_bytes_equal": True,
        "payload_bytes_equal": True,
    }
    assert summary["reset"] == {
        "post_reset_evidence_status": "no_contact",
        "same_manifest_digest": True,
        "same_scene_identity": True,
    }
    assert [item["name"] for item in summary["negative_controls"]] == [
        "no_contact",
        "measurement_unavailable",
        "invalid_contact",
        "invalid_scene",
        "solver_invalid",
    ]
    assert all(item["passed"] is True for item in summary["negative_controls"])

    payload_bytes = payload_path.read_bytes()
    payload = _read_json(payload_path)
    contact = payload["metadata"]["contact_task_v1"]
    qpos_projection = payload["metadata"]["contact_scene_robot_qpos_v1"]
    assert payload["time_s"] == valid_run["payload_time_s"]
    assert payload["frame_index"] == valid_run["payload_frame_index"]
    assert summary["fixture"]["robot_profile_qpos_dimension"] == 4
    assert len(payload["qpos"]) == (
        summary["fixture"]["robot_profile_qpos_dimension"] + 7
    )
    assert contact["binding"]["manifest_digest"] == valid_run[
        "contact_manifest_digest"
    ]
    assert contact["sequence_index"] == valid_run["payload_frame_index"]
    assert qpos_projection["schema_version"] == "contact-scene-robot-qpos/v1"
    assert qpos_projection["scene_identity"] == contact["binding"]["scene_identity"]
    assert qpos_projection["manifest_digest"] == contact["binding"]["manifest_digest"]
    assert qpos_projection["frame_index"] == payload["frame_index"]
    assert qpos_projection["time_s"] == payload["time_s"]
    assert qpos_projection["source_qpos_dimension"] == len(payload["qpos"])
    assert qpos_projection["robot_profile_id"] == payload["metadata"]["robot_profile_id"]
    assert qpos_projection["model_contract_version"] == payload["metadata"][
        "model_contract_version"
    ]
    assert qpos_projection["robot_joint_names"] == payload["metadata"][
        "robot_joint_names"
    ]
    assert qpos_projection["robot_qpos_dimension"] == payload["metadata"][
        "robot_qpos_dimension"
    ] == 4
    qpos_addresses = qpos_projection["qpos_addresses"]
    assert len(qpos_addresses) == qpos_projection["robot_qpos_dimension"]
    assert len(set(qpos_addresses)) == len(qpos_addresses)
    assert all(0 <= address < qpos_projection["source_qpos_dimension"] for address in qpos_addresses)
    assert hashlib.sha256(payload_bytes).hexdigest() == valid_run["payload_sha256"]
    qpos_bytes = json.dumps(
        payload["qpos"],
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(qpos_bytes).hexdigest() == valid_run["payload_qpos_sha256"]

    changed_revision = copy.deepcopy(summary)
    changed_revision["fixture"]["software_revision"] = "different-test-revision"
    changed_bytes = generator._canonical_json(changed_revision) + b"\n"
    with pytest.raises(ValueError, match="fixture identity or geometry"):
        generator.decode_contact_e2e_summary(changed_bytes)
