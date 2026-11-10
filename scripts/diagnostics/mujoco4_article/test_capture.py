"""固定モデルと比較条件、実シミュレーションの回帰検査。"""
import importlib.util
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("article_capture", Path(__file__).with_name("capture.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
pytestmark = pytest.mark.skipif(mujoco.__version__ != "4.0.0", reason="isolated MuJoCo 4.0.0 diagnostic")

@pytest.mark.parametrize("scene", module.SCENES)
def test_fixed_source_and_comparison_conditions(scene):
    xml, changes = module.model_xml(scene)
    tree = ET.fromstring(xml)
    elastic, plastic = tree.findall(".//elasticity")
    assert {k:v for k,v in elastic.attrib.items() if k != "yield"} == {k:v for k,v in plastic.attrib.items() if k != "yield"}
    assert "yield" not in elastic.attrib
    assert all(float(v) > 0 for v in plastic.attrib["yield"].split())
    assert tree.find("option").get("solver") == "CG"
    assert changes["both_elasticity_damping"] == elastic.get("damping")

@pytest.mark.parametrize("scene", module.SCENES)
def test_real_simulation_is_finite_and_plastic_shape_remains(scene):
    model = mujoco.MjModel.from_xml_string(module.model_xml(scene)[0])
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    initial = data.flexvert_xpos.copy()
    module.advance(model, data, 4.8)
    result = module.measure(model, data, initial)
    assert result["time_s"] == pytest.approx(4.8)
    assert result["warnings"] == [0] * len(data.warning.number)
    assert result["flex_rms_displacement_m"][1] > .01
    assert result["flex_rms_displacement_m"][0] < .002
    if scene == "torsion":
        assert abs(result["cap_twist_deg"][0]) < 1
        assert 60 < result["cap_twist_deg"][1] < 100


def test_wrong_version_is_rejected(monkeypatch):
    monkeypatch.setattr(mujoco, "__version__", "3.9.0")
    with pytest.raises(RuntimeError, match="isolated"):
        module.require_version()


def test_unknown_scene_is_rejected():
    with pytest.raises(ValueError):
        module.model_xml("../../arbitrary")


def test_non_finite_state_is_rejected():
    model = mujoco.MjModel.from_xml_string(module.model_xml("torsion")[0])
    data = mujoco.MjData(model)
    data.qpos[0] = math.nan
    with pytest.raises(RuntimeError, match="non-finite"):
        module.check_state(data)


def test_frames_are_fixed_step_and_real_time_mapping():
    model = mujoco.MjModel.from_xml_string(module.model_xml("torsion")[0])
    assert module.RATE / module.FPS / model.opt.timestep == pytest.approx(5)
    assert module.SECONDS * module.FPS == 120


def test_existing_output_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(module.shutil, "which", lambda value: "ffmpeg")
    monkeypatch.setattr(module.sys, "argv", ["capture", "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2

def test_speculative_contact_single_step():
    spec = importlib.util.spec_from_file_location("article_contact", Path(__file__).with_name("contact.py"))
    contact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contact)
    _, off = contact.trial(False)
    _, on = contact.trial(True)
    assert off[1]["sphere_center_x_m"] == pytest.approx(.12)
    assert on[1]["sphere_center_x_m"] < -.015
    assert on[0]["contact_count"] > 0