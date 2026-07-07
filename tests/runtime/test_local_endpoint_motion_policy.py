from __future__ import annotations

import math

import pytest

from selfrionette.kinematics.fast_arm_endpoint import FastArmMuJoCoModelForwardKinematicsSolver
from selfrionette.motion import LocalEndpointMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, extract_fast_arm_tip_site_endpoint_from_state
from selfrionette.schemas import InputIntent, JointCommand


class _RecordingEndpointKinematics:
    def __init__(self) -> None:
        self.calls: list[tuple[float, ...]] = []

    def forward(self, qpos_rad):
        qpos = tuple(float(component) for component in qpos_rad)
        self.calls.append(qpos)
        return (qpos[0], qpos[1], qpos[2])


def _intent(
    *,
    axis_values: tuple[float, float, float],
    endpoint_velocity_m_s: tuple[float, float, float],
    dt_s: float,
) -> InputIntent:
    return InputIntent(
        source="viewer_keyboard",
        timestamp_s=1.0,
        values=axis_values,
        metadata={
            "intent_kind": "local_endpoint_velocity",
            "input_continuity": "continuous",
            "axis_values": axis_values,
            "endpoint_velocity_m_s": endpoint_velocity_m_s,
            "local_endpoint_speed_m_s": 0.1,
            "local_endpoint_max_delta_m": 0.03,
            "dt_s": dt_s,
        },
    )


def test_local_endpoint_motion_generator_uses_injected_endpoint_kinematics() -> None:
    endpoint_kinematics = _RecordingEndpointKinematics()
    generator = LocalEndpointMotionGenerator(
        endpoint_kinematics=endpoint_kinematics,
        endpoint_model="recording_endpoint_model",
    )
    generator.set_current_qpos_rad((0.0, -1.5707963267948966, 0.0, 0.0))

    command = generator.update(
        _intent(
            axis_values=(1.0, 0.0, 0.0),
            endpoint_velocity_m_s=(0.1, 0.0, 0.0),
            dt_s=1.0 / 60.0,
        ),
        dt_s=1.0 / 60.0,
    )

    assert endpoint_kinematics.calls
    assert command.metadata["endpoint_model"] == "recording_endpoint_model"
    assert command.metadata["local_motion_policy"] == "finite_difference_jacobian"
    assert command.metadata["current_tip_position_m"] == pytest.approx((0.0, -1.5707963267948966, 0.0), abs=1e-12)


def test_local_endpoint_motion_generator_matches_mujoco_tip_site_for_representative_qpos() -> None:
    solver = FastArmMuJoCoModelForwardKinematicsSolver()
    generator = LocalEndpointMotionGenerator(
        endpoint_kinematics=solver,
        endpoint_model="mujoco_model_aligned_tip_site",
    )
    qpos = (0.0, -1.5707963267948966, 0.0, 0.0)
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    simulator.apply_qpos_command(JointCommand(joint_angles_rad=qpos))
    tip_site = extract_fast_arm_tip_site_endpoint_from_state(simulator.snapshot())

    generator.set_current_qpos_rad(qpos)
    command = generator.update(
        _intent(
            axis_values=(0.0, 0.0, 0.0),
            endpoint_velocity_m_s=(0.0, 0.0, 0.0),
            dt_s=1.0 / 60.0,
        ),
        dt_s=1.0 / 60.0,
    )

    assert solver.forward(qpos) == pytest.approx(tip_site.position_m, abs=1e-9)
    assert command.metadata["current_tip_position_m"] == pytest.approx(tip_site.position_m, abs=1e-9)
    assert command.metadata["endpoint_model"] == "mujoco_model_aligned_tip_site"
    assert command.metadata["endpoint_delta_achieved_m"] == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_local_endpoint_motion_generator_dt_scales_requested_endpoint_delta() -> None:
    generator = LocalEndpointMotionGenerator(
        endpoint_kinematics=FastArmMuJoCoModelForwardKinematicsSolver(),
        endpoint_model="mujoco_model_aligned_tip_site",
    )
    generator.set_current_qpos_rad((0.0, -1.5707963267948966, 0.0, 0.0))

    fast_command = generator.update(
        _intent(
            axis_values=(0.0, 1.0, 0.0),
            endpoint_velocity_m_s=(0.0, 0.1, 0.0),
            dt_s=1.0 / 60.0,
        ),
        dt_s=1.0 / 60.0,
    )
    slow_command = generator.update(
        _intent(
            axis_values=(0.0, 1.0, 0.0),
            endpoint_velocity_m_s=(0.0, 0.1, 0.0),
            dt_s=1.0 / 30.0,
        ),
        dt_s=1.0 / 30.0,
    )

    assert fast_command.metadata["endpoint_delta_requested_m"][1] == pytest.approx(1.0 / 600.0, abs=1e-12)
    assert slow_command.metadata["endpoint_delta_requested_m"][1] == pytest.approx(1.0 / 300.0, abs=1e-12)
    assert slow_command.metadata["endpoint_delta_requested_m"][1] == pytest.approx(
        fast_command.metadata["endpoint_delta_requested_m"][1] * 2.0,
        abs=1e-12,
    )


def test_local_endpoint_motion_generator_scales_large_dt_boundary_motion() -> None:
    generator = LocalEndpointMotionGenerator(
        endpoint_kinematics=FastArmMuJoCoModelForwardKinematicsSolver(),
        endpoint_model="mujoco_model_aligned_tip_site",
    )
    generator.set_current_qpos_rad((0.0, -1.5707963267948966, 0.0, 0.0))

    command = generator.update(
        _intent(
            axis_values=(1.0, 0.0, 0.0),
            endpoint_velocity_m_s=(0.1, 0.0, 0.0),
            dt_s=1.0,
        ),
        dt_s=1.0,
    )

    assert command.metadata["motion_status"] == "scaled"
    assert command.metadata["endpoint_delta_requested_m"] == pytest.approx((0.01, 0.0, 0.0), abs=1e-12)
    assert command.metadata["motion_rejection_reason"] is None
