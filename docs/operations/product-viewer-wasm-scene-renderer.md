---
status: canonical
owner: architecture
last_verified: 2026-06-19
canonical_for:
  - product viewer wasm scene renderer operation
related:
  - docs/design/mujoco-wasm-scene-renderer-design.md
  - docs/research/mujoco-webviewer-options.md
  - docs/operations/wasm-qpos-sync-poc.md
---

# Product Viewer WASM Scene Renderer

`apps/mujoco-viewer` は `experiments/mujoco-wasm-viewer-poc` で成立した `@mujoco/mujoco` の WASM scene renderer を product viewer としてホストする。

## Boundary

- Python native MuJoCo backend / IK / FK / runtime が source of truth
- Browser WASM MuJoCo は visual renderer only
- browser 側で IK / FK / qpos recompute はしない
- browser 側で qpos correction はしない
- qpos は外部入力 payload か fixture から受け取り `data.qpos` に適用する

## Product viewer entrypoint

- `apps/mujoco-viewer/src/main.tsx`
- default renderer mode: `wasm-scene`
- model path: `/assets/mujoco/fast_arm/scene.xml`
- qpos fallback fixture: `/fixtures/fast_arm_sweep_x_qpos.json`

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

If port `5173` is already in use, Vite may fall back to `5174` or another free port.

Viewer URL:

```text
http://127.0.0.1:5175/apps/mujoco-viewer/
```

## Validation

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

Recommended repo-root checks:

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
git diff --check
```

## Browser smoke

- viewer loads
- WASM loads
- fast_arm scene loads
- home keyframe applies
- qpos sync path works, or qpos unavailable is clearly shown
- floor / axes / legend / colors appear
- old renderer is not on the default production path

## Known limitations

- fixture fallback is debug-oriented
- live WebSocket qpos availability depends on publisher payloads
- browser-side payload correction is intentionally absent
