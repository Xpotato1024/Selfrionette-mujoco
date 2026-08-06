"""production Taskをexact logical identityで解決するcatalog。"""

from selfrionette.plugins.tasks.discovery import discover_production_task_plugins
from selfrionette.runtime.experiment.contracts import PluginSelection, TaskPlugin


TASK_REGISTRY = discover_production_task_plugins()
TASK_PLUGINS: tuple[TaskPlugin, ...] = TASK_REGISTRY.entries


def resolve_task_plugin(selection: PluginSelection) -> TaskPlugin:
    """Resolve one production Task without starting its lifecycle."""

    return TASK_REGISTRY.resolve(selection)


__all__ = ["TASK_PLUGINS", "TASK_REGISTRY", "resolve_task_plugin"]
