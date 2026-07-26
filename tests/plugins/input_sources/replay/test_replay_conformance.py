from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from tests.plugins.input_sources.contract.conformance import (
    InputSourceConformanceCase,
    assert_input_source_plugin_conforms,
)


def test_replay_plugin_conforms() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("replay").plugin
    assert_input_source_plugin_conforms(
        InputSourceConformanceCase(
            plugin=plugin,
            parameters={"metadata": {"fixture": "replay"}, "loop": True},
            expected_frame_source="replay",
        )
    )
