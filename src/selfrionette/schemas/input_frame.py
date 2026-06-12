from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RawInputFrame:
    source: str
    timestamp_s: float
    values: tuple[float, ...] = ()
    buttons: tuple[bool, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
