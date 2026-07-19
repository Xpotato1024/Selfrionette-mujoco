from __future__ import annotations

from typing import Protocol, runtime_checkable

from selfrionette.schemas import RawInputFrame


@runtime_checkable
class InputSource(Protocol):
    def read_frame(self) -> RawInputFrame:
        ...
