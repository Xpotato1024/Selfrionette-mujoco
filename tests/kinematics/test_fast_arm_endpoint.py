from __future__ import annotations

from selfrionette.plugins.robots.fast_arm.endpoint import extract_fast_arm_tip_site_endpoint_from_state

from selfrionette.plugins.robots.fast_arm.runtime import build_fast_arm_simulator

import math

import pytest

from selfrionette.plugins.robots.fast_arm.kinematics import (
    FAST_ARM_MUJOCO_MODEL_JOINT_REFS_RAD,
    FAST_ARM_MUJOCO_MODEL_TIP_SITE_NAME,
    FastArmEndpointForwardKinematicsSolver,
    FastArmEndpointInverseKinematicsSolver,
    FastArmMuJoCoModelForwardKinematicsSolver,
)
from selfrionette.mujoco_backend import (
    HeadlessMuJoCoSimulator,
)
from selfrionette.schemas import JointCommand



def test_fast_arm_mujoco_model_fk_matches_tip_site_for_fixed_qpos_fixtures() -> None:
    solver = FastArmMuJoCoModelForwardKinematicsSolver()
    qpos_fixtures = (
        (0.0, -math.pi / 2.0, 0.0, 0.0),
        (0.02, -1.5607963267948965, 0.015, 0.005),
        (-0.02, -1.5807963267948966, -0.015, -0.005),
        (0.0, -1.8274309072438202, 0.0, 0.0),
    )

    for qpos in qpos_fixtures:
        simulator = build_fast_arm_simulator()
        simulator.apply_qpos_command(JointCommand(joint_angles_rad=qpos))
        tip_site = extract_fast_arm_tip_site_endpoint_from_state(simulator.snapshot())

        assert tip_site.kind == "site"
        assert tip_site.name == FAST_ARM_MUJOCO_MODEL_TIP_SITE_NAME
        assert solver.forward(qpos) == pytest.approx(tip_site.position_m, abs=1e-9)


def test_fast_arm_mujoco_model_fk_preserves_joint_ref_contract() -> None:
    solver = FastArmMuJoCoModelForwardKinematicsSolver()

    assert solver.joint_refs_rad == pytest.approx(
        (0.0, -math.pi / 2.0, 0.0, 0.0),
        abs=1e-12,
    )
    assert FAST_ARM_MUJOCO_MODEL_JOINT_REFS_RAD == pytest.approx(
        solver.joint_refs_rad,
        abs=1e-12,
    )
