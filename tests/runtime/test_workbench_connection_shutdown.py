"""close handshake前の送信待ちも期限内に回収し、IO threadを残さない。"""
import asyncio
from contextlib import asynccontextmanager
from threading import Event, get_ident

import pytest

from xpotato_sim.runtime.application.workbench_projection import AsyncWorkerConnection


@pytest.mark.parametrize("stalled", [False, True])
def test_connection_close_bounds_complete_handshake_and_keeps_io_owner(monkeypatch, stalled):
    holder = {}

    class Connection:
        def __init__(self):
            self.loop = asyncio.get_running_loop()
            self.owner = get_ident()
            self.lost = asyncio.Event()
            self.cancelled = Event()
            self.aborts = 0
            self.transport = self

        def __aiter__(self):
            return self

        async def __anext__(self):
            await self.lost.wait()
            raise StopAsyncIteration

        async def close(self):
            # 実socketで再現した、drain中には内部close_timeoutが効かない状態を固定する。
            if not stalled:
                self.lost.set()
            try:
                await self.lost.wait()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise

        def abort(self):
            assert asyncio.get_running_loop() is self.loop
            assert get_ident() == self.owner
            self.aborts += 1
            self.lost.set()

        async def wait_closed(self):
            await self.lost.wait()

    @asynccontextmanager
    async def connect(*args, **kwargs):
        connection = holder["connection"] = Connection()
        try:
            yield connection
        finally:
            await connection.close()

    monkeypatch.setattr("websockets.asyncio.client.connect", connect)
    wire = AsyncWorkerConnection("ws://software-fixture.invalid", proxy=None)
    connection = holder["connection"]
    try:
        wire.close()
        assert not wire.thread.is_alive()
        assert wire.error is None
        assert connection.aborts == int(stalled)
        assert connection.cancelled.is_set() is stalled
        wire.close()
        assert connection.aborts == int(stalled)
    finally:
        # 修正前の失敗でも、故障注入したthreadを後続testへ持ち越さない。
        if wire.thread.is_alive():
            wire.loop.call_soon_threadsafe(connection.abort)
            wire.thread.join(3)
        assert not wire.thread.is_alive()
