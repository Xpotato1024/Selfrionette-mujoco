"""Fixed discovery entry point for viewer/v1."""

from __future__ import annotations

from collections.abc import Sequence

from selfrionette.plugins.input_sources import viewer
from selfrionette.plugins.input_source_registration import (
    InputSourcePluginRegistration,
    InputSourcePluginRequest,
)
from selfrionette.runtime.execution.input_source_adapters import (
    VIEWER_LOCAL_ENDPOINT_EXECUTION_ADAPTER,
)
from selfrionette.runtime.experiment.contracts import (
    ParameterContract,
    ParameterField,
    PluginSelection,
    VersionedIdentity,
)
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceMode,
    InputSourcePlugin,
)
from selfrionette.schemas import RawInputFrame


_SAFE_ENDPOINT = viewer.DEFAULT_VIEWER_SAFE_ENDPOINT_M


def _request(
    *,
    steps: int,
    frames: Sequence[RawInputFrame] | None,
    preset: str | None,
    **_: object,
) -> InputSourcePluginRequest:
    _ = steps
    if preset is not None:
        raise ValueError("preset is not supported for viewer input source")
    if frames is not None:
        raise ValueError("viewer input source does not accept custom frames")
    metadata = {
        "preset": "viewer",
        "source_kind": "viewer",
        "target_position_m": _SAFE_ENDPOINT,
        "desired_endpoint_m": _SAFE_ENDPOINT,
        "source_active": False,
        "command_age_ms": 0,
        "stale_reason": "no_control_message_received",
    }
    parameters = {
        "metadata": metadata,
        "initial_endpoint_m": _SAFE_ENDPOINT,
    }
    return InputSourcePluginRequest(
        parameters=parameters,
        frames=viewer.build_frames(parameters),
        loop=True,
        initial_metadata=metadata,
    )


_PLUGIN = InputSourcePlugin(
    identity=VersionedIdentity("viewer", 1),
    produced_sample_schema=VersionedIdentity("viewer_control_sample", 1),
    mode=InputSourceMode.VIEWER_BRIDGE,
    factory=viewer.build_reader,
    parameter_contract=ParameterContract(
        (
            ParameterField("metadata", dict),
            ParameterField("initial_endpoint_m", tuple),
        )
    ),
    initial_health=InputSourceHealth(
        InputSourceHealthStatus.STALE,
        reason="no_control_message_received",
        age_ms=0,
    ),
    initial_metadata={
        "preset": "viewer",
        "source_kind": "viewer",
        "source_active": False,
        "command_age_ms": 0,
        "stale_reason": "no_control_message_received",
    },
)
INPUT_SOURCE_PLUGIN = InputSourcePluginRegistration(
    plugin=_PLUGIN,
    cli_aliases=("viewer",),
    generic_cli_exposed=True,
    request_builder=_request,
    execution_adapter=VIEWER_LOCAL_ENDPOINT_EXECUTION_ADAPTER,
    default_control_mapping_selection=PluginSelection(
        "viewer_keyboard_gamepad_mapping", 1
    ),
    catalog_order=3,
    generic_cli_order=3,
)


__all__ = ["INPUT_SOURCE_PLUGIN"]
