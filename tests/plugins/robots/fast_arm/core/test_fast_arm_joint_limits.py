from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from fast_arm_core.joint_limits import (
    FastArmJointLimit,
    parse_fast_arm_joint_limit_bytes,
    parse_fast_arm_joint_limit_file,
)
DEFAULT_CONFIG_BYTES = files("fast_arm_core").joinpath(
    "resources/config/joint_limits.toml"
).read_bytes()
DEFAULT_CONFIG_TEXT = DEFAULT_CONFIG_BYTES.decode("utf-8")


def _write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "joint_limits.toml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def test_default_config_is_provisional_rad_and_covers_all_fast_arm_joints() -> None:
    config = parse_fast_arm_joint_limit_bytes(DEFAULT_CONFIG_BYTES)

    assert config.schema_version == 1
    assert config.robot == "fast_arm"
    assert config.model == "fast_arm"
    assert config.angle_unit == "rad"
    assert config.status == "provisional"
    assert config.joint_names == (
        "sholder_joint_1",
        "sholder_joint_2",
        "sholder_joint_3",
        "elbow_joint",
    )
    assert all(config.limit_for(name).lower_rad == pytest.approx(-3.141592653589793) for name in config.joint_names)
    assert all(config.limit_for(name).upper_rad == pytest.approx(3.141592653589793) for name in config.joint_names)


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (('schema_version = 1', 'schema_version = 2'), "unsupported"),
        (('robot = \"fast_arm\"', 'robot = \"other\"'), "robot"),
        (('model = \"fast_arm\"', 'model = \"other\"'), "model"),
        (('angle_unit = \"rad\"', 'angle_unit = \"deg\"'), "angle_unit"),
        (('status = \"provisional\"', 'status = \"unknown\"'), "status"),
        (('lower_rad = -3.141592653589793', 'lower_rad = nan'), "finite"),
        (('upper_rad = 3.141592653589793', 'upper_rad = inf'), "finite"),
        (
            (
                "lower_rad = -3.141592653589793\nupper_rad = 3.141592653589793",
                "lower_rad = 1.0\nupper_rad = 1.0",
            ),
            "lower_rad",
        ),
        (
            (
                "lower_rad = -3.141592653589793\nupper_rad = 3.141592653589793",
                "lower_rad = 1.0\nupper_rad = 0.5",
            ),
            "lower_rad",
        ),
    ],
)
def test_invalid_config_values_fail_at_parse_or_value_validation(
    tmp_path: Path,
    replacement: tuple[str, str],
    message: str,
) -> None:
    path = _write_config(tmp_path, DEFAULT_CONFIG_TEXT.replace(*replacement))

    with pytest.raises(ValueError, match=message):
        parse_fast_arm_joint_limit_file(path)


@pytest.mark.parametrize(
    "replacement",
    [
        ("[joints.elbow_joint]", "[joints.unknown_joint]"),
        ("[joints.elbow_joint]\nlower_rad = -3.141592653589793\nupper_rad = 3.141592653589793\n", ""),
    ],
)
def test_missing_or_unknown_joint_is_rejected(tmp_path: Path, replacement: tuple[str, str]) -> None:
    path = _write_config(tmp_path, DEFAULT_CONFIG_TEXT.replace(*replacement))

    with pytest.raises(ValueError, match="required"):
        parse_fast_arm_joint_limit_file(path)


@pytest.mark.parametrize(
    "arguments,message",
    (
        (("", -1.0, 1.0), "joint name must not be empty"),
        (("joint", float("inf"), 1.0), "joint 'joint' limits must be finite"),
        (
            ("joint", 1.0, 1.0),
            "joint 'joint' lower_rad must be less than upper_rad",
        ),
    ),
)
def test_core_joint_limit_validation_preserves_failure_literals(
    arguments: tuple[str, float, float], message: str
) -> None:
    with pytest.raises(ValueError) as exc_info:
        FastArmJointLimit(*arguments)
    assert str(exc_info.value) == message
