from selfrionette.plugins.robots.fast_arm.adapter.resources import (
    FAST_ARM_ARM_XML_RESOURCE,
    FAST_ARM_MESH_RESOURCES,
    FAST_ARM_SCENE_RESOURCE,
)
from selfrionette.runtime.composition.robot_resource import read_package_resource_bytes

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_MESHES = [
    "BaseLink.stl",
    "SholderLink1.stl",
    "SholderLink2.stl",
    "UpperArmLink.stl",
    "ForeArmLink.stl",
]


def test_fast_arm_assets_exist() -> None:
    assert read_package_resource_bytes(FAST_ARM_ARM_XML_RESOURCE)
    assert read_package_resource_bytes(FAST_ARM_SCENE_RESOURCE)
    assert tuple(resource.bundle_path for resource in FAST_ARM_MESH_RESOURCES) == tuple(
        f"meshes/{name}" for name in REQUIRED_MESHES
    )
    assert all(read_package_resource_bytes(resource) for resource in FAST_ARM_MESH_RESOURCES)


def test_fast_arm_xml_contract() -> None:
    arm_xml = read_package_resource_bytes(FAST_ARM_ARM_XML_RESOURCE).decode("utf-8")
    scene_xml = read_package_resource_bytes(FAST_ARM_SCENE_RESOURCE).decode("utf-8")

    assert 'meshdir="meshes"' in arm_xml
    assert '<include file="arm.xml"/>' in scene_xml
    assert 'site name="tip"' in arm_xml


def test_old_fast_arm_resource_directories_contain_no_production_duplicate() -> None:
    assert not tuple((ROOT / "assets/mujoco/fast_arm").rglob("*.xml"))
    assert not tuple((ROOT / "assets/mujoco/fast_arm").rglob("*.stl"))
    assert not tuple((ROOT / "assets/mujoco/fast_arm").rglob("*.json"))
    assert not tuple((ROOT / "configs/fast_arm").rglob("*.toml"))
