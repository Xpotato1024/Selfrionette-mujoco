# mujoco-viewer

## Endpoint presentation boundary

The input overlay parses existing payload-v0 endpoint metadata into typed
requested, resolved, predicted, and measured groups. Missing or malformed
values remain unavailable rather than becoming zero. Held, rejected, stale,
resolution-unavailable, and measurement-unavailable are independent states.
This is a read-only consumer: it defines no schema and performs no FK or IK.

`apps/mujoco-viewer` は MuJoCo WASM scene renderer を rendering-only でホストする。

## 正本

- [docs/operations/backend-viewer-startup.md](../../docs/operations/backend-viewer-startup.md)
- [docs/operations/r7-c-viewer-fixture-demo-procedure.md](../../docs/operations/r7-c-viewer-fixture-demo-procedure.md)
- [docs/operations/websocket-host-port-contract.md](../../docs/operations/websocket-host-port-contract.md)

## 役割

- browser-side FK / IK / qpos recompute: しない
- MuJoCo model loading: browser-side source of truth ではない
- `public/fixtures/fast_arm_sweep_x_qpos.json`: canonical product-owned debug fixture
- endpoint evaluation overlay: read-only diagnostic
- input overlay: read-only source state plus target rejection / hold metadata

## Fixture ownership and regeneration

The canonical fixture is generated from the native MuJoCo replay path and is
owned by this product viewer. From the repository root, regenerate it with:

```powershell
uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30
```

The default output is `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json`.
Its contract is `schema_version: 1`, model
`assets/mujoco/fast_arm/scene.xml`, preset `sweep_x`, `qpos_length: 4`, and
30 frames. The current regenerated content is SHA-256
`A30FD0A303506C7807BA2E687411FACDF28BA2BC2AE9AC8F909B9C59997FEE36`.
The viewer test parses the tracked file, validates its dimension and finite
qpos values, and therefore also acts as the regeneration check.

## 参照用の検証コマンド

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

リポジトリ root からの差分確認も行う。

```powershell
cd <repository root>
git diff --check
```

## Live Viewer URL

```powershell
cd apps\mujoco-viewer
npm run dev -- --host 127.0.0.1 --port 5173
```

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

`/apps/mujoco-viewer/` alone is the disconnected viewer. The canonical live
viewer URL is the same route with `?websocketUrl=ws://127.0.0.1:8766`.
