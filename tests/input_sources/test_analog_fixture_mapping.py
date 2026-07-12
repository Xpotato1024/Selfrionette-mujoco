from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from selfrionette.input_sources import (
    AnalogFixtureMappingConfig,
    AnalogFixtureSample,
    map_analog_fixture_sample,
    parse_analog_fixture_sample,
)
from selfrionette.schemas import MotionSampleRecord


FIXTURE = Path(__file__).parents[1] / "fixtures" / "analog_input_samples.json"


def config(**changes: object) -> AnalogFixtureMappingConfig:
    values = dict(
        centers=(512.0, 512.0, 512.0),
        half_ranges=(400.0, 200.0, 100.0),
        axis_order=(1, 2, 0),
        signs=(1, -1, 1),
        scales=(1.0, 0.5, 1.0),
        deadzone=0.1,
        speed_m_s=0.2,
        max_delta_m=0.01,
        control_frame="world",
    )
    values.update(changes)
    return AnalogFixtureMappingConfig(**values)  # type: ignore[arg-type]


def test_recorded_fixture_mapping_is_deterministic_and_preserves_p16_fields() -> None:
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))[0]
    sample = parse_analog_fixture_sample(value)
    first = map_analog_fixture_sample(sample, config())
    second = map_analog_fixture_sample(sample, config())

    assert first == second
    assert first.source_kind == "analog_fixture"
    assert first.source_active is True
    assert first.axis_values == pytest.approx((0.5, 0.5, 0.0))
    assert first.local_endpoint_velocity_m_s == pytest.approx(
        tuple(0.2 * component for component in first.axis_values)
    )
    assert first.control_frame == "world"
    assert first.zero_input is False
    assert first.stale_reason is None


def test_normalization_component_clamp_deadzone_order_sign_and_scale() -> None:
    intent = map_analog_fixture_sample(
        AnalogFixtureSample(1.0, (9999.0, 532.0, 412.0), True),
        config(),
    )
    # Raw channels normalize/clamp to (1, .1, -1), then reorder/sign/scale.
    # The .1 component is removed by the inclusive P16 deadzone.
    assert intent.deadzone_applied_axis_values == (0.0, 0.5, 1.0)
    assert intent.axis_values == pytest.approx((0.0, 1.0 / 5**0.5, 2.0 / 5**0.5))
    assert intent.norm_clamped is True


def test_active_zero_inactive_and_stale_remain_distinct() -> None:
    zero = map_analog_fixture_sample(AnalogFixtureSample(1.0, (512, 512, 512), True), config())
    inactive = map_analog_fixture_sample(AnalogFixtureSample(1.0, (700, 512, 512), False), config())
    stale = map_analog_fixture_sample(
        AnalogFixtureSample(1.0, (700, 512, 512), False, "recording_stale"), config()
    )
    assert (zero.source_active, zero.zero_input, zero.stale_reason) == (True, True, None)
    assert (inactive.source_active, inactive.zero_input, inactive.stale_reason) == (False, False, None)
    assert (stale.source_active, stale.zero_input, stale.stale_reason) == (
        False,
        False,
        "recording_stale",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"raw_values": None},
        {"raw_values": [1, 2]},
        {"raw_values": [True, 2, 3]},
        {"raw_values": ["1", 2, 3]},
        {"raw_values": [float("nan"), 2, 3]},
        {"raw_values": [float("inf"), 2, 3]},
        {"active": 1},
        {"timestamp_s": "1.0"},
    ],
)
def test_missing_extra_and_invalid_fixture_values_are_rejected(changes: dict[str, object]) -> None:
    value: dict[str, object] = {
        "timestamp_s": 1.0,
        "raw_values": [1, 2, 3],
        "active": True,
        "stale_reason": None,
    }
    if not changes:
        value.pop("raw_values")
    else:
        value.update(changes)
    with pytest.raises(ValueError):
        parse_analog_fixture_sample(value)


def test_config_is_immutable_and_rejects_ambiguous_mapping() -> None:
    mapping = config()
    with pytest.raises(FrozenInstanceError):
        mapping.deadzone = 0.2  # type: ignore[misc]
    with pytest.raises(ValueError):
        config(axis_order=(0, 0, 2))
    with pytest.raises(ValueError):
        config(signs=(1, 0, -1))
    with pytest.raises(ValueError):
        config(half_ranges=(1, 0, 1))


def test_p20_motion_sample_accepts_exact_p16_requested_fields() -> None:
    intent = map_analog_fixture_sample(AnalogFixtureSample(1.0, (712, 512, 512), True), config())
    record = MotionSampleRecord(
        experiment_id="experiment", session_id="session", participant_id="participant",
        configuration_id="configuration", trial_id="trial", sample_index=0,
        source_kind=intent.source_kind, source_timestamp_s=intent.source_timestamp_s,
        runtime_timestamp_s=1.1, source_active=intent.source_active,
        axis_values=intent.axis_values, zero_input=intent.zero_input,
        stale_reason=intent.stale_reason, requested_control_frame=intent.control_frame,
        local_endpoint_velocity_m_s=intent.local_endpoint_velocity_m_s,
        resolved_control_frame="mujoco_world", control_frame_resolution_status="world_passthrough",
        control_frame_resolution_reason=None,
        resolved_world_endpoint_velocity_m_s=intent.local_endpoint_velocity_m_s,
        endpoint_delta_requested_m=(0.001, 0.0, 0.0), endpoint_delta_achieved_m=(0.0, 0.0, 0.0),
        qpos_before_rad=(0.0,), qpos_after_rad=(0.0,), candidate_qpos_rad=(0.0,),
        measured_tip_position_before_m=None, measured_tip_position_after_m=None, actual_tip_delta_m=None,
        motion_status="held", motion_rejection_reason="fixture_test_hold",
        target_rejected=False, target_rejection_reason=None,
        endpoint_progress_status="measurement_unavailable",
        endpoint_progress_measurement_available=False,
        measurement_unavailable_reason="fixture_test_no_backend",
    )
    assert record.source_kind == intent.source_kind
    assert record.axis_values == intent.axis_values
    assert record.local_endpoint_velocity_m_s == intent.local_endpoint_velocity_m_s
