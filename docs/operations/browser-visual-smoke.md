---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - browser visual smoke
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/r6-f-p5-old-web-view-reference-audit.md
  - docs/operations/r6-f-completion-audit.md
  - apps/mujoco-viewer/README.md
---

# Browser Visual Smoke

R6-D-P3 は、browser で確認する smoke path を固定する。Three.js scene object
mutation skeleton の動作を、runtime 状態とあわせて人手で確認する。

## Purpose

payload v0 が browser viewer に届き、DOM status を更新し、marker object
registry を維持し、payload marker coordinates から Three.js
`Object3D.position` を更新することを確認する。対象は target marker, tip
marker, arm skeleton, fast_arm mesh scene, error vector skeleton である。

## Preconditions

- `main` が clean で最新である。
- `apps/mujoco-viewer` の依存関係が `npm ci` で入っている。
- local の Python smoke command が利用できる。
- browser viewer は smoke の grace period 中に開く。
- viewer WebSocket client はまだ自動 reconnect しない。

## Command Sequence

1. terminal 1 で smoke command を開始する。
2. CLI が表示する WebSocket endpoint と Viewer URL を読む。
3. grace period 中に Viewer URL を browser で開く。
4. viewer status が `WebSocket: open` になることを確認する。
5. marker summary に `payload v0`, current frame, body / site count が表示される
   ことを確認する。
6. 両 endpoint がある場合、marker object count が
   `bodies + sites + arm skeleton + target + error vector` と一致することを
   確認する。
7. 後続の payload frame で marker object position が scene 内で更新される
   ことを確認する。

## Browser URL

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` は互換 alias として受け付ける。
host / port / public host contract は
`docs/operations/websocket-host-port-contract.md` に固定する。

## Expected Viewer Status

- status text は marker summary と分けて `WebSocket` state を表示する。
- setup 中は `WebSocket: connecting` になりうる。
- socket が開くと `WebSocket: open` になる。
- browser を早く開きすぎた場合、reconnect が未実装のため `error` のまま
  になることがある。

## Expected DOM Attributes

root viewer element は smoke state を attributes で公開する。

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
- `data-dof-ring-status`
- `data-dof-ring-descriptor-count`
- `data-dof-ring-present-count`
- `data-dof-ring-absent-count`
- `data-dof-ring-count`
DoF ring display は marker object count とは別の presentation overlay として観測する。

status section は最新 frame summary text も反映する。

## Expected Marker Object Count

root `data-marker-object-count` は次の合計と一致する。

- marker bodies
- marker sites
- arm skeleton segments
- optional target marker
- optional error vector

現在の payload v0 fixture では、target がなく canonical arm skeleton
connection がある場合は body + site + arm skeleton になる。target と tip の
両方がある場合は body + site + arm skeleton + target + error vector に
なる。

## Expected Marker Position Behavior

- scene object registry は named body, site, target, error vector の
  `Object3D` instance を保持する。
- scene object registry は arm skeleton segment を read-only の `Object3D`
  connection として canonical payload body/site positions 間に保持する。
- fast_arm mesh scene は canonical STL assets を主 arm visual とし、mesh pose
  は payload body transforms からのみ作る。
- canonical `fast_arm` asset source は `assets/mujoco/fast_arm/` とする。
  asset contract は `docs/contracts/assets.md` と
  `assets/mujoco/fast_arm/README.md` を参照する。
  viewer は表示用 asset source として参照するだけで、STL / XML の
  geometry / scale / axis / origin / units / joint semantics は変更しない。
- Reused marker keys reuse the same object identity.
- 各 marker object の position は marker scene model に保存された payload
  marker coordinates に従う。
- arm skeleton segment は arm skeleton scene model に保存された payload
  body/site positions に従う。
- fast_arm mesh pose は、保守的な body mapping がある場合に限り、対応する
  payload body `position_m` と `quaternion_wxyz` に従う。
- error vector object は tip endpoint を position に持ち、target endpoint を
  `userData` に保持するので、pose を再計算せずに tip -> target 方向を
  表示できる。
- browser smoke が証明するのは payload coordinate の直接反映までであり、
  final coordinate mapping layer ではない。
- Phase D completion audit は `docs/operations/r6-d-completion-audit.md` に
  記録される。
- 次の handoff は IK / command integration skeleton work であり、rendered
  arm mesh でも完成済み IK path でもない。

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

- smoke server が ready になる前に browser を開いた場合は、grace period の
  後で refresh するか smoke command を再実行する。
- status が `WebSocket: open` に到達しない場合は、表示された endpoint と
  browser URL query string が一致しているか確認する。
- marker summary が更新されない場合は、grace period 中に viewer を開いた
  か、CLI がまだ frame を publish しているか確認する。
- object count が合わない場合は、表示中の payload frame に
  `target_position_m` があるか、canonical arm skeleton の body/site names
  があるかを確認する。

R6-G-P5 の troubleshooting では
`docs/operations/websocket-host-port-contract.md` を参照して host / port / URL
の混同を切り分ける。
R6-G-P5 の runtime-to-viewer E2E smoke 本体は
`docs/operations/runtime-to-viewer-e2e-smoke.md` に置く。

## Non-Goals

- production server はない。
- browser automation はない。
- auth, TLS, reverse proxy はない。
- hardware, serial, OSC access はない。
- payload schema change はない。
- transport schema change はない。
- marker と fast_arm mesh skeletons を超える Three.js real scene mutation
  はない。
- `@types/three` や Rapier の再導入はない。
- DoF ring display は body transform の `position_m` と
  `quaternion_wxyz` を表示用に反映する。
- DoF ring の `logicalJointLabel` と `label` は provisional な表示名であり、
  joint convention / IK semantics の source of truth ではない。
- `data-dof-ring-count` は descriptor count の互換 alias として扱い、
  present / absent の内訳は `data-dof-ring-present-count` と
  `data-dof-ring-absent-count` で読む。

R6-F-P5 では、この smoke path を採用済み viewer 表示要素の観測点としてのみ
扱う。これは旧 Web View の full parity contract ではなく、有用な表示要素と
除外する legacy UI を分離するための基準である。

R6-F-P6 の completion audit は、この smoke path が成立済みであることを
文書化し、Sweep_x visual demo と viewer 可視化 boundary の完了状態を
`docs/operations/r6-f-completion-audit.md` に固定する。browser visual smoke は
引き続き rendering-only の観測手順であり、新しい feature 追加の場ではない。
