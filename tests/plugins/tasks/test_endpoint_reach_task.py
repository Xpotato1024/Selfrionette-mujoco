from __future__ import annotations

import pytest

from selfrionette.plugins.tasks.endpoint_reach_task.implementation import (
    ENDPOINT_REACH_TASK_PLUGIN,
    ENDPOINT_REACH_TERMINAL_EVIDENCE,
    ENDPOINT_REACH_TRAJECTORY_EVIDENCE,
    EndpointReachTaskState,
)
from selfrionette.runtime.composition.robot_bundle import (
    ENDPOINT_POSE_V1,
    RESET_INITIAL_STATE_V1,
)
from selfrionette.runtime.experiment.contracts import (
    CanonicalEvidence,
    CanonicalEvidenceSet,
    EvidenceStatus,
    TaskTerminalClassification,
    VersionedIdentity,
)


def _terminal(
    classification: str,
    *,
    elapsed_time_s: float | None,
    reason: str | None = None,
    status: EvidenceStatus = EvidenceStatus.MEASURED,
) -> CanonicalEvidenceSet:
    value = None
    failure_reason = reason
    if status is EvidenceStatus.MEASURED:
        value = {
            "classification": classification,
            "elapsed_time_s": elapsed_time_s,
            "reason": reason,
        }
    elif failure_reason is None:
        failure_reason = "measurement unavailable"
    return CanonicalEvidenceSet(
        (
            CanonicalEvidence(
                identity=ENDPOINT_REACH_TERMINAL_EVIDENCE,
                status=status,
                value=value,
                provenance="test",
                reason=failure_reason,
            ),
        )
    )


def test_endpoint_reach_task_owns_state_capabilities_and_evidence() -> None:
    plugin = ENDPOINT_REACH_TASK_PLUGIN

    assert plugin.identity == VersionedIdentity("endpoint_reach_task", 1)
    assert plugin.lifecycle.initial_state({}) is EndpointReachTaskState.READY
    assert plugin.required_robot_capabilities == frozenset(
        {ENDPOINT_POSE_V1, RESET_INITIAL_STATE_V1}
    )
    assert plugin.produced_evidence == frozenset(
        {ENDPOINT_REACH_TERMINAL_EVIDENCE, ENDPOINT_REACH_TRAJECTORY_EVIDENCE}
    )
    assert plugin.compatible_backend_kinds == frozenset({"mujoco"})


@pytest.mark.parametrize(
    ("classification", "elapsed", "expected"),
    (
        ("running", None, TaskTerminalClassification.RUNNING),
        ("success", 1.25, TaskTerminalClassification.SUCCESS),
        ("failure", 5.0, TaskTerminalClassification.FAILURE),
        (
            "technical_invalid",
            None,
            TaskTerminalClassification.TECHNICAL_INVALID,
        ),
    ),
)
def test_endpoint_reach_task_classifies_closed_terminal_vocabulary(
    classification: str,
    elapsed: float | None,
    expected: TaskTerminalClassification,
) -> None:
    reason = "invalid stream" if classification == "technical_invalid" else None
    assert (
        ENDPOINT_REACH_TASK_PLUGIN.lifecycle.classify_terminal(
            EndpointReachTaskState.RUNNING,
            _terminal(classification, elapsed_time_s=elapsed, reason=reason),
        )
        is expected
    )


def test_endpoint_reach_task_does_not_treat_unavailable_as_success() -> None:
    result = ENDPOINT_REACH_TASK_PLUGIN.lifecycle.classify_terminal(
        EndpointReachTaskState.RUNNING,
        _terminal(
            "success",
            elapsed_time_s=None,
            status=EvidenceStatus.UNAVAILABLE,
        ),
    )
    assert result is TaskTerminalClassification.TECHNICAL_INVALID

    with pytest.raises(ValueError, match="requires elapsed_time_s"):
        ENDPOINT_REACH_TASK_PLUGIN.lifecycle.classify_terminal(
            EndpointReachTaskState.RUNNING,
            _terminal("success", elapsed_time_s=None),
        )
