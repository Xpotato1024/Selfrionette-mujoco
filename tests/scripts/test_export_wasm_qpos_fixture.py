from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "export_wasm_qpos_fixture.py"
SPEC = importlib.util.spec_from_file_location("export_wasm_qpos_fixture", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _line(*, frame_index: object = 1, time_s: object = 0.1, qpos: object = None, metadata: object = None) -> str:
    return json.dumps(
        {
            "frame_index": frame_index,
            "time_s": time_s,
            "qpos": [0.1, -0.2, 0.3, -0.4] if qpos is None else qpos,
            "metadata": {"phase": "test"} if metadata is None else metadata,
        }
    )


def _build_with_lines(monkeypatch: pytest.MonkeyPatch, lines: list[str]) -> dict[str, object]:
    monkeypatch.setattr(MODULE, "run_replay_mujoco_dry_run", lambda **_: lines)
    return MODULE._build_fixture(preset="sweep_x", steps=len(lines), dt_s=1.0 / 60.0)


def test_build_fixture_accepts_a_valid_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _build_with_lines(
        monkeypatch,
        [_line(frame_index=1, time_s=0.1), _line(frame_index=2, time_s=0.2)],
    )

    assert fixture["qpos_length"] == 4
    assert [frame["frame_index"] for frame in fixture["frames"]] == [1, 2]


@pytest.mark.parametrize(
    ("name", "lines", "message"),
    [
        ("duplicate timestamp", [_line(time_s=0.1), _line(frame_index=2, time_s=0.1)], "duplicate timestamp"),
        ("time rollback", [_line(time_s=0.2), _line(frame_index=2, time_s=0.1)], "time rollback"),
        ("frame gap", [_line(), _line(frame_index=3, time_s=0.2)], "frame index gap"),
        ("frame rollback", [_line(), _line(frame_index=0, time_s=0.2)], "frame index gap"),
        ("nan qpos", [_line(qpos=[float("nan"), 0.0, 0.0, 0.0])], "finite numbers"),
        ("inf qpos", [_line(qpos=[float("inf"), 0.0, 0.0, 0.0])], "finite numbers"),
        ("nonfinite time", [_line(time_s=float("inf"))], "time_s must be finite"),
        ("qpos dimension", [_line(), _line(frame_index=2, time_s=0.2, qpos=[0.1, 0.2, 0.3])], "dimension changed"),
        ("empty generation", [], "frame sequence is empty"),
    ],
)
def test_build_fixture_rejects_invalid_sequences(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    lines: list[str],
    message: str,
) -> None:
    del name
    with pytest.raises(RuntimeError, match=message):
        _build_with_lines(monkeypatch, lines)


def test_build_fixture_rejects_non_object_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="metadata must be a JSON object"):
        _build_with_lines(monkeypatch, [_line(metadata=[])])


def test_existing_output_is_preserved_when_generation_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "fixture.json"
    original_bytes = b"known-good\n"
    output_path.write_bytes(original_bytes)
    monkeypatch.setattr(MODULE, "run_replay_mujoco_dry_run", lambda **_: [_line(), _line(frame_index=3, time_s=0.2)])

    with pytest.raises(RuntimeError, match="frame index gap"):
        MODULE.main(["--output", str(output_path)])

    assert output_path.read_bytes() == original_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_cleans_temporary_file_when_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "fixture.json"
    original_bytes = b"known-good\n"
    output_path.write_bytes(original_bytes)

    def fail_replace(*_: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(MODULE.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        MODULE._write_fixture_atomic(output_path, "{}\n")

    assert output_path.read_bytes() == original_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_real_sweep_x_path_builds_and_writes_a_valid_fixture(tmp_path: Path) -> None:
    fixture = MODULE._build_fixture(preset="sweep_x", steps=30, dt_s=1.0 / 60.0)
    output_path = tmp_path / "fixture.json"
    MODULE._write_fixture_atomic(output_path, MODULE._serialize_fixture(fixture))

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["schema_version"] == 1
    assert written["source"] == "python-native-mujoco"
    assert written["model_path"] == "assets/mujoco/fast_arm/scene.xml"
    assert written["preset"] == "sweep_x"
    assert len(written["frames"]) == 30
    assert [frame["frame_index"] for frame in written["frames"]] == list(range(1, 31))
    assert all(
        previous["t_s"] < current["t_s"]
        for previous, current in zip(written["frames"], written["frames"][1:])
    )
