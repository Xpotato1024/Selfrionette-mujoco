"""位置増分と速度積分を独立した数式oracleで区別する。"""
from __future__ import annotations

import pytest

from selfrionette.motion import LocalEndpointMotionGenerator
from selfrionette.schemas import InputIntent


class LinearKinematics:
    """4 joint中3軸だけが単位Jacobianを持つ、非実機の解析用model。"""

    def forward(self, qpos_rad):
        """解析用の単位Jacobianに対応する位置を返す。"""
        return tuple(qpos_rad[:3])


def _generator():
    """実機と無関係な線形modelで既存局所solverを組み立てる。"""
    generator = LocalEndpointMotionGenerator(endpoint_kinematics=LinearKinematics(), damping=0.001)
    generator.set_current_qpos_rad((0.0, 0.0, 0.0, 0.0))
    return generator


def _delta_intent(delta):
    """位置増分であることを明示したworld-frame入力を作る。"""
    return InputIntent(source="synthetic", timestamp_s=0.0, values=(1.0, 0.0, 0.0), metadata={
        "intent_kind": "local_endpoint_delta", "control_frame": "world", "endpoint_delta_m": delta,
    })


@pytest.mark.parametrize("dt", (0.01, 0.02, 0.1))
def test_delta_is_per_sample_not_multiplied_by_dt(dt):
    """cadenceを変えても同じsample増分となることを確認する。"""
    delta = (0.001, -0.002, 0.003)
    command = _generator().update(_delta_intent(delta), dt)
    # J=Iなので J^T (JJ^T + damping I)^-1 delta = delta / 1.001。
    assert command.joint.joint_angles_rad == pytest.approx((*[v / 1.001 for v in delta], 0.0), abs=1e-12)
    assert command.metadata["endpoint_delta_requested_m"] == delta
    assert command.metadata["motion_input_semantics"] == "endpoint_delta_per_sample/v1"
    assert "endpoint_velocity_m_s" not in command.metadata
    assert "axis_values" not in command.metadata


def test_existing_velocity_semantics_still_integrate_dt():
    """既存velocity入力には従来どおりdtが掛かることを確認する。"""
    intent = InputIntent(source="synthetic", timestamp_s=0.0, metadata={
        "control_frame": "world", "endpoint_velocity_m_s": (0.01, 0.0, 0.0),
    })
    command = _generator().update(intent, 0.02)
    assert command.metadata["endpoint_delta_requested_m"] == pytest.approx((0.0002, 0.0, 0.0))
    assert command.joint.joint_angles_rad[0] == pytest.approx(0.0002 / 1.001)


@pytest.mark.parametrize("delta", (None, (1.0, 2.0), (float("nan"), 0.0, 0.0)))
def test_invalid_delta_is_not_replaced_by_zero(delta):
    """欠落・次元違い・非finite値を拒否する。"""
    with pytest.raises(ValueError):
        _generator().update(_delta_intent(delta), 0.02)


def test_zero_delta_does_not_move_even_with_nonzero_raw_values():
    """delta経路ではraw channelsを速度として使用しない。"""
    command = _generator().update(_delta_intent((0.0, 0.0, 0.0)), 0.02)
    assert command.joint.joint_angles_rad == (0.0, 0.0, 0.0, 0.0)
