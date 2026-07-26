from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from tests.plugins.input_sources.contract.conformance import (
    InputSourceConformanceCase,
    assert_input_source_plugin_conforms,
)


def test_loadcell_fixture_plugin_conforms_without_serial_io() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("loadcell_fixture").plugin
    assert_input_source_plugin_conforms(
        InputSourceConformanceCase(
            plugin=plugin,
            parameters={"lines": ("vector,1,1,2,3,4,5,6,7",)},
            expected_frame_source="loadcell_serial",
        )
    )
