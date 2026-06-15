from __future__ import annotations

from collections.abc import Mapping, Sequence

from selfrionette.kinematics import InverseKinematicsSolver
from selfrionette.schemas import InputIntent, JointCommand, MotionCommand, TargetCommand


def _has_non_zero_delta(delta_m: tuple[float, float, float]) -> bool:
    return any(component != 0.0 for component in delta_m)


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    return components


def _resolve_target_position_m(intent: InputIntent) -> tuple[float, float, float] | None:
    target_position_m = getattr(intent, "target_position_m", None)
    if target_position_m is None:
        target_position_m = intent.metadata.get("target_position_m")

    if target_position_m is None:
        return None

    return _coerce_vector3("target_position_m", target_position_m)


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
    """Build a MotionCommand from a command-side target boundary."""

    return _build_motion_command(
        timestamp_s=timestamp_s,
        target=target_command,
        joint=joint_command,
        metadata=metadata,
    )


def build_motion_command_from_input_intent(intent: InputIntent) -> MotionCommand:
    if intent.joint_delta_rad:
        raise ValueError("joint_delta_rad to MotionCommand.joint conversion is not supported")

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
    """Skeleton that resolves a target position through IK."""

    def __init__(
        self,
        ik_solver: InverseKinematicsSolver,
        *,
        seed_joint_angles_rad: tuple[float, ...] | None = None,
        qpos_joint_count: int | None = None,
    ) -> None:
        self._ik_solver = ik_solver
        self._seed_joint_angles_rad = seed_joint_angles_rad
        self._qpos_joint_count = qpos_joint_count

    def update(self, intent: InputIntent, dt_s: float) -> MotionCommand:
        _ = dt_s  # Protocol compatibility; this skeleton does not use delta time yet.

        if intent.joint_delta_rad:
            raise ValueError("joint_delta_rad to MotionCommand.joint conversion is not supported")

        target_position_m = _resolve_target_position_m(intent)
        if target_position_m is None:
            if _has_non_zero_delta(intent.target_delta_m):
                target = TargetCommand(delta_m=intent.target_delta_m)
                return build_motion_command_from_target_command(
                    timestamp_s=intent.timestamp_s,
                    target_command=target,
                    metadata=intent.metadata,
                )

            raise ValueError("target_position_m is required for TargetToJointMotionGenerator")

        target = TargetCommand(delta_m=intent.target_delta_m) if _has_non_zero_delta(intent.target_delta_m) else None
        joint = self._ik_solver.solve(
            target_position_m,
            seed_joint_angles_rad=self._seed_joint_angles_rad,
        )

        if self._qpos_joint_count is not None:
            joint_angles_rad = joint.joint_angles_rad
            if len(joint_angles_rad) > self._qpos_joint_count:
                raise ValueError("solver output is longer than the configured qpos joint count")

            if len(joint_angles_rad) < self._qpos_joint_count:
                joint = JointCommand(
                    joint_angles_rad=joint_angles_rad + (0.0,) * (self._qpos_joint_count - len(joint_angles_rad)),
                    joint_velocities_rad_s=joint.joint_velocities_rad_s,
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
