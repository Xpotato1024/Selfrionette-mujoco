"""Explicit deterministic registry for test-only robot conformance cases."""

from __future__ import annotations

from tests.plugins.robots.fast_arm.adapter.conformance_case import (
    FAST_ARM_ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASE,
)

from tests.support.robot_runtime_plugin_conformance import (
    RobotRuntimePluginConformanceCase,
)


ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASES: tuple[RobotRuntimePluginConformanceCase, ...] = (
    FAST_ARM_ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASE,
)


__all__ = ["ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASES"]
