---
status: canonical
owner: architecture
last_verified: 2026-07-17
canonical_for:
  - product viewer wasm scene renderer operation
related:
  - docs/archive/design/mujoco-wasm-scene-renderer-design.md
  - docs/archive/research/mujoco-webviewer-options.md
  - docs/archive/operations/wasm-qpos-sync-poc.md
---

# product viewer WASM scene renderer

`apps/mujoco-viewer`は`@mujoco/mujoco` WASM scene rendererの現在のproduction ownerである。
renderer、tests、fixture、operator pathはproduct viewer側に一本化する。

## boundary

- Python native MuJoCo backend / IK / FK / runtime が source of truth
- Browser WASM MuJoCo は visual renderer only
- browser 側で IK / FK / qpos recompute はしない
- browser 側で qpos correction はしない
- qpos は runtime payload を優先し、未接続時は compiled MuJoCo model default qpos を startup pose として使う

## product viewer entrypoint

- `apps/mujoco-viewer/src/main.tsx`
- default renderer mode: `wasm-scene`
- WebSocket接続時のmodel path: 最初のprofile-aware payloadのURL + digestから解決するversioned viewer declaration
- 未接続時のcompatibility path: plugin-owned
  `/mujoco/fast_arm/viewer-profile.json`をlegacy static facade経由でloadする

## WebSocket connectionとlive inputのlifecycle

- `connectionStatus`の所有者はWebSocket lifecycleである。開始前は`connecting`、`onOpen`は`open`、
  `onClose`は`closed`、`onConnectionError`は`error`、WebSocket無効時は`disabled`を設定する。
- declaration fetch、digest validation、model / VFS fetch、MuJoCo compile、scene構築はrendererの
  `status`（`loading` / `ready` / `error`など）だけを更新し、既に`open`になったconnectionを
  `connecting`へ戻さない。
- payload-first bootstrapは`open -> first profile-aware payload -> declaration / model bootstrap -> ready`
  の順で進み、bootstrap中もconnectionを`open`として保持する。
- live input availabilityは`connectionStatus === "open" && status !== "error"`から導出する。
  したがって`open/loading`、`open/ready`、`open/warning`はactive、`open/error`はfail-safeでinactive、
  closed / connection error / disabledもinactiveである。
- ProductViewerAppのinput effectはraw renderer statusではなく、この安定したavailability booleanだけを
  依存する。loading -> ready / warningではsenderとpollingを再生成せず、renderer errorになった時点で
  keyboard sender、gamepad sender、keyboard RAF、gamepad RAF / heartbeatをdisposeする。
- declaration fetch、digest validation、model / VFS fetch、MuJoCo compile、scene構築のfailureは共通して
  renderer `status=error`へ到達し、connectionStatusが`open`のままでもlive inputをfail-safe停止する。
- keyboardのblur / hidden safety、gamepadのfocus / visibility safety、cadence、deadzoneはこの
  connection lifecycleによって変更しない。

## 接触task logとpayloadのoffline表示

- `contact-task-log/v1` JSONLをlocal fileとして読み込める。readerはschema、canonical JSONL、manifest / signal digest、scene / object / presentation、trial、profile bindingを厳密に検証し、contact point / normal、cube pose、raw world force、derived signal、Task state、raw-evidence outcomeを表示する。
- viewerはcontact physics、force transform / filter、Task outcomeを再計算しない。3D overlayはbackend presentation projectionから作り、derived force arrowはframeが`mujoco_world`と明示された場合だけ描く。
- offline contact logにはrobot qposが含まれない。別途表示中のposeと時刻同期が保証されないため、UIはlog-only入力をその旨明示する。決定的synthetic fixtureはMuJoCo実測として表示しない。
- transport payload-v0 JSONをlocal fileとして読み込む入口では、既存のprofile / qpos validatorを通し、同じsnapshot由来の`qpos`とoptional `metadata.contact_task_v1`を表示する。contact metadataがmissing / malformed / stale / profile mismatchなら接触force overlayを消去し、残留させない。
- ContactScene全体の`qpos`にobject freejointが含まれる場合、producerは別optional `metadata.contact_scene_robot_qpos_v1` (`contact-scene-robot-qpos/v1`)で、同一scene / manifest / frame / timeのfull-scene qposからloaded Robot profileのcanonical joint addressを示す。viewerはこのmappingを同sampleの`contact_task_v1`とprofile / model identityへ照合し、妥当な場合だけ対応joint値を適用する。mappingまたはbindingが欠落・不正・stale・replayed・mismatchedならsceneを`ready`にせず、前回sceneを新sampleとして残さない。extensionがないpayloadは従来どおりqpos lengthとmodel dimensionのexact matchを要求する。
- live payloadでもcontact projectionはread-only display用である。invalid contact metadataはcontact sectionをunavailableにし、qpos / sceneの別validationを迂回しない。どの入口もnetwork、serial、OSC、device、robotへのforce / command出力を追加しない。

## startup pose source

- `home` keyframe: canonical fast_arm startup qpos。pre-payload表示はMJCFからこのqposを読む
- compiled MuJoCo model default qpos: historical fallbackではなく、startup sourceには使わない
- fixture qpos: default startup path では使わない
- runtime qpos: WebSocket payload が来たら `data.qpos` に適用する

## viewer declaration startup

- generic viewer sourceはproduction robot ID registryを持たない。
- WebSocket接続時は最初のframeにあるdeclaration resource path、deterministic public URL、SHA-256 digestを
  検証してfull declarationを一度だけfetch / strict decodeする。model、fixture、VFSのURL / resource対応、
  joint order、qpos dimension、keyframe、model contractを描画前に検証する。
- steady-state frameは同じcompact referenceだけを比較し、full declarationを再送・再decodeしない。
  reconnectでは再fetchし、session中のdigest / URL / resource path変更を拒否する。
- payload compatibility metadataとdeclarationが一致した場合だけmodelをloadし、qposを適用する。
- `fastArm.ts`は未接続時の既存表示を維持するcompatibility facadeであり、宣言内容を再定義せず
  plugin-owned JSONをloadする。新robot onboardingでこのfacadeまたはTypeScript registryを編集しない。
- viewerはdeclarationからrendering resourceを構成するだけで、IK、FK、planning、qpos生成、安全判定を
  行わない。

## canonical qpos fixture

- owner: fast_arm Robot Plugin resource
- path: `assets/mujoco/fast_arm/fixtures/fast_arm_sweep_x_qpos.json`
- schema owner: `apps/mujoco-viewer/src/wasm-scene/qposFrameTypes.ts`
- 再生成: `uv run python scripts/viewer/export_wasm_qpos_fixture.py --preset sweep_x --steps 30`
- fixture playbackはdebug/validation専用であり、startupはnamed `home` keyframeを使う

## fixture生成のintegrity

fixture再生成はstale velocity、BADQACC、time rollback、non-finite qpos、dimension不一致をrejectする。
exporterはin-memory sequence全体をvalidateし、serialization成功後だけtargetをatomicに置換する。
canonical fixtureはstrictly increasing simulation time、finiteな4-value qpos、move / return progression、
intentional terminal holdを持つ30 framesである。current SHA-256は
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
