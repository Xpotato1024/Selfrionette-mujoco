from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from selfrionette.schemas.types import QuaternionWXYZ, Vector3


@dataclass(frozen=True, slots=True)
class BodyTransform:
    name: str
    position_m: Vector3
    quaternion_wxyz: QuaternionWXYZ


@dataclass(frozen=True, slots=True)
class SiteTransform:
    name: str
    position_m: Vector3
    quaternion_wxyz: QuaternionWXYZ


@dataclass(frozen=True, slots=True)
class MuJoCoState:
    frame_index: int
    time_s: float
    qpos: tuple[float, ...] = ()
    qvel: tuple[float, ...] = ()
    bodies: tuple[BodyTransform, ...] = ()
    sites: tuple[SiteTransform, ...] = ()
    target_position_m: Vector3 | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
