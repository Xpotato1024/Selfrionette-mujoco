from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real

from selfrionette.schemas.types import Vector3


@dataclass(frozen=True, slots=True)
class EndpointVelocityCommand:
    timestamp_s: float
    velocity_m_s: Vector3
    frame: str

    def __post_init__(self) -> None:
        velocity = tuple(float(component) for component in self.velocity_m_s)
        if len(velocity) != 3 or not all(isfinite(component) for component in velocity):
            raise ValueError(
                "endpoint velocity command must contain exactly three finite values"
            )
        if self.frame not in {"world", "tool"}:
            raise ValueError(
                "endpoint velocity command frame must be 'world' or 'tool'"
            )
        if not isfinite(self.timestamp_s):
            raise ValueError("endpoint velocity command timestamp must be finite")
        object.__setattr__(self, "velocity_m_s", velocity)


@dataclass(frozen=True, slots=True)
class JointPositionCommand:
    timestamp_s: float
    joint_angles_rad: tuple[float, ...]

    def __post_init__(self) -> None:
        if isinstance(self.timestamp_s, bool) or not isinstance(
            self.timestamp_s, Real
        ):
            raise TypeError("joint position command timestamp must be numeric")
        timestamp_s = float(self.timestamp_s)
        if not isfinite(timestamp_s):
            raise ValueError("joint position command timestamp must be finite")

        values = tuple(self.joint_angles_rad)
        if not values:
            raise ValueError(
                "joint position command must contain at least one joint angle"
            )
        if any(
            isinstance(value, bool) or not isinstance(value, Real)
            for value in values
        ):
            raise TypeError("joint position command angles must be numeric")
        joint_angles_rad = tuple(float(value) for value in values)
        if not all(isfinite(value) for value in joint_angles_rad):
            raise ValueError("joint position command angles must be finite")

        object.__setattr__(self, "timestamp_s", timestamp_s)
        object.__setattr__(self, "joint_angles_rad", joint_angles_rad)


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


RobotCommand = EndpointVelocityCommand | JointPositionCommand


__all__ = [
    "EndpointVelocityCommand",
    "JointCommand",
    "JointPositionCommand",
    "MotionCommand",
    "RobotCommand",
    "TargetCommand",
]
