from __future__ import annotations

from pathlib import Path

import pytest

from selfrionette.mujoco_backend import default_fast_arm_scene_path, load_mujoco_model
from selfrionette.mujoco_backend.model_loader import FAST_ARM_INITIAL_KEYFRAME_NAME


def test_default_fast_arm_scene_path_points_to_scene_xml() -> None:
    path = default_fast_arm_scene_path()

    assert path.name == "scene.xml"
    assert path.is_file()


def test_load_mujoco_model_loads_default_scene() -> None:
    bundle = load_mujoco_model(default_fast_arm_scene_path())

    assert bundle.model_path == default_fast_arm_scene_path().resolve()
    assert bundle.model is not None
    assert bundle.data is not None
    assert tuple(bundle.data.qpos) == pytest.approx(
        tuple(bundle.model.key(FAST_ARM_INITIAL_KEYFRAME_NAME).qpos)
    )


def test_load_mujoco_model_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_scene.xml"

    with pytest.raises(FileNotFoundError):
        load_mujoco_model(missing_path)
