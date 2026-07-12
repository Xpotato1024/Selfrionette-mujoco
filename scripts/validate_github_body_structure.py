from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys


HEADING_RE = re.compile(r"^#{1,6} .+$")
TABLE_DELIMITER_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
MOJIBAKE_MARKERS = ("\ufffd", "???", "\u7e3a", "\u7e67", "\u8700", "\u9aea", "\u8b17", "\u9036", "\u8b5b", "\u83a0", "\u7e32", "\u0080")


@dataclass(frozen=True)
class BodyMetrics:
    byte_length: int
    sha256: str
    physical_line_count: int
    newline_count: int
    headings: list[str]
    table_delimiter_rows: list[str]
    code_fence_count: int


@dataclass(frozen=True)
class ValidationResult:
    before: BodyMetrics
    after: BodyMetrics
    diff: str
    violations: list[str]
    override_used: bool = False
    override_reason: str | None = None

    @property
    def accepted(self) -> bool:
        return not self.violations or self.override_used


def _decode(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"UTF-8 BOM is not allowed: {path}")
    try:
        return data, data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"body is not UTF-8: {path}: {exc}") from exc


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _metrics(data: bytes, text: str) -> BodyMetrics:
    normalized = _lf(text)
    lines = normalized.splitlines()
    return BodyMetrics(
        byte_length=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        physical_line_count=len(lines),
        newline_count=normalized.count("\n"),
        headings=[line for line in lines if HEADING_RE.fullmatch(line)],
        table_delimiter_rows=[line for line in lines if TABLE_DELIMITER_RE.fullmatch(line)],
        code_fence_count=sum(line.lstrip().startswith("```") for line in lines),
    )


def _is_ordered_subsequence(required: list[str], actual: list[str]) -> bool:
    iterator = iter(actual)
    return all(any(candidate == item for candidate in iterator) for item in required)


def validate(
    before_path: Path,
    after_path: Path,
    *,
    required_sections: list[str] | None = None,
    allow_structural_change: bool = False,
    override_reason: str | None = None,
) -> ValidationResult:
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
    violations: list[str] = []

    if before.physical_line_count > 1 and after.physical_line_count <= 1:
        violations.append("multiline body collapsed to one physical line")
    if before.newline_count >= 10 and after.newline_count < before.newline_count * 0.7:
        violations.append("newline count collapsed by more than 30%")
    if before.physical_line_count >= 10 and after.physical_line_count < before.physical_line_count * 0.7:
        violations.append("physical line count collapsed by more than 30%")
    if not _is_ordered_subsequence(before.headings, after.headings):
        violations.append("Markdown headings are missing or reordered")

    before_delimiters = Counter(before.table_delimiter_rows)
    after_delimiters = Counter(after.table_delimiter_rows)
    if any(after_delimiters[row] < count for row, count in before_delimiters.items()):
        violations.append("Markdown table delimiter rows are missing")
    if after.code_fence_count % 2:
        violations.append("proposed body has unbalanced code fences")
    if after.code_fence_count < before.code_fence_count:
        violations.append("code fences were removed")

    matcher = difflib.SequenceMatcher(a=before_lf.splitlines(), b=after_lf.splitlines())
    deleted_regions = [i2 - i1 for tag, i1, i2, _, _ in matcher.get_opcodes() if tag in {"delete", "replace"}]
    deleted_lines = sum(deleted_regions)
    if deleted_lines > max(20, int(before.physical_line_count * 0.2)):
        violations.append("unexpectedly large total deleted region")
    if deleted_regions and max(deleted_regions) > max(15, int(before.physical_line_count * 0.15)):
        violations.append("unexpectedly large contiguous deleted region")

    for section in required_sections or []:
        if section not in before_lf:
            violations.append(f"required sentinel is absent from before body: {section}")
        elif section not in after_lf:
            violations.append(f"required sentinel section was removed: {section}")
    found_markers = [marker for marker in MOJIBAKE_MARKERS if marker in after_lf]
    if found_markers:
        violations.append(f"replacement or mojibake marker found: {found_markers!r}")
    if after_lf.count("?") > before_lf.count("?"):
        violations.append("unexpected question-mark replacement found")

    if allow_structural_change and not override_reason:
        violations.append("structural-change override requires a non-empty reason")
    override_used = allow_structural_change and bool(override_reason)
    return ValidationResult(before, after, diff, violations, override_used, override_reason)


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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.allow_structural_change and args.diff_output is None:
        print("ERROR: structural-change override requires --diff-output", file=sys.stderr)
        return 2
    try:
        result = validate(
            args.before_body,
            args.after_body,
            required_sections=args.required_section,
            allow_structural_change=args.allow_structural_change,
            override_reason=args.override_reason,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.diff_output:
        args.diff_output.write_text(result.diff, encoding="utf-8", newline="\n")
    report = {
        "accepted": result.accepted,
        "mode": args.mode,
        "before": asdict(result.before),
        "after": asdict(result.after),
        "violations": result.violations,
        "override_used": result.override_used,
        "override_reason": result.override_reason,
        "diff_output": str(args.diff_output) if args.diff_output else None,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if result.diff and not args.diff_output:
        print(result.diff)
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
