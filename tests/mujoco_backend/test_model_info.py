from __future__ import annotations

from selfrionette.mujoco_backend import (
    default_fast_arm_scene_path,
    inspect_mujoco_model,
    load_mujoco_model,
)


def test_inspect_mujoco_model_returns_joint_body_and_site_names() -> None:
    bundle = load_mujoco_model(default_fast_arm_scene_path())
    info = inspect_mujoco_model(bundle.model)

    assert info.joint_names
    assert info.body_names
    assert info.site_names
    assert "tip" in info.site_names
    assert "sholder_joint_1" in info.joint_names
    assert "base_link" in info.body_names
