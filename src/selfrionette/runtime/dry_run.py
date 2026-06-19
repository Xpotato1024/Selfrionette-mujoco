from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import TextIO

from selfrionette.input_sources import build_sweep_x_input_source
from selfrionette.mujoco_backend import snapshot_mujoco_state
from selfrionette.runtime.concrete_mujoco_pipeline import DEFAULT_CONCRETE_TARGET_POSITION_M, build_concrete_mujoco_pipeline
from selfrionette.runtime.config import RuntimeConfig
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
        metadata={
            "preset": "r6-a-p3-default",
            "target_position_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
            "desired_endpoint_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
        },
    )


def _sweep_x_replay_frames(steps: int) -> tuple[RawInputFrame, ...]:
    source = build_sweep_x_input_source(initial_position_m=DEFAULT_CONCRETE_TARGET_POSITION_M, loop=False)
    return tuple(source.read_frame() for _ in range(steps))


def _validate_steps(steps: int) -> None:
    if steps < 1:
        raise ValueError("steps must be a positive integer")


def _validate_dt_s(dt_s: float | None) -> None:
    if dt_s is not None and dt_s <= 0.0:
        raise ValueError("dt_s must be positive")


def _validate_preset(preset: str | None) -> None:
    if preset is None:
        return
    if preset != "sweep_x":
        raise ValueError("unsupported dry-run preset")


def _validate_preset_frames(preset: str | None, frames: Sequence[RawInputFrame] | None) -> None:
    if preset is not None and frames is not None:
        raise ValueError("preset and custom frames are mutually exclusive")


async def _run_replay_mujoco_dry_run_async(
    *,
    steps: int,
    dt_s: float | None,
    frames: Sequence[RawInputFrame] | None,
    preset: str | None,
) -> list[str]:
    sender = _RecordingSender()
    runtime_config = RuntimeConfig() if dt_s is None else RuntimeConfig(dt_s=dt_s)
    dt = runtime_config.dt_s

    if preset == "sweep_x" and frames is None:
        pipeline = build_concrete_mujoco_pipeline(
            frames=_sweep_x_replay_frames(steps),
            config=runtime_config,
            loop=False,
            publisher=WebSocketStatePublisher(sender),
        )

        lines: list[str] = []
        for _ in range(steps):
            frame = pipeline.input_source.read_frame()
            intent = pipeline.input_interpreter.interpret(frame)
            command = pipeline.motion_generator.update(intent, dt)
            pipeline.simulator.apply_command(command)
            pipeline.simulator.step(dt)

            state = pipeline.simulator.snapshot()
            annotated_state = snapshot_mujoco_state(
                pipeline.simulator.model,
                pipeline.simulator.data,
                frame_index=state.frame_index,
                target_position_m=tuple(intent.metadata["desired_endpoint_m"]),
                metadata={
                    **state.metadata,
                    **intent.metadata,
                    "preset": "sweep_x",
                },
            )
            await pipeline.publisher.publish(annotated_state)
            lines.append(sender.messages[-1])

        return lines

    replay_frames = tuple(frames) if frames is not None else (_default_replay_frame(),)
    pipeline = build_concrete_mujoco_pipeline(
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
    preset: str | None = None,
) -> list[str]:
    _validate_steps(steps)
    _validate_dt_s(dt_s)
    _validate_preset(preset)
    _validate_preset_frames(preset, frames)

    lines = asyncio.run(
        _run_replay_mujoco_dry_run_async(
            steps=steps,
            dt_s=dt_s,
            frames=frames,
            preset=preset,
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
