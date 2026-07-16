from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SNAPSHOT_PATH = (
    ROOT / "docs" / "reports" / "inventories" / "markdown-inventory.md"
)
ALLOWED_STATUS = {"canonical", "supporting", "historical", "draft", "obsolete"}
SNAPSHOT_ALLOWED_ROLES = {
    "canonical",
    "supporting",
    "evidence",
    "historical",
    "draft",
    "obsolete",
    "merge-candidate",
}
SNAPSHOT_ALLOWED_ACTIONS = {
    "retain",
    "update",
    "translate",
    "move",
    "merge-and-move",
}
SNAPSHOT_ALLOWED_LANGUAGES = {"ja", "mixed", "en"}
MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u7e3a",
    "\u7e67",
    "\u8700",
    "\u9aea",
    "\u8b17",
    "\u9036",
    "\u8b5b",
    "\u83a0",
    "\u7e32",
    "\u0080",
)


@dataclass(frozen=True)
class InventorySnapshotRow:
    path: str
    directory: str
    front_matter_status: str
    role: str
    canonical: str
    destination: str
    language: str
    action: str


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    markdown_count: int = 0
    map_topic_count: int = 0

    @property
    def accepted(self) -> bool:
        return not self.errors


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def tracked_markdown() -> list[str]:
    return sorted(
        line for line in git("ls-files", "--cached", "--", "*.md").splitlines() if line
    )


def front_matter_status(text: str) -> str:
    if not text.startswith("---\n"):
        return "missing"
    end = text.find("\n---\n", 4)
    if end == -1:
        return "malformed"
    match = re.search(r"^status:\s*(\S+)\s*$", text[4:end], re.MULTILINE)
    return match.group(1) if match else "missing"


def directory_role(path: str) -> str:
    """Return placement responsibility without inferring canonical status."""
    if path == "docs/reports/inventories/markdown-inventory.md":
        return "historical-snapshot"
    if path.startswith("docs/reports/"):
        return "reports-index" if Path(path).name == "README.md" else "report-evidence"
    if path.startswith("docs/archive/"):
        return "archive-index" if Path(path).name == "README.md" else "archive-record"
    if path.startswith("docs/design/adr/"):
        return "decision-history"
    if path.startswith("docs/experiment-notes/"):
        return "experiment-evidence"
    if path.startswith("docs/migration/"):
        return "migration-evidence"
    if path.startswith("docs/architecture/"):
        return "architecture-current"
    if path.startswith("docs/contracts/"):
        return "contracts-current"
    if path.startswith("docs/evaluation/"):
        return "evaluation-current"
    if path.startswith("docs/operations/"):
        return "operations-current"
    if path.startswith("docs/"):
        return "docs-entry"
    if path.startswith("research/logs/"):
        return "research-evidence"
    if path.startswith("research/"):
        return "research-current"
    if path.startswith("legacy/") or "/legacy_selfrionette/" in path:
        return "legacy-evidence"
    if path.startswith("firmware/"):
        return "firmware-support"
    return "repository-support"


def allowed_statuses_for_directory(path: str) -> set[str] | None:
    role = directory_role(path)
    return {
        "historical-snapshot": {"historical"},
        "reports-index": {"supporting"},
        "report-evidence": {"historical"},
        "archive-index": {"supporting"},
        "archive-record": {"historical", "draft", "obsolete"},
        "decision-history": {"historical", "supporting"},
        "experiment-evidence": {"historical", "supporting"},
        "migration-evidence": {"historical", "supporting", "canonical"},
        "architecture-current": {"canonical", "supporting"},
        "contracts-current": {"canonical", "supporting"},
        "evaluation-current": {"canonical", "supporting"},
        "operations-current": {"canonical", "supporting"},
        "docs-entry": {"canonical", "supporting", "historical", "draft", "obsolete"},
        "research-evidence": {"historical"},
        "research-current": {"canonical", "supporting"},
    }.get(role)


def parse_inventory_snapshot(
    path: Path = INVENTORY_SNAPSHOT_PATH,
) -> list[InventorySnapshotRow]:
    """Parse the frozen #398/#399 migration snapshot; never use it as a registry."""
    rows: list[InventorySnapshotRow] = []
    if not path.is_file():
        return rows
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| path | current directory |"):
            in_table = True
            continue
        if not in_table or line.startswith("|---") or not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) != 8:
            raise ValueError(f"inventory snapshot row must have 8 cells: {line}")
        rows.append(InventorySnapshotRow(*cells))
    return rows


def changed_paths(base_ref: str | None) -> set[str]:
    if not base_ref:
        return set()
    output = git("diff", "--name-status", "-M", f"{base_ref}..HEAD")
    changed: set[str] = set()
    for line in output.splitlines():
        parts = line.split("\t")
        if parts[0].startswith("R") and len(parts) == 3:
            changed.update(parts[1:])
        elif len(parts) >= 2:
            changed.add(parts[-1])
    return changed


def added_lines(base_ref: str | None, path: str) -> str:
    if not base_ref:
        return ""
    output = git(
        "diff", "--unified=0", f"{base_ref}..HEAD", "--", path, check=False
    )
    return "\n".join(
        line[1:]
        for line in output.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def strip_code(text: str) -> str:
    text = re.sub(r"\`\`\`.*?\`\`\`", "", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`]*`", "", text)


def relative_links(path: str, text: str) -> list[str]:
    clean = strip_code(text)
    targets = []
    for match in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", clean):
        target = match.group(1).strip().split()[0].strip("<>")
        if target and not target.startswith(("#", "http://", "https://", "mailto:")):
            targets.append(target)
    return targets


def broken_link(path: str, target: str) -> bool:
    path_part = unquote(target.split("#", 1)[0])
    if not path_part:
        return False
    return not ((ROOT / path).parent / Path(path_part)).resolve().exists()


def source_map_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in (ROOT / "docs/README.md").read_text(encoding="utf-8").splitlines():
        if (
            not line.startswith("|")
            or line.startswith("|---")
            or "| Topic |" in line
            or "| トピック |" in line
        ):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.search(r"`([^`]+)`", cells[1])
        if match:
            rows.append((cells[0], match.group(1)))
    return rows


def validate(
    *,
    base_ref: str | None = None,
    strict_map: bool = False,
    strict_links: bool = False,
) -> ValidationResult:
    result = ValidationResult([], [])
    paths = tracked_markdown()
    result.markdown_count = len(paths)
    changed = changed_paths(base_ref)
    texts: dict[str, str] = {}
    statuses: dict[str, str] = {}

    for path in paths:
        data = (ROOT / path).read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            result.errors.append(f"UTF-8 BOM is not allowed: {path}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            result.errors.append(f"not UTF-8: {path}: {exc}")
            continue
        texts[path] = text
        if "\r" in text:
            result.errors.append(f"line endings must be LF: {path}")
        found = [marker for marker in MOJIBAKE_MARKERS if marker in text]
        if found:
            result.errors.append(f"mojibake-like marker in {path}: {found!r}")

        status = front_matter_status(text)
        statuses[path] = status
        if path.startswith(("docs/", "research/")) and status not in ALLOWED_STATUS:
            message = f"front matter status is missing or invalid: {path}: {status}"
            (result.errors if path in changed else result.warnings).append(message)
            continue
        allowed = allowed_statuses_for_directory(path)
        if allowed is not None and status in ALLOWED_STATUS and status not in allowed:
            message = (
                f"front matter status conflicts with directory role: "
                f"{path}: {status} not in {sorted(allowed)}"
            )
            (result.errors if path in changed else result.warnings).append(message)

    for path, text in texts.items():
        for target in relative_links(path, text):
            if broken_link(path, target):
                message = f"broken relative link: {path} -> {target}"
                if path in changed or (strict_links and base_ref is None):
                    result.errors.append(message)
                else:
                    result.warnings.append(message)

    map_rows = source_map_rows()
    result.map_topic_count = len(map_rows)
    topic_counts: dict[str, int] = {}
    target_counts: dict[str, int] = {}
    for topic, target in map_rows:
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        target_counts[target] = target_counts.get(target, 0) + 1
        if not (ROOT / target).exists():
            result.errors.append(f"Source of Truth Map target does not exist: {target}")
    duplicates = [
        f"topic {topic!r}" for topic, count in topic_counts.items() if count > 1
    ]
    duplicates.extend(
        f"target {target!r}" for target, count in target_counts.items() if count > 1
    )
    for duplicate in duplicates:
        message = f"Source of Truth Map duplicate: {duplicate}"
        map_changed = "docs/README.md" in changed
        (result.errors if strict_map and (base_ref is None or map_changed) else result.warnings).append(message)

    absolute_path = re.compile(
        r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/](?:Users|Xpotato|Xpotato-apps|Xpotato-Apps)[\\/]"
        r"|(?<![A-Za-z0-9_])/(?:home|Users|mnt)/[^\s`]+"
    )
    for path, text in texts.items():
        hits = absolute_path.findall(text)
        if hits:
            result.warnings.append(
                f"local absolute path candidates: {path}: {len(hits)}"
            )
        if path not in changed or statuses.get(path) not in {"canonical", "supporting"}:
            continue
        added = added_lines(base_ref, path)
        if absolute_path.search(strip_code(added)):
            result.errors.append(
                f"changed current human-facing text adds a local absolute path: {path}"
            )
        prose_lines = [
            line
            for line in strip_code(added).splitlines()
            if line.strip()
            and not line.lstrip().startswith(("---", "|", "#", ">"))
            and not re.match(
                r"^(?:status|owner|last_verified|canonical_for|related):",
                line.strip(),
            )
            and not re.fullmatch(r"[-*+]\s+`[^`]+`", line.strip())
            and not re.fullmatch(
                r"[-*+]\s+\[[^]]+\]\([^)]+\)", line.strip()
            )
            and not re.fullmatch(
                r"[-*+]\s+(?:docs|research|tests|scripts|src|apps|firmware|legacy)/\S+",
                line.strip(),
            )
        ]
        prose = "\n".join(prose_lines)
        latin = len(re.findall(r"[A-Za-z]", prose))
        japanese = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", prose))
        if len(prose_lines) >= 3 and latin >= 120 and japanese == 0:
            result.errors.append(
                f"changed current human-facing prose is English-only: {path}"
            )

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate current Markdown from file metadata, placement, links, and SoT."
    )
    parser.add_argument("--base-ref", help="Git base SHA/ref for changed-files policy")
    parser.add_argument(
        "--strict-map", action="store_true", help="Fail on Source of Truth Map duplicates"
    )
    parser.add_argument(
        "--strict-links", action="store_true", help="Fail on every broken relative link"
    )
    args = parser.parse_args(argv)
    result = validate(
        base_ref=args.base_ref,
        strict_map=args.strict_map,
        strict_links=args.strict_links,
    )
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(
        f"Markdown validation: files={result.markdown_count}, "
        f"SoT topics={result.map_topic_count}, "
        f"warnings={len(result.warnings)}, errors={len(result.errors)}"
    )
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
