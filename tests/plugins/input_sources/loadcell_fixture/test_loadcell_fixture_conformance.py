from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.loadcell import LOADCELL_ENDPOINT_MAPPING_PLUGIN
from tests.plugins.input_sources.contract.conformance import (
    InputSourceConformanceCase,
    TimestampSequencePolicy,
    assert_sample_schema_compatible,
    assert_input_source_plugin_conforms,
)


def test_loadcell_fixture_plugin_conforms_without_serial_io() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("loadcell_fixture").plugin
    assert_sample_schema_compatible(plugin, LOADCELL_ENDPOINT_MAPPING_PLUGIN)
    assert_input_source_plugin_conforms(
        InputSourceConformanceCase(
            plugin=plugin,
            parameters={"lines": ("vector,1,1,2,3,4,5,6,7", "vector,2,2,3,4,5,6,7,8")},
            expected_frame_source="loadcell_serial",
            reads_per_instance=2,
            timestamp_sequence_policy=TimestampSequencePolicy.PRESERVED_REPLAY_ORDER,
            timestamp_sequence_validator=lambda frames: (
                None
                if tuple(frame.timestamp_s for frame in frames) == (0.001, 0.002)
                else (_ for _ in ()).throw(AssertionError("fixture order changed"))
            ),
        )
    )
