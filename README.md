# Selfrionette-mujoco

`Selfrionette-mujoco` の docs 正本は `docs/README.md` です。
このルート README は、backend / dry-run / WebSocket publisher / Web viewer / browser 接続へ最短で辿る入口だけをまとめます。

## まず読むもの

- [docs/README.md](docs/README.md)
- [docs/architecture/dependency-boundaries.md](docs/architecture/dependency-boundaries.md)
- [docs/architecture/runtime-composition.md](docs/architecture/runtime-composition.md)
- [docs/contracts/experiment-plugin-composition.md](docs/contracts/experiment-plugin-composition.md)
- [docs/operations/backend-viewer-startup.md](docs/operations/backend-viewer-startup.md)
- [docs/operations/websocket-host-port-contract.md](docs/operations/websocket-host-port-contract.md)
- [docs/operations/runtime-to-viewer-e2e-smoke.md](docs/operations/runtime-to-viewer-e2e-smoke.md)
- [apps/mujoco-viewer/README.md](apps/mujoco-viewer/README.md)

## セットアップ

- Python 側は `uv run ...` を使います。
- root projectはuv workspaceで独立distribution `fast_arm_core`を通常dependencyとして解決します。
  `uv sync --frozen --group dev`はrootとcoreをeditableに同期し、配布確認ではcore wheelとroot wheelを別々にbuild/installします。
- viewer 側は `apps/mujoco-viewer` 配下で `npm ci` を実行します。
- browser viewer 用の build は `npm run browser:build` です。
- `npm run typecheck` と `npm run build` は TypeScript の静的検証です。
- `npm test` は viewer runtime / WebSocket skeleton のテストを実行します。

独立wheelの確認:

```bash
uv build --wheel src/selfrionette/plugins/robots/fast_arm/core --out-dir dist
uv build --wheel --out-dir dist
```

root sdist/wheelは`fast_arm_core` sourceを内包せず、install時にcore wheelを通常dependencyとして要求します。
rootのpackage dataはadapter resourceだけを明示収集し、物理mount pointは`MANIFEST.in`でもpruneします。

## 起動導線

### backend / dry-run

```bash
uv run selfrionette replay --robot fast_arm --steps 1
uv run selfrionette replay --robot fast_arm --steps 3 --preset sweep_x
```

dry-run は NDJSON payload / backend path の確認用です。WebSocket server は起動せず、browser viewer にも直接接続しません。

### WebSocket publisher

```bash
uv run selfrionette viewer --robot fast_arm --host 127.0.0.1 --port 8766 --steps 3
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
uv run python scripts/viewer/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

browser / viewer smoke の補助導線です。CLI は browser URL と WebSocket endpoint を区別して出力します。

## URL と host の注意

- `127.0.0.1` / `localhost` は同じ machine 上の browser 向け loopback です。
- `0.0.0.0` は server 側の bind address です。browser URL の host としては通常使いません。
- LAN / Tailscale / public host から開くときは、browser から見える host を URL に使います。
- bind host と browser から見える host は別です。
- viewer page URL と WebSocket endpoint URL は別です。
- 詳細な host / port / URL contract は [docs/operations/websocket-host-port-contract.md](docs/operations/websocket-host-port-contract.md) を参照してください。

## 参照

- [docs/operations/runtime-dry-run.md](docs/operations/runtime-dry-run.md)
- [docs/operations/unified-cli.md](docs/operations/unified-cli.md)
- [docs/operations/websocket-publisher-runner.md](docs/operations/websocket-publisher-runner.md)
- [docs/operations/live-viewer-smoke.md](docs/operations/live-viewer-smoke.md)
- [docs/operations/runtime-to-viewer-e2e-smoke.md](docs/operations/runtime-to-viewer-e2e-smoke.md)
- [docs/operations/browser-visual-smoke.md](docs/operations/browser-visual-smoke.md)
- [docs/reports/audits/r6-g-p3-startup-script-gap-audit.md](docs/reports/audits/r6-g-p3-startup-script-gap-audit.md)
- [docs/reports/audits/r6-f-completion-audit.md](docs/reports/audits/r6-f-completion-audit.md)
