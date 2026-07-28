"""Fixed discovery entry point for loadcell_serial/v1."""

from selfrionette.plugins.input_sources import loadcell_serial
from selfrionette.plugins.input_sources._loadcell.plugin_support import (
    LOADCELL_MAPPING_INPUT_ADAPTER,
    build_loadcell_request,
)
from selfrionette.plugins.input_source_registration import (
    InputSourcePluginRegistration,
)
from selfrionette.runtime.execution.input_source_adapters import (
    LOADCELL_EXECUTION_ADAPTER,
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


_PLUGIN = InputSourcePlugin(
    identity=VersionedIdentity("loadcell_serial", 1),
    produced_sample_schema=VersionedIdentity("loadcell_vector_sample", 1),
    mode=InputSourceMode.LIVE,
    factory=loadcell_serial.build_reader,
    parameter_contract=ParameterContract(
        (
            ParameterField("port", str, required=False),
            ParameterField("baud_rate", int, required=False),
            ParameterField("lines", tuple, required=False),
        )
    ),
    initial_health=InputSourceHealth(
        InputSourceHealthStatus.DISCONNECTED,
        reason="not_started",
        age_ms=0,
    ),
    initial_metadata={"source_kind": "loadcell_serial", "baud_rate": 115200},
    mapping_input_adapter=LOADCELL_MAPPING_INPUT_ADAPTER,
)
INPUT_SOURCE_PLUGIN = InputSourcePluginRegistration(
    plugin=_PLUGIN,
    cli_aliases=("loadcell_serial",),
    generic_cli_exposed=False,
    request_builder=build_loadcell_request,
    execution_adapter=LOADCELL_EXECUTION_ADAPTER,
    default_control_mapping_selection=PluginSelection(
        "loadcell_endpoint_mapping", 1
    ),
    catalog_order=4,
)


__all__ = ["INPUT_SOURCE_PLUGIN"]
