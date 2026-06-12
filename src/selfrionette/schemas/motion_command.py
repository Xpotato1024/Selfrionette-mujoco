from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from selfrionette.schemas.joint_command import JointCommand
from selfrionette.schemas.target_command import TargetCommand


@dataclass(frozen=True, slots=True)
class MotionCommand:
    timestamp_s: float
    target: TargetCommand | None = None
    joint: JointCommand | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
