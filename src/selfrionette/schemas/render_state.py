from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RenderState:
    frame_index: int
    time_s: float
    metadata: Mapping[str, object] = field(default_factory=dict)
