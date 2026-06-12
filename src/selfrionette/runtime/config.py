from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Runtime configuration for the NoOp composition pipeline."""

    dt_s: float = 1.0 / 60.0

