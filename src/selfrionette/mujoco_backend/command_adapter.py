from __future__ import annotations

from selfrionette.schemas import JointCommand, MotionCommand


def motion_command_to_qpos_command(command: MotionCommand) -> JointCommand | None:
    """MotionCommand から backend の qpos command boundary を切り出す。"""

    if command.target is not None:
        raise ValueError("target commands are not supported in qpos command boundary")

    return command.joint
