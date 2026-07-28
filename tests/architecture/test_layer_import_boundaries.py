from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VIEWER_SRC_ROOT = ROOT / "apps" / "mujoco-viewer" / "src"

VIEWER_FORBIDDEN_IMPORT_MARKERS = (
    "mujoco_backend",
    "mujoco",
    "rapier",
    "ik",
    "fk",
)

VIEWER_ALLOWED_IMPORT_MARKERS_BY_DIR = {
    "wasm-scene": ("mujoco",),
}

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

def test_viewer_app_src_does_not_import_backend_or_physics_layers() -> None:
    violations: list[str] = []

    for path in VIEWER_SRC_ROOT.rglob("*.ts"):
        allowed_markers: tuple[str, ...] = ()
        path_parts = {part.lower() for part in path.parts}
        for directory, markers in VIEWER_ALLOWED_IMPORT_MARKERS_BY_DIR.items():
            if directory in path_parts:
                allowed_markers = markers
                break

        for imported in iter_ts_imports(path):
            lowered = imported.lower()
            for forbidden in VIEWER_FORBIDDEN_IMPORT_MARKERS:
                if forbidden in lowered and forbidden not in allowed_markers:
                    violations.append(
                        f"{path.relative_to(ROOT)} imports {imported}; forbidden marker: {forbidden}"
                    )

    assert not violations, "\n".join(violations)
