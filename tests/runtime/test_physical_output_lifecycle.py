from __future__ import annotations

from dataclasses import replace

import pytest

from selfrionette.runtime.output import (
    PhysicalOutputLifecycle,
    PhysicalOutputLifecycleEvent,
    PhysicalOutputLifecycleTrace,
    PhysicalOutputRecordingSink,
)
from selfrionette.runtime.output.permission import evaluate_physical_output_permission
from selfrionette.schemas import PhysicalOutputPermission

from tests.schemas.test_physical_output_contract import _endpoint_request


def test_default_disabled_and_explicit_arm_are_fail_closed() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    request = _endpoint_request()

    assert lifecycle.state == "disabled"
    rejected = lifecycle.submit(request)
    assert not rejected.accepted
    assert rejected.reason == "lifecycle_state_not_accepting"
    assert lifecycle.state == "disabled"
    repeated = lifecycle.submit(request)
    assert not repeated.accepted
    assert repeated.reason == "duplicate_or_out_of_order_sequence"
    assert lifecycle.trace().events[-1].request_sequence is None

    assert not lifecycle.arm(PhysicalOutputPermission()).accepted
    assert lifecycle.state == "disabled"
    assert lifecycle.arm(PhysicalOutputPermission(mode="dry_run")).accepted
    assert lifecycle.state == "armed"


def test_submit_tracks_latest_state_but_rejects_duplicate_late_and_stale_requests() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    lifecycle.arm(permission)

    accepted = lifecycle.submit(request, now_s=1.0)
    assert accepted.accepted
    assert lifecycle.state == "active"
    assert lifecycle.latest_request == request
    assert lifecycle.last_request_sequence == request.sequence

    duplicate = lifecycle.submit(request, now_s=1.01)
    assert not duplicate.accepted
    assert duplicate.reason == "duplicate_or_out_of_order_sequence"
    assert lifecycle.latest_request == request

    late = lifecycle.submit(replace(request, sequence=3), now_s=1.02)
    assert not late.accepted
    assert late.reason == "duplicate_or_out_of_order_sequence"
    assert lifecycle.latest_request == request
    assert lifecycle.trace().events[-1].request_sequence is None

    stale_request = replace(
        request,
        sequence=5,
        command=replace(request.command, timestamp_s=2.0),
        timestamp_s=2.0,
    )
    stale = lifecycle.submit(stale_request, now_s=3.0, max_age_s=0.5)
    assert not stale.accepted
    assert stale.reason == "physical_output_request_stale"
    assert lifecycle.state == "hold"
    assert lifecycle.latest_request is None
    assert lifecycle.last_request_sequence == stale_request.sequence

    replay = lifecycle.submit(stale_request, now_s=2.1, max_age_s=0.5)
    assert not replay.accepted
    assert replay.reason == "duplicate_or_out_of_order_sequence"


def test_session_mismatch_rejection_is_not_bound_to_current_sequence() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)
    foreign = replace(_endpoint_request(), session_id="session-foreign", sequence=99)

    rejected = lifecycle.submit(foreign, now_s=1.0)
    assert not rejected.accepted
    assert rejected.reason == "session_mismatch"
    assert rejected.event is not None
    assert rejected.event.request_sequence is None

    accepted = lifecycle.submit(_endpoint_request(), now_s=1.0)
    assert accepted.accepted
    assert lifecycle.trace().events[-1].request_sequence == 4


def test_reconnect_does_not_rearm_and_explicit_rearm_keeps_stale_commands_out() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    lifecycle.arm(permission)
    lifecycle.submit(request, now_s=1.0)
    lifecycle.source_disconnected(timestamp_s=2.0)

    reconnect = lifecycle.reconnect(timestamp_s=3.0)
    assert reconnect.state_before == "hold"
    assert reconnect.state_after == "hold"
    assert lifecycle.state == "hold"
    assert not lifecycle.submit(replace(request, sequence=5), now_s=3.1).accepted

    assert lifecycle.arm(permission).accepted
    assert lifecycle.state == "armed"
    next_request = replace(
        request,
        sequence=6,
        command=replace(request.command, timestamp_s=3.2),
        timestamp_s=3.2,
    )
    assert lifecycle.submit(next_request, now_s=3.2).accepted


def test_stop_is_idempotent_and_bounded() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1", shutdown_timeout_s=1.0)
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)
    lifecycle.submit(_endpoint_request(), now_s=1.0)

    stopping = lifecycle.operator_stop(now_s=2.0)
    assert stopping.accepted
    assert lifecycle.state == "stopping"
    assert lifecycle.stop_deadline_s == 3.0
    assert lifecycle.latest_request is None

    repeated = lifecycle.operator_stop(now_s=2.5)
    assert repeated.accepted
    assert repeated.reason is None
    assert lifecycle.state == "stopping"

    stopped = lifecycle.complete_stop(now_s=2.9)
    assert stopped.accepted
    assert lifecycle.state == "stopped"
    assert lifecycle.stop_deadline_s is None
    assert lifecycle.complete_stop(now_s=3.0).accepted
    assert lifecycle.state == "stopped"

    timed_out = PhysicalOutputLifecycle("session-timeout", shutdown_timeout_s=1.0)
    timed_out.arm(permission)
    timed_out.submit(_endpoint_request(), now_s=0.0)
    timed_out.operator_stop(now_s=0.0)
    exceeded = timed_out.complete_stop(now_s=1.1)
    assert not exceeded.accepted
    assert exceeded.reason == "bounded_shutdown_deadline_exceeded"
    assert timed_out.state == "failed"
    assert timed_out.stop_deadline_s is None


def test_source_invalid_aborts_and_new_session_is_required_after_terminal_state() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)
    lifecycle.submit(_endpoint_request(), now_s=1.0)

    invalid = lifecycle.source_invalid("source_payload_invalid", timestamp_s=2.0)
    assert not invalid.accepted
    assert invalid.reason == "source_payload_invalid"
    assert lifecycle.state == "aborted"
    assert lifecycle.latest_request is None
    assert lifecycle.reconnect(timestamp_s=3.0).state_after == "aborted"
    assert not lifecycle.arm(permission).accepted
    assert lifecycle.arm(permission, session_id="session-2").accepted
    assert lifecycle.session_id == "session-2"
    assert lifecycle.state == "armed"
    assert lifecycle.trace().events[-1].session_id == "session-2"


def test_cleanup_failure_does_not_hide_primary_failure() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"))
    lifecycle.submit(_endpoint_request(), now_s=1.0)

    def cleanup() -> None:
        raise RuntimeError("cleanup broke")

    result = lifecycle.shutdown(
        now_s=2.0,
        cleanup=cleanup,
        primary_failure="primary_output_failure",
    )
    assert result.accepted
    assert lifecycle.state == "failed"
    assert lifecycle.events[2].event_kind == "failure"
    assert lifecycle.events[2].reason == "primary_output_failure"
    assert lifecycle.events[-1].event_kind == "cleanup_failure"
    assert lifecycle.events[-1].state_after == "failed"
    assert lifecycle.events[-1].reason == "cleanup_failed:RuntimeError"


def test_dry_run_sink_captures_lifecycle_trace_separately_from_output_trace() -> None:
    sink = PhysicalOutputRecordingSink()
    lifecycle = PhysicalOutputLifecycle("session-1", sink=sink)
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    lifecycle.arm(permission)
    decision = evaluate_physical_output_permission(request, permission)
    lifecycle.submit(request, now_s=1.0)
    sink.record_requested(request, permission)
    sink.record_permission_decision(decision)
    lifecycle.source_stale(timestamp_s=2.0)

    assert sink.events[0].event_kind == "requested"
    assert sink.events[1].event_kind == "permitted"
    assert len(sink.lifecycle_events) == len(lifecycle.events)
    lifecycle_trace = PhysicalOutputLifecycleTrace.from_jsonl(
        sink.lifecycle_trace_bytes()
    )
    assert lifecycle_trace.events == lifecycle.events
    assert lifecycle_trace.events[-1].state_after == "hold"


def test_lifecycle_trace_rejects_duplicate_and_out_of_order_artifacts() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"), timestamp_s=0.0)
    encoded = lifecycle.trace().to_jsonl_bytes()
    duplicate = encoded[:-2] + b',"event_sequence":0}\n'
    with pytest.raises(ValueError, match="duplicate field"):
        PhysicalOutputLifecycleTrace.from_jsonl(duplicate)

    event_lines = encoded.splitlines()
    reordered = b"\n".join((event_lines[0].replace(b'"event_sequence":0', b'"event_sequence":1', 1), event_lines[0])) + b"\n"
    with pytest.raises(ValueError, match="contiguous"):
        PhysicalOutputLifecycleTrace.from_jsonl(reordered)


def test_lifecycle_event_rejects_impossible_state_transition() -> None:
    with pytest.raises(ValueError, match="reconnect event"):
        PhysicalOutputLifecycleTrace(
            events=(
                # Direct construction exercises the typed transition guard.
                PhysicalOutputLifecycleEvent(
                    event_sequence=0,
                    event_kind="reconnect",
                    session_id="session-1",
                    state_before="disabled",
                    state_after="armed",
                ),
            )
        )

    lifecycle = PhysicalOutputLifecycle("session-1")
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"))
    lifecycle.source_invalid("invalid", timestamp_s=1.0)
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"), session_id="session-2")
    with pytest.raises(ValueError, match="session may change"):
        PhysicalOutputLifecycleTrace(
            events=(
                replace(lifecycle.events[0], session_id="session-2"),
                *lifecycle.events[1:],
            )
        )
