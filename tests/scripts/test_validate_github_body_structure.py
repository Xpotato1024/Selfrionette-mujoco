from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "validate_github_body_structure.py"
SPEC = importlib.util.spec_from_file_location("validate_github_body_structure", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


BASE = """## 状態

日本語の長期台帳です。

## 更新ルール

- narrow replacement only

## 台帳

| Slot | 状態 |
|---|---|
| P20 | open |

## 詳細

```text
preserved
```

historical line 1
historical line 2
historical line 3
historical line 4
historical line 5
historical line 6
historical line 7
historical line 8
historical line 9
historical line 10
"""


def check(tmp_path: Path, after: str, before: str = BASE):
    before_path = tmp_path / "before.md"
    after_path = tmp_path / "after.md"
    before_path.write_text(before, encoding="utf-8", newline="")
    after_path.write_text(after, encoding="utf-8", newline="")
    return MODULE.validate(before_path, after_path, required_sections=["## 状態", "## 台帳"])


def reasons(result) -> str:
    return "\n".join(result.violations)


def test_multiline_body_collapsed_to_one_line_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("\n", " "))
    assert not result.accepted
    assert "one physical line" in reasons(result)


def test_drastic_newline_reduction_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, "\n".join(BASE.splitlines()[:8]) + "\n")
    assert not result.accepted
    assert "newline count collapsed" in reasons(result)


def test_required_heading_removed_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("## 更新ルール", "更新ルール"))
    assert not result.accepted
    assert "headings are missing" in reasons(result)


def test_table_delimiter_removed_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("|---|---|", "| Slot | 状態 |", 1))
    assert not result.accepted
    assert "table delimiter" in reasons(result)


def test_unbalanced_code_fence_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("```\n\nhistorical", "\nhistorical"))
    assert not result.accepted
    assert "unbalanced code fences" in reasons(result)


def test_unrelated_large_section_deletion_is_rejected(tmp_path: Path) -> None:
    before = BASE + "".join(f"extra historical line {index}\n" for index in range(100))
    after = BASE + "".join(f"extra historical line {index}\n" for index in range(10))
    result = check(tmp_path, after, before)
    assert not result.accepted
    assert "large" in reasons(result)


def test_exact_localized_state_row_replacement_is_accepted(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("| P20 | open |", "| P20 | open / draft PR #368 |"))
    assert result.accepted


def test_small_appended_status_section_is_accepted(tmp_path: Path) -> None:
    result = check(tmp_path, BASE + "\n## Current status\n\n- P20 remains open.\n")
    assert result.accepted


def test_crlf_to_lf_normalization_only_is_accepted(tmp_path: Path) -> None:
    result = check(tmp_path, BASE, BASE.replace("\n", "\r\n"))
    assert result.accepted
    assert result.diff == ""


def test_japanese_utf8_body_round_trip_is_accepted(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("日本語の長期台帳です。", "日本語の長期台帳を安全に更新します。"))
    assert result.accepted


@pytest.mark.parametrize("marker", ["\ufffd", "???", "\u7e3a"])
def test_replacement_or_mojibake_marker_is_rejected(tmp_path: Path, marker: str) -> None:
    result = check(tmp_path, BASE + marker)
    assert not result.accepted
    assert "mojibake marker" in reasons(result)


def test_unintended_question_mark_replacement_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("日本語", "???"))
    assert not result.accepted
    assert "question-mark replacement" in reasons(result)


def test_override_requires_reason_and_saved_diff(tmp_path: Path) -> None:
    before_path = tmp_path / "before.md"
    after_path = tmp_path / "after.md"
    before_path.write_text(BASE, encoding="utf-8")
    after_path.write_text(BASE.replace("\n", " "), encoding="utf-8")
    assert MODULE.main([str(before_path), str(after_path), "--allow-structural-change"]) == 2


def test_reasoned_override_accepts_and_saves_diff(tmp_path: Path) -> None:
    before_path = tmp_path / "before.md"
    after_path = tmp_path / "after.md"
    diff_path = tmp_path / "override.diff"
    before_path.write_text(BASE, encoding="utf-8")
    after_path.write_text(BASE.replace("\n", " "), encoding="utf-8")
    result = MODULE.main([
        str(before_path), str(after_path), "--allow-structural-change",
        "--override-reason", "task explicitly authorizes a rewrite",
        "--diff-output", str(diff_path),
    ])
    assert result == 0
    assert diff_path.read_text(encoding="utf-8").startswith("---")
