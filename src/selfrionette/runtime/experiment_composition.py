"""Fail-closed startup readiness for explicit experiment plugin composition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from selfrionette.runtime.experiment_contracts import (
    ControlMappingPlugin,
    EnvironmentPlugin,
    EvaluationPlugin,
    PluginSelection,
    SemanticRole,
    TaskPlugin,
    VersionedIdentity,
)
from selfrionette.runtime.experiment_registry import VersionedPluginRegistry
from selfrionette.runtime.robot_bundle import RobotBundle


@dataclass(frozen=True, slots=True)
class PluginParameters:
    plugin_id: str
    values: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.plugin_id:
            raise ValueError("plugin parameter owner ID must not be empty")


@dataclass(frozen=True, slots=True)
class ExperimentPluginManifest:
    robot_bundle: PluginSelection
    environment: PluginSelection
    control_mapping: PluginSelection
    task: PluginSelection
    evaluators: tuple[PluginSelection, ...]
    parameters: tuple[PluginParameters, ...] = ()

    def __post_init__(self) -> None:
        evaluator_ids = tuple(selection.plugin_id for selection in self.evaluators)
        if len(evaluator_ids) != len(set(evaluator_ids)):
            raise ValueError("duplicate evaluator selection")
        parameter_ids = tuple(item.plugin_id for item in self.parameters)
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("duplicate plugin parameter owner")


@dataclass(frozen=True, slots=True)
class ExperimentPluginRegistries:
    robot_bundles: VersionedPluginRegistry[RobotBundle]
    environments: VersionedPluginRegistry[EnvironmentPlugin]
    control_mappings: VersionedPluginRegistry[ControlMappingPlugin]
    tasks: VersionedPluginRegistry[TaskPlugin]
    evaluators: VersionedPluginRegistry[EvaluationPlugin]


@dataclass(frozen=True, slots=True)
class ResolvedExperimentComposition:
    manifest: ExperimentPluginManifest
    robot_bundle: RobotBundle
    environment: EnvironmentPlugin
    control_mapping: ControlMappingPlugin
    task: TaskPlugin
    evaluators: tuple[EvaluationPlugin, ...]
    resolved_capabilities: frozenset[VersionedIdentity]
    resolved_roles: frozenset[SemanticRole]
    available_evidence: frozenset[VersionedIdentity]


def _parameters_by_id(
    manifest: ExperimentPluginManifest,
) -> dict[str, Mapping[str, object]]:
    return {item.plugin_id: item.values for item in manifest.parameters}


def _validate_compatibility(
    robot: RobotBundle,
    environment: EnvironmentPlugin,
    task: TaskPlugin,
) -> None:
    bundle_id = robot.identity.name
    backend_kind = robot.profile.backend_kind
    if (
        environment.compatible_robot_bundle_ids
        and bundle_id not in environment.compatible_robot_bundle_ids
    ):
        raise ValueError("robot/environment compatibility mismatch")
    if (
        environment.compatible_backend_kinds
        and backend_kind not in environment.compatible_backend_kinds
    ):
        raise ValueError("robot backend/environment compatibility mismatch")
    if task.compatible_robot_bundle_ids and bundle_id not in task.compatible_robot_bundle_ids:
        raise ValueError("robot/task compatibility mismatch")
    if (
        task.compatible_environment_ids
        and environment.identity.name not in task.compatible_environment_ids
    ):
        raise ValueError("environment/task compatibility mismatch")
    if task.compatible_backend_kinds and backend_kind not in task.compatible_backend_kinds:
        raise ValueError("robot backend/task compatibility mismatch")


def compose_experiment(
    manifest: ExperimentPluginManifest,
    registries: ExperimentPluginRegistries,
) -> ResolvedExperimentComposition:
    robot = registries.robot_bundles.resolve(manifest.robot_bundle)
    environment = registries.environments.resolve(manifest.environment)
    mapping = registries.control_mappings.resolve(manifest.control_mapping)
    task = registries.tasks.resolve(manifest.task)
    evaluators = tuple(
        registries.evaluators.resolve(selection) for selection in manifest.evaluators
    )
    resolved_types = (
        (robot, RobotBundle, "Robot Bundle"),
        (environment, EnvironmentPlugin, "environment"),
        (mapping, ControlMappingPlugin, "control mapping"),
        (task, TaskPlugin, "task"),
        *((evaluator, EvaluationPlugin, "evaluation") for evaluator in evaluators),
    )
    for plugin, expected_type, registry_kind in resolved_types:
        if not isinstance(plugin, expected_type):
            raise ValueError(
                f"experiment registry-set type mismatch for {registry_kind}: "
                f"expected {expected_type.__name__}, got {type(plugin).__name__}"
            )

    parameter_values = _parameters_by_id(manifest)
    selected_plugins = (environment, mapping, task, *evaluators)
    selected_ids = {plugin.identity.name for plugin in selected_plugins}
    unknown_parameter_owners = tuple(sorted(set(parameter_values) - selected_ids))
    if unknown_parameter_owners:
        raise ValueError(
            f"parameters supplied for unselected plugins: {unknown_parameter_owners}"
        )
    for plugin in selected_plugins:
        plugin.parameter_contract.validate(parameter_values.get(plugin.identity.name, {}))

    required_capabilities = (
        environment.required_robot_capabilities
        | mapping.required_robot_capabilities
        | task.required_robot_capabilities
    )
    for capability in required_capabilities:
        robot.provider(capability)

    robot_role_bindings = robot.semantic_role_bindings()
    robot_roles = tuple(binding.role for binding in robot_role_bindings)
    if len(robot_roles) != len(set(robot_roles)):
        raise ValueError("ambiguous robot semantic role provider")
    environment_roles = tuple(item.role for item in environment.roles)
    combined_roles = robot_roles + environment_roles
    if len(combined_roles) != len(set(combined_roles)):
        raise ValueError("ambiguous semantic role binding across robot and environment")
    resolved_roles = frozenset(combined_roles)
    required_roles = environment.required_robot_roles | task.required_environment_roles
    missing_roles = tuple(
        sorted(role.name for role in required_roles if role not in resolved_roles)
    )
    if missing_roles:
        raise ValueError(f"semantic role binding failure: missing {missing_roles}")

    _validate_compatibility(robot, environment, task)

    available_evidence = (
        robot.provided_evidence
        | environment.produced_evidence
        | mapping.produced_evidence
        | task.produced_evidence
    )
    for evaluator in evaluators:
        missing_evidence = tuple(
            sorted(
                identity.canonical_id
                for identity in evaluator.required_evidence
                if identity not in available_evidence
            )
        )
        if missing_evidence:
            raise ValueError(
                f"evaluator evidence requirement mismatch for "
                f"{evaluator.identity.canonical_id!r}: missing {missing_evidence}"
            )

    return ResolvedExperimentComposition(
        manifest=manifest,
        robot_bundle=robot,
        environment=environment,
        control_mapping=mapping,
        task=task,
        evaluators=evaluators,
        resolved_capabilities=robot.provided_capabilities,
        resolved_roles=resolved_roles,
        available_evidence=available_evidence,
    )


__all__ = [
    "ExperimentPluginManifest",
    "ExperimentPluginRegistries",
    "PluginParameters",
    "ResolvedExperimentComposition",
    "compose_experiment",
]
