from __future__ import annotations

import pytest

from selfrionette.motion import LocalEndpointMotionGenerator
from selfrionette.schemas import InputIntent


def _intent(*, axis_values: tuple[float, float, float], endpoint_velocity_m_s: tuple[float, float, float], dt_s: float) -> InputIntent:
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


def test_local_endpoint_motion_generator_accepts_small_motion() -> None:
    generator = LocalEndpointMotionGenerator()
    generator.set_current_qpos_rad((0.0, -1.5707963267948966, 0.0, 0.0))

    command = generator.update(
        _intent(
            axis_values=(1.0, 0.0, 0.0),
            endpoint_velocity_m_s=(0.1, 0.0, 0.0),
            dt_s=1.0 / 60.0,
        ),
        dt_s=1.0 / 60.0,
    )

    assert command.metadata["local_motion_policy"] == "finite_difference_jacobian"
    assert command.metadata["motion_status"] in {"accepted", "scaled"}
    assert command.metadata["qpos_delta_norm_rad"] <= 0.2 + 1e-12
    assert command.metadata["endpoint_delta_requested_m"] == pytest.approx((1.0 / 600.0, 0.0, 0.0), abs=1e-12)
    assert command.metadata["endpoint_delta_achieved_m"][0] > 0.0
    assert command.joint is not None


def test_local_endpoint_motion_generator_dt_scales_requested_endpoint_delta() -> None:
    generator = LocalEndpointMotionGenerator()
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
    generator = LocalEndpointMotionGenerator()
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

