"""Test-double namespace for input source stubs."""

from __future__ import annotations

from selfrionette.input_sources.base import InputSource
from selfrionette.schemas import RawInputFrame


class StaticInputSource:
    """Static input source stub that always returns the provided frame."""

    def __init__(self, frame: RawInputFrame) -> None:
        self._frame = frame

    def read_frame(self) -> RawInputFrame:
        return self._frame


# Keep the contract import available for explicit, module-local imports.
__all__ = ["StaticInputSource"]
