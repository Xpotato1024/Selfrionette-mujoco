"""Additive Robot Bundle and typed capability-provider boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from selfrionette.motion.base import MotionGenerator
from selfrionette.robot_profile import RobotProfile
from selfrionette.runtime.experiment_contracts import (
    CanonicalEvidence,
    ParameterContract,
    SemanticRole,
    VersionedIdentity,
)
from selfrionette.runtime.qpos_feasibility import QposFeasibilityGuard
from selfrionette.runtime.robot_plugin import RobotRuntimePlugin
from selfrionette.runtime.robot_plugin_registry import validate_robot_profile_plugin_consistency
from selfrionette.schemas import MuJoCoState


RESET_INITIAL_STATE_V1 = VersionedIdentity("reset_initial_state", 1)
ENDPOINT_POSE_V1 = VersionedIdentity("endpoint_pose", 1)
ENDPOINT_COMMAND_V1 = VersionedIdentity("endpoint_command", 1)
QPOS_FEASIBILITY_V1 = VersionedIdentity("qpos_feasibility", 1)
SCENE_ROLE_BINDING_V1 = VersionedIdentity("scene_role_binding", 1)
CONTACT_EVIDENCE_V1 = VersionedIdentity("contact_evidence", 1)

ROBOT_TOOL_ENDPOINT_ROLE = SemanticRole("robot.tool_endpoint")


@dataclass(frozen=True, slots=True)
class InitialStateReference:
    source_kind: str
    source_id: str

    def __post_init__(self) -> None:
        if not self.source_kind or not self.source_id:
            raise ValueError("initial state source kind and ID must not be empty")


@dataclass(frozen=True, slots=True)
class EndpointPoseObservation:
    position_m: tuple[float, float, float] | None
    quaternion_wxyz: tuple[float, float, float, float] | None


@dataclass(frozen=True, slots=True)
class SemanticRoleBinding:
    role: SemanticRole
    backend_kind: str
    target_kind: str
    target_id: str
    object_kind: str
    frame: str
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, SemanticRole):
            raise TypeError("semantic role binding must use SemanticRole")
        if any(
            not value
            for value in (
                self.backend_kind,
                self.target_kind,
                self.target_id,
                self.object_kind,
                self.frame,
                self.unit,
            )
        ):
            raise ValueError("semantic role binding fields must not be empty")


@runtime_checkable
class ResetInitialStateProvider(Protocol):
    capability_identity: VersionedIdentity

    def resolve_initial_state(self) -> InitialStateReference: ...


@runtime_checkable
class EndpointPoseProvider(Protocol):
    capability_identity: VersionedIdentity

    def observe_endpoint_pose(self, state: MuJoCoState) -> EndpointPoseObservation: ...


@runtime_checkable
class EndpointCommandProvider(Protocol):
    capability_identity: VersionedIdentity

    def build_target_motion_generator(
        self,
        *,
        seed_joint_angles_rad: tuple[float, ...] | None,
        discontinuity_threshold_rad: float | None,
        discontinuity_threshold_label: str,
    ) -> MotionGenerator: ...

    def build_local_endpoint_motion_generator(self) -> MotionGenerator: ...


@runtime_checkable
class QposFeasibilityProvider(Protocol):
    capability_identity: VersionedIdentity

    def build_guard(
        self, *, model: object, config_path: str | Path | None
    ) -> QposFeasibilityGuard: ...


@runtime_checkable
class SceneRoleBindingProvider(Protocol):
    capability_identity: VersionedIdentity

    def semantic_role_bindings(self) -> tuple[SemanticRoleBinding, ...]: ...


@runtime_checkable
class ContactEvidenceProvider(Protocol):
    capability_identity: VersionedIdentity

    @property
    def evidence_identities(self) -> frozenset[VersionedIdentity]: ...

    def observe_contact_evidence(
        self, state: MuJoCoState
    ) -> tuple[CanonicalEvidence, ...]: ...


CAPABILITY_PROVIDER_TYPES: Mapping[VersionedIdentity, type] = MappingProxyType(
    {
        RESET_INITIAL_STATE_V1: ResetInitialStateProvider,
        ENDPOINT_POSE_V1: EndpointPoseProvider,
        ENDPOINT_COMMAND_V1: EndpointCommandProvider,
        QPOS_FEASIBILITY_V1: QposFeasibilityProvider,
        SCENE_ROLE_BINDING_V1: SceneRoleBindingProvider,
        CONTACT_EVIDENCE_V1: ContactEvidenceProvider,
    }
)


@dataclass(frozen=True, slots=True)
class CapabilityProviderBinding:
    identity: VersionedIdentity
    provider: object

    def __post_init__(self) -> None:
        expected_type = CAPABILITY_PROVIDER_TYPES.get(self.identity)
        if expected_type is None:
            raise ValueError(f"unknown capability identity {self.identity.canonical_id!r}")
        if not isinstance(self.provider, expected_type):
            raise TypeError(
                f"provider for {self.identity.canonical_id!r} does not satisfy "
                f"{expected_type.__name__}"
            )
        if getattr(self.provider, "capability_identity", None) != self.identity:
            raise ValueError(
                f"provider capability identity mismatch for {self.identity.canonical_id!r}"
            )


@dataclass(frozen=True, slots=True)
class RobotBundle:
    identity: VersionedIdentity
    profile: RobotProfile
    runtime_plugin: RobotRuntimePlugin
    capability_providers: tuple[CapabilityProviderBinding, ...]
    parameter_contract: ParameterContract = ParameterContract()

    def __post_init__(self) -> None:
        validate_robot_profile_plugin_consistency(
            self.profile.profile_id, self.profile, self.runtime_plugin
        )
        identities = tuple(binding.identity for binding in self.capability_providers)
        if len(identities) != len(set(identities)):
            raise ValueError("ambiguous Robot Bundle capability provider registration")

    @property
    def provided_capabilities(self) -> frozenset[VersionedIdentity]:
        return frozenset(binding.identity for binding in self.capability_providers)

    def provider(self, identity: VersionedIdentity) -> object:
        providers = tuple(
            binding.provider
            for binding in self.capability_providers
            if binding.identity == identity
        )
        if not providers:
            provided_ids = tuple(
                item.canonical_id for item in sorted(self.provided_capabilities)
            )
            raise ValueError(
                f"unsupported Robot Bundle capability {identity.canonical_id!r}; "
                f"provided={provided_ids}"
            )
        if len(providers) != 1:
            raise ValueError(
                f"ambiguous Robot Bundle capability provider {identity.canonical_id!r}"
            )
        return providers[0]

    def semantic_role_bindings(self) -> tuple[SemanticRoleBinding, ...]:
        provider = self.provider(SCENE_ROLE_BINDING_V1)
        assert isinstance(provider, SceneRoleBindingProvider)
        return provider.semantic_role_bindings()

    @property
    def provided_evidence(self) -> frozenset[VersionedIdentity]:
        if CONTACT_EVIDENCE_V1 not in self.provided_capabilities:
            return frozenset()
        provider = self.provider(CONTACT_EVIDENCE_V1)
        assert isinstance(provider, ContactEvidenceProvider)
        return provider.evidence_identities


__all__ = [
    "CAPABILITY_PROVIDER_TYPES",
    "CONTACT_EVIDENCE_V1",
    "CapabilityProviderBinding",
    "ContactEvidenceProvider",
    "ENDPOINT_COMMAND_V1",
    "ENDPOINT_POSE_V1",
    "EndpointCommandProvider",
    "EndpointPoseObservation",
    "EndpointPoseProvider",
    "InitialStateReference",
    "QPOS_FEASIBILITY_V1",
    "QposFeasibilityProvider",
    "RESET_INITIAL_STATE_V1",
    "ROBOT_TOOL_ENDPOINT_ROLE",
    "ResetInitialStateProvider",
    "RobotBundle",
    "SCENE_ROLE_BINDING_V1",
    "SceneRoleBindingProvider",
    "SemanticRoleBinding",
]
