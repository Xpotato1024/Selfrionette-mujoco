from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Runtime configuration for runtime composition."""

    dt_s: float = 1.0 / 60.0
    mujoco_model_path: Path | None = None
