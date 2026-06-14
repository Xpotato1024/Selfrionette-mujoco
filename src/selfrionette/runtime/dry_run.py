from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import TextIO

from selfrionette.motion import NoOpMotionGenerator
from selfrionette.mujoco_backend import snapshot_mujoco_state
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


def _sweep_x_replay_frames(steps: int) -> tuple[RawInputFrame, ...]:
    frames: list[RawInputFrame] = []
    for index in range(steps):
        target_delta_m = (0.001 * float(index + 1), 0.0, 0.0)
        frames.append(
            RawInputFrame(
                source="replay",
                timestamp_s=float(index),
                metadata={
                    "preset": "sweep_x",
                    "frame_index": index + 1,
                    "target_delta_m": target_delta_m,
                },
            )
        )

    return tuple(frames)


def _metadata_vector3(value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence):
        raise ValueError("sweep_x replay fixture requires a 3-vector metadata value")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError("sweep_x replay fixture requires a 3-vector metadata value")

    return components


def _find_tip_position_m(state) -> tuple[float, float, float]:
    for site in state.sites:
        if site.name == "tip":
            return site.position_m

    raise ValueError("tip site is required for the sweep_x dry-run fixture")


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
        pipeline = build_replay_mujoco_pipeline(
            frames=_sweep_x_replay_frames(steps),
            config=runtime_config,
            loop=False,
            publisher=WebSocketStatePublisher(sender),
        )
        pipeline.motion_generator = NoOpMotionGenerator()

        lines: list[str] = []
        for _ in range(steps):
            frame = pipeline.input_source.read_frame()
            intent = pipeline.input_interpreter.interpret(frame)
            command = pipeline.motion_generator.update(intent, dt)
            pipeline.simulator.apply_command(command)
            pipeline.simulator.step(dt)

            state = pipeline.simulator.snapshot()
            current_tip_position_m = _find_tip_position_m(state)
            target_delta_m = _metadata_vector3(intent.metadata.get("target_delta_m", (0.0, 0.0, 0.0)))
            desired_endpoint_m = tuple(
                current + delta for current, delta in zip(current_tip_position_m, target_delta_m, strict=True)
            )
            annotated_state = snapshot_mujoco_state(
                pipeline.simulator.model,
                pipeline.simulator.data,
                frame_index=state.frame_index,
                target_position_m=desired_endpoint_m,
                metadata={
                    **state.metadata,
                    "preset": "sweep_x",
                    "current_tip_position_m": current_tip_position_m,
                    "target_delta_m": target_delta_m,
                    "desired_endpoint_m": desired_endpoint_m,
                },
            )
            await pipeline.publisher.publish(annotated_state)
            lines.append(sender.messages[-1])

        return lines

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
