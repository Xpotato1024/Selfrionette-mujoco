from __future__ import annotations

from typing import Protocol

from selfrionette.schemas import JointCommand, Vector3


class ForwardKinematicsSolver(Protocol):
    def forward(self, joint_angles_rad: tuple[float, ...]) -> Vector3:
        ...


class InverseKinematicsSolver(Protocol):
    def solve(
        self,
        target_position_m: Vector3,
        seed_joint_angles_rad: tuple[float, ...] | None = None,
    ) -> JointCommand:
        ...
