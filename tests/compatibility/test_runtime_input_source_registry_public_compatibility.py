"""Public low-level registry compatibility retained until C4."""

from __future__ import annotations

import pytest

from selfrionette.input_sources import (
    INPUT_SOURCE_REGISTRY,
    SUPPORTED_INPUT_SOURCE_NAMES,
    get_input_source_descriptor,
)
from selfrionette.schemas import RawInputFrame


def test_runtime_input_source_registry_exposes_supported_sources() -> None:
    assert SUPPORTED_INPUT_SOURCE_NAMES == ("programmed_target", "replay", "noop", "viewer")
    assert tuple(INPUT_SOURCE_REGISTRY) == SUPPORTED_INPUT_SOURCE_NAMES


@pytest.mark.parametrize(
    ("source_name", "expected_contract_key", "expected_contract_value"),
    [
        ("programmed_target", "trajectory_name", "sweep_x"),
        ("replay", "preset", "r6-h-p5-default"),
        ("noop", "source_kind", "noop"),
        ("viewer", "source_kind", "viewer"),
    ],
)
def test_runtime_input_source_registry_initial_metadata_contract(
    source_name: str,
    expected_contract_key: str,
    expected_contract_value: object,
) -> None:
    descriptor = get_input_source_descriptor(source_name)

    assert descriptor.name == source_name
    assert expected_contract_key in descriptor.initial_metadata
    assert descriptor.initial_metadata[expected_contract_key] == expected_contract_value
    assert callable(descriptor.build_frames)

    if source_name == "viewer":
        assert descriptor.initial_metadata["source_active"] is False
        assert descriptor.initial_metadata["command_age_ms"] == 0
        assert descriptor.initial_metadata["stale_reason"] == "no_control_message_received"
        assert descriptor.initial_metadata["desired_endpoint_m"] == descriptor.initial_metadata["target_position_m"]


def test_low_level_registry_preserves_programmed_target_initial_position() -> None:
    descriptor = get_input_source_descriptor("programmed_target")

    frame = descriptor.build_frames(
        steps=1,
        initial_position_m=(0.1, 0.2, 0.3),
    )[0]

    assert frame.metadata["target_position_m"] == (0.1, 0.2, 0.3)
    assert frame.metadata["desired_endpoint_m"] == (0.1, 0.2, 0.3)


def test_low_level_registry_preserves_replay_frames_and_metadata() -> None:
    descriptor = get_input_source_descriptor("replay")
    custom_frame = RawInputFrame(source="custom", timestamp_s=2.5, values=(1.0,))

    assert descriptor.build_frames(frames=(custom_frame,)) == (custom_frame,)
    assert descriptor.build_frames(metadata={"custom": "value"})[0].metadata == {
        "custom": "value"
    }


def test_low_level_registry_preserves_noop_and_viewer_metadata() -> None:
    noop_metadata = {"custom": "noop"}
    viewer_metadata = {"custom": "viewer", "source_active": False}

    noop_frame = get_input_source_descriptor("noop").build_frames(
        metadata=noop_metadata
    )[0]
    viewer_frame = get_input_source_descriptor("viewer").build_frames(
        metadata=viewer_metadata
    )[0]

    assert noop_frame.metadata == noop_metadata
    assert viewer_frame.metadata == viewer_metadata


def test_runtime_input_source_registry_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="unsupported input source"):
        get_input_source_descriptor("unknown")
