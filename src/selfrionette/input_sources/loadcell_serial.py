"""Public load-cell compatibility facade.

Source acquisition, parsing, diagnostics, and intrinsic normalization are
owned by ``plugins.input_sources._loadcell``. Mapping symbols remain owned by
``plugins.mappings.loadcell``. The recorded dry-run helper stays here until
its separately classified C3/C4 retirement.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from selfrionette.plugins.input_sources._loadcell import (
    LoadcellNormalizationConfig,
    LoadcellNormalizedInputIntentConverter,
    NormalizedLoadcellInputIntent,
    RawLoadcellVectorRecord,
    SerialDiagnosticEvent,
    SerialFrameParseError,
    SerialInputSource,
    normalize_loadcell_frame_for_mapping,
    parse_serial_frame_line,
)
from selfrionette.plugins.mappings.loadcell import (
    LoadcellEndpointMappingConfig,
    LoadcellEndpointMotionCommandConverter,
    build_motion_command_from_normalized_loadcell_intent,
    build_r7_a_lite_smoke_endpoint_mapping_config,
)
from selfrionette.schemas import InputIntent, MotionCommand, RawInputFrame


@dataclass(frozen=True, slots=True)
class LoadcellSerialDryRunSmokeResult:
    frames_read: int
    vectors_read: int
    diagnostics: tuple[SerialDiagnosticEvent, ...]
    raw_frame: RawInputFrame | None
    normalized_intent: NormalizedLoadcellInputIntent | None
    motion_command: MotionCommand | None


def run_loadcell_serial_dry_run_smoke(
    lines: Iterable[str],
    *,
    max_vectors: int = 1,
    normalization_config: LoadcellNormalizationConfig | None = None,
    endpoint_config: LoadcellEndpointMappingConfig | None = None,
    current_tip_position_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
    mapping_plugin: object | None = None,
    mapping_parameters: Mapping[str, object] | None = None,
) -> LoadcellSerialDryRunSmokeResult:
    """Run the recorded-frame smoke through the canonical mapping when supplied.

    ``mapping_plugin=None`` preserves the public recorded-fixture compatibility
    helper and delegates to the canonical mapping converter. Production runner
    entry points resolve and pass the versioned Control Mapping Plugin.
    """

    if max_vectors < 1:
        raise ValueError("max_vectors must be a positive integer")

    normalized_converter = LoadcellNormalizedInputIntentConverter(normalization_config)
    endpoint_converter = LoadcellEndpointMotionCommandConverter(endpoint_config)
    selected_mapping_parameters = (
        {
            "mapping_config": endpoint_config or {},
            "current_tip_position_m": current_tip_position_m,
        }
        if mapping_parameters is None
        else mapping_parameters
    )
    if mapping_plugin is not None:
        normalize_parameters = getattr(mapping_plugin, "normalize_parameters", None)
        if not callable(normalize_parameters):
            raise TypeError("loadcell mapping plugin must expose normalize_parameters")
        selected_mapping_parameters = normalize_parameters(selected_mapping_parameters)
    source = SerialInputSource.from_lines(lines)

    frames_read = 0
    vectors_read = 0
    last_raw_frame: RawInputFrame | None = None
    last_normalized_intent: NormalizedLoadcellInputIntent | None = None
    last_motion_command: MotionCommand | None = None

    while vectors_read < max_vectors:
        try:
            raw_frame = source.read_frame()
        except StopIteration:
            break

        frames_read += 1
        vectors_read += 1
        last_raw_frame = raw_frame
        last_normalized_intent = normalized_converter.convert(raw_frame)
        if mapping_plugin is None:
            last_motion_command = endpoint_converter.convert(
                last_normalized_intent,
                current_tip_position_m=current_tip_position_m,
            )
        else:
            strategy = getattr(mapping_plugin, "strategy", None)
            map_input = getattr(strategy, "map_input", None)
            if not callable(map_input):
                raise TypeError("loadcell mapping plugin must expose strategy.map_input")
            mapped_intent = map_input(
                last_normalized_intent,
                selected_mapping_parameters,
            )
            if not isinstance(mapped_intent, InputIntent):
                raise TypeError("loadcell mapping strategy returned an invalid input intent")
            last_motion_command = MotionCommand(
                timestamp_s=mapped_intent.timestamp_s,
                metadata=mapped_intent.metadata,
            )

    return LoadcellSerialDryRunSmokeResult(
        frames_read=frames_read,
        vectors_read=vectors_read,
        diagnostics=source.diagnostics,
        raw_frame=last_raw_frame,
        normalized_intent=last_normalized_intent,
        motion_command=last_motion_command,
    )


__all__ = [
    "LoadcellNormalizationConfig",
    "LoadcellEndpointMappingConfig",
    "LoadcellEndpointMotionCommandConverter",
    "build_motion_command_from_normalized_loadcell_intent",
    "build_r7_a_lite_smoke_endpoint_mapping_config",
    "LoadcellNormalizedInputIntentConverter",
    "normalize_loadcell_frame_for_mapping",
    "LoadcellSerialDryRunSmokeResult",
    "NormalizedLoadcellInputIntent",
    "RawLoadcellVectorRecord",
    "SerialDiagnosticEvent",
    "SerialFrameParseError",
    "SerialInputSource",
    "parse_serial_frame_line",
    "run_loadcell_serial_dry_run_smoke",
]
