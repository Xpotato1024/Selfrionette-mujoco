---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - live viewer smoke path
related:
  - docs/operations/websocket-publisher-runner.md
  - docs/operations/backend-viewer-startup.md
  - docs/architecture/data-flow.md
  - apps/mujoco-viewer/README.md
---

# live viewer smoke

R6-C-P3でreplay payload v0からbrowser viewer runtimeまでのdeterministic local smoke pathを追加した。

## command

```bash
uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

## viewer URL

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

CLIが表示するWebSocket endpointは`ws://127.0.0.1:8766`、browser viewer URLは
`apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766`である。endpointとbrowser pageを混同しないよう、
CLIは両方を出力する。

`websocketUrl`なしで`/apps/mujoco-viewer/`を開くと、設計どおりdisconnectedのままになる。
`?ws=ws://127.0.0.1:8766`はcompatibility aliasとして受理する。

## 推奨手順

1. terminal 1でsmoke commandを起動する。
2. CLIが表示したViewer URLをcopyする。
3. grace period中にbrowserでViewer URLを開く。
4. viewer statusが`WebSocket: open`へ変わることを確認する。
5. marker summaryがpayload v0 frame updateを反映することを確認する。

smoke commandはlocal WebSocket server起動後、最初のpayload publish前にbrowserが接続できるようgrace periodを
設ける。viewer WebSocket clientは現在reconnectを実装していないため、server準備前にbrowserを開くとerror stateに
残る場合がある。grace window終了前にbrowserが接続しない場合、runnerはpayloadをdropする。

R6-C-P4ではlocal/dev publisher、browser viewer、marker summary update skeletonからscopeを広げず、このsmoke
pathをPhase C completion handoffとした。R6-D-P1ではviewer側にThree.js scene object registry skeletonを追加し、
R6-D-P2ではbrowser viewerのrendering-only roleを変えず、payload marker coordinateをThree.js objectへ直接適用した。
R6-D-P4のPhase D completion auditは`docs/reports/audits/r6-d-completion-audit.md`に置き、次のhandoffをrendered
arm meshや完了済みIK pathではなくIK / command integration skeletonへ限定した。

canonical backend / viewer startup guideは`docs/operations/backend-viewer-startup.md`、host / port / URL contractは
`docs/operations/websocket-host-port-contract.md`を正とする。
R6-G-P5 の E2E smoke / troubleshooting の本体は
`docs/operations/runtime-to-viewer-e2e-smoke.md` に置く。

## smoke pathが証明する範囲

- Python replay dry-runがpayload v0を生成する
- local/dev WebSocket publisher runnerがclientへpayload v0をdeliveryできる
- browser viewerがconfigured endpointへ接続できる
- viewer runtimeが受信payloadをstateへ保持する
- marker rendering skeletonがlatest payloadからsummary text、scene placeholder text、root attributeを更新する
- viewerがmarker skeleton object向けThree.js scene object registryを維持し、marker scene modelからpayload
  marker positionを直接適用する

## success condition

- viewer statusがopen WebSocket connectionを示す
- summary textが受信`frame_index`まで進む
- viewer rootのbody/site countが受信payloadへ追従する
- rendered marker summaryに`base_link`と`tip`が残る

## client不在時のbehavior

Python publisher runnerは不在client向けpayloadをbufferしない。frame publish時にbrowser viewerが未接続なら、そのframeを
dropする。smoke pathをdeterministicに保つにはgrace periodを使うか、viewerを先に起動する。

## scope

- browser automationなし
- production serverなし
- auth / TLSなし
- reverse proxyなし
- public network exposureなし
- serial、OSC、hardware accessなし
- `@types/three`またはRapierの再導入なし
- direct marker position assignmentを超えるThree.js real scene mutationなし
- direct payload coordinateを超えるbody/site/target position mappingなし
- FK / IKなし

## handoff

R6-D-P3ではrenderer、camera、animation loopを追加せず、browser-visible DOMとscene-object smoke stateを
`docs/operations/browser-visual-smoke.md`へ記録した。

R6-E-P0ではstale placeholderだけを削除し、empty-directory `.gitkeep` markerを維持してPhase E準備cleanupを行った。
次のhandoffは別parent Issueで作るPhase E IK / target command integration skeletonである。
