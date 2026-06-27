from __future__ import annotations

from selfrionette.runtime import FastArmEndpointMotionSanityResult, run_fast_arm_endpoint_motion_sanity
from selfrionette.runtime import endpoint_motion_sanity as endpoint_motion_sanity_module


def test_run_fast_arm_endpoint_motion_sanity_returns_axiswise_results() -> None:
    results = run_fast_arm_endpoint_motion_sanity()

    assert isinstance(results, tuple)
    assert len(results) == 6
    assert [result.command_label for result in results] == ["+x", "-x", "+y", "-y", "+z", "-z"]

    for result in results:
        assert isinstance(result, FastArmEndpointMotionSanityResult)
        assert result.axis in {"x", "y", "z"}
        assert result.sign in {-1, 1}
        assert result.status in {"pass", "rejected", "limitation", "unavailable"}
        assert result.reason
        assert len(result.commanded_delta_m) == 3
        assert len(result.command_direction_m) == 3
        assert len(result.qpos_before) == 4
        assert len(result.qpos_after) == 4
        assert result.desired_endpoint_m == result.target_position_m
        assert result.initial_tip_position_m is not None
        assert result.final_tip_position_m is not None
        assert result.actual_delta_m is not None
        assert result.direction_dot is not None
        assert result.desired_endpoint_source == 'MotionCommand.metadata["desired_endpoint_m"]'

    x_plus = results[0]
    z_plus = results[4]
    z_minus = results[5]
    assert x_plus.status in {"pass", "limitation", "rejected"}
    assert z_plus.status in {"pass", "limitation", "rejected"}
    assert z_minus.status in {"pass", "limitation", "rejected"}


def test_run_fast_arm_endpoint_motion_sanity_converts_pipeline_build_failures_into_unavailable_results(monkeypatch) -> None:
    def _raise_build_failure(*args, **kwargs):  # noqa: ANN001, ANN002
        raise RuntimeError("boom")

    monkeypatch.setattr(endpoint_motion_sanity_module, "build_concrete_mujoco_pipeline", _raise_build_failure)

    results = run_fast_arm_endpoint_motion_sanity()

    assert len(results) == 6
    for result in results:
        assert result.status == "unavailable"
        assert result.reason == "backend_exception"
        assert result.error_message == "boom"
        assert result.initial_tip_position_m is None
        assert result.final_tip_position_m is None
        assert result.actual_delta_m is None
        assert result.qpos_before == ()
        assert result.qpos_after == ()
