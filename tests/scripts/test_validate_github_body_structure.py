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
backtick block
```

~~~text
tilde block with ``` inside
~~~

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


def paths(tmp_path: Path, after: str, before: str = BASE) -> tuple[Path, Path]:
    before_path = tmp_path / "before.md"
    after_path = tmp_path / "after.md"
    before_path.write_text(before, encoding="utf-8", newline="")
    after_path.write_text(after, encoding="utf-8", newline="")
    return before_path, after_path


def check(tmp_path: Path, after: str, before: str = BASE):
    before_path, after_path = paths(tmp_path, after, before)
    return MODULE.validate(before_path, after_path, required_sections=["## 状態", "## 台帳"])


def hard_reasons(result) -> str:
    return "\n".join(result.hard_violations)


def structural_reasons(result) -> str:
    return "\n".join(result.structural_violations)


def override(result, tmp_path: Path, reason: str = "task explicitly authorizes this structural rewrite"):
    return MODULE.apply_structural_override(result, reason=reason, diff_evidence_path=tmp_path / "override.diff")


def test_multiline_body_collapsed_to_one_line_is_hard_failure(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("\n", " "))
    assert not result.accepted
    assert "one physical line" in hard_reasons(result)


def test_reasoned_override_still_rejects_one_line_collapse(tmp_path: Path) -> None:
    result = override(check(tmp_path, BASE.replace("\n", " ")), tmp_path)
    assert not result.accepted
    assert not result.override_used


@pytest.mark.parametrize("marker", ["\ufffd", "???", "\u7e3a"])
def test_reasoned_override_still_rejects_corruption_markers(tmp_path: Path, marker: str) -> None:
    result = override(check(tmp_path, BASE + marker), tmp_path)
    assert not result.accepted
    assert not result.override_used
    assert "mojibake marker" in hard_reasons(result)


@pytest.mark.parametrize(
    ("after", "marker"),
    [
        (BASE.replace("```\n\n~~~text", "\n\n~~~text"), "```"),
        (BASE.replace("~~~\n\nhistorical", "\n\nhistorical"), "~~~"),
    ],
)
def test_reasoned_override_still_rejects_unbalanced_fence(tmp_path: Path, after: str, marker: str) -> None:
    result = override(check(tmp_path, after), tmp_path)
    assert not result.accepted
    assert not result.override_used
    assert marker in hard_reasons(result)


def test_mixed_backtick_and_tilde_fences_are_balanced_independently(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("backtick block", "backtick block with ~~~ inside"))
    assert result.accepted
    assert result.after.code_fence_markers == ["```", "```", "~~~", "~~~"]


def test_drastic_newline_reduction_is_structural(tmp_path: Path) -> None:
    result = check(tmp_path, "\n".join(BASE.splitlines()[:10]) + "\n")
    assert not result.accepted
    assert "newline count collapsed" in structural_reasons(result)


def test_required_heading_removed_is_structural(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("## 更新ルール", "更新ルール"))
    assert not result.accepted
    assert "headings are missing" in structural_reasons(result)


def test_table_delimiter_removed_is_structural(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("|---|---|", "| Slot | 状態 |", 1))
    assert not result.accepted
    assert "table delimiter" in structural_reasons(result)


def test_authorized_large_balanced_structural_rewrite_is_accepted(tmp_path: Path) -> None:
    before = BASE + "".join(f"extra historical line {index}\n" for index in range(100))
    after = """## Replacement

This is an explicitly authorized multiline rewrite.

~~~text
balanced
~~~
""" + "".join(f"replacement line {index}\n" for index in range(20))
    result = override(check(tmp_path, after, before), tmp_path)
    assert result.accepted
    assert result.override_used
    assert Path(result.diff_evidence_path).read_text(encoding="utf-8") == result.diff


def test_authorized_heading_and_table_rewrite_is_accepted_with_saved_diff(tmp_path: Path) -> None:
    after = BASE.replace("## 台帳", "## Ledger").replace("|---|---|", "|:---|---:|")
    result = override(check(tmp_path, after), tmp_path)
    assert result.accepted
    assert result.override_used
    assert result.structural_violations


def test_cli_authorized_structural_rewrite_uses_same_evidence_gate(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    diff_path = tmp_path / "cli-override.diff"
    exit_code = MODULE.main([
        str(before_path), str(after_path),
        "--allow-structural-change",
        "--override-reason", "task explicitly authorizes this structural rewrite",
        "--diff-output", str(diff_path),
    ])
    assert exit_code == 0
    assert diff_path.read_text(encoding="utf-8").startswith("---")


def test_cli_reasoned_override_cannot_accept_one_line_collapse(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("\n", " "))
    exit_code = MODULE.main([
        str(before_path), str(after_path),
        "--allow-structural-change",
        "--override-reason", "task explicitly authorizes this structural rewrite",
        "--diff-output", str(tmp_path / "hard.diff"),
    ])
    assert exit_code == 1


def test_override_without_structural_violation_is_not_used(tmp_path: Path) -> None:
    result = override(check(tmp_path, BASE.replace("| P20 | open |", "| P20 | open / draft |")), tmp_path)
    assert result.accepted
    assert not result.override_used
    assert result.diff_evidence_path is None


def test_direct_python_validate_has_no_override_bypass(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    with pytest.raises(TypeError):
        MODULE.validate(before_path, after_path, allow_structural_change=True, override_reason="authorized")


def test_direct_override_without_diff_evidence_is_rejected(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    overridden = MODULE.apply_structural_override(result, reason="authorized", diff_evidence_path=None)
    assert not overridden.accepted
    assert "saved diff evidence" in hard_reasons(overridden)


def test_missing_reason_rejects_override(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    overridden = MODULE.apply_structural_override(result, reason=" ", diff_evidence_path=tmp_path / "override.diff")
    assert not overridden.accepted
    assert "non-empty reason" in hard_reasons(overridden)


def test_unwritable_diff_output_rejects_override(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    overridden = MODULE.apply_structural_override(result, reason="authorized", diff_evidence_path=tmp_path)
    assert not overridden.accepted
    assert "failed to save" in hard_reasons(overridden)


def test_exact_localized_state_row_replacement_is_accepted(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("| P20 | open |", "| P20 | open / draft PR #368 |"))
    assert result.accepted
    assert not result.override_used


def test_small_appended_status_section_is_accepted(tmp_path: Path) -> None:
    assert check(tmp_path, BASE + "\n## Current status\n\n- P20 remains open.\n").accepted


def test_crlf_to_lf_normalization_only_is_accepted(tmp_path: Path) -> None:
    result = check(tmp_path, BASE, BASE.replace("\n", "\r\n"))
    assert result.accepted
    assert result.diff == ""


def test_japanese_utf8_body_round_trip_is_accepted(tmp_path: Path) -> None:
    assert check(tmp_path, BASE.replace("日本語の長期台帳です。", "日本語の長期台帳を安全に更新します。")).accepted


def test_utf8_bom_is_rejected_by_imported_api(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE)
    after_path.write_bytes(b"\xef\xbb\xbf" + BASE.encode("utf-8"))
    with pytest.raises(MODULE.InputValidationError, match="BOM"):
        MODULE.validate(before_path, after_path)
