"""Robot-independent MuJoCo model reference contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedModelReference:
    role: str
    kind: str
    name: str


__all__ = ["ResolvedModelReference"]
