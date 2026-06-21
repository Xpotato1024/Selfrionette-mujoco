from __future__ import annotations

import json
from pathlib import Path

import pytest

from selfrionette.input_sources import (
    KeyboardBinding,
    KeyboardInputConfig,
    build_default_keyboard_input_config,
    build_keyboard_motion_command,
)
from selfrionette.runtime import resolve_desired_endpoint_from_motion_command
from selfrionette.schemas import MotionCommand


def test_default_keyboard_keybind_contract_matches_reserved_config() -> None:
    config_path = Path("configs/input/keyboard_default.json")
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    config = build_default_keyboard_input_config()

    assert payload["source_kind"] == "keyboard"
    assert payload["step_m"] == 0.01
    assert payload["deadzone"] == 0.0
    assert payload["max_delta_m"] == 0.03
    assert config.bindings["KeyW"] == KeyboardBinding(axis="y", direction=1)
    assert config.bindings["KeyS"] == KeyboardBinding(axis="y", direction=-1)
    assert config.bindings["KeyA"] == KeyboardBinding(axis="x", direction=-1)
    assert config.bindings["KeyD"] == KeyboardBinding(axis="x", direction=1)
    assert config.bindings["Space"] == KeyboardBinding(axis="z", direction=1)
    assert config.bindings["ShiftLeft"] == KeyboardBinding(axis="z", direction=-1)
    assert config.bindings["ShiftRight"] == KeyboardBinding(axis="z", direction=-1)


@pytest.mark.parametrize(
    ("pressed_keys", "expected_delta_m"),
    [
        (("KeyW",), (0.0, 0.01, 0.0)),
        (("KeyS",), (0.0, -0.01, 0.0)),
        (("KeyA",), (-0.01, 0.0, 0.0)),
        (("KeyD",), (0.01, 0.0, 0.0)),
        (("Space",), (0.0, 0.0, 0.01)),
        (("ShiftLeft",), (0.0, 0.0, -0.01)),
        (("ShiftRight",), (0.0, 0.0, -0.01)),
    ],
)
def test_keyboard_pressed_keys_map_to_expected_axis_delta(
    pressed_keys: tuple[str, ...],
    expected_delta_m: tuple[float, float, float],
) -> None:
    command = build_keyboard_motion_command(
        pressed_keys,
        current_tip_position_m=(1.0, 2.0, 3.0),
        timestamp_s=12.5,
    )

    assert command.target is None
    assert command.metadata["source_kind"] == "keyboard"
    assert command.metadata["pressed_keys"] == tuple(sorted(pressed_keys))
    assert command.metadata["endpoint_delta_m"] == expected_delta_m
    assert command.metadata["current_tip_position_m"] == (1.0, 2.0, 3.0)
    assert command.metadata["desired_endpoint_m"] == tuple(
        current + delta for current, delta in zip((1.0, 2.0, 3.0), expected_delta_m, strict=True)
    )


def test_keyboard_opposite_keys_cancel_on_same_axis() -> None:
    command = build_keyboard_motion_command(
        ("KeyW", "KeyS", "KeyA", "KeyD"),
        current_tip_position_m=(0.5, 0.5, 0.5),
        timestamp_s=1.0,
    )

    assert command.metadata["endpoint_delta_m"] == (0.0, 0.0, 0.0)
    assert command.metadata["desired_endpoint_m"] == (0.5, 0.5, 0.5)


def test_keyboard_max_delta_m_clamps_total_delta() -> None:
    config = KeyboardInputConfig(
        bindings={
            "KeyW": KeyboardBinding(axis="y", direction=1),
            "KeyD": KeyboardBinding(axis="x", direction=1),
            "Space": KeyboardBinding(axis="z", direction=1),
        },
        step_m=0.1,
        deadzone=0.0,
        max_delta_m=0.03,
    )

    command = build_keyboard_motion_command(
        ("KeyW", "KeyD", "Space"),
        current_tip_position_m=(0.0, 0.0, 0.0),
        timestamp_s=2.0,
        config=config,
    )

    endpoint_delta_m = command.metadata["endpoint_delta_m"]
    assert sum(component * component for component in endpoint_delta_m) <= 0.03 * 0.03 + 1e-12


def test_keyboard_empty_key_state_is_no_op() -> None:
    command = build_keyboard_motion_command(
        (),
        current_tip_position_m=(0.1, 0.2, 0.3),
        timestamp_s=0.0,
    )

    assert command.metadata["endpoint_delta_m"] == (0.0, 0.0, 0.0)
    assert command.metadata["desired_endpoint_m"] == (0.1, 0.2, 0.3)


def test_keyboard_motion_command_resolves_desired_endpoint() -> None:
    command = build_keyboard_motion_command(
        ("KeyW", "KeyA"),
        current_tip_position_m=(0.1, 0.2, 0.3),
        timestamp_s=0.5,
    )

    resolved = resolve_desired_endpoint_from_motion_command(command)

    assert resolved.desired_endpoint_m == command.metadata["desired_endpoint_m"]
    assert resolved.source == 'MotionCommand.metadata["desired_endpoint_m"]'


@pytest.mark.parametrize(
    ("config_kwargs", "match"),
    [
        ({"bindings": {"KeyW": type("InvalidBinding", (), {"axis": "q", "direction": 1})()}, "step_m": 0.01, "deadzone": 0.0, "max_delta_m": 0.03}, "unknown axis"),
        ({"bindings": {"KeyW": KeyboardBinding(axis="x", direction=1)}, "step_m": -0.01, "deadzone": 0.0, "max_delta_m": 0.03}, "step_m must be non-negative"),
        ({"bindings": {"KeyW": KeyboardBinding(axis="x", direction=1)}, "step_m": 0.01, "deadzone": 0.0, "max_delta_m": -0.03}, "max_delta_m must be non-negative"),
    ],
)
def test_keyboard_config_validation_rejects_invalid_values(config_kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        KeyboardInputConfig(**config_kwargs)


def test_keyboard_current_tip_position_validation_rejects_bad_values() -> None:
    with pytest.raises(ValueError, match="must contain exactly three values"):
        build_keyboard_motion_command(("KeyW",), current_tip_position_m=(0.0, 0.0), timestamp_s=0.0)

    with pytest.raises(ValueError, match="must contain only finite values"):
        build_keyboard_motion_command(("KeyW",), current_tip_position_m=(0.0, float("nan"), 0.0), timestamp_s=0.0)
