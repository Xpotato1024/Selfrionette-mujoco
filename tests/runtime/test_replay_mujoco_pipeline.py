from __future__ import annotations

import asyncio

from selfrionette.motion import InputIntentMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime import RuntimePipeline, build_replay_mujoco_pipeline
from selfrionette.schemas import MotionCommand, MuJoCoState, RawInputFrame


def test_build_replay_mujoco_pipeline_returns_runtime_pipeline() -> None:
    pipeline = build_replay_mujoco_pipeline()

    assert isinstance(pipeline, RuntimePipeline)
    assert isinstance(pipeline.motion_generator, InputIntentMotionGenerator)
    assert isinstance(pipeline.simulator, HeadlessMuJoCoSimulator)


def test_run_once_replays_frame_into_mujoco_state() -> None:
    frame = RawInputFrame(
        source="replay",
        timestamp_s=3.5,
        metadata={"case": "R6-A-P1"},
    )
    pipeline = build_replay_mujoco_pipeline(frames=(frame,))

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert state.frame_index == 1
    assert state.time_s > 0.0
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)


def test_motion_command_reaches_simulator() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=7.25)
    pipeline = build_replay_mujoco_pipeline(frames=(frame,))

    asyncio.run(pipeline.run_once())

    assert isinstance(pipeline.simulator.last_command, MotionCommand)
    assert pipeline.simulator.last_command.timestamp_s == frame.timestamp_s


def test_replay_eof_raises_stop_iteration_without_looping() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=1.0)
    pipeline = build_replay_mujoco_pipeline(frames=(frame,), loop=False)

    asyncio.run(pipeline.run_once())

    try:
        asyncio.run(pipeline.run_once())
    except StopIteration:
        return
    except RuntimeError as exc:
        assert isinstance(exc.__cause__, StopIteration)
        return

    raise AssertionError("expected StopIteration on replay EOF")


def test_custom_dt_s_is_forwarded_to_simulator() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=2.0)
    pipeline = build_replay_mujoco_pipeline(frames=(frame,))

    asyncio.run(pipeline.run_once(dt_s=0.125))

    assert pipeline.simulator.last_dt_s == 0.125
