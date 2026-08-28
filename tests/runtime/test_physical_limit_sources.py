from __future__ import annotations

import json

import pytest

from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    LimitConversionProvenance,
    LimitQuantity,
    LimitSourceProvenance,
    LimitSpace,
    PhysicalLimit,
    PhysicalSafetyEnvelope,
    classify_source_status,
    make_unknown_limit,
    validate_envelope,
)


def _source(
    *,
    kind: str = "lab_document",
    status: EvidenceStatus = EvidenceStatus.AUTHORITATIVE,
    evidence_reference: str | None = "lab-record-001",
) -> LimitSourceProvenance:
    return LimitSourceProvenance(
        source_kind=kind,
        source_id="fast-arm-limit-sheet",
        revision="rev-1",
        status=status,
        evidence_reference=evidence_reference,
    )


def _joint_limit(
    *,
    status: EvidenceStatus = EvidenceStatus.AUTHORITATIVE,
    source: LimitSourceProvenance | None = None,
    lower: float | None = -1.0,
    upper: float | None = 1.0,
) -> PhysicalLimit:
    return PhysicalLimit(
        name="joint_1",
        quantity=LimitQuantity.POSITION,
        lower=lower,
        upper=upper,
        unit="rad",
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=status,
        source=source or _source(status=status),
        conversion=LimitConversionProvenance.identity(LimitSpace.JOINT),
    )


def test_authoritative_limit_requires_explicit_physical_provenance() -> None:
    limit = _joint_limit()

    assert limit.is_authoritative
    assert limit.source.is_physical_evidence
    assert limit.conversion is not None
    assert limit.conversion.method == "identity"


def test_software_sources_cannot_be_marked_authoritative() -> None:
    with pytest.raises(ValueError, match="software-only"):
        _source(kind="joint_limit_toml")


def test_missing_physical_source_is_typed_unknown_and_not_bounded() -> None:
    limit = make_unknown_limit(
        name="elbow_joint",
        quantity=LimitQuantity.POSITION,
        space=LimitSpace.JOINT,
        unit="rad",
        frame="fast_arm joint space",
        reason="manufacturer range has not been supplied",
    )

    assert limit.status is EvidenceStatus.UNKNOWN
    assert not limit.is_bounded
    assert not limit.is_authoritative


def test_envelope_serialization_is_deterministic_and_round_trips() -> None:
    envelope = PhysicalSafetyEnvelope(
        envelope_id="fast_arm_physical_limits",
        envelope_version=1,
        robot_id="fast_arm",
        model_id="fast_arm",
        limits=(_joint_limit(),),
        source_summary="explicit lab evidence fixture",
    )

    encoded = envelope.to_json_bytes()
    assert encoded == envelope.to_json_bytes()
    assert not encoded.startswith(b"\xef\xbb\xbf")
    assert PhysicalSafetyEnvelope.from_json_bytes(encoded) == envelope
    assert validate_envelope(envelope) is envelope


def test_envelope_rejects_unknown_fields_and_bom() -> None:
    envelope = PhysicalSafetyEnvelope(
        envelope_id="fixture",
        envelope_version=1,
        robot_id="fast_arm",
        model_id="fast_arm",
        limits=(_joint_limit(),),
    )
    raw = json.loads(envelope.to_json_bytes())
    raw["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        PhysicalSafetyEnvelope.from_json_bytes(
            json.dumps(raw, separators=(",", ":")).encode("utf-8")
        )
    with pytest.raises(ValueError, match="BOM"):
        PhysicalSafetyEnvelope.from_json_bytes(b"\xef\xbb\xbf" + envelope.to_json_bytes())


def test_invalid_and_conflicting_values_do_not_become_authoritative() -> None:
    with pytest.raises(ValueError, match="finite"):
        PhysicalLimit(
            name="joint_1",
            quantity=LimitQuantity.POSITION,
            lower=float("nan"),
            upper=1.0,
            unit="rad",
            space=LimitSpace.JOINT,
            frame="fast_arm joint space",
            status=EvidenceStatus.INVALID,
            source=_source(status=EvidenceStatus.INVALID, evidence_reference=None),
            reason="source values were inconsistent",
        )

    conflict = PhysicalLimit(
        name="joint_1",
        quantity=LimitQuantity.POSITION,
        lower=None,
        upper=None,
        unit="rad",
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=EvidenceStatus.CONFLICT,
        source=_source(status=EvidenceStatus.CONFLICT, evidence_reference=None),
        reason="two revisions disagree",
    )
    assert not conflict.is_authoritative


@pytest.mark.parametrize(
    ("kind", "evidence_reference", "authority_asserted", "expected"),
    (
        ("joint_limit_toml", "record", True, EvidenceStatus.PROVISIONAL),
        ("manufacturer_document", "record", True, EvidenceStatus.AUTHORITATIVE),
        ("lab_document", None, True, EvidenceStatus.UNKNOWN),
        ("controller_setting", None, False, EvidenceStatus.PROVISIONAL),
    ),
)
def test_source_classification_is_explicit_and_fail_closed(
    kind: str,
    evidence_reference: str | None,
    authority_asserted: bool,
    expected: EvidenceStatus,
) -> None:
    assert (
        classify_source_status(
            source_kind=kind,
            evidence_reference=evidence_reference,
            authority_asserted=authority_asserted,
        )
        is expected
    )
