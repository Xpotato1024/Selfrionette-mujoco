from __future__ import annotations

from selfrionette.mujoco_backend import (
    default_fast_arm_scene_path,
    load_mujoco_model,
    snapshot_mujoco_state,
)
from selfrionette.schemas import MuJoCoState


def test_snapshot_mujoco_state_builds_state_from_headless_model() -> None:
    bundle = load_mujoco_model(default_fast_arm_scene_path())
    state = snapshot_mujoco_state(
        bundle.model,
        bundle.data,
        frame_index=7,
    )

    assert isinstance(state, MuJoCoState)
    assert state.frame_index == 7
    assert isinstance(state.time_s, float)
    assert isinstance(state.qpos, tuple)
    assert state.qpos
    assert isinstance(state.qvel, tuple)
    assert isinstance(state.bodies, tuple)
    assert state.bodies
    assert isinstance(state.sites, tuple)
    assert state.sites
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)

    for body in state.bodies:
        assert len(body.position_m) == 3
        assert len(body.quaternion_wxyz) == 4

    for site in state.sites:
        assert len(site.position_m) == 3
        assert len(site.quaternion_wxyz) == 4


def test_snapshot_mujoco_state_preserves_metadata_and_target_position() -> None:
    bundle = load_mujoco_model(default_fast_arm_scene_path())
    metadata = {"source": "unit-test", "step": 4}
    target_position_m = (0.1, 0.2, 0.3)

    state = snapshot_mujoco_state(
        bundle.model,
        bundle.data,
        frame_index=11,
        target_position_m=target_position_m,
        metadata=metadata,
    )

    assert state.metadata == metadata
    assert state.target_position_m == target_position_m
