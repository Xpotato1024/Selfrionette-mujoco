from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from selfrionette.mujoco_backend.model_contract import validate_fast_arm_model_name_contract
from selfrionette.mujoco_backend.model_info import inspect_mujoco_model
from selfrionette.schemas import JointCommand, MotionCommand

FAST_ARM_JOINT_LIMIT_SCHEMA_VERSION = 1
FAST_ARM_JOINT_NAMES: tuple[str, ...] = (
    "sholder_joint_1",
    "sholder_joint_2",
    "sholder_joint_3",
    "elbow_joint",
)


def default_fast_arm_joint_limits_path() -> Path:
    return Path(__file__).resolve().parents[3] / "configs" / "fast_arm" / "joint_limits.toml"


@dataclass(frozen=True, slots=True)
class FastArmJointLimit:
    name: str
    lower_rad: float
    upper_rad: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("joint name must not be empty")
        if not isfinite(self.lower_rad) or not isfinite(self.upper_rad):
            raise ValueError(f"joint {self.name!r} limits must be finite")
        if self.lower_rad >= self.upper_rad:
            raise ValueError(f"joint {self.name!r} lower_rad must be less than upper_rad")


@dataclass(frozen=True, slots=True)
class FastArmJointLimitViolation:
    joint_name: str
    candidate_value_rad: float
    lower_rad: float
    upper_rad: float


@dataclass(frozen=True, slots=True)
class FastArmJointLimitConfig:
    schema_version: int
    robot: str
    model: str
    angle_unit: str
    status: str
    joints: tuple[FastArmJointLimit, ...]

    def __post_init__(self) -> None:
        if self.schema_version != FAST_ARM_JOINT_LIMIT_SCHEMA_VERSION:
            raise ValueError(f"unsupported fast_arm joint-limit schema version: {self.schema_version!r}")
        if self.robot != "fast_arm":
            raise ValueError("fast_arm joint-limit robot must be 'fast_arm'")
        if self.model != "fast_arm":
            raise ValueError("fast_arm joint-limit model must be 'fast_arm'")
        if self.angle_unit != "rad":
            raise ValueError("fast_arm joint-limit angle_unit must be 'rad'")
        if self.status not in {"provisional", "validated"}:
            raise ValueError("fast_arm joint-limit status must be 'provisional' or 'validated'")
        names = tuple(joint.name for joint in self.joints)
        if len(names) != len(set(names)):
            raise ValueError("fast_arm joint-limit joint names must be unique")
        missing = tuple(name for name in FAST_ARM_JOINT_NAMES if name not in names)
        unknown = tuple(name for name in names if name not in FAST_ARM_JOINT_NAMES)
        if missing or unknown:
            raise ValueError(
                "fast_arm joint-limit joints must contain exactly the required joints: "
                f"missing={missing}, unknown={unknown}"
            )
        if names != FAST_ARM_JOINT_NAMES:
            raise ValueError(
                "fast_arm joint-limit joints must match the canonical order: "
                f"expected {FAST_ARM_JOINT_NAMES}, got {names}"
            )

    def limit_for(self, joint_name: str) -> FastArmJointLimit:
        for joint in self.joints:
            if joint.name == joint_name:
                return joint
        raise KeyError(joint_name)

    @property
    def joint_names(self) -> tuple[str, ...]:
        return tuple(joint.name for joint in self.joints)

    def violations_for_qpos(
        self,
        qpos_rad: Sequence[float],
    ) -> tuple[FastArmJointLimitViolation, ...]:
        values = tuple(float(value) for value in qpos_rad)
        if len(values) != len(self.joints):
            raise ValueError(
                "candidate qpos length does not match fast_arm joint-limit contract: "
                f"expected {len(self.joints)}, got {len(values)}"
            )

        violations: list[FastArmJointLimitViolation] = []
        for joint, value in zip(self.joints, values, strict=True):
            if not isfinite(value) or value < joint.lower_rad or value > joint.upper_rad:
                violations.append(
                    FastArmJointLimitViolation(
                        joint_name=joint.name,
                        candidate_value_rad=value,
                        lower_rad=joint.lower_rad,
                        upper_rad=joint.upper_rad,
                    )
                )
        return tuple(violations)


@dataclass(frozen=True, slots=True)
class FastArmQposFeasibilityResult:
    motion_command: MotionCommand
    accepted: bool
    action: str
    candidate_qpos_rad: tuple[float, ...] | None
    violations: tuple[FastArmJointLimitViolation, ...]


def _require_mapping(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a TOML table")
    return value


def _require_string(data: Mapping[str, object], *, name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_schema_version(data: Mapping[str, object]) -> int:
    value = data.get("schema_version")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("schema_version must be an integer")
    return value


def _require_finite_float(data: Mapping[str, object], *, name: str) -> float:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{name} must be a finite number")
    return numeric


def parse_fast_arm_joint_limit_config(path: str | Path) -> FastArmJointLimitConfig:
    resolved_path = Path(path).expanduser().resolve()
    if not resolved_path.is_file():
        raise FileNotFoundError(resolved_path)

    with resolved_path.open("rb") as stream:
        raw = tomllib.load(stream)

    schema_version = _require_schema_version(raw)
    robot = _require_string(raw, name="robot")
    model = _require_string(raw, name="model")
    angle_unit = _require_string(raw, name="angle_unit")
    status = _require_string(raw, name="status")
    joints_table = _require_mapping(raw.get("joints"), name="joints")
    joints: list[FastArmJointLimit] = []
    for joint_name, raw_joint in joints_table.items():
        if not isinstance(joint_name, str):
            raise ValueError("joint names must be strings")
        joint = _require_mapping(raw_joint, name=f"joints.{joint_name}")
        joints.append(
            FastArmJointLimit(
                name=joint_name,
                lower_rad=_require_finite_float(joint, name="lower_rad"),
                upper_rad=_require_finite_float(joint, name="upper_rad"),
            )
        )

    return FastArmJointLimitConfig(
        schema_version=schema_version,
        robot=robot,
        model=model,
        angle_unit=angle_unit,
        status=status,
        joints=tuple(joints),
    )


def validate_fast_arm_joint_limit_config(
    config: FastArmJointLimitConfig,
    model: object,
) -> FastArmJointLimitConfig:
    model_joint_names = inspect_mujoco_model(model).joint_names
    if model_joint_names != config.joint_names:
        missing = tuple(name for name in config.joint_names if name not in model_joint_names)
        unknown = tuple(name for name in model_joint_names if name not in config.joint_names)
        raise ValueError(
            "fast_arm joint-limit config does not match MuJoCo model joint order: "
            f"config={config.joint_names}, model={model_joint_names}, "
            f"missing={missing}, unknown={unknown}"
        )

    validate_fast_arm_model_name_contract(model)

    mujoco = _import_mujoco()
    keyframe_id = int(
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    )
    if keyframe_id < 0:
        raise ValueError("canonical fast_arm home keyframe is missing: home")
    home_qpos = tuple(float(value) for value in model.key("home").qpos)
    violations = config.violations_for_qpos(home_qpos)
    if violations:
        details = ", ".join(
            f"{violation.joint_name}={violation.candidate_value_rad} not in "
            f"[{violation.lower_rad}, {violation.upper_rad}]"
            for violation in violations
        )
        raise ValueError(f"canonical fast_arm home qpos is outside configured limits: {details}")
    return config


def load_and_validate_fast_arm_joint_limit_config(
    path: str | Path,
    *,
    model: object,
) -> FastArmJointLimitConfig:
    return validate_fast_arm_joint_limit_config(parse_fast_arm_joint_limit_config(path), model)


def _diagnostic_number(value: float) -> float | str:
    return value if isfinite(value) else repr(value)


def apply_fast_arm_qpos_feasibility_guard(
    motion_command: MotionCommand,
    *,
    current_qpos_rad: Sequence[float],
    joint_limits: FastArmJointLimitConfig,
) -> FastArmQposFeasibilityResult:
    if motion_command.joint is None:
        return FastArmQposFeasibilityResult(
            motion_command=motion_command,
            accepted=True,
            action="accept_no_qpos_candidate",
            candidate_qpos_rad=None,
            violations=(),
        )

    candidate_qpos_rad = tuple(float(value) for value in motion_command.joint.joint_angles_rad)
    violations = joint_limits.violations_for_qpos(candidate_qpos_rad)
    if not violations:
        return FastArmQposFeasibilityResult(
            motion_command=motion_command,
            accepted=True,
            action="accept",
            candidate_qpos_rad=candidate_qpos_rad,
            violations=(),
        )

    current_qpos = tuple(float(value) for value in current_qpos_rad)
    if len(current_qpos) != len(joint_limits.joints):
        raise ValueError(
            "current qpos length does not match fast_arm joint-limit contract: "
            f"expected {len(joint_limits.joints)}, got {len(current_qpos)}"
        )
    violation_metadata = tuple(
        {
            "joint_name": violation.joint_name,
            "candidate_value_rad": _diagnostic_number(violation.candidate_value_rad),
            "lower_rad": violation.lower_rad,
            "upper_rad": violation.upper_rad,
        }
        for violation in violations
    )
    metadata = {
        **dict(motion_command.metadata),
        "qpos_feasibility_status": "rejected",
        "qpos_feasibility_action": "hold_current_qpos",
        "qpos_rejection_reason": "joint_limit_violation",
        "qpos_feasibility_rejected": True,
        "qpos_candidate_rad": tuple(_diagnostic_number(value) for value in candidate_qpos_rad),
        "qpos_limit_violations": violation_metadata,
        "qpos_limit_status": joint_limits.status,
    }
    held_command = MotionCommand(
        timestamp_s=motion_command.timestamp_s,
        target=None,
        joint=JointCommand(joint_angles_rad=current_qpos),
        metadata=metadata,
    )
    return FastArmQposFeasibilityResult(
        motion_command=held_command,
        accepted=False,
        action="hold_current_qpos",
        candidate_qpos_rad=candidate_qpos_rad,
        violations=violations,
    )


def _import_mujoco() -> object:
    import mujoco

    return mujoco


__all__ = [
    "FAST_ARM_JOINT_LIMIT_SCHEMA_VERSION",
    "FAST_ARM_JOINT_NAMES",
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
