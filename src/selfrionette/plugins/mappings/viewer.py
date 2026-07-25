"""Behavior-preserving keyboard/gamepad Control Mapping Plugin."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

from selfrionette.plugins.mappings.continuous_endpoint_velocity import (
    build_continuous_endpoint_velocity_intent,
)
from selfrionette.plugins.mappings.keyboard import (
    KeyboardBinding,
    KeyboardInputConfig,
    build_default_keyboard_input_config,
    build_keyboard_continuous_velocity_intent,
)
from selfrionette.runtime.experiment.contracts import (
    ControlMappingPlugin,
    ControlMappingStrategy,
    ParameterContract,
    ParameterField,
    VersionedIdentity,
)
from selfrionette.schemas import InputIntent, RawInputFrame, coerce_viewer_control_message
from selfrionette.schemas.viewer_input import (
    VIEWER_CONTROL_SAMPLE_SCHEMA,
    ViewerCanonicalInputSample,
)

VIEWER_CONTROL_MAPPING_IDENTITY = VersionedIdentity("viewer_keyboard_gamepad_mapping", 1)
VIEWER_MAPPING_SEMANTICS_IDENTITY = VersionedIdentity("viewer_keyboard_gamepad_semantics", 1)
VIEWER_CONTROL_SAMPLE_IDENTITY = VersionedIdentity("viewer_control_sample", 1)
_DEFAULT_GAMEPAD_SPEED_M_S = 0.1
_DEFAULT_GAMEPAD_DEADZONE = 0.1
_DEFAULT_GAMEPAD_MAX_DELTA_M = 0.03


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
    if not isinstance(source_kind, str):
        raise ValueError("viewer mapping canonical sample source_kind is required")
    if not isinstance(provider_id, str) or not isinstance(provider_schema, str):
        raise ValueError("viewer mapping canonical sample provider identity is required")
    if source_kind == "keyboard":
        keyboard_payload = sample.get("keyboard")
        if not isinstance(keyboard_payload, Mapping):
            raise ValueError("viewer keyboard sample payload is required")
        message_payload = {
            "type": "viewer_control_message",
            "timestamp_s": sample.get("timestamp_s"),
            "source_kind": "keyboard",
            "provider_id": provider_id,
            "provider_schema": provider_schema,
            "keyboard": _as_json_wire_value(keyboard_payload),
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
            requested_control_frame=str(sample.get("requested_control_frame", "world")),
            keyboard=message.keyboard,
            source_active=bool(sample.get("source_active", False)),
            zero_state=bool(sample.get("zero_state", True)),
            stale_reason=sample.get("stale_reason"),
            diagnostics=sample.get("diagnostics", {}),  # type: ignore[arg-type]
        )

    if source_kind != "gamepad":
        raise ValueError("viewer mapping received an unknown sample source kind")
    gamepad_payload = sample.get("gamepad")
    if not isinstance(gamepad_payload, Mapping):
        raise ValueError("viewer gamepad sample payload is required")

    message_payload = {
        "type": "viewer_control_message",
        "timestamp_s": sample.get("timestamp_s"),
        "source_kind": "gamepad",
        "provider_id": provider_id,
        "provider_schema": provider_schema,
        "gamepad": _as_json_wire_value(gamepad_payload),
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
        requested_control_frame=str(sample.get("requested_control_frame", "world")),
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


def _normalize_gamepad_axis_for_mapping(value: float, deadzone: float) -> float:
    """Apply the selected mapping deadzone to one canonical raw axis."""

    clamped = max(-1.0, min(1.0, value))
    magnitude = abs(clamped)
    if magnitude <= deadzone:
        return 0.0
    scaled = (magnitude - deadzone) / max(1.0 - deadzone, 1e-12)
    return (1.0 if clamped > 0.0 else -1.0) * max(0.0, min(1.0, scaled))


@dataclass(frozen=True, slots=True)
class ViewerControlMappingParameters:
    keyboard_config: KeyboardInputConfig
    gamepad_speed_m_s: float = _DEFAULT_GAMEPAD_SPEED_M_S
    gamepad_deadzone: float = _DEFAULT_GAMEPAD_DEADZONE
    gamepad_max_delta_m: float = _DEFAULT_GAMEPAD_MAX_DELTA_M

    def __post_init__(self) -> None:
        if not isinstance(self.keyboard_config, KeyboardInputConfig):
            raise ValueError("keyboard_config must be a KeyboardInputConfig")
        for name, value in (
            ("gamepad_speed_m_s", self.gamepad_speed_m_s),
            ("gamepad_deadzone", self.gamepad_deadzone),
            ("gamepad_max_delta_m", self.gamepad_max_delta_m),
        ):
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")


def build_viewer_control_mapping_parameters(
    parameters: Mapping[str, object] | None = None,
) -> ViewerControlMappingParameters:
    values = {} if parameters is None else dict(parameters)
    allowed = {
        "keyboard_config",
        "gamepad_speed_m_s",
        "gamepad_deadzone",
        "gamepad_max_delta_m",
    }
    unknown = tuple(sorted(set(values) - allowed))
    if unknown:
        raise ValueError(f"unknown viewer mapping parameters: {unknown}")
    keyboard_config = values.get("keyboard_config")
    if keyboard_config is None:
        keyboard_config = build_default_keyboard_input_config()
    elif isinstance(keyboard_config, Mapping):
        bindings_payload = keyboard_config.get("bindings")
        if not isinstance(bindings_payload, Mapping):
            raise ValueError("keyboard_config.bindings must be a mapping")
        bindings: dict[str, KeyboardBinding] = {}
        for key, binding in bindings_payload.items():
            if not isinstance(binding, Mapping):
                raise ValueError("keyboard_config bindings must use mapping values")
            if "axis" not in binding or "direction" not in binding:
                raise ValueError(f"binding {key!r} must include axis and direction")
            if type(binding["direction"]) is not int or binding["direction"] not in {-1, 1}:
                raise ValueError(f"invalid direction for binding {key!r}")
            if not isinstance(binding["axis"], str):
                raise ValueError(f"invalid axis for binding {key!r}")
            direction = binding["direction"]
            bindings[str(key)] = KeyboardBinding(
                axis=binding["axis"],
                direction=direction,
            )
        speed_m_s = keyboard_config.get("speed_m_s")
        deadzone = keyboard_config.get("deadzone")
        max_delta_m = keyboard_config.get("max_delta_m")
        if speed_m_s is None or deadzone is None or max_delta_m is None:
            raise ValueError("keyboard_config requires speed_m_s, deadzone, and max_delta_m")
        keyboard_config = KeyboardInputConfig(
            bindings=bindings,
            speed_m_s=float(speed_m_s),
            deadzone=float(deadzone),
            max_delta_m=float(max_delta_m),
        )
    return ViewerControlMappingParameters(
        keyboard_config=keyboard_config,
        gamepad_speed_m_s=float(values.get("gamepad_speed_m_s", _DEFAULT_GAMEPAD_SPEED_M_S)),
        gamepad_deadzone=float(values.get("gamepad_deadzone", _DEFAULT_GAMEPAD_DEADZONE)),
        gamepad_max_delta_m=float(values.get("gamepad_max_delta_m", _DEFAULT_GAMEPAD_MAX_DELTA_M)),
    )


def normalize_viewer_control_mapping_parameters(
    parameters: Mapping[str, object],
) -> Mapping[str, object]:
    """Validate and freeze viewer mapping parameters before source execution."""

    normalized = build_viewer_control_mapping_parameters(parameters)
    keyboard_config = KeyboardInputConfig(
        bindings=MappingProxyType(
            dict(sorted(normalized.keyboard_config.bindings.items()))
        ),
        speed_m_s=normalized.keyboard_config.speed_m_s,
        deadzone=normalized.keyboard_config.deadzone,
        max_delta_m=normalized.keyboard_config.max_delta_m,
    )
    return MappingProxyType(
        {
            "keyboard_config": keyboard_config,
            "gamepad_speed_m_s": normalized.gamepad_speed_m_s,
            "gamepad_deadzone": normalized.gamepad_deadzone,
            "gamepad_max_delta_m": normalized.gamepad_max_delta_m,
        }
    )


class ViewerKeyboardGamepadMappingStrategy:
    mapping_semantics_identity = VIEWER_MAPPING_SEMANTICS_IDENTITY

    def map_input(self, input_intent: object, parameters: Mapping[str, object]) -> InputIntent:
        if not isinstance(input_intent, RawInputFrame):
            raise TypeError("viewer mapping accepts a canonical RawInputFrame sample")
        embedded_parameters = input_intent.metadata.get("viewer_mapping_parameters")
        effective_parameters = parameters or (
            embedded_parameters if isinstance(embedded_parameters, Mapping) else {}
        )
        mapping_parameters = build_viewer_control_mapping_parameters(effective_parameters)
        sample_payload = input_intent.metadata.get("viewer_input_sample")
        if not isinstance(sample_payload, Mapping):
            intent = build_continuous_endpoint_velocity_intent(
                (0.0, 0.0, 0.0),
                source_kind="viewer",
                source_timestamp_s=input_intent.timestamp_s,
                speed_m_s=mapping_parameters.gamepad_speed_m_s,
                deadzone=mapping_parameters.gamepad_deadzone,
                max_delta_m=mapping_parameters.gamepad_max_delta_m,
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
        control_frame = _normalize_control_frame(sample.requested_control_frame)

        if sample.source_kind == "keyboard":
            assert sample.keyboard is not None
            intent = build_keyboard_continuous_velocity_intent(
                sample.keyboard.active_key_codes if sample.source_active else (),
                timestamp_s=sample.timestamp_s,
                config=mapping_parameters.keyboard_config,  # type: ignore[arg-type]
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
            source_axes = (
                sample.gamepad.raw_axes
                if sample.gamepad.raw_axes is not None
                else sample.gamepad.axes
            )
            mapping_axes = (
                tuple(
                    _normalize_gamepad_axis_for_mapping(
                        value,
                        mapping_parameters.gamepad_deadzone,
                    )
                    for value in source_axes
                )
                if sample.gamepad.raw_axes is not None
                else tuple(source_axes)
            ) if sample.source_active else (0.0, 0.0, 0.0)
            if not sample.source_active:
                supplements = [0.0, 0.0, 0.0]
            intent = build_continuous_endpoint_velocity_intent(
                _coerce_axis_vector3(mapping_axes),
                source_kind="viewer_gamepad",
                source_timestamp_s=sample.timestamp_s,
                speed_m_s=mapping_parameters.gamepad_speed_m_s,
                # Raw gamepad axes have already received the selected mapping
                # deadzone above. Legacy axes are already normalized by the
                # old provider projection and retain the existing threshold
                # semantics through their compatibility path.
                deadzone=(
                    0.0
                    if sample.gamepad.raw_axes is not None
                    else mapping_parameters.gamepad_deadzone
                ),
                max_delta_m=mapping_parameters.gamepad_max_delta_m,
                control_frame=control_frame,
                source_active=sample.source_active,
                stale_reason=sample.stale_reason,
                supplemental_axis_values=tuple(supplements),
                source_diagnostics={"raw_axes": tuple(source_axes)},
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
    parameter_contract=ParameterContract(
        (
            ParameterField("keyboard_config", object, required=False),
            ParameterField("gamepad_speed_m_s", float, required=False),
            ParameterField("gamepad_deadzone", float, required=False),
            ParameterField("gamepad_max_delta_m", float, required=False),
        )
    ),
    control_frame=None,
    comparison_family_identity=VersionedIdentity("viewer_keyboard_gamepad_comparison", 1),
    mapping_semantics_identity=VIEWER_MAPPING_SEMANTICS_IDENTITY,
    parameter_normalizer=normalize_viewer_control_mapping_parameters,
)


__all__ = [
    "VIEWER_CONTROL_MAPPING_IDENTITY",
    "VIEWER_CONTROL_MAPPING_PLUGIN",
    "ViewerControlMappingParameters",
    "build_viewer_control_mapping_parameters",
    "normalize_viewer_control_mapping_parameters",
    "VIEWER_CONTROL_SAMPLE_IDENTITY",
    "VIEWER_MAPPING_SEMANTICS_IDENTITY",
    "ViewerKeyboardGamepadMappingStrategy",
]
