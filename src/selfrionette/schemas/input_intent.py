from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from selfrionette.schemas.types import Vector3


@dataclass(frozen=True, slots=True)
class InputIntent:
    source: str
    timestamp_s: float
    target_delta_m: Vector3 = (0.0, 0.0, 0.0)
    joint_delta_rad: tuple[float, ...] = ()
    buttons: tuple[bool, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
