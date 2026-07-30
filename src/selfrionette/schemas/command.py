"""MappingからRobot/runtimeへ渡すtyped command schema。

field ordering、unit、frameは各commandのcontractで固定し、viewerやtransportが独自に
physical stateを再構成するためのschemaではない。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real

from selfrionette.schemas.types import Vector3


@dataclass(frozen=True, slots=True)
class EndpointVelocityCommand:
    """``frame`` 座標系のendpoint linear velocity command。

    ``velocity_m_s`` は(x, y, z)順のm/s、``max_delta_m`` は1 stepの上限である。
    accept/reject/holdとqpos生成は対応Robot providerが所有する。
    """

    timestamp_s: float
    velocity_m_s: Vector3
    frame: str

    def __post_init__(self) -> None:
        if isinstance(self.timestamp_s, bool) or not isinstance(
            self.timestamp_s, Real
        ):
            raise TypeError("endpoint velocity command timestamp must be numeric")
        timestamp_s = float(self.timestamp_s)
        if not isfinite(timestamp_s):
            raise ValueError("endpoint velocity command timestamp must be finite")

        values = tuple(self.velocity_m_s)
        if len(values) != 3:
            raise ValueError(
                "endpoint velocity command must contain exactly three finite values"
            )
        if any(
            isinstance(component, bool) or not isinstance(component, Real)
            for component in values
        ):
            raise TypeError(
                "endpoint velocity command components must be numeric"
            )
        velocity = tuple(float(component) for component in values)
        if not all(isfinite(component) for component in velocity):
            raise ValueError(
                "endpoint velocity command must contain exactly three finite values"
            )
        if self.frame not in {"world", "tool"}:
            raise ValueError(
                "endpoint velocity command frame must be 'world' or 'tool'"
            )
        object.__setattr__(self, "timestamp_s", timestamp_s)
        object.__setattr__(self, "velocity_m_s", velocity)


@dataclass(frozen=True, slots=True)
class JointPositionCommand:
    """Robot-owned joint orderingのtarget qpos。角度jointのunitはrad。"""

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
    """legacy joint delta/absolute commandを保持するcompatibility schema。"""

    joint_angles_rad: tuple[float, ...] = ()
    joint_velocities_rad_s: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class TargetCommand:
    """world frameのtarget positionをmで表すhigh-level intent。"""

    position_m: Vector3 | None = None
    delta_m: Vector3 = (0.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class MotionCommand:
    """1 runtime stepで高々1種類のcommandを運ぶexclusive envelope。"""

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
