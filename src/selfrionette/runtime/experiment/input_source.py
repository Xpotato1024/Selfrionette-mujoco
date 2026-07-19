"""Generic versioned Input Source Plugin contracts.

This module deliberately owns no concrete device, robot, task, or viewer
implementation.  Existing ``InputSource`` remains the runtime reader
compatibility boundary; this module adds the versioned composition metadata
and optional lifecycle capability around it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from selfrionette.input_sources.base import InputSource
from selfrionette.runtime.experiment.contracts import (
    ParameterContract,
    VersionedIdentity,
)
from selfrionette.schemas import RawInputFrame


class InputSourceMode(str, Enum):
    OFFLINE = "offline"
    REPLAY = "replay"
    LIVE = "live"
    VIEWER_BRIDGE = "viewer_bridge"


# Descriptive alias used by callers that refer to the contract as SourceMode.
SourceMode = InputSourceMode


class InputSourceHealthStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    INVALID = "invalid"
    DISCONNECTED = "disconnected"


def _freeze_metadata(name: str, value: object) -> object:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        return 0.0 if value == 0.0 else value
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_metadata(f"{name}[{index}]", item)
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{name} keys must be strings")
            frozen[key] = _freeze_metadata(f"{name}.{key}", item)
        return MappingProxyType(dict(sorted(frozen.items())))
    raise TypeError(
        f"{name} must be a deterministic JSON-compatible value; "
        f"got {type(value).__name__}"
    )


@dataclass(frozen=True, slots=True)
class InputSourceHealth:
    status: InputSourceHealthStatus
    reason: str | None = None
    age_ms: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, InputSourceHealthStatus):
            raise TypeError("input source health status must use InputSourceHealthStatus")
        if self.status is InputSourceHealthStatus.ACTIVE:
            if self.reason is not None:
                raise ValueError("active input source health must not have a failure reason")
        elif not isinstance(self.reason, str) or not self.reason:
            raise ValueError(
                f"{self.status.value} input source health requires a reason"
            )
        if self.age_ms is not None and (
            type(self.age_ms) is not int or self.age_ms < 0
        ):
            raise ValueError("input source health age_ms must be None or a non-negative integer")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("input source health metadata must use a mapping")
        object.__setattr__(
            self,
            "metadata",
            _freeze_metadata("input source health metadata", self.metadata),
        )


@runtime_checkable
class ManagedInputSource(Protocol):
    """Optional lifecycle capability for live and viewer-bridge instances."""

    def start(self) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class InputSourceFactory(Protocol):
    def __call__(self, parameters: Mapping[str, object]) -> object: ...


@dataclass(frozen=True, slots=True)
class InputSourcePlugin:
    identity: VersionedIdentity
    produced_sample_schema: VersionedIdentity
    mode: InputSourceMode
    factory: InputSourceFactory
    parameter_contract: ParameterContract
    initial_health: InputSourceHealth
    initial_metadata: Mapping[str, object]
    produced_evidence: frozenset[VersionedIdentity] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.identity, VersionedIdentity):
            raise TypeError("input source plugin identity must use VersionedIdentity")
        if not isinstance(self.produced_sample_schema, VersionedIdentity):
            raise TypeError(
                "input source produced sample schema must use VersionedIdentity"
            )
        if not isinstance(self.mode, InputSourceMode):
            raise TypeError("input source mode must use InputSourceMode")
        if not isinstance(self.factory, InputSourceFactory):
            raise TypeError("input source plugin requires a typed factory")
        if not isinstance(self.parameter_contract, ParameterContract):
            raise TypeError("input source plugin requires a ParameterContract")
        if not isinstance(self.initial_health, InputSourceHealth):
            raise TypeError("input source plugin requires typed initial health")
        if not isinstance(self.initial_metadata, Mapping):
            raise TypeError("input source initial metadata must use a mapping")
        object.__setattr__(
            self,
            "initial_metadata",
            _freeze_metadata("input source initial metadata", self.initial_metadata),
        )
        evidence = frozenset(self.produced_evidence)
        if any(not isinstance(identity, VersionedIdentity) for identity in evidence):
            raise TypeError("input source produced evidence must use VersionedIdentity")
        object.__setattr__(self, "produced_evidence", evidence)

    def create_runtime_reader(self, parameters: Mapping[str, object]) -> InputSource:
        """Validate parameters and create one reader without starting it."""

        if not isinstance(parameters, Mapping):
            raise TypeError("input source parameters must use a mapping")
        frozen_parameters = _freeze_metadata("input source parameters", parameters)
        assert isinstance(frozen_parameters, Mapping)
        self.parameter_contract.validate(frozen_parameters)
        reader = self.factory(frozen_parameters)
        if not isinstance(reader, InputSource):
            raise TypeError(
                "input source factory returned an object that does not satisfy "
                "InputSource.read_frame()"
            )
        if self.mode in (InputSourceMode.LIVE, InputSourceMode.VIEWER_BRIDGE) and not isinstance(
            reader, ManagedInputSource
        ):
            raise TypeError(
                f"{self.mode.value} input source factory output must provide "
                "ManagedInputSource.start()/close()"
            )
        return reader

    @property
    def source_mode(self) -> InputSourceMode:
        return self.mode

    @property
    def produced_sample_schema_identity(self) -> VersionedIdentity:
        return self.produced_sample_schema

    # Short compatibility spelling for callers that use the generic reader term.
    def create_reader(self, parameters: Mapping[str, object]) -> InputSource:
        return self.create_runtime_reader(parameters)


__all__ = [
    "InputSourceFactory",
    "InputSourceHealth",
    "InputSourceHealthStatus",
    "InputSourceMode",
    "InputSourcePlugin",
    "InputSource",
    "ManagedInputSource",
    "RawInputFrame",
    "SourceMode",
]
