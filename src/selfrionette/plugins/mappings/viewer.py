"""Behavior-preserving keyboard/gamepad Control Mapping Plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite

from selfrionette.plugins.mappings.continuous_endpoint_velocity import (
    build_continuous_endpoint_velocity_intent,
)
from selfrionette.plugins.mappings.keyboard import (
    build_default_keyboard_input_config,
    build_keyboard_continuous_velocity_intent,
)
from selfrionette.runtime.experiment.contracts import (
    ControlMappingPlugin,
    ControlMappingStrategy,
    ParameterContract,
    VersionedIdentity,
)
from selfrionette.schemas import InputIntent, RawInputFrame
from selfrionette.schemas.viewer_input import (
    VIEWER_CONTROL_SAMPLE_SCHEMA,
    ViewerCanonicalInputSample,
)

VIEWER_CONTROL_MAPPING_IDENTITY = VersionedIdentity("viewer_keyboard_gamepad_mapping", 1)
VIEWER_MAPPING_SEMANTICS_IDENTITY = VersionedIdentity("viewer_keyboard_gamepad_semantics", 1)
VIEWER_CONTROL_SAMPLE_IDENTITY = VersionedIdentity("viewer_control_sample", 1)


def _as_json_wire_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _as_json_wire_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_as_json_wire_value(item) for item in value]
    return value


def _coerce_frame_sample(frame: RawInputFrame) -> ViewerCanonicalInputSample:
    sample = frame.metadata.get("viewer_input_sample")
    if not isinstance(sample, Mapping):
        raise ValueError("viewer mapping requires canonical viewer_input_sample metadata")
    if sample.get("schema") != VIEWER_CONTROL_SAMPLE_SCHEMA:
        raise ValueError("viewer mapping received an incompatible canonical sample schema")

    source_kind = sample.get("source_kind")
    provider_id = sample.get("provider_id")
    provider_schema = sample.get("provider_schema")
    if source_kind == "keyboard":
        keyboard_payload = sample.get("keyboard")
        if not isinstance(keyboard_payload, Mapping):
            raise ValueError("viewer keyboard sample payload is required")
        keyboard = frame.metadata["viewer_control_message"]
        if not isinstance(keyboard, Mapping) or not isinstance(keyboard.get("keyboard"), Mapping):
            raise ValueError("viewer keyboard compatibility payload is invalid")
        # Reuse the already validated wire message through the source-owned
        # compatibility object; no frontend or transport import is required.
        from selfrionette.schemas import coerce_viewer_control_message

        message_payload = {
            "type": "viewer_control_message",
            "timestamp_s": sample.get("timestamp_s"),
            "source_kind": "keyboard",
            "keyboard": _as_json_wire_value(keyboard["keyboard"]),
            "metadata": dict(keyboard.get("metadata", {})),
        }
        if sample.get("sequence") is not None:
            message_payload["sequence"] = sample.get("sequence")
        message = coerce_viewer_control_message(message_payload)
        return ViewerCanonicalInputSample(
            provider_id=provider_id,  # type: ignore[arg-type]
            provider_schema=provider_schema,  # type: ignore[arg-type]
            source_kind="keyboard",
            timestamp_s=float(sample["timestamp_s"]),
            sequence=sample.get("sequence"),
            keyboard=message.keyboard,
            source_active=bool(sample.get("source_active", False)),
            zero_state=bool(sample.get("zero_state", True)),
            stale_reason=sample.get("stale_reason"),
            diagnostics=sample.get("diagnostics", {}),  # type: ignore[arg-type]
        )

    if source_kind != "gamepad":
        raise ValueError("viewer mapping received an unknown sample source kind")
    gamepad = frame.metadata["viewer_control_message"]
    if not isinstance(gamepad, Mapping) or not isinstance(gamepad.get("gamepad"), Mapping):
        raise ValueError("viewer gamepad compatibility payload is invalid")
    from selfrionette.schemas import coerce_viewer_control_message

    message_payload = {
        "type": "viewer_control_message",
        "timestamp_s": sample.get("timestamp_s"),
        "source_kind": "gamepad",
        "gamepad": _as_json_wire_value(gamepad["gamepad"]),
        "metadata": dict(gamepad.get("metadata", {})),
    }
    if sample.get("sequence") is not None:
        message_payload["sequence"] = sample.get("sequence")
    message = coerce_viewer_control_message(message_payload)
    return ViewerCanonicalInputSample(
        provider_id=provider_id,  # type: ignore[arg-type]
        provider_schema=provider_schema,  # type: ignore[arg-type]
        source_kind="gamepad",
        timestamp_s=float(sample["timestamp_s"]),
        sequence=sample.get("sequence"),
        gamepad=message.gamepad,
        source_active=bool(sample.get("source_active", False)),
        zero_state=bool(sample.get("zero_state", True)),
        stale_reason=sample.get("stale_reason"),
        diagnostics=sample.get("diagnostics", {}),  # type: ignore[arg-type]
    )


def _normalize_control_frame(value: object) -> str:
    if not isinstance(value, str):
        return "world"
    value = value.strip().lower()
    return value if value in {"world", "tool"} else "world"


def _coerce_axis_vector3(axes: Sequence[float]) -> tuple[float, float, float]:
    values = tuple(float(axis) for axis in axes)
    if not all(isfinite(axis) for axis in values):
        raise ValueError("gamepad axes must be finite")
    return (
        values[0] if len(values) > 0 else 0.0,
        values[1] if len(values) > 1 else 0.0,
        values[2] if len(values) > 2 else 0.0,
    )


class ViewerKeyboardGamepadMappingStrategy:
    mapping_semantics_identity = VIEWER_MAPPING_SEMANTICS_IDENTITY

    def map_input(self, input_intent: object, parameters: Mapping[str, object]) -> InputIntent:
        if not isinstance(input_intent, RawInputFrame):
            raise TypeError("viewer mapping accepts a canonical RawInputFrame sample")
        if parameters:
            raise ValueError("viewer mapping does not accept unknown parameters")
        sample_payload = input_intent.metadata.get("viewer_input_sample")
        if not isinstance(sample_payload, Mapping):
            intent = build_continuous_endpoint_velocity_intent(
                (0.0, 0.0, 0.0),
                source_kind="viewer",
                source_timestamp_s=input_intent.timestamp_s,
                speed_m_s=0.1,
                deadzone=0.1,
                max_delta_m=0.03,
                control_frame="world",
                source_active=False,
                stale_reason=input_intent.metadata.get("stale_reason"),
            )
            metadata = dict(input_intent.metadata)
            metadata.update(intent.to_metadata())
            metadata.update(
                {
                    "endpoint_velocity_m_s": intent.local_endpoint_velocity_m_s,
                    "resolved_world_endpoint_velocity_m_s": intent.local_endpoint_velocity_m_s,
                    "endpoint_velocity_frame": "mujoco_world",
                }
            )
            return InputIntent(
                source="viewer",
                timestamp_s=input_intent.timestamp_s,
                values=intent.axis_values,
                buttons=(),
                metadata=metadata,
            )
        sample = _coerce_frame_sample(input_intent)
        raw_message = input_intent.metadata["viewer_control_message"]
        if not isinstance(raw_message, Mapping):
            raise ValueError("viewer control summary is required")
        control_frame = _normalize_control_frame(raw_message.get("metadata", {}).get("control_frame") if isinstance(raw_message.get("metadata"), Mapping) else None)

        if sample.source_kind == "keyboard":
            assert sample.keyboard is not None
            intent = build_keyboard_continuous_velocity_intent(
                sample.keyboard.active_key_codes,
                timestamp_s=sample.timestamp_s,
                config=build_default_keyboard_input_config(),
                control_frame=control_frame,
                source_active=sample.source_active,
                stale_reason=sample.stale_reason,
                source_kind="viewer_keyboard",
            )
            buttons = tuple(sample.keyboard.key_state.get(code, False) for code in sample.keyboard.active_key_codes)
        else:
            assert sample.gamepad is not None
            supplements = [0.0, 0.0, 0.0]
            for index, button in enumerate(sample.gamepad.buttons):
                if index == 0 and button.pressed:
                    supplements[2] += 1.0
                if index == 1 and button.pressed:
                    supplements[2] -= 1.0
            intent = build_continuous_endpoint_velocity_intent(
                _coerce_axis_vector3(sample.gamepad.axes),
                source_kind="viewer_gamepad",
                source_timestamp_s=sample.timestamp_s,
                speed_m_s=0.1,
                deadzone=0.1,
                max_delta_m=0.03,
                control_frame=control_frame,
                source_active=sample.source_active,
                stale_reason=sample.stale_reason,
                supplemental_axis_values=tuple(supplements),
                source_diagnostics={"raw_axes": tuple(sample.gamepad.axes)},
            )
            buttons = tuple(button.pressed for button in sample.gamepad.buttons)

        metadata = dict(input_intent.metadata)
        metadata.update(intent.to_metadata())
        metadata.update(
            {
                "endpoint_velocity_m_s": intent.local_endpoint_velocity_m_s,
                "resolved_world_endpoint_velocity_m_s": (
                    intent.local_endpoint_velocity_m_s
                    if control_frame == "world"
                    else None
                ),
                "endpoint_velocity_frame": "mujoco_world",
            }
        )
        metadata.update(
            {
                "viewer_source_kind": sample.source_kind,
                "sequence": sample.sequence,
                "control_frame": control_frame,
                "source_active": sample.source_active,
                "stale_reason": sample.stale_reason,
            }
        )
        return InputIntent(
            source="viewer",
            timestamp_s=sample.timestamp_s,
            values=intent.axis_values,
            buttons=buttons,
            metadata=metadata,
        )


VIEWER_CONTROL_MAPPING_PLUGIN = ControlMappingPlugin(
    identity=VIEWER_CONTROL_MAPPING_IDENTITY,
    strategy=ViewerKeyboardGamepadMappingStrategy(),
    accepted_input_sample_schemas=frozenset({VIEWER_CONTROL_SAMPLE_IDENTITY}),
    parameter_contract=ParameterContract(),
    control_frame=None,
    comparison_family_identity=VersionedIdentity("viewer_keyboard_gamepad_comparison", 1),
    mapping_semantics_identity=VIEWER_MAPPING_SEMANTICS_IDENTITY,
)


__all__ = [
    "VIEWER_CONTROL_MAPPING_IDENTITY",
    "VIEWER_CONTROL_MAPPING_PLUGIN",
    "VIEWER_CONTROL_SAMPLE_IDENTITY",
    "VIEWER_MAPPING_SEMANTICS_IDENTITY",
    "ViewerKeyboardGamepadMappingStrategy",
]
