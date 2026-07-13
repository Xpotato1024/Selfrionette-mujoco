"""Runtime composition module with a compatibility noop builder."""

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
from selfrionette.runtime.fast_arm_joint_limits import (
    FastArmJointLimitConfig,
    apply_fast_arm_qpos_feasibility_guard,
)


@dataclass(slots=True)
class RuntimePipeline:
    config: RuntimeConfig
    input_source: InputSource
    input_interpreter: InputInterpreter
    motion_generator: MotionGenerator
    simulator: MuJoCoSimulator
    publisher: StatePublisher
    joint_limits: FastArmJointLimitConfig | None = None

    async def run_once(self, dt_s: float | None = None) -> MuJoCoState:
        dt = self.config.dt_s if dt_s is None else dt_s
        frame = self.input_source.read_frame()
        intent = self.input_interpreter.interpret(frame)
        command = self.motion_generator.update(intent, dt)
        pre_step_state = self.simulator.snapshot()
        if self.joint_limits is not None:
            command = apply_fast_arm_qpos_feasibility_guard(
                command,
                current_qpos_rad=pre_step_state.qpos,
                joint_limits=self.joint_limits,
            ).motion_command
        self.simulator.apply_command(command)
        self.simulator.step(dt)
        state = self.simulator.snapshot()
        if command.metadata.get("qpos_feasibility_rejected"):
            state = MuJoCoState(
                frame_index=state.frame_index,
                time_s=state.time_s,
                qpos=state.qpos,
                qvel=state.qvel,
                bodies=state.bodies,
                sites=state.sites,
                target_position_m=state.target_position_m,
                metadata={
                    **state.metadata,
                    **dict(command.metadata),
                    "endpoint_evaluation": None,
                },
            )
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
