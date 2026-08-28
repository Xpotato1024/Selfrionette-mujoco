from __future__ import annotations

import json

import pytest

from selfrionette.runtime.output import (
    PhysicalOutputRecordingSink,
    PhysicalOutputTrace,
    physical_output_traces_equivalent,
    replay_physical_output_trace,
)
from selfrionette.runtime.output.permission import evaluate_physical_output_permission
from selfrionette.schemas import PhysicalOutputPermission

from tests.schemas.test_physical_output_contract import _endpoint_request


def test_recording_sink_keeps_request_permission_and_drop_evidence_separate() -> None:
    request = _endpoint_request()
    permission = PhysicalOutputPermission(mode="dry_run")
    decision = evaluate_physical_output_permission(request, permission)
    sink = PhysicalOutputRecordingSink()

    requested = sink.record_requested(request, permission)
    permitted = sink.record_permission_decision(decision)
    dropped = sink.record_dropped(
        request,
        permission,
        reason="recording_sink_closed",
    )

    assert [event.event_kind for event in sink.events] == [
        "requested",
        "permitted",
        "dropped",
    ]
    assert requested.request_bytes == request.to_json_bytes()
    assert permitted.permission_bytes == permission.to_json_bytes()
    assert dropped.reason == "recording_sink_closed"
    assert all(event.request == request for event in sink.events)
    assert all(event.request.sequence == 4 for event in sink.events)


def test_trace_jsonl_is_deterministic_and_replays_byte_equivalently(tmp_path) -> None:
    request = _endpoint_request()
    permission = PhysicalOutputPermission(mode="dry_run")
    sink = PhysicalOutputRecordingSink()
    sink.record_requested(request, permission)
    sink.record_permission_decision(
        evaluate_physical_output_permission(request, permission)
    )
    trace = sink.snapshot()
    encoded = trace.to_jsonl_bytes()

    assert encoded == trace.to_jsonl_bytes()
    assert encoded.endswith(b"\n")
    assert b"\xef\xbb\xbf" not in encoded
    assert replay_physical_output_trace(encoded).to_jsonl_bytes() == encoded
    assert physical_output_traces_equivalent(trace, encoded)

    path = trace.write_atomic(tmp_path / "physical-output.jsonl")
    assert PhysicalOutputTrace.read_strict(path) == trace
    assert path.read_bytes() == encoded


def test_trace_rejects_duplicate_unknown_and_noncanonical_fields() -> None:
    request = _endpoint_request()
    permission = PhysicalOutputPermission(mode="dry_run")
    sink = PhysicalOutputRecordingSink()
    sink.record_requested(request, permission)
    encoded = sink.to_jsonl_bytes()
    event = json.loads(encoded)

    unknown = dict(event)
    unknown["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        PhysicalOutputTrace.from_jsonl(
            json.dumps(unknown, separators=(",", ":")).encode("utf-8") + b"\n"
        )

    duplicate = encoded[:-2] + b',"event_sequence":0}\n'
    with pytest.raises(ValueError, match="duplicate field"):
        PhysicalOutputTrace.from_jsonl(duplicate)

    noncanonical = encoded.replace(b'"requested"', b'"requested"', 1)
    noncanonical = noncanonical.replace(b"\n", b"\n\n", 1)
    with pytest.raises(ValueError, match="blank lines"):
        PhysicalOutputTrace.from_jsonl(noncanonical)


def test_trace_rejects_duplicate_and_out_of_order_events() -> None:
    request = _endpoint_request()
    permission = PhysicalOutputPermission(mode="dry_run")
    sink = PhysicalOutputRecordingSink()
    sink.record_requested(request, permission)
    sink.record_permission_decision(
        evaluate_physical_output_permission(request, permission)
    )
    event_lines = sink.to_jsonl_bytes().splitlines()

    duplicate = event_lines[0].replace(
        b'"event_sequence":0', b'"event_sequence":2', 1
    )
    with pytest.raises(ValueError, match="contiguous"):
        PhysicalOutputTrace.from_jsonl(b"\n".join((event_lines[0], duplicate)) + b"\n")

    out_of_order = b"\n".join((event_lines[1], event_lines[0])) + b"\n"
    with pytest.raises(ValueError, match="requested predecessor|contiguous"):
        PhysicalOutputTrace.from_jsonl(out_of_order)


def test_rejected_decision_is_recorded_without_sent_or_acknowledged_claim() -> None:
    request = _endpoint_request()
    permission = PhysicalOutputPermission()
    sink = PhysicalOutputRecordingSink()
    sink.record_requested(request, permission)
    decision = evaluate_physical_output_permission(request, permission)
    event = sink.record_permission_decision(decision)

    assert event.event_kind == "rejected"
    assert event.decision_status == "rejected"
    assert event.reason == "physical_output_disabled"
    assert not hasattr(event, "sent")
    assert not hasattr(event, "acknowledged")
