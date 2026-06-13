from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "selfrionette"
VIEWER_SRC_ROOT = ROOT / "apps" / "mujoco-viewer" / "src"

PY_LAYER_FORBIDDEN_IMPORTS = {
    "input_sources": (
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.viewer",
        "selfrionette.motion",
        "selfrionette.kinematics",
    ),
    "input_interpreters": (
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.viewer",
        "selfrionette.motion",
        "selfrionette.kinematics",
    ),
    "motion": (
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.viewer",
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
    ),
    "kinematics": (
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.viewer",
    ),
}

VIEWER_FORBIDDEN_IMPORT_MARKERS = (
    "mujoco_backend",
    "mujoco",
    "rapier",
    "ik",
    "fk",
)


def iter_python_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def iter_ts_imports(path: Path) -> list[str]:
    imports: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith(("import ", "export ")):
            continue
        if " from " not in stripped:
            continue

        module = stripped.rsplit(" from ", 1)[1].rstrip(";")
        if module[:1] in {"'", '"'} and module[-1:] == module[:1]:
            module = module[1:-1]
        imports.append(module)

    return imports


def test_source_layer_import_boundaries_cover_replay_and_motion_layers() -> None:
    violations: list[str] = []

    for layer, forbidden_imports in PY_LAYER_FORBIDDEN_IMPORTS.items():
        for path in (SRC_ROOT / layer).rglob("*.py"):
            for imported in iter_python_imports(path):
                for forbidden in forbidden_imports:
                    if imported.startswith(forbidden):
                        violations.append(
                            f"{path.relative_to(ROOT)} imports {imported}; forbidden prefix: {forbidden}"
                        )

    assert not violations, "\n".join(violations)


def test_viewer_app_src_does_not_import_backend_or_physics_layers() -> None:
    violations: list[str] = []

    for path in VIEWER_SRC_ROOT.rglob("*.ts"):
        for imported in iter_ts_imports(path):
            lowered = imported.lower()
            for forbidden in VIEWER_FORBIDDEN_IMPORT_MARKERS:
                if forbidden in lowered:
                    violations.append(
                        f"{path.relative_to(ROOT)} imports {imported}; forbidden marker: {forbidden}"
                    )

    assert not violations, "\n".join(violations)
