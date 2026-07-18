"""Typed binding from stable fast_arm logical IDs to package-owned resources."""

from __future__ import annotations

from selfrionette.runtime.composition.robot_resource import (
    PackageResource,
    PackageResourceBundle,
    read_package_resource_bytes,
)


ADAPTER_PACKAGE = "selfrionette.plugins.robots.fast_arm.adapter"
CORE_PACKAGE = "fast_arm_core"

FAST_ARM_SCENE_RESOURCE = PackageResource(
    ADAPTER_PACKAGE,
    "resources/mujoco/scene.xml",
    "assets/mujoco/fast_arm/scene.xml",
    "scene.xml",
)
FAST_ARM_VIEWER_DECLARATION_RESOURCE = PackageResource(
    ADAPTER_PACKAGE,
    "resources/viewer-profile.json",
    "assets/mujoco/fast_arm/viewer-profile.json",
)
FAST_ARM_VIEWER_FIXTURE_RESOURCE = PackageResource(
    ADAPTER_PACKAGE,
    "resources/fixtures/fast_arm_sweep_x_qpos.json",
    "assets/mujoco/fast_arm/fixtures/fast_arm_sweep_x_qpos.json",
)
FAST_ARM_JOINT_LIMIT_RESOURCE = PackageResource(
    CORE_PACKAGE,
    "resources/config/joint_limits.toml",
    "configs/fast_arm/joint_limits.toml",
)
FAST_ARM_ARM_XML_RESOURCE = PackageResource(
    CORE_PACKAGE,
    "resources/model/arm.xml",
    "assets/mujoco/fast_arm/arm.xml",
    "arm.xml",
)

_MESH_NAMES = (
    "BaseLink.stl",
    "SholderLink1.stl",
    "SholderLink2.stl",
    "UpperArmLink.stl",
    "ForeArmLink.stl",
)
FAST_ARM_MESH_RESOURCES = tuple(
    PackageResource(
        CORE_PACKAGE,
        f"resources/model/meshes/{name}",
        f"assets/mujoco/fast_arm/meshes/{name}",
        f"meshes/{name}",
    )
    for name in _MESH_NAMES
)
FAST_ARM_MODEL_VFS_RESOURCES = (FAST_ARM_ARM_XML_RESOURCE, *FAST_ARM_MESH_RESOURCES)
FAST_ARM_MODEL_BUNDLE = PackageResourceBundle(
    entrypoint=FAST_ARM_SCENE_RESOURCE,
    resources=FAST_ARM_MODEL_VFS_RESOURCES,
)


def fast_arm_model_resource_bytes() -> tuple[bytes, dict[str, bytes]]:
    return FAST_ARM_MODEL_BUNDLE.model_xml_and_assets()


__all__ = [
    "FAST_ARM_ARM_XML_RESOURCE",
    "FAST_ARM_JOINT_LIMIT_RESOURCE",
    "FAST_ARM_MESH_RESOURCES",
    "FAST_ARM_MODEL_BUNDLE",
    "FAST_ARM_MODEL_VFS_RESOURCES",
    "FAST_ARM_SCENE_RESOURCE",
    "FAST_ARM_VIEWER_DECLARATION_RESOURCE",
    "FAST_ARM_VIEWER_FIXTURE_RESOURCE",
    "fast_arm_model_resource_bytes",
]
