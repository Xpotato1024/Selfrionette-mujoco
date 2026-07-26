from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from math import isfinite
from typing import cast

from selfrionette.input_sources.loadcell_serial import (
    LoadcellNormalizedInputIntentConverter,
    NormalizedLoadcellInputIntent,
)
from selfrionette.plugins.mappings.loadcell import LoadcellEndpointMotionCommandConverter
from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.runtime.experiment.input_source import InputSourceRuntimeDependencies
from selfrionette.runtime.runners.offline_input_smoke import run_offline_input_runtime_stepping_smoke

DEFAULT_LIVE_LOADCELL_BAUD_RATE = 115200
DEFAULT_LIVE_LOADCELL_MAX_FRAMES = 300
DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M = (0.1, 0.0, 0.3)
DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME = 1


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
        object.__setattr__(
            self,
            "current_tip_position_m",
            _coerce_vector3("current_tip_position_m", self.current_tip_position_m),
        )


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
            raise ValueError(
                f"{name} must contain only finite values at index {component_index}"
            )
        coerced_components.append(component)

    return cast(tuple[float, float, float], tuple(coerced_components))


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

    materialized_lines = tuple(line_source) if line_source is not None else None
    registration = INPUT_SOURCE_CATALOG.resolve(
        "loadcell_fixture" if materialized_lines is not None else "loadcell_serial"
    )
    source_parameters = (
        {"lines": materialized_lines}
        if materialized_lines is not None
        else {"port": config.port, "baud_rate": config.baud_rate}
    )
    source = registration.plugin.create_runtime_reader(
        source_parameters,
        runtime_dependencies=(
            InputSourceRuntimeDependencies(line_source=materialized_lines)
            if materialized_lines is not None
            else None
        ),
    )
    normalized_converter = LoadcellNormalizedInputIntentConverter(source="loadcell_serial")
    endpoint_converter = LoadcellEndpointMotionCommandConverter()

    payloads: list[Mapping[str, object]] = []
    start = getattr(source, "start", None)
    close = getattr(source, "close", None)
    start_attempted = False
    primary_failure: BaseException | None = None
    try:
        if callable(start):
            start_attempted = True
            start()
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
    except BaseException as failure:
        primary_failure = failure
        raise
    finally:
        if start_attempted and callable(close):
            try:
                close()
            except BaseException as cleanup_failure:
                if primary_failure is not None:
                    primary_failure.add_note(
                        f"input source cleanup failed: {cleanup_failure!r}"
                    )
                else:
                    raise

    return payloads


__all__ = [
    "DEFAULT_LIVE_LOADCELL_BAUD_RATE",
    "DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M",
    "DEFAULT_LIVE_LOADCELL_MAX_FRAMES",
    "DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME",
    "LiveLoadcellRuntimeRunnerConfig",
    "run_live_loadcell_runtime_runner",
]
