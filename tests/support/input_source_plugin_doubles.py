from __future__ import annotations

from collections.abc import Mapping

from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceMode,
    InputSourcePlugin,
)
from selfrionette.runtime.experiment.contracts import (
    ParameterContract,
    VersionedIdentity,
)
from selfrionette.schemas import RawInputFrame


CONFORMANCE_INPUT_SOURCE = VersionedIdentity("conformance_input_source", 1)
CONFORMANCE_SAMPLE_SCHEMA = VersionedIdentity("conformance_sample", 1)


class ConformanceInputSourceReader:
    def __init__(self, parameters: Mapping[str, object]) -> None:
        self.parameters = dict(parameters)
        self.started = False
        self.closed = False

    def read_frame(self) -> RawInputFrame:
        return RawInputFrame(
            source="conformance_input_source",
            timestamp_s=1.0,
            values=(0.25, -0.5),
            metadata={"fixture": "deterministic"},
        )


class ManagedConformanceInputSourceReader(ConformanceInputSourceReader):
    def start(self) -> None:
        self.started = True

    def close(self) -> None:
        self.closed = True


def build_conformance_input_source(
    *,
    mode: InputSourceMode = InputSourceMode.OFFLINE,
    parameter_contract: ParameterContract = ParameterContract(),
    accepted: bool = True,
    produced_evidence: frozenset[VersionedIdentity] = frozenset(),
) -> InputSourcePlugin:
    def factory(parameters: Mapping[str, object]) -> object:
        if mode in (InputSourceMode.LIVE, InputSourceMode.VIEWER_BRIDGE):
            return ManagedConformanceInputSourceReader(parameters)
        return ConformanceInputSourceReader(parameters)

    return InputSourcePlugin(
        identity=CONFORMANCE_INPUT_SOURCE,
        produced_sample_schema=CONFORMANCE_SAMPLE_SCHEMA,
        mode=mode,
        factory=factory,
        parameter_contract=parameter_contract,
        initial_health=InputSourceHealth(InputSourceHealthStatus.ACTIVE),
        initial_metadata={"fixture": "deterministic", "mode": mode.value},
        produced_evidence=produced_evidence,
    )
