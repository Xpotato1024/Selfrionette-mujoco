from __future__ import annotations

from typing import Protocol

from selfrionette.schemas import InputIntent, RawInputFrame


class InputInterpreter(Protocol):
    def interpret(self, frame: RawInputFrame) -> InputIntent:
        ...
