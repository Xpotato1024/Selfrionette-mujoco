from __future__ import annotations

from collections.abc import Sequence

from selfrionette.schemas import RawInputFrame


class ReplayInputSource:
    """Deterministic replay source that yields stored RawInputFrame objects.

    The source returns the frozen frame reference it owns; it does not clone
    the frame or its metadata on read.
    """

    def __init__(self, frames: Sequence[RawInputFrame], *, loop: bool = False) -> None:
        if not frames:
            raise ValueError("ReplayInputSource requires at least one frame")

        self._frames = tuple(frames)
        self._loop = loop
        self._index = 0

    def read_frame(self) -> RawInputFrame:
        if self._index >= len(self._frames):
            if not self._loop:
                raise StopIteration("ReplayInputSource reached end of frames")
            self._index = 0

        frame = self._frames[self._index]
        self._index += 1
        return frame


__all__ = ["ReplayInputSource"]
