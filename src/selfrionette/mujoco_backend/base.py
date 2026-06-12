from __future__ import annotations

from typing import Protocol

from selfrionette.schemas import MotionCommand, MuJoCoState


class MuJoCoSimulator(Protocol):
    def apply_command(self, command: MotionCommand) -> None:
        ...

    def step(self, dt_s: float) -> None:
        ...

    def snapshot(self) -> MuJoCoState:
        ...
