---
status: historical
owner: runtime
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/contracts/pre-hardware-signal-emulation.md
  - docs/contracts/contact-task-manifest.md
---

# ADR 0008: 信号から接触までを単一sceneの実行で検証する

## 状態と目的

#543の実装方針。P1-P3の部品試験を並べるのではなく、production Input Source / Mapping / typed routeから
同じMuJoCo sceneを更新し、raw contact Task / log、no-I/O wire previewへ結ぶ。実機完了ではない。

## 確認した不足

従来backendは全jointを指令対象とし、qvelも全消去する。cube freejointが加わるsceneでは4軸指令を
そのまま適用できない。Robot用snapshotもscene全体のqposと区別する必要がある。

## 決定

- backendへ実行前に一度だけscalar joint名をbindする限定APIを追加する。既定動作は変えない。
  named groupへの指令はそのqpos/qvelだけを変更し、cubeのfreejoint状態を保存する。
- runtimeのContactRobotViewは同じmodel/dataを共有してRobot座標を名前/addressで投影するだけとする。
  scene全体のsnapshotは別に保持し、切り詰めや第二のFK/IK/physicsを作らない。
- Robot-owned resourcesのpreflightで既存profile/limit configを検証する。実行sceneは1つとし、
  geometryを変えないbase Robotとderived sceneのjoint名・初期値対応を確認する。
- profileで宣言するtool siteに半径0.01 mの明示synthetic sphereをprivate asset copyとして追加する。
  proxy、model digest、source revision、実際のMuJoCo versionをartifactへ記録する。実物形状とは扱わない。
- Robot側は既存direct-qpos backend semantics、cube側はmj_stepの運動を保持する。
  quasistaticな規定Cartesian軌道や別IKで入力を置換しない。dynamic stabilityや実機軌道安全性は主張しない。
- 取得失敗では新しい指令を生成せず、partial traceと元の終了理由を残す。Task outcomeとrunner終了理由を混同しない。
- contact-task-log/v1とpayload-v0は再利用する。追加のscenario/traceはlocal-only strict JSONに限定し、
  固定revision・入力digest・各段階の記録を照合する。内容digestは真正性の署名ではない。
- CLIはfixture file / output directory / software revisionだけを受け、port/host/permissionを持たない。
  実機P5 allowや#509証拠は生成しない。物理出力permissionはdisabledのまま記録する。

## 却下した代案

全scene qposを4個へsliceする案、cube速度を毎回0にする案、別simulationからcontact値をコピーする案は
観測意味を変えるため却下。汎用scheduler・registry・新しいplannerは不要。既存contact E2E scriptを
productionからimportする案も、旧規定軌道と新しい入力経路を混同するため採用しない。

## 受入と残存gate

両sourceからのcontact到達と失敗、順序を変えたsceneのnamed projection、cube速度保持、no-contact、
悪い入力/応答、同条件再生成、改ざん・truncation、終了後の再送禁止、I/O tripwireを検証する。
実機安全/実機通信/校正は#509/#516-#519に残る。software未完が見つかればcompletionを偽装しない。
