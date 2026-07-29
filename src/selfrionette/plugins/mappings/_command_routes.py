"""Axis-local helpers for executable Control Mapping command routes."""

from __future__ import annotations

from selfrionette.runtime.execution.command_routes import (
    JointPositionCommandRouteExecutionStrategy,
)
from selfrionette.runtime.experiment.contracts import (
    CommandSemanticsRoute,
    JOINT_POSITION_COMMAND_V1,
    VersionedIdentity,
)


def joint_position_command_route(
    *,
    route_identity: VersionedIdentity,
    control_semantics_identity: VersionedIdentity,
) -> CommandSemanticsRoute:
    strategy = JointPositionCommandRouteExecutionStrategy(
        route_identity=route_identity,
        control_semantics_identity=control_semantics_identity,
        robot_command_semantics_identity=JOINT_POSITION_COMMAND_V1,
    )
    return CommandSemanticsRoute(
        identity=route_identity,
        control_semantics_identity=control_semantics_identity,
        robot_command_semantics_identity=JOINT_POSITION_COMMAND_V1,
        execution_strategy=strategy,
    )


__all__ = ["joint_position_command_route"]
