"""Reusable, source-agnostic Input Source Plugin conformance assertions."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping

from selfrionette.runtime.experiment.contracts import ControlMappingPlugin
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceMode,
    InputSourcePlugin,
    InputSourceRuntimeDependencies,
    ManagedInputSource,
)
from selfrionette.schemas import RawInputFrame


@dataclass(frozen=True, slots=True)
class InputSourceConformanceCase:
    """Source-local valid parameters around the generic contract assertions."""

    plugin: InputSourcePlugin
    parameters: Mapping[str, object]
    expected_frame_source: str
    runtime_dependencies: InputSourceRuntimeDependencies | None = None
    expected_started_status: str | None = None


def assert_input_source_plugin_conforms(case: InputSourceConformanceCase) -> None:
    """Exercise the reusable contract against one production or test plugin.

    The case owns only source-specific valid parameters and injected dependencies;
    all identity, sample, health, lifecycle, and deterministic-reader assertions
    remain generic.
    """

    plugin = case.plugin
    assert plugin.identity.name
    assert plugin.identity.version >= 1
    assert plugin.produced_sample_schema.canonical_id
    assert isinstance(plugin.initial_health, InputSourceHealth)
    assert isinstance(plugin.initial_metadata, MappingProxyType)
    plugin.parameter_contract.validate(case.parameters)

    def read_once() -> RawInputFrame:
        reader = plugin.create_runtime_reader(
            case.parameters,
            runtime_dependencies=case.runtime_dependencies,
        )
        assert reader.current_health() == plugin.initial_health
        managed = plugin.mode in (InputSourceMode.LIVE, InputSourceMode.VIEWER_BRIDGE)
        if managed:
            assert isinstance(reader, ManagedInputSource)
            reader.start()
        else:
            assert not isinstance(reader, ManagedInputSource)

        frame = reader.read_frame()
        assert isinstance(frame, RawInputFrame)
        assert frame.source == case.expected_frame_source
        assert reader.current_health().status.value in {
            "active",
            "inactive",
            "stale",
            "invalid",
            "disconnected",
        }
        if case.expected_started_status is not None:
            assert reader.current_health().status.value == case.expected_started_status
        if managed:
            reader.close()
        return frame

    first = read_once()
    second = read_once()
    assert second == first


def assert_sample_schema_compatible(
    plugin: InputSourcePlugin,
    mapping: ControlMappingPlugin,
) -> None:
    """Keep the source-produced / mapping-accepted schema gate explicit."""

    assert mapping.accepted_input_sample_schemas
    assert plugin.produced_sample_schema in mapping.accepted_input_sample_schemas


__all__ = [
    "InputSourceConformanceCase",
    "assert_input_source_plugin_conforms",
    "assert_sample_schema_compatible",
]
