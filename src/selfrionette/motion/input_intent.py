from __future__ import annotations

from selfrionette.kinematics import InverseKinematicsSolver
from selfrionette.schemas import InputIntent, JointCommand, MotionCommand, TargetCommand


def _has_non_zero_delta(delta_m: tuple[float, float, float]) -> bool:
    return any(component != 0.0 for component in delta_m)


class InputIntentMotionGenerator:
    """Minimal motion skeleton that turns replay intent into MotionCommand."""

    def update(self, intent: InputIntent, dt_s: float) -> MotionCommand:
        _ = dt_s  # Protocol compatibility; this skeleton does not use delta time yet.

        if intent.joint_delta_rad:
            raise ValueError("joint_delta_rad is not supported in Step 5-F")

        target = TargetCommand(delta_m=intent.target_delta_m) if _has_non_zero_delta(intent.target_delta_m) else None

        return MotionCommand(
            timestamp_s=intent.timestamp_s,
            target=target,
            joint=None,
            metadata=dict(intent.metadata),
        )


class TargetToJointMotionGenerator:
    """Skeleton that optionally resolves target positions through IK.

    The optional target_position_m attribute is a temporary compatibility hook
    for future target-position carriers. It is not a formal schema field yet.
    """

    def __init__(
        self,
        ik_solver: InverseKinematicsSolver,
        *,
        seed_joint_angles_rad: tuple[float, ...] | None = None,
    ) -> None:
        self._ik_solver = ik_solver
        self._seed_joint_angles_rad = seed_joint_angles_rad

    def update(self, intent: InputIntent, dt_s: float) -> MotionCommand:
        _ = dt_s  # Protocol compatibility; this skeleton does not use delta time yet.

        if intent.joint_delta_rad:
            raise ValueError("joint_delta_rad is not supported in Step 5-F")

        target = TargetCommand(delta_m=intent.target_delta_m) if _has_non_zero_delta(intent.target_delta_m) else None
        joint: JointCommand | None = None

        # Temporary hook for future target-position compatible objects only.
        target_position_m = getattr(intent, "target_position_m", None)
        if target_position_m is not None:
            joint = self._ik_solver.solve(
                target_position_m,
                seed_joint_angles_rad=self._seed_joint_angles_rad,
            )

        return MotionCommand(
            timestamp_s=intent.timestamp_s,
            target=target,
            joint=joint,
            metadata=dict(intent.metadata),
        )


__all__ = [
    "InputIntentMotionGenerator",
    "TargetToJointMotionGenerator",
]
