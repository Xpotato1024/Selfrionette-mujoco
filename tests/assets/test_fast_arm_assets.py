from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FAST_ARM_DIR = ROOT / "assets" / "mujoco" / "fast_arm"
MESHES_DIR = FAST_ARM_DIR / "meshes"
REQUIRED_MESHES = [
    "BaseLink.stl",
    "SholderLink1.stl",
    "SholderLink2.stl",
    "UpperArmLink.stl",
    "ForeArmLink.stl",
]


def test_fast_arm_assets_exist() -> None:
    assert FAST_ARM_DIR.is_dir()
    assert (FAST_ARM_DIR / "arm.xml").is_file()
    assert (FAST_ARM_DIR / "scene.xml").is_file()
    assert MESHES_DIR.is_dir()

    for mesh_name in REQUIRED_MESHES:
        assert (MESHES_DIR / mesh_name).is_file()


def test_fast_arm_xml_contract() -> None:
    arm_xml = (FAST_ARM_DIR / "arm.xml").read_text(encoding="utf-8")
    scene_xml = (FAST_ARM_DIR / "scene.xml").read_text(encoding="utf-8")

    assert 'meshdir="meshes"' in arm_xml
    assert '<include file="arm.xml"/>' in scene_xml
    assert 'site name="tip"' in arm_xml
