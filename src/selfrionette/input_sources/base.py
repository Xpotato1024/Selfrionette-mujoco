from __future__ import annotations

from typing import Protocol

from selfrionette.schemas import RawInputFrame


class InputSource(Protocol):
    def read_frame(self) -> RawInputFrame:
        ...
