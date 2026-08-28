from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from math import inf, nan
from threading import Barrier

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
    assert repeated.reason == "lifecycle_state_not_accepting"
    assert lifecycle.trace().events[-1].request_sequence is None

    assert not lifecycle.arm(PhysicalOutputPermission()).accepted
    assert lifecycle.state == "disabled"
    assert lifecycle.arm(PhysicalOutputPermission(mode="dry_run")).accepted
    assert lifecycle.state == "armed"
    assert lifecycle.submit(request, now_s=1.0, max_age_s=1.0).accepted


def test_submit_tracks_latest_state_but_rejects_duplicate_late_and_stale_requests() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    lifecycle.arm(permission)

    accepted = lifecycle.submit(request, now_s=1.0, max_age_s=1.0)
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

    accepted = lifecycle.submit(_endpoint_request(), now_s=1.0, max_age_s=1.0)
    assert accepted.accepted
    assert lifecycle.trace().events[-1].request_sequence == 4


def test_reconnect_does_not_rearm_and_explicit_rearm_keeps_stale_commands_out() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    lifecycle.arm(permission)
    lifecycle.submit(request, now_s=1.0, max_age_s=1.0)
    lifecycle.source_disconnected(timestamp_s=2.0)

    reconnect = lifecycle.reconnect(timestamp_s=3.0)
    assert reconnect.state_before == "hold"
    assert reconnect.state_after == "hold"
    assert lifecycle.state == "hold"
    assert not lifecycle.submit(replace(request, sequence=5), now_s=3.1).accepted

    assert lifecycle.arm(permission, session_id="session-2").accepted
    assert lifecycle.state == "armed"
    next_request = replace(
        request,
        session_id="session-2",
        sequence=6,
        command=replace(request.command, timestamp_s=3.2),
        timestamp_s=3.2,
    )
    assert lifecycle.submit(next_request, now_s=3.2, max_age_s=1.0).accepted


def test_stop_is_idempotent_and_bounded() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1", shutdown_timeout_s=1.0)
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)
    lifecycle.submit(_endpoint_request(), now_s=1.0, max_age_s=1.0)

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
    timed_out.submit(_endpoint_request(), now_s=0.0, max_age_s=1.0)
    timed_out.operator_stop(now_s=0.0)
    exceeded = timed_out.complete_stop(now_s=1.1)
    assert not exceeded.accepted
    assert exceeded.reason == "bounded_shutdown_deadline_exceeded"
    assert timed_out.state == "failed"
    assert timed_out.stop_deadline_s is None


def test_complete_stop_rejects_timestamp_before_stop_start_without_mutation() -> None:
    lifecycle = PhysicalOutputLifecycle("session-order", shutdown_timeout_s=2.0)
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"))
    lifecycle.operator_stop(now_s=10.0)
    before_events = lifecycle.events

    result = lifecycle.complete_stop(now_s=9.0)

    assert not result.accepted
    assert result.reason == "stop_completion_before_start"
    assert lifecycle.state == "stopping"
    assert lifecycle.stop_started_s == 10.0
    assert lifecycle.stop_deadline_s == 12.0
    assert lifecycle.events == before_events


@pytest.mark.parametrize("timestamp", (nan, inf, -inf))
@pytest.mark.parametrize(
    "operation",
    ("arm", "submit", "source_stale", "source_invalid", "abort", "fail", "cleanup", "reconnect"),
)
def test_non_finite_transition_timestamp_cannot_partially_commit(
    timestamp: float,
    operation: str,
) -> None:
    lifecycle = PhysicalOutputLifecycle("session-timestamp")
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    if operation != "arm":
        lifecycle.arm(permission)
    if operation in {"submit", "source_stale", "source_invalid", "abort", "fail", "cleanup", "reconnect"}:
        if operation != "submit":
            lifecycle.submit(request, now_s=1.0, max_age_s=1.0)
    before = (
        lifecycle.state,
        lifecycle.permission,
        lifecycle.session_id,
        lifecycle.latest_request,
        lifecycle.last_request_sequence,
        lifecycle.stop_started_s,
        lifecycle.stop_deadline_s,
        lifecycle.events,
    )

    with pytest.raises(ValueError, match="finite"):
        if operation == "arm":
            lifecycle.arm(permission, timestamp_s=timestamp)
        elif operation == "submit":
            lifecycle.submit(request, now_s=timestamp, max_age_s=1.0)
        elif operation == "source_stale":
            lifecycle.source_stale(timestamp_s=timestamp)
        elif operation == "source_invalid":
            lifecycle.source_invalid("invalid", timestamp_s=timestamp)
        elif operation == "abort":
            lifecycle.abort("abort", timestamp_s=timestamp)
        elif operation == "fail":
            lifecycle.fail("failure", timestamp_s=timestamp)
        elif operation == "cleanup":
            lifecycle.record_cleanup_failure("cleanup", timestamp_s=timestamp)
        else:
            lifecycle.reconnect(timestamp_s=timestamp)

    after = (
        lifecycle.state,
        lifecycle.permission,
        lifecycle.session_id,
        lifecycle.latest_request,
        lifecycle.last_request_sequence,
        lifecycle.stop_started_s,
        lifecycle.stop_deadline_s,
        lifecycle.events,
    )
    assert after == before


def test_source_invalid_aborts_and_new_session_is_required_after_terminal_state() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)
    lifecycle.submit(_endpoint_request(), now_s=1.0, max_age_s=1.0)

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
    lifecycle.submit(_endpoint_request(), now_s=1.0, max_age_s=1.0)

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
    lifecycle.submit(request, now_s=1.0, max_age_s=1.0)
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

    with pytest.raises(ValueError, match="cannot enter hold"):
        PhysicalOutputLifecycleEvent(
            event_sequence=0,
            event_kind="source_stale",
            session_id="session-1",
            state_before="disabled",
            state_after="hold",
            reason="source_stale",
        )

    with pytest.raises(ValueError, match="cannot enter stopping"):
        PhysicalOutputLifecycleEvent(
            event_sequence=0,
            event_kind="operator_stop",
            session_id="session-1",
            state_before="disabled",
            state_after="stopping",
            reason="operator_stop",
        )


def test_missing_freshness_context_enters_hold_without_acceptance() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)

    result = lifecycle.submit(_endpoint_request(), now_s=1.0)

    assert not result.accepted
    assert result.reason == "physical_output_freshness_context_missing"
    assert lifecycle.state == "hold"
    assert lifecycle.latest_request is None
    assert lifecycle.last_request_sequence == 4


def test_hold_rearm_requires_an_unused_session_id_for_lifetime() -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    lifecycle.arm(permission)
    lifecycle.submit(_endpoint_request(), now_s=1.0, max_age_s=1.0)
    lifecycle.source_stale(timestamp_s=2.0)

    same_session = lifecycle.arm(permission, session_id="session-1")
    assert not same_session.accepted
    assert same_session.reason == "new_session_required_for_rearm"

    assert lifecycle.arm(permission, session_id="session-2").accepted
    lifecycle.source_invalid("invalid", timestamp_s=3.0)
    reused_session = lifecycle.arm(permission, session_id="session-1")
    assert not reused_session.accepted
    assert reused_session.reason == "session_id_reuse_forbidden"


@pytest.mark.parametrize("health_event", ("source_stale", "source_disconnected"))
def test_submit_and_source_health_are_serialized_without_trace_corruption(
    health_event: str,
) -> None:
    lifecycle = PhysicalOutputLifecycle("session-1")
    permission = PhysicalOutputPermission(mode="dry_run")
    request = _endpoint_request()
    lifecycle.arm(permission)
    barrier = Barrier(2)

    def submit() -> object:
        barrier.wait()
        return lifecycle.submit(request, now_s=1.0, max_age_s=1.0)

    def stale() -> object:
        barrier.wait()
        return getattr(lifecycle, health_event)(timestamp_s=1.0)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda operation: operation(), (submit, stale)))

    assert len(results) == 2
    assert lifecycle.state == "hold"
    assert lifecycle.latest_request is None
    trace = lifecycle.trace()
    assert PhysicalOutputLifecycleTrace.from_jsonl(trace.to_jsonl_bytes()) == trace


def test_sink_event_failure_fails_closed_and_keeps_internal_trace_valid() -> None:
    class BrokenSink:
        def record_lifecycle_event(self, event: PhysicalOutputLifecycleEvent) -> None:
            raise RuntimeError("sink unavailable")

    lifecycle = PhysicalOutputLifecycle("session-1", sink=BrokenSink())
    with pytest.raises(RuntimeError, match="event recording failed"):
        lifecycle.arm(PhysicalOutputPermission(mode="dry_run"))

    assert lifecycle.state == "failed"
    assert lifecycle.latest_request is None
    assert lifecycle.events[-1].event_kind == "failure"
    assert "lifecycle_event_recording_failed:RuntimeError" == lifecycle.events[-1].reason
    assert PhysicalOutputLifecycleTrace.from_jsonl(lifecycle.trace().to_jsonl_bytes()) == lifecycle.trace()


def test_shutdown_uses_post_cleanup_monotonic_time_and_marks_overrun_failed() -> None:
    clock_values = iter((0.0, 2.0))
    lifecycle = PhysicalOutputLifecycle(
        "session-slow-cleanup",
        shutdown_timeout_s=1.0,
        clock=lambda: next(clock_values),
    )
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"))
    lifecycle.submit(_endpoint_request(), now_s=1.0, max_age_s=1.0)

    result = lifecycle.shutdown(now_s=2.0, cleanup=lambda: None)

    assert not result.accepted
    assert result.reason == "bounded_shutdown_deadline_exceeded"
    assert lifecycle.state == "failed"


def test_stop_deadline_overflow_fails_closed() -> None:
    lifecycle = PhysicalOutputLifecycle(
        "session-overflow",
        shutdown_timeout_s=1.0e308,
    )
    lifecycle.arm(PhysicalOutputPermission(mode="dry_run"))

    result = lifecycle.operator_stop(now_s=1.0e308)

    assert not result.accepted
    assert result.reason == "bounded_shutdown_deadline_overflow"
    assert lifecycle.state == "failed"
    assert lifecycle.stop_deadline_s is None


def test_lifecycle_trace_rejects_same_session_rearm_from_stopped() -> None:
    events = (
        PhysicalOutputLifecycleEvent(
            event_sequence=0,
            event_kind="armed",
            session_id="session-1",
            state_before="disabled",
            state_after="armed",
        ),
        PhysicalOutputLifecycleEvent(
            event_sequence=1,
            event_kind="operator_stop",
            session_id="session-1",
            state_before="armed",
            state_after="stopping",
            reason="operator_stop",
        ),
        PhysicalOutputLifecycleEvent(
            event_sequence=2,
            event_kind="stop_completed",
            session_id="session-1",
            state_before="stopping",
            state_after="stopped",
        ),
        PhysicalOutputLifecycleEvent(
            event_sequence=3,
            event_kind="armed",
            session_id="session-1",
            state_before="stopped",
            state_after="armed",
        ),
    )

    with pytest.raises(ValueError, match="re-arm requires a new session"):
        PhysicalOutputLifecycleTrace(events=events)


def test_lifecycle_trace_rejects_disabled_request_to_hold() -> None:
    with pytest.raises(ValueError, match="request_rejected can enter hold"):
        PhysicalOutputLifecycleEvent(
            event_sequence=0,
            event_kind="request_rejected",
            session_id="session-1",
            state_before="disabled",
            state_after="hold",
            request_sequence=0,
            reason="physical_output_request_stale",
        )
