from __future__ import annotations

from selfrionette.plugins.robots.fast_arm.adapter.profile import FAST_ARM_ROBOT_PROFILE
from selfrionette.plugins.mappings.replay_mapping import (
    REPLAY_CONTROL_MAPPING_PLUGIN,
)
from selfrionette.plugins.robots.catalog import resolve_robot_bundle

import asyncio
import json

from selfrionette.runtime.composition.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.runtime.experiment.composition import resolve_command_execution
from selfrionette.transport import WebSocketStatePublisher


class RecordingSender:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


def test_replay_pipeline_publishes_payload_v0_json_in_memory() -> None:
    sender = RecordingSender()
    pipeline = build_replay_mujoco_pipeline(
        publisher=WebSocketStatePublisher(sender),
        model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset,
        resolved_command_execution=resolve_command_execution(
            REPLAY_CONTROL_MAPPING_PLUGIN,
            resolve_robot_bundle("fast_arm"),
            None,
        ),
    )

    state = asyncio.run(pipeline.run_once())

    assert len(sender.messages) == 1
    assert sender.messages[0] == json.dumps(json.loads(sender.messages[0]))

    payload = json.loads(sender.messages[0])
    assert payload["version"] == 0
    assert payload["frame_index"] == state.frame_index
    assert payload["time_s"] == state.time_s
    assert "qpos" in payload
    assert "qvel" in payload
    assert "bodies" in payload
    assert "sites" in payload
    assert any(site["name"] == "tip" for site in payload["sites"])
    assert any(body["name"] == "base_link" for body in payload["bodies"])
