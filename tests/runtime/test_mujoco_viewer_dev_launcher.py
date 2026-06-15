from __future__ import annotations

import contextlib
import importlib.util
import io
import socket
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_mujoco_viewer_dev.py"
SPEC = importlib.util.spec_from_file_location("run_mujoco_viewer_dev", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_default_browser_url_uses_loopback_host() -> None:
    config = MODULE.build_selected_launcher_config(
        bind_host="127.0.0.1",
        requested_port=8766,
        public_host=None,
        auto_port=False,
        viewer_path="apps/mujoco-viewer/index.html",
    )

    assert config.websocket_url == "ws://127.0.0.1:8766"
    assert config.viewer_url == "apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766"


def test_public_host_is_used_for_browser_visible_url() -> None:
    config = MODULE.build_selected_launcher_config(
        bind_host="0.0.0.0",
        requested_port=8766,
        public_host="100.110.169.96",
        auto_port=False,
        viewer_path="apps/mujoco-viewer/index.html",
    )

    assert config.bind_host == "0.0.0.0"
    assert config.websocket_url == "ws://100.110.169.96:8766"
    assert "0.0.0.0" not in config.viewer_url


def test_bind_host_0_0_0_0_does_not_leak_into_viewer_url() -> None:
    config = MODULE.build_selected_launcher_config(
        bind_host="0.0.0.0",
        requested_port=8766,
        public_host=None,
        auto_port=False,
        viewer_path="apps/mujoco-viewer/index.html",
    )

    assert config.websocket_url == "ws://127.0.0.1:8766"
    assert config.viewer_url == "apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766"
    assert "0.0.0.0" not in config.viewer_url


def test_auto_port_selects_the_next_free_port() -> None:
    requested_port = _free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", requested_port))
        sock.listen(1)
        selected_port = MODULE.resolve_port("127.0.0.1", requested_port, auto_port=True)

    assert selected_port != requested_port
    assert selected_port > requested_port


def test_print_only_does_not_run_browser_build() -> None:
    with patch.object(MODULE, "_run_browser_build") as run_browser_build:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = MODULE.main(
                [
                    "--print-only",
                    "--no-browser-build",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8766",
                    "--steps",
                    "3",
                    "--preset",
                    "sweep_x",
                ]
            )

    assert exit_code == 0
    run_browser_build.assert_not_called()
    output = stdout.getvalue()
    assert "ws://127.0.0.1:8766" in output
    assert "apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766" in output
    assert "scripts/run_replay_mujoco_websocket_publisher.py" in output
    assert "scripts/run_replay_mujoco_dry_run.py" in output
