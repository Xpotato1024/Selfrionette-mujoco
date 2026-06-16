from __future__ import annotations

import asyncio

from selfrionette.input_interpreters.stubs import NoOpInputInterpreter
from selfrionette.input_sources.stubs import StaticInputSource
from selfrionette.motion.stubs import NoOpMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, default_fast_arm_scene_path
from selfrionette.transport.stubs import NoOpStatePublisher
from selfrionette.runtime import RuntimePipeline, build_mujoco_pipeline, build_noop_pipeline
from selfrionette.schemas import MuJoCoState


def test_build_noop_pipeline_still_works() -> None:
    pipeline = build_noop_pipeline()

    assert isinstance(pipeline, RuntimePipeline)


def test_build_mujoco_pipeline_returns_runtime_pipeline_and_state() -> None:
    pipeline = build_mujoco_pipeline()

    assert isinstance(pipeline, RuntimePipeline)
    assert isinstance(pipeline.input_source, StaticInputSource)
    assert isinstance(pipeline.input_interpreter, NoOpInputInterpreter)
    assert isinstance(pipeline.motion_generator, NoOpMotionGenerator)
    assert isinstance(pipeline.simulator, HeadlessMuJoCoSimulator)
    assert isinstance(pipeline.publisher, NoOpStatePublisher)

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)


def test_build_mujoco_pipeline_accepts_explicit_default_model_path() -> None:
    pipeline = build_mujoco_pipeline(model_path=default_fast_arm_scene_path())

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert state.frame_index == 1
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)
