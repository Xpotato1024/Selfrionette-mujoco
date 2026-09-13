from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from selfrionette.runtime.output.safety_gate import (
    PhysicalOutputSafetyEvaluation,
    PhysicalOutputSafetyTraceEvidence,
    PhysicalOutputSendableRequest,
    evaluate_and_bind_physical_output_safety,
    validate_physical_output_sendable_request,
)
from selfrionette.runtime.safety.limit_resolution import LimitResolutionStatus
from selfrionette.runtime.safety.physical_safety_core import evaluate_physical_safety
from selfrionette.schemas import PhysicalOutputRequest

from tests.runtime.test_physical_safety_core import _input
from tests.schemas.test_physical_output_contract import _endpoint_request


def _request(**changes: object) -> PhysicalOutputRequest:
    request = replace(_endpoint_request(), target_robot_id="fixture-robot")
    return replace(request, **changes) if changes else request


def _safety_input(request: PhysicalOutputRequest, *, limits=LimitResolutionStatus.RESOLVED_AUTHORITATIVE):
    safety_input = _input(limits=limits)
    return replace(
        safety_input,
        provenance=(*safety_input.provenance, f"software_revision:{request.software_revision}"),
    )


def test_allow_binding_hashes_canonical_request_and_typed_safety_content() -> None:
    request = _request()
    safety_input = _safety_input(request)
    evaluation = evaluate_and_bind_physical_output_safety(
        request,
        safety_input,
        checked_at_s=request.timestamp_s,
    )

    assert evaluation.status == "allowed"
    assert evaluation.sendable
    assert evaluation.request_sha256 == sha256(request.to_json_bytes()).hexdigest()
    assert evaluation.safety_input_sha256
    assert evaluation.decision_sha256
    sendable = evaluation.to_sendable_request()
    assert isinstance(sendable, PhysicalOutputSendableRequest)
    assert validate_physical_output_sendable_request(sendable) is sendable
    assert sendable.request == request

    evidence = evaluation.to_trace_evidence()
    assert PhysicalOutputSafetyTraceEvidence.from_json_value(evidence.to_json_value()) == evidence
    assert evidence.gate_status == "allowed"
    assert evidence.candidate_id == safety_input.candidate_id
    assert evidence.safety_input_sha256 == evaluation.safety_input_sha256
    assert evidence.decision_sha256 == evaluation.decision_sha256

    changed_request = replace(
        request,
        sequence=request.sequence + 1,
        timestamp_s=request.timestamp_s + 0.1,
        command=replace(request.command, timestamp_s=request.timestamp_s + 0.1),
    )
    changed_request_evaluation = evaluate_and_bind_physical_output_safety(
        changed_request,
        safety_input,
        checked_at_s=changed_request.timestamp_s,
    )
    assert changed_request_evaluation.request_sha256 != evaluation.request_sha256
    assert changed_request_evaluation.binding_sha256 != evaluation.binding_sha256

    changed_safety_input = _safety_input(
        request,
        limits=LimitResolutionStatus.RESOLVED_PROVISIONAL,
    )
    changed_safety_evaluation = evaluate_and_bind_physical_output_safety(
        request,
        changed_safety_input,
        checked_at_s=request.timestamp_s,
    )
    assert changed_safety_input.candidate_id == safety_input.candidate_id
    assert changed_safety_evaluation.safety_input_sha256 != evaluation.safety_input_sha256
    assert changed_safety_evaluation.binding_sha256 != evaluation.binding_sha256


def test_nonallow_decision_cannot_create_sendable_request() -> None:
    request = _request()
    safety_input = _safety_input(request, limits=LimitResolutionStatus.RESOLVED_PROVISIONAL)
    evaluation = evaluate_and_bind_physical_output_safety(
        request,
        safety_input,
        checked_at_s=request.timestamp_s,
    )

    assert evaluation.status == "held"
    assert not evaluation.sendable
    with pytest.raises(ValueError, match="explicit safety allow"):
        evaluation.to_sendable_request()
    with pytest.raises(ValueError, match="explicit P5 allow"):
        PhysicalOutputSendableRequest(evaluation)


def test_binding_rejects_robot_and_revision_mismatch() -> None:
    request = _request()
    base = _safety_input(request)
    wrong_robot = "other-fixture-robot"
    wrong_robot_input = replace(
        base,
        limit_resolution=replace(base.limit_resolution, robot_id=wrong_robot),
        collision=replace(
            base.collision,
            context=replace(base.collision.context, robot_id=wrong_robot),
        ),
    )
    wrong_robot = evaluate_and_bind_physical_output_safety(
        request,
        wrong_robot_input,
        checked_at_s=request.timestamp_s,
    )
    assert wrong_robot.status == "rejected"
    assert wrong_robot.reason == "physical_safety_target_robot_mismatch"
    assert not wrong_robot.sendable

    no_revision_input = replace(
        base,
        provenance=tuple(
            item for item in base.provenance if not item.startswith("software_revision:")
        ),
    )
    wrong_revision = evaluate_and_bind_physical_output_safety(
        request,
        no_revision_input,
        checked_at_s=request.timestamp_s,
    )
    assert wrong_revision.status == "rejected"
    assert wrong_revision.reason == "physical_safety_software_revision_mismatch"
    assert not wrong_revision.sendable


def test_binding_rejects_a_valid_decision_from_another_safety_input() -> None:
    request = _request()
    safety_input = _safety_input(request)
    unrelated_input = _safety_input(
        request,
        limits=LimitResolutionStatus.MISMATCH,
    )
    evaluation = PhysicalOutputSafetyEvaluation(
        request=request,
        safety_input=safety_input,
        decision=evaluate_physical_safety(unrelated_input),
        checked_at_s=request.timestamp_s,
    )

    assert evaluation.status == "invalid"
    assert evaluation.reason == "physical_safety_decision_mismatch"
    assert not evaluation.sendable
