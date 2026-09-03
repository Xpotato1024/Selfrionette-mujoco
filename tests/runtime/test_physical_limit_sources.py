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
    effective_limit_status,
    make_unknown_limit,
    validate_envelope,
)


def _source(
    *,
    kind: str = "lab_document",
    status: EvidenceStatus = EvidenceStatus.AUTHORITATIVE,
    evidence_reference: str | None = "lab-record-001",
    source_id: str = "fast-arm-limit-sheet",
    revision: str = "rev-1",
) -> LimitSourceProvenance:
    return LimitSourceProvenance(
        source_kind=kind,
        source_id=source_id,
        revision=revision,
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


@pytest.mark.parametrize("authority_asserted", ("false", 1))
def test_source_classification_requires_exact_bool_authority_assertion(
    authority_asserted: object,
) -> None:
    with pytest.raises(TypeError, match="authority_asserted must be bool"):
        classify_source_status(
            source_kind="manufacturer_document",
            evidence_reference="record-1",
            authority_asserted=authority_asserted,  # type: ignore[arg-type]
        )


def test_source_classification_rejects_placeholder_authority_reference() -> None:
    with pytest.raises(ValueError, match="concrete identities"):
        classify_source_status(
            source_kind="manufacturer_document",
            evidence_reference="unknown",
            authority_asserted=True,
        )


def test_source_classification_rejects_synthetic_authority_kind() -> None:
    with pytest.raises(ValueError, match="synthetic"):
        classify_source_status(
            source_kind="fixture",
            evidence_reference="record-1",
            authority_asserted=True,
        )


def test_source_classification_rejects_whitespace_reference() -> None:
    with pytest.raises(ValueError, match="evidence_reference"):
        classify_source_status(
            source_kind="manufacturer_document",
            evidence_reference=" record-1 ",
            authority_asserted=True,
        )


def test_source_kind_must_use_canonical_lowercase_underscore_identity() -> None:
    with pytest.raises(ValueError, match="canonical lowercase underscore"):
        _source(kind="JOINT_LIMIT_TOML")


def test_authoritative_source_rejects_synthetic_source_kind() -> None:
    with pytest.raises(ValueError, match="synthetic"):
        _source(kind="fixture")


def test_authoritative_source_rejects_whitespace_evidence_reference() -> None:
    with pytest.raises(ValueError, match="evidence_reference"):
        _source(evidence_reference=" record-1 ")


@pytest.mark.parametrize("field_name", ("source_id", "revision", "evidence_reference"))
def test_authoritative_source_rejects_placeholder_identity(field_name: str) -> None:
    values: dict[str, object] = {
        "source_id": "fast-arm-limit-sheet",
        "revision": "rev-1",
        "evidence_reference": "lab-record-001",
    }
    values[field_name] = "unknown"

    with pytest.raises(ValueError, match="concrete identities"):
        _source(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("source_kind", ("manufacturer_document", "physical_measurement"))
def test_concrete_physical_authority_remains_valid(source_kind: str) -> None:
    source = _source(kind=source_kind)

    assert source.status is EvidenceStatus.AUTHORITATIVE
    assert source.is_physical_evidence


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


def test_authoritative_limit_requires_authoritative_typed_source() -> None:
    with pytest.raises(ValueError, match="authoritative limit requires authoritative source"):
        _joint_limit(
            status=EvidenceStatus.AUTHORITATIVE,
            source=_source(
                kind="lab_document",
                status=EvidenceStatus.UNKNOWN,
                evidence_reference=None,
            ),
        )


@pytest.mark.parametrize(
    ("limit_status", "source_status", "expected"),
    (
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.PROVISIONAL, EvidenceStatus.PROVISIONAL),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.UNKNOWN, EvidenceStatus.UNKNOWN),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.UNAVAILABLE, EvidenceStatus.UNAVAILABLE),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.CONFLICT, EvidenceStatus.CONFLICT),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.INVALID, EvidenceStatus.INVALID),
        (EvidenceStatus.UNKNOWN, EvidenceStatus.CONFLICT, EvidenceStatus.CONFLICT),
        (EvidenceStatus.CONFLICT, EvidenceStatus.INVALID, EvidenceStatus.INVALID),
    ),
)
def test_effective_status_has_typed_value_source_precedence(
    limit_status: EvidenceStatus,
    source_status: EvidenceStatus,
    expected: EvidenceStatus,
) -> None:
    limit = PhysicalLimit(
        name="joint_1",
        quantity=LimitQuantity.POSITION,
        lower=None
        if limit_status
        in {
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CONFLICT,
            EvidenceStatus.INVALID,
        }
        else -1.0,
        upper=None
        if limit_status
        in {
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CONFLICT,
            EvidenceStatus.INVALID,
        }
        else 1.0,
        unit="rad",
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=limit_status,
        source=_source(
            kind="fixture",
            status=source_status,
            evidence_reference=None,
        ),
        reason=f"{limit_status.value} fixture"
        if limit_status
        in {
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CONFLICT,
            EvidenceStatus.INVALID,
        }
        else None,
    )

    assert effective_limit_status(limit) is expected


@pytest.mark.parametrize(
    "status",
    (
        EvidenceStatus.UNKNOWN,
        EvidenceStatus.UNAVAILABLE,
        EvidenceStatus.CONFLICT,
        EvidenceStatus.INVALID,
    ),
)
def test_unresolved_limit_statuses_are_always_unbounded(
    status: EvidenceStatus,
) -> None:
    limit = PhysicalLimit(
        name="joint_1",
        quantity=LimitQuantity.POSITION,
        lower=None,
        upper=None,
        unit="rad",
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=status,
        source=_source(status=status, evidence_reference=None),
        reason=f"{status.value} source",
    )

    assert not limit.is_bounded
    with pytest.raises(ValueError, match="must not contain bounds"):
        PhysicalLimit(
            name="joint_1",
            quantity=LimitQuantity.POSITION,
            lower=-1.0,
            upper=1.0,
            unit="rad",
            space=LimitSpace.JOINT,
            frame="fast_arm joint space",
            status=status,
            source=_source(status=status, evidence_reference=None),
            reason=f"{status.value} source",
        )


def test_envelope_decoder_rejects_duplicate_json_keys() -> None:
    envelope = PhysicalSafetyEnvelope(
        envelope_id="fixture",
        envelope_version=1,
        robot_id="fast_arm",
        model_id="fast_arm",
        limits=(_joint_limit(),),
    )

    duplicate_root = (
        b'{"schema_version":1,"schema_version":1,'
        b'"envelope_id":"fixture","envelope_version":1,'
        b'"robot_id":"fast_arm","model_id":"fast_arm","limits":[]}'
    )
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        PhysicalSafetyEnvelope.from_json_bytes(duplicate_root)

    raw = envelope.to_json_bytes().decode("utf-8")
    duplicate_nested = raw.replace(
        '"source_kind":"lab_document"',
        '"source_kind":"lab_document","source_kind":"lab_document"',
        1,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        PhysicalSafetyEnvelope.from_json_bytes(duplicate_nested)


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
