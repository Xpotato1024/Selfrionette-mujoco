from __future__ import annotations

from dataclasses import replace
from math import inf, nan

import pytest

from selfrionette.plugins.input_sources.viewer import ViewerInputSource
from selfrionette.plugins.mappings.keyboard import KeyboardBinding, KeyboardInputConfig
from selfrionette.plugins.mappings.viewer import VIEWER_CONTROL_MAPPING_PLUGIN
from selfrionette.schemas import (
    ViewerControlGamepadButtonMessage,
    ViewerControlGamepadMessage,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
)


def keyboard_message(
    timestamp_s: float,
    *key_codes: str,
    focus_state: str = "focused",
    zero_state: bool | None = None,
    control_frame: str = "world",
) -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="keyboard",
        keyboard=ViewerControlKeyboardMessage(
            active_key_codes=key_codes,
            key_state={key_code: True for key_code in key_codes},
            focus_state=focus_state,  # type: ignore[arg-type]
            zero_state=not key_codes if zero_state is None else zero_state,
        ),
        metadata={"control_frame": control_frame},
    )


def gamepad_message(
    timestamp_s: float,
    axes: tuple[float, ...],
    *,
    buttons: tuple[bool, ...] = (),
    connected: bool = True,
    stale: bool = False,
    zero_state: bool = False,
    control_frame: str = "world",
    raw_axes: tuple[float, ...] | None = None,
) -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="gamepad",
        gamepad=ViewerControlGamepadMessage(
            connected=connected,
            index=0,
            id="pad-1",
            raw_axes=raw_axes,
            axes=axes,
            buttons=tuple(
                ViewerControlGamepadButtonMessage(pressed=pressed, value=float(pressed))
                for pressed in buttons
            ),
            stale=stale,
            zero_state=zero_state,
        ),
        metadata={"control_frame": control_frame},
    )


def map_frame(frame):
    return VIEWER_CONTROL_MAPPING_PLUGIN.strategy.map_input(frame, {})


_LEGACY_FRONTEND_GAMEPAD_DEADZONE = 0.1


def _baseline_frontend_gamepad_projection(value: float) -> float:
    """Independent reference for main's fixed frontend projection."""

    clamped = max(-1.0, min(1.0, value))
    magnitude = abs(clamped)
    if magnitude <= _LEGACY_FRONTEND_GAMEPAD_DEADZONE:
        return 0.0
    return (1.0 if clamped > 0.0 else -1.0) * (
        (magnitude - _LEGACY_FRONTEND_GAMEPAD_DEADZONE)
        / max(1.0 - _LEGACY_FRONTEND_GAMEPAD_DEADZONE, 1e-12)
    )


def _baseline_gamepad_transfer(value: float, backend_deadzone: float = 0.1) -> float:
    """Reproduce main's fixed frontend projection plus backend threshold."""

    projected = _baseline_frontend_gamepad_projection(value)
    return 0.0 if abs(projected) <= backend_deadzone else projected


def _provider_zero_state_for_raw_axis(value: float) -> bool:
    return _baseline_frontend_gamepad_projection(value) == 0.0


@pytest.mark.parametrize(
    "raw_axis",
    (
        0.00,
        0.05,
        0.10,
        0.15,
        0.19,
        0.20,
        0.50,
        1.00,
        -0.05,
        -0.10,
        -0.15,
        -0.19,
        -0.20,
        -0.50,
        -1.00,
    ),
)
def test_raw_gamepad_transfer_matches_complete_legacy_default_function(
    raw_axis: float,
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(
            4.0,
            (0.0, 0.0, 0.0),
            raw_axes=(raw_axis, 0.0, 0.0),
            zero_state=_provider_zero_state_for_raw_axis(raw_axis),
        )
    )

    intent = map_frame(frame)
    expected_axis = _baseline_gamepad_transfer(raw_axis)
    assert intent.values[0] == pytest.approx(expected_axis, abs=1e-12)
    assert intent.metadata["deadzone_applied_axis_values"][0] == pytest.approx(
        expected_axis, abs=1e-12
    )
    assert intent.metadata["local_endpoint_velocity_m_s"][0] == pytest.approx(
        expected_axis * 0.1, abs=1e-12
    )


@pytest.mark.parametrize(
    ("deadzone", "raw_axis"),
    (
        (0.0, 0.05),
        (0.0, 0.10),
        (0.0, 0.15),
        (0.0, 0.20),
        (0.0, -0.15),
        (0.2, 0.05),
        (0.2, 0.20),
        (0.2, 0.279),
        (0.2, 0.28),
        (0.2, 0.30),
        (0.2, -0.30),
    ),
)
def test_raw_gamepad_custom_deadzone_preserves_parameterized_legacy_composition(
    deadzone: float,
    raw_axis: float,
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0, gamepad_deadzone=deadzone)
    frame = source.ingest_control_message(
        gamepad_message(
            4.0,
            (0.0, 0.0, 0.0),
            raw_axes=(raw_axis, 0.0, 0.0),
            zero_state=_provider_zero_state_for_raw_axis(raw_axis),
        )
    )

    intent = map_frame(frame)
    assert intent.values[0] == pytest.approx(
        _baseline_gamepad_transfer(raw_axis, deadzone), abs=1e-12
    )


@pytest.mark.parametrize(
    ("key_code", "expected_axis"),
    (
        ("KeyD", (1.0, 0.0, 0.0)),
        ("KeyA", (-1.0, 0.0, 0.0)),
        ("KeyW", (0.0, 1.0, 0.0)),
        ("KeyS", (0.0, -1.0, 0.0)),
        ("Space", (0.0, 0.0, 1.0)),
        ("ShiftLeft", (0.0, 0.0, -1.0)),
    ),
)
def test_viewer_mapping_preserves_keyboard_axis_sign_and_speed(
    key_code: str, expected_axis: tuple[float, float, float]
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(keyboard_message(2.5, key_code))

    assert frame.metadata["viewer_input_sample"]["schema"] == "viewer_control_sample/v1"
    assert frame.metadata["viewer_input_sample"]["provider_id"] == "keyboard/v1"
    assert frame.metadata["viewer_input_sample"]["provider_schema"] == "viewer_keyboard_sample/v1"
    assert frame.values == ()
    assert "axis_values" not in frame.metadata

    intent = map_frame(frame)
    assert intent.values == pytest.approx(expected_axis, abs=1e-12)
    assert intent.metadata["local_endpoint_velocity_m_s"] == pytest.approx(
        tuple(component * 0.1 for component in expected_axis), abs=1e-12
    )
    assert intent.metadata["source_kind"] == "viewer_keyboard"
    assert intent.metadata["control_frame"] == "world"


def test_viewer_source_preserves_key_up_blur_and_zero_state_for_mapping() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    for message in (
        keyboard_message(1.0, "KeyW"),
        keyboard_message(1.1, focus_state="blurred", zero_state=True),
    ):
        frame = source.ingest_control_message(message)
        assert frame.metadata["source_active"] is (message.keyboard.focus_state == "focused" and not message.keyboard.zero_state)
        intent = map_frame(frame)
        assert intent.metadata["source_active"] is frame.metadata["source_active"]
        assert intent.metadata["stale_reason"] is not None if not frame.metadata["source_active"] else intent.metadata["stale_reason"] is None


def test_viewer_mapping_preserves_gamepad_axes_deadzone_and_button_supplement() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(4.0, (1.0, 0.0, -0.5), buttons=(True, False))
    )
    assert frame.values == (1.0, 0.0, -0.5)
    assert frame.metadata["viewer_input_sample"]["provider_id"] == "gamepad/v1"
    intent = map_frame(frame)
    assert intent.values == pytest.approx((0.85065080835204, 0.0, 0.5257311121191337), abs=1e-12)
    assert intent.metadata["local_endpoint_velocity_m_s"] == pytest.approx(
        (0.085065080835204, 0.0, 0.0525731112119134), abs=1e-12
    )

    for axis, expected in ((0.1, 0.0), (0.2, 0.2), (-0.1, 0.0), (-0.2, -0.2)):
        boundary_intent = map_frame(source.ingest_control_message(gamepad_message(5.0, (axis, 0.0, 0.0))))
        assert boundary_intent.values[0] == pytest.approx(expected, abs=1e-12)


def test_viewer_mapping_uses_canonical_sample_without_legacy_summary() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(4.0, (0.4444444444444445, 0.0, 0.0), raw_axes=(0.5, 0.0, 0.0))
    )
    expected = map_frame(frame)
    assert expected.values[0] == pytest.approx(0.4444444444444445, abs=1e-12)
    metadata = dict(frame.metadata)
    metadata.pop("viewer_control_message")
    summary_free = replace(frame, metadata=metadata)
    assert map_frame(summary_free).values == pytest.approx(expected.values, abs=1e-12)


def test_viewer_mapping_ignores_legacy_summary_when_it_disagrees_with_canonical_sample() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(4.0, (0.4444444444444445, 0.0, 0.0), raw_axes=(0.5, 0.0, 0.0))
    )
    expected = map_frame(frame)
    metadata = dict(frame.metadata)
    metadata["viewer_control_message"] = {"gamepad": {"axes": (0.0, 0.0, 0.0), "buttons": ()}}
    assert map_frame(replace(frame, metadata=metadata)).values == pytest.approx(
        expected.values, abs=1e-12
    )


def test_raw_gamepad_sample_preserves_legacy_zero_state_when_projected_axes_are_zero() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(
            4.0,
            (0.0, 0.0, 0.0),
            raw_axes=(0.05, 0.0, 0.0),
            zero_state=True,
        )
    )

    assert frame.metadata["source_active"] is False
    assert frame.metadata["viewer_input_sample"]["zero_state"] is True
    assert frame.metadata["viewer_input_sample"]["gamepad"]["raw_axes"] == (0.05, 0.0, 0.0)
    assert map_frame(frame).values == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_legacy_gamepad_sample_without_raw_axes_keeps_zero_state_compatibility() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(4.0, (0.0, 0.0, 0.0), zero_state=True)
    )

    assert frame.metadata["source_active"] is False
    assert map_frame(frame).values == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_viewer_mapping_applies_compatibility_parameters_and_preserves_defaults() -> None:
    keyboard_config = KeyboardInputConfig(
        bindings={"KeyQ": KeyboardBinding(axis="z", direction=-1)},
        speed_m_s=0.2,
        deadzone=0.0,
        max_delta_m=0.05,
    )
    source = ViewerInputSource(
        clock=lambda: 0.0,
        keyboard_config=keyboard_config,
        gamepad_speed_m_s=0.2,
        gamepad_deadzone=0.2,
        gamepad_max_delta_m=0.05,
    )
    keyboard_intent = map_frame(source.ingest_control_message(keyboard_message(1.0, "KeyQ")))
    assert keyboard_intent.values == pytest.approx((0.0, 0.0, -1.0), abs=1e-12)
    assert keyboard_intent.metadata["local_endpoint_velocity_m_s"] == pytest.approx(
        (0.0, 0.0, -0.2), abs=1e-12
    )
    assert keyboard_intent.metadata["local_endpoint_max_delta_m"] == pytest.approx(0.05)

    gamepad_intent = map_frame(
        source.ingest_control_message(gamepad_message(2.0, (0.3, 0.0, 0.0)))
    )
    assert gamepad_intent.values[0] == pytest.approx(0.3, abs=1e-12)
    assert gamepad_intent.metadata["local_endpoint_velocity_m_s"][0] == pytest.approx(0.06)


@pytest.mark.parametrize(
    "field",
    ("gamepad_speed_m_s", "gamepad_deadzone", "gamepad_max_delta_m"),
)
def test_viewer_input_source_rejects_negative_or_non_finite_mapping_parameters(field: str) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        ViewerInputSource(**{field: -1.0})
    with pytest.raises(ValueError, match="finite and non-negative"):
        ViewerInputSource(**{field: inf if field == "gamepad_speed_m_s" else nan})


@pytest.mark.parametrize(
    ("buttons", "expected_z"),
    (((True, False), 1.0), ((False, True), -1.0), ((True, True), 0.0), ((False, False), 0.0)),
)
def test_viewer_gamepad_button_supplement_remains_mapping_owned(
    buttons: tuple[bool, ...], expected_z: float
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(
        gamepad_message(
            4.0,
            (0.0, 0.0, 0.0),
            buttons=buttons,
            raw_axes=(0.0, 0.0, 0.0),
            zero_state=not any(buttons),
        )
    )
    assert frame.values == (0.0, 0.0, 0.0)
    assert "axis_values" not in frame.metadata
    assert frame.metadata["source_active"] is any(buttons)
    assert map_frame(frame).values[2] == pytest.approx(expected_z, abs=1e-12)
