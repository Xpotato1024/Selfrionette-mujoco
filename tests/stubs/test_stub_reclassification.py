from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "reports" / "implementation" / "r6-i-p3-stub-reclassification.md"

EXPECTED_ROWS = {
    "StaticInputSource": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "NoOpInputInterpreter": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "ZeroForwardKinematicsSolver": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "no",
        "owner issue": "#137",
    },
    "ZeroInverseKinematicsSolver": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "no",
        "owner issue": "#137",
    },
    "NoOpMotionGenerator": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "NoOpMuJoCoSimulator": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "NoOpStatePublisher": {
        "current category": "test-double",
        "allowed import path": ".stubs explicit import only",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "build_noop_pipeline": {
        "current category": "compatibility-helper",
        "allowed import path": "selfrionette.runtime.pipeline",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "build_mujoco_pipeline": {
        "current category": "compatibility-helper",
        "allowed import path": "selfrionette.runtime.mujoco_pipeline",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "build_motion_command_from_input_intent": {
        "current category": "compatibility-helper",
        "allowed import path": "selfrionette.motion.input_intent",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
    "build_motion_command_from_target_command": {
        "current category": "compatibility-helper",
        "allowed import path": "selfrionette.motion.input_intent",
        "runtime-default-visible": "no",
        "compatibility-path-visible": "yes",
        "owner issue": "#137",
    },
}


def _parse_classification_table(text: str) -> dict[str, dict[str, str]]:
    lines = text.splitlines()
    start_index = None
    header: list[str] = []

    for index, line in enumerate(lines):
        if line.startswith("| symbol |"):
            start_index = index
            header = [cell.strip() for cell in line.split("|")[1:-1]]
            break

    assert start_index is not None, "classification table not found"

    rows: dict[str, dict[str, str]] = {}
    for line in lines[start_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        row = dict(zip(header, cells, strict=True))
        rows[row["symbol"].strip("`")] = row

    return rows


def test_stub_reclassification_doc_covers_remaining_stubs_and_helpers() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    rows = _parse_classification_table(text)

    assert "現時点では該当なし" in text

    for symbol, expected in EXPECTED_ROWS.items():
        assert symbol in rows, f"missing classification row for {symbol}"
        row = rows[symbol]
        for column, expected_value in expected.items():
            assert expected_value in row[column], f"{symbol} {column} mismatch: {row[column]}"

    assert "ProgrammedTargetInputSource" in text
    assert "RawInputFrame.metadata" in text
    assert "build_motion_command_from_*" in text
