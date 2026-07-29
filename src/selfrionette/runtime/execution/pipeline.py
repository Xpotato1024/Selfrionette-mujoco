"""Canonical mapped runtime pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from selfrionette.motion import MotionGenerator
from selfrionette.mujoco_backend import MuJoCoSimulator
from selfrionette.schemas import InputIntent, MotionCommand, MuJoCoState, RawInputFrame
from selfrionette.transport import StatePublisher

from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.control.input_source_state import (
    RuntimeInputSourceState,
    build_runtime_input_source_state_from_metadata,
)
from selfrionette.runtime.experiment.contracts import ControlMappingPlugin
from selfrionette.runtime.experiment.input_source import HealthyInputSource
from selfrionette.runtime.experiment.input_source import InputSourceMappingAdapterContract
from selfrionette.runtime.safety.qpos_feasibility import QposFeasibilityGuard
from selfrionette.runtime.composition.robot_profile_metadata import merge_runtime_metadata

if TYPE_CHECKING:
    from selfrionette.runtime.execution.command_routes import (
        CommandExecutionBinding,
    )
    from selfrionette.runtime.experiment.contracts import CommandSemanticsRoute
    from selfrionette.runtime.safety.input_safety import RuntimeInputSafetyResult


@dataclass(slots=True)
class ControlMappedRuntimePipeline:
    """Production runtime pipeline using the versioned Control Mapping Plugin."""

    config: RuntimeConfig
    input_source: HealthyInputSource
    control_mapping: ControlMappingPlugin
    motion_generator: MotionGenerator | None
    simulator: MuJoCoSimulator
    publisher: StatePublisher
    control_mapping_parameters: Mapping[str, object]
    command_semantics_route: CommandSemanticsRoute
    command_execution: CommandExecutionBinding
    mapping_input_adapter: InputSourceMappingAdapterContract | None = None
    qpos_feasibility_guard: QposFeasibilityGuard | None = None
    state_metadata: Mapping[str, object] | None = None
    robot_profile_metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        from selfrionette.runtime.execution.command_routes import (
            CommandExecutionBinding,
        )

        if not isinstance(self.command_execution, CommandExecutionBinding):
            raise TypeError(
                "runtime pipeline requires a typed command execution binding"
            )
        if (
            self.command_execution.route_identity
            != self.command_semantics_route.identity
            or self.command_execution.control_semantics_identity
            != self.command_semantics_route.control_semantics_identity
            or self.command_execution.robot_command_semantics_identity
            != self.command_semantics_route.robot_command_semantics_identity
            or self.command_execution.command_type
            is not self.command_semantics_route.execution_strategy.command_type
        ):
            raise ValueError(
                "runtime pipeline command route/execution binding mismatch"
            )

    def map_input(self, frame: RawInputFrame) -> InputIntent:
        mapping_input = (
            self.mapping_input_adapter(frame)
            if self.mapping_input_adapter is not None
            else frame
        )
        intent = self.control_mapping.strategy.map_input(
            mapping_input,
            self.control_mapping_parameters,
        )
        if not isinstance(intent, InputIntent):
            raise TypeError("control mapping strategy must return a typed InputIntent")
        return intent

    def execute_intent(
        self,
        intent: InputIntent,
        *,
        dt_s: float,
        pre_step_state: MuJoCoState,
        source_state: RuntimeInputSourceState,
    ) -> RuntimeInputSafetyResult:
        return self.command_execution.execute(
            intent,
            dt_s=dt_s,
            pre_step_state=pre_step_state,
            source_state=source_state,
            pipeline=self,
        )

    def execute_motion_command(
        self,
        command: MotionCommand,
        *,
        pre_step_state: MuJoCoState,
        source_state: RuntimeInputSourceState,
    ) -> RuntimeInputSafetyResult:
        from selfrionette.runtime.execution.command_routes import (
            MotionCommandExecutionBinding,
        )

        if not isinstance(
            self.command_execution,
            MotionCommandExecutionBinding,
        ):
            raise TypeError(
                "selected command route does not accept a MotionCommand envelope"
            )
        return self.command_execution.execute_motion_command(
            command,
            pre_step_state=pre_step_state,
            source_state=source_state,
            pipeline=self,
        )

    async def run_once(self, dt_s: float | None = None) -> MuJoCoState:
        dt = self.config.dt_s if dt_s is None else dt_s
        frame = self.input_source.read_frame()
        intent = self.map_input(frame)
        pre_step_state = self.simulator.snapshot()
        source_state = build_runtime_input_source_state_from_metadata(
            frame.metadata,
            default_source_kind=frame.source,
        )
        safety_result = self.execute_intent(
            intent,
            dt_s=dt,
            pre_step_state=pre_step_state,
            source_state=source_state,
        )
        command = safety_result.motion_command
        qpos_rejected = safety_result.qpos_feasibility_rejected
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
