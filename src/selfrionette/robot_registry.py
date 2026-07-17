"""Compatibility facade for profile resolution and generic registry primitives."""

from selfrionette.plugins.catalog import (
    ROBOT_PROFILE_REGISTRY,
    registered_robot_profile_ids,
    resolve_robot_profile,
)
from selfrionette.runtime.robot_resolution import ImmutableRegistry

__all__ = [
    "ImmutableRegistry",
    "registered_robot_profile_ids",
    "resolve_robot_profile",
]
