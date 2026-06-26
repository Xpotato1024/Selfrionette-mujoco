from __future__ import annotations

from dataclasses import dataclass

import pytest

from selfrionette.kinematics import (
    FastArmEndpointForwardKinematicsSolver,
    FastArmEndpointInverseKinematicsSolver,
    PlanarChainForwardKinematicsSolver,
    PlanarTwoLinkInverseKinematicsSolver,
)
from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.schemas import InputIntent, JointCommand


@dataclass(slots=True)
class FutureTargetPositionCompatibleIntent:
    source: str
    timestamp_s: float
    target_delta_m: tuple[float, float, float] = (0.0, 0.0, 0.0)
    joint_delta_rad: tuple[float, ...] = ()
    metadata: dict[str, object] | None = None
    desired_endpoint_m: tuple[float, float, float] | None = None
    target_position_m: tuple[float, float, float] | None = None


def test_target_to_joint_motion_generator_uses_concrete_inverse_kinematics_solver() -> None:
    fk = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))
    target_joint_angles_rad = (0.3, -0.2)
    target_position_m = fk.forward(target_joint_angles_rad)
    intent = FutureTargetPositionCompatibleIntent(
        source="replay",
        timestamp_s=2.0,
        metadata={"origin": "concrete-ik"},
        target_position_m=target_position_m,
    )

    command = TargetToJointMotionGenerator(
        solver,
        seed_joint_angles_rad=(0.0, -0.2),
    ).update(intent, dt_s=0.016)

    assert command.timestamp_s == 2.0
    assert command.target is None
    assert command.metadata == {"origin": "concrete-ik"}
    assert command.joint is not None
    assert command.joint.joint_angles_rad == pytest.approx(target_joint_angles_rad, abs=1e-9)
    assert command.joint != JointCommand()
    assert command.joint.joint_angles_rad != ()


def test_target_to_joint_motion_generator_prefers_desired_endpoint_metadata_over_target_position_m() -> None:
    fk = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))
    target_joint_angles_rad = (0.3, -0.2)
    desired_endpoint_m = fk.forward(target_joint_angles_rad)
    fallback_target_position_m = (9.0, 8.0, 7.0)
    intent = FutureTargetPositionCompatibleIntent(
        source="replay",
        timestamp_s=2.0,
        metadata={"origin": "concrete-ik", "target_position_m": fallback_target_position_m},
        desired_endpoint_m=desired_endpoint_m,
        target_position_m=fallback_target_position_m,
    )

    command = TargetToJointMotionGenerator(
        solver,
        seed_joint_angles_rad=(0.0, -0.2),
    ).update(intent, dt_s=0.016)

    assert command.timestamp_s == 2.0
    assert command.target is None
    assert command.metadata == {"origin": "concrete-ik", "target_position_m": fallback_target_position_m}
    assert command.joint is not None
    assert command.joint.joint_angles_rad == pytest.approx(target_joint_angles_rad, abs=1e-9)


def test_target_to_joint_motion_generator_reports_target_position_m_for_invalid_fallback_metadata() -> None:
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))
    intent = FutureTargetPositionCompatibleIntent(
        source="replay",
        timestamp_s=2.0,
        metadata={"origin": "concrete-ik", "target_position_m": (0.1, 0.2)},
    )

    with pytest.raises(ValueError, match="target_position_m must contain exactly three values"):
        TargetToJointMotionGenerator(solver).update(intent, dt_s=0.016)


def test_target_to_joint_motion_generator_uses_metadata_target_position_and_pads_qpos_for_backend() -> None:
    fk = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))
    target_joint_angles_rad = (0.3, -0.2)
    target_position_m = fk.forward(target_joint_angles_rad)
    intent = InputIntent(
        source="replay",
        timestamp_s=2.0,
        metadata={"origin": "concrete-ik", "target_position_m": target_position_m},
    )

    command = TargetToJointMotionGenerator(
        solver,
        seed_joint_angles_rad=(0.0, -0.2),
        qpos_joint_count=4,
    ).update(intent, dt_s=0.016)

    assert command.timestamp_s == 2.0
    assert command.target is None
    assert command.metadata == {"origin": "concrete-ik", "target_position_m": target_position_m}
    assert command.joint is not None
    assert command.joint.joint_angles_rad[:2] == pytest.approx(target_joint_angles_rad, abs=1e-9)
    assert command.joint.joint_angles_rad[2:] == (0.0, 0.0)
    assert command.joint != JointCommand()
    assert len(command.joint.joint_angles_rad) == 4


def test_target_to_joint_motion_generator_keeps_four_dof_fast_arm_seed_and_does_not_pad_output() -> None:
    fk = FastArmEndpointForwardKinematicsSolver()
    solver = FastArmEndpointInverseKinematicsSolver()
    target_joint_angles_rad = (0.15, -0.25, 0.3, -0.05)
    desired_endpoint_m = fk.forward(target_joint_angles_rad)
    intent = InputIntent(
        source="replay",
        timestamp_s=2.0,
        metadata={"origin": "fast-arm", "desired_endpoint_m": desired_endpoint_m},
    )

    command = TargetToJointMotionGenerator(
        solver,
        current_qpos_rad=(0.0, 0.0, 0.0, 0.0),
        qpos_joint_count=4,
    ).update(intent, dt_s=0.016)

    assert command.timestamp_s == 2.0
    assert command.target is None
    assert command.metadata == {"origin": "fast-arm", "desired_endpoint_m": desired_endpoint_m}
    assert command.joint is not None
    assert len(command.joint.joint_angles_rad) == 4
    assert command.joint.joint_angles_rad[2:] != (0.0, 0.0)
    assert fk.forward(command.joint.joint_angles_rad) == pytest.approx(desired_endpoint_m, abs=1e-4)


def test_target_to_joint_motion_generator_rejects_non_converged_fast_arm_targets() -> None:
    class _NonConvergingSolver:
        def solve(self, target_position_m, seed_joint_angles_rad=None):  # noqa: ANN001
            _ = target_position_m
            _ = seed_joint_angles_rad
            raise ValueError("target_position_m did not converge")

    intent = InputIntent(
        source="replay",
        timestamp_s=3.0,
        metadata={"origin": "fast-arm", "desired_endpoint_m": (0.58, 0.02, 0.11)},
    )

    command = TargetToJointMotionGenerator(
        _NonConvergingSolver(),
        current_qpos_rad=(0.1, -0.1, 0.2, -0.2),
        qpos_joint_count=4,
    ).update(intent, dt_s=0.016)

    assert command.target is None
    assert command.joint is not None
    assert command.joint.joint_angles_rad == (0.1, -0.1, 0.2, -0.2)
    assert command.metadata["target_rejected"] is True
    assert command.metadata["target_rejection_reason"] == "invalid_target"
    assert command.metadata["target_rejection_message"] == "target_position_m did not converge"
    assert command.metadata["runtime_input_safety_applied"] is True
