"""Versioned contracts shared by experiment composition plugins."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True, order=True)
class VersionedIdentity:
    name: str
    version: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("versioned identity name must not be empty")
        if self.version < 1:
            raise ValueError("versioned identity version must be positive")

    @property
    def canonical_id(self) -> str:
        return f"{self.name}/v{self.version}"


@dataclass(frozen=True, slots=True)
class PluginSelection:
    plugin_id: str
    contract_version: int

    def __post_init__(self) -> None:
        if not self.plugin_id:
            raise ValueError("plugin_id must not be empty")
        if self.contract_version < 1:
            raise ValueError("contract_version must be positive")


class EvidenceStatus(str, Enum):
    REQUESTED = "requested"
    RESOLVED = "resolved"
    PREDICTED = "predicted"
    MEASURED = "measured"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class CanonicalEvidence:
    identity: VersionedIdentity
    status: EvidenceStatus
    value: object | None
    provenance: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ValueError("canonical evidence provenance must not be empty")
        if self.status in (EvidenceStatus.UNAVAILABLE, EvidenceStatus.INVALID):
            if self.value is not None:
                raise ValueError(f"{self.status.value} evidence must not carry a value")
            if not self.reason:
                raise ValueError(f"{self.status.value} evidence requires a reason")
        elif self.status in (
            EvidenceStatus.RESOLVED,
            EvidenceStatus.PREDICTED,
            EvidenceStatus.MEASURED,
        ) and self.value is None:
            raise ValueError(f"{self.status.value} evidence requires a value")


class CanonicalEvidenceSet:
    def __init__(self, entries: tuple[CanonicalEvidence, ...]) -> None:
        values: dict[VersionedIdentity, CanonicalEvidence] = {}
        for entry in entries:
            if entry.identity in values:
                raise ValueError(
                    f"duplicate canonical evidence: {entry.identity.canonical_id!r}"
                )
            values[entry.identity] = entry
        self._values = values

    @property
    def identities(self) -> frozenset[VersionedIdentity]:
        return frozenset(self._values)

    def require(self, identity: VersionedIdentity) -> CanonicalEvidence:
        try:
            return self._values[identity]
        except KeyError as exc:
            raise ValueError(
                f"missing canonical evidence {identity.canonical_id!r}"
            ) from exc


@dataclass(frozen=True, slots=True)
class ParameterField:
    name: str
    value_type: type
    required: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("parameter field name must not be empty")


@dataclass(frozen=True, slots=True)
class ParameterContract:
    fields: tuple[ParameterField, ...] = ()

    def __post_init__(self) -> None:
        names = tuple(field.name for field in self.fields)
        if len(names) != len(set(names)):
            raise ValueError("parameter contract field names must be unique")

    def validate(self, parameters: Mapping[str, object]) -> None:
        declared = {field.name: field for field in self.fields}
        unknown = tuple(sorted(set(parameters) - set(declared)))
        if unknown:
            raise ValueError(f"unknown plugin parameters: {unknown}")
        missing = tuple(
            field.name
            for field in self.fields
            if field.required and field.name not in parameters
        )
        if missing:
            raise ValueError(f"missing required plugin parameters: {missing}")
        for name, value in parameters.items():
            expected = declared[name].value_type
            if not isinstance(value, expected):
                raise ValueError(
                    f"plugin parameter {name!r} must be {expected.__name__}, "
                    f"got {type(value).__name__}"
                )


@dataclass(frozen=True, slots=True, order=True)
class SemanticRole:
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("semantic role name must not be empty")


@dataclass(frozen=True, slots=True)
class EnvironmentRole:
    role: SemanticRole
    object_kind: str
    frame: str
    unit: str

    def __post_init__(self) -> None:
        if not self.object_kind or not self.frame or not self.unit:
            raise ValueError("environment role kind, frame, and unit must not be empty")


@runtime_checkable
class EnvironmentSceneProvider(Protocol):
    def compose_scene(self, parameters: Mapping[str, object]) -> object: ...

    def reset_scene(self, scene: object) -> None: ...


@runtime_checkable
class ControlMappingStrategy(Protocol):
    def map_input(self, input_intent: object, parameters: Mapping[str, object]) -> object: ...


class TaskTerminalClassification(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TECHNICAL_INVALID = "technical_invalid"


@runtime_checkable
class TaskLifecycleStrategy(Protocol):
    def initial_state(self, parameters: Mapping[str, object]) -> object: ...

    def classify_terminal(
        self, state: object, evidence: CanonicalEvidenceSet
    ) -> TaskTerminalClassification: ...


class EvidenceDisposition(str, Enum):
    REJECT = "reject"
    PRODUCE_UNAVAILABLE = "produce_unavailable"
    PRODUCE_INVALID = "produce_invalid"


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    missing: EvidenceDisposition = EvidenceDisposition.REJECT
    unavailable: EvidenceDisposition = EvidenceDisposition.REJECT
    invalid: EvidenceDisposition = EvidenceDisposition.REJECT


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_id: VersionedIdentity
    value: object | None
    status: EvidenceStatus
    provenance: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ValueError("metric result provenance must not be empty")
        if self.status in (EvidenceStatus.UNAVAILABLE, EvidenceStatus.INVALID):
            if self.value is not None:
                raise ValueError(f"{self.status.value} metric must not carry a value")
            if not self.reason:
                raise ValueError(f"{self.status.value} metric requires a reason")
        elif self.value is None:
            raise ValueError(f"{self.status.value} metric requires a value")


@runtime_checkable
class MetricDerivationStrategy(Protocol):
    def derive(
        self,
        evidence: CanonicalEvidenceSet,
        parameters: Mapping[str, object],
        *,
        provenance: str,
    ) -> MetricResult: ...


@dataclass(frozen=True, slots=True)
class EnvironmentPlugin:
    identity: VersionedIdentity
    scene_provider: EnvironmentSceneProvider
    roles: tuple[EnvironmentRole, ...]
    required_robot_capabilities: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    required_robot_roles: frozenset[SemanticRole] = field(default_factory=frozenset)
    parameter_contract: ParameterContract = ParameterContract()
    produced_evidence: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    backend_scene_owner: str = "runtime"
    viewer_presentation_reference: str | None = None
    compatible_robot_bundle_ids: frozenset[str] = field(default_factory=frozenset)
    compatible_backend_kinds: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.scene_provider, EnvironmentSceneProvider):
            raise TypeError("environment plugin requires a typed scene provider")
        if self.backend_scene_owner != "runtime":
            raise ValueError("environment backend scene composition owner must be runtime")
        roles = tuple(item.role for item in self.roles)
        if len(roles) != len(set(roles)):
            raise ValueError("environment plugin roles must be unique")


@dataclass(frozen=True, slots=True)
class ControlMappingPlugin:
    identity: VersionedIdentity
    strategy: ControlMappingStrategy
    required_robot_capabilities: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    parameter_contract: ParameterContract = ParameterContract()
    produced_evidence: frozenset[VersionedIdentity] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, ControlMappingStrategy):
            raise TypeError("control mapping plugin requires a typed mapping strategy")


@dataclass(frozen=True, slots=True)
class TaskPlugin:
    identity: VersionedIdentity
    lifecycle: TaskLifecycleStrategy
    required_robot_capabilities: frozenset[VersionedIdentity]
    required_environment_roles: frozenset[SemanticRole]
    parameter_contract: ParameterContract
    task_event_identity: VersionedIdentity
    produced_evidence: frozenset[VersionedIdentity]
    compatible_robot_bundle_ids: frozenset[str] = field(default_factory=frozenset)
    compatible_environment_ids: frozenset[str] = field(default_factory=frozenset)
    compatible_backend_kinds: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle, TaskLifecycleStrategy):
            raise TypeError("task plugin requires a typed lifecycle strategy")
        if self.task_event_identity not in self.produced_evidence:
            raise ValueError("task event identity must be declared as produced evidence")


@dataclass(frozen=True, slots=True)
class EvaluationPlugin:
    identity: VersionedIdentity
    metric_deriver: MetricDerivationStrategy
    required_evidence: frozenset[VersionedIdentity]
    evidence_policy: EvidencePolicy
    parameter_contract: ParameterContract
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.metric_deriver, MetricDerivationStrategy):
            raise TypeError("evaluation plugin requires a typed metric derivation strategy")
        if not self.provenance:
            raise ValueError("evaluation plugin provenance must not be empty")

    def derive_metric(
        self,
        evidence: CanonicalEvidenceSet,
        parameters: Mapping[str, object],
    ) -> MetricResult:
        self.parameter_contract.validate(parameters)
        for identity in self.required_evidence:
            if identity not in evidence.identities:
                if self.evidence_policy.missing is EvidenceDisposition.REJECT:
                    raise ValueError(
                        f"missing evaluator evidence {identity.canonical_id!r}"
                    )
                status = (
                    EvidenceStatus.UNAVAILABLE
                    if self.evidence_policy.missing
                    is EvidenceDisposition.PRODUCE_UNAVAILABLE
                    else EvidenceStatus.INVALID
                )
                return MetricResult(
                    metric_id=self.identity,
                    value=None,
                    status=status,
                    provenance=self.provenance,
                    reason=f"missing required evidence {identity.canonical_id}",
                )
            entry = evidence.require(identity)
            if entry.status is EvidenceStatus.UNAVAILABLE:
                if self.evidence_policy.unavailable is EvidenceDisposition.REJECT:
                    raise ValueError(
                        f"unavailable evaluator evidence {identity.canonical_id!r}"
                    )
                return MetricResult(
                    metric_id=self.identity,
                    value=None,
                    status=(
                        EvidenceStatus.UNAVAILABLE
                        if self.evidence_policy.unavailable
                        is EvidenceDisposition.PRODUCE_UNAVAILABLE
                        else EvidenceStatus.INVALID
                    ),
                    provenance=self.provenance,
                    reason=f"required evidence unavailable: {identity.canonical_id}",
                )
            elif entry.status is EvidenceStatus.INVALID:
                if self.evidence_policy.invalid is EvidenceDisposition.REJECT:
                    raise ValueError(f"invalid evaluator evidence {identity.canonical_id!r}")
                return MetricResult(
                    metric_id=self.identity,
                    value=None,
                    status=(
                        EvidenceStatus.UNAVAILABLE
                        if self.evidence_policy.invalid
                        is EvidenceDisposition.PRODUCE_UNAVAILABLE
                        else EvidenceStatus.INVALID
                    ),
                    provenance=self.provenance,
                    reason=f"required evidence invalid: {identity.canonical_id}",
                )
        return self.metric_deriver.derive(
            evidence,
            parameters,
            provenance=self.provenance,
        )


__all__ = [
    "CanonicalEvidence",
    "CanonicalEvidenceSet",
    "ControlMappingPlugin",
    "ControlMappingStrategy",
    "EnvironmentPlugin",
    "EnvironmentRole",
    "EnvironmentSceneProvider",
    "EvaluationPlugin",
    "EvidenceDisposition",
    "EvidencePolicy",
    "EvidenceStatus",
    "MetricDerivationStrategy",
    "MetricResult",
    "ParameterContract",
    "ParameterField",
    "PluginSelection",
    "SemanticRole",
    "TaskLifecycleStrategy",
    "TaskPlugin",
    "TaskTerminalClassification",
    "VersionedIdentity",
]
