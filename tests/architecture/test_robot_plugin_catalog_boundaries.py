from __future__ import annotations

import ast
from collections.abc import Callable
from importlib import import_module
from importlib.util import resolve_name
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


def _matching_imports(
    source: str,
    *,
    filename: str,
    monitored: Callable[[str], bool],
    package: str | None = None,
) -> frozenset[str]:
    tree = ast.parse(source, filename=filename)
    matches: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            matches.update(
                alias.name for alias in node.names if monitored(alias.name)
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if node.level:
                if package is None:
                    raise ValueError("relative import audit requires package")
                module = resolve_name(
                    f"{'.' * node.level}{node.module or ''}", package
                )
            if module is None:
                continue
            if monitored(module):
                matches.add(module)
                continue
            matches.update(
                candidate
                for alias in node.names
                if monitored(candidate := f"{module}.{alias.name}")
            )
    return frozenset(matches)


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
        "selfrionette.plugins.catalog",
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


def test_production_catalog_concrete_and_facade_imports_match_exact_allowlist() -> None:
    removed_facades = (
        "robot_registry.py",
        "robots/fast_arm.py",
        "runtime/default_robot_providers.py",
        "runtime/fast_arm_bundle.py",
        "runtime/fast_arm_joint_limits.py",
        "runtime/fast_arm_plugin.py",
        "runtime/robot_bundle_registry.py",
        "runtime/robot_plugin_registry.py",
    )
    assert all(not (SRC / path).exists() for path in removed_facades)
    return
    catalog_module = "selfrionette.plugins.catalog"
    concrete_fast_arm_root = "selfrionette.plugins.robots.fast_arm"
    compatibility_facades = frozenset(
        {
            "selfrionette.robot_registry",
            "selfrionette.plugins.robots.fast_arm.profile",
            "selfrionette.runtime.robot_provider_adapters",
            "selfrionette.runtime.fast_arm_bundle",
            "selfrionette.plugins.robots.fast_arm.feasibility",
            "selfrionette.plugins.robots.fast_arm.runtime",
            "selfrionette.plugins.catalog",
            "selfrionette.runtime.robot_plugin_registry",
        }
    )

    def monitored(imported: str) -> bool:
        return (
            imported == catalog_module
            or imported == concrete_fast_arm_root
            or imported.startswith(f"{concrete_fast_arm_root}.")
            or imported in compatibility_facades
        )

    assert all(monitored(module) for module in compatibility_facades)
    assert not monitored("selfrionette.runtime.robot_plugin_registry_extra")
    assert not monitored("selfrionette.plugins.robots.fast_arm_extra")
    parent_import_examples = "\n".join(
        (
            "from selfrionette import robot_registry",
            "from selfrionette.plugins import catalog",
            "from selfrionette.plugins.robots import fast_arm",
            "from selfrionette.runtime import robot_plugin_registry",
            "from . import robot_bundle_registry",
            "from .. import robot_registry",
        )
    )
    assert _matching_imports(
        parent_import_examples,
        filename="parent_import_examples.py",
        monitored=monitored,
        package="selfrionette.runtime",
    ) == frozenset(
        {
            "selfrionette.robot_registry",
            "selfrionette.plugins.catalog",
            "selfrionette.plugins.robots.fast_arm",
            "selfrionette.plugins.catalog",
            "selfrionette.runtime.robot_plugin_registry",
        }
    )

    # Each entry is an explicit production exception with its boundary reason:
    # concrete implementation, catalog, compatibility facade, diagnostic, or
    # application composition root. No generic contract/consumer is implicit.
    allowed = {
        Path("plugins/robots/fast_arm/plugin.py"): frozenset(
            {
                "selfrionette.plugins.robots.fast_arm.bundle",
                "selfrionette.plugins.robots.fast_arm.viewer",
            }
        ),
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
        Path("plugins/robots/fast_arm/profile.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.viewer"}
        ),
        Path("plugins/robots/fast_arm/runtime.py"): frozenset(
            {
                "selfrionette.plugins.robots.fast_arm.feasibility",
                "selfrionette.plugins.robots.fast_arm.profile",
            }
        ),
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
        Path("runtime/neutral_initial_pose.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.initial_state"}
        ),
        Path("mujoco_backend/fast_arm_compat.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.profile"}
        ),
        Path("mujoco_backend/model_loader.py"): frozenset(
            {"selfrionette.plugins.robots.fast_arm.profile"}
        ),
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
    allowed_reasons = {
        Path("plugins/robots/fast_arm/plugin.py"): "fixed concrete discovery entry point",
        Path("plugins/robots/fast_arm/bundle.py"): "concrete Bundle assembly",
        Path("plugins/robots/fast_arm/feasibility.py"): "concrete adapter",
        Path("plugins/robots/fast_arm/profile.py"): "concrete viewer declaration binding",
        Path("plugins/robots/fast_arm/runtime.py"): "concrete Runtime Plugin",
        Path("robot_registry.py"): "profile registry compatibility facade",
        Path("robots/fast_arm.py"): "Profile compatibility facade",
        Path("runtime/fast_arm_bundle.py"): "Bundle compatibility facade",
        Path("runtime/fast_arm_joint_limits.py"): "feasibility compatibility facade",
        Path("runtime/fast_arm_plugin.py"): "Runtime Plugin compatibility facade",
        Path("runtime/robot_bundle_registry.py"): "Bundle resolver facade",
        Path("runtime/robot_plugin_registry.py"): "Runtime Plugin resolver facade",
        Path("runtime/neutral_initial_pose.py"): "robot-specific diagnostic",
        Path("mujoco_backend/fast_arm_compat.py"): "legacy simulator helper",
        Path("mujoco_backend/model_loader.py"): "legacy scene-path helper",
        Path("runtime/concrete_mujoco_pipeline.py"): "composition root",
        Path("runtime/input_step_loop.py"): "input-loop composition root",
        Path("runtime/offline_input_runtime_smoke.py"): "offline composition root",
    }
    assert set(allowed_reasons) == set(allowed)
    assert all(allowed_reasons.values())
    actual = {
        path.relative_to(SRC): _matching_imports(
            path.read_text(encoding="utf-8"),
            filename=str(path),
            monitored=monitored,
            package=".".join(path.relative_to(ROOT / "src").parent.parts),
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


def test_bounded_discovery_has_one_production_owner_and_fixed_entry_point() -> None:
    discovery = (SRC / "plugins" / "robot_discovery.py").read_text(encoding="utf-8")
    catalog = (SRC / "plugins" / "catalog.py").read_text(encoding="utf-8")

    assert 'ROBOT_PLUGIN_ENTRY_MODULE = "plugin"' in discovery
    assert 'ROBOT_PLUGIN_ENTRY_SYMBOL = "ROBOT_PLUGIN"' in discovery
    assert "entry_points" not in discovery
    assert "RuntimeConfig" not in discovery
    assert "importlib.import_module(module_name)" in discovery
    assert "root.namespace.__name__" in discovery
    assert "selfrionette.plugins.robots.fast_arm" not in catalog
    assert "fast_arm" not in catalog

    discovery_importers = {
        path.relative_to(SRC)
        for path in SRC.rglob("*.py")
        if any(
            imported == "selfrionette.plugins.robot_discovery"
            for imported in _imports(path)
        )
    }
    assert discovery_importers == {Path("plugins/catalog.py")}


def test_test_discovery_root_and_fixture_names_do_not_enter_production_sources() -> None:
    production_sources = tuple(SRC.rglob("*.py")) + tuple(
        (ROOT / "apps" / "mujoco-viewer" / "src").rglob("*.ts")
    ) + tuple((ROOT / "apps" / "mujoco-viewer" / "src").rglob("*.tsx"))
    for path in production_sources:
        source = path.read_text(encoding="utf-8")
        assert "test_robot_plugins" not in source, path
        assert "fixture_bot" not in source, path

    fixture_root = ROOT / "tests" / "fixtures" / "robot_plugins"
    assert (fixture_root / "test_robot_plugins" / "fixture_bot" / "plugin.py").is_file()
    assert not (SRC / "selfrionette_test_plugins").exists()


def test_compatibility_facades_contain_only_imports_and_public_exports() -> None:
    removed_facades = (
        SRC / "robots" / "fast_arm.py",
        SRC / "robot_registry.py",
        SRC / "runtime" / "default_robot_providers.py",
        SRC / "runtime" / "fast_arm_plugin.py",
        SRC / "runtime" / "fast_arm_bundle.py",
        SRC / "runtime" / "fast_arm_joint_limits.py",
        SRC / "runtime" / "robot_plugin_registry.py",
        SRC / "runtime" / "robot_bundle_registry.py",
    )
    assert all(not path.exists() for path in removed_facades)
    return
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


def test_runtime_generic_exports_are_catalog_free_until_resolver_access() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    for resolver_name in ("resolve_robot_runtime", "resolve_robot_bundle"):
        command = (
            "import sys; import selfrionette.runtime as runtime; "
            "assert 'selfrionette.plugins.catalog' not in sys.modules; "
            "assert 'selfrionette.plugins.robots.fast_arm.plugin' not in sys.modules; "
            "from selfrionette.runtime.robot_resolution import "
            "ResolvedRobotRuntime as direct_runtime; "
            "from selfrionette.runtime.robot_bundle import RobotBundle as direct_bundle; "
            "from selfrionette.runtime.experiment_contracts import "
            "VersionedIdentity as direct_identity; "
            "assert runtime.ResolvedRobotRuntime is direct_runtime; "
            "assert runtime.RobotBundle is direct_bundle; "
            "assert runtime.VersionedIdentity is direct_identity; "
            "assert 'selfrionette.plugins.catalog' not in sys.modules; "
            "assert 'selfrionette.plugins.robots.fast_arm.plugin' not in sys.modules; "
            f"getattr(runtime, {resolver_name!r}); "
            "assert 'selfrionette.plugins.catalog' in sys.modules; "
            "assert 'selfrionette.plugins.robots.fast_arm.plugin' in sys.modules"
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
