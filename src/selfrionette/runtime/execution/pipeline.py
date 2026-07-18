"""Generic RuntimePipeline composition contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from selfrionette.input_interpreters import InputInterpreter
from selfrionette.input_sources import InputSource
from selfrionette.motion import MotionGenerator
from selfrionette.mujoco_backend import MuJoCoSimulator
from selfrionette.schemas import MuJoCoState
from selfrionette.transport import StatePublisher

from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.safety.qpos_feasibility import NoOpQposFeasibilityGuard, QposFeasibilityGuard
from selfrionette.runtime.composition.robot_profile_metadata import merge_runtime_metadata


@dataclass(slots=True)
class RuntimePipeline:
    config: RuntimeConfig
    input_source: InputSource
    input_interpreter: InputInterpreter
    motion_generator: MotionGenerator
    simulator: MuJoCoSimulator
    publisher: StatePublisher
    qpos_feasibility_guard: QposFeasibilityGuard | None = None
    state_metadata: Mapping[str, object] | None = None
    robot_profile_metadata: Mapping[str, object] | None = None

    async def run_once(self, dt_s: float | None = None) -> MuJoCoState:
        dt = self.config.dt_s if dt_s is None else dt_s
        frame = self.input_source.read_frame()
        intent = self.input_interpreter.interpret(frame)
        command = self.motion_generator.update(intent, dt)
        pre_step_state = self.simulator.snapshot()
        qpos_guard = self.qpos_feasibility_guard or NoOpQposFeasibilityGuard()
        qpos_result = qpos_guard.evaluate(
            command,
            current_qpos_rad=pre_step_state.qpos,
        )
        command = qpos_result.motion_command
        qpos_rejected = not qpos_result.accepted
        self.simulator.apply_command(command)
        self.simulator.step(dt)
        state = self.simulator.snapshot()
        state = replace(
            state,
            metadata=merge_runtime_metadata(
                state.metadata,
                self.state_metadata,
                authoritative_profile_metadata=self.robot_profile_metadata,
            ),
        )
        if qpos_rejected:
            state = MuJoCoState(
                frame_index=state.frame_index,
                time_s=state.time_s,
                qpos=state.qpos,
                qvel=state.qvel,
                bodies=state.bodies,
                sites=state.sites,
                target_position_m=state.target_position_m,
                metadata=merge_runtime_metadata(
                    state.metadata,
                    command.metadata,
                    {"endpoint_evaluation": None},
                    authoritative_profile_metadata=self.robot_profile_metadata,
                ),
            )
        await self.publisher.publish(state)
        return state
