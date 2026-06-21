from __future__ import annotations

import json
from dataclasses import replace

from selfrionette.input_sources import build_keyboard_motion_command
from selfrionette.runtime import run_offline_input_runtime_stepping_smoke


def test_r7_b_input_driven_payload_smoke_roundtrips_keyboard_payload_and_feedback_target() -> None:
    command = build_keyboard_motion_command(
        ("KeyD",),
        current_tip_position_m=(0.1, 0.0, 0.3),
        timestamp_s=0.5,
    )
    command = replace(
        command,
        metadata={
            **command.metadata,
            "target_position_m": (0.24, 0.5, 0.75),
        },
    )

    result = run_offline_input_runtime_stepping_smoke(command, initial_qpos=(0.0, 0.0, 0.0, 0.0))

    assert isinstance(result.payload, dict)
    assert result.payload["metadata"]["desired_endpoint_m"] == (0.11, 0.0, 0.3)
    assert result.payload["metadata"]["target_position_m"] == (0.24, 0.5, 0.75)
    assert result.payload["target_position_m"] == [0.24, 0.5, 0.75]

    roundtrip_payload = json.loads(json.dumps(result.payload))
    assert roundtrip_payload["metadata"]["desired_endpoint_m"] == [0.11, 0.0, 0.3]
    assert roundtrip_payload["metadata"]["target_position_m"] == [0.24, 0.5, 0.75]
    assert roundtrip_payload["target_position_m"] == [0.24, 0.5, 0.75]

    if result.endpoint_evaluation is None:
        assert "endpoint_evaluation" not in result.payload
        assert "endpoint_evaluation" not in roundtrip_payload
    else:
        assert result.payload["endpoint_evaluation"] == result.endpoint_evaluation
        assert roundtrip_payload["endpoint_evaluation"] == result.endpoint_evaluation
        assert result.payload["endpoint_evaluation"]["desired_endpoint_m"] == [0.11, 0.0, 0.3]

