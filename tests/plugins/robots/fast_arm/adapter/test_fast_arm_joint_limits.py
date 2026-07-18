from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import selfrionette.plugins.robots.fast_arm.adapter.feasibility as joint_limits_module
from selfrionette.input_sources import ViewerInputSource
from selfrionette.mujoco_backend.model_info import MuJoCoModelInfo
from selfrionette.plugins.robots.fast_arm.adapter.feasibility import (
    FastArmJointLimitGuard,
    apply_fast_arm_qpos_feasibility_guard,
    load_and_validate_fast_arm_joint_limit_config,
    parse_fast_arm_joint_limit_config,
    validate_fast_arm_joint_limit_config,
)
from selfrionette.plugins.robots.fast_arm.adapter.resources import FAST_ARM_JOINT_LIMIT_RESOURCE
from selfrionette.plugins.robots.fast_arm.adapter.runtime import build_fast_arm_simulator
from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.composition.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.composition.robot_resource import read_package_resource_bytes
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.runtime.control.viewer_control_ingress import ingest_viewer_control_message
from selfrionette.runtime.execution.input_step_loop import (
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.schemas import (
    JointCommand,
    MotionCommand,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
)


DEFAULT_CONFIG_PATH = FAST_ARM_JOINT_LIMIT_RESOURCE
DEFAULT_CONFIG_TEXT = read_package_resource_bytes(DEFAULT_CONFIG_PATH).decode("utf-8")
HOME_QPOS = (0.0, -0.5235987755982989, 0.0, -1.0471975511965976)


def _write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "joint_limits.toml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def test_missing_config_file_is_a_startup_failure(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_concrete_mujoco_pipeline(
            config=RuntimeConfig(
                robot_profile_id="fast_arm",
                joint_limit_config_path=tmp_path / "missing.toml",
            ),
            publisher=_RecordingPublisher(),
        )


def test_home_qpos_is_checked_against_the_loaded_config(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        DEFAULT_CONFIG_TEXT.replace(
            "[joints.elbow_joint]\nlower_rad = -3.141592653589793\nupper_rad = 3.141592653589793",
            "[joints.elbow_joint]\nlower_rad = -0.5\nupper_rad = 0.5",
        ),
    )
    simulator = build_fast_arm_simulator()

    with pytest.raises(ValueError, match="home qpos"):
        load_and_validate_fast_arm_joint_limit_config(path, model=simulator.model)


def test_model_joint_order_is_checked_before_home_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    config = parse_fast_arm_joint_limit_config(DEFAULT_CONFIG_PATH)
    monkeypatch.setattr(
        joint_limits_module,
        "inspect_mujoco_model",
        lambda _model: MuJoCoModelInfo(
            joint_names=("elbow_joint", "sholder_joint_1", "sholder_joint_2", "sholder_joint_3"),
            body_names=(),
            site_names=(),
        ),
    )

    with pytest.raises(ValueError, match="joint order"):
        validate_fast_arm_joint_limit_config(config, object())


def _command(qpos_rad: tuple[float, ...]) -> MotionCommand:
    return MotionCommand(
        timestamp_s=1.0,
        joint=JointCommand(joint_angles_rad=qpos_rad),
        metadata={"desired_endpoint_m": (0.2, 0.0, 0.3)},
    )


def test_boundary_values_are_accepted_without_metadata_rewrite() -> None:
    config = parse_fast_arm_joint_limit_config(DEFAULT_CONFIG_PATH)
    command = _command((-3.141592653589793, 3.141592653589793, 0.0, -3.141592653589793))

    result = apply_fast_arm_qpos_feasibility_guard(
        command,
        current_qpos_rad=HOME_QPOS,
        joint_limits=config,
    )

    assert result.accepted is True
    assert result.action == "accept"
    assert result.motion_command is command
    assert result.violations == ()


def test_single_and_multiple_violations_hold_the_entire_current_qpos() -> None:
    config = parse_fast_arm_joint_limit_config(DEFAULT_CONFIG_PATH)
    command = _command((3.2, HOME_QPOS[1], HOME_QPOS[2], -3.2))

    result = apply_fast_arm_qpos_feasibility_guard(
        command,
        current_qpos_rad=HOME_QPOS,
        joint_limits=config,
    )

    assert result.accepted is False
    assert result.action == "hold_current_qpos"
    assert result.motion_command.joint is not None
    assert result.motion_command.joint.joint_angles_rad == HOME_QPOS
    assert result.motion_command.target is None
    assert [violation.joint_name for violation in result.violations] == [
        "sholder_joint_1",
        "elbow_joint",
    ]
    assert result.motion_command.metadata["qpos_feasibility_action"] == "hold_current_qpos"
    assert result.motion_command.metadata["qpos_rejection_reason"] == "joint_limit_violation"
    assert result.motion_command.metadata["qpos_candidate_rad"] == (3.2, HOME_QPOS[1], HOME_QPOS[2], -3.2)
    assert result.motion_command.metadata["qpos_limit_violations"][0]["joint_name"] == "sholder_joint_1"


def test_runtime_factory_accepts_a_replaced_config_and_validates_it_at_startup(tmp_path: Path) -> None:
    custom_path = _write_config(
        tmp_path,
        DEFAULT_CONFIG_TEXT.replace(
            "[joints.sholder_joint_1]\nlower_rad = -3.141592653589793\nupper_rad = 3.141592653589793",
            "[joints.sholder_joint_1]\nlower_rad = -0.25\nupper_rad = 0.25",
        ),
    )
    simulator = build_fast_arm_simulator()
    config = load_and_validate_fast_arm_joint_limit_config(custom_path, model=simulator.model)
    pipeline = build_concrete_mujoco_pipeline(
        config=RuntimeConfig(
            robot_profile_id="fast_arm",
            joint_limit_config_path=custom_path,
        ),
        publisher=_RecordingPublisher(),
    )

    assert config.limit_for("sholder_joint_1").upper_rad == pytest.approx(0.25)
    assert isinstance(pipeline.qpos_feasibility_guard, FastArmJointLimitGuard)
    assert pipeline.qpos_feasibility_guard.joint_limits.limit_for("sholder_joint_1").upper_rad == pytest.approx(0.25)


class _OutOfRangeMotionGenerator:
    def update(self, intent, dt_s):
        _ = dt_s
        return _command((4.0, HOME_QPOS[1], HOME_QPOS[2], HOME_QPOS[3]))


class _RecordingPublisher:
    def __init__(self) -> None:
        self.states = []

    async def publish(self, state) -> None:
        self.states.append(state)


def test_viewer_qpos_rejection_holds_target_lifecycle_and_rebase() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    publisher = _RecordingPublisher()
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("viewer", steps=1),
        publisher=publisher,
        viewer_input_source=source,
    )
    plan.pipeline.motion_generator = _OutOfRangeMotionGenerator()
    initial_tip = source.current_endpoint_m
    ingest_viewer_control_message(
        source,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=1.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("Space",),
                key_state={"Space": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )

    record = asyncio.run(run_runtime_input_source_step_loop(plan, steps=1))[0]

    assert record.state.qpos == pytest.approx(HOME_QPOS)
    assert record.motion_command.joint is not None
    assert record.motion_command.joint.joint_angles_rad == pytest.approx(HOME_QPOS)
    assert record.motion_command.metadata["qpos_feasibility_rejected"] is True
    assert record.motion_command.metadata["qpos_feasibility_action"] == "hold_current_qpos"
    assert record.state.target_position_m == pytest.approx(initial_tip)
    assert source.current_endpoint_m == pytest.approx(initial_tip)
    assert publisher.states[0].target_position_m == pytest.approx(initial_tip)


def test_direct_runtime_pipeline_step_uses_the_same_qpos_guard() -> None:
    publisher = _RecordingPublisher()
    pipeline = build_concrete_mujoco_pipeline(publisher=publisher)
    pipeline.motion_generator = _OutOfRangeMotionGenerator()

    state = asyncio.run(pipeline.run_once())

    assert state.qpos == pytest.approx(HOME_QPOS)
    assert state.metadata["qpos_feasibility_rejected"] is True
    assert state.metadata["qpos_feasibility_action"] == "hold_current_qpos"
    assert state.metadata["endpoint_evaluation"] is None
