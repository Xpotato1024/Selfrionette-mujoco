from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

ViewerControlSourceKind = Literal["keyboard", "gamepad"]
ViewerControlEnvelopeType = Literal["viewer_control_message"]
ViewerControlKeyboardFocusState = Literal["focused", "blurred"]


class ViewerControlMessageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ViewerControlKeyboardMessage:
    active_key_codes: tuple[str, ...] = ()
    key_state: Mapping[str, bool] = field(default_factory=dict)
    focus_state: ViewerControlKeyboardFocusState | None = None
    zero_state: bool | None = None


@dataclass(frozen=True, slots=True)
class ViewerControlGamepadButtonMessage:
    pressed: bool
    value: float | None = None


@dataclass(frozen=True, slots=True)
class ViewerControlGamepadMessage:
    connected: bool
    index: int | None = None
    id: str | None = None
    axes: tuple[float, ...] = ()
    buttons: tuple[ViewerControlGamepadButtonMessage, ...] = ()
    stale: bool | None = None
    zero_state: bool | None = None


@dataclass(frozen=True, slots=True)
class ViewerControlMessage:
    type: ViewerControlEnvelopeType
    timestamp_s: float
    source_kind: ViewerControlSourceKind
    sequence: int | None = None
    keyboard: ViewerControlKeyboardMessage | None = None
    gamepad: ViewerControlGamepadMessage | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


def _is_plain_mapping(value: object) -> bool:
    return isinstance(value, Mapping)


def _is_str(value: object) -> bool:
    return isinstance(value, str)


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value not in {float("inf"), float("-inf")}


def _ensure_allowed_keys(payload: Mapping[str, object], allowed_keys: set[str], context: str) -> None:
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        unknown = ", ".join(unknown_keys)
        raise ViewerControlMessageError(f"{context} contains unknown fields: {unknown}")


def _coerce_string_tuple(value: object, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not _is_str(item) for item in value):
        raise ViewerControlMessageError(f"{context} must be an array of strings")
    return tuple(value)


def _coerce_number_tuple(value: object, *, context: str) -> tuple[float, ...]:
    if not isinstance(value, list) or any(not _is_finite_number(item) for item in value):
        raise ViewerControlMessageError(f"{context} must be an array of finite numbers")
    return tuple(float(item) for item in value)


def _coerce_key_state(value: object, *, context: str) -> dict[str, bool]:
    if not _is_plain_mapping(value):
        raise ViewerControlMessageError(f"{context} must be a JSON object")

    key_state: dict[str, bool] = {}
    for key, mapped_value in value.items():
        if not _is_str(key):
            raise ViewerControlMessageError(f"{context} keys must be strings")
        if not _is_bool(mapped_value):
            raise ViewerControlMessageError(f"{context}[{key!r}] must be a boolean")
        key_state[key] = mapped_value

    return key_state


def _coerce_optional_bool(value: object, *, context: str) -> bool | None:
    if value is None:
        raise ViewerControlMessageError(f"{context} must be a boolean")
    if not _is_bool(value):
        raise ViewerControlMessageError(f"{context} must be a boolean")
    return value


def _coerce_optional_focus_state(value: object, *, context: str) -> ViewerControlKeyboardFocusState | None:
    if value is None:
        raise ViewerControlMessageError(f"{context} must be 'focused' or 'blurred'")
    if value not in {"focused", "blurred"}:
        raise ViewerControlMessageError(f"{context} must be 'focused' or 'blurred'")
    return value


def _coerce_optional_number(value: object, *, context: str) -> float | None:
    if value is None:
        raise ViewerControlMessageError(f"{context} must be a finite number")
    if not _is_finite_number(value):
        raise ViewerControlMessageError(f"{context} must be a finite number")
    return float(value)


def _coerce_gamepad_button_message(value: object, *, context: str) -> ViewerControlGamepadButtonMessage:
    if not _is_plain_mapping(value):
        raise ViewerControlMessageError(f"{context} must be a JSON object")

    allowed_keys = {"pressed", "value"}
    _ensure_allowed_keys(value, allowed_keys, context)

    if "pressed" not in value:
        raise ViewerControlMessageError(f"{context}.pressed is required")
    if not _is_bool(value["pressed"]):
        raise ViewerControlMessageError(f"{context}.pressed must be a boolean")

    pressed = value["pressed"]
    button_value = _coerce_optional_number(value["value"], context=f"{context}.value") if "value" in value else None

    return ViewerControlGamepadButtonMessage(pressed=pressed, value=button_value)


def _coerce_button_tuple(
    value: object,
    *,
    context: str,
) -> tuple[ViewerControlGamepadButtonMessage, ...]:
    if not isinstance(value, list):
        raise ViewerControlMessageError(f"{context} must be an array")

    buttons: list[ViewerControlGamepadButtonMessage] = []
    for index, button_value in enumerate(value):
        buttons.append(_coerce_gamepad_button_message(button_value, context=f"{context}[{index}]"))

    return tuple(buttons)


def _coerce_keyboard_message(value: object) -> ViewerControlKeyboardMessage:
    if not _is_plain_mapping(value):
        raise ViewerControlMessageError("keyboard must be a JSON object")

    allowed_keys = {"active_key_codes", "key_state", "focus_state", "zero_state"}
    _ensure_allowed_keys(value, allowed_keys, "keyboard")

    if "active_key_codes" not in value:
        raise ViewerControlMessageError("keyboard.active_key_codes is required")
    if "key_state" not in value:
        raise ViewerControlMessageError("keyboard.key_state is required")

    active_key_codes = _coerce_string_tuple(value["active_key_codes"], context="keyboard.active_key_codes")
    key_state = _coerce_key_state(value["key_state"], context="keyboard.key_state")
    focus_state = _coerce_optional_focus_state(value["focus_state"], context="keyboard.focus_state") if "focus_state" in value else None
    zero_state = _coerce_optional_bool(value["zero_state"], context="keyboard.zero_state") if "zero_state" in value else None

    return ViewerControlKeyboardMessage(
        active_key_codes=active_key_codes,
        key_state=key_state,
        focus_state=focus_state,
        zero_state=zero_state,
    )


def _coerce_gamepad_message(value: object) -> ViewerControlGamepadMessage:
    if not _is_plain_mapping(value):
        raise ViewerControlMessageError("gamepad must be a JSON object")

    allowed_keys = {"index", "id", "connected", "axes", "buttons", "stale", "zero_state"}
    _ensure_allowed_keys(value, allowed_keys, "gamepad")

    if "connected" not in value:
        raise ViewerControlMessageError("gamepad.connected is required")
    if "axes" not in value:
        raise ViewerControlMessageError("gamepad.axes is required")
    if "buttons" not in value:
        raise ViewerControlMessageError("gamepad.buttons is required")

    if "index" in value:
        index = value["index"]
        if not _is_int(index):
            raise ViewerControlMessageError("gamepad.index must be an integer")
        index = int(index)
    else:
        index = None

    if "id" in value:
        gamepad_id = value["id"]
        if not _is_str(gamepad_id):
            raise ViewerControlMessageError("gamepad.id must be a string")
    else:
        gamepad_id = None
    if not _is_bool(value["connected"]):
        raise ViewerControlMessageError("gamepad.connected must be a boolean")

    axes = _coerce_number_tuple(value["axes"], context="gamepad.axes")
    buttons = _coerce_button_tuple(value["buttons"], context="gamepad.buttons")
    stale = _coerce_optional_bool(value["stale"], context="gamepad.stale") if "stale" in value else None
    zero_state = _coerce_optional_bool(value["zero_state"], context="gamepad.zero_state") if "zero_state" in value else None

    return ViewerControlGamepadMessage(
        index=index,
        id=gamepad_id,
        connected=value["connected"],
        axes=axes,
        buttons=buttons,
        stale=stale,
        zero_state=zero_state,
    )


def coerce_viewer_control_message(payload: object) -> ViewerControlMessage:
    if not _is_plain_mapping(payload):
        raise ViewerControlMessageError("Invalid viewer control message: expected a JSON object")

    allowed_keys = {"type", "timestamp_s", "source_kind", "sequence", "keyboard", "gamepad", "metadata"}
    _ensure_allowed_keys(payload, allowed_keys, "viewer control message")

    if payload.get("type") != "viewer_control_message":
        raise ViewerControlMessageError("viewer control message type must be 'viewer_control_message'")
    if "timestamp_s" not in payload:
        raise ViewerControlMessageError("viewer control message.timestamp_s is required")
    if "source_kind" not in payload:
        raise ViewerControlMessageError("viewer control message.source_kind is required")

    timestamp_s = payload["timestamp_s"]
    if not _is_finite_number(timestamp_s):
        raise ViewerControlMessageError("viewer control message.timestamp_s must be a finite number")

    source_kind = payload["source_kind"]
    if source_kind not in {"keyboard", "gamepad"}:
        raise ViewerControlMessageError("viewer control message.source_kind must be 'keyboard' or 'gamepad'")

    if "sequence" in payload:
        sequence = payload["sequence"]
        if not _is_int(sequence):
            raise ViewerControlMessageError("viewer control message.sequence must be an integer")
    else:
        sequence = None

    metadata = payload["metadata"] if "metadata" in payload else {}
    if not _is_plain_mapping(metadata):
        raise ViewerControlMessageError("viewer control message.metadata must be a JSON object")
    metadata_copy: dict[str, object] = {}
    for key, value_item in metadata.items():
        if not _is_str(key):
            raise ViewerControlMessageError("viewer control message.metadata keys must be strings")
        metadata_copy[key] = value_item

    keyboard_present = "keyboard" in payload
    gamepad_present = "gamepad" in payload
    if source_kind == "keyboard":
        if not keyboard_present:
            raise ViewerControlMessageError("keyboard payload is required when source_kind is 'keyboard'")
        if gamepad_present:
            raise ViewerControlMessageError("gamepad payload is not allowed when source_kind is 'keyboard'")
        keyboard = _coerce_keyboard_message(payload["keyboard"])
        gamepad = None
    else:
        if not gamepad_present:
            raise ViewerControlMessageError("gamepad payload is required when source_kind is 'gamepad'")
        if keyboard_present:
            raise ViewerControlMessageError("keyboard payload is not allowed when source_kind is 'gamepad'")
        keyboard = None
        gamepad = _coerce_gamepad_message(payload["gamepad"])

    return ViewerControlMessage(
        type="viewer_control_message",
        timestamp_s=float(timestamp_s),
        source_kind=source_kind,
        sequence=sequence,
        keyboard=keyboard,
        gamepad=gamepad,
        metadata=metadata_copy,
    )


def parse_viewer_control_message_json(message: str) -> ViewerControlMessage:
    try:
        payload = json.loads(message)
    except json.JSONDecodeError as exc:
        raise ViewerControlMessageError("Invalid viewer control message: malformed JSON") from exc

    return coerce_viewer_control_message(payload)


__all__ = [
    "ViewerControlEnvelopeType",
    "ViewerControlGamepadButtonMessage",
    "ViewerControlGamepadMessage",
    "ViewerControlKeyboardFocusState",
    "ViewerControlKeyboardMessage",
    "ViewerControlMessage",
    "ViewerControlMessageError",
    "ViewerControlSourceKind",
    "coerce_viewer_control_message",
    "parse_viewer_control_message_json",
]
