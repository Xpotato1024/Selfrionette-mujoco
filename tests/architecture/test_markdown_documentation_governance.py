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


def test_inventory_classification_enums_are_complete() -> None:
    rows = MODULE.parse_inventory()
    assert rows
    assert len({row.path for row in rows}) == len(rows)
    assert {row.role for row in rows} <= MODULE.ALLOWED_ROLES
    assert {row.action for row in rows} <= MODULE.ALLOWED_ACTIONS
    assert {row.language for row in rows} <= MODULE.ALLOWED_LANGUAGES


def test_all_tracked_markdown_is_classified() -> None:
    rows = MODULE.parse_inventory()
    covered = {row.path for row in rows} | {row.destination for row in rows}
    assert set(MODULE.tracked_markdown()) <= covered


def test_source_of_truth_map_targets_exist() -> None:
    rows = MODULE.source_map_rows()
    assert rows
    for _, target in rows:
        assert (MODULE.ROOT / target).exists(), target


def test_repository_markdown_encoding_and_inventory_are_accepted() -> None:
    result = MODULE.validate()
    assert result.accepted, result.errors
