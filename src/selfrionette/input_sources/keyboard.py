from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite, sqrt
from pathlib import Path

from selfrionette.schemas import MotionCommand, RawInputFrame

_VALID_AXES = {"x", "y", "z"}
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "input" / "keyboard_default.json"


@dataclass(frozen=True, slots=True)
class KeyboardBinding:
    axis: str
    direction: int

    def __post_init__(self) -> None:
        if self.axis not in _VALID_AXES:
            raise ValueError(f"unknown axis: {self.axis!r}")
        if self.direction not in {-1, 1}:
            raise ValueError("direction must be -1 or +1")


@dataclass(frozen=True, slots=True)
class KeyboardInputConfig:
    bindings: Mapping[str, KeyboardBinding]
    speed_m_s: float
    deadzone: float
    max_delta_m: float

    def __post_init__(self) -> None:
        if not isfinite(self.speed_m_s):
            raise ValueError("speed_m_s must be finite")
        if self.speed_m_s < 0.0:
            raise ValueError("speed_m_s must be non-negative")

        if not isfinite(self.deadzone):
            raise ValueError("deadzone must be finite")
        if self.deadzone < 0.0:
            raise ValueError("deadzone must be non-negative")

        if not isfinite(self.max_delta_m):
            raise ValueError("max_delta_m must be finite")
        if self.max_delta_m < 0.0:
            raise ValueError("max_delta_m must be non-negative")

        for key_code, binding in self.bindings.items():
            if not isinstance(key_code, str) or not key_code:
                raise ValueError("binding key codes must be non-empty strings")

            binding_axis = getattr(binding, "axis", None)
            binding_direction = getattr(binding, "direction", None)
            if binding_axis not in _VALID_AXES:
                raise ValueError(f"unknown axis: {binding_axis!r}")
            if binding_direction not in {-1, 1}:
                raise ValueError("direction must be -1 or +1")


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


def _coerce_pressed_keys(pressed_keys: Iterable[str]) -> tuple[str, ...]:
    deduplicated_keys = dict.fromkeys(pressed_keys)
    return tuple(sorted(deduplicated_keys))


def _clamp_vector3(vector: tuple[float, float, float], *, limit: float) -> tuple[float, float, float]:
    magnitude = sqrt(sum(component * component for component in vector))
    if magnitude == 0.0 or magnitude <= limit:
        return vector

    scale = limit / magnitude
    return tuple(component * scale for component in vector)


def _load_keyboard_config_from_path(path: Path) -> KeyboardInputConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("keyboard config must be a JSON object")

    if payload.get("source_kind") != "keyboard":
        raise ValueError("keyboard config source_kind must be 'keyboard'")

    bindings_payload = payload.get("bindings")
    if not isinstance(bindings_payload, dict):
        raise ValueError("keyboard config bindings must be a JSON object")

    bindings: dict[str, KeyboardBinding] = {}
    for key_code, binding_payload in bindings_payload.items():
        if not isinstance(binding_payload, dict):
            raise ValueError(f"binding {key_code!r} must be a JSON object")

        if "axis" not in binding_payload or "direction" not in binding_payload:
            raise ValueError(f"binding {key_code!r} must include axis and direction")

        bindings[key_code] = KeyboardBinding(
            axis=str(binding_payload["axis"]),
            direction=int(binding_payload["direction"]),
        )

    return KeyboardInputConfig(
        bindings=bindings,
        speed_m_s=float(payload["speed_m_s"]),
        deadzone=float(payload["deadzone"]),
        max_delta_m=float(payload["max_delta_m"]),
    )


def build_default_keyboard_input_config() -> KeyboardInputConfig:
    return _load_keyboard_config_from_path(_DEFAULT_CONFIG_PATH)


def build_keyboard_motion_command(
    pressed_keys: Iterable[str],
    *,
    current_tip_position_m: tuple[float, float, float],
    timestamp_s: float,
    config: KeyboardInputConfig | None = None,
) -> MotionCommand:
    keyboard_config = build_default_keyboard_input_config() if config is None else config
    current_tip_position_m = _coerce_vector3("current_tip_position_m", current_tip_position_m)
    pressed_key_tuple = _coerce_pressed_keys(pressed_keys)

    axis_by_axis = {"x": 0.0, "y": 0.0, "z": 0.0}
    for key_code in pressed_key_tuple:
        binding = keyboard_config.bindings.get(key_code)
        if binding is None:
            continue
        axis_by_axis[binding.axis] += float(binding.direction)

    axis_values = _clamp_vector3(
        (
            axis_by_axis["x"],
            axis_by_axis["y"],
            axis_by_axis["z"],
        ),
        limit=1.0,
    )

    if keyboard_config.deadzone > 0.0:
        axis_values = tuple(
            0.0 if abs(component) <= keyboard_config.deadzone else component
            for component in axis_values
        )

    endpoint_velocity_m_s = tuple(
        component * keyboard_config.speed_m_s for component in axis_values
    )

    return MotionCommand(
        timestamp_s=timestamp_s,
        metadata={
            "source_kind": "keyboard",
            "intent_kind": "local_endpoint_velocity",
            "input_continuity": "continuous",
            "pressed_keys": pressed_key_tuple,
            "axis_values": axis_values,
            "local_endpoint_speed_m_s": keyboard_config.speed_m_s,
            "local_endpoint_max_delta_m": keyboard_config.max_delta_m,
            "endpoint_velocity_m_s": endpoint_velocity_m_s,
            "current_tip_position_m": current_tip_position_m,
        },
    )


__all__ = [
    "KeyboardBinding",
    "KeyboardInputConfig",
    "build_default_keyboard_input_config",
    "build_keyboard_motion_command",
]
