from __future__ import annotations

from collections.abc import Callable, Mapping
from time import monotonic

from selfrionette.input_sources import ViewerInputSource
from selfrionette.input_sources.viewer import DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS, DEFAULT_VIEWER_SAFE_ENDPOINT_M
from selfrionette.input_sources.keyboard import KeyboardInputConfig
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
    source: ViewerInputSource,
    message: ViewerControlMessage | str | Mapping[str, object],
) -> RawInputFrame:
    if isinstance(message, str):
        validated_message = parse_viewer_control_message_json(message)
    elif isinstance(message, ViewerControlMessage):
        validated_message = message
    else:
        validated_message = coerce_viewer_control_message(message)

    return source.ingest_control_message(validated_message)


def ingest_viewer_control_message_json(source: ViewerInputSource, message: str) -> RawInputFrame:
    return source.ingest_control_message(parse_viewer_control_message_json(message))


__all__ = [
    "build_viewer_input_source",
    "ingest_viewer_control_message",
    "ingest_viewer_control_message_json",
]
