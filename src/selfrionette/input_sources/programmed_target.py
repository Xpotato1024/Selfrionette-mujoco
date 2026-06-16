from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from selfrionette.schemas import RawInputFrame
from selfrionette.schemas.types import Vector3


def _coerce_vector3(name: str, value: object) -> Vector3:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    return components


@dataclass(frozen=True, slots=True)
class ProgrammedTargetFrame:
    t_s: float
    target_position_m: Vector3
    desired_endpoint_m: Vector3
    target_velocity_mps: Vector3 | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_position_m", _coerce_vector3("target_position_m", self.target_position_m))
        object.__setattr__(self, "desired_endpoint_m", _coerce_vector3("desired_endpoint_m", self.desired_endpoint_m))
        if self.target_velocity_mps is not None:
            object.__setattr__(
                self,
                "target_velocity_mps",
                _coerce_vector3("target_velocity_mps", self.target_velocity_mps),
            )

    def to_raw_input_frame(self, *, trajectory_name: str, frame_index: int) -> RawInputFrame:
        metadata: dict[str, object] = {
            "source_kind": "programmed_target",
            "trajectory_name": trajectory_name,
            "target_position_m": self.target_position_m,
            "desired_endpoint_m": self.desired_endpoint_m,
            "t_s": self.t_s,
            "frame_index": frame_index,
        }
        if self.target_velocity_mps is not None:
            metadata["target_velocity_mps"] = self.target_velocity_mps

        return RawInputFrame(
            source="programmed_target",
            timestamp_s=self.t_s,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class ProgrammedTargetTrajectory:
    name: str
    frames: tuple[ProgrammedTargetFrame, ...]

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("ProgrammedTargetTrajectory requires at least one frame")

        object.__setattr__(self, "frames", tuple(self.frames))


class ProgrammedTargetInputSource:
    """Deterministic programmed target input source."""

    def __init__(self, trajectory: ProgrammedTargetTrajectory, *, loop: bool = False) -> None:
        self._trajectory = trajectory
        self._loop = loop
        self._index = 0

    def _next_frame_index(self) -> int:
        frame_count = len(self._trajectory.frames)
        if self._loop:
            frame_index = self._index % frame_count
            self._index = (frame_index + 1) % frame_count
            return frame_index

        frame_index = min(self._index, frame_count - 1)
        if self._index < frame_count - 1:
            self._index += 1
        else:
            self._index = frame_count - 1
        return frame_index

    def read_frame(self) -> RawInputFrame:
        frame_index = self._next_frame_index()
        frame = self._trajectory.frames[frame_index]
        return frame.to_raw_input_frame(trajectory_name=self._trajectory.name, frame_index=frame_index)


__all__ = [
    "ProgrammedTargetFrame",
    "ProgrammedTargetInputSource",
    "ProgrammedTargetTrajectory",
]
