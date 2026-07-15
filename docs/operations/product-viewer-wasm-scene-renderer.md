---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - product viewer wasm scene renderer operation
related:
  - docs/archive/design/mujoco-wasm-scene-renderer-design.md
  - docs/archive/research/mujoco-webviewer-options.md
  - docs/archive/operations/wasm-qpos-sync-poc.md
---

# product viewer WASM scene renderer

`apps/mujoco-viewer` は、`experiments/mujoco-wasm-viewer-poc` で成立し #185 で昇格した `@mujoco/mujoco` WASM scene renderer の現在のproduction ownerです。実行可能なPoCは #385 で退役し、現行のrenderer・tests・fixture・operator pathはこのproduct viewer側に一本化されています。

## boundary

- Python native MuJoCo backend / IK / FK / runtime が source of truth
- Browser WASM MuJoCo は visual renderer only
- browser 側で IK / FK / qpos recompute はしない
- browser 側で qpos correction はしない
- qpos は runtime payload を優先し、未接続時は compiled MuJoCo model default qpos を startup pose として使う

## product viewer entrypoint

- `apps/mujoco-viewer/src/main.tsx`
- default renderer mode: `wasm-scene`
- model path: `/assets/mujoco/fast_arm/scene.xml`

## startup pose source

- `home` keyframe: canonical fast_arm startup qpos。pre-payload表示はMJCFからこのqposを読む
- compiled MuJoCo model default qpos: historical fallbackではなく、startup sourceには使わない
- fixture qpos: default startup path では使わない
- runtime qpos: WebSocket payload が来たら `data.qpos` に適用する

## canonical qpos fixture

- owner: product viewerの`apps/mujoco-viewer/`
- path: `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json`
- schema owner: `apps/mujoco-viewer/src/wasm-scene/qposFrameTypes.ts`
- 再生成: `uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30`
- fixture playbackはdebug/validation専用であり、startupはnamed `home` keyframeを使う

## fixture生成のintegrity

PR #392では当初、不正な再生成候補
`A30FD0A303506C7807BA2E687411FACDF28BA2BC2AE9AC8F909B9C59997FEE36`が得られた。
native simulatorが新しいjoint positionを適用するとき、前stepのvelocityを残していた。MuJoCoはBADQACCを出し、
`mj_step`からreset-like time valueを返した。snapshot、payload、exporterはその値を並べ替えたり変更したりしていない。
同じdefectはcurrent `main`と#392 branchの両方で再現した。

root-cause fixではposition-command boundaryがqposを書き込むときにvelocityをclearし、`sweep_x`はmove/returnの各frameへ
interpolated endpointを供給する。既存payload schemaとviewer boundaryを維持し、browser FK/IKまたはqpos
recomputationを追加しない。exporterはin-memory sequence全体についてindex、time、metadata、qpos finiteness、dimensionを
validateし、serialization成功後だけtargetをatomicに置換する。

修復後のcommandは、strictly increasing simulation time、finiteな4-value qpos、意図したmove/return progression、
intentional terminal holdを持つ30 framesを生成し、BADQACC warningを出さない。current canonical fixture SHA-256は
`4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A`である。

## 旧rendererの扱い

- decision: deleted
- default production routeは旧Three.js hand-built renderer stackをimportしない
- code bloatを避けるため旧viewer-specific renderer / runtime / view model / testsを削除した

## 実行

```powershell
cd apps\mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Vite dev server は起動後にブラウザを自動で開き、`/apps/mujoco-viewer/` を表示する。
実際の port は Vite の表示に従う。`5175` は手元環境での一例。
ポートが使用中なら Vite が次の空きポートを選ぶ。

## validation

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

## browser smoke

- viewerをloadできる
- WASMをloadできる
- fast_arm sceneをloadできる
- initial pose sourceが明示される
- qpos sync pathが動作するか、qpos unavailableを明示する
- floor / axes / legend / colorを表示する
- 旧rendererがdefault production pathにない

## 既知の制限

- fixture qpos は debug 用の参照としてのみ扱い、startup では自動適用しない
- live WebSocket qpos availability depends on publisher payloads
- browser-side payload correction is intentionally absent
