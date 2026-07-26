"""Versioned contracts shared by experiment composition plugins."""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
        if type(self.version) is not int or self.version < 1:
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
        if type(self.contract_version) is not int or self.contract_version < 1:
            raise ValueError("contract_version must be positive")


class PluginAxis(str, Enum):
    ROBOT_BUNDLE = "robot_bundle"
    ENVIRONMENT = "environment"
    CONTROL_MAPPING = "control_mapping"
    TASK = "task"
    EVALUATION = "evaluation"
    INPUT_SOURCE = "input_source"


@dataclass(frozen=True, slots=True)
class PluginParameterOwner:
    axis: PluginAxis
    selection: PluginSelection

    def __post_init__(self) -> None:
        if not isinstance(self.axis, PluginAxis):
            raise TypeError("plugin parameter owner axis must use PluginAxis")
        if not isinstance(self.selection, PluginSelection):
            raise TypeError("plugin parameter owner selection must use PluginSelection")

    @property
    def canonical_id(self) -> str:
        return (
            f"{self.axis.value}:{self.selection.plugin_id}"
            f"/v{self.selection.contract_version}"
        )


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
    condition_specific: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("parameter field name must not be empty")
        if type(self.required) is not bool:
            raise TypeError("parameter field required must be a bool")
        if type(self.condition_specific) is not bool:
            raise TypeError("parameter field condition_specific must be a bool")


@dataclass(frozen=True, slots=True)
class ParameterContract:
    fields: tuple[ParameterField, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.fields, tuple):
            object.__setattr__(self, "fields", tuple(self.fields))
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
            if expected in (int, float) and isinstance(value, bool):
                raise ValueError(
                    f"plugin parameter {name!r} must be {expected.__name__}, "
                    "not bool"
                )
            if not _parameter_value_matches(expected, value):
                raise ValueError(
                    f"plugin parameter {name!r} must be {expected.__name__}, "
                    f"got {type(value).__name__}"
                )

    @property
    def condition_specific_field_names(self) -> frozenset[str]:
        return frozenset(
            field.name for field in self.fields if field.condition_specific
        )


def _parameter_value_matches(expected: type, value: object) -> bool:
    """Match frozen recursive JSON values against the generic parameter contract."""

    if expected is list:
        return isinstance(value, tuple)
    if expected is tuple:
        return isinstance(value, tuple)
    if expected is dict:
        return isinstance(value, Mapping)
    if expected is Mapping:
        return isinstance(value, Mapping)
    return isinstance(value, expected)


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
        if not isinstance(self.role, SemanticRole):
            raise TypeError("environment role must use SemanticRole")
        if not self.object_kind or not self.frame or not self.unit:
            raise ValueError("environment role kind, frame, and unit must not be empty")


ROLE_ATTRIBUTE_WILDCARD = "*"


@dataclass(frozen=True, slots=True, order=True)
class SemanticRoleRequirement:
    role: SemanticRole
    object_kind: str
    frame: str
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, SemanticRole):
            raise TypeError("semantic role requirement must use SemanticRole")
        if not self.object_kind or not self.frame or not self.unit:
            raise ValueError(
                "semantic role requirement kind, frame, and unit must not be empty; "
                "use '*' as an explicit wildcard"
            )

    def matches(self, descriptor: EnvironmentRole) -> bool:
        return self.role == descriptor.role and all(
            required == ROLE_ATTRIBUTE_WILDCARD or required == actual
            for required, actual in (
                (self.object_kind, descriptor.object_kind),
                (self.frame, descriptor.frame),
                (self.unit, descriptor.unit),
            )
        )


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
    required_robot_roles: frozenset[SemanticRoleRequirement] = field(default_factory=frozenset)
    parameter_contract: ParameterContract = ParameterContract()
    produced_evidence: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    backend_scene_owner: str = "runtime"
    viewer_presentation_reference: str | None = None
    compatible_robot_bundles: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    compatible_backend_kinds: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.scene_provider, EnvironmentSceneProvider):
            raise TypeError("environment plugin requires a typed scene provider")
        if self.backend_scene_owner != "runtime":
            raise ValueError("environment backend scene composition owner must be runtime")
        roles = tuple(item.role for item in self.roles)
        if len(roles) != len(set(roles)):
            raise ValueError("environment plugin roles must be unique")
        if any(
            not isinstance(requirement, SemanticRoleRequirement)
            for requirement in self.required_robot_roles
        ):
            raise TypeError(
                "environment required robot roles must use SemanticRoleRequirement"
            )
        if any(
            not isinstance(identity, VersionedIdentity)
            for identity in self.compatible_robot_bundles
        ):
            raise TypeError(
                "environment compatible Robot Bundles must use VersionedIdentity"
            )


@dataclass(frozen=True, slots=True)
class ControlMappingPlugin:
    identity: VersionedIdentity
    strategy: ControlMappingStrategy
    accepted_input_sample_schemas: frozenset[VersionedIdentity]
    required_robot_capabilities: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    parameter_contract: ParameterContract = ParameterContract()
    produced_evidence: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    control_frame: str | None = None
    comparison_family_identity: VersionedIdentity | None = None
    mapping_semantics_identity: VersionedIdentity | None = None
    parameter_normalizer: Callable[[Mapping[str, object]], Mapping[str, object]] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, ControlMappingStrategy):
            raise TypeError("control mapping plugin requires a typed mapping strategy")
        schemas = frozenset(self.accepted_input_sample_schemas)
        if any(not isinstance(identity, VersionedIdentity) for identity in schemas):
            raise TypeError(
                "control mapping accepted input sample schemas must use VersionedIdentity"
            )
        object.__setattr__(self, "accepted_input_sample_schemas", schemas)
        if self.control_frame is not None and self.control_frame not in {"world", "tool"}:
            raise ValueError("control mapping control_frame must be 'world' or 'tool'")
        for name, identity in (
            ("comparison_family_identity", self.comparison_family_identity),
            ("mapping_semantics_identity", self.mapping_semantics_identity),
        ):
            if identity is not None and not isinstance(identity, VersionedIdentity):
                raise TypeError(f"{name} must use VersionedIdentity")
        if self.mapping_semantics_identity is not None:
            strategy_identity = getattr(self.strategy, "mapping_semantics_identity", None)
            if strategy_identity != self.mapping_semantics_identity:
                raise ValueError(
                    "mapping strategy semantic identity mismatch: "
                    "strategy and plugin must declare the same VersionedIdentity"
                )
        if self.parameter_normalizer is not None and not callable(self.parameter_normalizer):
            raise TypeError("control mapping parameter_normalizer must be callable")


@dataclass(frozen=True, slots=True)
class TaskPlugin:
    identity: VersionedIdentity
    lifecycle: TaskLifecycleStrategy
    required_robot_capabilities: frozenset[VersionedIdentity]
    required_semantic_roles: frozenset[SemanticRoleRequirement]
    parameter_contract: ParameterContract
    task_event_identity: VersionedIdentity
    produced_evidence: frozenset[VersionedIdentity]
    compatible_robot_bundles: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    compatible_environments: frozenset[VersionedIdentity] = field(default_factory=frozenset)
    compatible_backend_kinds: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle, TaskLifecycleStrategy):
            raise TypeError("task plugin requires a typed lifecycle strategy")
        if self.task_event_identity not in self.produced_evidence:
            raise ValueError("task event identity must be declared as produced evidence")
        if any(
            not isinstance(requirement, SemanticRoleRequirement)
            for requirement in self.required_semantic_roles
        ):
            raise TypeError("task required roles must use SemanticRoleRequirement")
        if any(
            not isinstance(identity, VersionedIdentity)
            for identity in self.compatible_robot_bundles
        ):
            raise TypeError("task compatible Robot Bundles must use VersionedIdentity")
        if any(
            not isinstance(identity, VersionedIdentity)
            for identity in self.compatible_environments
        ):
            raise TypeError("task compatible environments must use VersionedIdentity")


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
        result = self.metric_deriver.derive(
            evidence,
            parameters,
            provenance=self.provenance,
        )
        if not isinstance(result, MetricResult):
            raise TypeError("evaluation strategy must return MetricResult")
        if result.metric_id != self.identity:
            raise ValueError(
                "evaluation metric identity mismatch: "
                f"expected {self.identity.canonical_id!r}, "
                f"got {result.metric_id.canonical_id!r}"
            )
        if result.provenance != self.provenance:
            raise ValueError(
                "evaluation metric provenance mismatch: "
                f"expected {self.provenance!r}, got {result.provenance!r}"
            )
        return result


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
    "PluginAxis",
    "PluginParameterOwner",
    "PluginSelection",
    "ROLE_ATTRIBUTE_WILDCARD",
    "SemanticRole",
    "SemanticRoleRequirement",
    "TaskLifecycleStrategy",
    "TaskPlugin",
    "TaskTerminalClassification",
    "VersionedIdentity",
]
