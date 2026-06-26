from __future__ import annotations

from selfrionette.input_sources import ViewerInputSource
from selfrionette.input_sources.keyboard import build_keyboard_motion_command
from selfrionette.schemas import (
    ViewerControlGamepadButtonMessage,
    ViewerControlGamepadMessage,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
)


class FakeClock:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def test_viewer_input_source_returns_safe_inactive_frame_before_ingest() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)

    frame = source.read_frame()

    assert frame.source == "viewer"
    assert frame.metadata["source_kind"] == "viewer"
    assert frame.metadata["source_active"] is False
    assert frame.metadata["command_age_ms"] == 0
    assert frame.metadata["stale_reason"] == "source_inactive"
    assert frame.metadata["desired_endpoint_m"] == (0.6, 0.0, 0.1)
    assert frame.metadata["target_position_m"] == (0.6, 0.0, 0.1)
    assert frame.values == ()
    assert frame.buttons == ()


def test_viewer_input_source_converts_keyboard_message_to_raw_input_frame() -> None:
    clock = FakeClock((10.0, 10.0))
    source = ViewerInputSource(clock=clock)
    message = ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=2.5,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=("KeyW", "KeyD"),
            key_state={"KeyW": True, "KeyD": True},
            focus_state="focused",
            zero_state=False,
        ),
    )

    frame = source.ingest_control_message(message)
    expected_command = build_keyboard_motion_command(
        ("KeyW", "KeyD"),
        current_tip_position_m=(0.6, 0.0, 0.1),
        timestamp_s=2.5,
    )

    assert frame.source == "viewer"
    assert frame.metadata["source_kind"] == "viewer_keyboard"
    assert frame.metadata["viewer_source_kind"] == "keyboard"
    assert frame.metadata["source_active"] is True
    assert frame.metadata["command_age_ms"] == 0
    assert frame.metadata["stale_reason"] is None
    assert frame.metadata["desired_endpoint_m"] == expected_command.metadata["desired_endpoint_m"]
    assert frame.metadata["target_position_m"] == expected_command.metadata["desired_endpoint_m"]
    assert frame.metadata["viewer_control_message"]["keyboard"]["active_key_codes"] == ("KeyW", "KeyD")
    assert frame.values == expected_command.metadata["endpoint_delta_m"]
    assert frame.buttons == (True, True)


def test_viewer_input_source_converts_gamepad_message_to_raw_input_frame() -> None:
    clock = FakeClock((20.0, 20.0))
    source = ViewerInputSource(clock=clock)
    message = ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=4.0,
        source_kind="gamepad",
        gamepad=ViewerControlGamepadMessage(
            connected=True,
            index=0,
            id="pad-1",
            axes=(1.0, 0.0, -0.5),
            buttons=(
                ViewerControlGamepadButtonMessage(pressed=True, value=1.0),
                ViewerControlGamepadButtonMessage(pressed=False, value=0.0),
            ),
            stale=False,
            zero_state=False,
        ),
    )

    frame = source.ingest_control_message(message)

    assert frame.source == "viewer"
    assert frame.metadata["source_kind"] == "viewer_gamepad"
    assert frame.metadata["viewer_source_kind"] == "gamepad"
    assert frame.metadata["source_active"] is True
    assert frame.metadata["command_age_ms"] == 0
    assert frame.metadata["stale_reason"] is None
    assert frame.metadata["viewer_control_message"]["gamepad"]["axes"] == (1.0, 0.0, -0.5)
    assert frame.values == (1.0, 0.0, -0.5)
    assert frame.buttons == (True, False)
    assert frame.metadata["desired_endpoint_m"] == (0.61, 0.0, 0.105)
    assert frame.metadata["target_position_m"] == (0.61, 0.0, 0.105)


def test_viewer_input_source_marks_frame_stale_after_timeout() -> None:
    clock = FakeClock((30.0, 30.301))
    source = ViewerInputSource(clock=clock, timeout_ms=250)
    message = ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=5.0,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=("KeyW",),
            key_state={"KeyW": True},
            focus_state="focused",
            zero_state=False,
        ),
    )

    source.ingest_control_message(message)
    stale_frame = source.read_frame()

    assert stale_frame.metadata["source_kind"] == "viewer_keyboard"
    assert stale_frame.metadata["source_active"] is False
    assert stale_frame.metadata["command_age_ms"] == 301
    assert stale_frame.metadata["stale_reason"] == "command_age_ms_exceeded_timeout_250"
    assert stale_frame.metadata["desired_endpoint_m"] == (0.6, 0.01, 0.1)
    assert stale_frame.metadata["target_position_m"] == (0.6, 0.01, 0.1)


def test_viewer_input_source_can_rebase_current_endpoint() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)

    source.rebase_current_endpoint_m((0.2, 0.3, 0.4))

    assert source.current_endpoint_m == (0.2, 0.3, 0.4)
