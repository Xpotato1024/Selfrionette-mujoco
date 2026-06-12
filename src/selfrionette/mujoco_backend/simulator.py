from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from selfrionette.mujoco_backend.model_loader import default_fast_arm_scene_path, load_mujoco_model
from selfrionette.mujoco_backend.snapshot import snapshot_mujoco_state
from selfrionette.schemas import MotionCommand, MuJoCoState


@dataclass(slots=True)
class HeadlessMuJoCoSimulator:
    model: object
    data: object
    model_path: Path
    _frame_index: int = 0
    _last_dt_s: float | None = None
    _last_command: MotionCommand | None = None

    @classmethod
    def from_model_path(cls, model_path: str | Path) -> "HeadlessMuJoCoSimulator":
        bundle = load_mujoco_model(model_path)
        return cls(model=bundle.model, data=bundle.data, model_path=bundle.model_path)

    @classmethod
    def from_default_fast_arm(cls) -> "HeadlessMuJoCoSimulator":
        return cls.from_model_path(default_fast_arm_scene_path())

    def apply_command(self, command: MotionCommand) -> None:
        self._last_command = command

    def step(self, dt_s: float) -> None:
        self._last_dt_s = dt_s
        self._frame_index += 1

    def snapshot(self) -> MuJoCoState:
        return snapshot_mujoco_state(
            self.model,
            self.data,
            frame_index=self._frame_index,
        )
