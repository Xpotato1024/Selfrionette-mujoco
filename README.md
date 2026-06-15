# Selfrionette-mujoco

`Selfrionette-mujoco` の正本は `docs/README.md` から辿る。
このルート README は、現在の起動導線と参照先を短くまとめた入口であり、
詳細な手順は各 canonical doc に置く。

## まず見るもの

- `docs/README.md`
- `docs/operations/r6-g-p1-startup-path-audit.md`
- `apps/mujoco-viewer/README.md`

## 現在の起動導線

- backend / dry-run: `uv run python scripts/run_replay_mujoco_dry_run.py --steps 1`
- WebSocket publisher: `uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3`
- live viewer smoke: `uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5`
- browser viewer: `apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766`

## 参照

- `docs/operations/runtime-dry-run.md`
- `docs/operations/websocket-publisher-runner.md`
- `docs/operations/live-viewer-smoke.md`
- `docs/operations/browser-visual-smoke.md`
- `docs/operations/r6-f-completion-audit.md`
