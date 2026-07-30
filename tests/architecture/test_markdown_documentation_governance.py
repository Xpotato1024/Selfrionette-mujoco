from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "repository" / "validate_markdown_docs.py"
SPEC = importlib.util.spec_from_file_location("validate_markdown_docs", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_historical_inventory_snapshot_is_frozen_and_well_formed() -> None:
    text = MODULE.INVENTORY_SNAPSHOT_PATH.read_text(encoding="utf-8")
    rows = MODULE.parse_inventory_snapshot()
    assert rows
    assert len({row.path for row in rows}) == len(rows)
    assert {row.role for row in rows} <= MODULE.SNAPSHOT_ALLOWED_ROLES
    assert {row.action for row in rows} <= MODULE.SNAPSHOT_ALLOWED_ACTIONS
    assert {row.language for row in rows} <= MODULE.SNAPSHOT_ALLOWED_LANGUAGES
    assert "snapshot_date: 2026-07-16" in text
    assert "baseline_commit: cf17fe830645c99b591615b6ffb55a42979c0d5e" in text
    assert "frozen: true" in text
    assert not hasattr(MODULE, "write_inventory")
    assert "--write-inventory" not in SCRIPT_PATH.read_text(encoding="utf-8")


def test_all_tracked_markdown_has_a_current_directory_role() -> None:
    paths = MODULE.tracked_markdown()
    assert paths
    assert all(MODULE.directory_role(path) for path in paths)


def test_directory_role_status_matrix_is_responsibility_specific() -> None:
    expected = {
        "docs/architecture/example.md": ("architecture-current", {"canonical", "supporting"}),
        "docs/contracts/example.md": ("contracts-current", {"canonical", "supporting"}),
        "docs/evaluation/example.md": ("evaluation-current", {"canonical", "supporting"}),
        "docs/operations/example.md": ("operations-current", {"canonical", "supporting"}),
        "docs/reports/README.md": ("reports-index", {"supporting"}),
        "docs/reports/implementation/example.md": ("report-evidence", {"historical"}),
        "docs/archive/README.md": ("archive-index", {"supporting"}),
        "docs/archive/operations/example.md": (
            "archive-record",
            {"historical", "draft", "obsolete"},
        ),
    }
    for path, (role, statuses) in expected.items():
        assert MODULE.directory_role(path) == role
        assert MODULE.allowed_statuses_for_directory(path) == statuses


def test_current_directories_contain_only_current_statuses() -> None:
    current_roots = (
        "docs/architecture/",
        "docs/contracts/",
        "docs/evaluation/",
        "docs/operations/",
    )
    for path in MODULE.tracked_markdown():
        if path.startswith(current_roots):
            text = (MODULE.ROOT / path).read_text(encoding="utf-8")
            assert MODULE.front_matter_status(text) in {"canonical", "supporting"}, path


def test_current_validation_does_not_read_historical_snapshot(monkeypatch) -> None:
    def fail_if_called():
        raise AssertionError("historical snapshot must not be a current registry")

    monkeypatch.setattr(MODULE, "parse_inventory_snapshot", fail_if_called)
    result = MODULE.validate()
    assert result.accepted, result.errors


def test_source_of_truth_map_targets_exist() -> None:
    rows = MODULE.source_map_rows()
    assert rows
    for _, target in rows:
        assert (MODULE.ROOT / target).exists(), target


def test_current_metadata_and_canonical_ownership_are_complete() -> None:
    topics: dict[str, str] = {}
    for path in MODULE.tracked_markdown():
        text = (MODULE.ROOT / path).read_text(encoding="utf-8")
        fields = MODULE.front_matter_fields(text)
        status = MODULE.front_matter_status(text)
        if status not in {"canonical", "supporting"}:
            continue
        assert {
            "status",
            "owner",
            "last_verified",
            "canonical_for",
            "related",
        } <= fields.keys(), path
        canonical_for = fields["canonical_for"]
        assert isinstance(canonical_for, tuple), path
        if status == "supporting":
            assert not canonical_for, path
            continue
        assert canonical_for, path
        for topic in canonical_for:
            assert topic not in topics, (topic, topics.get(topic), path)
            topics[topic] = path


def test_source_of_truth_map_covers_every_current_canonical_document() -> None:
    targets = {target for _, target in MODULE.source_map_rows()}
    expected = {
        path
        for path in MODULE.tracked_markdown()
        if path != "docs/README.md"
        and path.startswith(("docs/", "research/"))
        and MODULE.front_matter_status(
            (MODULE.ROOT / path).read_text(encoding="utf-8")
        )
        == "canonical"
    }
    assert targets == expected


def test_repository_current_markdown_governance_is_accepted() -> None:
    result = MODULE.validate(strict_map=True, strict_links=True)
    assert result.accepted, result.errors


def test_changed_files_strict_policy_accepts_unmodified_baseline_debt(
    monkeypatch,
) -> None:
    monkeypatch.setattr(MODULE, "changed_paths", lambda _base_ref: set())
    result = MODULE.validate(
        base_ref="synthetic-baseline",
        strict_map=True,
        strict_links=True,
    )
    assert result.accepted, result.errors


def _configure_temp_markdown_repository(
    monkeypatch, tmp_path: Path, files: dict[str, str], changed: set[str]
) -> None:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    monkeypatch.setattr(MODULE, "tracked_markdown", lambda: sorted(files))
    monkeypatch.setattr(MODULE, "changed_paths", lambda _base_ref: changed)


def test_changed_governed_markdown_requires_valid_front_matter(
    monkeypatch, tmp_path: Path
) -> None:
    files = {
        "docs/README.md": "# empty SoT map\n",
        "docs/new.md": "# front matterなし\n",
    }
    _configure_temp_markdown_repository(monkeypatch, tmp_path, files, {"docs/new.md"})
    result = MODULE.validate(base_ref="base")
    assert any("front matter status is missing or invalid: docs/new.md" in error for error in result.errors)


def test_changed_current_prose_rejects_english_only_and_local_path(
    monkeypatch, tmp_path: Path
) -> None:
    files = {
        "docs/README.md": "# empty SoT map\n",
        "docs/current.md": "---\nstatus: canonical\n---\n\n# 現在仕様\n",
    }
    _configure_temp_markdown_repository(monkeypatch, tmp_path, files, {"docs/current.md"})
    added = "\n".join(
        (
            "This newly added paragraph contains enough English prose to be a human-facing explanation.",
            "It intentionally exceeds the policy threshold and contains no Japanese explanation at all.",
            "The operator should run it from D:/Xpotato-apps/private-checkout before continuing validation.",
        )
    )
    monkeypatch.setattr(MODULE, "added_lines", lambda _base_ref, _path: added)
    result = MODULE.validate(base_ref="base")
    assert any("English-only" in error for error in result.errors)
    assert any("local absolute path" in error for error in result.errors)


def test_changed_strict_map_and_links_are_hard_failures(
    monkeypatch, tmp_path: Path
) -> None:
    files = {
        "docs/README.md": "| Topic | Canonical |\n|---|---|\n| duplicate | `docs/current.md` |\n| duplicate | `docs/current.md` |\n",
        "docs/current.md": "---\nstatus: canonical\n---\n\n[missing](missing.md)\n",
    }
    _configure_temp_markdown_repository(
        monkeypatch, tmp_path, files, {"docs/README.md", "docs/current.md"}
    )
    monkeypatch.setattr(MODULE, "added_lines", lambda _base_ref, _path: "")
    result = MODULE.validate(base_ref="base", strict_map=True, strict_links=True)
    assert any("broken relative link" in error for error in result.errors)
    assert any("Source of Truth Map duplicate" in error for error in result.errors)


def test_agents_requires_docs_research_and_experiment_impact_gate() -> None:
    text = (MODULE.ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for marker in (
        "### Task impact gate",
        "Documentation impact",
        "Research log impact",
        "Experiment evidence impact",
        "research/README.md",
        "docs/experiment-notes/README.md",
        "更新不要理由",
    ):
        assert marker in text


def test_research_log_policy_uses_substantive_research_impact() -> None:
    text = (MODULE.ROOT / "research/README.md").read_text(encoding="utf-8")
    for marker in (
        "変更したファイルやdirectoryではなく",
        "研究で実行または評価できる対象",
        "AGENTS.md",
        "documentation governance",
        "CI、validator、repository hygiene",
        "実質的に変える場合は更新対象",
        "docs/experiment-notes/",
        "更新不要理由",
    ):
        assert marker in text


def test_codex_workflow_connects_all_impact_decisions() -> None:
    text = (MODULE.ROOT / "docs/operations/codex-workflow.md").read_text(encoding="utf-8")
    assert "Documentation impact" in text
    assert "Research log impact" in text
    assert "Experiment evidence impact" in text
    assert "変更ファイルの種類で決めない" in text
    assert "research/README.md" in text
