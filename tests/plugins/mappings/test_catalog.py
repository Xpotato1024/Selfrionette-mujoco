from __future__ import annotations

import pytest

from selfrionette.input_sources.loadcell_serial import NormalizedLoadcellInputIntent
from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.catalog import CONTROL_MAPPING_REGISTRY
from selfrionette.plugins.mappings.loadcell import (
    LoadcellEndpointMappingConfig,
    LOADCELL_ENDPOINT_MAPPING_PLUGIN,
    LOADCELL_NORMALIZED_SAMPLE_SCHEMA,
    LOADCELL_VECTOR_SAMPLE_SCHEMA,
)
from selfrionette.plugins.mappings.replay import REPLAY_CONTROL_MAPPING_PLUGIN
from selfrionette.runtime.experiment.contracts import PluginSelection
from selfrionette.schemas import RawInputFrame


def test_production_mapping_catalog_is_deterministic_and_source_compatible_where_applicable() -> None:
    assert CONTROL_MAPPING_REGISTRY.ids == (
        "analog_fixture_mapping",
        "loadcell_endpoint_mapping",
        "replay_mapping",
        "viewer_keyboard_gamepad_mapping",
    )
    analog = CONTROL_MAPPING_REGISTRY.resolve(PluginSelection("analog_fixture_mapping", 1))
    replay = CONTROL_MAPPING_REGISTRY.resolve(PluginSelection("replay_mapping", 1))
    assert INPUT_SOURCE_CATALOG.resolve("analog_fixture").plugin.produced_sample_schema in analog.accepted_input_sample_schemas
    assert INPUT_SOURCE_CATALOG.resolve("replay").plugin.produced_sample_schema in replay.accepted_input_sample_schemas
    assert LOADCELL_NORMALIZED_SAMPLE_SCHEMA in LOADCELL_ENDPOINT_MAPPING_PLUGIN.accepted_input_sample_schemas
    assert LOADCELL_VECTOR_SAMPLE_SCHEMA not in LOADCELL_ENDPOINT_MAPPING_PLUGIN.accepted_input_sample_schemas


def test_loadcell_mapping_consumes_source_normalized_intent_without_reimplementing_normalization() -> None:
    intent = NormalizedLoadcellInputIntent(
        source="loadcell_serial",
        timestamp_s=1.0,
        values=(0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        active_channels=(0,),
        metadata={"source_kind": "loadcell_serial"},
    )
    mapped = LOADCELL_ENDPOINT_MAPPING_PLUGIN.strategy.map_input(
        intent,
        {
            "mapping_config": {
                "channel_axis_weights": (
                    (1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                ),
                "gain_m": 0.01,
                "max_delta_m": 0.03,
            },
            "current_tip_position_m": (0.1, 0.2, 0.3),
        },
    )
    assert mapped.metadata["desired_endpoint_m"] == pytest.approx((0.102, 0.2, 0.3))


def test_replay_mapping_is_a_typed_raw_frame_boundary() -> None:
    mapped = REPLAY_CONTROL_MAPPING_PLUGIN.strategy.map_input(
        RawInputFrame(source="replay", timestamp_s=2.0, values=(1.0,), metadata={"x": 1}),
        {},
    )
    assert mapped.source == "replay"
    assert mapped.timestamp_s == 2.0
    assert mapped.values == (1.0,)
