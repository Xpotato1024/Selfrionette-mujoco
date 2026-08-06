"""Production six-axis catalogs exposed to application composition roots.

This module lists axis infrastructure, not concrete plugin identities.  Each
catalog remains populated by bounded discovery in its owning axis package.
"""

from selfrionette.plugins.environments.catalog import ENVIRONMENT_REGISTRY
from selfrionette.plugins.evaluations.catalog import EVALUATION_REGISTRY
from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.catalog import CONTROL_MAPPING_REGISTRY
from selfrionette.plugins.robots.catalog import ROBOT_BUNDLE_REGISTRY
from selfrionette.plugins.tasks.catalog import TASK_REGISTRY
from selfrionette.runtime.experiment.composition import (
    ExperimentPluginManifest,
    ExperimentPluginRegistries,
    ResolvedExperimentComposition,
    compose_experiment,
)


PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES = ExperimentPluginRegistries(
    robot_bundles=ROBOT_BUNDLE_REGISTRY,
    environments=ENVIRONMENT_REGISTRY,
    control_mappings=CONTROL_MAPPING_REGISTRY,
    tasks=TASK_REGISTRY,
    evaluators=EVALUATION_REGISTRY,
    input_sources=INPUT_SOURCE_CATALOG.registry,
)


def resolve_production_experiment(
    manifest: ExperimentPluginManifest,
) -> ResolvedExperimentComposition:
    """Resolve all six production axes without starting any lifecycle."""

    return compose_experiment(manifest, PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES)


__all__ = [
    "PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES",
    "resolve_production_experiment",
]
