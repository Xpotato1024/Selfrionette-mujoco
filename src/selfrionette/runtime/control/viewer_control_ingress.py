"""Viewer control ingress boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from time import monotonic

from selfrionette.plugins.mappings.keyboard import KeyboardInputConfig
from selfrionette.plugins.input_sources.viewer import (
    DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS,
    DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    ViewerInputSource,
)
from selfrionette.runtime.experiment.input_source import ViewerBridgeRuntimeCapability
from selfrionette.schemas import RawInputFrame, ViewerControlMessage, coerce_viewer_control_message, parse_viewer_control_message_json


def build_viewer_input_source(
    *,
    clock: Callable[[], float] | None = None,
    timeout_ms: int = DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS,
    keyboard_config: KeyboardInputConfig | None = None,
    initial_endpoint_m: tuple[float, float, float] = DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    gamepad_speed_m_s: float = 0.1,
    gamepad_deadzone: float = 0.1,
    gamepad_max_delta_m: float = 0.03,
) -> ViewerInputSource:
    return ViewerInputSource(
        clock=(clock if clock is not None else monotonic),
        timeout_ms=timeout_ms,
        keyboard_config=keyboard_config,
        initial_endpoint_m=initial_endpoint_m,
        gamepad_speed_m_s=gamepad_speed_m_s,
        gamepad_deadzone=gamepad_deadzone,
        gamepad_max_delta_m=gamepad_max_delta_m,
    )


def ingest_viewer_control_message(
    source: ViewerBridgeRuntimeCapability,
    message: ViewerControlMessage | str | Mapping[str, object],
) -> RawInputFrame:
    try:
        if isinstance(message, str):
            validated_message = parse_viewer_control_message_json(message)
        elif isinstance(message, ViewerControlMessage):
            validated_message = message
        else:
            validated_message = coerce_viewer_control_message(message)
    except Exception as exc:
        source.record_ingress_failure(str(exc))
        raise

    return source.ingest_control_message(validated_message)


def ingest_viewer_control_message_json(source: ViewerBridgeRuntimeCapability, message: str) -> RawInputFrame:
    return ingest_viewer_control_message(source, message)


__all__ = [
    "build_viewer_input_source",
    "ingest_viewer_control_message",
    "ingest_viewer_control_message_json",
]
