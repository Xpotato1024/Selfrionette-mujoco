from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import sys


HEADING_RE = re.compile(r"^#{1,6} .+$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
MOJIBAKE_MARKERS = ("\ufffd", "???", "\u7e3a", "\u7e67", "\u8700", "\u9aea", "\u8b17", "\u9036", "\u8b5b", "\u83a0", "\u7e32", "\u0080")


class InputValidationError(ValueError):
    """An input cannot be safely decoded or read."""


@dataclass(frozen=True)
class FenceBlock:
    marker_type: str
    opening_length: int
    closing_compatible: bool


@dataclass(frozen=True)
class BodyMetrics:
    byte_length: int
    sha256: str
    physical_line_count: int
    newline_count: int
    headings: list[str]
    table_delimiter_rows: list[str]
    code_fence_blocks: list[FenceBlock]


@dataclass(frozen=True)
class ValidationResult:
    before_path: str
    after_path: str
    before: BodyMetrics
    after: BodyMetrics
    diff: str
    hard_violations: list[str]
    structural_violations: list[str]
    override_used: bool = False
    override_reason: str | None = None
    diff_evidence_path: str | None = None

    @property
    def accepted(self) -> bool:
        if self.hard_violations:
            return False
        return not self.structural_violations or self.override_used


def _decode(path: Path) -> tuple[bytes, str]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InputValidationError(f"unreadable input file: {path}: {exc}") from exc
    if data.startswith(b"\xef\xbb\xbf"):
        raise InputValidationError(f"UTF-8 BOM is not allowed: {path}")
    try:
        return data, data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputValidationError(f"body is not UTF-8: {path}: {exc}") from exc


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _is_table_delimiter(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = stripped.split("|")
    if cells and not cells[0].strip():
        cells.pop(0)
    if cells and not cells[-1].strip():
        cells.pop()
    return len(cells) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _scan_structure(lines: list[str]) -> tuple[list[str], list[str], list[FenceBlock], str | None]:
    headings: list[str] = []
    table_delimiters: list[str] = []
    blocks: list[FenceBlock] = []
    opening: tuple[str, int] | None = None
    for line in lines:
        match = FENCE_RE.fullmatch(line)
        if match:
            marker, rest = match.groups()
            marker_type = marker[0]
            marker_length = len(marker)
            if opening is None:
                if marker_type == "`" and "`" in rest:
                    match = None
                else:
                    opening = (marker_type, marker_length)
                    continue
            elif marker_type == opening[0] and marker_length >= opening[1] and not rest.strip():
                blocks.append(FenceBlock(opening[0], opening[1], True))
                opening = None
                continue
        if opening is not None:
            continue
        if HEADING_RE.fullmatch(line):
            headings.append(line)
        if _is_table_delimiter(line):
            table_delimiters.append(line)
    if opening is None:
        return headings, table_delimiters, blocks, None
    return headings, table_delimiters, blocks, f"unbalanced {opening[0] * opening[1]} code fence"


def _metrics(data: bytes, text: str) -> BodyMetrics:
    normalized = _lf(text)
    lines = normalized.splitlines()
    headings, table_delimiters, blocks, _ = _scan_structure(lines)
    return BodyMetrics(
        byte_length=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        physical_line_count=len(lines),
        newline_count=normalized.count("\n"),
        headings=headings,
        table_delimiter_rows=table_delimiters,
        code_fence_blocks=blocks,
    )


def _is_ordered_subsequence(required: list[str], actual: list[str]) -> bool:
    iterator = iter(actual)
    return all(any(candidate == item for candidate in iterator) for item in required)


def validate(
    before_path: Path,
    after_path: Path,
    *,
    required_sections: list[str] | None = None,
) -> ValidationResult:
    """Validate bodies without applying an override.

    Structural overrides are intentionally unavailable here. Call
    ``apply_structural_override`` with saved diff evidence instead.
    """
    before_data, before_text = _decode(before_path)
    after_data, after_text = _decode(after_path)
    before_lf = _lf(before_text)
    after_lf = _lf(after_text)
    before = _metrics(before_data, before_text)
    after = _metrics(after_data, after_text)
    diff = "".join(
        difflib.unified_diff(
            before_lf.splitlines(keepends=True),
            after_lf.splitlines(keepends=True),
            fromfile=str(before_path),
            tofile=str(after_path),
        )
    )
    hard: list[str] = []
    structural: list[str] = []

    if not after_lf.strip() or not re.search(r"\w", after_lf, flags=re.UNICODE):
        hard.append("proposed body is empty or effectively empty")
    if before.physical_line_count > 1 and after.physical_line_count <= 1:
        hard.append("multiline body collapsed to one physical line")
    found_markers = [marker for marker in MOJIBAKE_MARKERS if marker in after_lf]
    if found_markers:
        hard.append(f"replacement or mojibake marker found: {found_markers!r}")
    _, _, _, before_fence_error = _scan_structure(before_lf.splitlines())
    _, _, _, after_fence_error = _scan_structure(after_lf.splitlines())
    if before_fence_error:
        hard.append(f"before body has {before_fence_error}")
    if after_fence_error:
        hard.append(f"proposed body has {after_fence_error}")

    if before.newline_count >= 10 and after.newline_count < before.newline_count * 0.7:
        structural.append("newline count collapsed by more than 30%")
    if before.physical_line_count >= 10 and after.physical_line_count < before.physical_line_count * 0.7:
        structural.append("physical line count collapsed by more than 30%")
    if not _is_ordered_subsequence(before.headings, after.headings):
        structural.append("Markdown headings are missing or reordered")

    before_delimiters = Counter(before.table_delimiter_rows)
    after_delimiters = Counter(after.table_delimiter_rows)
    if any(after_delimiters[row] < count for row, count in before_delimiters.items()):
        structural.append("Markdown table delimiter rows are missing")
    if after.code_fence_blocks != before.code_fence_blocks:
        structural.append("ordered code-fence block structure changed")

    matcher = difflib.SequenceMatcher(a=before_lf.splitlines(), b=after_lf.splitlines())
    deleted_regions = [i2 - i1 for tag, i1, i2, _, _ in matcher.get_opcodes() if tag in {"delete", "replace"}]
    deleted_lines = sum(deleted_regions)
    if deleted_lines > max(20, int(before.physical_line_count * 0.2)):
        structural.append("unexpectedly large total deleted region")
    if deleted_regions and max(deleted_regions) > max(15, int(before.physical_line_count * 0.15)):
        structural.append("unexpectedly large contiguous deleted region")

    for section in required_sections or []:
        if not HEADING_RE.fullmatch(section):
            hard.append(f"required sentinel must be an exact Markdown heading line: {section}")
        elif section not in before.headings:
            hard.append(f"required sentinel heading is absent outside fences in before body: {section}")
        elif section not in after.headings:
            structural.append(f"required sentinel section was removed: {section}")

    return ValidationResult(str(before_path.absolute()), str(after_path.absolute()), before, after, diff, hard, structural)


def _paths_alias(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=False) == right.resolve(strict=False):
            return True
    except OSError:
        if left.absolute() == right.absolute():
            return True
    if left.exists() and right.exists():
        try:
            return os.path.samefile(left, right)
        except OSError:
            return False
    return False


def _diff_aliases_input(result: ValidationResult, path: Path) -> bool:
    return _paths_alias(path, Path(result.before_path)) or _paths_alias(path, Path(result.after_path))


def apply_structural_override(
    result: ValidationResult,
    *,
    reason: str | None,
    diff_evidence_path: Path | None,
) -> ValidationResult:
    """Apply an authorized override only after exact diff evidence is saved."""
    if result.hard_violations or not result.structural_violations:
        return result
    hard = list(result.hard_violations)
    normalized_reason = reason.strip() if reason else ""
    if not normalized_reason:
        hard.append("structural-change override requires a non-empty reason")
    if diff_evidence_path is None:
        hard.append("structural-change override requires saved diff evidence")
    elif _diff_aliases_input(result, diff_evidence_path):
        hard.append("diff evidence path must not alias either input body")
    elif not hard:
        try:
            diff_evidence_path.write_text(result.diff, encoding="utf-8", newline="\n")
            saved = diff_evidence_path.read_text(encoding="utf-8")
        except OSError as exc:
            hard.append(f"failed to save required diff evidence: {exc}")
        else:
            if not result.diff or saved != result.diff:
                hard.append("failed to save required diff evidence exactly")
    if hard:
        return replace(result, hard_violations=hard)
    return replace(
        result,
        override_used=True,
        override_reason=normalized_reason,
        diff_evidence_path=str(diff_evidence_path),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reject structural collapse in long-form GitHub Markdown body updates.")
    parser.add_argument("before_body", type=Path)
    parser.add_argument("after_body", type=Path)
    parser.add_argument("--mode", choices=("localized-update",), default="localized-update")
    parser.add_argument("--required-section", action="append", default=[])
    parser.add_argument("--diff-output", type=Path)
    parser.add_argument("--allow-structural-change", action="store_true")
    parser.add_argument("--override-reason")
    return parser


def _report(result: ValidationResult, mode: str) -> dict[str, object]:
    return {
        "accepted": result.accepted,
        "mode": mode,
        "before": asdict(result.before),
        "after": asdict(result.after),
        "hard_violations": result.hard_violations,
        "structural_violations": result.structural_violations,
        "override_used": result.override_used,
        "override_reason": result.override_reason,
        "diff_evidence_path": result.diff_evidence_path,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate(args.before_body, args.after_body, required_sections=args.required_section)
    except InputValidationError as exc:
        print(json.dumps({"accepted": False, "hard_violations": [str(exc)], "structural_violations": []}, indent=2), file=sys.stderr)
        return 2
    if args.allow_structural_change:
        result = apply_structural_override(result, reason=args.override_reason, diff_evidence_path=args.diff_output)
    elif args.diff_output:
        if _diff_aliases_input(result, args.diff_output):
            result = replace(result, hard_violations=[*result.hard_violations, "diff evidence path must not alias either input body"])
        else:
            try:
                args.diff_output.write_text(result.diff, encoding="utf-8", newline="\n")
            except OSError as exc:
                result = replace(result, hard_violations=[*result.hard_violations, f"failed to save required diff evidence: {exc}"])
    print(json.dumps(_report(result, args.mode), ensure_ascii=False, indent=2))
    if result.diff and not args.diff_output:
        print(result.diff)
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
