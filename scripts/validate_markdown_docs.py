from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "reports" / "inventories" / "markdown-inventory.md"
ALLOWED_STATUS = {"canonical", "supporting", "historical", "draft", "obsolete"}
ALLOWED_ROLES = {
    "canonical",
    "supporting",
    "evidence",
    "historical",
    "draft",
    "obsolete",
    "merge-candidate",
}
ALLOWED_ACTIONS = {"retain", "update", "translate", "move", "merge-and-move"}
ALLOWED_LANGUAGES = {"ja", "mixed", "en"}
MOJIBAKE_MARKERS = ("\ufffd", "\u7e3a", "\u7e67", "\u8700", "\u9aea", "\u8b17", "\u9036", "\u8b5b", "\u83a0", "\u7e32", "\u0080")

OPERATIONS_CANONICAL = {
    "backend-viewer-startup.md",
    "browser-visual-smoke.md",
    "codex-workflow.md",
    "git-pr-workflow.md",
    "hardware-safety.md",
    "japanese-doc-writing-guardrails.md",
    "live-viewer-smoke.md",
    "mujoco-viewer-dev-launcher.md",
    "product-viewer-wasm-scene-renderer.md",
    "r6-l-keyboard-gamepad-live-viewer-smoke.md",
    "r7-a-lite-serial-dry-run-smoke.md",
    "r7-a-lite-websocket-viewer-smoke.md",
    "r7-b-input-driven-websocket-viewer-smoke.md",
    "r7-b-manual-live-loadcell-runtime-runner.md",
    "r7-c-axis-sanity-check.md",
    "r7-c-keyboard-replay-demo-package.md",
    "r7-c-live-loadcell-validation-log.md",
    "r7-c-manual-validation-preflight.md",
    "r7-c-viewer-fixture-demo-procedure.md",
    "r7-d-p3-fast-arm-endpoint-command-check-procedure.md",
    "r7-e-p1-fast-arm-endpoint-motion-sanity.md",
    "runtime-dry-run.md",
    "runtime-to-viewer-e2e-smoke.md",
    "validation.md",
    "websocket-host-port-contract.md",
    "websocket-publisher-runner.md",
}
OPERATIONS_SUPPORTING = {
    "README.md",
    "generic-kinematics-test-doubles.md",
    "robot-runtime-plugin-conformance-tests.md",
}
OPERATIONS_DRAFT_DESTINATIONS = {
    "native-mujoco-fast-arm-viewer-check.md": "docs/operations/native-mujoco-fast-arm-viewer-check.md",
    "provisional-persistent-task-runtime-and-robot-output-round.md": "docs/archive/proposals/provisional-persistent-task-runtime-and-robot-output-round.md",
    "r6-k-p4-live-input-stale-command-safety.md": "docs/archive/drafts/r6-k-p4-live-input-stale-command-safety.md",
    "r7-e-followup-p12-control-frame-resolution-metadata.md": "docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md",
    "r7-e-p10-measured-axis-progress-semantics.md": "docs/archive/drafts/r7-e-p10-measured-axis-progress-semantics.md",
    "r7-e-p11-gamepad-publication-cadence.md": "docs/archive/drafts/r7-e-p11-gamepad-publication-cadence.md",
}
MERGE_TARGETS = {
    "docs/migration/legacy-to-new-layer-map.md": "docs/architecture/dependency-boundaries.md",
    "docs/operations/r6-i-p2-public-export-policy.md": "docs/architecture/dependency-boundaries.md",
    "docs/operations/r6-i-p4-programmed-target-input-contract.md": "docs/contracts/programmed-target-input-source.md",
    "docs/operations/r6-k-p1-runtime-input-source-registry.md": "docs/contracts/runtime-input-source-registry.md",
    "docs/operations/r6-k-p3-input-source-state-payload.md": "docs/contracts/runtime-input-source-state.md",
    "docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md": "docs/contracts/robot-profile-runtime-viewer-profile.md",
    "docs/operations/r7-e-followup-p14-runtime-diagnostic-boundary.md": "docs/architecture/runtime-composition.md",
    "docs/operations/r7-e-followup-viewer-backend-endpoint-separation.md": "docs/architecture/data-flow.md",
    "docs/operations/r7-e-p1-endpoint-target-generator-contract.md": "docs/contracts/endpoint-target-generator.md",
    "docs/operations/r7-e-p22-neutral-initial-pose.md": "docs/contracts/robot-profile-runtime-viewer-profile.md",
    "docs/operations/r7-e-p25-live-viewer-pacing-backlog.md": "docs/architecture/runtime-composition.md",
}


@dataclass(frozen=True)
class InventoryRow:
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
    inventory_count: int = 0
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


def tracked_markdown(*, include_untracked: bool = False) -> list[str]:
    args = ["ls-files", "--cached"]
    if include_untracked:
        args.extend(["--others", "--exclude-standard"])
    args.extend(["--", "*.md"])
    return sorted({line for line in git(*args).splitlines() if line})


def front_matter_status(text: str) -> str:
    if not text.startswith("---\n"):
        return "missing"
    end = text.find("\n---\n", 4)
    if end == -1:
        return "malformed"
    match = re.search(r"^status:\s*(\S+)\s*$", text[4:end], re.MULTILINE)
    return match.group(1) if match else "missing"


def language_state(text: str) -> str:
    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    prose = re.sub(r"`[^`]*`", "", prose)
    japanese = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", prose))
    latin = len(re.findall(r"[A-Za-z]", prose))
    if japanese == 0:
        return "en"
    if japanese >= max(20, latin // 10):
        return "ja"
    return "mixed"


def reports_destination(name: str) -> str:
    if "inventory" in name:
        return f"docs/reports/inventories/{name}"
    if "audit" in name:
        return f"docs/reports/audits/{name}"
    return f"docs/reports/implementation/{name}"


def classify(path: str, status: str, language: str) -> InventoryRow:
    posix = PurePosixPath(path)
    name = posix.name
    directory = str(posix.parent) if str(posix.parent) != "." else "."
    role = "supporting"
    canonical = "docs/README.md"
    destination = path
    action = "retain"

    if path in MERGE_TARGETS:
        role = "merge-candidate"
        canonical = MERGE_TARGETS[path]
        destination = reports_destination(name) if path.startswith("docs/operations/") else path
        action = "merge-and-move" if destination != path else "update"
    elif path == "AGENTS.md":
        role, canonical, action = "canonical", path, "update"
    elif path == "research/README.md":
        role, canonical, action = "canonical", path, "retain"
    elif path.startswith("research/logs/"):
        role, canonical = "evidence", "research/README.md"
    elif path == "docs/reports/inventories/markdown-inventory.md":
        role, canonical = "evidence", "docs/architecture/documentation-sot-policy.md"
    elif path in {"README.md", "apps/mujoco-viewer/README.md"}:
        role, canonical = "supporting", "docs/README.md"
        action = "translate" if language != "ja" else "retain"
    elif path == "docs/README.md" or path == "docs/conventions.md":
        role, canonical = "canonical", path
        action = "translate" if language != "ja" else "retain"
    elif path.startswith("docs/architecture/"):
        if name == "README.md":
            role, canonical = "supporting", "docs/README.md"
        else:
            role, canonical = "canonical", path
        action = "translate" if language != "ja" else "retain"
    elif path.startswith("docs/contracts/"):
        if name == "README.md":
            role, canonical = "supporting", "docs/README.md"
        elif name == "websocket.md":
            role, canonical = "supporting", "docs/contracts/transport-payload.md"
        else:
            role, canonical = "canonical", path
        action = "translate" if role in {"canonical", "supporting"} and language != "ja" else "retain"
    elif path.startswith("docs/evaluation/"):
        role, canonical = "canonical", path
        action = "translate" if language != "ja" else "retain"
    elif path.startswith("docs/operations/"):
        if name in OPERATIONS_CANONICAL:
            role, canonical = "canonical", path
            action = "translate" if language != "ja" else "retain"
        elif name in OPERATIONS_SUPPORTING:
            role, canonical = "supporting", "docs/README.md"
            action = "translate" if language != "ja" else "retain"
        elif name == "wasm-qpos-sync-poc.md":
            role = "historical"
            canonical = "docs/operations/product-viewer-wasm-scene-renderer.md"
            destination = f"docs/archive/operations/{name}"
            action = "move"
        elif name == "r7-e-p8-architecture-endpoint-audit.md":
            role, canonical = "draft", "docs/architecture/runtime-composition.md"
            destination = f"docs/reports/audits/{name}"
            action = "move"
        elif name in OPERATIONS_DRAFT_DESTINATIONS:
            role, canonical = "draft", "docs/README.md"
            destination = OPERATIONS_DRAFT_DESTINATIONS[name]
            action = "move" if destination != path else "retain"
        else:
            role = "evidence"
            canonical = "docs/README.md"
            destination = reports_destination(name)
            action = "move"
    elif path.startswith("docs/reports/"):
        role = "supporting" if name == "README.md" else "evidence"
        canonical = "docs/architecture/documentation-sot-policy.md"
        action = "translate" if name == "README.md" and language != "ja" else "retain"
    elif path.startswith("docs/experiment-notes/"):
        role = "supporting" if name == "README.md" or "/templates/" in path else "evidence"
        canonical = "docs/architecture/documentation-sot-policy.md"
        action = "translate" if name == "README.md" and language != "ja" else "retain"
    elif path.startswith("docs/design/adr/"):
        role = "supporting" if name == "README.md" else "historical"
        canonical = "docs/architecture/development-policy.md"
        action = "translate" if name == "README.md" and language != "ja" else "retain"
    elif path == "docs/design/mujoco-wasm-scene-renderer-design.md":
        role, canonical = "historical", "docs/operations/product-viewer-wasm-scene-renderer.md"
        destination, action = "docs/archive/design/mujoco-wasm-scene-renderer-design.md", "move"
    elif path == "docs/design/README.md":
        role, canonical = "supporting", "docs/architecture/development-policy.md"
        action = "translate" if language != "ja" else "retain"
    elif path == "docs/research/mujoco-webviewer-options.md":
        role, canonical = "historical", "docs/operations/product-viewer-wasm-scene-renderer.md"
        destination, action = "docs/archive/research/mujoco-webviewer-options.md", "move"
    elif path.startswith("docs/migration/"):
        role = "supporting" if name == "README.md" else ("evidence" if name == "legacy-inventory.md" else "historical")
        canonical = "docs/architecture/dependency-boundaries.md"
        action = "translate" if name == "README.md" and language != "ja" else "retain"
    elif path == "docs/index.md":
        role, canonical = "obsolete", "docs/README.md"
        destination, action = "docs/archive/indexes/docs-index.md", "move"
    elif path.startswith("docs/archive/"):
        role, canonical = "supporting" if name == "README.md" else "historical", "docs/architecture/documentation-sot-policy.md"
        action = "translate" if name == "README.md" and language != "ja" else "retain"
    elif name == "REVIEW.md":
        role, canonical = "evidence", "docs/contracts/r7-a-lite-serial-frame-contract.md"
    elif "loadcell_7ch_pro_micro" in path:
        role, canonical = "evidence", "docs/contracts/r7-a-lite-serial-frame-contract.md"
        action = "update"
    elif path == "legacy/fast_arm_control/README.md":
        role, canonical = "supporting", "docs/architecture/dependency-boundaries.md"
        action = "translate" if language != "ja" else "retain"
    elif path.startswith("legacy/") or "/legacy_selfrionette/" in path:
        role, canonical = "historical", "docs/architecture/dependency-boundaries.md"
    elif path.startswith("firmware/"):
        role, canonical = "supporting", "docs/contracts/r7-a-lite-serial-frame-contract.md"
        action = "translate" if language != "ja" else "retain"
    elif path.startswith("src/") or path.startswith("assets/"):
        role, canonical = "supporting", "docs/README.md"
        action = "translate" if language != "ja" else "retain"

    return InventoryRow(path, directory, status, role, canonical, destination, language, action)


def build_inventory_rows(paths: list[str]) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    for path in sorted(paths):
        text = (ROOT / path).read_text(encoding="utf-8") if (ROOT / path).exists() else ""
        rows.append(classify(path, front_matter_status(text), language_state(text)))
    return rows


def inventory_markdown(rows: list[InventoryRow]) -> str:
    counts = {role: 0 for role in sorted(ALLOWED_ROLES)}
    for row in rows:
        counts[row.role] += 1
    summary = " / ".join(f"`{role}` {count}" for role, count in counts.items() if count)
    lines = [
        "---",
        "status: historical",
        "owner: architecture",
        "last_verified: 2026-07-16",
        "canonical_for: []",
        "related:",
        "  - docs/architecture/documentation-sot-policy.md",
        "  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/398",
        "---",
        "",
        "# tracked Markdown inventory",
        "",
        "#398の作業treeに存在する全tracked / 追加予定Markdownを分類した。baseline mainは`cf17fe830645c99b591615b6ffb55a42979c0d5e`である。",
        "",
        "`front matter`はinventory作成時点の値、`proposed role`と`destination`は#399のmigration inputである。`merge-candidate`はcurrent factsだけをcanonicalへ統合し、元本文をevidenceとして保持する。文書は削除しない。",
        "",
        f"- Markdown件数: {len(rows)}",
        f"- role件数: {summary}",
        "- language: `ja` / `mixed` / `en`",
        "- action: `retain` / `update` / `translate` / `move` / `merge-and-move`",
        "",
        "| path | current directory | front matter | proposed role | canonical / related | proposed destination | language | action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        values = [row.path, row.directory, row.front_matter_status, row.role, row.canonical, row.destination, row.language, row.action]
        lines.append("| " + " | ".join(f"`{value}`" for value in values) + " |")
    return "\n".join(lines) + "\n"


def write_inventory() -> None:
    paths = tracked_markdown(include_untracked=True)
    relative_inventory = INVENTORY_PATH.relative_to(ROOT).as_posix()
    if relative_inventory not in paths:
        paths.append(relative_inventory)
    rows = build_inventory_rows(paths)
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_PATH.write_text(inventory_markdown(rows), encoding="utf-8", newline="\n")


def parse_inventory(path: Path = INVENTORY_PATH) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
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
            raise ValueError(f"inventory row must have 8 cells: {line}")
        rows.append(InventoryRow(*cells))
    return rows


def changed_paths(base_ref: str | None) -> set[str]:
    if not base_ref:
        return set()
    output = git("diff", "--name-status", "-M", f"{base_ref}...HEAD")
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
    output = git("diff", "--unified=0", f"{base_ref}...HEAD", "--", path, check=False)
    return "\n".join(
        line[1:]
        for line in output.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
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
        if not line.startswith("|") or line.startswith("|---") or "| Topic |" in line or "| トピック |" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.search(r"`([^`]+)`", cells[1])
        if match:
            rows.append((cells[0], match.group(1)))
    return rows


def validate(*, base_ref: str | None = None, strict_map: bool = False, strict_links: bool = False) -> ValidationResult:
    result = ValidationResult([], [])
    paths = tracked_markdown()
    result.markdown_count = len(paths)
    changed = changed_paths(base_ref)
    texts: dict[str, str] = {}

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
        if path.startswith(("docs/", "research/")) and status not in ALLOWED_STATUS:
            message = f"front matter status is missing or invalid: {path}: {status}"
            (result.errors if path in changed else result.warnings).append(message)

    broken: list[str] = []
    for path, text in texts.items():
        for target in relative_links(path, text):
            if broken_link(path, target):
                message = f"broken relative link: {path} -> {target}"
                broken.append(message)
                if strict_links or path in changed:
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
    duplicates = [f"topic {topic!r}" for topic, count in topic_counts.items() if count > 1]
    duplicates.extend(f"target {target!r}" for target, count in target_counts.items() if count > 1)
    for duplicate in duplicates:
        message = f"Source of Truth Map duplicate: {duplicate}"
        (result.errors if strict_map else result.warnings).append(message)

    try:
        inventory = parse_inventory()
    except ValueError as exc:
        result.errors.append(str(exc))
        inventory = []
    result.inventory_count = len(inventory)
    seen: set[str] = set()
    covered: set[str] = set()
    for row in inventory:
        if row.path in seen:
            result.errors.append(f"duplicate inventory path: {row.path}")
        seen.add(row.path)
        covered.update((row.path, row.destination))
        if row.role not in ALLOWED_ROLES:
            result.errors.append(f"invalid inventory role: {row.path}: {row.role}")
        if row.action not in ALLOWED_ACTIONS:
            result.errors.append(f"invalid inventory action: {row.path}: {row.action}")
        if row.language not in ALLOWED_LANGUAGES:
            result.errors.append(f"invalid inventory language: {row.path}: {row.language}")
        if not (ROOT / row.path).exists() and not (ROOT / row.destination).exists():
            result.errors.append(f"inventory source and destination are both missing: {row.path}")
    for path in sorted(set(paths) - covered):
        result.errors.append(f"tracked Markdown is not classified by inventory: {path}")

    absolute_path = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/](?:Users|Xpotato|Xpotato-apps|Xpotato-Apps)[\\/]|(?<![A-Za-z0-9_])/(?:home|Users|mnt)/[^\s`]+")
    for path, text in texts.items():
        hits = absolute_path.findall(text)
        if hits:
            result.warnings.append(f"local absolute path candidates: {path}: {len(hits)}")
        if path in changed:
            added = added_lines(base_ref, path)
            if absolute_path.search(strip_code(added)):
                result.errors.append(f"changed human-facing text adds a local absolute path: {path}")
            prose_lines = [
                line
                for line in strip_code(added).splitlines()
                if line.strip()
                and not line.lstrip().startswith(("---", "|", "#", ">"))
                and not re.fullmatch(r"[-*+]\s+`[^`]+`", line.strip())
            ]
            prose = "\n".join(prose_lines)
            latin = len(re.findall(r"[A-Za-z]", prose))
            japanese = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", prose))
            if len(prose_lines) >= 3 and latin >= 120 and japanese == 0:
                result.errors.append(f"changed human-facing prose is English-only: {path}")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate tracked Markdown governance and migration inventory.")
    parser.add_argument("--base-ref", help="Git base SHA/ref for changed-files policy")
    parser.add_argument("--strict-map", action="store_true", help="Fail on Source of Truth Map duplicates")
    parser.add_argument("--strict-links", action="store_true", help="Fail on every broken relative link")
    parser.add_argument("--write-inventory", action="store_true", help="Regenerate the #398 migration inventory")
    args = parser.parse_args(argv)
    if args.write_inventory:
        write_inventory()
    result = validate(base_ref=args.base_ref, strict_map=args.strict_map, strict_links=args.strict_links)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(
        f"Markdown validation: files={result.markdown_count}, inventory={result.inventory_count}, "
        f"SoT topics={result.map_topic_count}, warnings={len(result.warnings)}, errors={len(result.errors)}"
    )
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
