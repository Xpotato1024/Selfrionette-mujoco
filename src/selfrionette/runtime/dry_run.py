from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import TextIO

from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import WebSocketStatePublisher


class _RecordingSender:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


def _default_replay_frame() -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={"preset": "r6-a-p3-default"},
    )


def _validate_steps(steps: int) -> None:
    if steps < 1:
        raise ValueError("steps must be a positive integer")


def _validate_dt_s(dt_s: float | None) -> None:
    if dt_s is not None and dt_s <= 0.0:
        raise ValueError("dt_s must be positive")


async def _run_replay_mujoco_dry_run_async(
    *,
    steps: int,
    dt_s: float | None,
    frames: Sequence[RawInputFrame] | None,
) -> list[str]:
    sender = _RecordingSender()
    runtime_config = RuntimeConfig() if dt_s is None else RuntimeConfig(dt_s=dt_s)
    replay_frames = tuple(frames) if frames is not None else (_default_replay_frame(),)
    pipeline = build_replay_mujoco_pipeline(
        frames=replay_frames,
        config=runtime_config,
        loop=True,
        publisher=WebSocketStatePublisher(sender),
    )

    lines: list[str] = []
    for _ in range(steps):
        await pipeline.run_once(dt_s=dt_s)
        lines.append(sender.messages[-1])

    return lines


def run_replay_mujoco_dry_run(
    *,
    steps: int,
    dt_s: float | None = None,
    output: TextIO | str | Path | None = None,
    frames: Sequence[RawInputFrame] | None = None,
) -> list[str]:
    _validate_steps(steps)
    _validate_dt_s(dt_s)

    lines = asyncio.run(
        _run_replay_mujoco_dry_run_async(
            steps=steps,
            dt_s=dt_s,
            frames=frames,
        )
    )

    if output is None:
        return lines

    with ExitStack() as stack:
        if isinstance(output, (str, Path)):
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            stream = stack.enter_context(output_path.open("w", encoding="utf-8", newline="\n"))
        else:
            stream = output

        for line in lines:
            stream.write(f"{line}\n")

        stream.flush()

    return lines


__all__ = ["run_replay_mujoco_dry_run"]
