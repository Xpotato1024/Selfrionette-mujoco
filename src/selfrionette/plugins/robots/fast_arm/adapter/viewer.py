"""Plugin-owned fast_arm viewer declaration loaded from its serializable SoT."""

from __future__ import annotations

import json

from selfrionette.runtime.composition.viewer_robot_declaration import (
    ViewerRobotDeclaration,
    decode_viewer_robot_declaration,
)
from selfrionette.plugins.robots.fast_arm.adapter.resources import (
    FAST_ARM_VIEWER_DECLARATION_RESOURCE as _VIEWER_RESOURCE,
)
from selfrionette.runtime.composition.robot_resource import read_package_resource_bytes


FAST_ARM_VIEWER_DECLARATION_RESOURCE = (
    "assets/mujoco/fast_arm/viewer-profile.json"
)

FAST_ARM_VIEWER_DECLARATION: ViewerRobotDeclaration = (
    decode_viewer_robot_declaration(
        json.loads(read_package_resource_bytes(_VIEWER_RESOURCE).decode("utf-8"))
    )
)


__all__ = [
    "FAST_ARM_VIEWER_DECLARATION",
    "FAST_ARM_VIEWER_DECLARATION_RESOURCE",
]
