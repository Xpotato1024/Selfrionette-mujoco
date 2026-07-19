from __future__ import annotations

from dataclasses import replace

import pytest

from selfrionette.runtime.experiment.composition import (
    PluginParameters,
    compose_experiment,
)
from selfrionette.runtime.experiment.contracts import (
    ParameterContract,
    ParameterField,
    PluginAxis,
    PluginParameterOwner,
    PluginSelection,
    VersionedIdentity,
)
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceMode,
    InputSourcePlugin,
    ManagedInputSource,
)
from selfrionette.runtime.experiment.registry import VersionedPluginRegistry
from tests.runtime.test_experiment_plugin_composition import (
    _manifest,
    _mapping,
    _registries,
    _task,
)
from tests.support.input_source_plugin_doubles import (
    CONFORMANCE_INPUT_SOURCE,
    CONFORMANCE_SAMPLE_SCHEMA,
    ConformanceInputSourceReader,
    ManagedConformanceInputSourceReader,
    build_conformance_input_source,
)


def test_valid_plugin_reader_and_metadata_are_detached() -> None:
    metadata = {"nested": ["stable"]}
    plugin = replace(build_conformance_input_source(), initial_metadata=metadata)
    metadata["nested"].append("mutated")

    reader = plugin.create_runtime_reader({})

    assert reader.read_frame().values == (0.25, -0.5)
    assert plugin.initial_metadata["nested"] == ("stable",)


@pytest.mark.parametrize(
    "change, message",
    (
        ({"mode": "offline"}, "mode"),
        ({"produced_sample_schema": "sample/v1"}, "schema"),
        ({"factory": object()}, "factory"),
        ({"initial_health": object()}, "health"),
        ({"initial_metadata": {1: "bad"}}, "keys"),
        ({"produced_evidence": frozenset({"evidence/v1"})}, "evidence"),
    ),
)
def test_invalid_plugin_declarations_fail_closed(change: dict[str, object], message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        replace(build_conformance_input_source(), **change)


def test_health_contract_rejects_contradictory_or_invalid_values() -> None:
    with pytest.raises(ValueError, match="failure reason"):
        InputSourceHealth(InputSourceHealthStatus.ACTIVE, reason="failed")
    with pytest.raises(ValueError, match="requires a reason"):
        InputSourceHealth(InputSourceHealthStatus.STALE)
    with pytest.raises(ValueError, match="non-negative"):
        InputSourceHealth(InputSourceHealthStatus.STALE, reason="old", age_ms=-1)
    with pytest.raises(ValueError, match="non-negative"):
        InputSourceHealth(InputSourceHealthStatus.STALE, reason="old", age_ms=True)


def test_factory_output_and_parameters_are_validated_without_fallback() -> None:
    def bad_factory(parameters):
        return object()

    plugin = replace(build_conformance_input_source(), factory=bad_factory)
    with pytest.raises(TypeError, match="does not satisfy"):
        plugin.create_runtime_reader({})

    parameter_plugin = replace(
        build_conformance_input_source(),
        parameter_contract=ParameterContract((ParameterField("gain", float),)),
    )
    with pytest.raises(ValueError, match="missing required"):
        parameter_plugin.create_runtime_reader({})
    with pytest.raises(ValueError, match="not bool"):
        parameter_plugin.create_runtime_reader({"gain": True})


def test_offline_does_not_require_lifecycle_and_live_does() -> None:
    offline = build_conformance_input_source(mode=InputSourceMode.OFFLINE)
    assert isinstance(offline.create_runtime_reader({}), ConformanceInputSourceReader)

    def plain_factory(parameters):
        return ConformanceInputSourceReader(parameters)

    live = replace(
        build_conformance_input_source(mode=InputSourceMode.LIVE), factory=plain_factory
    )
    with pytest.raises(TypeError, match="ManagedInputSource"):
        live.create_runtime_reader({})


def test_live_factory_creation_is_side_effect_free_until_explicit_start() -> None:
    plugin = build_conformance_input_source(mode=InputSourceMode.VIEWER_BRIDGE)
    reader = plugin.create_runtime_reader({})

    assert isinstance(reader, ManagedInputSource)
    assert isinstance(reader, ManagedConformanceInputSourceReader)
    assert reader.started is False
    reader.start()
    assert reader.started is True
    reader.close()
    assert reader.closed is True


def test_registry_resolve_and_ids_are_deterministic() -> None:
    alpha = replace(
        build_conformance_input_source(), identity=VersionedIdentity("alpha", 1)
    )
    beta = replace(
        build_conformance_input_source(), identity=VersionedIdentity("beta", 1)
    )
    registry = VersionedPluginRegistry((beta, alpha), kind="input source plugin")
    assert registry.ids == ("alpha", "beta")
    assert registry.resolve(PluginSelection("alpha", 1)) is alpha
    with pytest.raises(ValueError, match="unknown input source plugin ID"):
        registry.resolve(PluginSelection("unknown", 1))
    with pytest.raises(ValueError, match="contract version mismatch"):
        registry.resolve(PluginSelection("alpha", 2))
    with pytest.raises(ValueError, match="duplicate input source plugin registration"):
        VersionedPluginRegistry((alpha, alpha), kind="input source plugin")


def test_composition_resolves_source_schema_and_evidence_without_factory_call() -> None:
    evidence = VersionedIdentity("source.diagnostic", 1)
    source = build_conformance_input_source(produced_evidence=frozenset({evidence}))
    resolved = compose_experiment(
        _manifest(
            parameters=(
                *_manifest().parameters,
                PluginParameters(
                    PluginParameterOwner(
                        PluginAxis.INPUT_SOURCE,
                        PluginSelection(CONFORMANCE_INPUT_SOURCE.name, 1),
                    ),
                    {},
                ),
            )
        ),
        _registries(input_source=source),
    )
    assert resolved.input_source is source
    assert resolved.resolved_input_sample_schema == CONFORMANCE_SAMPLE_SCHEMA
    assert resolved.evidence_producer(evidence).producer_axis is PluginAxis.INPUT_SOURCE


def test_composition_rejects_schema_mismatch_and_empty_mapping_acceptance() -> None:
    source = build_conformance_input_source()
    incompatible = replace(
        _mapping(),
        accepted_input_sample_schemas=frozenset(
            {VersionedIdentity("other_sample", 1)}
        ),
    )
    with pytest.raises(ValueError, match="input sample schema compatibility mismatch"):
        compose_experiment(_manifest(), _registries(input_source=source, mapping=incompatible))

    empty = replace(_mapping(), accepted_input_sample_schemas=frozenset())
    with pytest.raises(ValueError, match="at least one accepted"):
        compose_experiment(_manifest(), _registries(input_source=source, mapping=empty))


def test_composition_rejects_unselected_source_parameters_and_wrong_registry_type() -> None:
    source_owner = PluginParameterOwner(
        PluginAxis.INPUT_SOURCE, PluginSelection(CONFORMANCE_INPUT_SOURCE.name, 1)
    )
    unselected_owner = PluginParameterOwner(
        PluginAxis.INPUT_SOURCE, PluginSelection("other_source", 1)
    )
    with pytest.raises(ValueError, match="unselected plugins"):
        compose_experiment(
            _manifest(parameters=(PluginParameters(unselected_owner, {}),)),
            _registries(),
        )
    resolved = compose_experiment(
        _manifest(
            parameters=(*_manifest().parameters, PluginParameters(source_owner, {}))
        ),
        _registries(),
    )
    assert resolved.input_source.identity == CONFORMANCE_INPUT_SOURCE

    wrong = replace(
        _registries(),
        input_sources=VersionedPluginRegistry((_task(),), kind="input source plugin"),
    )
    with pytest.raises(ValueError, match="registry-set type mismatch for input source"):
        compose_experiment(
            _manifest(input_source=PluginSelection("dummy_reach_task", 1)), wrong
        )
