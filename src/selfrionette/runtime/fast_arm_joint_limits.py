"""Compatibility facade for the fast_arm feasibility implementation."""

from selfrionette.plugins.robots.fast_arm.feasibility import (
    FAST_ARM_JOINT_LIMIT_SCHEMA_VERSION,
    FAST_ARM_JOINT_NAMES,
    FastArmJointLimit,
    FastArmJointLimitConfig,
    FastArmJointLimitGuard,
    FastArmJointLimitViolation,
    FastArmQposFeasibilityResult,
    apply_fast_arm_qpos_feasibility_guard,
    default_fast_arm_joint_limits_path,
    load_and_validate_fast_arm_joint_limit_config,
    parse_fast_arm_joint_limit_config,
    validate_fast_arm_joint_limit_config,
)

__all__ = [
    "FAST_ARM_JOINT_LIMIT_SCHEMA_VERSION",
    "FAST_ARM_JOINT_NAMES",
    "FastArmJointLimitGuard",
    "FastArmJointLimit",
    "FastArmJointLimitConfig",
    "FastArmJointLimitViolation",
    "FastArmQposFeasibilityResult",
    "apply_fast_arm_qpos_feasibility_guard",
    "default_fast_arm_joint_limits_path",
    "load_and_validate_fast_arm_joint_limit_config",
    "parse_fast_arm_joint_limit_config",
    "validate_fast_arm_joint_limit_config",
]
