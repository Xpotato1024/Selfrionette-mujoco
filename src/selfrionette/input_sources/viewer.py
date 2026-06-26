from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite, sqrt
from time import monotonic

from selfrionette.input_sources.keyboard import (
    KeyboardInputConfig,
    build_default_keyboard_input_config,
    build_keyboard_motion_command,
)
from selfrionette.schemas import (
    RawInputFrame,
    ViewerControlGamepadButtonMessage,
    ViewerControlGamepadMessage,
    ViewerControlKeyboardMessage,
    ViewerControlMessage,
    parse_viewer_control_message_json,
)

DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS = 250
DEFAULT_VIEWER_SAFE_ENDPOINT_M: tuple[float, float, float] = (0.6, 0.0, 0.1)
_VIEWER_SOURCE_KIND = "viewer"
_VIEWER_KEYBOARD_SOURCE_KIND = "viewer_keyboard"
_VIEWER_GAMEPAD_SOURCE_KIND = "viewer_gamepad"
_SOURCE_INACTIVE_STALE_REASON = "source_inactive"
_VIEWER_KEYBOARD_INACTIVE_STALE_REASON = "keyboard_inactive"
_VIEWER_GAMEPAD_INACTIVE_STALE_REASON = "gamepad_inactive"
_VIEWER_CONTROL_SUMMARY_KEY = "viewer_control_message"


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    for component_index, component in enumerate(components):
        if not isfinite(component):
            raise ValueError(f"{name} must contain only finite values at index {component_index}")

    return components


def _clamp_vector3(vector: tuple[float, float, float], *, limit: float) -> tuple[float, float, float]:
    magnitude = sqrt(sum(component * component for component in vector))
    if magnitude == 0.0 or magnitude <= limit:
        return vector

    scale = limit / magnitude
    return tuple(component * scale for component in vector)


def _round_vector3(vector: tuple[float, float, float], *, places: int = 12) -> tuple[float, float, float]:
    return tuple(round(component, places) for component in vector)


def _coerce_axis_vector3(
    axes: Sequence[float],
    *,
    step_m: float,
    deadzone: float,
    max_delta_m: float,
) -> tuple[float, float, float]:
    axis_values = tuple(float(axis) for axis in axes)
    raw_delta_m = (
        axis_values[0] if len(axis_values) > 0 else 0.0,
        axis_values[1] if len(axis_values) > 1 else 0.0,
        axis_values[2] if len(axis_values) > 2 else 0.0,
    )
    deadzoned_delta_m = tuple(
        0.0 if abs(component) <= deadzone else component * step_m
        for component in raw_delta_m
    )
    return _clamp_vector3(deadzoned_delta_m, limit=max_delta_m)


def _gamepad_button_buttons(buttons: Sequence[ViewerControlGamepadButtonMessage]) -> tuple[bool, ...]:
    return tuple(button.pressed for button in buttons)


def _gamepad_button_values(buttons: Sequence[ViewerControlGamepadButtonMessage]) -> tuple[dict[str, object], ...]:
    return tuple({"pressed": button.pressed, "value": button.value} for button in buttons)


def _keyboard_button_values(
    key_state: Mapping[str, bool],
    active_key_codes: Sequence[str],
) -> tuple[bool, ...]:
    return tuple(key_state.get(key_code, False) for key_code in active_key_codes)


def _elapsed_ms(now_s: float, last_update_s: float) -> int:
    age_ms = int(round((now_s - last_update_s) * 1000.0))
    return age_ms if age_ms >= 0 else 0


def _stale_reason_for_timeout(timeout_ms: int) -> str:
    return f"command_age_ms_exceeded_timeout_{timeout_ms}"


@dataclass(frozen=True, slots=True)
class _ViewerFrameSpec:
    source_kind: str
    source_active: bool
    stale_reason: str | None
    desired_endpoint_m: tuple[float, float, float]
    values: tuple[float, ...]
    buttons: tuple[bool, ...]
    viewer_source_kind: str | None
    control_summary: Mapping[str, object]
    timestamp_s: float


class ViewerInputSource:
    """Stateful viewer control source that emits RawInputFrame objects."""

    def __init__(
        self,
        *,
        initial_endpoint_m: tuple[float, float, float] = DEFAULT_VIEWER_SAFE_ENDPOINT_M,
        timeout_ms: int = DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS,
        clock: Callable[[], float] = monotonic,
        keyboard_config: KeyboardInputConfig | None = None,
        gamepad_step_m: float = 0.01,
        gamepad_deadzone: float = 0.1,
        gamepad_max_delta_m: float = 0.03,
    ) -> None:
        if timeout_ms < 0:
            raise ValueError("timeout_ms must be non-negative")
        if not isfinite(gamepad_step_m) or gamepad_step_m < 0.0:
            raise ValueError("gamepad_step_m must be finite and non-negative")
        if not isfinite(gamepad_deadzone) or gamepad_deadzone < 0.0:
            raise ValueError("gamepad_deadzone must be finite and non-negative")
        if not isfinite(gamepad_max_delta_m) or gamepad_max_delta_m < 0.0:
            raise ValueError("gamepad_max_delta_m must be finite and non-negative")

        self._clock = clock
        self._timeout_ms = timeout_ms
        self._keyboard_config = build_default_keyboard_input_config() if keyboard_config is None else keyboard_config
        self._gamepad_step_m = float(gamepad_step_m)
        self._gamepad_deadzone = float(gamepad_deadzone)
        self._gamepad_max_delta_m = float(gamepad_max_delta_m)

        self._current_endpoint_m = _coerce_vector3("initial_endpoint_m", initial_endpoint_m)
        self._last_update_monotonic_s: float | None = None
        self._last_message_kind: str | None = None
        self._last_control_message: ViewerControlMessage | None = None
        self._last_frame = self._build_inactive_frame(
            source_kind=_VIEWER_SOURCE_KIND,
            stale_reason=_SOURCE_INACTIVE_STALE_REASON,
            timestamp_s=0.0,
            source_active=False,
            command_age_ms=0,
            viewer_source_kind=None,
            control_summary={
                "viewer_source_kind": None,
                "sequence": None,
                "keyboard": None,
                "gamepad": None,
            },
            values=(),
            buttons=(),
        )

    @property
    def last_control_message(self) -> ViewerControlMessage | None:
        return self._last_control_message

    @property
    def last_control_message_kind(self) -> str | None:
        return self._last_message_kind

    @property
    def current_endpoint_m(self) -> tuple[float, float, float]:
        return self._current_endpoint_m

    def rebase_current_endpoint_m(self, endpoint_m: Sequence[float]) -> None:
        self._current_endpoint_m = _coerce_vector3("endpoint_m", endpoint_m)

    def _build_inactive_frame(
        self,
        *,
        source_kind: str,
        stale_reason: str | None,
        timestamp_s: float,
        source_active: bool,
        command_age_ms: int | None,
        viewer_source_kind: str | None,
        control_summary: Mapping[str, object],
        values: tuple[float, ...],
        buttons: tuple[bool, ...],
    ) -> RawInputFrame:
        metadata: dict[str, object] = {
            "source_kind": source_kind,
            "source_active": source_active,
            "command_age_ms": command_age_ms,
            "stale_reason": stale_reason,
            "desired_endpoint_m": self._current_endpoint_m,
            "target_position_m": self._current_endpoint_m,
            "viewer_source_kind": viewer_source_kind,
            _VIEWER_CONTROL_SUMMARY_KEY: dict(control_summary),
        }
        return RawInputFrame(
            source=_VIEWER_SOURCE_KIND,
            timestamp_s=timestamp_s,
            values=values,
            buttons=buttons,
            metadata=metadata,
        )

    def _build_keyboard_frame(self, message: ViewerControlMessage, *, source_active: bool, stale_reason: str | None) -> _ViewerFrameSpec:
        assert message.keyboard is not None
        motion_command = build_keyboard_motion_command(
            message.keyboard.active_key_codes,
            current_tip_position_m=self._current_endpoint_m,
            timestamp_s=message.timestamp_s,
            config=self._keyboard_config,
        )
        desired_endpoint_m = _round_vector3(
            _coerce_vector3("desired_endpoint_m", motion_command.metadata["desired_endpoint_m"])
        )
        endpoint_delta_m = _round_vector3(
            _coerce_vector3("endpoint_delta_m", motion_command.metadata["endpoint_delta_m"])
        )
        key_state = dict(message.keyboard.key_state)
        summary = {
            "viewer_source_kind": "keyboard",
            "sequence": message.sequence,
            "keyboard": {
                "active_key_codes": message.keyboard.active_key_codes,
                "key_state": key_state,
                "focus_state": message.keyboard.focus_state,
                "zero_state": message.keyboard.zero_state,
            },
        }

        return _ViewerFrameSpec(
            source_kind=_VIEWER_KEYBOARD_SOURCE_KIND,
            source_active=source_active,
            stale_reason=stale_reason,
            desired_endpoint_m=desired_endpoint_m,
            values=endpoint_delta_m,
            buttons=_keyboard_button_values(key_state, message.keyboard.active_key_codes),
            viewer_source_kind="keyboard",
            control_summary=summary,
            timestamp_s=message.timestamp_s,
        )

    def _build_gamepad_frame(self, message: ViewerControlMessage, *, source_active: bool, stale_reason: str | None) -> _ViewerFrameSpec:
        assert message.gamepad is not None
        axis_delta_m = _coerce_axis_vector3(
            message.gamepad.axes,
            step_m=self._gamepad_step_m,
            deadzone=self._gamepad_deadzone,
            max_delta_m=self._gamepad_max_delta_m,
        )
        if message.gamepad.buttons:
            pressed_button_indices = {index for index, button in enumerate(message.gamepad.buttons) if button.pressed}
            if 0 in pressed_button_indices:
                axis_delta_m = (axis_delta_m[0], axis_delta_m[1], axis_delta_m[2] + self._gamepad_step_m)
            if 1 in pressed_button_indices:
                axis_delta_m = (axis_delta_m[0], axis_delta_m[1], axis_delta_m[2] - self._gamepad_step_m)

        desired_endpoint_m = _round_vector3(
            tuple(
                self._current_endpoint_m[index] + axis_delta_m[index]
                for index in range(3)
            )
        )
        summary = {
            "viewer_source_kind": "gamepad",
            "sequence": message.sequence,
            "gamepad": {
                "connected": message.gamepad.connected,
                "index": message.gamepad.index,
                "id": message.gamepad.id,
                "axes": message.gamepad.axes,
                "buttons": _gamepad_button_values(message.gamepad.buttons),
                "stale": message.gamepad.stale,
                "zero_state": message.gamepad.zero_state,
            },
        }

        return _ViewerFrameSpec(
            source_kind=_VIEWER_GAMEPAD_SOURCE_KIND,
            source_active=source_active,
            stale_reason=stale_reason,
            desired_endpoint_m=desired_endpoint_m,
            values=message.gamepad.axes,
            buttons=_gamepad_button_buttons(message.gamepad.buttons),
            viewer_source_kind="gamepad",
            control_summary=summary,
            timestamp_s=message.timestamp_s,
        )

    def _build_spec_from_message(self, message: ViewerControlMessage) -> _ViewerFrameSpec:
        if message.type != "viewer_control_message":
            raise ValueError("viewer control message type must be 'viewer_control_message'")

        if message.source_kind == "keyboard":
            if message.keyboard is None:
                raise ValueError("keyboard payload is required when source_kind is 'keyboard'")
            source_active = not (
                message.keyboard.zero_state is True or message.keyboard.focus_state == "blurred"
            )
            stale_reason = None if source_active else _VIEWER_KEYBOARD_INACTIVE_STALE_REASON
            return self._build_keyboard_frame(message, source_active=source_active, stale_reason=stale_reason)

        if message.gamepad is None:
            raise ValueError("gamepad payload is required when source_kind is 'gamepad'")
        source_active = not (
            message.gamepad.zero_state is True
            or message.gamepad.stale is True
            or message.gamepad.connected is False
        )
        stale_reason = None if source_active else _VIEWER_GAMEPAD_INACTIVE_STALE_REASON
        return self._build_gamepad_frame(message, source_active=source_active, stale_reason=stale_reason)

    def _build_frame_from_spec(
        self,
        spec: _ViewerFrameSpec,
        *,
        command_age_ms: int | None,
        stale_reason: str | None,
    ) -> RawInputFrame:
        metadata: dict[str, object] = {
            "source_kind": spec.source_kind,
            "source_active": spec.source_active,
            "command_age_ms": command_age_ms,
            "stale_reason": stale_reason,
            "desired_endpoint_m": spec.desired_endpoint_m,
            "target_position_m": spec.desired_endpoint_m,
            "viewer_source_kind": spec.viewer_source_kind,
            _VIEWER_CONTROL_SUMMARY_KEY: dict(spec.control_summary),
        }
        return RawInputFrame(
            source=_VIEWER_SOURCE_KIND,
            timestamp_s=spec.timestamp_s,
            values=spec.values,
            buttons=spec.buttons,
            metadata=metadata,
        )

    def ingest_control_message(self, message: ViewerControlMessage) -> RawInputFrame:
        spec = self._build_spec_from_message(message)

        self._last_update_monotonic_s = self._clock()
        self._last_message_kind = message.source_kind
        self._last_control_message = message
        self._last_frame = self._build_frame_from_spec(spec, command_age_ms=0, stale_reason=spec.stale_reason)
        return self._last_frame

    def ingest_control_message_json(self, message: str) -> RawInputFrame:
        return self.ingest_control_message(parse_viewer_control_message_json(message))

    def read_frame(self) -> RawInputFrame:
        if self._last_update_monotonic_s is None or self._last_message_kind is None:
            self._last_frame = self._build_inactive_frame(
                source_kind=_VIEWER_SOURCE_KIND,
                stale_reason=_SOURCE_INACTIVE_STALE_REASON,
                timestamp_s=0.0,
                source_active=False,
                command_age_ms=0,
                viewer_source_kind=None,
                control_summary={
                    "viewer_source_kind": None,
                    "sequence": None,
                    "keyboard": None,
                    "gamepad": None,
                },
                values=(),
                buttons=(),
            )
            return self._last_frame

        age_ms = _elapsed_ms(self._clock(), self._last_update_monotonic_s)
        stale_reason = None
        source_active = bool(self._last_frame.metadata.get("source_active", False))

        if age_ms > self._timeout_ms:
            stale_reason = _stale_reason_for_timeout(self._timeout_ms)
            source_active = False
            source_kind = self._last_frame.metadata.get("source_kind", _VIEWER_SOURCE_KIND)
        else:
            source_kind = self._last_frame.metadata.get("source_kind", _VIEWER_SOURCE_KIND)
            if not source_active:
                stale_reason = self._last_frame.metadata.get("stale_reason")  # type: ignore[assignment]

        metadata = dict(self._last_frame.metadata)
        metadata["source_kind"] = source_kind
        metadata["source_active"] = source_active
        metadata["command_age_ms"] = age_ms
        metadata["stale_reason"] = stale_reason
        self._last_frame = RawInputFrame(
            source=self._last_frame.source,
            timestamp_s=self._last_frame.timestamp_s,
            values=self._last_frame.values,
            buttons=self._last_frame.buttons,
            metadata=metadata,
        )
        return self._last_frame


__all__ = [
    "DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS",
    "DEFAULT_VIEWER_SAFE_ENDPOINT_M",
    "ViewerInputSource",
]
