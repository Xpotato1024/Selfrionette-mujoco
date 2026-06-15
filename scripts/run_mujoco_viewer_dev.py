from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_VIEWER_PATH = "apps/mujoco-viewer/index.html"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_STEPS = 3
DEFAULT_PRESET = "sweep_x"


@dataclass(frozen=True, slots=True)
class SelectedLauncherConfig:
    bind_host: str
    port: int
    browser_host: str
    websocket_url: str
    viewer_url: str


def _host(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("host must not be empty")
    return value


def _port(value: str) -> int:
    parsed = int(value)
    if parsed < 1 or parsed > 65535:
        raise argparse.ArgumentTypeError("port must be in the range 1..65535")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("steps must be a positive integer")
    return parsed


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
        return True


def _find_free_port(host: str, start_port: int) -> int:
    for candidate in range(start_port, 65536):
        if _port_is_free(host, candidate):
            return candidate
    raise RuntimeError(f"no free ports found at or above {start_port}")


def resolve_browser_host(bind_host: str, public_host: str | None) -> str:
    if public_host:
        return public_host
    if bind_host in {"127.0.0.1", "localhost"}:
        return bind_host
    if bind_host == "0.0.0.0":
        return "127.0.0.1"
    return bind_host


def build_websocket_url(browser_host: str, port: int) -> str:
    return f"ws://{browser_host}:{port}"


def build_viewer_url(viewer_path: str, websocket_url: str) -> str:
    return f"{viewer_path}?websocketUrl={quote(websocket_url, safe=':/?=&')}"


def resolve_port(bind_host: str, requested_port: int, auto_port: bool) -> int:
    if _port_is_free(bind_host, requested_port):
        return requested_port
    if not auto_port:
        raise RuntimeError(f"port {requested_port} is already in use")
    return _find_free_port(bind_host, requested_port + 1)


def build_publisher_command(bind_host: str, port: int, steps: int) -> str:
    return (
        "uv run python scripts/run_replay_mujoco_websocket_publisher.py "
        f"--host {bind_host} --port {port} --steps {steps}"
    )


def build_dry_run_command(steps: int, preset: str) -> str:
    return f"uv run python scripts/run_replay_mujoco_dry_run.py --steps {steps} --preset {preset}"


def build_browser_build_command() -> str:
    return "cd apps/mujoco-viewer && npm run browser:build"


def build_selected_launcher_config(
    *,
    bind_host: str,
    requested_port: int,
    public_host: str | None,
    auto_port: bool,
    viewer_path: str,
) -> SelectedLauncherConfig:
    selected_port = resolve_port(bind_host, requested_port, auto_port)
    browser_host = resolve_browser_host(bind_host, public_host)
    websocket_url = build_websocket_url(browser_host, selected_port)
    viewer_url = build_viewer_url(viewer_path, websocket_url)
    return SelectedLauncherConfig(
        bind_host=bind_host,
        port=selected_port,
        browser_host=browser_host,
        websocket_url=websocket_url,
        viewer_url=viewer_url,
    )


def build_report_lines(
    *,
    config: SelectedLauncherConfig,
    steps: int,
    preset: str,
    no_browser_build: bool,
) -> list[str]:
    lines = [
        "Selected WebSocket publisher:",
        f"  bind:   {config.bind_host}:{config.port}",
        f"  browser host: {config.browser_host}",
        f"  websocket: {config.websocket_url}",
        "",
        "Open viewer:",
        f"  {config.viewer_url}",
        "",
        "Commands:",
        f"  {build_dry_run_command(steps, preset)}",
        f"  {build_publisher_command(config.bind_host, config.port, steps)}",
    ]
    if no_browser_build:
        lines.append("  cd apps/mujoco-viewer && npm run browser:build  # skipped with --no-browser-build")
    else:
        lines.append(f"  {build_browser_build_command()}")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the minimal MuJoCo viewer dev launcher for replay payload v0 smoke work.",
    )
    parser.add_argument("--host", type=_host, default=DEFAULT_HOST, help="WebSocket publisher bind host")
    parser.add_argument("--port", type=_port, default=DEFAULT_PORT, help="requested WebSocket publisher port")
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="select the next free port when the requested port is already in use",
    )
    parser.add_argument(
        "--public-host",
        type=_host,
        default=None,
        help="browser-visible host for LAN / Tailscale / public access",
    )
    parser.add_argument(
        "--viewer-path",
        default=DEFAULT_VIEWER_PATH,
        help="viewer page path that receives websocketUrl",
    )
    parser.add_argument("--steps", type=_positive_int, default=DEFAULT_STEPS, help="replay steps to describe")
    parser.add_argument("--preset", default=DEFAULT_PRESET, help="replay preset to describe")
    parser.add_argument(
        "--no-browser-build",
        action="store_true",
        help="do not run npm run browser:build; only print the command",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="print the selected URL and commands without running subprocesses",
    )
    return parser


def _run_browser_build() -> None:
    subprocess.run(["npm", "run", "browser:build"], cwd=ROOT / "apps/mujoco-viewer", check=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = build_selected_launcher_config(
        bind_host=args.host,
        requested_port=args.port,
        public_host=args.public_host,
        auto_port=args.auto_port,
        viewer_path=args.viewer_path,
    )

    for line in build_report_lines(
        config=config,
        steps=args.steps,
        preset=args.preset,
        no_browser_build=args.no_browser_build,
    ):
        print(line)

    if not args.print_only and not args.no_browser_build:
        print("Running browser build...")
        _run_browser_build()

    print("Press Ctrl+C only for the separate publisher command if you choose to start it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
