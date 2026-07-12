from __future__ import annotations

import importlib.util
import os
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


def test_before_and_after_same_path_are_rejected_by_imported_api(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(BASE, encoding="utf-8")
    with pytest.raises(MODULE.InputValidationError, match="distinct filesystem objects"):
        MODULE.validate(body, body)


def test_before_and_after_relative_alias_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body = tmp_path / "body.md"
    body.write_text(BASE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(MODULE.InputValidationError, match="distinct filesystem objects"):
        MODULE.validate(Path("body.md"), body)


def test_before_and_after_symlink_alias_are_rejected(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    alias = tmp_path / "body-alias.md"
    body.write_text(BASE, encoding="utf-8")
    try:
        alias.symlink_to(body)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(MODULE.InputValidationError, match="distinct filesystem objects"):
        MODULE.validate(body, alias)


def test_before_and_after_hardlink_alias_are_rejected(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    alias = tmp_path / "body-hardlink.md"
    body.write_text(BASE, encoding="utf-8")
    try:
        os.link(body, alias)
    except OSError as exc:
        pytest.skip(f"hardlink unavailable: {exc}")
    with pytest.raises(MODULE.InputValidationError, match="distinct filesystem objects"):
        MODULE.validate(body, alias)


@pytest.mark.skipif(os.name != "nt", reason="Windows path case semantics")
def test_before_and_after_windows_case_alias_are_rejected(tmp_path: Path) -> None:
    body = tmp_path / "MixedCaseBody.md"
    body.write_text(BASE, encoding="utf-8")
    alias = tmp_path / "mixedcasebody.md"
    with pytest.raises(MODULE.InputValidationError, match="distinct filesystem objects"):
        MODULE.validate(body, alias)


def test_distinct_files_with_identical_bytes_are_accepted(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE)
    result = MODULE.validate(before_path, after_path)
    assert result.accepted
    assert result.diff == ""


def test_cli_and_imported_api_share_input_identity_gate(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(BASE, encoding="utf-8")
    with pytest.raises(MODULE.InputValidationError):
        MODULE.validate(body, body)
    assert MODULE.main([str(body), str(body)]) == 2


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
    assert [(block.marker_type, block.opening_length, block.closing_compatible) for block in result.after.code_fence_blocks] == [("`", 3, True), ("~", 3, True)]


@pytest.mark.parametrize("block_text", ["backtick block", "tilde block with ``` inside"])
def test_heading_inside_fence_cannot_replace_real_heading(tmp_path: Path, block_text: str) -> None:
    after = BASE.replace("## 詳細\n\n", "").replace(block_text, block_text + "\n## 詳細")
    result = check(tmp_path, after)
    assert not result.accepted
    assert "headings are missing" in structural_reasons(result)


def test_table_delimiter_inside_fence_cannot_replace_real_delimiter(tmp_path: Path) -> None:
    after = BASE.replace("|---|---|\n", "").replace("backtick block", "backtick block\n|---|---|")
    result = check(tmp_path, after)
    assert not result.accepted
    assert "table block" in structural_reasons(result)


def test_required_sentinel_inside_fence_cannot_replace_real_heading(tmp_path: Path) -> None:
    after = BASE.replace("## 状態\n\n", "").replace("backtick block", "backtick block\n## 状態")
    result = check(tmp_path, after)
    assert not result.accepted
    assert "required sentinel section was removed" in structural_reasons(result)


@pytest.mark.parametrize("delimiter", [
    "|---|---|",
    "---|---",
    "--- | ---",
    "| --- | --- |",
    ":--- | ---:",
    "| :--- | :---: | ---: |",
])
def test_valid_gfm_table_delimiter_forms_are_recognized(tmp_path: Path, delimiter: str) -> None:
    column_count = len(MODULE._pipe_cells(delimiter))
    header = " | ".join(f"H{index}" for index in range(column_count))
    body = f"## Table\n\n{header}\n{delimiter}\n" + " | ".join("value" for _ in range(column_count)) + "\n"
    before_path, after_path = paths(tmp_path, body, body)
    result = MODULE.validate(before_path, after_path)
    assert result.accepted
    assert len(result.after.table_blocks) == 1
    assert result.after.table_blocks[0].column_count == column_count


def test_horizontal_rule_and_fenced_delimiter_are_not_table_rows(tmp_path: Path) -> None:
    after = BASE.replace("|---|---|\n", "---\n").replace("backtick block", "backtick block\n|---|---|")
    result = check(tmp_path, after)
    assert result.after.table_blocks == []


def test_blank_line_between_header_and_delimiter_breaks_table(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("| Slot | 状態 |\n|---|---|", "| Slot | 状態 |\n\n|---|---|"))
    assert not result.accepted
    assert "table block" in structural_reasons(result)


def test_relocated_delimiter_does_not_preserve_table(tmp_path: Path) -> None:
    after = BASE.replace("|---|---|\n", "").replace("historical line 10", "historical line 10\n|---|---|")
    result = check(tmp_path, after)
    assert not result.accepted
    assert "table block" in structural_reasons(result)


@pytest.mark.parametrize("delimiter", ["|---|---|", "---|---"])
def test_standalone_delimiter_is_not_a_table(tmp_path: Path, delimiter: str) -> None:
    body = f"## Section\n\nplain text\n\n{delimiter}\n"
    before_path, after_path = paths(tmp_path, body, body)
    result = MODULE.validate(before_path, after_path)
    assert result.accepted
    assert result.after.table_blocks == []


def test_indented_code_header_delimiter_pair_is_not_a_table(tmp_path: Path) -> None:
    body = "## Section\n\n    Header | Value\n    ---|---\n"
    before_path, after_path = paths(tmp_path, body, body)
    result = MODULE.validate(before_path, after_path)
    assert result.after.table_blocks == []


def test_fenced_header_delimiter_pair_is_not_a_table(tmp_path: Path) -> None:
    body = "## Section\n\n```text\nHeader | Value\n---|---\n```\n"
    before_path, after_path = paths(tmp_path, body, body)
    result = MODULE.validate(before_path, after_path)
    assert result.accepted
    assert result.after.table_blocks == []


def test_header_delimiter_column_mismatch_is_not_a_table(tmp_path: Path) -> None:
    body = "## Section\n\nHeader | Value\n---|---|---\n"
    before_path, after_path = paths(tmp_path, body, body)
    result = MODULE.validate(before_path, after_path)
    assert result.after.table_blocks == []


def test_table_block_records_section_columns_alignment_and_rows(tmp_path: Path) -> None:
    body = "## Ledger\n\nSlot | State | Note\n:--- | :---: | ---:\nP20 | open | draft\n"
    before_path, after_path = paths(tmp_path, body, body)
    block = MODULE.validate(before_path, after_path).after.table_blocks[0]
    assert block.section_identity == "## Ledger"
    assert block.column_count == 3
    assert block.alignments == ("left", "center", "right")
    assert block.header_row == "Slot | State | Note"
    assert block.delimiter_row == ":--- | :---: | ---:"


@pytest.mark.parametrize(
    "after",
    [
        BASE.replace("```text", "~~~~text").replace("```\n\n~~~text", "~~~~\n\n~~~text"),
        BASE.replace("```text", "````text").replace("```\n\n~~~text", "````\n\n~~~text"),
        BASE.replace("~~~text\ntilde block with ``` inside\n~~~\n\n", ""),
    ],
)
def test_localized_update_protects_ordered_fence_block_structure(tmp_path: Path, after: str) -> None:
    result = check(tmp_path, after)
    assert not result.accepted
    assert "fence block structure changed" in structural_reasons(result)


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
    assert "table block" in structural_reasons(result)


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


@pytest.mark.parametrize("which", ["before", "after"])
def test_diff_evidence_cannot_equal_input_body(tmp_path: Path, which: str) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    result = MODULE.validate(before_path, after_path)
    evidence = before_path if which == "before" else after_path
    original = evidence.read_bytes()
    overridden = MODULE.apply_structural_override(result, reason="authorized", diff_evidence_path=evidence)
    assert not overridden.accepted
    assert "must not alias" in hard_reasons(overridden)
    assert evidence.read_bytes() == original


def test_cli_diff_alias_cannot_overwrite_input(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    original = after_path.read_bytes()
    exit_code = MODULE.main([
        str(before_path), str(after_path),
        "--allow-structural-change", "--override-reason", "authorized",
        "--diff-output", str(after_path),
    ])
    assert exit_code == 1
    assert after_path.read_bytes() == original


def test_cli_localized_diff_output_cannot_overwrite_input(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("| P20 | open |", "| P20 | draft |"))
    original = before_path.read_bytes()
    exit_code = MODULE.main([str(before_path), str(after_path), "--diff-output", str(before_path)])
    assert exit_code == 1
    assert before_path.read_bytes() == original


def test_relative_diff_alias_cannot_overwrite_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    result = MODULE.validate(before_path, after_path)
    original = before_path.read_bytes()
    monkeypatch.chdir(tmp_path)
    overridden = MODULE.apply_structural_override(result, reason="authorized", diff_evidence_path=Path("before.md"))
    assert not overridden.accepted
    assert "must not alias" in hard_reasons(overridden)
    assert before_path.read_bytes() == original


def test_symlink_diff_alias_cannot_overwrite_input(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    alias = tmp_path / "before-alias.md"
    try:
        alias.symlink_to(before_path)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    result = MODULE.validate(before_path, after_path)
    original = before_path.read_bytes()
    overridden = MODULE.apply_structural_override(result, reason="authorized", diff_evidence_path=alias)
    assert not overridden.accepted
    assert "must not alias" in hard_reasons(overridden)
    assert before_path.read_bytes() == original


def test_independent_diff_path_remains_valid(tmp_path: Path) -> None:
    result = check(tmp_path, BASE.replace("## 台帳", "## Ledger"))
    evidence = tmp_path / "independent.diff"
    overridden = MODULE.apply_structural_override(result, reason="authorized", diff_evidence_path=evidence)
    assert overridden.accepted and overridden.override_used
    assert evidence.read_text(encoding="utf-8") == result.diff


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


PROTECTED = """## Numbering / SoT status

- Parent state: open

## Current child roadmap

| P | State |
|---|---|
| P18 | open |

## Current batch

- Batch state: draft.
"""


def protected_check(tmp_path: Path, before: str, after: str):
    before_path, after_path = paths(tmp_path, after, before)
    return MODULE.validate(
        before_path,
        after_path,
        required_sections=["## Numbering / SoT status", "## Current child roadmap", "## Current batch"],
        require_multiline_baseline=True,
        required_table_sections=["## Current child roadmap"],
    )


def test_already_collapsed_before_and_one_line_after_is_hard_failure(tmp_path: Path) -> None:
    before = "## Numbering / SoT status text ## Current child roadmap | P | State | ## Current batch draft"
    result = protected_check(tmp_path, before, before + " updated")
    assert not result.accepted
    assert "inline Markdown heading markers" in hard_reasons(result)
    assert not override(result, tmp_path).accepted


def test_already_collapsed_before_and_superficially_multiline_after_is_hard_failure(tmp_path: Path) -> None:
    before = "## Numbering / SoT status text ## Current child roadmap table ## Current batch draft"
    result = protected_check(tmp_path, before, PROTECTED)
    assert not result.accepted
    assert "inline Markdown heading markers" in hard_reasons(result)


def test_inline_heading_fragments_do_not_count_as_headings(tmp_path: Path) -> None:
    collapsed = "prefix ## Numbering / SoT status text ## Current child roadmap text"
    result = protected_check(tmp_path, collapsed, PROTECTED)
    assert result.before.headings == []
    assert "zero parsed headings" in hard_reasons(result)


def test_protected_profile_requires_explicit_sentinels(tmp_path: Path) -> None:
    before_path, after_path = paths(tmp_path, PROTECTED, PROTECTED)
    result = MODULE.validate(before_path, after_path, require_multiline_baseline=True)
    assert not result.accepted
    assert "requires explicit sentinel headings" in hard_reasons(result)


def test_valid_multiline_protected_before_and_candidate_pass(tmp_path: Path) -> None:
    result = protected_check(tmp_path, PROTECTED, PROTECTED.replace("| P18 | open |", "| P18 | open / draft |"))
    assert result.accepted


def test_damaged_324_shape_is_rejected_and_repaired_candidate_passes(tmp_path: Path) -> None:
    damaged = PROTECTED.replace("\n", " ")
    assert not protected_check(tmp_path, damaged, PROTECTED).accepted
    assert protected_check(tmp_path, PROTECTED, PROTECTED.replace("draft.", "three draft PRs.")).accepted


def test_293_normal_localized_update_still_passes_protected_profile(tmp_path: Path) -> None:
    after = PROTECTED.replace("| P18 | open |", "| P18 | open / draft PR #372 |")
    assert protected_check(tmp_path, PROTECTED, after).accepted
