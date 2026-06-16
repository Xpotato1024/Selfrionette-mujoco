from __future__ import annotations

from selfrionette.kinematics.base import ForwardKinematicsSolver, InverseKinematicsSolver
from selfrionette.schemas import JointCommand, Vector3


class ZeroForwardKinematicsSolver:
    """Zero-valued FK stub, not a real forward kinematics implementation."""

    def forward(self, joint_angles_rad: tuple[float, ...]) -> Vector3:
        return (0.0, 0.0, 0.0)


class ZeroInverseKinematicsSolver:
    """Empty IK stub, not a real inverse kinematics implementation."""

    def solve(
        self,
        target_position_m: Vector3,
        seed_joint_angles_rad: tuple[float, ...] | None = None,
    ) -> JointCommand:
        return JointCommand()


# Keep the contract imports available for explicit, module-local imports.
__all__ = [
    "ZeroForwardKinematicsSolver",
    "ZeroInverseKinematicsSolver",
]
