from __future__ import annotations

from collections.abc import Mapping

import pytest

from selfrionette.plugins.input_sources._common import ManagedFrameHealthReader
from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.runtime.control.input_source_selection import (
    select_runtime_input_source,
)
from selfrionette.runtime.control.input_source_state import (
    annotate_raw_input_frame,
    build_runtime_input_source_state_from_health,
)
from selfrionette.runtime.control.viewer_control_ingress import (
    ingest_viewer_control_message,
)
from selfrionette.runtime.execution.input_step_loop import (
    build_runtime_input_source_step_loop_plan,
)
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
)
from selfrionette.schemas import (
    RawInputFrame,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
)


class _RetryLifecycleDelegate:
    def __init__(
        self,
        *,
        fail_first_start: bool = False,
        fail_first_close: bool = False,
    ) -> None:
        self.start_calls = 0
        self.close_calls = 0
        self.is_open = False
        self._fail_first_start = fail_first_start
        self._fail_first_close = fail_first_close

    def start(self) -> None:
        self.start_calls += 1
        if self._fail_first_start and self.start_calls == 1:
            raise RuntimeError("first start failure")
        self.is_open = True

    def close(self) -> None:
        self.close_calls += 1
        if self._fail_first_close and self.close_calls == 1:
            raise RuntimeError("first close failure")
        self.is_open = False

    def read_frame(self) -> RawInputFrame:
        return RawInputFrame(source="fixture", timestamp_s=0.0)

    def current_health(self) -> InputSourceHealth:
        return InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0)


def _managed_reader(delegate: _RetryLifecycleDelegate) -> ManagedFrameHealthReader:
    return ManagedFrameHealthReader(
        delegate,
        InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0),
    )


def test_managed_reader_retries_after_failed_start_cleanup_without_leaking() -> None:
    delegate = _RetryLifecycleDelegate(fail_first_start=True)
    reader = _managed_reader(delegate)

    with pytest.raises(RuntimeError, match="first start failure"):
        reader.start()
    reader.close()

    reader.start()
    assert delegate.is_open is True
    reader.close()

    assert delegate.start_calls == 2
    assert delegate.close_calls == 2
    assert delegate.is_open is False


def test_managed_reader_allows_cleanup_retry_after_close_failure() -> None:
    delegate = _RetryLifecycleDelegate(fail_first_close=True)
    reader = _managed_reader(delegate)

    reader.start()
    with pytest.raises(RuntimeError, match="first close failure"):
        reader.close()
    assert delegate.is_open is True

    reader.close()

    assert delegate.start_calls == 1
    assert delegate.close_calls == 2
    assert delegate.is_open is False


def _analog_sample(
    timestamp_s: float,
    *,
    active: bool,
    stale_reason: str | None,
) -> Mapping[str, object]:
    return {
        "timestamp_s": timestamp_s,
        "raw_values": (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0),
        "active": active,
        "stale_reason": stale_reason,
    }


def test_analog_plugin_preserves_active_inactive_and_stale_states() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("analog_fixture").plugin
    reader = plugin.create_runtime_reader(
        {
            "samples": (
                _analog_sample(1.0, active=True, stale_reason=None),
                _analog_sample(2.0, active=False, stale_reason=None),
                _analog_sample(
                    3.0,
                    active=False,
                    stale_reason="recording_stale",
                ),
            )
        }
    )

    expected = (
        (InputSourceHealthStatus.ACTIVE, True, None),
        (InputSourceHealthStatus.INACTIVE, False, None),
        (InputSourceHealthStatus.STALE, False, "recording_stale"),
    )
    frames: list[RawInputFrame] = []
    for expected_status, expected_active, expected_reason in expected:
        frame = reader.read_frame()
        health = reader.current_health()
        state = build_runtime_input_source_state_from_health(
            health,
            source_kind="analog_fixture",
        )
        projected = annotate_raw_input_frame(frame, state)

        assert health.status is expected_status
        assert health.reason == expected_reason
        assert projected.metadata["source_active"] is expected_active
        assert projected.metadata.get("stale_reason") == expected_reason
        frames.append(projected)

    held_frame = reader.read_frame()
    held_health = reader.current_health()
    held_state = build_runtime_input_source_state_from_health(
        held_health,
        source_kind="analog_fixture",
    )
    assert annotate_raw_input_frame(held_frame, held_state) == frames[-1]


def test_inactive_health_rejects_failure_reason() -> None:
    health = InputSourceHealth(
        InputSourceHealthStatus.INACTIVE,
        age_ms=0,
    )
    state = build_runtime_input_source_state_from_health(
        health,
        source_kind="fixture",
    )

    assert state.source_active is False
    assert state.stale_reason is None

    with pytest.raises(ValueError, match="must not have a failure reason"):
        InputSourceHealth(
            InputSourceHealthStatus.INACTIVE,
            reason="not_stale",
            age_ms=0,
        )


class _MutableClock:
    def __init__(self, now_s: float) -> None:
        self.now_s = now_s

    def __call__(self) -> float:
        return self.now_s


def test_plugin_backed_viewer_plan_applies_injected_clock() -> None:
    clock = _MutableClock(10.0)
    original_selection = select_runtime_input_source("viewer", steps=1)

    plan = build_runtime_input_source_step_loop_plan(
        original_selection,
        viewer_clock=clock,
    )
    capability = plan.viewer_bridge_capability
    assert capability is not None
    assert plan.selection.runtime_reader is plan.pipeline.input_source

    ingest_viewer_control_message(
        capability,
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=1.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyD",),
                key_state={"KeyD": True},
                focus_state="focused",
                zero_state=False,
            ),
        ),
    )

    clock.now_s = 10.251
    frame = plan.pipeline.input_source.read_frame()
    health = plan.pipeline.input_source.current_health()

    assert frame.metadata["command_age_ms"] == 251
    assert frame.metadata["source_active"] is False
    assert frame.metadata["stale_reason"] == "command_age_ms_exceeded_timeout_250"
    assert health.status is InputSourceHealthStatus.STALE
    assert health.age_ms == 251
    assert health.reason == "command_age_ms_exceeded_timeout_250"
