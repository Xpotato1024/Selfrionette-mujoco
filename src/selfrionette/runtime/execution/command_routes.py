"""Typed executable control-to-Robot command route bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from selfrionette.runtime.composition.robot_bundle import (
    RobotCommandSemanticProvider,
)
from selfrionette.runtime.control.input_source_state import RuntimeInputSourceState
from selfrionette.runtime.execution.pipeline import ControlMappedRuntimePipeline
from selfrionette.runtime.experiment.contracts import (
    CommandSemanticsRoute,
    VersionedIdentity,
)
from selfrionette.runtime.safety.input_safety import (
    RuntimeInputSafetyResult,
    build_runtime_input_safety_result,
)
from selfrionette.schemas import (
    EndpointVelocityCommand,
    InputIntent,
    JointPositionCommand,
    MotionCommand,
    MuJoCoState,
)


@runtime_checkable
class CommandExecutionBinding(Protocol):
    route_identity: VersionedIdentity
    control_semantics_identity: VersionedIdentity
    robot_command_semantics_identity: VersionedIdentity
    requires_motion_generator: bool

    def execute(
        self,
        intent: InputIntent,
        *,
        dt_s: float,
        pre_step_state: MuJoCoState,
        source_state: RuntimeInputSourceState,
        pipeline: ControlMappedRuntimePipeline,
    ) -> RuntimeInputSafetyResult: ...


@dataclass(frozen=True, slots=True)
class ResolvedCommandExecution:
    route: CommandSemanticsRoute
    binding: CommandExecutionBinding

    def __post_init__(self) -> None:
        if not isinstance(self.binding, CommandExecutionBinding):
            raise TypeError(
                "resolved command execution requires a typed execution binding"
            )
        if (
            self.binding.route_identity != self.route.identity
            or self.binding.control_semantics_identity
            != self.route.control_semantics_identity
            or self.binding.robot_command_semantics_identity
            != self.route.robot_command_semantics_identity
        ):
            raise ValueError(
                "selected command route and execution binding identity mismatch"
            )


def _validate_provider(
    provider: object,
    *,
    semantic_identity: VersionedIdentity,
    command_type: type,
) -> RobotCommandSemanticProvider:
    if not isinstance(provider, RobotCommandSemanticProvider):
        raise TypeError(
            "command route execution strategy requires a typed "
            "RobotCommandSemanticProvider"
        )
    if provider.command_semantics_identity != semantic_identity:
        raise ValueError(
            "command route execution strategy/Robot provider semantic mismatch"
        )
    if provider.command_type is not command_type:
        raise TypeError(
            "command route execution strategy/Robot provider command type mismatch"
        )
    return provider


def project_joint_position_command(
    command: MotionCommand,
) -> JointPositionCommand:
    """Project a validated runtime envelope onto the Robot command boundary."""

    if not isinstance(command, MotionCommand):
        raise TypeError(
            "joint-position projection requires a MotionCommand envelope"
        )
    if command.joint is None:
        raise ValueError(
            "joint_position_command/v1 requires MotionCommand.joint"
        )
    if command.joint.joint_velocities_rad_s:
        raise ValueError(
            "joint_position_command/v1 does not accept joint velocities"
        )
    return JointPositionCommand(
        timestamp_s=command.timestamp_s,
        joint_angles_rad=command.joint.joint_angles_rad,
    )


@dataclass(frozen=True, slots=True)
class JointPositionCommandExecutionBinding:
    route_identity: VersionedIdentity
    control_semantics_identity: VersionedIdentity
    robot_command_semantics_identity: VersionedIdentity
    provider: RobotCommandSemanticProvider
    requires_motion_generator: bool = True

    def execute(
        self,
        intent: InputIntent,
        *,
        dt_s: float,
        pre_step_state: MuJoCoState,
        source_state: RuntimeInputSourceState,
        pipeline: ControlMappedRuntimePipeline,
    ) -> RuntimeInputSafetyResult:
        motion_generator = pipeline.motion_generator
        if motion_generator is None:
            raise RuntimeError(
                "joint-position command execution requires a MotionGenerator"
            )
        set_current_qpos = getattr(motion_generator, "set_current_qpos_rad", None)
        if callable(set_current_qpos):
            set_current_qpos(tuple(pre_step_state.qpos))
        motion_command = motion_generator.update(intent, dt_s)
        safety_result = build_runtime_input_safety_result(
            motion_command,
            source_state=source_state,
            current_state=pre_step_state,
            qpos_feasibility_guard=pipeline.qpos_feasibility_guard,
        )
        robot_command = project_joint_position_command(
            safety_result.motion_command
        )
        self.provider.execute(robot_command, backend=pipeline.simulator)
        record_motion_envelope = getattr(
            pipeline.simulator,
            "record_motion_command_envelope",
            None,
        )
        if callable(record_motion_envelope):
            record_motion_envelope(safety_result.motion_command)
        return safety_result


@dataclass(frozen=True, slots=True)
class NativeEndpointVelocityCommandExecutionBinding:
    route_identity: VersionedIdentity
    control_semantics_identity: VersionedIdentity
    robot_command_semantics_identity: VersionedIdentity
    provider: RobotCommandSemanticProvider
    requires_motion_generator: bool = False

    def execute(
        self,
        intent: InputIntent,
        *,
        dt_s: float,
        pre_step_state: MuJoCoState,
        source_state: RuntimeInputSourceState,
        pipeline: ControlMappedRuntimePipeline,
    ) -> RuntimeInputSafetyResult:
        _ = dt_s
        _ = pre_step_state
        velocity_value = intent.metadata.get("local_endpoint_velocity_m_s")
        if not isinstance(velocity_value, (tuple, list)) or len(velocity_value) != 3:
            raise TypeError(
                "native endpoint-velocity execution requires "
                "local_endpoint_velocity_m_s"
            )
        velocity = tuple(float(component) for component in velocity_value)
        frame_value = intent.metadata.get(
            "local_endpoint_velocity_frame",
            intent.metadata.get("control_frame"),
        )
        if not isinstance(frame_value, str) or not frame_value:
            raise TypeError(
                "native endpoint-velocity execution requires a velocity frame"
            )
        stale_reason = source_state.stale_reason
        if stale_reason is None and not source_state.source_active:
            stale_reason = "source_inactive"
        applied_velocity = (0.0, 0.0, 0.0) if stale_reason is not None else velocity
        command = EndpointVelocityCommand(
            timestamp_s=intent.timestamp_s,
            velocity_m_s=applied_velocity,
            frame=frame_value,
        )
        self.provider.execute(command, backend=pipeline.simulator)
        projection = MotionCommand(
            timestamp_s=intent.timestamp_s,
            metadata={
                **dict(intent.metadata),
                "command_route_execution": self.route_identity.canonical_id,
                "robot_command_semantics": (
                    self.robot_command_semantics_identity.canonical_id
                ),
                "endpoint_velocity_m_s": applied_velocity,
                "endpoint_velocity_frame": frame_value,
                "runtime_input_safety_applied": stale_reason is not None,
            },
        )
        return RuntimeInputSafetyResult(
            motion_command=projection,
            source_state=RuntimeInputSourceState(
                source_kind=source_state.source_kind,
                source_active=source_state.source_active,
                command_age_ms=source_state.command_age_ms,
                stale_reason=stale_reason,
            ),
            is_stale=stale_reason is not None,
            should_update_target_position_m=False,
            stale_reason=stale_reason,
            command_age_ms=source_state.command_age_ms,
        )


@dataclass(frozen=True, slots=True)
class JointPositionCommandRouteExecutionStrategy:
    route_identity: VersionedIdentity
    control_semantics_identity: VersionedIdentity
    robot_command_semantics_identity: VersionedIdentity

    def bind(self, provider: object) -> JointPositionCommandExecutionBinding:
        typed_provider = _validate_provider(
            provider,
            semantic_identity=self.robot_command_semantics_identity,
            command_type=JointPositionCommand,
        )
        return JointPositionCommandExecutionBinding(
            route_identity=self.route_identity,
            control_semantics_identity=self.control_semantics_identity,
            robot_command_semantics_identity=self.robot_command_semantics_identity,
            provider=typed_provider,
        )


@dataclass(frozen=True, slots=True)
class NativeEndpointVelocityCommandRouteExecutionStrategy:
    route_identity: VersionedIdentity
    control_semantics_identity: VersionedIdentity
    robot_command_semantics_identity: VersionedIdentity

    def bind(
        self, provider: object
    ) -> NativeEndpointVelocityCommandExecutionBinding:
        typed_provider = _validate_provider(
            provider,
            semantic_identity=self.robot_command_semantics_identity,
            command_type=EndpointVelocityCommand,
        )
        return NativeEndpointVelocityCommandExecutionBinding(
            route_identity=self.route_identity,
            control_semantics_identity=self.control_semantics_identity,
            robot_command_semantics_identity=self.robot_command_semantics_identity,
            provider=typed_provider,
        )


__all__ = [
    "CommandExecutionBinding",
    "JointPositionCommandExecutionBinding",
    "JointPositionCommandRouteExecutionStrategy",
    "NativeEndpointVelocityCommandExecutionBinding",
    "NativeEndpointVelocityCommandRouteExecutionStrategy",
    "project_joint_position_command",
    "ResolvedCommandExecution",
]
