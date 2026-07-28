"""Fixed discovery entry point for analog_fixture/v1."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from selfrionette.plugins.input_sources import analog_fixture
from selfrionette.plugins.input_sources.registration import (
    InputSourcePluginRegistration,
    InputSourcePluginRequest,
)
from selfrionette.runtime.execution.input_source_adapters import (
    ANALOG_FIXTURE_EXECUTION_ADAPTER,
)
from selfrionette.runtime.experiment.contracts import (
    ParameterContract,
    ParameterField,
    VersionedIdentity,
)
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceMode,
    InputSourcePlugin,
)
from selfrionette.schemas import RawInputFrame


def _request(
    *,
    steps: int,
    frames: Sequence[RawInputFrame] | None,
    preset: str | None,
    samples: Sequence[Mapping[str, object]] | None = None,
    **_: object,
) -> InputSourcePluginRequest:
    _ = (steps, frames)
    if preset is not None:
        raise ValueError("preset is not supported for analog_fixture input source")
    if samples is None:
        raise ValueError("analog_fixture input source requires fixture samples")
    parameters = {"samples": tuple(dict(sample) for sample in samples)}
    return InputSourcePluginRequest(
        parameters=parameters,
        frames=(),
        loop=False,
        initial_metadata={"source_kind": "analog_fixture"},
    )


_PLUGIN = InputSourcePlugin(
    identity=VersionedIdentity("analog_fixture", 1),
    produced_sample_schema=VersionedIdentity("analog_fixture_sample", 1),
    mode=InputSourceMode.REPLAY,
    factory=analog_fixture.build_reader,
    parameter_contract=ParameterContract((ParameterField("samples", tuple),)),
    initial_health=InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0),
    initial_metadata={"source_kind": "analog_fixture", "fixture": True},
)
INPUT_SOURCE_PLUGIN = InputSourcePluginRegistration(
    plugin=_PLUGIN,
    cli_aliases=("analog_fixture",),
    request_builder=_request,
    execution_adapter=ANALOG_FIXTURE_EXECUTION_ADAPTER,
)


__all__ = ["INPUT_SOURCE_PLUGIN"]
