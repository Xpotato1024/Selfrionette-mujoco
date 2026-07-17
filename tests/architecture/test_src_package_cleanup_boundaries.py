from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import selfrionette.runtime as runtime
from selfrionette.plugins.catalog import (
    resolve_robot_bundle,
    resolve_robot_profile,
    resolve_robot_runtime_plugin,
)
from selfrionette.plugins.robots.fast_arm.bundle import FAST_ARM_ROBOT_BUNDLE
from selfrionette.plugins.robots.fast_arm.plugin import ROBOT_PLUGIN


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "selfrionette"
GENERIC_PACKAGE_ROOTS = tuple(
    SRC / name for name in ("kinematics", "motion", "mujoco_backend", "runtime")
)
REMOVED_MODULE_PATHS = (
    SRC / "robot_registry.py",
    SRC / "robots" / "fast_arm.py",
    SRC / "kinematics" / "fk.py",
    SRC / "kinematics" / "ik.py",
    SRC / "kinematics" / "fast_arm_endpoint.py",
    SRC / "mujoco_backend" / "fast_arm_compat.py",
    SRC / "runtime" / "default_robot_providers.py",
    SRC / "runtime" / "fast_arm_bundle.py",
    SRC / "runtime" / "fast_arm_joint_limits.py",
    SRC / "runtime" / "fast_arm_plugin.py",
    SRC / "runtime" / "robot_bundle_registry.py",
    SRC / "runtime" / "robot_plugin_registry.py",
    SRC / "runtime" / "endpoint_motion_sanity.py",
    SRC / "runtime" / "jacobian_mobility_diagnostics.py",
    SRC / "runtime" / "neutral_initial_pose.py",
    SRC / "runtime" / "mujoco_pipeline.py",
)
REMOVED_IMPORT_MODULES = frozenset(
    str(path.relative_to(SRC.parent)).removesuffix(".py").replace("\\", ".").replace("/", ".")
    for path in REMOVED_MODULE_PATHS
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def test_generic_packages_do_not_import_fast_arm_plugin_implementation() -> None:
    for package_root in GENERIC_PACKAGE_ROOTS:
        for path in package_root.rglob("*.py"):
            assert not any(
                name == "selfrionette.plugins.robots.fast_arm"
                or name.startswith("selfrionette.plugins.robots.fast_arm.")
                for name in _imports(path)
            ), path.relative_to(ROOT)


def test_plugin_discovery_does_not_eagerly_load_diagnostics() -> None:
    code = (
        "import sys;sys.path.insert(0, 'src');"
        "from selfrionette.plugins.robot_discovery import discover_production_robot_plugins;"
        "discover_production_robot_plugins();"
        "assert not any('.diagnostics' in name for name in sys.modules), "
        "sorted(name for name in sys.modules if '.diagnostics' in name)"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)


def test_removed_facade_and_compatibility_modules_cannot_reappear() -> None:
    assert all(not path.exists() for path in REMOVED_MODULE_PATHS)


def test_repository_has_no_import_consumers_of_removed_modules() -> None:
    roots = (SRC, ROOT / "tests", ROOT / "scripts")
    for root in roots:
        for path in root.rglob("*.py"):
            assert _imports(path).isdisjoint(REMOVED_IMPORT_MODULES), path.relative_to(ROOT)


def test_production_source_contains_no_test_double_modules_or_test_imports() -> None:
    assert not tuple(SRC.rglob("stubs.py"))
    for path in SRC.rglob("*.py"):
        assert not any(name == "tests" or name.startswith("tests.") for name in _imports(path))


def test_generic_kinematics_and_mujoco_packages_are_robot_independent() -> None:
    assert {path.name for path in (SRC / "kinematics").glob("*.py")} == {"__init__.py", "base.py"}
    for path in (SRC / "mujoco_backend").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        strings = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        assert not any("FAST_ARM" in name for name in names), path.relative_to(ROOT)
        assert not any("default_fast_arm" in value for value in strings), path.relative_to(ROOT)


def test_diagnostic_scripts_import_plugin_owned_entrypoints() -> None:
    for path in (ROOT / "scripts").glob("run_fast_arm_*diagnostic*.py"):
        imported = _imports(path)
        assert any(
            name.startswith("selfrionette.plugins.robots.fast_arm.diagnostics")
            for name in imported
        ), path.relative_to(ROOT)
        assert not any(name.startswith("selfrionette.runtime.endpoint_motion_sanity") for name in imported)


def test_public_packages_export_no_test_doubles_or_fast_arm_generic_symbols() -> None:
    for module_name in (
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
        "selfrionette.kinematics",
        "selfrionette.motion",
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.runtime",
    ):
        module = importlib.import_module(module_name)
        assert not any(name.startswith(("NoOp", "Zero", "Static")) for name in module.__all__)
    assert runtime._PUBLIC_EXPORTS.keys() == set(runtime.__all__) or set(runtime._PUBLIC_EXPORTS) == set(runtime.__all__)
    assert not any("FastArm" in name for name in importlib.import_module("selfrionette.kinematics").__all__)
    assert not any("FAST_ARM" in name for name in importlib.import_module("selfrionette.mujoco_backend").__all__)


def test_catalog_registration_bundle_profile_and_runtime_identity_is_unchanged() -> None:
    bundle = resolve_robot_bundle("fast_arm")
    assert bundle is FAST_ARM_ROBOT_BUNDLE
    assert ROBOT_PLUGIN.bundle is bundle
    assert resolve_robot_profile("fast_arm") is bundle.profile
    assert resolve_robot_runtime_plugin("fast_arm") is bundle.runtime_plugin
