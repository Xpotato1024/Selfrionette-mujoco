from __future__ import annotations

from dataclasses import dataclass

from selfrionette.input_interpreters import InputInterpreter
from selfrionette.input_interpreters.stubs import NoOpInputInterpreter
from selfrionette.input_sources import InputSource
from selfrionette.input_sources.stubs import StaticInputSource
from selfrionette.motion import MotionGenerator
from selfrionette.motion.stubs import NoOpMotionGenerator
from selfrionette.mujoco_backend import MuJoCoSimulator
from selfrionette.mujoco_backend.stubs import NoOpMuJoCoSimulator
from selfrionette.schemas import MuJoCoState, RawInputFrame
from selfrionette.transport import StatePublisher
from selfrionette.transport.stubs import NoOpStatePublisher

from selfrionette.runtime.config import RuntimeConfig


@dataclass(slots=True)
class RuntimePipeline:
    config: RuntimeConfig
    input_source: InputSource
    input_interpreter: InputInterpreter
    motion_generator: MotionGenerator
    simulator: MuJoCoSimulator
    publisher: StatePublisher

    async def run_once(self, dt_s: float | None = None) -> MuJoCoState:
        dt = self.config.dt_s if dt_s is None else dt_s
        frame = self.input_source.read_frame()
        intent = self.input_interpreter.interpret(frame)
        command = self.motion_generator.update(intent, dt)
        self.simulator.apply_command(command)
        self.simulator.step(dt)
        state = self.simulator.snapshot()
        await self.publisher.publish(state)
        return state


def build_noop_pipeline(
    frame: RawInputFrame | None = None,
    config: RuntimeConfig | None = None,
) -> RuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    raw_frame = frame if frame is not None else RawInputFrame(source="noop", timestamp_s=0.0)

    return RuntimePipeline(
        config=runtime_config,
        input_source=StaticInputSource(raw_frame),
        input_interpreter=NoOpInputInterpreter(),
        motion_generator=NoOpMotionGenerator(),
        simulator=NoOpMuJoCoSimulator(),
        publisher=NoOpStatePublisher(),
    )
