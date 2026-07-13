from __future__ import annotations

from dataclasses import dataclass

import pytest

import selfrionette.runtime.fast_arm_plugin as fast_arm_plugin_module
from selfrionette.mujoco_backend.model_info import MuJoCoModelInfo
from selfrionette.robot_profile import RobotProfile, robot_profile_runtime_metadata
from selfrionette.robot_registry import (
    ImmutableRegistry,
    registered_robot_profile_ids,
    resolve_robot_profile,
)
from selfrionette.robots.fast_arm import FAST_ARM_ROBOT_PROFILE
from selfrionette.runtime import RuntimeConfig, build_concrete_mujoco_pipeline
from selfrionette.runtime.fast_arm_plugin import FAST_ARM_RUNTIME_PLUGIN
from selfrionette.runtime.robot_plugin_registry import (
    registered_robot_runtime_plugin_ids,
    resolve_robot_runtime_plugin,
)
from selfrionette.transport import mujoco_state_to_payload


@dataclass(frozen=True)
class _Entry:
    profile_id: str


class _Publisher:
    async def publish(self, state) -> None:  # noqa: ANN001
        _ = state


def test_fast_arm_profile_and_plugin_resolve_explicitly() -> None:
    profile = resolve_robot_profile("fast_arm")
    plugin = resolve_robot_runtime_plugin("fast_arm")

    assert profile is FAST_ARM_ROBOT_PROFILE
    assert plugin is FAST_ARM_RUNTIME_PLUGIN
    assert plugin.profile is profile
    assert registered_robot_profile_ids() == ("fast_arm",)
    assert registered_robot_runtime_plugin_ids() == ("fast_arm",)


def test_unknown_profile_and_plugin_ids_fail_explicitly() -> None:
    with pytest.raises(ValueError, match="unknown robot profile ID"):
        resolve_robot_profile("unknown")
    with pytest.raises(ValueError, match="unknown robot runtime plugin ID"):
        resolve_robot_runtime_plugin("unknown")


def test_duplicate_registration_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate test registration"):
        ImmutableRegistry((_Entry("same"), _Entry("same")), kind="test")


def test_production_composition_requires_profile_when_config_is_supplied() -> None:
    with pytest.raises(ValueError, match="requires robot_profile_id"):
        build_concrete_mujoco_pipeline(config=RuntimeConfig(), publisher=_Publisher())


def test_production_composition_rejects_unknown_profile_at_startup() -> None:
    with pytest.raises(ValueError, match="unknown robot runtime plugin ID"):
        build_concrete_mujoco_pipeline(
            config=RuntimeConfig(robot_profile_id="unknown"),
            publisher=_Publisher(),
        )


@pytest.mark.parametrize(
    ("nq", "nv", "joint_names", "message"),
    [
        (3, 4, FAST_ARM_ROBOT_PROFILE.canonical_joint_names, "qpos dimension mismatch"),
        (4, 3, FAST_ARM_ROBOT_PROFILE.canonical_joint_names, "qvel dimension mismatch"),
        (4, 4, tuple(reversed(FAST_ARM_ROBOT_PROFILE.canonical_joint_names)), "joint order mismatch"),
    ],
)
def test_profile_model_dimension_and_joint_order_mismatch_fail_at_startup(
    monkeypatch: pytest.MonkeyPatch,
    nq: int,
    nv: int,
    joint_names: tuple[str, ...],
    message: str,
) -> None:
    model = type("Model", (), {"nq": nq, "nv": nv})()
    monkeypatch.setattr(
        fast_arm_plugin_module,
        "inspect_mujoco_model",
        lambda _model: MuJoCoModelInfo(joint_names=joint_names, body_names=(), site_names=()),
    )

    with pytest.raises(ValueError, match=message):
        FAST_ARM_RUNTIME_PLUGIN.validate_model(model)


def test_profile_identity_uses_payload_v0_metadata_without_shape_break() -> None:
    pipeline = build_concrete_mujoco_pipeline(publisher=_Publisher())
    state = pipeline.simulator.snapshot()
    state = type(state)(
        frame_index=state.frame_index,
        time_s=state.time_s,
        qpos=state.qpos,
        qvel=state.qvel,
        bodies=state.bodies,
        sites=state.sites,
        target_position_m=state.target_position_m,
        metadata=robot_profile_runtime_metadata(FAST_ARM_ROBOT_PROFILE),
    )

    payload = mujoco_state_to_payload(state)

    assert payload["version"] == 0
    assert payload["metadata"]["robot_profile_id"] == "fast_arm"
    assert payload["metadata"]["model_contract_version"] == FAST_ARM_ROBOT_PROFILE.model_contract_version
    assert payload["metadata"]["robot_joint_names"] == FAST_ARM_ROBOT_PROFILE.canonical_joint_names
    assert set(payload) == {
        "version",
        "frame_index",
        "time_s",
        "qpos",
        "qvel",
        "bodies",
        "sites",
        "target_position_m",
        "metadata",
    }


def test_profile_declaration_contains_no_executable_factory_fields() -> None:
    field_names = set(RobotProfile.__dataclass_fields__)
    assert not any("module" in name or "class" in name or "factory" in name for name in field_names)
