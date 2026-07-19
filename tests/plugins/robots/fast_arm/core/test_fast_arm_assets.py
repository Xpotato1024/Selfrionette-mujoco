from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
CORE_MODEL = files("fast_arm_core").joinpath("resources/model")
REQUIRED_MESHES = [
    "BaseLink.stl",
    "SholderLink1.stl",
    "SholderLink2.stl",
    "UpperArmLink.stl",
    "ForeArmLink.stl",
]


def test_fast_arm_assets_exist() -> None:
    assert CORE_MODEL.joinpath("arm.xml").read_bytes()
    assert {
        resource.name for resource in CORE_MODEL.joinpath("meshes").iterdir()
    } == set(REQUIRED_MESHES)
    assert all(CORE_MODEL.joinpath("meshes", name).read_bytes() for name in REQUIRED_MESHES)


def test_fast_arm_xml_contract() -> None:
    arm_xml = CORE_MODEL.joinpath("arm.xml").read_text(encoding="utf-8")

    assert 'meshdir="meshes"' in arm_xml
    assert 'site name="tip"' in arm_xml


def test_old_fast_arm_resource_directories_contain_no_production_duplicate() -> None:
    assert not tuple((ROOT / "assets/mujoco/fast_arm").rglob("*.xml"))
    assert not tuple((ROOT / "assets/mujoco/fast_arm").rglob("*.stl"))
    assert not tuple((ROOT / "assets/mujoco/fast_arm").rglob("*.json"))
    assert not tuple((ROOT / "configs/fast_arm").rglob("*.toml"))
