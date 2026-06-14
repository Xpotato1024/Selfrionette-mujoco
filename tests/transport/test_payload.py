from __future__ import annotations

import json

from selfrionette.schemas import BodyTransform, MuJoCoState, SiteTransform
from selfrionette.transport import TRANSPORT_PAYLOAD_VERSION, mujoco_state_to_payload


def test_mujoco_state_to_payload_returns_json_compatible_payload() -> None:
    metadata = {"source": "test", "flags": ["a", "b"]}
    state = MuJoCoState(
        frame_index=1,
        time_s=0.5,
        qpos=(1.0, 2.0, 3.0),
        qvel=(4.0, 5.0),
        bodies=(
            BodyTransform(
                name="base_link",
                position_m=(0.0, 0.0, 0.0),
                quaternion_wxyz=(1.0, 0.0, 0.0, 0.0),
            ),
        ),
        sites=(
            SiteTransform(
                name="tip",
                position_m=(0.1, 0.2, 0.3),
                quaternion_wxyz=(1.0, 0.0, 0.0, 0.0),
            ),
        ),
        target_position_m=None,
        metadata=metadata,
    )

    payload = mujoco_state_to_payload(state)

    assert isinstance(payload, dict)
    assert payload["version"] == TRANSPORT_PAYLOAD_VERSION == 0
    assert payload["frame_index"] == 1
    assert payload["time_s"] == 0.5
    assert payload["qpos"] == [1.0, 2.0, 3.0]
    assert payload["qvel"] == [4.0, 5.0]
    assert isinstance(payload["qpos"], list)
    assert isinstance(payload["qvel"], list)
    assert isinstance(payload["bodies"], list)
    assert isinstance(payload["sites"], list)
    assert payload["bodies"] == [
        {
            "name": "base_link",
            "position_m": [0.0, 0.0, 0.0],
            "quaternion_wxyz": [1.0, 0.0, 0.0, 0.0],
        }
    ]
    assert payload["sites"] == [
        {
            "name": "tip",
            "position_m": [0.1, 0.2, 0.3],
            "quaternion_wxyz": [1.0, 0.0, 0.0, 0.0],
        }
    ]
    assert payload["target_position_m"] is None
    assert payload["metadata"] == metadata
    assert payload["metadata"] is not metadata

    json.dumps(payload)


def test_mujoco_state_to_payload_converts_target_position_tuple_to_list() -> None:
    state = MuJoCoState(
        frame_index=2,
        time_s=1.25,
        target_position_m=(0.4, 0.5, 0.6),
    )

    payload = mujoco_state_to_payload(state)

    assert payload["target_position_m"] == [0.4, 0.5, 0.6]
    assert isinstance(payload["target_position_m"], list)


def test_mujoco_state_to_payload_keeps_target_feedback_separate_from_metadata() -> None:
    state = MuJoCoState(
        frame_index=3,
        time_s=2.0,
        target_position_m=(1.0, 2.0, 3.0),
        metadata={
            "preset": "sweep_x",
            "target_delta_m": [0.1, 0.0, 0.0],
            "desired_endpoint_m": [1.1, 2.0, 3.0],
        },
    )

    payload = mujoco_state_to_payload(state)

    assert payload["target_position_m"] == [1.0, 2.0, 3.0]
    assert payload["metadata"]["preset"] == "sweep_x"
    assert payload["metadata"]["target_delta_m"] == [0.1, 0.0, 0.0]
    assert payload["metadata"]["desired_endpoint_m"] == [1.1, 2.0, 3.0]
