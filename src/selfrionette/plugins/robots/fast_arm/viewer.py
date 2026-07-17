"""Plugin-owned fast_arm viewer declaration loaded from its serializable SoT."""

from __future__ import annotations

import json
from pathlib import Path

from selfrionette.viewer_robot_declaration import (
    ViewerRobotDeclaration,
    decode_viewer_robot_declaration,
)


FAST_ARM_VIEWER_DECLARATION_RESOURCE = (
    "assets/mujoco/fast_arm/viewer-profile.json"
)
_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]

FAST_ARM_VIEWER_DECLARATION: ViewerRobotDeclaration = (
    decode_viewer_robot_declaration(
        json.loads(
            (_REPOSITORY_ROOT / FAST_ARM_VIEWER_DECLARATION_RESOURCE).read_text(
                encoding="utf-8"
            )
        )
    )
)


__all__ = [
    "FAST_ARM_VIEWER_DECLARATION",
    "FAST_ARM_VIEWER_DECLARATION_RESOURCE",
]
