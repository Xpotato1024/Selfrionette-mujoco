from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from tests.plugins.input_sources.contract.conformance import (
    InputSourceConformanceCase,
    assert_input_source_plugin_conforms,
)


_VALID_LINE = "vector,1,1,2,3,4,5,6,7"


def test_loadcell_serial_plugin_conforms_with_injected_lines() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("loadcell_serial").plugin
    assert_input_source_plugin_conforms(
        InputSourceConformanceCase(
            plugin=plugin,
            parameters={"lines": (_VALID_LINE,)},
            expected_frame_source="loadcell_serial",
            expected_started_status="active",
        )
    )
