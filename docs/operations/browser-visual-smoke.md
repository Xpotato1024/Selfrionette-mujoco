---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - browser visual smoke
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/live-viewer-smoke.md
  - apps/mujoco-viewer/README.md
---

# Browser Visual Smoke

R6-D-P3 freezes the browser-visible smoke path for the viewer runtime and the
Three.js scene object mutation skeleton.

Visual smoke here means browser-visible runtime state plus Three.js scene
object mutation skeleton behavior. It does not mean a finalized
camera/renderer pipeline or a completed animation loop.

## Purpose

Confirm that payload v0 reaches the browser viewer, updates DOM status, keeps
the marker object registry alive, and mutates Three.js `Object3D.position`
from payload marker coordinates for the target marker, tip marker, arm
skeleton, fast_arm mesh scene, and error vector skeleton.

## Preconditions

- `main` is clean and up to date.
- `apps/mujoco-viewer` dependencies are installed with `npm ci`.
- The local Python smoke command is available.
- The browser viewer is opened during the smoke grace period.
- The viewer WebSocket client does not yet reconnect automatically.

## Command Sequence

1. Start the smoke command in terminal 1.
2. Read the WebSocket endpoint and Viewer URL printed by the CLI.
3. Open the Viewer URL in the browser during the grace period.
4. Confirm the viewer status becomes `WebSocket: open`.
5. Confirm the marker summary shows `payload v0`, the current frame, and the
   body / site counts.
6. Confirm the marker object count equals `bodies + sites + arm skeleton + target + error vector` when both endpoints are present.
7. Confirm later payload frames update marker object positions in the scene.

## Browser URL

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` is accepted as a compatibility alias.

## Expected Viewer Status

- Status text shows the WebSocket state separately from the marker summary.
- During setup, the status may show `WebSocket: connecting`.
- After the socket opens, the status shows `WebSocket: open`.
- If the browser is opened too early, the status can remain `error` because
  reconnect is not implemented yet.

## Expected DOM Attributes

The root viewer element exposes the smoke state through attributes:

- `data-websocket-status`
- `data-websocket-url`
- `data-payload-version`
- `data-frame-index`
- `data-marker-body-count`
- `data-marker-site-count`
- `data-marker-object-count`
- `data-arm-skeleton-status`
- `data-arm-skeleton-segment-count`
- `data-fast-arm-mesh-status`
- `data-fast-arm-mesh-count`

The status section also mirrors the latest frame summary text.

## Expected Marker Object Count

The root `data-marker-object-count` must equal the sum of:

- marker bodies
- marker sites
- arm skeleton segments
- optional target marker
- optional error vector

For the current payload v0 fixture, that means body + site + arm skeleton
when the target is absent and the canonical arm skeleton connection exists.
When both target and tip are present, the count becomes body + site + arm
skeleton + target + error vector.

## Expected Marker Position Behavior

- scene object registry は named body, site, target, error vector の `Object3D` instance を保持する。
- scene object registry は arm skeleton segment を read-only の `Object3D` connection として canonical payload body/site positions 間に保持する。
- fast_arm mesh scene は canonical STL assets を主 arm visual とし、mesh pose は payload body transforms からのみ作る。
- canonical `fast_arm` asset source は `assets/mujoco/fast_arm/` とする。
  asset contract は `docs/contracts/assets.md` と `assets/mujoco/fast_arm/README.md` を参照する。
  viewer は表示用 asset source として参照するだけで、STL / XML の geometry / scale / axis / origin / units / joint semantics は変更しない。
- Reused marker keys reuse the same object identity.
- 各 marker object の position は marker scene model に保存された payload marker coordinates に従う。
- arm skeleton segment は arm skeleton scene model に保存された payload body/site positions に従う。
- fast_arm mesh pose は、保守的な body mapping がある場合に限り、対応する payload body `position_m` と `quaternion_wxyz` に従う。
- error vector object は tip endpoint を position に持ち、target endpoint を `userData` に保持するので、pose を再計算せずに tip -> target 方向を表示できる。
- browser smoke が証明するのは payload coordinate の直接反映までであり、final coordinate mapping layer ではない。
- Phase D completion audit は `docs/operations/r6-d-completion-audit.md` に記録される。
- 次の handoff は IK / command integration skeleton work であり、rendered arm mesh でも完成済み IK path でもない。

## What Is Intentionally Not Visualized Yet

- camera, renderer, animation loop の挙動。
- labels / overlays を完成した visual design として扱うこと。
- IK / FK。
- `qpos` pose recompute。
- payload body/site positions 以外から arm skeleton を合成すること。
- `base_link_to_tip` line skeleton を final arm visual とすること。
- browser での MuJoCo model loading。
- WebSocket reconnect / retry hardening。

## Troubleshooting

- smoke server が ready になる前に browser を開いた場合は、grace period の後で refresh するか smoke command を再実行する。
- status が `WebSocket: open` に到達しない場合は、表示された endpoint と browser URL query string が一致しているか確認する。
- marker summary が更新されない場合は、grace period 中に viewer を開いたか、CLI がまだ frame を publish しているか確認する。
- object count が合わない場合は、表示中の payload frame に `target_position_m` があるか、canonical arm skeleton の body/site names があるかを確認する。

## Non-Goals

- No production server.
- No browser automation.
- No auth, TLS, or reverse proxy.
- No hardware, serial, or OSC access.
- No payload schema change.
- No transport schema change.
- No Three.js real scene mutation beyond the marker and fast_arm mesh skeletons.
- No `@types/three` or Rapier reintroduction.
