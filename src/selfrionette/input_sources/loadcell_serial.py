"""Public load-cell compatibility facade.

Source acquisition, parsing, diagnostics, and intrinsic normalization are
owned by ``plugins.input_sources._loadcell``. Mapping symbols remain owned by
``plugins.mappings.loadcell``. The recorded dry-run helper remains re-exported
here as a public compatibility surface until C4.
"""

from __future__ import annotations

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
from selfrionette.runtime.runners.loadcell_serial_dry_run import (
    LoadcellSerialDryRunSmokeResult,
    run_loadcell_serial_dry_run_smoke,
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
