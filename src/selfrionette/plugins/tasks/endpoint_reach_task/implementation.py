"""R7-G endpoint reach task lifecycle and canonical evidence declarations."""

from __future__ import annotations

from enum import Enum

from selfrionette.runtime.composition.robot_bundle import (
    ENDPOINT_POSE_V1,
    RESET_INITIAL_STATE_V1,
    ROBOT_TOOL_ENDPOINT_ROLE,
)
from selfrionette.runtime.experiment.contracts import (
    CanonicalEvidenceSet,
    EvidenceStatus,
    ParameterContract,
    ROLE_ATTRIBUTE_WILDCARD,
    SemanticRoleRequirement,
    TaskPlugin,
    TaskTerminalClassification,
    VersionedIdentity,
)
from selfrionette.runtime.experiment.endpoint_reach_evidence import (
    ENDPOINT_REACH_TERMINAL_EVIDENCE,
    ENDPOINT_REACH_TRAJECTORY_EVIDENCE,
    decode_endpoint_reach_terminal_evidence,
)


ENDPOINT_REACH_TASK_IDENTITY = VersionedIdentity("endpoint_reach_task", 1)
class EndpointReachTaskState(str, Enum):
    """Runner-independent task state owned by the endpoint reach lifecycle."""

    READY = "ready"
    RUNNING = "running"


class EndpointReachTaskLifecycle:
    """Classify the canonical task event without calculating evaluation metrics."""

    def initial_state(self, parameters: Mapping[str, object]) -> EndpointReachTaskState:
        if parameters:
            raise ValueError("endpoint reach task does not accept plugin parameters")
        return EndpointReachTaskState.READY

    def classify_terminal(
        self,
        state: object,
        evidence: CanonicalEvidenceSet,
    ) -> TaskTerminalClassification:
        if state not in {EndpointReachTaskState.READY, EndpointReachTaskState.RUNNING}:
            raise ValueError("unknown endpoint reach task state")
        entry = evidence.require(ENDPOINT_REACH_TERMINAL_EVIDENCE)
        if entry.status in {EvidenceStatus.UNAVAILABLE, EvidenceStatus.INVALID}:
            return TaskTerminalClassification.TECHNICAL_INVALID
        if entry.status is not EvidenceStatus.MEASURED:
            raise ValueError("endpoint reach terminal evidence must be measured")
        terminal = decode_endpoint_reach_terminal_evidence(evidence)
        return terminal.classification


ENDPOINT_REACH_TASK_PLUGIN = TaskPlugin(
    identity=ENDPOINT_REACH_TASK_IDENTITY,
    lifecycle=EndpointReachTaskLifecycle(),
    required_robot_capabilities=frozenset(
        {ENDPOINT_POSE_V1, RESET_INITIAL_STATE_V1}
    ),
    required_semantic_roles=frozenset(
        {
            SemanticRoleRequirement(
                role=ROBOT_TOOL_ENDPOINT_ROLE,
                object_kind="robot_endpoint",
                frame=ROLE_ATTRIBUTE_WILDCARD,
                unit="meter",
            )
        }
    ),
    parameter_contract=ParameterContract(),
    task_event_identity=ENDPOINT_REACH_TERMINAL_EVIDENCE,
    produced_evidence=frozenset(
        {ENDPOINT_REACH_TERMINAL_EVIDENCE, ENDPOINT_REACH_TRAJECTORY_EVIDENCE}
    ),
    compatible_backend_kinds=frozenset({"mujoco"}),
)


__all__ = [
    "ENDPOINT_REACH_TASK_IDENTITY",
    "ENDPOINT_REACH_TASK_PLUGIN",
    "ENDPOINT_REACH_TERMINAL_EVIDENCE",
    "ENDPOINT_REACH_TRAJECTORY_EVIDENCE",
    "EndpointReachTaskLifecycle",
    "EndpointReachTaskState",
]
