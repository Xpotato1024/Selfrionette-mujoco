from __future__ import annotations

import math
from dataclasses import dataclass

from selfrionette.schemas import JointCommand, Vector3


def _validate_vector3(name: str, value: Vector3) -> tuple[float, float, float]:
    if len(value) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return tuple(float(component) for component in value)


@dataclass(frozen=True, slots=True)
class PlanarTwoLinkInverseKinematicsSolver:
    """Minimal concrete IK baseline on an x-z planar two-link chain.

    This is intentionally small and deterministic. It exists to replace the
    empty IK stub with a concrete target-to-joint path for runtime and tests,
    not as a final robotics-grade IK stack.
    """

    link_lengths_m: tuple[float, float]
    base_position_m: Vector3 = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if len(self.link_lengths_m) == 0:
            raise ValueError("link_lengths_m must contain exactly two links")
        if len(self.link_lengths_m) != 2:
            raise ValueError("unsupported joint count: this solver only supports two links")
        if any(link_length < 0.0 for link_length in self.link_lengths_m):
            raise ValueError("link_lengths_m must be non-negative")
        if len(self.base_position_m) != 3:
            raise ValueError("base_position_m must contain exactly three values")

    def solve(
        self,
        target_position_m: Vector3,
        seed_joint_angles_rad: tuple[float, ...] | None = None,
    ) -> JointCommand:
        target_x_m, target_y_m, target_z_m = _validate_vector3("target_position_m", target_position_m)
        base_x_m, base_y_m, base_z_m = _validate_vector3("base_position_m", self.base_position_m)

        if not math.isclose(target_y_m, base_y_m, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("target_position_m must remain on the solver plane")

        if seed_joint_angles_rad is not None and len(seed_joint_angles_rad) != 2:
            raise ValueError("seed_joint_angles_rad must contain exactly two values for this solver")

        link_1_m, link_2_m = (float(value) for value in self.link_lengths_m)
        local_x_m = target_x_m - base_x_m
        local_z_m = target_z_m - base_z_m
        distance_m = math.hypot(local_x_m, local_z_m)
        min_reach_m = abs(link_1_m - link_2_m)
        max_reach_m = link_1_m + link_2_m

        if distance_m < min_reach_m - 1e-9 or distance_m > max_reach_m + 1e-9:
            raise ValueError("target_position_m is outside the reachable workspace")

        if link_1_m == 0.0 and link_2_m == 0.0:
            if distance_m > 1e-9:
                raise ValueError("target_position_m is outside the reachable workspace")
            return JointCommand(joint_angles_rad=(0.0, 0.0))

        if link_2_m == 0.0:
            if not math.isclose(distance_m, link_1_m, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("target_position_m is outside the reachable workspace")
            return JointCommand(joint_angles_rad=(math.atan2(local_z_m, local_x_m), 0.0))

        if link_1_m == 0.0:
            if not math.isclose(distance_m, link_2_m, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("target_position_m is outside the reachable workspace")
            return JointCommand(joint_angles_rad=(0.0, math.atan2(local_z_m, local_x_m)))

        cos_elbow_rad = (distance_m**2 - link_1_m**2 - link_2_m**2) / (2.0 * link_1_m * link_2_m)
        if cos_elbow_rad < -1.0 - 1e-9 or cos_elbow_rad > 1.0 + 1e-9:
            raise ValueError("target_position_m is outside the reachable workspace")
        cos_elbow_rad = max(-1.0, min(1.0, cos_elbow_rad))

        seed_elbow_angle_rad = None
        if seed_joint_angles_rad is not None:
            seed_elbow_angle_rad = float(seed_joint_angles_rad[1])

        elbow_angle_candidates_rad = (math.acos(cos_elbow_rad), -math.acos(cos_elbow_rad))
        if seed_elbow_angle_rad is None:
            elbow_angle_rad = elbow_angle_candidates_rad[0]
        else:
            elbow_angle_rad = min(
                elbow_angle_candidates_rad,
                key=lambda candidate: abs(candidate - seed_elbow_angle_rad),
            )

        k1_m = link_1_m + link_2_m * math.cos(elbow_angle_rad)
        k2_m = link_2_m * math.sin(elbow_angle_rad)
        shoulder_angle_rad = math.atan2(local_z_m, local_x_m) - math.atan2(k2_m, k1_m)

        return JointCommand(joint_angles_rad=(shoulder_angle_rad, elbow_angle_rad))


__all__ = ["PlanarTwoLinkInverseKinematicsSolver"]
