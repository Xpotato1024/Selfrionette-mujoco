from __future__ import annotations

import pytest

from selfrionette.kinematics import (
    ForwardKinematicsSolver,
    PlanarChainForwardKinematicsSolver,
)
from selfrionette.kinematics.stubs import ZeroForwardKinematicsSolver


def test_planar_chain_forward_kinematics_solver_matches_protocol_and_returns_vector3() -> None:
    solver = PlanarChainForwardKinematicsSolver(
        link_lengths_m=(0.5, 0.25, 0.125),
        base_position_m=(0.1, 0.2, 0.3),
    )

    assert isinstance(solver, ForwardKinematicsSolver)

    same_input_result = solver.forward((0.0, 0.0, 0.0))
    assert isinstance(same_input_result, tuple)
    assert len(same_input_result) == 3
    assert same_input_result == (0.975, 0.2, 0.3)


def test_planar_chain_forward_kinematics_solver_is_deterministic_and_angle_sensitive() -> None:
    solver = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))

    first = solver.forward((0.0, 0.0))
    second = solver.forward((0.3, -0.2))
    third = solver.forward((0.3, -0.2))

    assert first != second
    assert second == third
    assert first != (0.0, 0.0, 0.0)


def test_planar_chain_forward_kinematics_solver_rejects_invalid_joint_count() -> None:
    solver = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25, 0.125))

    with pytest.raises(ValueError, match="joint angle count does not match link length contract"):
        solver.forward((0.0, 0.0))


def test_planar_chain_forward_kinematics_solver_differs_from_zero_stub() -> None:
    solver = PlanarChainForwardKinematicsSolver(link_lengths_m=(0.5, 0.25))
    zero_solver = ZeroForwardKinematicsSolver()

    assert solver.forward((0.0, 0.0)) != zero_solver.forward((0.0, 0.0))
