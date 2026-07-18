from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from selfrionette.schemas.types import Vector3


@dataclass(frozen=True, slots=True)
class JointCommand:
    joint_angles_rad: tuple[float, ...] = ()
    joint_velocities_rad_s: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class TargetCommand:
    position_m: Vector3 | None = None
    delta_m: Vector3 = (0.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class MotionCommand:
    timestamp_s: float
    target: TargetCommand | None = None
    joint: JointCommand | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


__all__ = ["JointCommand", "MotionCommand", "TargetCommand"]
