---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - product viewer wasm scene renderer operation
related:
  - docs/design/mujoco-wasm-scene-renderer-design.md
  - docs/research/mujoco-webviewer-options.md
  - docs/operations/wasm-qpos-sync-poc.md
---

# Product Viewer WASM Scene Renderer

`apps/mujoco-viewer` は、`experiments/mujoco-wasm-viewer-poc` で成立し #185 で昇格した `@mujoco/mujoco` WASM scene renderer の現在のproduction ownerです。実行可能なPoCは #385 で退役し、現行のrenderer・tests・fixture・operator pathはこのproduct viewer側に一本化されています。

## Boundary

- Python native MuJoCo backend / IK / FK / runtime が source of truth
- Browser WASM MuJoCo は visual renderer only
- browser 側で IK / FK / qpos recompute はしない
- browser 側で qpos correction はしない
- qpos は runtime payload を優先し、未接続時は compiled MuJoCo model default qpos を startup pose として使う

## Product viewer entrypoint

- `apps/mujoco-viewer/src/main.tsx`
- default renderer mode: `wasm-scene`
- model path: `/assets/mujoco/fast_arm/scene.xml`

## Startup pose source

- `home` keyframe: canonical fast_arm startup qpos。pre-payload表示はMJCFからこのqposを読む
- compiled MuJoCo model default qpos: historical fallbackではなく、startup sourceには使わない
- fixture qpos: default startup path では使わない
- runtime qpos: WebSocket payload が来たら `data.qpos` に適用する

## Canonical qpos fixture

- owner: `apps/mujoco-viewer/`
- path: `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json`
- schema owner: `apps/mujoco-viewer/src/wasm-scene/qposFrameTypes.ts`
- regeneration: `uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30`
- fixture playback is debug/validation only; startup still uses the named `home` keyframe

## Old renderer handling

- decision: deleted
- default production route: no longer imports the old Three.js hand-built renderer stack
- old viewer-specific renderer / runtime / view model / tests were removed to avoid code bloat

## Run

```powershell
cd apps\mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Vite dev server は起動後にブラウザを自動で開き、`/apps/mujoco-viewer/` を表示する。
実際の port は Vite の表示に従う。`5175` は手元環境での一例。
ポートが使用中なら Vite が次の空きポートを選ぶ。

## Validation

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

```powershell
cd <repository root>
git diff --check
```

## Browser smoke

- viewer loads
- WASM loads
- fast_arm scene loads
- initial pose source is explicit
- qpos sync path works, or qpos unavailable is clearly shown
- floor / axes / legend / colors appear
- old renderer is not on the default production path

## Known limitations

- fixture qpos は debug 用の参照としてのみ扱い、startup では自動適用しない
- live WebSocket qpos availability depends on publisher payloads
- browser-side payload correction is intentionally absent
