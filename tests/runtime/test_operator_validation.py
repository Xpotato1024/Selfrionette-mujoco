from __future__ import annotations

import json

import pytest

from selfrionette.runtime.safety.operator_validation import (
    ClearanceDeclaration,
    EvidenceClass,
    MeasurementSource,
    MeasurementSourceKind,
    OperatorIdentity,
    PreflightChecklist,
    PreflightItem,
    RollbackProcedure,
    SafetyDecisionEvidence,
    StopProcedure,
    TargetIdentity,
    ValidationCheckEvidence,
    ValidationCheckKind,
    ValidationCheckSpec,
    ValidationCheckStatus,
    ValidationClassification,
    ValidationProcedure,
    build_dry_run_validation_artifact,
    build_validation_artifact,
    decode_validation_artifact,
    validate_operator_gate,
    validate_validation_artifact,
)
from selfrionette.runtime.safety.physical_safety_core import SafetyDecisionAction


STARTED = "2026-08-28T10:00:00Z"
OBSERVED = "2026-08-28T10:00:01Z"
COMPLETED = "2026-08-28T10:00:02Z"


def _procedure(
    *,
    operator_confirmed: bool = True,
    preflight_complete: bool = True,
    verified_clearance_m: float | None = 1.0,
    clearance_verified_at: str | None = OBSERVED,
    acknowledged_by: str = "operator-001",
) -> ValidationProcedure:
    return ValidationProcedure(
        procedure_id="procedure-001",
        target=TargetIdentity("target-001", "fast-arm", "controller-001", "connection-001", "model-001"),
        operator=OperatorIdentity("operator-001", "safety-operator"),
        software_revision="revision-001",
        created_at=STARTED,
        preflight=PreflightChecklist(
            (
                PreflightItem("power-isolated", "power isolation was checked", preflight_complete),
                PreflightItem("workspace-clear", "workspace clearance was checked", preflight_complete),
            ),
            acknowledged_by,
            OBSERVED,
        ),
        clearance=ClearanceDeclaration(
            0.5,
            verified_clearance_m,
            MeasurementSource(MeasurementSourceKind.SOFTWARE_DRY_RUN, "fixture", "revision-001"),
            clearance_verified_at,
        ),
        stop=StopProcedure(("stop command",), ("emergency stop",)),
        rollback=RollbackProcedure(("restore neutral state",), "neutral-home"),
        required_checks=(
            ValidationCheckSpec("limits", ValidationCheckKind.LIMIT_RANGE, "range check"),
            ValidationCheckSpec("collision", ValidationCheckKind.COLLISION_CLEARANCE, "clearance check"),
            ValidationCheckSpec("trajectory", ValidationCheckKind.TRAJECTORY_FEASIBILITY, "bounded trajectory check"),
            ValidationCheckSpec("stop", ValidationCheckKind.STOP_PROCEDURE, "stop check"),
            ValidationCheckSpec("rollback", ValidationCheckKind.ROLLBACK_PROCEDURE, "rollback check"),
        ),
        operator_confirmed=operator_confirmed,
    )


def _check(
    check_id: str,
    kind: ValidationCheckKind,
    *,
    status: ValidationCheckStatus = ValidationCheckStatus.PASS,
    action: SafetyDecisionAction = SafetyDecisionAction.ALLOW,
    source: MeasurementSource | None = None,
    software_revision: str = "revision-001",
) -> ValidationCheckEvidence:
    return ValidationCheckEvidence(
        check_id=check_id,
        kind=kind,
        status=status,
        expected={"expected": "fixture-value"},
        observed=None if status in {ValidationCheckStatus.UNAVAILABLE, ValidationCheckStatus.TECHNICAL_INVALID} else {"observed": "fixture-value"},
        measurement_source=source or MeasurementSource(MeasurementSourceKind.SOFTWARE_DRY_RUN, "fixture", "revision-001"),
        observed_at=None if status in {ValidationCheckStatus.UNAVAILABLE, ValidationCheckStatus.TECHNICAL_INVALID} else OBSERVED,
        software_revision=software_revision,
        safety_decision=SafetyDecisionEvidence(action, f"fixture:{action.value}", ("fixture",)),
        reason="fixture check",
    )


def _all_checks(**kwargs: object) -> tuple[ValidationCheckEvidence, ...]:
    return (
        _check("limits", ValidationCheckKind.LIMIT_RANGE, **kwargs),
        _check("collision", ValidationCheckKind.COLLISION_CLEARANCE, **kwargs),
        _check("trajectory", ValidationCheckKind.TRAJECTORY_FEASIBILITY, **kwargs),
        _check("stop", ValidationCheckKind.STOP_PROCEDURE, **kwargs),
        _check("rollback", ValidationCheckKind.ROLLBACK_PROCEDURE, **kwargs),
    )


def test_operator_gate_requires_confirmation_preflight_clearance_stop_and_rollback() -> None:
    procedure = _procedure()
    gate = validate_operator_gate(procedure)
    assert gate.classification is ValidationClassification.PASS
    assert gate.reason_code == "operator_gate_ready"

    assert validate_operator_gate(_procedure(operator_confirmed=False)).reason_code == "operator_confirmation_required"
    assert validate_operator_gate(_procedure(preflight_complete=False)).reason_code == "preflight_incomplete"
    assert validate_operator_gate(_procedure(verified_clearance_m=None, clearance_verified_at=None)).reason_code == "clearance_verification_unavailable"
    assert validate_operator_gate(_procedure(verified_clearance_m=0.1)).classification is ValidationClassification.FAIL
    assert validate_operator_gate(_procedure(acknowledged_by="other-operator")).reason_code == "preflight_operator_mismatch"


def test_dry_run_artifact_round_trips_and_marks_software_evidence() -> None:
    artifact = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks(),
        artifact_id="artifact-001",
        started_at=STARTED,
        completed_at=COMPLETED,
    )

    encoded = artifact.to_json_bytes()
    assert artifact.classification is ValidationClassification.PASS
    assert artifact.evidence_class is EvidenceClass.SOFTWARE_ONLY
    assert not artifact.physical_evidence_present
    assert not encoded.startswith(b"\xef\xbb\xbf")
    assert validate_validation_artifact(artifact).to_json_bytes() == encoded
    assert decode_validation_artifact(encoded).to_json_bytes() == encoded


def test_failure_unavailable_aborted_and_technical_invalid_never_become_pass() -> None:
    failed = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks(status=ValidationCheckStatus.FAIL, action=SafetyDecisionAction.REJECT),
        artifact_id="artifact-fail",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert failed.classification is ValidationClassification.FAIL

    incomplete = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks()[:-1],
        artifact_id="artifact-incomplete",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert incomplete.classification is ValidationClassification.UNAVAILABLE
    assert not incomplete.complete

    aborted = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks()[:-1],
        artifact_id="artifact-aborted",
        started_at=STARTED,
        completed_at=COMPLETED,
        operator_aborted=True,
    )
    assert aborted.classification is ValidationClassification.ABORTED

    technical = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks(status=ValidationCheckStatus.TECHNICAL_INVALID, action=SafetyDecisionAction.INVALID),
        artifact_id="artifact-technical",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert technical.classification is ValidationClassification.TECHNICAL_INVALID


def test_source_revision_and_kind_identity_are_strict() -> None:
    revision_mismatch = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks(software_revision="revision-other"),
        artifact_id="artifact-revision",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert revision_mismatch.classification is ValidationClassification.TECHNICAL_INVALID

    wrong_kind = list(_all_checks())
    wrong_kind[0] = _check("limits", ValidationCheckKind.COLLISION_CLEARANCE)
    kind_mismatch = build_dry_run_validation_artifact(
        _procedure(),
        tuple(wrong_kind),
        artifact_id="artifact-kind",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert kind_mismatch.classification is ValidationClassification.TECHNICAL_INVALID

    unknown_source = _all_checks(source=MeasurementSource(MeasurementSourceKind.UNKNOWN, "unknown", "unknown"))
    unavailable = build_dry_run_validation_artifact(
        _procedure(),
        unknown_source,
        artifact_id="artifact-source",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert unavailable.classification is ValidationClassification.UNAVAILABLE
    assert unavailable.evidence_class is EvidenceClass.UNKNOWN


def test_physical_source_is_visible_and_not_collapsed_into_software() -> None:
    source = MeasurementSource(MeasurementSourceKind.PHYSICAL_MEASUREMENT, "sensor-001", "run-001", "obs-001")
    artifact = build_validation_artifact(
        _procedure(),
        _all_checks(source=source),
        artifact_id="artifact-physical",
        started_at=STARTED,
        completed_at=COMPLETED,
    )

    assert artifact.classification is ValidationClassification.PASS
    assert artifact.evidence_class is EvidenceClass.PHYSICAL_ONLY
    assert artifact.physical_evidence_present

    document_source = MeasurementSource(MeasurementSourceKind.MANUFACTURER_DOCUMENT, "manual-001", "rev-001", "page-12")
    document_artifact = build_validation_artifact(
        _procedure(),
        _all_checks(source=document_source),
        artifact_id="artifact-document",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    assert document_artifact.evidence_class is EvidenceClass.PHYSICAL_ONLY
    with pytest.raises(ValueError, match="evidence_reference"):
        MeasurementSource(MeasurementSourceKind.MANUFACTURER_DOCUMENT, "manual-001", "rev-001")


def test_strict_decoder_rejects_unknown_duplicate_bom_and_nonfinite_values() -> None:
    artifact = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks(),
        artifact_id="artifact-strict",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    document = artifact.to_dict()

    unknown = dict(document)
    unknown["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        decode_validation_artifact(unknown)

    duplicate = artifact.to_json_bytes().decode("utf-8").replace('"artifact_id":"artifact-strict"', '"artifact_id":"artifact-strict","artifact_id":"duplicate"', 1)
    with pytest.raises(ValueError, match="duplicate JSON field"):
        decode_validation_artifact(duplicate)

    with pytest.raises(ValueError, match="BOM"):
        decode_validation_artifact(b"\xef\xbb\xbf" + artifact.to_json_bytes())

    nonfinite = json.loads(artifact.to_json_bytes().decode("utf-8"))
    nonfinite["checks"][0]["expected"]["value"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        decode_validation_artifact(nonfinite)


def test_check_contract_requires_status_specific_safety_action_and_observation() -> None:
    source = MeasurementSource(MeasurementSourceKind.SOFTWARE_DRY_RUN, "fixture", "revision-001")
    with pytest.raises(ValueError, match="observed_at"):
        ValidationCheckEvidence(
            "check",
            ValidationCheckKind.LIMIT_RANGE,
            ValidationCheckStatus.PASS,
            {"expected": 1},
            {"observed": 1},
            source,
            None,
            "revision-001",
            SafetyDecisionEvidence(SafetyDecisionAction.ALLOW, "fixture:allow", ("fixture",)),
            "missing timestamp",
        )

    with pytest.raises(ValueError, match="unavailable safety decision"):
        _check("check", ValidationCheckKind.LIMIT_RANGE, status=ValidationCheckStatus.UNAVAILABLE, action=SafetyDecisionAction.HOLD)


def test_artifact_lifecycle_rejects_reversed_timestamps_and_boolean_schema_version() -> None:
    artifact = build_dry_run_validation_artifact(
        _procedure(),
        _all_checks(),
        artifact_id="artifact-lifecycle",
        started_at=STARTED,
        completed_at=COMPLETED,
    )
    with pytest.raises(ValueError, match="completed_at must not precede started_at"):
        build_dry_run_validation_artifact(
            _procedure(),
            _all_checks(),
            artifact_id="artifact-reversed",
            started_at=COMPLETED,
            completed_at=STARTED,
        )

    malformed = artifact.to_dict()
    malformed["schema_version"] = True
    with pytest.raises(ValueError, match="schema version"):
        decode_validation_artifact(malformed)
