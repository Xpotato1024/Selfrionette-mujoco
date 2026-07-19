from __future__ import annotations

import pytest

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.input_sources.registration import (
    InputSourcePluginRegistration,
)
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source
from selfrionette.runtime.experiment.contracts import VersionedIdentity
from selfrionette.runtime.experiment.input_source import InputSourceHealthStatus
from selfrionette.runtime.execution.input_source_adapters import (
    REPLAY_COMPATIBILITY_EXECUTION_ADAPTER,
)


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
