from __future__ import annotations

from dataclasses import dataclass

from selfrionette.schemas.types import Vector3


@dataclass(frozen=True, slots=True)
class TargetCommand:
    position_m: Vector3 | None = None
    delta_m: Vector3 = (0.0, 0.0, 0.0)
