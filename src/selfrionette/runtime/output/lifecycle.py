"""Fail-closed physical-output lifecycle coordination.

This module owns only state, transition evidence, and bounded local shutdown
semantics.  It never sends a request, opens a transport, or replays a stale
command.  A caller may attach a recording-only sink through the tiny
``record_lifecycle_event`` protocol.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from math import isfinite
from numbers import Real
from threading import RLock
from time import monotonic
from typing import Literal, Protocol, TypeAlias

from selfrionette.schemas import PhysicalOutputPermission, PhysicalOutputRequest


PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION = "physical-output-lifecycle/v1"
PhysicalOutputLifecycleState: TypeAlias = Literal[
    "disabled",
    "armed",
    "active",
    "hold",
    "stopping",
    "stopped",
    "aborted",
    "failed",
]
PhysicalOutputLifecycleEventKind: TypeAlias = Literal[
    "arm_rejected",
    "armed",
    "request_accepted",
    "request_rejected",
    "source_stale",
    "source_disconnected",
    "source_invalid",
    "operator_stop",
    "runtime_shutdown",
    "stop_completed",
    "stop_deadline_exceeded",
    "abort",
    "failure",
    "cleanup_failure",
    "reconnect",
]

_LIFECYCLE_STATES = frozenset(
    {"disabled", "armed", "active", "hold", "stopping", "stopped", "aborted", "failed"}
)
_LIFECYCLE_EVENT_KINDS = frozenset(
    {
        "arm_rejected",
        "armed",
        "request_accepted",
        "request_rejected",
        "source_stale",
        "source_disconnected",
        "source_invalid",
        "operator_stop",
        "runtime_shutdown",
        "stop_completed",
        "stop_deadline_exceeded",
        "abort",
        "failure",
        "cleanup_failure",
        "reconnect",
    }
)
_LIFECYCLE_EVENT_FIELDS = frozenset(
    {
        "event_kind",
        "event_sequence",
        "reason",
        "request_sequence",
        "schema_version",
        "session_id",
        "state_after",
        "state_before",
        "timestamp_s",
    }
)


class PhysicalOutputLifecycleSink(Protocol):
    """Minimal recording-only sink protocol used by the lifecycle owner."""

    def record_lifecycle_event(self, event: "PhysicalOutputLifecycleEvent") -> object: ...


def _lifecycle_locked(method: Callable[..., object]) -> Callable[..., object]:
    """Serialize public lifecycle access through one re-entrant reducer lock."""

    @wraps(method)
    def synchronized(
        self: "PhysicalOutputLifecycle",
        *args: object,
        **kwargs: object,
    ) -> object:
        with self._lock:
            return method(self, *args, **kwargs)

    return synchronized


def _lifecycle_identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if "\x00" in value:
        raise ValueError(f"{name} must not contain NUL")
    return value


def _lifecycle_sequence(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("lifecycle sequence must be a non-negative integer")
    return value


def _lifecycle_timestamp(name: str, value: object | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric or null")
    timestamp = float(value)
    if not isfinite(timestamp):
        raise ValueError(f"{name} must be finite or null")
    return timestamp


def _lifecycle_canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class PhysicalOutputLifecycleEvent:
    """Immutable transition evidence; state_after is the authoritative result."""

    event_sequence: int
    event_kind: PhysicalOutputLifecycleEventKind
    session_id: str
    state_before: PhysicalOutputLifecycleState
    state_after: PhysicalOutputLifecycleState
    request_sequence: int | None = None
    timestamp_s: float | None = None
    reason: str | None = None
    schema_version: str = PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _lifecycle_sequence(self.event_sequence)
        _lifecycle_identifier("session_id", self.session_id)
        if self.schema_version != PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION:
            raise ValueError(
                "unsupported physical output lifecycle schema_version: "
                f"{self.schema_version!r}"
            )
        if self.event_kind not in _LIFECYCLE_EVENT_KINDS:
            raise ValueError(
                "physical output lifecycle event_kind must be one of "
                f"{sorted(_LIFECYCLE_EVENT_KINDS)!r}"
            )
        if self.state_before not in _LIFECYCLE_STATES:
            raise ValueError("physical output lifecycle state_before is unknown")
        if self.state_after not in _LIFECYCLE_STATES:
            raise ValueError("physical output lifecycle state_after is unknown")
        request_sequence = None
        if self.request_sequence is not None:
            request_sequence = _lifecycle_sequence(self.request_sequence)
        timestamp_s = _lifecycle_timestamp("timestamp_s", self.timestamp_s)
        reason = None if self.reason is None else _lifecycle_identifier("reason", self.reason)
        if self.event_kind in {
            "arm_rejected",
            "request_rejected",
            "source_stale",
            "source_disconnected",
            "source_invalid",
            "operator_stop",
            "runtime_shutdown",
            "stop_deadline_exceeded",
            "abort",
            "failure",
            "cleanup_failure",
        } and reason is None:
            raise ValueError(f"{self.event_kind} lifecycle event requires a reason")
        if self.event_kind == "armed" and self.state_after != "armed":
            raise ValueError("armed event must enter armed state")
        if self.event_kind == "armed" and self.state_before not in {
            "disabled",
            "hold",
            "stopped",
            "aborted",
            "failed",
        }:
            raise ValueError("armed event must come from a non-running state")
        if self.event_kind == "arm_rejected" and self.state_after != self.state_before:
            raise ValueError("arm_rejected event cannot change lifecycle state")
        if self.event_kind == "request_accepted" and self.state_before not in {
            "armed",
            "active",
        }:
            raise ValueError("request_accepted event must come from armed or active state")
        if self.event_kind == "request_accepted" and self.state_after != "active":
            raise ValueError("request_accepted event must enter active state")
        if self.event_kind == "request_rejected" and self.state_after not in {
            self.state_before,
            "hold",
        }:
            raise ValueError("request_rejected event may only preserve state or enter hold")
        if self.event_kind == "stop_completed":
            if self.state_before not in {"stopping", "stopped"}:
                raise ValueError("stop_completed event must come from stopping or stopped state")
            if self.state_after != "stopped":
                raise ValueError("stop_completed event must enter stopped state")
        if self.event_kind in {"source_stale", "source_disconnected"} and self.state_after not in {
            "hold",
            self.state_before,
        }:
            raise ValueError(f"{self.event_kind} event must enter or remain in hold")
        if self.event_kind in {"operator_stop", "runtime_shutdown"} and self.state_after not in {
            self.state_before,
            "stopping",
        }:
            raise ValueError(f"{self.event_kind} event must preserve state or enter stopping")
        if self.event_kind == "stop_deadline_exceeded" and (
            self.state_before != "stopping" or self.state_after != "failed"
        ):
            raise ValueError("stop_deadline_exceeded event must enter failed from stopping")
        if self.event_kind in {"source_invalid", "abort"} and self.state_after not in {
            "aborted",
            "failed",
        }:
            raise ValueError(f"{self.event_kind} event must enter a terminal state")
        if self.event_kind == "failure" and self.state_after not in {
            "failed",
            "aborted",
        }:
            raise ValueError("failure event must enter a terminal state")
        if self.event_kind == "cleanup_failure" and self.state_after not in {
            self.state_before,
            "failed",
        }:
            raise ValueError("cleanup_failure event must preserve state or enter failed")
        if self.event_kind == "reconnect" and self.state_after != self.state_before:
            raise ValueError("reconnect event cannot change lifecycle state")
        if self.event_kind in {"source_stale", "source_disconnected"}:
            if self.state_after == "hold" and self.state_before not in {
                "armed",
                "active",
                "hold",
            }:
                raise ValueError(
                    f"{self.event_kind} cannot enter hold from {self.state_before}"
                )
        if (
            self.event_kind == "request_rejected"
            and self.state_after == "hold"
            and self.state_before != "hold"
        ):
            if self.state_before not in {"armed", "active"}:
                raise ValueError(
                    "request_rejected can enter hold only from armed or active state"
                )
            if self.reason not in {
                "physical_output_freshness_context_missing",
                "physical_output_freshness_context_invalid",
                "physical_output_request_stale",
                "physical_output_timestamp_in_future",
            }:
                raise ValueError(
                    "request_rejected can enter hold only for a freshness failure"
                )
        if self.event_kind in {"operator_stop", "runtime_shutdown"}:
            enters_stopping = self.state_after == "stopping"
            if enters_stopping and self.state_before not in {
                "armed",
                "active",
                "hold",
                "stopping",
            }:
                raise ValueError(
                    f"{self.event_kind} cannot enter stopping from {self.state_before}"
                )
        if self.event_kind == "source_invalid":
            expected_state = (
                self.state_before
                if self.state_before in {"aborted", "failed"}
                else "aborted"
            )
            if self.state_after != expected_state:
                raise ValueError(
                    "source_invalid must enter aborted or preserve a terminal state"
                )
        if self.event_kind == "abort":
            expected_state = (
                self.state_before
                if self.state_before in {"aborted", "failed"}
                else "aborted"
            )
            if self.state_after != expected_state:
                raise ValueError(
                    "abort must enter aborted or preserve a terminal state"
                )
        if self.event_kind == "failure":
            expected_state = (
                self.state_before
                if self.state_before in {"aborted", "failed"}
                else "failed"
            )
            if self.state_after != expected_state:
                raise ValueError(
                    "failure must enter failed or preserve a terminal state"
                )
        if self.event_kind == "cleanup_failure":
            expected_state = (
                self.state_before
                if self.state_before in {"aborted", "failed"}
                else "failed"
            )
            if self.state_after != expected_state:
                raise ValueError(
                    "cleanup_failure must enter failed or preserve a terminal state"
                )
        object.__setattr__(self, "request_sequence", request_sequence)
        object.__setattr__(self, "timestamp_s", timestamp_s)
        object.__setattr__(self, "reason", reason)

    def to_json_value(self) -> dict[str, object]:
        return {
            "event_kind": self.event_kind,
            "event_sequence": self.event_sequence,
            "reason": self.reason,
            "request_sequence": self.request_sequence,
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "state_after": self.state_after,
            "state_before": self.state_before,
            "timestamp_s": self.timestamp_s,
        }

    def to_json_bytes(self) -> bytes:
        return _lifecycle_canonical_json_bytes(self.to_json_value())


def _lifecycle_parse_json_object(document: bytes | str) -> dict[str, object]:
    if isinstance(document, bytes):
        if document.startswith(b"\xef\xbb\xbf"):
            raise ValueError("physical output lifecycle trace must not contain a UTF-8 BOM")
        try:
            text = document.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("physical output lifecycle trace must be valid UTF-8") from exc
    elif isinstance(document, str):
        text = document
    else:
        raise TypeError("physical output lifecycle event must be UTF-8 bytes or text")

    def reject_duplicate_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(
                    f"duplicate field in physical output lifecycle trace: {key!r}"
                )
            result[key] = value
        return result

    def reject_non_finite_constant(value: str) -> object:
        raise ValueError(f"non-finite JSON constant is forbidden: {value}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_fields,
            parse_constant=reject_non_finite_constant,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("physical output lifecycle event is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("physical output lifecycle event must be a JSON object")
    return value


def _lifecycle_event_from_json(
    document: bytes | str | dict[str, object],
) -> PhysicalOutputLifecycleEvent:
    payload = (
        document
        if isinstance(document, dict)
        else _lifecycle_parse_json_object(document)
    )
    actual = frozenset(payload)
    unknown = sorted(actual - _LIFECYCLE_EVENT_FIELDS)
    missing = sorted(_LIFECYCLE_EVENT_FIELDS - actual)
    if unknown:
        raise ValueError(f"physical output lifecycle event has unknown fields: {unknown}")
    if missing:
        raise ValueError(f"physical output lifecycle event is missing fields: {missing}")
    event_kind = payload["event_kind"]
    state_before = payload["state_before"]
    state_after = payload["state_after"]
    session_id = payload["session_id"]
    schema_version = payload["schema_version"]
    if not all(isinstance(value, str) for value in (event_kind, state_before, state_after, session_id, schema_version)):
        raise ValueError("physical output lifecycle string fields have invalid types")
    request_sequence = payload["request_sequence"]
    if request_sequence is not None and type(request_sequence) is not int:
        raise ValueError("physical output lifecycle request_sequence must be integer or null")
    timestamp_s = payload["timestamp_s"]
    if timestamp_s is not None and (
        isinstance(timestamp_s, bool) or not isinstance(timestamp_s, Real)
    ):
        raise ValueError("physical output lifecycle timestamp_s must be numeric or null")
    reason = payload["reason"]
    if reason is not None and not isinstance(reason, str):
        raise ValueError("physical output lifecycle reason must be string or null")
    return PhysicalOutputLifecycleEvent(
        event_sequence=_lifecycle_sequence(payload["event_sequence"]),
        event_kind=event_kind,  # type: ignore[arg-type]
        session_id=session_id,
        state_before=state_before,  # type: ignore[arg-type]
        state_after=state_after,  # type: ignore[arg-type]
        request_sequence=request_sequence,
        timestamp_s=timestamp_s,
        reason=reason,
        schema_version=schema_version,
    )


def _validate_lifecycle_events(events: tuple[PhysicalOutputLifecycleEvent, ...]) -> None:
    expected_sequence = 0
    previous_state: PhysicalOutputLifecycleState = "disabled"
    session_id: str | None = None
    used_session_ids: set[str] = set()
    latest_request_sequence_by_session: dict[str, int] = {}
    seen_request_sequences_by_session: dict[str, set[int]] = {}
    for event in events:
        if event.event_sequence != expected_sequence:
            raise ValueError("physical output lifecycle event sequence must be contiguous from zero")
        expected_sequence += 1
        if event.state_before != previous_state:
            raise ValueError("physical output lifecycle event state chain is inconsistent")
        if session_id is None:
            session_id = event.session_id
            used_session_ids.add(session_id)
        elif event.session_id != session_id:
            if not (
                event.event_kind == "armed"
                and previous_state in {"hold", "stopped", "aborted", "failed"}
            ):
                raise ValueError(
                    "physical output lifecycle session may change only on re-arm"
                )
            if event.session_id in used_session_ids:
                raise ValueError("physical output lifecycle session id may not be reused")
            session_id = event.session_id
            used_session_ids.add(session_id)
        elif event.event_kind == "armed" and previous_state in {
            "hold",
            "stopped",
            "aborted",
            "failed",
        }:
            raise ValueError("physical output lifecycle re-arm requires a new session")
        previous_state = event.state_after
        if event.event_kind in {"request_accepted", "request_rejected"}:
            if event.request_sequence is None and not (
                event.event_kind == "request_rejected"
                and event.reason
                in {
                    "session_mismatch",
                    "duplicate_or_out_of_order_sequence",
                    "lifecycle_state_not_accepting",
                }
            ):
                raise ValueError(f"{event.event_kind} requires request_sequence")
            if event.request_sequence is None:
                continue
            latest_request_sequence = latest_request_sequence_by_session.get(event.session_id)
            seen_request_sequences = seen_request_sequences_by_session.setdefault(
                event.session_id,
                set(),
            )
            if (
                latest_request_sequence is not None
                and event.request_sequence < latest_request_sequence
            ):
                raise ValueError("physical output lifecycle request event is late or out of order")
            if event.request_sequence in seen_request_sequences:
                raise ValueError("duplicate physical output lifecycle request event")
            seen_request_sequences.add(event.request_sequence)
            latest_request_sequence_by_session[event.session_id] = event.request_sequence


@dataclass(frozen=True, slots=True)
class PhysicalOutputLifecycleTrace:
    """Strict deterministic lifecycle-only JSONL evidence."""

    events: tuple[PhysicalOutputLifecycleEvent, ...] = ()
    schema_version: str = PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION:
            raise ValueError(
                "unsupported physical output lifecycle trace schema_version: "
                f"{self.schema_version!r}"
            )
        events = tuple(self.events)
        if any(not isinstance(event, PhysicalOutputLifecycleEvent) for event in events):
            raise TypeError("physical output lifecycle trace events must be typed events")
        object.__setattr__(self, "events", events)
        _validate_lifecycle_events(events)

    def to_jsonl_bytes(self) -> bytes:
        if not self.events:
            return b""
        return b"\n".join(event.to_json_bytes() for event in self.events) + b"\n"

    @classmethod
    def from_jsonl(cls, document: bytes | str) -> "PhysicalOutputLifecycleTrace":
        if isinstance(document, str):
            document_bytes = document.encode("utf-8")
        elif isinstance(document, bytes):
            document_bytes = document
        else:
            raise TypeError("physical output lifecycle trace must be UTF-8 bytes or text")
        if document_bytes.startswith(b"\xef\xbb\xbf"):
            raise ValueError("physical output lifecycle trace must not contain a UTF-8 BOM")
        if not document_bytes:
            return cls()
        if not document_bytes.endswith(b"\n"):
            raise ValueError("physical output lifecycle trace must end with a newline")
        lines = document_bytes[:-1].split(b"\n")
        if any(not line for line in lines):
            raise ValueError("physical output lifecycle trace must not contain blank lines")
        trace = cls(events=tuple(_lifecycle_event_from_json(line) for line in lines))
        if trace.to_jsonl_bytes() != document_bytes:
            raise ValueError("physical output lifecycle trace is not canonical JSONL")
        return trace


@dataclass(frozen=True, slots=True)
class PhysicalOutputLifecycleResult:
    """Outcome returned by request/transition operations."""

    accepted: bool
    state: PhysicalOutputLifecycleState
    reason: str | None = None
    event: PhysicalOutputLifecycleEvent | None = None


class PhysicalOutputLifecycle:
    """Pure local state machine guarding request acceptance and stop semantics."""

    def __init__(
        self,
        session_id: str,
        *,
        shutdown_timeout_s: float = 1.0,
        sink: PhysicalOutputLifecycleSink | None = None,
        clock: Callable[[], Real] | None = None,
    ) -> None:
        self._lock = RLock()
        self._session_id = _lifecycle_identifier("session_id", session_id)
        if isinstance(shutdown_timeout_s, bool) or not isinstance(shutdown_timeout_s, Real):
            raise TypeError("shutdown_timeout_s must be numeric")
        self._shutdown_timeout_s = float(shutdown_timeout_s)
        if not isfinite(self._shutdown_timeout_s) or self._shutdown_timeout_s <= 0.0:
            raise ValueError("shutdown_timeout_s must be finite and positive")
        if sink is not None and not callable(getattr(sink, "record_lifecycle_event", None)):
            raise TypeError("lifecycle sink must implement record_lifecycle_event")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._sink = sink
        self._clock = monotonic if clock is None else clock
        self._used_session_ids: set[str] = {self._session_id}
        self._state: PhysicalOutputLifecycleState = "disabled"
        self._permission: PhysicalOutputPermission | None = None
        self._latest_request: PhysicalOutputRequest | None = None
        self._last_request_sequence: int | None = None
        self._event_sequence = 0
        self._events: list[PhysicalOutputLifecycleEvent] = []
        self._stop_deadline_s: float | None = None

    @property
    @_lifecycle_locked
    def session_id(self) -> str:
        return self._session_id

    @property
    @_lifecycle_locked
    def state(self) -> PhysicalOutputLifecycleState:
        return self._state

    @property
    @_lifecycle_locked
    def permission(self) -> PhysicalOutputPermission | None:
        return self._permission

    @property
    @_lifecycle_locked
    def latest_request(self) -> PhysicalOutputRequest | None:
        return self._latest_request

    @property
    @_lifecycle_locked
    def last_request_sequence(self) -> int | None:
        return self._last_request_sequence

    @property
    @_lifecycle_locked
    def stop_deadline_s(self) -> float | None:
        return self._stop_deadline_s

    @property
    @_lifecycle_locked
    def events(self) -> tuple[PhysicalOutputLifecycleEvent, ...]:
        return tuple(self._events)

    @_lifecycle_locked
    def trace(self) -> PhysicalOutputLifecycleTrace:
        return PhysicalOutputLifecycleTrace(events=tuple(self._events))

    def _record(
        self,
        event_kind: PhysicalOutputLifecycleEventKind,
        *,
        state_before: PhysicalOutputLifecycleState,
        state_after: PhysicalOutputLifecycleState,
        request_sequence: int | None = None,
        timestamp_s: float | None = None,
        reason: str | None = None,
    ) -> PhysicalOutputLifecycleEvent:
        event = PhysicalOutputLifecycleEvent(
            event_sequence=self._event_sequence,
            event_kind=event_kind,
            session_id=self._session_id,
            state_before=state_before,
            state_after=state_after,
            request_sequence=request_sequence,
            timestamp_s=timestamp_s,
            reason=reason,
        )
        self._event_sequence += 1
        self._events.append(event)
        if self._sink is not None:
            try:
                self._sink.record_lifecycle_event(event)
            except Exception as exc:
                failure_state: PhysicalOutputLifecycleState = (
                    "aborted" if event.state_after == "aborted" else "failed"
                )
                self._state = failure_state
                self._latest_request = None
                self._stop_deadline_s = None
                failure_event = PhysicalOutputLifecycleEvent(
                    event_sequence=self._event_sequence,
                    event_kind="failure",
                    session_id=self._session_id,
                    state_before=event.state_after,
                    state_after=failure_state,
                    timestamp_s=timestamp_s,
                    reason=f"lifecycle_event_recording_failed:{type(exc).__name__}",
                )
                self._event_sequence += 1
                self._events.append(failure_event)
                raise RuntimeError(
                    "physical output lifecycle event recording failed"
                ) from exc
        return event

    def _result(
        self,
        accepted: bool,
        reason: str | None = None,
        event: PhysicalOutputLifecycleEvent | None = None,
    ) -> PhysicalOutputLifecycleResult:
        return PhysicalOutputLifecycleResult(
            accepted=accepted,
            state=self._state,
            reason=reason,
            event=event,
        )

    def _clock_now(self) -> float:
        return _required_timestamp("clock", self._clock())

    @_lifecycle_locked
    def arm(
        self,
        permission: PhysicalOutputPermission,
        *,
        session_id: str | None = None,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        """Explicitly arm; reconnect alone never invokes this transition."""

        if not isinstance(permission, PhysicalOutputPermission):
            raise TypeError("lifecycle arm requires PhysicalOutputPermission")
        if permission.mode == "disabled":
            event = self._record(
                "arm_rejected",
                state_before=self._state,
                state_after=self._state,
                timestamp_s=timestamp_s,
                reason="physical_output_disabled",
            )
            return self._result(False, "physical_output_disabled", event)
        if self._state in {"armed", "active", "stopping"}:
            event = self._record(
                "arm_rejected",
                state_before=self._state,
                state_after=self._state,
                timestamp_s=timestamp_s,
                reason="lifecycle_already_running",
            )
            return self._result(False, "lifecycle_already_running", event)
        if self._state in {"hold", "stopped", "aborted", "failed"}:
            if session_id is None:
                reason = "new_session_required_for_rearm"
                event = self._record(
                    "arm_rejected",
                    state_before=self._state,
                    state_after=self._state,
                    timestamp_s=timestamp_s,
                    reason=reason,
                )
                return self._result(False, reason, event)
            resolved_session_id = _lifecycle_identifier("session_id", session_id)
            if resolved_session_id == self._session_id:
                reason = "new_session_required_for_rearm"
                event = self._record(
                    "arm_rejected",
                    state_before=self._state,
                    state_after=self._state,
                    timestamp_s=timestamp_s,
                    reason=reason,
                )
                return self._result(False, reason, event)
            if resolved_session_id in self._used_session_ids:
                reason = "session_id_reuse_forbidden"
                event = self._record(
                    "arm_rejected",
                    state_before=self._state,
                    state_after=self._state,
                    timestamp_s=timestamp_s,
                    reason=reason,
                )
                return self._result(False, reason, event)
            self._session_id = resolved_session_id
            self._used_session_ids.add(resolved_session_id)
            self._last_request_sequence = None
        elif session_id is not None and _lifecycle_identifier("session_id", session_id) != self._session_id:
            reason = "session_mismatch"
            event = self._record(
                "arm_rejected",
                state_before=self._state,
                state_after=self._state,
                timestamp_s=timestamp_s,
                reason=reason,
            )
            return self._result(False, reason, event)

        before = self._state
        self._permission = permission
        self._latest_request = None
        self._stop_deadline_s = None
        self._state = "armed"
        event = self._record(
            "armed",
            state_before=before,
            state_after=self._state,
            timestamp_s=timestamp_s,
        )
        return self._result(True, event=event)

    @_lifecycle_locked
    def reconnect(self, *, timestamp_s: float | None = None) -> PhysicalOutputLifecycleEvent:
        """Record reconnect only; it never changes state or accepts output."""

        return self._record(
            "reconnect",
            state_before=self._state,
            state_after=self._state,
            timestamp_s=timestamp_s,
            reason=None,
        )

    @_lifecycle_locked
    def submit(
        self,
        request: PhysicalOutputRequest,
        *,
        now_s: float | None = None,
        max_age_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        """Accept only fresh, increasing requests in armed/active state."""

        if not isinstance(request, PhysicalOutputRequest):
            raise TypeError("lifecycle submit requires PhysicalOutputRequest")
        if request.session_id != self._session_id:
            return self._reject_request(
                request,
                "session_mismatch",
                timestamp_s=now_s,
                record_sequence=False,
            )
        if (
            self._last_request_sequence is not None
            and request.sequence <= self._last_request_sequence
        ):
            return self._reject_request(
                request,
                "duplicate_or_out_of_order_sequence",
                timestamp_s=now_s,
                record_sequence=False,
            )
        if self._state not in {"armed", "active"}:
            return self._reject_request(
                request,
                "lifecycle_state_not_accepting",
                timestamp_s=now_s,
                record_sequence=False,
            )
        freshness_reason = _request_freshness_reason(
            request,
            now_s=now_s,
            max_age_s=max_age_s,
        )
        self._last_request_sequence = request.sequence
        if freshness_reason is not None:
            before = self._state
            self._state = "hold"
            self._latest_request = None
            event = self._record(
                "request_rejected",
                state_before=before,
                state_after=self._state,
                request_sequence=request.sequence,
                timestamp_s=now_s,
                reason=freshness_reason,
            )
            return self._result(False, freshness_reason, event)
        before = self._state
        self._latest_request = request
        self._state = "active"
        event = self._record(
            "request_accepted",
            state_before=before,
            state_after=self._state,
            request_sequence=request.sequence,
            timestamp_s=now_s,
        )
        return self._result(True, event=event)

    def _reject_request(
        self,
        request: PhysicalOutputRequest,
        reason: str,
        *,
        timestamp_s: float | None,
        record_sequence: bool = True,
    ) -> PhysicalOutputLifecycleResult:
        event = self._record(
            "request_rejected",
            state_before=self._state,
            state_after=self._state,
            request_sequence=request.sequence if record_sequence else None,
            timestamp_s=timestamp_s,
            reason=reason,
        )
        return self._result(False, reason, event)

    @_lifecycle_locked
    def source_stale(
        self,
        reason: str = "source_stale",
        *,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        return self._enter_hold("source_stale", reason, timestamp_s=timestamp_s)

    @_lifecycle_locked
    def source_disconnected(
        self,
        reason: str = "source_disconnected",
        *,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        return self._enter_hold("source_disconnected", reason, timestamp_s=timestamp_s)

    def _enter_hold(
        self,
        event_kind: Literal["source_stale", "source_disconnected"],
        reason: str,
        *,
        timestamp_s: float | None,
    ) -> PhysicalOutputLifecycleResult:
        reason = _lifecycle_identifier("reason", reason)
        before = self._state
        if self._state in {"active", "armed"}:
            self._state = "hold"
            self._latest_request = None
        event = self._record(
            event_kind,
            state_before=before,
            state_after=self._state,
            timestamp_s=timestamp_s,
            reason=reason,
        )
        return self._result(True, event=event)

    @_lifecycle_locked
    def source_invalid(
        self,
        reason: str = "source_invalid",
        *,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        return self._terminal_transition("source_invalid", "aborted", reason, timestamp_s)

    @_lifecycle_locked
    def operator_stop(
        self,
        reason: str = "operator_stop",
        *,
        now_s: float,
    ) -> PhysicalOutputLifecycleResult:
        return self._request_stop("operator_stop", reason, now_s=now_s)

    @_lifecycle_locked
    def runtime_shutdown(
        self,
        reason: str = "runtime_shutdown",
        *,
        now_s: float,
    ) -> PhysicalOutputLifecycleResult:
        return self._request_stop("runtime_shutdown", reason, now_s=now_s)

    def _request_stop(
        self,
        event_kind: Literal["operator_stop", "runtime_shutdown"],
        reason: str,
        *,
        now_s: float,
    ) -> PhysicalOutputLifecycleResult:
        now = _required_timestamp("now_s", now_s)
        reason = _lifecycle_identifier("reason", reason)
        if self._state == "disabled":
            event = self._record(
                event_kind,
                state_before=self._state,
                state_after=self._state,
                timestamp_s=now,
                reason="stop_idempotent",
            )
            return self._result(True, event=event)
        if self._state in {"stopping", "stopped"}:
            event = self._record(
                event_kind,
                state_before=self._state,
                state_after=self._state,
                timestamp_s=now,
                reason="stop_idempotent",
            )
            return self._result(True, event=event)
        if self._state in {"aborted", "failed"}:
            event = self._record(
                event_kind,
                state_before=self._state,
                state_after=self._state,
                timestamp_s=now,
                reason="terminal_state_preserved",
            )
            return self._result(True, event=event)
        deadline = now + self._shutdown_timeout_s
        if not isfinite(deadline):
            before = self._state
            self._state = "failed"
            self._latest_request = None
            self._stop_deadline_s = None
            event = self._record(
                "failure",
                state_before=before,
                state_after=self._state,
                timestamp_s=now,
                reason="bounded_shutdown_deadline_overflow",
            )
            return self._result(False, "bounded_shutdown_deadline_overflow", event)
        before = self._state
        self._state = "stopping"
        self._latest_request = None
        self._stop_deadline_s = deadline
        event = self._record(
            event_kind,
            state_before=before,
            state_after=self._state,
            timestamp_s=now,
            reason=reason,
        )
        return self._result(True, event=event)

    @_lifecycle_locked
    def complete_stop(
        self,
        *,
        now_s: float,
    ) -> PhysicalOutputLifecycleResult:
        now = _required_timestamp("now_s", now_s)
        if self._state == "stopped":
            event = self._record(
                "stop_completed",
                state_before=self._state,
                state_after=self._state,
                timestamp_s=now,
                reason="stop_idempotent",
            )
            return self._result(True, event=event)
        if self._state != "stopping":
            return self._result(False, "stop_not_pending")
        if self._stop_deadline_s is not None and now > self._stop_deadline_s:
            before = self._state
            self._state = "failed"
            self._stop_deadline_s = None
            event = self._record(
                "stop_deadline_exceeded",
                state_before=before,
                state_after=self._state,
                timestamp_s=now,
                reason="bounded_shutdown_deadline_exceeded",
            )
            return self._result(False, "bounded_shutdown_deadline_exceeded", event)
        before = self._state
        self._state = "stopped"
        self._latest_request = None
        self._stop_deadline_s = None
        event = self._record(
            "stop_completed",
            state_before=before,
            state_after=self._state,
            timestamp_s=now,
        )
        return self._result(True, event=event)

    @_lifecycle_locked
    def abort(
        self,
        reason: str = "operator_abort",
        *,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        return self._terminal_transition("abort", "aborted", reason, timestamp_s)

    @_lifecycle_locked
    def fail(
        self,
        reason: str = "output_failure",
        *,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        return self._terminal_transition("failure", "failed", reason, timestamp_s)

    @_lifecycle_locked
    def record_cleanup_failure(
        self,
        reason: str = "cleanup_failure",
        *,
        timestamp_s: float | None = None,
    ) -> PhysicalOutputLifecycleResult:
        reason = _lifecycle_identifier("reason", reason)
        before = self._state
        if self._state in {"failed", "aborted"}:
            self._stop_deadline_s = None
            event = self._record(
                "cleanup_failure",
                state_before=before,
                state_after=before,
                timestamp_s=timestamp_s,
                reason=reason,
            )
            return self._result(True, event=event)
        self._state = "failed"
        self._latest_request = None
        self._stop_deadline_s = None
        event = self._record(
            "cleanup_failure",
            state_before=before,
            state_after=self._state,
            timestamp_s=timestamp_s,
            reason=reason,
        )
        return self._result(False, reason, event)

    @_lifecycle_locked
    def shutdown(
        self,
        reason: str = "runtime_shutdown",
        *,
        now_s: float,
        cleanup: Callable[[], object] | None = None,
        primary_failure: str | None = None,
    ) -> PhysicalOutputLifecycleResult:
        """Run bounded local shutdown while preserving a prior primary failure."""

        now = _required_timestamp("now_s", now_s)
        if primary_failure is not None:
            self.fail(primary_failure, timestamp_s=now)
        stop_result = self.runtime_shutdown(reason, now_s=now)
        completion_now = now
        if cleanup is not None:
            try:
                cleanup_started = self._clock_now()
            except Exception:
                return self.record_cleanup_failure(
                    "cleanup_clock_invalid",
                    timestamp_s=now,
                )
            try:
                cleanup()
            except Exception as exc:  # cleanup must not hide primary failure
                try:
                    cleanup_finished = self._clock_now()
                    cleanup_timestamp = _cleanup_completion_timestamp(
                        now,
                        cleanup_started,
                        cleanup_finished,
                    )
                except Exception:
                    cleanup_timestamp = now
                return self.record_cleanup_failure(
                    f"cleanup_failed:{type(exc).__name__}",
                    timestamp_s=cleanup_timestamp,
                )
            try:
                cleanup_finished = self._clock_now()
                completion_now = _cleanup_completion_timestamp(
                    now,
                    cleanup_started,
                    cleanup_finished,
                )
            except Exception:
                return self.record_cleanup_failure(
                    "cleanup_clock_invalid",
                    timestamp_s=now,
                )
        if self._state == "stopping":
            return self.complete_stop(now_s=completion_now)
        return stop_result

    def _terminal_transition(
        self,
        event_kind: Literal["source_invalid", "abort", "failure"],
        terminal_state: Literal["aborted", "failed"],
        reason: str,
        timestamp_s: float | None,
    ) -> PhysicalOutputLifecycleResult:
        reason = _lifecycle_identifier("reason", reason)
        before = self._state
        if self._state in {"failed", "aborted"}:
            self._stop_deadline_s = None
            event = self._record(
                event_kind,
                state_before=before,
                state_after=before,
                timestamp_s=timestamp_s,
                reason="terminal_state_preserved",
            )
            return self._result(True, event=event)
        self._state = terminal_state
        self._latest_request = None
        self._stop_deadline_s = None
        event = self._record(
            event_kind,
            state_before=before,
            state_after=self._state,
            timestamp_s=timestamp_s,
            reason=reason,
        )
        return self._result(False, reason, event)


def _cleanup_completion_timestamp(
    shutdown_timestamp: float,
    cleanup_started: float,
    cleanup_finished: float,
) -> float:
    elapsed = cleanup_finished - cleanup_started
    if not isfinite(elapsed) or elapsed < 0.0:
        raise ValueError("cleanup monotonic clock moved backwards or became non-finite")
    completion_timestamp = shutdown_timestamp + elapsed
    if not isfinite(completion_timestamp):
        raise ValueError("cleanup completion timestamp became non-finite")
    return completion_timestamp


def _required_timestamp(name: str, value: object) -> float:
    timestamp = _lifecycle_timestamp(name, value)
    if timestamp is None:
        raise ValueError(f"{name} is required")
    return timestamp


def _request_freshness_reason(
    request: PhysicalOutputRequest,
    *,
    now_s: float | None,
    max_age_s: float | None,
) -> str | None:
    if now_s is None or max_age_s is None:
        if now_s is not None:
            try:
                _required_timestamp("now_s", now_s)
            except Exception:
                return "physical_output_freshness_context_invalid"
        if max_age_s is not None:
            try:
                max_age = _lifecycle_timestamp("max_age_s", max_age_s)
            except (TypeError, ValueError):
                return "physical_output_freshness_context_invalid"
            if max_age is None or max_age < 0.0:
                return "physical_output_freshness_context_invalid"
        return "physical_output_freshness_context_missing"
    try:
        max_age = _lifecycle_timestamp("max_age_s", max_age_s)
    except (TypeError, ValueError):
        return "physical_output_freshness_context_invalid"
    if max_age is None or max_age < 0.0:
        return "physical_output_freshness_context_invalid"
    try:
        now = _required_timestamp("now_s", now_s)
    except (TypeError, ValueError):
        return "physical_output_freshness_context_invalid"
    age = now - request.timestamp_s
    if age < 0.0:
        return "physical_output_timestamp_in_future"
    if age > max_age:
        return "physical_output_request_stale"
    return None


__all__ = [
    "PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION",
    "PhysicalOutputLifecycle",
    "PhysicalOutputLifecycleEvent",
    "PhysicalOutputLifecycleEventKind",
    "PhysicalOutputLifecycleResult",
    "PhysicalOutputLifecycleSink",
    "PhysicalOutputLifecycleState",
    "PhysicalOutputLifecycleTrace",
]
