from __future__ import annotations

import ast
from importlib import import_module
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


def test_runtime_execution_edges_use_typed_providers_not_broad_plugins() -> None:
    input_loop_source = (SRC / "runtime" / "input_step_loop.py").read_text(
        encoding="utf-8"
    )
    offline_smoke_source = (
        SRC / "runtime" / "offline_input_runtime_smoke.py"
    ).read_text(encoding="utf-8")
    for source in (input_loop_source, offline_smoke_source):
        assert "ResolvedRobotRuntime" not in source
        assert "resolve_robot_runtime" not in source
        assert "plugin.endpoint_position_from_state(" not in source
        assert "plugin.endpoint_orientation_from_state(" not in source
        assert "plugin.build_qpos_feasibility_guard(" not in source
        assert "plugin.build_target_motion_generator(" not in source
        assert "observe_endpoint_pose(" in source

    assert "resolved_robot_runtime" not in input_loop_source
    assert "endpoint_pose_provider: EndpointPoseProvider" in input_loop_source
    assert (
        "endpoint_command_provider: EndpointCommandProvider" in input_loop_source
    )
    assert (
        "qpos_feasibility_provider: QposFeasibilityProvider" in input_loop_source
    )


def test_production_concrete_imports_match_the_documented_allowlist() -> None:
    target_prefixes = (
        "selfrionette.plugins.robots.fast_arm",
        "selfrionette.robots.fast_arm",
        "selfrionette.runtime.fast_arm_",
        "selfrionette.plugins.catalog",
    )
    # Each entry is an explicit production exception with its boundary reason:
    # concrete implementation, catalog, compatibility facade, diagnostic, or
    # application composition root. No generic contract/consumer is implicit.
    allowed = {
        # Single concrete registration SoT.
        Path("plugins/catalog.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.bundle"}
        ),
        # Concrete fast_arm implementation may depend on its sibling declarations.
        Path("plugins/robots/fast_arm/bundle.py"): frozenset(
            {
                "selfrionette.plugins.robots.fast_arm.initial_state",
                "selfrionette.plugins.robots.fast_arm.profile",
                "selfrionette.plugins.robots.fast_arm.runtime",
            }
        ),
        Path("plugins/robots/fast_arm/feasibility.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.profile"}
        ),
        Path("plugins/robots/fast_arm/runtime.py"): frozenset(
            {
                "selfrionette.plugins.robots.fast_arm.feasibility",
                "selfrionette.plugins.robots.fast_arm.profile",
            }
        ),
        # Behavior-free compatibility facades.
        Path("robot_registry.py"): frozenset({"selfrionette.plugins.catalog"}),
        Path("robots/fast_arm.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.profile"}
        ),
        Path("runtime/fast_arm_bundle.py"): frozenset(
            {
                "selfrionette.plugins.robots.fast_arm.bundle",
                "selfrionette.plugins.robots.fast_arm.initial_state",
            }
        ),
        Path("runtime/fast_arm_joint_limits.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.feasibility"}
        ),
        Path("runtime/fast_arm_plugin.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.runtime"}
        ),
        Path("runtime/robot_bundle_registry.py"): frozenset(
            {"selfrionette.plugins.catalog"}
        ),
        Path("runtime/robot_plugin_registry.py"): frozenset(
            {"selfrionette.plugins.catalog"}
        ),
        # Explicit robot-specific diagnostic and legacy compatibility helpers.
        Path("runtime/neutral_initial_pose.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.initial_state"}
        ),
        Path("mujoco_backend/fast_arm_compat.py"): frozenset(
            {"selfrionette.robots.fast_arm"}
        ),
        Path("mujoco_backend/model_loader.py"): frozenset(
            {"selfrionette.robots.fast_arm"}
        ),
        # Current application composition roots; these import only the catalog.
        Path("runtime/concrete_mujoco_pipeline.py"): frozenset(
            {"selfrionette.plugins.catalog"}
        ),
        Path("runtime/input_step_loop.py"): frozenset(
            {"selfrionette.plugins.catalog"}
        ),
        Path("runtime/offline_input_runtime_smoke.py"): frozenset(
            {"selfrionette.plugins.catalog"}
        ),
    }
    actual = {
        path.relative_to(SRC): frozenset(
            imported
            for imported in _imports(path)
            if any(imported.startswith(prefix) for prefix in target_prefixes)
        )
        for path in SRC.rglob("*.py")
    }
    actual = {path: imports for path, imports in actual.items() if imports}
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
        "bundle = runtime.resolve_robot_bundle('fast_arm'); "
        "assert 'selfrionette.plugins.catalog' in sys.modules; "
        "from selfrionette.plugins.catalog import resolve_robot_bundle; "
        "assert resolve_robot_bundle('fast_arm') is bundle"
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


def test_runtime_public_exports_have_one_explicit_owner_and_preserve_identity() -> None:
    import selfrionette.runtime as runtime

    assert set(runtime._PUBLIC_EXPORTS) == set(runtime.__all__)
    source = (SRC / "runtime" / "__init__.py").read_text(encoding="utf-8")
    assert "_PUBLIC_EXPORT_MODULES" not in source
    assert "hasattr(" not in source

    for public_name, (
        module_name,
        attribute_name,
    ) in runtime._PUBLIC_EXPORTS.items():
        owner = import_module(module_name)
        assert getattr(runtime, public_name) is getattr(
            owner, attribute_name
        ), public_name
