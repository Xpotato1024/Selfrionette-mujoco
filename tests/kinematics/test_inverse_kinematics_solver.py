from __future__ import annotations

import pytest

from selfrionette.kinematics import (
    InverseKinematicsSolver,
    PlanarChainForwardKinematicsSolver,
    PlanarTwoLinkInverseKinematicsSolver,
)
from selfrionette.kinematics.stubs import ZeroInverseKinematicsSolver
from selfrionette.schemas import JointCommand


def test_planar_two_link_inverse_kinematics_solver_matches_protocol_and_returns_joint_command() -> None:
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))

    assert isinstance(solver, InverseKinematicsSolver)

    command = solver.solve((0.6, 0.0, 0.1))

    assert isinstance(command, JointCommand)
    assert command.joint_angles_rad != ()


def test_planar_two_link_inverse_kinematics_solver_is_deterministic_and_target_sensitive() -> None:
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))
    fk = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))

    target_a = fk.forward((0.3, -0.2))
    target_b = fk.forward((0.1, 0.4))

    first = solver.solve(target_a, seed_joint_angles_rad=(0.0, -0.2))
    second = solver.solve(target_a, seed_joint_angles_rad=(0.0, -0.2))
    third = solver.solve(target_b, seed_joint_angles_rad=(0.0, 0.4))

    assert first == second
    assert first != third
    assert first.joint_angles_rad != ()


def test_planar_two_link_inverse_kinematics_solver_round_trips_with_fk_baseline() -> None:
    fk = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))

    desired_joint_angles_rad = (0.3, -0.2)
    target_position_m = fk.forward(desired_joint_angles_rad)

    command = solver.solve(target_position_m, seed_joint_angles_rad=(0.0, -0.2))

    assert command.joint_angles_rad == pytest.approx(desired_joint_angles_rad, abs=1e-9)
    assert fk.forward(command.joint_angles_rad) == pytest.approx(target_position_m, abs=1e-9)


def test_planar_two_link_inverse_kinematics_solver_rejects_invalid_inputs_and_unreachable_targets() -> None:
    solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))

    with pytest.raises(ValueError, match="target_position_m"):
        solver.solve((0.1, 0.2), seed_joint_angles_rad=None)

    with pytest.raises(ValueError, match="plane"):
        solver.solve((0.6, 0.1, 0.1), seed_joint_angles_rad=None)

    with pytest.raises(ValueError, match="workspace"):
        solver.solve((10.0, 0.0, 0.0), seed_joint_angles_rad=None)

    with pytest.raises(ValueError, match="seed_joint_angles_rad"):
        solver.solve((0.6, 0.0, 0.1), seed_joint_angles_rad=(0.0,))

    with pytest.raises(ValueError, match="exactly two links"):
        PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=())

    with pytest.raises(ValueError, match="unsupported joint count"):
        PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25, 0.1))

    with pytest.raises(ValueError, match="non-negative"):
        PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(-0.5, 0.25))


def test_concrete_inverse_kinematics_solver_differs_from_zero_stub() -> None:
    zero_solver = ZeroInverseKinematicsSolver()
    concrete_solver = PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=(0.5, 0.25))

    zero_command = zero_solver.solve((0.1, 0.0, 0.1))
    concrete_command = concrete_solver.solve((0.6, 0.0, 0.1))

    assert zero_command == JointCommand()
    assert concrete_command != JointCommand()
