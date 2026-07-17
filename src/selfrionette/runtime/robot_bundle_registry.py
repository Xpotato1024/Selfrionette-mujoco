"""Compatibility facade for production Robot Bundle resolution."""

from selfrionette.plugins.catalog import (
    ROBOT_BUNDLE_REGISTRY,
    registered_robot_bundle_ids,
    resolve_robot_bundle,
)

__all__ = [
    "ROBOT_BUNDLE_REGISTRY",
    "registered_robot_bundle_ids",
    "resolve_robot_bundle",
]
