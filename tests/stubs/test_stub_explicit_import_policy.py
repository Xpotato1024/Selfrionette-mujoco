from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = ROOT / "tests"

FORBIDDEN_STUB_IMPORTS = {
    "selfrionette.input_sources": {"StaticInputSource"},
    "selfrionette.input_interpreters": {"NoOpInputInterpreter"},
    "selfrionette.kinematics": {"ZeroForwardKinematicsSolver", "ZeroInverseKinematicsSolver"},
    "selfrionette.motion": {"NoOpMotionGenerator"},
    "selfrionette.mujoco_backend": {"NoOpMuJoCoSimulator"},
    "selfrionette.transport": {"NoOpStatePublisher"},
}


def test_tests_use_explicit_stub_imports() -> None:
    violations: list[str] = []

    for path in TEST_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_names = {alias.name for alias in node.names}
                for module_name, forbidden_names in FORBIDDEN_STUB_IMPORTS.items():
                    if node.module == module_name and imported_names & forbidden_names:
                        violations.append(
                            f"{path.relative_to(ROOT)} imports {sorted(imported_names & forbidden_names)} from {module_name}; use .stubs"
                        )

    assert not violations, "\n".join(violations)
