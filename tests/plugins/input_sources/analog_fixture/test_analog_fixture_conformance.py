from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from tests.plugins.input_sources.contract.conformance import (
    InputSourceConformanceCase,
    assert_input_source_plugin_conforms,
)


def test_analog_fixture_plugin_conforms_from_deterministic_sample() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("analog_fixture").plugin
    assert_input_source_plugin_conforms(
        InputSourceConformanceCase(
            plugin=plugin,
            parameters={
                "samples": (
                    {
                        "timestamp_s": 1.0,
                        "raw_values": (512, 612, 312, 512, 512, 512, 512),
                        "active": True,
                        "stale_reason": None,
                    },
                )
            },
            expected_frame_source="analog_fixture",
        )
    )
