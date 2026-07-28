from __future__ import annotations

import pytest

from selfrionette.plugins.input_sources.replay import ReplayInputSource
from selfrionette.schemas import RawInputFrame


def test_replay_input_source_returns_frames_in_order() -> None:
    frames = (
        RawInputFrame(source="replay", timestamp_s=0.0, values=(1.0, 2.0)),
        RawInputFrame(source="replay", timestamp_s=0.1, values=(3.0, 4.0)),
    )
    source = ReplayInputSource(frames)

    assert source.read_frame() is frames[0]
    assert source.read_frame() is frames[1]


def test_replay_input_source_raises_stop_iteration_at_eof() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=0.0, values=(1.0,))
    source = ReplayInputSource((frame,), loop=False)

    assert source.read_frame() == frame

    with pytest.raises(
        StopIteration,
        match="ReplayInputSource reached end of frames",
    ):
        source.read_frame()


def test_replay_input_source_loops_back_to_start() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=0.0, values=(1.0,))
    source = ReplayInputSource((frame,), loop=True)

    assert source.read_frame() == frame
    assert source.read_frame() == frame


def test_replay_input_source_rejects_empty_frames() -> None:
    with pytest.raises(ValueError, match="at least one frame"):
        ReplayInputSource(())


def test_old_replay_path_re_exports_canonical_reader() -> None:
    from selfrionette.input_sources import (
        ReplayInputSource as CompatibilityReplayInputSource,
    )

    assert CompatibilityReplayInputSource is ReplayInputSource
