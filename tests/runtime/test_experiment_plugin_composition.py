from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from selfrionette.robot_profile import (
    CoordinateUnitContract,
    EndpointReference,
    RobotProfile,
)
from selfrionette.runtime.default_robot_providers import NamedKeyframeInitialStateProvider
from selfrionette.runtime.experiment_composition import (
    ExperimentPluginManifest,
    ExperimentPluginRegistries,
    PluginParameters,
    compose_experiment,
)
from selfrionette.runtime.experiment_contracts import (
    CanonicalEvidence,
    CanonicalEvidenceSet,
    ControlMappingPlugin,
    EnvironmentPlugin,
    EnvironmentRole,
    EvaluationPlugin,
    EvidenceDisposition,
    EvidencePolicy,
    EvidenceStatus,
    MetricResult,
    ParameterContract,
    ParameterField,
    PluginSelection,
    SemanticRole,
    TaskPlugin,
    TaskTerminalClassification,
    VersionedIdentity,
)
from selfrionette.runtime.experiment_registry import VersionedPluginRegistry
from selfrionette.runtime.fast_arm_plugin import FAST_ARM_RUNTIME_PLUGIN
from selfrionette.runtime.robot_bundle import (
    CONTACT_EVIDENCE_V1,
    ENDPOINT_COMMAND_V1,
    ENDPOINT_POSE_V1,
    QPOS_FEASIBILITY_V1,
    RESET_INITIAL_STATE_V1,
    ROBOT_TOOL_ENDPOINT_ROLE,
    SCENE_ROLE_BINDING_V1,
    CapabilityProviderBinding,
    RobotBundle,
)
from selfrionette.runtime.robot_bundle_registry import resolve_robot_bundle


TARGET_ROLE = SemanticRole("environment.target_object")
TASK_TERMINAL_EVIDENCE = VersionedIdentity("task.terminal_classification", 1)
UNKNOWN_EVIDENCE = VersionedIdentity("evidence.not_produced", 1)


@dataclass(frozen=True)
class _DummyRuntimePlugin:
    profile: RobotProfile

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id

    def validate_model(self, model: object) -> None:
        return None

    def build_inverse_kinematics(self):
        raise NotImplementedError

    def build_forward_kinematics(self):
        raise NotImplementedError

    def build_target_motion_generator(self, **kwargs):
        return ("target-motion", kwargs)

    def build_local_endpoint_motion_generator(self):
        return "local-motion"

    def build_qpos_feasibility_guard(self, **kwargs):
        return ("qpos-guard", kwargs)

    def endpoint_position_from_state(self, state):
        return (0.0, 0.0, 0.0)

    def endpoint_orientation_from_state(self, state):
        return (1.0, 0.0, 0.0, 0.0)


class _EndpointPoseProvider:
    capability_identity = ENDPOINT_POSE_V1

    def observe_endpoint_pose(self, state):
        return object()


class _EndpointCommandProvider:
    capability_identity = ENDPOINT_COMMAND_V1

    def build_target_motion_generator(self, **kwargs):
        return object()

    def build_local_endpoint_motion_generator(self):
        return object()


class _QposFeasibilityProvider:
    capability_identity = QPOS_FEASIBILITY_V1

    def build_guard(self, **kwargs):
        return object()


class _SceneRoleProvider:
    capability_identity = SCENE_ROLE_BINDING_V1

    def semantic_role_bindings(self):
        from selfrionette.runtime.robot_bundle import SemanticRoleBinding

        return (
            SemanticRoleBinding(
                role=ROBOT_TOOL_ENDPOINT_ROLE,
                backend_kind="dummy",
                target_kind="site",
                target_id="endpoint",
            ),
        )


class _SceneProvider:
    def compose_scene(self, parameters):
        return dict(parameters)

    def reset_scene(self, scene):
        return None


class _MappingStrategy:
    def map_input(self, input_intent, parameters):
        return (input_intent, dict(parameters))


class _TaskLifecycle:
    def initial_state(self, parameters):
        return {"phase": "running", **parameters}

    def classify_terminal(self, state, evidence):
        return TaskTerminalClassification.SUCCESS


class _SuccessMetric:
    metric_id = VersionedIdentity("success_within_timeout", 1)

    def derive(self, evidence, parameters, *, provenance):
        terminal = evidence.require(TASK_TERMINAL_EVIDENCE)
        return MetricResult(
            metric_id=self.metric_id,
            value=terminal.value == TaskTerminalClassification.SUCCESS.value,
            status=EvidenceStatus.MEASURED,
            provenance=provenance,
        )


def _dummy_profile() -> RobotProfile:
    return RobotProfile(
        profile_id="dummy_robot",
        profile_contract_version=1,
        model_contract_version="dummy-model/v1",
        backend_kind="dummy",
        mujoco_model_asset=Path("dummy.xml"),
        canonical_joint_names=("joint",),
        qpos_dimension=1,
        qvel_dimension=1,
        initial_keyframe_name="neutral",
        endpoint=EndpointReference(site_name="endpoint", body_name=None),
        joint_limit_config_asset=None,
        coordinate_units=CoordinateUnitContract(
            position_unit="meter",
            angle_unit="rad",
            coordinate_frame="dummy world",
            quaternion_order="wxyz",
        ),
        viewer_profile_id="dummy_robot",
        supported_capabilities=frozenset(),
    )


def _dummy_bundle(
    *, include_endpoint_pose: bool = True, duplicate_endpoint_pose: bool = False
) -> RobotBundle:
    profile = _dummy_profile()
    plugin = _DummyRuntimePlugin(profile)
    providers = [
        CapabilityProviderBinding(
            RESET_INITIAL_STATE_V1,
            NamedKeyframeInitialStateProvider(profile),
        ),
        CapabilityProviderBinding(ENDPOINT_COMMAND_V1, _EndpointCommandProvider()),
        CapabilityProviderBinding(QPOS_FEASIBILITY_V1, _QposFeasibilityProvider()),
        CapabilityProviderBinding(SCENE_ROLE_BINDING_V1, _SceneRoleProvider()),
    ]
    if include_endpoint_pose:
        providers.append(CapabilityProviderBinding(ENDPOINT_POSE_V1, _EndpointPoseProvider()))
    if duplicate_endpoint_pose:
        providers.append(CapabilityProviderBinding(ENDPOINT_POSE_V1, _EndpointPoseProvider()))
    return RobotBundle(
        identity=VersionedIdentity("dummy_robot_bundle", 1),
        profile=profile,
        runtime_plugin=plugin,
        capability_providers=tuple(providers),
    )


def _environment(*, roles=(TARGET_ROLE,)) -> EnvironmentPlugin:
    return EnvironmentPlugin(
        identity=VersionedIdentity("dummy_environment", 1),
        scene_provider=_SceneProvider(),
        roles=tuple(
            EnvironmentRole(role, object_kind="target", frame="world", unit="meter")
            for role in roles
        ),
        required_robot_capabilities=frozenset({SCENE_ROLE_BINDING_V1}),
        required_robot_roles=frozenset({ROBOT_TOOL_ENDPOINT_ROLE}),
        parameter_contract=ParameterContract((ParameterField("target_x", float),)),
        compatible_backend_kinds=frozenset({"dummy"}),
    )


def _mapping() -> ControlMappingPlugin:
    return ControlMappingPlugin(
        identity=VersionedIdentity("dummy_mapping", 1),
        strategy=_MappingStrategy(),
        required_robot_capabilities=frozenset({ENDPOINT_COMMAND_V1}),
    )


def _task(*, produced_evidence=frozenset({TASK_TERMINAL_EVIDENCE})) -> TaskPlugin:
    return TaskPlugin(
        identity=VersionedIdentity("dummy_reach_task", 1),
        lifecycle=_TaskLifecycle(),
        required_robot_capabilities=frozenset({ENDPOINT_POSE_V1}),
        required_environment_roles=frozenset({ROBOT_TOOL_ENDPOINT_ROLE, TARGET_ROLE}),
        parameter_contract=ParameterContract(),
        task_event_identity=TASK_TERMINAL_EVIDENCE,
        produced_evidence=produced_evidence,
        compatible_environment_ids=frozenset({"dummy_environment"}),
        compatible_backend_kinds=frozenset({"dummy"}),
    )


def _evaluator(*, required=TASK_TERMINAL_EVIDENCE) -> EvaluationPlugin:
    return EvaluationPlugin(
        identity=VersionedIdentity("dummy_success_evaluator", 1),
        metric_deriver=_SuccessMetric(),
        required_evidence=frozenset({required}),
        evidence_policy=EvidencePolicy(),
        parameter_contract=ParameterContract(),
        provenance="dummy_success_evaluator/v1:deterministic",
    )


def _registries(
    *,
    bundle: RobotBundle | None = None,
    environment: EnvironmentPlugin | None = None,
    task: TaskPlugin | None = None,
    evaluator: EvaluationPlugin | None = None,
) -> ExperimentPluginRegistries:
    return ExperimentPluginRegistries(
        robot_bundles=VersionedPluginRegistry(
            (bundle or _dummy_bundle(),), kind="Robot Bundle"
        ),
        environments=VersionedPluginRegistry(
            (environment or _environment(),), kind="environment plugin"
        ),
        control_mappings=VersionedPluginRegistry((_mapping(),), kind="mapping plugin"),
        tasks=VersionedPluginRegistry((task or _task(),), kind="task plugin"),
        evaluators=VersionedPluginRegistry(
            (evaluator or _evaluator(),), kind="evaluation plugin"
        ),
    )


def _manifest(**overrides) -> ExperimentPluginManifest:
    values = {
        "robot_bundle": PluginSelection("dummy_robot_bundle", 1),
        "environment": PluginSelection("dummy_environment", 1),
        "control_mapping": PluginSelection("dummy_mapping", 1),
        "task": PluginSelection("dummy_reach_task", 1),
        "evaluators": (PluginSelection("dummy_success_evaluator", 1),),
        "parameters": (PluginParameters("dummy_environment", {"target_x": 0.2}),),
    }
    values.update(overrides)
    return ExperimentPluginManifest(**values)


def test_non_fast_arm_conformance_composition_resolves_all_axes_before_startup() -> None:
    resolved = compose_experiment(_manifest(), _registries())

    assert resolved.robot_bundle.identity.canonical_id == "dummy_robot_bundle/v1"
    assert resolved.environment.identity.canonical_id == "dummy_environment/v1"
    assert resolved.control_mapping.identity.canonical_id == "dummy_mapping/v1"
    assert resolved.task.identity.canonical_id == "dummy_reach_task/v1"
    assert tuple(item.identity.canonical_id for item in resolved.evaluators) == (
        "dummy_success_evaluator/v1",
    )
    assert ENDPOINT_POSE_V1 in resolved.resolved_capabilities
    assert resolved.resolved_roles == frozenset({ROBOT_TOOL_ENDPOINT_ROLE, TARGET_ROLE})
    reset = resolved.robot_bundle.provider(RESET_INITIAL_STATE_V1)
    assert reset.resolve_initial_state().source_id == "neutral"


def test_versioned_registries_reject_unknown_duplicate_and_version_mismatch() -> None:
    registry = VersionedPluginRegistry((_mapping(),), kind="mapping plugin")

    with pytest.raises(ValueError, match="unknown mapping plugin ID"):
        registry.resolve(PluginSelection("unknown", 1))
    with pytest.raises(ValueError, match="contract version mismatch"):
        registry.resolve(PluginSelection("dummy_mapping", 2))
    with pytest.raises(ValueError, match="duplicate mapping plugin registration"):
        VersionedPluginRegistry((_mapping(), _mapping()), kind="mapping plugin")


def test_composition_rejects_registry_set_type_mismatch() -> None:
    registries = _registries()
    mismatched = ExperimentPluginRegistries(
        robot_bundles=registries.robot_bundles,
        environments=registries.environments,
        control_mappings=VersionedPluginRegistry((_task(),), kind="mapping plugin"),
        tasks=registries.tasks,
        evaluators=registries.evaluators,
    )

    with pytest.raises(ValueError, match="registry-set type mismatch for control mapping"):
        compose_experiment(
            _manifest(control_mapping=PluginSelection("dummy_reach_task", 1)),
            mismatched,
        )


def test_composition_rejects_missing_capability_without_fallback() -> None:
    with pytest.raises(ValueError, match="unsupported Robot Bundle capability 'endpoint_pose/v1'"):
        compose_experiment(
            _manifest(),
            _registries(bundle=_dummy_bundle(include_endpoint_pose=False)),
        )


def test_composition_rejects_semantic_role_binding_failure() -> None:
    with pytest.raises(ValueError, match="semantic role binding failure"):
        compose_experiment(
            _manifest(),
            _registries(environment=_environment(roles=())),
        )


def test_composition_rejects_evaluator_evidence_requirement_mismatch() -> None:
    with pytest.raises(ValueError, match="evaluator evidence requirement mismatch"):
        compose_experiment(
            _manifest(),
            _registries(evaluator=_evaluator(required=UNKNOWN_EVIDENCE)),
        )


def test_robot_bundle_rejects_ambiguous_provider_and_has_no_unsupported_default() -> None:
    with pytest.raises(ValueError, match="ambiguous Robot Bundle capability provider"):
        _dummy_bundle(duplicate_endpoint_pose=True)

    with pytest.raises(
        ValueError,
        match="unsupported Robot Bundle capability 'contact_evidence/v1'",
    ):
        _dummy_bundle().provider(CONTACT_EVIDENCE_V1)


def test_composition_rejects_robot_environment_task_compatibility_mismatch() -> None:
    incompatible = EnvironmentPlugin(
        identity=VersionedIdentity("dummy_environment", 1),
        scene_provider=_SceneProvider(),
        roles=(EnvironmentRole(TARGET_ROLE, "target", "world", "meter"),),
        required_robot_capabilities=frozenset({SCENE_ROLE_BINDING_V1}),
        required_robot_roles=frozenset({ROBOT_TOOL_ENDPOINT_ROLE}),
        parameter_contract=ParameterContract((ParameterField("target_x", float),)),
        compatible_backend_kinds=frozenset({"not-dummy"}),
    )
    with pytest.raises(ValueError, match="robot backend/environment compatibility mismatch"):
        compose_experiment(_manifest(), _registries(environment=incompatible))


def test_evidence_statuses_remain_distinct_and_metric_is_deterministic() -> None:
    evaluator = _evaluator()
    evidence = CanonicalEvidenceSet(
        (
            CanonicalEvidence(
                identity=TASK_TERMINAL_EVIDENCE,
                status=EvidenceStatus.MEASURED,
                value=TaskTerminalClassification.SUCCESS.value,
                provenance="dummy_task/v1:terminal",
            ),
        )
    )

    first = evaluator.derive_metric(evidence, {})
    second = evaluator.derive_metric(evidence, {})
    assert first == second
    assert first.value is True
    assert first.provenance == "dummy_success_evaluator/v1:deterministic"

    with pytest.raises(ValueError, match="unavailable evidence must not carry a value"):
        CanonicalEvidence(
            identity=TASK_TERMINAL_EVIDENCE,
            status=EvidenceStatus.UNAVAILABLE,
            value=False,
            provenance="dummy",
            reason="not observed",
        )


def test_evaluator_applies_declared_missing_policy_without_inventing_a_metric() -> None:
    evaluator = EvaluationPlugin(
        identity=VersionedIdentity("policy_evaluator", 1),
        metric_deriver=_SuccessMetric(),
        required_evidence=frozenset({TASK_TERMINAL_EVIDENCE}),
        evidence_policy=EvidencePolicy(
            missing=EvidenceDisposition.PRODUCE_UNAVAILABLE
        ),
        parameter_contract=ParameterContract(),
        provenance="policy_evaluator/v1:deterministic",
    )

    result = evaluator.derive_metric(CanonicalEvidenceSet(()), {})

    assert result.status is EvidenceStatus.UNAVAILABLE
    assert result.value is None
    assert result.reason == "missing required evidence task.terminal_classification/v1"


def test_fast_arm_bundle_reuses_existing_profile_plugin_and_home_contract() -> None:
    bundle = resolve_robot_bundle("fast_arm", contract_version=1)

    assert bundle.runtime_plugin is FAST_ARM_RUNTIME_PLUGIN
    assert bundle.profile is FAST_ARM_RUNTIME_PLUGIN.profile
    assert bundle.provider(RESET_INITIAL_STATE_V1).resolve_initial_state().source_id == "home"
    assert bundle.provided_capabilities == frozenset(
        {
            RESET_INITIAL_STATE_V1,
            ENDPOINT_POSE_V1,
            ENDPOINT_COMMAND_V1,
            QPOS_FEASIBILITY_V1,
            SCENE_ROLE_BINDING_V1,
        }
    )
    assert CONTACT_EVIDENCE_V1 not in bundle.provided_capabilities


def test_manifest_rejects_duplicate_evaluator_and_unknown_parameter_owner() -> None:
    with pytest.raises(ValueError, match="duplicate evaluator selection"):
        _manifest(
            evaluators=(
                PluginSelection("dummy_success_evaluator", 1),
                PluginSelection("dummy_success_evaluator", 1),
            )
        )
    with pytest.raises(ValueError, match="parameters supplied for unselected plugins"):
        compose_experiment(
            _manifest(
                parameters=(
                    PluginParameters("dummy_environment", {"target_x": 0.2}),
                    PluginParameters("not-selected", {}),
                )
            ),
            _registries(),
        )
