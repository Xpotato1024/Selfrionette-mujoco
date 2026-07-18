from __future__ import annotations

import ast
import importlib
import sys
import tomllib
from pathlib import Path

import pytest

from fast_arm_core.joint_limits import FastArmJointLimit
from fast_arm_core.reference.initial_state import FAST_ARM_INITIAL_STATE
from selfrionette.plugins.robots.fast_arm import bundle as compatibility_bundle
from selfrionette.plugins.robots.fast_arm import kinematics as compatibility_kinematics
from selfrionette.plugins.robots.fast_arm.adapter import bundle as adapter_bundle
from selfrionette.plugins.robots.fast_arm.adapter import kinematics as adapter_kinematics
from selfrionette.plugins.robots.fast_arm.adapter.initial_state import (
    FAST_ARM_INITIAL_STATE_CONTRACT,
)
from selfrionette.plugins.robots.fast_arm.adapter.profile import FAST_ARM_ROBOT_PROFILE
from selfrionette.runtime.composition.robot_resource import (
    PackageResource,
    package_resource_traversable,
)


ROOT = Path(__file__).resolve().parents[2]
FAST_ARM_ROOT = ROOT / "src/selfrionette/plugins/robots/fast_arm"
CORE_PROJECT = FAST_ARM_ROOT / "core"
CORE_SOURCE = CORE_PROJECT / "src/fast_arm_core"


def _imports(path: Path) -> set[str]:
    imported: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_fast_arm_core_is_an_independent_distribution() -> None:
    project = tomllib.loads((CORE_PROJECT / "pyproject.toml").read_text(encoding="utf-8"))
    root_project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["name"] == "fast_arm_core"
    assert project["tool"]["setuptools"]["include-package-data"] is False
    assert root_project["tool"]["uv"]["sources"]["fast-arm-core"] == {
        "workspace": True
    }
    assert "fast-arm-core" in root_project["project"]["dependencies"]
    package_find = root_project["tool"]["setuptools"]["packages"]["find"]
    assert root_project["tool"]["setuptools"]["include-package-data"] is False
    assert package_find["namespaces"] is False
    assert "selfrionette.plugins.robots.fast_arm.core*" in package_find["exclude"]
    assert not (CORE_PROJECT / "__init__.py").exists()
    assert (ROOT / "MANIFEST.in").read_text(encoding="utf-8").strip() == (
        "prune src/selfrionette/plugins/robots/fast_arm/core"
    )


def test_fast_arm_core_has_no_selfrionette_dependency() -> None:
    violations = {
        str(path.relative_to(ROOT)): sorted(
            name for name in _imports(path) if name == "selfrionette" or name.startswith("selfrionette.")
        )
        for path in CORE_SOURCE.rglob("*.py")
        if any(
            name == "selfrionette" or name.startswith("selfrionette.")
            for name in _imports(path)
        )
    }
    assert violations == {}


def test_plugin_entrypoint_only_assembles_the_adapter() -> None:
    imports = _imports(FAST_ARM_ROOT / "plugin.py")
    concrete_imports = {
        name
        for name in imports
        if name.startswith("selfrionette.plugins.robots.fast_arm")
    }
    assert concrete_imports
    assert all(
        name.startswith("selfrionette.plugins.robots.fast_arm.adapter")
        for name in concrete_imports
    )


def test_compatibility_modules_preserve_public_object_identity() -> None:
    assert compatibility_bundle.FAST_ARM_ROBOT_BUNDLE is adapter_bundle.FAST_ARM_ROBOT_BUNDLE
    assert (
        compatibility_kinematics.FastArmEndpointForwardKinematicsSolver
        is adapter_kinematics.FastArmEndpointForwardKinematicsSolver
    )
    assert (
        compatibility_kinematics.FastArmEndpointInverseKinematicsSolver
        is adapter_kinematics.FastArmEndpointInverseKinematicsSolver
    )


@pytest.mark.parametrize(
    "module_suffix",
    (
        "bundle",
        "endpoint",
        "feasibility",
        "initial_state",
        "kinematics",
        "model_contract",
        "profile",
        "runtime",
        "viewer",
        "diagnostics.endpoint_motion_sanity",
        "diagnostics.jacobian_mobility",
        "diagnostics.neutral_initial_pose",
    ),
)
def test_compatibility_modules_preserve_all_and_export_identities(
    module_suffix: str,
) -> None:
    compatibility = importlib.import_module(
        f"selfrionette.plugins.robots.fast_arm.{module_suffix}"
    )
    adapter = importlib.import_module(
        f"selfrionette.plugins.robots.fast_arm.adapter.{module_suffix}"
    )
    assert compatibility.__all__ == adapter.__all__
    for name in adapter.__all__:
        assert getattr(compatibility, name) is getattr(adapter, name)


def test_initial_state_contract_is_an_exact_core_projection() -> None:
    contract = FAST_ARM_INITIAL_STATE_CONTRACT
    assert contract.source_id == FAST_ARM_INITIAL_STATE.source_id
    assert contract.qpos_rad == FAST_ARM_INITIAL_STATE.qpos_rad
    assert contract.tip_position_m == FAST_ARM_INITIAL_STATE.tip_position_m
    assert (
        contract.tool_orientation_wxyz
        == FAST_ARM_INITIAL_STATE.tool_orientation_wxyz
    )
    assert contract.frame == FAST_ARM_INITIAL_STATE.frame
    assert contract.position_unit == FAST_ARM_INITIAL_STATE.tip_position_unit
    assert contract.quaternion_order == FAST_ARM_INITIAL_STATE.quaternion_order
    assert FAST_ARM_ROBOT_PROFILE.initial_keyframe_name == FAST_ARM_INITIAL_STATE.source_id


@pytest.mark.parametrize(
    "field,value",
    (
        ("resource_path", "../escape.xml"),
        ("resource_path", "/absolute.xml"),
        ("logical_identifier", "assets/../escape.xml"),
        ("bundle_path", "../arm.xml"),
    ),
)
def test_package_resource_rejects_traversal(field: str, value: str) -> None:
    arguments: dict[str, str] = {
        "package": "fast_arm_core",
        "resource_path": "resources/model/arm.xml",
        "logical_identifier": "assets/mujoco/fast_arm/arm.xml",
        "bundle_path": "arm.xml",
    }
    arguments[field] = value
    with pytest.raises(ValueError):
        PackageResource(**arguments)


def test_package_resource_fails_for_missing_package_and_resource() -> None:
    with pytest.raises(ValueError, match="missing package resource owner"):
        package_resource_traversable(
            PackageResource(
                "missing_fast_arm_package",
                "resource.xml",
                "assets/mujoco/fast_arm/resource.xml",
            )
        )
    with pytest.raises(ValueError, match="missing package resource"):
        package_resource_traversable(
            PackageResource(
                "fast_arm_core",
                "resources/model/missing.xml",
                "assets/mujoco/fast_arm/missing.xml",
            )
        )


def test_package_resource_rejects_resolved_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package_root = tmp_path / "fast_arm_resource_owner"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    outside = tmp_path / "outside.xml"
    outside.write_text("<mujoco/>", encoding="utf-8")
    link = package_root / "escaped.xml"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("fast_arm_resource_owner", None)
    importlib.import_module("fast_arm_resource_owner")
    with pytest.raises(ValueError, match="escapes its owning package"):
        package_resource_traversable(
            PackageResource(
                "fast_arm_resource_owner",
                "escaped.xml",
                "assets/mujoco/fast_arm/escaped.xml",
            )
        )


@pytest.mark.parametrize(
    "arguments,message",
    (
        (("", -1.0, 1.0), "joint name must not be empty"),
        (("joint", float("inf"), 1.0), "joint 'joint' limits must be finite"),
        (
            ("joint", 1.0, 1.0),
            "joint 'joint' lower_rad must be less than upper_rad",
        ),
    ),
)
def test_core_joint_limit_validation_preserves_failure_literals(
    arguments: tuple[str, float, float], message: str
) -> None:
    with pytest.raises(ValueError) as exc_info:
        FastArmJointLimit(*arguments)
    assert str(exc_info.value) == message
