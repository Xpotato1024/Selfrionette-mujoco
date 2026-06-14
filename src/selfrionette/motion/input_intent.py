from __future__ import annotations

from collections.abc import Mapping

from selfrionette.kinematics import InverseKinematicsSolver
from selfrionette.schemas import InputIntent, JointCommand, MotionCommand, TargetCommand


def _has_non_zero_delta(delta_m: tuple[float, float, float]) -> bool:
    return any(component != 0.0 for component in delta_m)


def _build_motion_command(
    *,
    timestamp_s: float,
    target: TargetCommand | None = None,
    joint: JointCommand | None = None,
    metadata: Mapping[str, object] | None = None,
) -> MotionCommand:
    return MotionCommand(
        timestamp_s=timestamp_s,
        target=target,
        joint=joint,
        metadata={} if metadata is None else dict(metadata),
    )


def build_motion_command_from_target_command(
    *,
    timestamp_s: float,
    target_command: TargetCommand | None,
    metadata: Mapping[str, object] | None = None,
    joint_command: JointCommand | None = None,
) -> MotionCommand:
    """command-side target boundary から MotionCommand を構築する。"""

    return _build_motion_command(
        timestamp_s=timestamp_s,
        target=target_command,
        joint=joint_command,
        metadata=metadata,
    )


def build_motion_command_from_input_intent(intent: InputIntent) -> MotionCommand:
    if intent.joint_delta_rad:
        raise ValueError("R6-E-P2 では joint_delta_rad から MotionCommand.joint への変換は未対応です")

    target = TargetCommand(delta_m=intent.target_delta_m) if _has_non_zero_delta(intent.target_delta_m) else None
    return build_motion_command_from_target_command(
        timestamp_s=intent.timestamp_s,
        target_command=target,
        metadata=intent.metadata,
    )


class InputIntentMotionGenerator:
    """Minimal motion skeleton that turns replay intent into MotionCommand."""

    def update(self, intent: InputIntent, dt_s: float) -> MotionCommand:
        _ = dt_s  # Protocol compatibility; this skeleton does not use delta time yet.
        return build_motion_command_from_input_intent(intent)


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
            raise ValueError("R6-E-P2 では joint_delta_rad から MotionCommand.joint への変換は未対応です")

        target = TargetCommand(delta_m=intent.target_delta_m) if _has_non_zero_delta(intent.target_delta_m) else None
        joint: JointCommand | None = None

        # Temporary hook for future target-position compatible objects only.
        target_position_m = getattr(intent, "target_position_m", None)
        if target_position_m is not None:
            joint = self._ik_solver.solve(
                target_position_m,
                seed_joint_angles_rad=self._seed_joint_angles_rad,
            )

        return build_motion_command_from_target_command(
            timestamp_s=intent.timestamp_s,
            target_command=target,
            joint_command=joint,
            metadata=intent.metadata,
        )


__all__ = [
    "InputIntentMotionGenerator",
    "build_motion_command_from_input_intent",
    "build_motion_command_from_target_command",
    "TargetToJointMotionGenerator",
]
