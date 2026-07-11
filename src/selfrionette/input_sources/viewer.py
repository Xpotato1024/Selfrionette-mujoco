from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from time import monotonic

from selfrionette.input_sources.keyboard import (
    KeyboardInputConfig,
    build_default_keyboard_input_config,
    build_keyboard_continuous_velocity_intent,
)
from selfrionette.input_sources.continuous_endpoint_velocity import build_continuous_endpoint_velocity_intent
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
_DEFAULT_CONTROL_FRAME = "world"
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


def _round_vector3(vector: tuple[float, float, float], *, places: int = 12) -> tuple[float, float, float]:
    return tuple(round(component, places) for component in vector)


def _normalize_control_frame(value: object) -> str:
    if not isinstance(value, str):
        return _DEFAULT_CONTROL_FRAME

    normalized_control_frame = value.strip().lower()
    if normalized_control_frame in {"world", "tool"}:
        return normalized_control_frame

    return _DEFAULT_CONTROL_FRAME


def _coerce_axis_vector3(axes: Sequence[float]) -> tuple[float, float, float]:
    axis_values = tuple(float(axis) for axis in axes)
    raw_axis_values = (
        axis_values[0] if len(axis_values) > 0 else 0.0,
        axis_values[1] if len(axis_values) > 1 else 0.0,
        axis_values[2] if len(axis_values) > 2 else 0.0,
    )
    return raw_axis_values


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
    intent_metadata: Mapping[str, object]
    source_kind: str
    intent_kind: str
    input_continuity: str
    control_frame: str
    source_active: bool
    stale_reason: str | None
    desired_endpoint_m: tuple[float, float, float]
    local_endpoint_velocity_m_s: tuple[float, float, float]
    endpoint_velocity_m_s: tuple[float, float, float]
    current_tip_position_m: tuple[float, float, float]
    axis_values: tuple[float, float, float]
    local_endpoint_speed_m_s: float
    local_endpoint_max_delta_m: float
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
        gamepad_speed_m_s: float = 0.1,
        gamepad_deadzone: float = 0.1,
        gamepad_max_delta_m: float = 0.03,
    ) -> None:
        if timeout_ms < 0:
            raise ValueError("timeout_ms must be non-negative")
        if not isfinite(gamepad_speed_m_s) or gamepad_speed_m_s < 0.0:
            raise ValueError("gamepad_speed_m_s must be finite and non-negative")
        if not isfinite(gamepad_deadzone) or gamepad_deadzone < 0.0:
            raise ValueError("gamepad_deadzone must be finite and non-negative")
        if not isfinite(gamepad_max_delta_m) or gamepad_max_delta_m < 0.0:
            raise ValueError("gamepad_max_delta_m must be finite and non-negative")

        self._clock = clock
        self._timeout_ms = timeout_ms
        self._keyboard_config = build_default_keyboard_input_config() if keyboard_config is None else keyboard_config
        self._gamepad_speed_m_s = float(gamepad_speed_m_s)
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
                "metadata": {},
                "intent_kind": None,
                "input_continuity": None,
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
            "control_frame": _DEFAULT_CONTROL_FRAME,
            _VIEWER_CONTROL_SUMMARY_KEY: dict(control_summary),
            "intent_kind": None,
            "input_continuity": None,
            "local_endpoint_velocity_frame": _DEFAULT_CONTROL_FRAME,
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
        control_frame = _normalize_control_frame(message.metadata.get("control_frame", _DEFAULT_CONTROL_FRAME))
        intent = build_keyboard_continuous_velocity_intent(
            message.keyboard.active_key_codes,
            timestamp_s=message.timestamp_s,
            config=self._keyboard_config,
            control_frame=control_frame,
            source_active=source_active,
            stale_reason=stale_reason,
            source_kind=_VIEWER_KEYBOARD_SOURCE_KIND,
        )
        axis_values = _round_vector3(intent.axis_values)
        endpoint_velocity_m_s = _round_vector3(intent.local_endpoint_velocity_m_s)
        desired_endpoint_m = _round_vector3(self._current_endpoint_m)
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
            "metadata": dict(message.metadata),
            "intent_kind": intent.intent_kind,
            "input_continuity": intent.input_continuity,
            "control_frame": control_frame,
        }

        return _ViewerFrameSpec(
            intent_metadata=intent.to_metadata(),
            source_kind=_VIEWER_KEYBOARD_SOURCE_KIND,
            intent_kind=intent.intent_kind,
            input_continuity=intent.input_continuity,
            control_frame=control_frame,
            source_active=source_active,
            stale_reason=stale_reason,
            desired_endpoint_m=desired_endpoint_m,
            local_endpoint_velocity_m_s=_round_vector3(
                _coerce_vector3(
                    "local_endpoint_velocity_m_s",
                    intent.local_endpoint_velocity_m_s,
                )
            ),
            endpoint_velocity_m_s=endpoint_velocity_m_s,
            current_tip_position_m=_round_vector3(self._current_endpoint_m),
            axis_values=axis_values,
            local_endpoint_speed_m_s=intent.local_endpoint_speed_m_s,
            local_endpoint_max_delta_m=intent.local_endpoint_max_delta_m,
            values=axis_values,
            buttons=_keyboard_button_values(key_state, message.keyboard.active_key_codes),
            viewer_source_kind="keyboard",
            control_summary=summary,
            timestamp_s=message.timestamp_s,
        )

    def _build_gamepad_frame(self, message: ViewerControlMessage, *, source_active: bool, stale_reason: str | None) -> _ViewerFrameSpec:
        assert message.gamepad is not None
        control_frame = _normalize_control_frame(message.metadata.get("control_frame", _DEFAULT_CONTROL_FRAME))
        raw_axis_values = _coerce_axis_vector3(message.gamepad.axes)
        supplemental_axis_values = (0.0, 0.0, 0.0)
        if message.gamepad.buttons:
            pressed_button_indices = {index for index, button in enumerate(message.gamepad.buttons) if button.pressed}
            if 0 in pressed_button_indices:
                supplemental_axis_values = (0.0, 0.0, supplemental_axis_values[2] + 1.0)
            if 1 in pressed_button_indices:
                supplemental_axis_values = (0.0, 0.0, supplemental_axis_values[2] - 1.0)
        intent = build_continuous_endpoint_velocity_intent(
            raw_axis_values,
            source_kind=_VIEWER_GAMEPAD_SOURCE_KIND,
            source_timestamp_s=message.timestamp_s,
            speed_m_s=self._gamepad_speed_m_s,
            deadzone=self._gamepad_deadzone,
            max_delta_m=self._gamepad_max_delta_m,
            control_frame=control_frame,
            source_active=source_active,
            stale_reason=stale_reason,
            supplemental_axis_values=supplemental_axis_values,
            source_diagnostics={"raw_axes": tuple(message.gamepad.axes)},
        )
        axis_values = intent.axis_values
        endpoint_velocity_m_s = _round_vector3(intent.local_endpoint_velocity_m_s)
        desired_endpoint_m = _round_vector3(self._current_endpoint_m)
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
            "metadata": dict(message.metadata),
            "intent_kind": "local_endpoint_velocity",
            "input_continuity": "continuous",
            "control_frame": control_frame,
        }

        return _ViewerFrameSpec(
            intent_metadata=intent.to_metadata(),
            source_kind=_VIEWER_GAMEPAD_SOURCE_KIND,
            intent_kind="local_endpoint_velocity",
            input_continuity="continuous",
            control_frame=control_frame,
            source_active=source_active,
            stale_reason=stale_reason,
            desired_endpoint_m=desired_endpoint_m,
            local_endpoint_velocity_m_s=_round_vector3(
                tuple(component * self._gamepad_speed_m_s for component in axis_values)
            ),
            endpoint_velocity_m_s=endpoint_velocity_m_s,
            current_tip_position_m=_round_vector3(self._current_endpoint_m),
            axis_values=axis_values,
            local_endpoint_speed_m_s=self._gamepad_speed_m_s,
            local_endpoint_max_delta_m=self._gamepad_max_delta_m,
            values=axis_values,
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
        metadata: dict[str, object] = dict(spec.intent_metadata)
        metadata.update({
            "source_kind": spec.source_kind,
            "intent_kind": spec.intent_kind,
            "input_continuity": spec.input_continuity,
            "source_active": spec.source_active,
            "command_age_ms": command_age_ms,
            "stale_reason": stale_reason,
            "desired_endpoint_m": spec.desired_endpoint_m,
            "target_position_m": spec.desired_endpoint_m,
            "control_frame": spec.control_frame,
            "endpoint_velocity_m_s": spec.endpoint_velocity_m_s,
            "local_endpoint_velocity_m_s": spec.local_endpoint_velocity_m_s,
            "local_endpoint_velocity_frame": spec.control_frame,
            "axis_values": spec.axis_values,
            "local_endpoint_speed_m_s": spec.local_endpoint_speed_m_s,
            "local_endpoint_max_delta_m": spec.local_endpoint_max_delta_m,
            "current_tip_position_m": spec.current_tip_position_m,
            "viewer_source_kind": spec.viewer_source_kind,
            _VIEWER_CONTROL_SUMMARY_KEY: dict(spec.control_summary),
        })
        if spec.control_frame == _DEFAULT_CONTROL_FRAME:
            metadata["resolved_world_endpoint_velocity_m_s"] = spec.endpoint_velocity_m_s
            metadata["endpoint_velocity_frame"] = "mujoco_world"
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
                    "metadata": {},
                    "intent_kind": None,
                    "input_continuity": None,
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
