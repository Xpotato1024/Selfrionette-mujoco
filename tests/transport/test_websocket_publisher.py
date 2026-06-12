from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path

from selfrionette.schemas import BodyTransform, MuJoCoState, SiteTransform
from selfrionette.transport import WebSocketStatePublisher


class RecordingSender:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


def test_websocket_state_publisher_publish_is_awaitable() -> None:
    sender = RecordingSender()
    publisher = WebSocketStatePublisher(sender)
    state = MuJoCoState(frame_index=7, time_s=1.5)

    async def run_publish() -> None:
        await publisher.publish(state)

    asyncio.run(run_publish())

    assert sender.messages == [json.dumps({
        "version": 0,
        "frame_index": 7,
        "time_s": 1.5,
        "qpos": [],
        "qvel": [],
        "bodies": [],
        "sites": [],
        "target_position_m": None,
        "metadata": {},
    })]


def test_websocket_state_publisher_sends_json_payload_contract() -> None:
    sender = RecordingSender()
    publisher = WebSocketStatePublisher(sender)
    state = MuJoCoState(
        frame_index=11,
        time_s=2.25,
        qpos=(1.0,),
        qvel=(2.0, 3.0),
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
        target_position_m=(0.4, 0.5, 0.6),
        metadata={"origin": "test"},
    )

    asyncio.run(publisher.publish(state))

    assert len(sender.messages) == 1
    message = sender.messages[0]
    assert isinstance(message, str)

    payload = json.loads(message)
    assert payload["version"] == 0
    assert payload["frame_index"] == 11
    assert payload["time_s"] == 2.25
    assert payload["qpos"] == [1.0]
    assert payload["qvel"] == [2.0, 3.0]
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
    assert payload["target_position_m"] == [0.4, 0.5, 0.6]
    assert payload["metadata"] == {"origin": "test"}


def test_transport_websocket_module_does_not_import_forbidden_layers() -> None:
    path = Path(__file__).resolve().parents[2] / "src" / "selfrionette" / "transport" / "websocket.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    assert not any(name.startswith("selfrionette.mujoco_backend") for name in imports)
    assert not any(name.startswith("selfrionette.viewer") for name in imports)
    assert not any(name.startswith("selfrionette.kinematics") for name in imports)
    assert not any(name.startswith("selfrionette.motion") for name in imports)
