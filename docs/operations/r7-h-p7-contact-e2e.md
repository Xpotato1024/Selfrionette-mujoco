---
status: canonical
owner: operations
last_verified: 2026-09-13
canonical_for:
  - R7-H-P7 software-only contact E2E
related:
  - docs/contracts/contact-task-manifest.md
  - docs/contracts/virtual-reaction-force.md
  - docs/contracts/contact-task-log-v1.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
  - docs/reports/audits/r7-h-p7-completion-audit.md
---

# R7-H-P7 contact E2E

Issue #417 の有限 smoke は、contact manifest のscene生成・reset、MuJoCo contact solverによるraw
evidence、virtual reaction-force、raw evidenceだけを入力とするTask、versioned log、同じsnapshotの
viewer payloadを一続きで検証する。出力はsoftware fixtureの検証artifactであり、実験参加者や実機の
観測記録ではない。

## 境界

- RobotBundleから読み込んだ`arm.xml`はメモリ上のコピーだけを変更する。`tip`位置に半径0.01 mの
  `contact_e2e_tool_proxy`球を追加し、production assetやRobot profileは変更しない。
- cubeのscene identityは`contact_cube_scene/v1`である。初期状態は非接触で、reset後もscene identityと
  manifest digestを照合する。
- 軌道は明示したqpos目標をJacobian pseudoinverseで設定し、`mj_forward`で状態を再計算する。
  `mj_step`、hardware、serial、OSC、robot output、network accessは実行しない。
- Taskはraw contact evidenceから評価する。derived forceには2 Nのmagnitude clampを設定し、
  Taskの5–15 N raw bandと異なる値のまま同じsampleへ記録する。
- `--software-revision`には対象source commitを明示する。CLIはGit HEADやdirty working treeから
  revisionを推測しない。unit / integration testでは専用の`test-only-...` identityを使用する。
  manifest identityとsummaryはrevision、fixture version、model input SHA-256、proxy identityを保持する。
- 生成するJSONLは既存`contact-task-log/v1`であり、そのschemaを変更しない。summaryはこのscriptが
  strict decodeする`contact-e2e-summary/v1`、viewer snapshotは`payload-v0`である。
- `payload.qpos`はcube freejointを含むMuJoCo scene全体の配列のまま保持する。Robot profile用のaddressは
  同じmodelとresolved profileのcanonical joint namesから解決し、optional
  `metadata.contact_scene_robot_qpos_v1` (`contact-scene-robot-qpos/v1`)にscene / manifest / frame / time bindingとともに記録する。

## 実行

Python環境にrepositoryのruntime sourceとfast_arm core sourceを含める。出力先は、呼出側が用意した
空の絶対directoryにする。同名artifactを上書きしない。

```powershell
$repoRoot = (Get-Location).Path
$artifactDir = '<existing empty absolute directory>'
$sourceRevision = '<commit SHA under validation>'
$env:PYTHONPATH = "$repoRoot\src;$repoRoot\src\selfrionette\plugins\robots\fast_arm\core\src"
$env:PYTHONDONTWRITEBYTECODE = '1'
python "$repoRoot\scripts\viewer\generate_contact_e2e_artifacts.py" `
  --output-dir $artifactDir `
  --software-revision $sourceRevision
```

テストでは`--software-revision test-only-contact-e2e-v1`のような明示identityを使う。productionまたは
PR validationでは、検証対象commit SHAを呼出側が渡す。作業中のHEADを実装snapshotと見なさない。

成功時は次の3 artifactを出力directoryだけへ作成する。

- `contact-task-log-v1-<trial fingerprint>.jsonl`: raw evidence、derived signal、Task state/outcomeを持つstrict log
- `contact-e2e-payload-v0.json`: logの最終sampleと同じtime / frame / qposを持つviewer payload
- `contact-e2e-summary-v1.json`: revision / fixture / model binding、reset、5つのnegative control、
  valid Task、force range、artifact hash、2回のsemantic determinism、software-only executionを持つsummary

scriptは生成前に同じcaptureを2回実行し、canonical log / payload bytesが一致しなければ失敗する。
logとsummaryをstrict decoderへ戻し、viewer payloadもcanonical JSONとして読み返してから成功を返す。
failed write後に作成済みartifactは同じ出力directoryから除去する。

## 成功条件と確認

summaryで次を確認する。

- scene reset後の状態が`no_contact`で、scene identityとmanifest digestが初期値に一致する。
- valid trialは`approach → first_contact → press → hold → success`で終了し、Task outcomeはraw evidenceだけを
  使用する。raw force rangeは5–15 N内、derived peakは2 N clamp以下である。
- `no_contact`、`measurement_unavailable`、`invalid_contact`、`invalid_scene`、`solver_invalid`の5 controlが
  それぞれ期待するevidence / signal / Task classificationでfail-closedになる。
- logとsummaryのmanifest / scene / trial binding、payloadのtime / frame / qpos binding、revisionを含む
  `software_revision_identity`が一致する。
- qpos projectionのsource dimensionがpayload全体のqpos lengthに一致し、canonical joint orderとaddressが
  Robot profileに合う。viewerはこのmappingと同じsampleの`contact_task_v1` bindingを検証し、Robot profile用の
  値だけを適用する。full scene qposを切り詰めず、欠落・stale・replayed・mismatch時にsceneを`ready`にしない。

read-only product viewerへlogとpayloadを渡す場合は
[Product Viewer WASM scene renderer](product-viewer-wasm-scene-renderer.md)のoffline file inputを使う。
cube、contact point / normal、raw force、derived force、Task outcomeが同じframeで表示されることを確認し、
Robot modelに適用したqposがpayloadの`qpos_addresses`と一致することを確認し、viewerがforceやqposを再計算しないことを保つ。

## 主張範囲

このfixtureはcontact scene、solver evidence extraction、derived-signal lifecycle、raw-evidence Task、log、
viewer snapshotのsoftware integrationを検査する。qposを規定する有限software fixtureであり、
dynamic stability、trajectory safety、physical force、haptic device、participant response、実機動作を
証明しない。pilot条件やphysical observationへ昇格させず、該当するhardware operator gateを迂回しない。

実装結果と未実施gateは
[R7-H-P7 completion audit](../reports/audits/r7-h-p7-completion-audit.md)を参照する。
