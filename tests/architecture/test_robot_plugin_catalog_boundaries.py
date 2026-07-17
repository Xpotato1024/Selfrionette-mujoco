from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "selfrionette"


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return tuple(names)


def test_generic_contracts_do_not_import_catalog_or_concrete_plugins() -> None:
    paths = (
        SRC / "runtime" / "robot_plugin.py",
        SRC / "runtime" / "robot_bundle.py",
        SRC / "runtime" / "robot_provider_adapters.py",
        SRC / "runtime" / "robot_resolution.py",
        SRC / "runtime" / "experiment_contracts.py",
        SRC / "runtime" / "experiment_registry.py",
        SRC / "runtime" / "experiment_composition.py",
        SRC / "runtime" / "evaluation_manifest.py",
    )
    for path in paths:
        imported = _imports(path)
        assert not any(name.startswith("selfrionette.plugins") for name in imported), path
        assert not any("fast_arm" in name for name in imported), path


def test_domain_layers_do_not_reverse_depend_on_assembly_or_manifest() -> None:
    forbidden = (
        "selfrionette.plugins.catalog",
        "selfrionette.runtime.robot_bundle",
        "selfrionette.runtime.robot_bundle_registry",
        "selfrionette.runtime.evaluation_manifest",
    )
    paths = tuple((SRC / "kinematics").rglob("*.py"))
    paths += tuple((SRC / "motion").rglob("*.py"))
    paths += tuple((SRC / "mujoco_backend").rglob("*.py"))
    for path in paths:
        imported = _imports(path)
        assert not any(
            name.startswith(prefix)
            for name in imported
            for prefix in forbidden
        ), path


def test_generic_plugin_axes_do_not_embed_fast_arm_names_or_solver_types() -> None:
    forbidden = (
        "fast_arm",
        "sholder_joint",
        "elbow_joint",
        "FastArm",
        "tip\"",
        "geom",
    )
    for directory in ("environments", "mappings", "tasks", "evaluations"):
        for path in (SRC / "plugins" / directory).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for marker in forbidden:
                assert marker not in source, f"{path}: {marker}"


def test_catalog_imports_are_limited_to_composition_roots_and_facades() -> None:
    allowed = {
        Path("robot_registry.py"),
        Path("runtime/concrete_mujoco_pipeline.py"),
        Path("runtime/input_step_loop.py"),
        Path("runtime/offline_input_runtime_smoke.py"),
        Path("runtime/robot_bundle_registry.py"),
        Path("runtime/robot_plugin_registry.py"),
    }
    actual = {
        path.relative_to(SRC)
        for path in SRC.rglob("*.py")
        if "selfrionette.plugins.catalog" in _imports(path)
    }
    assert actual == allowed


def test_catalog_and_bundle_do_not_introduce_defaults_or_dynamic_discovery() -> None:
    paths = (
        SRC / "plugins" / "catalog.py",
        SRC / "plugins" / "__init__.py",
        SRC / "plugins" / "robots" / "fast_arm" / "bundle.py",
        SRC / "runtime" / "robot_provider_adapters.py",
        SRC / "runtime" / "robot_resolution.py",
    )
    forbidden = (
        "DefaultRobot",
        "DEFAULT_ROBOT_BUNDLE",
        "importlib",
        "__import__",
        "entry_points",
        "pkgutil",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{path}: {marker}"


def test_compatibility_facades_contain_only_imports_and_public_exports() -> None:
    paths = (
        SRC / "robots" / "fast_arm.py",
        SRC / "robot_registry.py",
        SRC / "runtime" / "default_robot_providers.py",
        SRC / "runtime" / "fast_arm_plugin.py",
        SRC / "runtime" / "fast_arm_bundle.py",
        SRC / "runtime" / "fast_arm_joint_limits.py",
        SRC / "runtime" / "robot_plugin_registry.py",
        SRC / "runtime" / "robot_bundle_registry.py",
    )
    allowed_nodes = (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign)
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert all(isinstance(node, allowed_nodes) for node in tree.body), path
        for node in tree.body:
            if isinstance(node, ast.Assign):
                assert all(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in node.targets
                ), path


def test_runtime_package_initialization_is_catalog_free_and_import_order_is_acyclic() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    command = (
        "import sys; import selfrionette.runtime as runtime; "
        "assert 'selfrionette.plugins.catalog' not in sys.modules; "
        "assert runtime.RobotBundle.__module__ == 'selfrionette.runtime.robot_bundle'; "
        "assert 'selfrionette.plugins.catalog' not in sys.modules; "
        "from selfrionette.plugins.catalog import resolve_robot_bundle; "
        "assert resolve_robot_bundle('fast_arm') is runtime.resolve_robot_bundle('fast_arm')"
    )
    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
