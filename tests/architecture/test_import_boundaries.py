from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "selfrionette"

FORBIDDEN_IMPORTS = {
    "input_sources": [
        "selfrionette.motion",
        "selfrionette.kinematics",
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.runtime",
    ],
    "input_interpreters": [
        "selfrionette.motion",
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.runtime",
    ],
    "kinematics": [
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.runtime",
    ],
    "mujoco_backend": [
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
        "selfrionette.motion",
        "selfrionette.transport",
        "selfrionette.runtime",
    ],
    "transport": [
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
        "selfrionette.motion",
        "selfrionette.kinematics",
        "selfrionette.mujoco_backend",
        "selfrionette.runtime",
    ],
}


def iter_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def test_import_boundaries() -> None:
    violations: list[str] = []

    for layer, forbidden_prefixes in FORBIDDEN_IMPORTS.items():
        for path in (SRC_ROOT / layer).rglob("*.py"):
            for imported in iter_imports(path):
                for forbidden in forbidden_prefixes:
                    if imported.startswith(forbidden):
                        violations.append(
                            f"{path.relative_to(ROOT)} imports {imported}; "
                            f"forbidden prefix: {forbidden}"
                        )

    assert not violations, "\n".join(violations)
