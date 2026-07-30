"""Issue #485で確定した重要code documentation boundaryのfocused guard。"""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _module(path: str) -> ast.Module:
    return ast.parse((REPOSITORY_ROOT / path).read_text(encoding="utf-8"))


def _documented_top_level_symbols(path: str) -> dict[str, str]:
    tree = _module(path)
    return {
        node.name: ast.get_docstring(node) or ""
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_architecture_sensitive_python_contracts_have_semantic_documentation() -> None:
    required_symbols = {
        "src/selfrionette/runtime/experiment/contracts.py": {
            "VersionedIdentity",
            "CommandSemanticsRoute",
            "EnvironmentPlugin",
            "ControlMappingPlugin",
            "TaskPlugin",
            "EvaluationPlugin",
        },
        "src/selfrionette/runtime/experiment/composition.py": {
            "ResolvedExperimentComposition",
            "compose_experiment",
        },
        "src/selfrionette/runtime/composition/robot_bundle.py": {
            "RobotCommandSemanticProvider",
            "RobotBundle",
        },
        "src/selfrionette/runtime/execution/command_routes.py": {
            "ResolvedCommandExecution",
            "NativeEndpointVelocityCommandExecutionBinding",
        },
        "src/selfrionette/runtime/control/endpoint_target_generator.py": {
            "EndpointTargetGeneratorConfig",
            "EndpointTargetGeneratorState",
            "generate_endpoint_target",
        },
    }

    for path, names in required_symbols.items():
        documented = _documented_top_level_symbols(path)
        assert names <= documented.keys()
        assert all(documented[name].strip() for name in names)


def test_fixed_plugin_entry_points_document_declaration_without_starting_lifecycle() -> None:
    entry_points = sorted(
        (REPOSITORY_ROOT / "src/selfrionette/plugins").glob("**/plugin.py")
    )
    assert entry_points

    for path in entry_points:
        module_doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        assert "declaration" in module_doc
        assert "import" in module_doc
        assert any(marker in module_doc for marker in ("開始しない", "行わない", "実行しない"))


def test_viewer_boundary_jsdoc_preserves_mujoco_sot_and_qpos_ordering() -> None:
    qpos_sync = (
        REPOSITORY_ROOT
        / "apps/mujoco-viewer/src/wasm-scene/mujocoQposSync.ts"
    ).read_text(encoding="utf-8")
    renderer = (
        REPOSITORY_ROOT
        / "apps/mujoco-viewer/src/wasm-scene/mujocoSceneRenderer.ts"
    ).read_text(encoding="utf-8")
    input_provider = (
        REPOSITORY_ROOT
        / "apps/mujoco-viewer/src/input/viewerInputProvider.ts"
    ).read_text(encoding="utf-8")

    assert "model ordering" in qpos_sync
    assert "fallbackしない" in qpos_sync
    assert "physical stateをSoT" in renderer
    assert "viewer-side FK/IK" in renderer
    assert "backend Mapping" in input_provider
