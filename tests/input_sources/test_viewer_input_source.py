from __future__ import annotations

import math

import pytest

from selfrionette.input_sources import KeyboardBinding, KeyboardInputConfig, ViewerInputSource
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
    assert frame.metadata["control_frame"] == "world"
    assert frame.metadata["desired_endpoint_m"] == (0.6, 0.0, 0.1)
    assert frame.metadata["target_position_m"] == (0.6, 0.0, 0.1)
    assert frame.metadata["intent_kind"] is None
    assert frame.metadata["input_continuity"] is None
    assert frame.values == ()
    assert frame.buttons == ()


def test_viewer_input_source_converts_keyboard_message_to_continuous_axis_frame() -> None:
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
    axis_scale = math.sqrt(2.0)
    expected_axis_values = (1.0 / axis_scale, 1.0 / axis_scale, 0.0)

    assert frame.source == "viewer"
    assert frame.metadata["source_kind"] == "viewer_keyboard"
    assert frame.metadata["viewer_source_kind"] == "keyboard"
    assert frame.metadata["intent_kind"] == "local_endpoint_velocity"
    assert frame.metadata["input_continuity"] == "continuous"
    assert frame.metadata["source_active"] is True
    assert frame.metadata["command_age_ms"] == 0
    assert frame.metadata["stale_reason"] is None
    assert frame.metadata["control_frame"] == "world"
    assert frame.metadata["axis_values"] == pytest.approx(expected_axis_values, abs=1e-12)
    assert frame.metadata["endpoint_velocity_m_s"] == pytest.approx(
        tuple(component * 0.1 for component in expected_axis_values),
        abs=1e-12,
    )
    assert frame.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx(
        tuple(component * 0.1 for component in expected_axis_values),
        abs=1e-12,
    )
    assert frame.metadata["local_endpoint_velocity_m_s"] == pytest.approx(
        tuple(component * 0.1 for component in expected_axis_values),
        abs=1e-12,
    )
    assert frame.metadata["local_endpoint_velocity_frame"] == "world"
    assert frame.metadata["endpoint_velocity_frame"] == "mujoco_world"
    assert frame.metadata["local_endpoint_speed_m_s"] == pytest.approx(0.1, abs=1e-12)
    assert frame.metadata["local_endpoint_max_delta_m"] == pytest.approx(0.03, abs=1e-12)
    assert frame.metadata["viewer_control_message"]["keyboard"]["active_key_codes"] == ("KeyW", "KeyD")
    assert frame.values == pytest.approx(expected_axis_values, abs=1e-12)
    assert frame.buttons == (True, True)


@pytest.mark.parametrize(
    ("key_codes", "expected_axis_values"),
    (
        (("KeyA", "KeyD"), (0.0, 0.0, 0.0)),
        (("KeyW", "KeyS"), (0.0, 0.0, 0.0)),
        (("Space", "ShiftLeft"), (0.0, 0.0, 0.0)),
        (("KeyD",), (1.0, 0.0, 0.0)),
        (("KeyA",), (-1.0, 0.0, 0.0)),
        (("KeyW",), (0.0, 1.0, 0.0)),
        (("KeyS",), (0.0, -1.0, 0.0)),
        (("Space",), (0.0, 0.0, 1.0)),
        (("ShiftLeft",), (0.0, 0.0, -1.0)),
    ),
)
def test_viewer_input_source_keyboard_digital_axis_semantics(
    key_codes: tuple[str, ...],
    expected_axis_values: tuple[float, float, float],
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    key_state = {key_code: True for key_code in key_codes}

    frame = source.ingest_control_message(
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=7.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=key_codes,
                key_state=key_state,
                focus_state="focused",
                zero_state=False,
            ),
        )
    )

    assert frame.metadata["axis_values"] == pytest.approx(expected_axis_values, abs=1e-12)
    assert frame.values == pytest.approx(expected_axis_values, abs=1e-12)
    assert frame.metadata["control_frame"] == "world"


def test_viewer_input_source_converts_gamepad_message_to_continuous_axis_frame() -> None:
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
    assert frame.metadata["intent_kind"] == "local_endpoint_velocity"
    assert frame.metadata["input_continuity"] == "continuous"
    assert frame.metadata["source_active"] is True
    assert frame.metadata["command_age_ms"] == 0
    assert frame.metadata["stale_reason"] is None
    assert frame.metadata["control_frame"] == "world"
    assert frame.metadata["viewer_control_message"]["gamepad"]["axes"] == (1.0, 0.0, -0.5)
    assert frame.metadata["local_endpoint_speed_m_s"] == pytest.approx(0.1, abs=1e-12)
    assert frame.metadata["local_endpoint_max_delta_m"] == pytest.approx(0.03, abs=1e-12)
    assert frame.metadata["resolved_world_endpoint_velocity_m_s"] == pytest.approx(frame.metadata["endpoint_velocity_m_s"], abs=1e-12)
    assert frame.metadata["local_endpoint_velocity_frame"] == "world"
    assert frame.metadata["endpoint_velocity_frame"] == "mujoco_world"
    assert frame.values == pytest.approx((0.85065080835204, 0.0, 0.5257311121191337), abs=1e-12)
    assert frame.buttons == (True, False)


@pytest.mark.parametrize(
    ("pressed_buttons", "expected_axis", "expected_zero"),
    [
        ((True, False), (0.0, 0.0, 1.0), False),
        ((False, True), (0.0, 0.0, -1.0), False),
        ((True, True), (0.0, 0.0, 0.0), True),
        ((False, False), (0.0, 0.0, 0.0), True),
    ],
)
def test_viewer_gamepad_zero_input_uses_final_button_supplemented_axis(
    pressed_buttons: tuple[bool, bool],
    expected_axis: tuple[float, float, float],
    expected_zero: bool,
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=4.0,
            source_kind="gamepad",
            gamepad=ViewerControlGamepadMessage(
                connected=True,
                index=0,
                id="pad-1",
                axes=(0.0, 0.0, 0.0),
                buttons=tuple(
                    ViewerControlGamepadButtonMessage(pressed=pressed, value=float(pressed))
                    for pressed in pressed_buttons
                ),
                stale=False,
                zero_state=False,
            ),
        )
    )
    assert frame.metadata["axis_values"] == expected_axis
    assert frame.metadata["zero_input"] is expected_zero
    assert frame.metadata["local_endpoint_velocity_m_s"] == pytest.approx(
        tuple(component * 0.1 for component in expected_axis), abs=1e-12
    )


def test_viewer_keyboard_preserves_legacy_clamp_before_deadzone() -> None:
    config = KeyboardInputConfig(
        bindings={
            "KeyD": KeyboardBinding("x", 1),
            "KeyW": KeyboardBinding("y", 1),
        },
        speed_m_s=0.1,
        deadzone=0.8,
        max_delta_m=0.03,
    )
    source = ViewerInputSource(clock=lambda: 0.0, keyboard_config=config)
    frame = source.ingest_control_message(
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=2.5,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("KeyD", "KeyW"),
                key_state={"KeyD": True, "KeyW": True},
                focus_state="focused",
                zero_state=False,
            ),
        )
    )
    assert frame.metadata["axis_values"] == (0.0, 0.0, 0.0)
    assert frame.metadata["local_endpoint_velocity_m_s"] == (0.0, 0.0, 0.0)
    assert frame.metadata["zero_input"] is True
    assert frame.metadata["norm_clamped"] is True


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
    assert stale_frame.metadata["control_frame"] == "world"
    assert stale_frame.metadata["axis_values"] == (0.0, 1.0, 0.0)
    assert stale_frame.metadata["endpoint_velocity_m_s"] == pytest.approx((0.0, 0.1, 0.0), abs=1e-12)


def test_viewer_input_source_can_rebase_current_endpoint() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)

    source.rebase_current_endpoint_m((0.2, 0.3, 0.4))

    assert source.current_endpoint_m == (0.2, 0.3, 0.4)


def test_viewer_input_source_uses_rebased_endpoint_for_first_keyboard_command() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    initial_tip_site_position_m = (0.622, 0.0, 0.7)
    source.rebase_current_endpoint_m(initial_tip_site_position_m)

    frame = source.ingest_control_message(
        ViewerControlMessage(
            type="viewer_control_message",
            timestamp_s=6.0,
            source_kind="keyboard",
            keyboard=ViewerControlKeyboardMessage(
                active_key_codes=("Space",),
                key_state={"Space": True},
                focus_state="focused",
                zero_state=False,
            ),
        )
    )

    assert frame.metadata["current_tip_position_m"] == initial_tip_site_position_m
    assert frame.metadata["axis_values"] == (0.0, 0.0, 1.0)
    assert frame.metadata["endpoint_velocity_m_s"] == pytest.approx((0.0, 0.0, 0.1), abs=1e-12)
    assert frame.metadata["desired_endpoint_m"] == initial_tip_site_position_m
    assert frame.metadata["desired_endpoint_m"] != (0.6, 0.0, 0.11)
