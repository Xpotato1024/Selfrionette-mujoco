from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, replace
from math import isfinite
from typing import cast

from selfrionette.input_sources.loadcell_serial import (
    LoadcellEndpointMotionCommandConverter,
    LoadcellNormalizedInputIntentConverter,
    NormalizedLoadcellInputIntent,
    SerialInputSource,
)
from selfrionette.runtime.runners.offline_input_smoke import run_offline_input_runtime_stepping_smoke

DEFAULT_LIVE_LOADCELL_BAUD_RATE = 115200
DEFAULT_LIVE_LOADCELL_MAX_FRAMES = 300
DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M = (0.1, 0.0, 0.3)
DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME = 1
_SERIAL_IMPORT_ERROR = "serial module is required for live serial mode. Install pyserial or run fixture mode."


@dataclass(frozen=True, slots=True)
class LiveLoadcellRuntimeRunnerConfig:
    port: str | None
    baud_rate: int = DEFAULT_LIVE_LOADCELL_BAUD_RATE
    max_frames: int = DEFAULT_LIVE_LOADCELL_MAX_FRAMES
    current_tip_position_m: tuple[float, float, float] = DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M
    steps_per_frame: int = DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME

    def __post_init__(self) -> None:
        if self.port is not None and not self.port.strip():
            raise ValueError("port must not be empty")
        if self.baud_rate <= 0:
            raise ValueError("baud_rate must be positive")
        if self.max_frames < 1:
            raise ValueError("max_frames must be a positive integer")
        if self.steps_per_frame < 1:
            raise ValueError("steps_per_frame must be a positive integer")
        object.__setattr__(self, "current_tip_position_m", _coerce_vector3("current_tip_position_m", self.current_tip_position_m))


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    if not isinstance(value, tuple):
        try:
            value = tuple(value)  # type: ignore[arg-type]
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValueError(f"{name} must contain exactly three values") from exc

    components = cast(tuple[float, float, float], value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    coerced_components = []
    for component_index, component in enumerate(components):
        component = float(component)
        if not isfinite(component):
            raise ValueError(f"{name} must contain only finite values at index {component_index}")
        coerced_components.append(component)

    return cast(tuple[float, float, float], tuple(coerced_components))


def _iter_live_serial_lines(port: str, baud_rate: int) -> Iterator[str]:
    try:
        import serial  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(_SERIAL_IMPORT_ERROR) from exc

    serial_port = serial.Serial(port=port, baudrate=baud_rate)
    try:
        while True:
            raw_line = serial_port.readline()
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            yield line
    finally:
        serial_port.close()


def _build_runtime_intent(
    intent: NormalizedLoadcellInputIntent,
    *,
    frame_index: int,
    serial_timestamp_s: float,
    config: LiveLoadcellRuntimeRunnerConfig,
) -> NormalizedLoadcellInputIntent:
    metadata = dict(intent.metadata)
    metadata.setdefault("source_kind", "loadcell_serial")
    metadata["frame_index"] = frame_index
    metadata["serial_timestamp_s"] = serial_timestamp_s
    if config.port is not None:
        metadata["serial_port"] = config.port
        metadata["baud_rate"] = config.baud_rate

    return replace(intent, metadata=metadata)


def run_live_loadcell_runtime_runner(
    config: LiveLoadcellRuntimeRunnerConfig,
    *,
    line_source: Iterable[str] | None = None,
) -> list[Mapping[str, object]]:
    if config.port is None and line_source is None:
        raise ValueError("port is required for live serial mode")

    source = (
        SerialInputSource.from_lines(line_source)
        if line_source is not None
        else SerialInputSource(_iter_live_serial_lines(config.port, config.baud_rate))
    )
    normalized_converter = LoadcellNormalizedInputIntentConverter(source="loadcell_serial")
    endpoint_converter = LoadcellEndpointMotionCommandConverter()

    payloads: list[Mapping[str, object]] = []
    for frame_index in range(1, config.max_frames + 1):
        try:
            raw_frame = source.read_frame()
        except StopIteration:
            break

        normalized_intent = normalized_converter.convert(raw_frame)
        runtime_intent = _build_runtime_intent(
            normalized_intent,
            frame_index=frame_index,
            serial_timestamp_s=raw_frame.timestamp_s,
            config=config,
        )
        motion_command = endpoint_converter.convert(
            runtime_intent,
            current_tip_position_m=config.current_tip_position_m,
        )
        runtime_result = run_offline_input_runtime_stepping_smoke(
            motion_command,
            steps=config.steps_per_frame,
        )
        if runtime_result.payload is None:  # pragma: no cover - defensive
            raise RuntimeError("offline runtime smoke did not produce a payload")
        payloads.append(runtime_result.payload)

    return payloads


__all__ = [
    "DEFAULT_LIVE_LOADCELL_BAUD_RATE",
    "DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M",
    "DEFAULT_LIVE_LOADCELL_MAX_FRAMES",
    "DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME",
    "LiveLoadcellRuntimeRunnerConfig",
    "run_live_loadcell_runtime_runner",
]
