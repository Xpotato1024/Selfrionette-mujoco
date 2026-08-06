"""production Evaluationをexact logical identityで解決するcatalog。"""

from selfrionette.plugins.evaluations.discovery import (
    discover_production_evaluation_plugins,
)
from selfrionette.runtime.experiment.contracts import EvaluationPlugin, PluginSelection


EVALUATION_REGISTRY = discover_production_evaluation_plugins()
EVALUATION_PLUGINS: tuple[EvaluationPlugin, ...] = EVALUATION_REGISTRY.entries


def resolve_evaluation_plugin(selection: PluginSelection) -> EvaluationPlugin:
    """Resolve one production Evaluation without deriving a metric."""

    return EVALUATION_REGISTRY.resolve(selection)


__all__ = [
    "EVALUATION_PLUGINS",
    "EVALUATION_REGISTRY",
    "resolve_evaluation_plugin",
]
