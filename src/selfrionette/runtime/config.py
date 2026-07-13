from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Runtime configuration for runtime composition."""

    dt_s: float = 1.0 / 60.0
    mujoco_model_path: Path | None = None
    fast_arm_joint_limits_path: Path | None = None

    def __post_init__(self) -> None:
        if self.fast_arm_joint_limits_path is not None:
            object.__setattr__(self, "fast_arm_joint_limits_path", Path(self.fast_arm_joint_limits_path))
