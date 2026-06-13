from __future__ import annotations

import asyncio
import json
import socket

from websockets.asyncio.client import connect

from selfrionette.schemas import BodyTransform, MuJoCoState, SiteTransform
from selfrionette.transport import WebSocketPublisherServer, WebSocketStatePublisher


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _receive_single_payload() -> dict[str, object]:
    port = _find_free_port()

    async with WebSocketPublisherServer(host="127.0.0.1", port=port) as server:
        publisher = WebSocketStatePublisher(server)
        state = MuJoCoState(
            frame_index=1,
            time_s=0.25,
            qpos=(1.0, 2.0),
            qvel=(3.0, 4.0),
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
        )

        async with connect(f"ws://127.0.0.1:{port}") as websocket:
            await publisher.publish(state)
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            return json.loads(message)


def test_websocket_publisher_server_delivers_payload_v0_to_connected_client() -> None:
    payload = asyncio.run(_receive_single_payload())

    assert payload["version"] == 0
    assert payload["frame_index"] == 1
    assert payload["qpos"] == [1.0, 2.0]
    assert payload["qvel"] == [3.0, 4.0]
    assert any(body["name"] == "base_link" for body in payload["bodies"])
    assert any(site["name"] == "tip" for site in payload["sites"])


def test_websocket_publisher_server_stop_is_clean() -> None:
    port = _find_free_port()

    async def run() -> None:
        server = WebSocketPublisherServer(host="127.0.0.1", port=port)
        await server.start()
        assert server.is_running
        await server.stop()
        assert not server.is_running

    asyncio.run(run())


def test_websocket_publisher_server_rejects_invalid_configuration() -> None:
    for kwargs in (
        {"host": "", "port": 8766},
        {"host": "127.0.0.1", "port": 0},
        {"host": "127.0.0.1", "port": 70000},
    ):
        try:
            WebSocketPublisherServer(**kwargs)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {kwargs}")
