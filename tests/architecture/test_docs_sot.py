from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_STATUS = {"canonical", "supporting", "historical", "draft", "obsolete"}
CANONICAL_DOCS = [
    "docs/README.md",
    "docs/conventions.md",
    "docs/architecture/development-policy.md",
    "docs/architecture/mujoco-skeleton-first-spec.md",
    "docs/architecture/documentation-sot-policy.md",
    "docs/architecture/dependency-boundaries.md",
    "docs/architecture/data-flow.md",
    "docs/architecture/runtime-composition.md",
    "docs/contracts/schemas.md",
    "docs/contracts/mujoco-state.md",
    "docs/contracts/websocket.md",
    "docs/contracts/assets.md",
    "docs/operations/git-pr-workflow.md",
    "docs/operations/validation.md",
    "docs/operations/hardware-safety.md",
    "docs/operations/codex-workflow.md",
    "docs/migration/legacy-inventory.md",
    "docs/migration/legacy-to-new-layer-map.md",
    "docs/migration/rapier-to-mujoco-migration.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def front_matter(text: str) -> str:
    assert text.startswith("---\n"), "missing opening front matter delimiter"
    end = text.find("\n---\n", 4)
    assert end != -1, "missing closing front matter delimiter"
    return text[4:end]


def status_value(front: str) -> str:
    for line in front.splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("front matter missing status")


def test_docs_sot_required_paths_exist() -> None:
    required = [
        "docs/README.md",
        "docs/conventions.md",
        "docs/architecture/documentation-sot-policy.md",
        "docs/architecture/dependency-boundaries.md",
    ]

    for path in required:
        assert (ROOT / path).is_file(), path


def test_doc_directory_is_not_used() -> None:
    assert not (ROOT / "doc").exists()


def test_canonical_docs_have_valid_front_matter() -> None:
    for path in CANONICAL_DOCS:
        front = front_matter(read(path))
        assert status_value(front) in ALLOWED_STATUS, path


def test_docs_readme_has_source_of_truth_map() -> None:
    text = read("docs/README.md")
    assert "Source of Truth Map" in text
    assert "| Topic | Canonical document | Notes |" in text
