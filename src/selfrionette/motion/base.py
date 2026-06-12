from __future__ import annotations

from typing import Protocol

from selfrionette.schemas import InputIntent, MotionCommand


class MotionGenerator(Protocol):
    def update(self, intent: InputIntent, dt_s: float) -> MotionCommand:
        ...
