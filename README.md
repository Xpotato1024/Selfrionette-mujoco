# Selfrionette-mujoco

`Selfrionette-mujoco` の docs 正本は `docs/README.md` です。
このルート README は、backend / dry-run / WebSocket publisher / Web viewer / browser 接続へ最短で辿る入口だけをまとめます。

## まず読むもの

- [docs/README.md](docs/README.md)
- [docs/operations/backend-viewer-startup.md](docs/operations/backend-viewer-startup.md)
- [docs/operations/websocket-host-port-contract.md](docs/operations/websocket-host-port-contract.md)
- [docs/operations/r6-g-p1-startup-path-audit.md](docs/operations/r6-g-p1-startup-path-audit.md)
- [docs/operations/r6-g-p3-startup-script-gap-audit.md](docs/operations/r6-g-p3-startup-script-gap-audit.md)
- [apps/mujoco-viewer/README.md](apps/mujoco-viewer/README.md)

## セットアップ

- Python 側は `uv run ...` を使います。
- viewer 側は `apps/mujoco-viewer` 配下で `npm ci` を実行します。
- browser viewer 用の build は `npm run browser:build` です。
- `npm run typecheck` と `npm run build` は TypeScript の静的検証です。
- `npm test` は viewer runtime / WebSocket skeleton のテストを実行します。

## 起動導線

### backend / dry-run

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
```

dry-run は NDJSON payload / backend path の確認用です。WebSocket server は起動せず、browser viewer にも直接接続しません。

### WebSocket publisher

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
```

browser viewer に payload v0 を流す local/dev publisher です。標準的な loopback は `127.0.0.1:8766` です。

### Web viewer

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

browser で開く URL 例:

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

互換 alias:

```text
apps/mujoco-viewer/index.html?ws=ws://127.0.0.1:8766
```

browser page URL と WebSocket URL は別です。viewer は `websocketUrl` を優先し、`ws` は互換 alias です。query がない場合は自動接続しません。

### live viewer smoke

```bash
uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

browser / viewer smoke の補助導線です。CLI は browser URL と WebSocket endpoint を区別して出力します。R6-F visual elements の観測入口として使います。

## URL と host の注意

- `127.0.0.1` / `localhost` は同じ machine 上の browser 向け loopback です。
- `0.0.0.0` は server 側の bind address です。browser URL の host としては通常使いません。
- LAN / Tailscale / public host から開くときは、browser から見える host を URL に使います。
- bind host と browser から見える host は別です。
- viewer page URL と WebSocket endpoint URL は別です。
- 詳細な host / port / URL contract は [docs/operations/websocket-host-port-contract.md](docs/operations/websocket-host-port-contract.md) を参照してください。

## 参照

- [docs/operations/runtime-dry-run.md](docs/operations/runtime-dry-run.md)
- [docs/operations/websocket-publisher-runner.md](docs/operations/websocket-publisher-runner.md)
- [docs/operations/live-viewer-smoke.md](docs/operations/live-viewer-smoke.md)
- [docs/operations/browser-visual-smoke.md](docs/operations/browser-visual-smoke.md)
- [docs/operations/r6-g-p3-startup-script-gap-audit.md](docs/operations/r6-g-p3-startup-script-gap-audit.md)
- [docs/operations/r6-f-completion-audit.md](docs/operations/r6-f-completion-audit.md)
