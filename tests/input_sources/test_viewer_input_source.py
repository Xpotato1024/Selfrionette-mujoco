from __future__ import annotations

import pytest

from selfrionette.input_sources import ViewerInputSource
from selfrionette.plugins.input_sources._common import health_from_frame
from selfrionette.plugins.mappings.viewer import VIEWER_CONTROL_MAPPING_PLUGIN
from selfrionette.runtime.experiment.input_source import InputSourceHealthStatus
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
) -> ViewerControlMessage:
    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=timestamp_s,
        source_kind="gamepad",
        gamepad=ViewerControlGamepadMessage(
            connected=connected,
            index=0,
            id="pad-1",
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


def test_viewer_input_source_emits_raw_canonical_sample_before_ingest() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)

    frame = source.read_frame()

    assert frame.source == "viewer"
    assert frame.metadata["source_kind"] == "viewer"
    assert frame.metadata["source_active"] is False
    assert frame.metadata["command_age_ms"] == 0
    assert frame.metadata["stale_reason"] == "source_inactive"
    assert frame.values == ()
    assert frame.buttons == ()
    assert "axis_values" not in frame.metadata
    assert "endpoint_velocity_m_s" not in frame.metadata


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


@pytest.mark.parametrize(
    ("buttons", "expected_z"),
    (((True, False), 1.0), ((False, True), -1.0), ((True, True), 0.0), ((False, False), 0.0)),
)
def test_viewer_gamepad_button_supplement_remains_mapping_owned(
    buttons: tuple[bool, ...], expected_z: float
) -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    frame = source.ingest_control_message(gamepad_message(4.0, (0.0, 0.0, 0.0), buttons=buttons))
    assert frame.values == (0.0, 0.0, 0.0)
    assert "axis_values" not in frame.metadata
    assert map_frame(frame).values[2] == pytest.approx(expected_z, abs=1e-12)


def test_viewer_source_health_covers_disconnect_and_stale_timeout() -> None:
    clock = FakeClock((30.0, 30.0))
    source = ViewerInputSource(clock=clock, timeout_ms=250)
    source.ingest_control_message(gamepad_message(4.0, (0.8, 0.0, 0.0), connected=False, zero_state=True))
    disconnected_frame = source.read_frame()
    assert disconnected_frame.metadata["source_active"] is False
    assert disconnected_frame.metadata["stale_reason"] == "gamepad_inactive"
    assert health_from_frame(disconnected_frame).status is InputSourceHealthStatus.DISCONNECTED

    source = ViewerInputSource(clock=FakeClock((40.0, 40.301)), timeout_ms=250)
    source.ingest_control_message(keyboard_message(5.0, "KeyW"))
    stale_frame = source.read_frame()
    assert stale_frame.metadata["source_active"] is False
    assert stale_frame.metadata["command_age_ms"] == 301
    assert stale_frame.metadata["stale_reason"] == "command_age_ms_exceeded_timeout_250"


def test_viewer_source_invalid_provider_is_reported_as_invalid_health() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    with pytest.raises(ValueError, match="provider"):
        source.ingest_control_message(
            ViewerControlMessage(
                type="viewer_control_message",
                timestamp_s=1.0,
                source_kind="keyboard",
                provider_id="gamepad/v1",
                provider_schema="viewer_gamepad_sample/v1",
                keyboard=ViewerControlKeyboardMessage(
                    active_key_codes=("KeyW",),
                    key_state={"KeyW": True},
                    focus_state="focused",
                    zero_state=False,
                ),
            )
        )
    assert health_from_frame(source.read_frame()).status is InputSourceHealthStatus.INVALID


def test_viewer_source_rejects_malformed_provider_identity_without_fallback() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    with pytest.raises(ValueError, match="provider"):
        source.ingest_control_message(
            ViewerControlMessage(
                type="viewer_control_message",
                timestamp_s=1.0,
                source_kind="keyboard",
                provider_id="gamepad/v1",
                provider_schema="viewer_gamepad_sample/v1",
                keyboard=ViewerControlKeyboardMessage(
                    active_key_codes=("KeyW",),
                    key_state={"KeyW": True},
                    focus_state="focused",
                    zero_state=False,
                ),
            )
        )


def test_viewer_source_endpoint_accessor_is_only_compatibility_state() -> None:
    source = ViewerInputSource(clock=lambda: 0.0)
    source.rebase_current_endpoint_m((0.2, 0.3, 0.4))
    assert source.current_endpoint_m == (0.2, 0.3, 0.4)
    frame = source.ingest_control_message(keyboard_message(6.0, "Space"))
    assert "desired_endpoint_m" not in frame.metadata
    assert "current_tip_position_m" not in frame.metadata
