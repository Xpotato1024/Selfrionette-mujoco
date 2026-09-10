from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PERMISSION_PATH = ROOT / "src" / "selfrionette" / "runtime" / "output" / "permission.py"
TRACE_PATH = ROOT / "src" / "selfrionette" / "runtime" / "output" / "trace.py"
FORBIDDEN_IMPORT_ROOTS = {
    "mujoco",
    "osc4py3",
    "pythonosc",
    "serial",
    "socket",
    "usb",
}
FORBIDDEN_SELF_RIONETTE_IMPORTS = (
    "selfrionette.plugins.robots",
    "selfrionette.runtime.execution",
    "selfrionette.runtime.runners",
    "selfrionette.transport",
)


def _imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_permission_evaluator_has_no_transport_or_hardware_imports() -> None:
    tree = ast.parse(
        PERMISSION_PATH.read_text(encoding="utf-8"),
        filename=str(PERMISSION_PATH),
    )
    imported = _imported_modules(tree)
    assert {
        module.split(".", maxsplit=1)[0]
        for module in imported
    }.isdisjoint(FORBIDDEN_IMPORT_ROOTS)
    assert all(
        not any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in FORBIDDEN_SELF_RIONETTE_IMPORTS
        )
        for module in imported
    )

    calls = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert calls.isdisjoint({"connect", "send", "write"})


def test_trace_owner_has_no_transport_or_hardware_imports() -> None:
    tree = ast.parse(TRACE_PATH.read_text(encoding="utf-8"), filename=str(TRACE_PATH))
    imported = _imported_modules(tree)
    assert {
        module.split(".", maxsplit=1)[0]
        for module in imported
    }.isdisjoint(FORBIDDEN_IMPORT_ROOTS)
    assert all(
        not any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in FORBIDDEN_SELF_RIONETTE_IMPORTS
        )
        for module in imported
    )
