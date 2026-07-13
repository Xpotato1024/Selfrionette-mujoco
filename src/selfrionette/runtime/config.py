from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Runtime configuration for runtime composition."""

    dt_s: float = 1.0 / 60.0
    robot_profile_id: str | None = None
    mujoco_model_path: Path | None = None
    joint_limit_config_path: Path | None = None

    def __post_init__(self) -> None:
        if self.robot_profile_id is not None and not self.robot_profile_id:
            raise ValueError("robot_profile_id must be a non-empty string when supplied")
        if self.mujoco_model_path is not None:
            object.__setattr__(self, "mujoco_model_path", Path(self.mujoco_model_path))
        if self.joint_limit_config_path is not None:
            object.__setattr__(self, "joint_limit_config_path", Path(self.joint_limit_config_path))
