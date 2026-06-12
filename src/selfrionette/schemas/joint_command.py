from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointCommand:
    joint_angles_rad: tuple[float, ...] = ()
    joint_velocities_rad_s: tuple[float, ...] = ()
