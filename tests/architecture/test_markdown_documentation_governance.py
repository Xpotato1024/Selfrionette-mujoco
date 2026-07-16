from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "validate_markdown_docs.py"
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


def test_repository_current_markdown_governance_is_accepted() -> None:
    result = MODULE.validate()
    assert result.accepted, result.errors


def test_changed_files_strict_policy_accepts_unmodified_baseline_debt() -> None:
    result = MODULE.validate(
        base_ref="cf17fe830645c99b591615b6ffb55a42979c0d5e",
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
