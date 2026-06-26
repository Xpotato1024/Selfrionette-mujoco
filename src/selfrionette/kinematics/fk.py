from __future__ import annotations

import math
from dataclasses import dataclass

from selfrionette.kinematics.fast_arm_endpoint import FastArmEndpointForwardKinematicsSolver
from selfrionette.schemas import Vector3


@dataclass(frozen=True, slots=True)
class PlanarChainForwardKinematicsSolver:
    """Minimal concrete FK baseline on an x-z planar chain.

    This is intentionally small and deterministic. It is not a robotics-grade
    FK stack, but it provides a concrete runtime/test baseline that is distinct
    from the zero-valued stub.
    """

    link_lengths_m: tuple[float, ...]
    base_position_m: Vector3 = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if not self.link_lengths_m:
            raise ValueError("link_lengths_m must contain at least one link")
        if len(self.base_position_m) != 3:
            raise ValueError("base_position_m must contain exactly three values")
        if any(link_length < 0.0 for link_length in self.link_lengths_m):
            raise ValueError("link_lengths_m must be non-negative")

    def forward(self, joint_angles_rad: tuple[float, ...]) -> Vector3:
        if len(joint_angles_rad) != len(self.link_lengths_m):
            raise ValueError(
                "joint angle count does not match link length contract: "
                f"expected {len(self.link_lengths_m)}, got {len(joint_angles_rad)}"
            )

        x, y, z = (float(value) for value in self.base_position_m)
        cumulative_angle_rad = 0.0

        for link_length_m, joint_angle_rad in zip(
            self.link_lengths_m,
            joint_angles_rad,
            strict=True,
        ):
            cumulative_angle_rad += float(joint_angle_rad)
            x += float(link_length_m) * math.cos(cumulative_angle_rad)
            z += float(link_length_m) * math.sin(cumulative_angle_rad)

        return (x, y, z)


__all__ = [
    "FastArmEndpointForwardKinematicsSolver",
    "PlanarChainForwardKinematicsSolver",
]
