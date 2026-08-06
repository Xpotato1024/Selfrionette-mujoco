"""R7-G free-space scene condition with no task object or contact surface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from selfrionette.runtime.experiment.contracts import (
    EnvironmentPlugin,
    ParameterContract,
    VersionedIdentity,
)


FREE_SPACE_ENVIRONMENT_IDENTITY = VersionedIdentity(
    "free_space_environment", 1
)


@dataclass(frozen=True, slots=True)
class FreeSpaceSceneCondition:
    """Robot-owned base sceneにtask objectを追加しないscene projection。"""

    uses_robot_base_scene: bool = True
    task_objects: tuple[object, ...] = ()
    contact_required: bool = False


class FreeSpaceSceneProvider:
    """Side-effect-free provider for the explicit free-space condition."""

    def compose_scene(self, parameters: Mapping[str, object]) -> FreeSpaceSceneCondition:
        if parameters:
            raise ValueError("free-space environment does not accept parameters")
        return FreeSpaceSceneCondition()

    def reset_scene(self, scene: object) -> None:
        if not isinstance(scene, FreeSpaceSceneCondition):
            raise TypeError("free-space environment reset requires its scene condition")


FREE_SPACE_ENVIRONMENT_PLUGIN = EnvironmentPlugin(
    identity=FREE_SPACE_ENVIRONMENT_IDENTITY,
    scene_provider=FreeSpaceSceneProvider(),
    roles=(),
    parameter_contract=ParameterContract(),
    produced_evidence=frozenset(),
    compatible_backend_kinds=frozenset({"mujoco"}),
)


__all__ = [
    "FREE_SPACE_ENVIRONMENT_IDENTITY",
    "FREE_SPACE_ENVIRONMENT_PLUGIN",
    "FreeSpaceSceneCondition",
    "FreeSpaceSceneProvider",
]
