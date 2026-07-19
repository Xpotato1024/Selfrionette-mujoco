from __future__ import annotations

import importlib.resources
import math

import mujoco
import pytest

from fast_arm_core.model_kinematics import (
    FAST_ARM_MUJOCO_MODEL_JOINT_REFS_RAD,
    FAST_ARM_MUJOCO_MODEL_TIP_SITE_NAME,
    FastArmModelForwardKinematics,
)


def _load_model() -> mujoco.MjModel:
    model_root = importlib.resources.files("fast_arm_core").joinpath("resources/model")
    with importlib.resources.as_file(model_root) as path:
        return mujoco.MjModel.from_xml_path(str(path / "arm.xml"))


def _tip_site_position(model: mujoco.MjModel, qpos: tuple[float, ...]) -> tuple[float, ...]:
    data = mujoco.MjData(model)
    data.qpos[:] = qpos
    mujoco.mj_forward(model, data)
    tip_site_id = model.site(FAST_ARM_MUJOCO_MODEL_TIP_SITE_NAME).id
    return tuple(float(value) for value in data.site_xpos[tip_site_id])


def test_fast_arm_mujoco_model_fk_matches_tip_site_for_fixed_qpos_fixtures() -> None:
    solver = FastArmModelForwardKinematics()
    model = _load_model()
    qpos_fixtures = (
        (0.0, -math.pi / 2.0, 0.0, 0.0),
        (0.02, -1.5607963267948965, 0.015, 0.005),
        (-0.02, -1.5807963267948966, -0.015, -0.005),
        (0.0, -1.8274309072438202, 0.0, 0.0),
    )

    for qpos in qpos_fixtures:
        assert solver.forward(qpos) == pytest.approx(
            _tip_site_position(model, qpos), abs=1e-9
        )


def test_fast_arm_mujoco_model_fk_preserves_joint_ref_contract() -> None:
    solver = FastArmModelForwardKinematics()

    assert solver.joint_refs_rad == pytest.approx(
        (0.0, -math.pi / 2.0, 0.0, 0.0),
        abs=1e-12,
    )
    assert FAST_ARM_MUJOCO_MODEL_JOINT_REFS_RAD == pytest.approx(
        solver.joint_refs_rad,
        abs=1e-12,
    )
