from __future__ import annotations

from math import nan
from types import MappingProxyType

import pytest

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.catalog import CONTROL_MAPPING_REGISTRY
from selfrionette.plugins.input_sources.registration import (
    InputSourcePluginRegistration,
)
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.runtime.experiment.contracts import PluginSelection, VersionedIdentity
from selfrionette.runtime.experiment.input_source import InputSourcePlugin
from selfrionette.runtime.experiment.input_source import InputSourceHealthStatus
from selfrionette.runtime.execution.input_source_adapters import (
    REPLAY_COMPATIBILITY_EXECUTION_ADAPTER,
)
from selfrionette.plugins.input_sources._loadcell import NormalizedLoadcellInputIntent
from selfrionette.schemas import InputIntent


def test_production_input_source_catalog_is_versioned_and_deterministic() -> None:
    assert INPUT_SOURCE_CATALOG.ids == (
        "analog_fixture",
        "loadcell_fixture",
        "loadcell_serial",
        "noop",
        "programmed_target",
        "replay",
        "viewer",
    )
    assert INPUT_SOURCE_CATALOG.aliases == (
        "programmed_target",
        "replay",
        "noop",
        "viewer",
    )
    assert INPUT_SOURCE_CATALOG.resolve("loadcell_serial").plugin.produced_sample_schema_identity == VersionedIdentity(
        "loadcell_vector_sample", 1
    )
    assert INPUT_SOURCE_CATALOG.resolve("loadcell_fixture").plugin.produced_sample_schema_identity == VersionedIdentity(
        "loadcell_vector_sample", 1
    )


def test_generic_aliases_do_not_expose_live_or_fixture_sources() -> None:
    assert "loadcell_serial" not in INPUT_SOURCE_CATALOG.aliases
    assert "loadcell_fixture" not in INPUT_SOURCE_CATALOG.aliases
    assert "analog_fixture" not in INPUT_SOURCE_CATALOG.aliases


def test_selection_resolves_plugin_schema_reader_health_and_adapter() -> None:
    selection = select_runtime_input_source("viewer", steps=1)
    assert selection.plugin_selection is not None
    assert selection.resolved_plugin is not None
    assert selection.produced_sample_schema_identity == VersionedIdentity(
        "viewer_control_sample", 1
    )
    assert selection.runtime_reader is not None
    assert selection.initial_health is not None
    assert selection.initial_health.status is InputSourceHealthStatus.STALE
    assert selection.execution_adapter is not None
    assert selection.execution_adapter.identity == VersionedIdentity(
        "viewer_local_endpoint_input_execution", 1
    )
    assert selection.control_mapping_selection == PluginSelection(
        "viewer_keyboard_gamepad_mapping", 1
    )
    assert selection.control_mapping is CONTROL_MAPPING_REGISTRY.resolve(
        PluginSelection("viewer_keyboard_gamepad_mapping", 1)
    )
    registration = INPUT_SOURCE_CATALOG.resolve("viewer")
    assert not hasattr(registration, "control_mapping")


def test_explicit_mapping_selection_is_not_replaced_by_source_default() -> None:
    explicit = PluginSelection("viewer_keyboard_gamepad_mapping", 1)
    selection = select_runtime_input_source(
        "viewer",
        steps=1,
        control_mapping_selection=explicit,
    )
    assert selection.control_mapping_selection is explicit
    assert selection.control_mapping is CONTROL_MAPPING_REGISTRY.resolve(explicit)


@pytest.mark.parametrize(
    "mapping_selection",
    (None, PluginSelection("viewer_keyboard_gamepad_mapping", 1)),
)
@pytest.mark.parametrize(
    "parameters",
    (
        {"unknown_parameter": 1.0},
        {"gamepad_speed_m_s": -0.1},
        {"gamepad_deadzone": nan},
        {
            "keyboard_config": {
                "bindings": {"KeyQ": {"axis": "bad", "direction": 1}},
                "speed_m_s": 0.1,
                "deadzone": 0.0,
                "max_delta_m": 0.03,
            }
        },
        {
            "keyboard_config": {
                "bindings": {"KeyQ": {"axis": "x", "direction": 0}},
                "speed_m_s": 0.1,
                "deadzone": 0.0,
                "max_delta_m": 0.03,
            }
        },
    ),
)
def test_mapping_parameters_fail_during_selection_for_default_and_explicit_mapping(
    mapping_selection: PluginSelection | None,
    parameters: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        select_runtime_input_source(
            "viewer",
            steps=1,
            control_mapping_selection=mapping_selection,
            control_mapping_parameters=parameters,
        )


def test_invalid_mapping_parameters_do_not_create_a_managed_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_calls: list[str] = []
    original = InputSourcePlugin.create_runtime_reader

    def spy(self, *args, **kwargs):
        create_calls.append(self.identity.canonical_id)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(InputSourcePlugin, "create_runtime_reader", spy)
    with pytest.raises(ValueError, match="unknown"):
        select_runtime_input_source(
            "viewer",
            steps=1,
            control_mapping_parameters={"unknown_parameter": True},
        )

    assert create_calls == []


def test_valid_mapping_parameters_are_normalized_and_frozen_before_runtime() -> None:
    selection = select_runtime_input_source(
        "viewer",
        steps=1,
        control_mapping_parameters={
            "gamepad_speed_m_s": 0.2,
            "gamepad_deadzone": 0.0,
            "gamepad_max_delta_m": 0.05,
        },
    )

    assert isinstance(selection.control_mapping_parameters, MappingProxyType)
    assert selection.control_mapping_parameters["gamepad_speed_m_s"] == 0.2
    assert selection.control_mapping_parameters["gamepad_deadzone"] == 0.0
    assert selection.control_mapping_parameters["gamepad_max_delta_m"] == 0.05
    with pytest.raises(TypeError):
        selection.control_mapping_parameters["gamepad_deadzone"] = 0.1  # type: ignore[index]


def test_duplicate_alias_is_rejected_before_catalog_creation() -> None:
    registration = INPUT_SOURCE_CATALOG.resolve("replay")
    with pytest.raises(ValueError, match="duplicate input source CLI alias"):
        from selfrionette.plugins.input_sources.catalog import InputSourceCatalog

        InputSourceCatalog((registration, registration))


def test_replay_uses_typed_runtime_dependency_for_custom_frames() -> None:
    from selfrionette.schemas import RawInputFrame

    frame = RawInputFrame(source="replay", timestamp_s=3.0, values=(1.0,))
    selection = select_runtime_input_source("replay", steps=1, frames=(frame,))
    assert selection.runtime_reader is not None
    assert selection.runtime_reader.read_frame().timestamp_s == 3.0
    assert selection.execution_adapter is REPLAY_COMPATIBILITY_EXECUTION_ADAPTER


def _loadcell_mapping_parameters() -> dict[str, object]:
    return {
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
    }


def test_production_loadcell_selection_adapts_raw_frame_before_mapping_strategy() -> None:
    selection = select_runtime_input_source(
        "loadcell_fixture",
        steps=1,
        line_source=("vector,1000,1,0,0,0,0,0,0",),
        control_mapping_selection=PluginSelection("loadcell_endpoint_mapping", 1),
        control_mapping_parameters=_loadcell_mapping_parameters(),
    )

    assert selection.produced_sample_schema_identity == VersionedIdentity(
        "loadcell_vector_sample", 1
    )
    assert selection.control_mapping is CONTROL_MAPPING_REGISTRY.resolve(
        PluginSelection("loadcell_endpoint_mapping", 1)
    )
    assert selection.mapping_input_adapter is not None
    assert selection.mapping_input_adapter.input_schema == VersionedIdentity(
        "loadcell_vector_sample", 1
    )
    assert selection.mapping_input_adapter.output_schema == VersionedIdentity(
        "loadcell_normalized_input_intent", 1
    )
    assert selection.effective_mapping_input_sample_schema == VersionedIdentity(
        "loadcell_normalized_input_intent", 1
    )
    assert selection.effective_mapping_input_sample_schema in (
        selection.control_mapping.accepted_input_sample_schemas
        if selection.control_mapping is not None
        else ()
    )
    assert selection.runtime_reader is not None
    raw_frame = selection.runtime_reader.read_frame()
    normalized_intent = selection.mapping_input_adapter(raw_frame)
    assert isinstance(normalized_intent, NormalizedLoadcellInputIntent)
    mapped_intent = selection.control_mapping.strategy.map_input(
        normalized_intent,
        selection.control_mapping_parameters,
    )
    assert isinstance(mapped_intent, InputIntent)
    assert mapped_intent.metadata["desired_endpoint_m"] == pytest.approx(
        (0.11, 0.2, 0.3)
    )


def test_production_loadcell_selection_rejects_incompatible_mapping_before_reader_use() -> None:
    with pytest.raises(ValueError, match="schema compatibility mismatch"):
        select_runtime_input_source(
            "loadcell_fixture",
            steps=1,
            line_source=("vector,1000,1,0,0,0,0,0,0",),
            control_mapping_selection=PluginSelection(
                "viewer_keyboard_gamepad_mapping", 1
            ),
        )


@pytest.mark.parametrize(
    "parameters",
    (
        {
            "mapping_config": {"gain_m": -0.01},
            "current_tip_position_m": (0.1, 0.2, 0.3),
        },
        {
            "mapping_config": {"max_delta_m": 0.0},
            "current_tip_position_m": (0.1, 0.2, 0.3),
        },
        {
            "mapping_config": {
                "channel_axis_weights": (
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0),
                )
            },
            "current_tip_position_m": (0.1, 0.2, 0.3),
        },
        {
            "mapping_config": {},
            "current_tip_position_m": (0.1, 0.2),
        },
    ),
)
def test_invalid_loadcell_mapping_parameters_fail_before_source_reader_creation(
    monkeypatch: pytest.MonkeyPatch,
    parameters: dict[str, object],
) -> None:
    create_calls: list[str] = []
    original = InputSourcePlugin.create_runtime_reader

    def spy(self, *args, **kwargs):
        create_calls.append(self.identity.canonical_id)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(InputSourcePlugin, "create_runtime_reader", spy)
    with pytest.raises((TypeError, ValueError)):
        select_runtime_input_source(
            "loadcell_serial",
            steps=1,
            line_source=("vector,1000,1,0,0,0,0,0,0",),
            control_mapping_selection=PluginSelection("loadcell_endpoint_mapping", 1),
            control_mapping_parameters=parameters,
        )

    assert create_calls == []
