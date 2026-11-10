---
status: proposed
owner: architecture
last_verified: 2026-11-11
canonical_for: []
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/contracts/launch-profile.md
  - docs/contracts/finite-trial-runtime.md
  - docs/contracts/object-scene-contact-diagnostic.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
  - docs/contracts/workbench.md
---

# Scene単独実験とMuJoCo版選択の統合案

## 状態と目的

2026-11-11の本人の方針修正を受けた設計案。現行仕様・実装済み機能・merge承認ではない。
PR #643の `mujoco4_article` 専用実行・専用収録経路は予備検証として扱い、そのまま恒久機能として採用しない。
取得済みの素材・数値・固定upstream原本は保全する。次の実装は研究用Simの通常機能へ統合し、記事はその利用者とする。
この提案を置くだけで旧専用実装を汎用化できたとは扱わない。旧差分の置換は実装時の受入条件である。

## 確認した現状

調査基点はmain `d3e667b461ff0d795c03afb9bbe43fc7c68201da`。並行PR #640〜#642の未マージ差分を現行仕様と混同しない。

| 現行の所有者 | 確認した制約・再利用点 |
|---|---|
| `plugins/environments/object_scene_environment/` | 固定・可動・ばねbox、world、初期速度、登録済みpresetを所有。球やflexは今のbox schemaへそのまま追加できない |
| `runtime/scene/world_composition.py` | world/Executionのoption投影とhome合成を所有するが、Robotのsourceとhomeを前提とする |
| `runtime/execution/physics.py` | DynamicsSettingsに積分条件とRobotの速度・追従上限が混在。現行許可はEuler/implicitfast、Newton |
| `runtime/execution/model_execution.py` | 名前付きendpoint、Mapping、Source、fresh neutralを前提とする。Input未受信では物理が進まない |
| `runtime/experiment/trial_condition.py` | Robot/modelとInput/Mappingを必須にし、SceneとTaskの同時選択を要求する |
| `scripts/workbench_local.py` | 固定venv・固定Web buildの準備と起動を所有。workerは既存プロセス監督から起動される |
| `apps/mujoco-viewer/` | Pythonを物理の正本にしてWASMを描画に使用。既存の描画契約にはflex/skinを含む。4.0材料・状態の対応が完了した証拠ではない |

したがって「柔軟体XMLを追加する」「Robotを見えなくする」「pipで上書きする」だけでは通常経路にならない。
既存の責務を必要な境界で一度だけ一般化し、記事専用runtimeやphysics loopを追加しない。

## 採る構造

```text
Profile（Scene / 任意Robot / Control / Physics / Engine / 任意Task）
  → 共通の構成・能力・初期状態検証
  → 選択した固定環境で同じWorkbench / TrialRunner / ModelExecution
  → 唯一のMuJoCo物理実行・同一時刻の観測
  → 共通記録 / 通常Viewer / 保存記録からの映像出力

記事制作：記録・映像を利用して本文、図のラベル、GIF等を作成する
```

別の物理エンジン一般を扱う新frameworkは作らない。当面の対象はMuJoCoの版選択と既存研究基盤の構成能力である。
「共通化」は型の意味を失わせることではない。rigid/flex、controlled/passiveの異なる条件を明示し、未知値を推測で補完しない。

## 1. Scene・Objectとして増やす

利用者は、キューブ・ばねと同じScene選択から球体、薄い障害物、弾性体、弾塑性体を呼び出す。
高速球体は新しい種類の物理objectではなく、sphereの形状・質量・初期速度を設定したpresetにする。

Environmentはworld、形状、材料、境界・固定条件、初期位置/速度と資源参照を所有する。
数値積分、solver、step幅、投機的接触flagはExecutionの物理設定が所有する。
時間刻みや接触flagをpreset内部へ隠して、比較対象ごとに別条件で実行しない。

box/sphereは識別可能なgeometry型として既存Object定義を拡張する。柔軟体はtopology、material、固定点、
質量などを持つ型付きのmodel resourceとして扱い、boxのhalf_extentsへ押し込まない。
MuJoCoのflex/MJCFを再利用し、Sim側にFEM計算や別の材料ソルバーを実装しない。
すべてのMJCF要素を一般化する独自DSLも作らず、必要なresource/parameterを所有するpluginへ閉じる。
登録済みの資源と有限なtyped parameterだけを受理し、任意XML/path/importを無検査で実行する入口にはしない。

## 2. Robotなしを構成として正式に扱う

画面では「ロボットなし」を選択できる。内部は明示的にRobotを選択していない構成とし、
空Robot・偽のendpoint・ゼロ値のFK・見えないfast_armで必須項目を埋めない。
Robotなしでも、球のfreejointやflexには自由度がある。Robot不在を `model.nv == 0` と同一視しない。

構成resolverはworldからmodelを構築し、選択されたRobotがある場合だけそのresourceと制御能力を合成する。
homeは選択componentの初期状態から一回だけ構築する。freejoint quaternion等を無効なゼロ配列で埋めない。
既存Robotのhome、関節順、境界・安全条件を変更しない。

Input/Mappingは制御対象がある構成に対して必要とし、Scene単独の受動物理実験に偽Gamepadやneutral入力を送らない。
共通の実行ownerが明示Start後に同じstep処理を進める。Robot制御のある条件では従来のfresh neutralとfreshnessを維持する。
条件付き分岐は構成・能力検査と適切なownerへ集中させ、各層へ `if robot is None` を散在させない。

Taskなしの有限観測も許す。duration終了は試行停止理由であってTask成功ではない。
Robot endpointが必要なTask/Evaluation/MappingをRobotなしで選んだ場合は準備時に理由付きで拒否する。
UIは利用できないRobot操作を無効化し、床・カメラ・時計・開始/停止/reset・記録は共通に保つ。

## 3. 数値設定とRobot制御設定を分離する

現行DynamicsSettingsのphysics_dt/integrator/solver/iterations/toleranceと、
max_joint_speed/max_tracking_errorなどのRobot制御上限は、異なる責務として分離する。
Scene単独実験に無意味なRobot上限を入力させず、Robotを追加した場合は制御条件を明示的に合成する。

solver/integrator/flagの選択は、エンジン版の実測済み能力と選択モデルの要求を照合する。
全柔軟体を4.0専用とはしない。弾性体、弾塑性、投機的接触など、機能ごとに必要条件を管理する。
未対応flagを無視、solverを暗黙変更、flexを剛体に代替することは禁止する。

## 4. 3.9.0 / 4.0.0は起動前に固定環境を選ぶ

同じsourceと共通の依存定義から、MuJoCo版ごとの固定依存環境を準備する。
既存launcherが、選択環境のPythonで同じWorkbenchとworkerを起動する。別launcherや記事専用runnerは増やさない。
選択はMuJoCoをimportしてmodelを構築する前に確定する。通常起動中にpipで版を入れ替えない。
初回setupは明示操作、通常起動は用意済み環境を検証して使用する。未準備なら準備方法を示して拒否し、別版へfallbackしない。

Profile/CLIで要求した版と、実workerが報告する版・lock・Sim revisionを照合する。
CLI overrideを提供する場合はProfileの無言の書換えではなく、新しい実効条件として表示・保存・再検証する。
旧Profileの保存bytes/digestは書き換えず、旧来歴と新しい実効条件のdigestを区別する。
バージョンはlatestでなく3.9.0/4.0.0等のexact pin。初期対応は起動session中固定とし、変更は終了・再起動して新session/epochで行う。

Pythonだけでなく、ViewerのWASM・model宣言・描画変換の整合も扱う。
初期方針は検証した同一版のnative/WASM組を選ぶこと。異版組合せを使う場合は別の互換性検証が必要。
同じViewer shellと描画adapterを使い、固定の資源選択表から対応WASMを選ぶ。4.0専用UIは作らない。
通常Viewerで使えるWASM版・APIの実在性と、flexの表示を受入時に確認する。native成功だけでブラウザ成功としない。

## 5. 記録・再生・出力を共通化する

モデル/資源、Scene、初期条件、入力、Physics、engine exact version、依存lock、software revisionをtrialへ束縛する。
描画用のsnapshotと、物理計算を再開するcheckpointは別の要求とする。
MuJoCo4.0では `mjSTATE_PLASTIC` があり、qpos/qvelだけで塑性を含む完全再開を保証しない。
実装ではその版の公式state APIと必要な状態項目を確認し、同一版・同一model/layoutの保存/復元試験を行う。
版間でcompiled modelやstateの生bytesを無条件流用しない。resetで塑性・積分履歴・入力・Taskも初期状態へ戻す。

保存済みtrialから通常Viewerへ状態を反映して映像出力する既存方向を優先する。
#642のraw-video exporterは未マージ差分として確認し、統合時に再利用・一般化する。別のcapture.pyに物理再実行を持たせない。
新規収録も同じ実行owner/記録を使い、再生と再シミュレーションを混同しない。
記事名、記事用モデル一覧、図中文字、サイト固有のGIF圧縮はSimの実行条件に入れず制作側へ置く。
物理のstep/control周期と描画fpsを分離し、再生の0.3倍速やエンコード時間をRTFと呼ばない。

## 例示する組合せ（構想であり現行の設定schemaではない）

| Scene | Robot | Control | Engine / 数値条件 | 用途 |
|---|---|---|---|---|
| キューブ・ばね | 既存単腕/双腕 | 既存入力・Mapping | 3.9.0の既存条件 | 研究の回帰基準 |
| sphereと薄い壁 | なし | なし | 3.9.0または4.0.0、共通に指定した刻み等 | エンジン差の比較 |
| 同じsphereと壁 | なし | なし | 4.0.0、同じ条件で投機的接触OFF/ON | 機能の独立比較 |
| 弾性/弾塑性の薄板・棒 | なし | なし | モデルの能力要求を満たす版・数値設定 | 材料モデル観察 |
| 同じ柔軟体 | fast_arm | 既存入力・Mapping | 検証済みエンジン構成 | 押圧・接触研究への接続 |

高速球体、なしRobot、4.0を固定した記事専用profile型は作らない。既存の役割別profileとGUI選択へ投影する。

## 実装順序と受入条件

1. **版と構成の共通契約**：現行3.9条件の回帰を基準化し、optional Robot/Control/Task、PhysicsとRobot制御の分離、engine identityを設計・実装する。未知条件を拒否し旧保存データを改変しない。
2. **Scene単独のsphere実験**：まず既存3.9でも扱える小さい物理実験を通常TrialRunnerで成立させ、start/stop/reset/記録/通常Viewerを端まで検証する。Robot不在を一時的な例外経路で済ませない。
3. **固定4.0環境と表示・保存**：同じprofile解決・実行ownerに4.0を加え、native/WASM照合、版別能力、途中変更拒否、epoch/資源の廃棄を確認する。
4. **柔軟体と接触機能**：登録resourceから弾性/弾塑性を構成し、reset・checkpoint・通常Viewer・記録で同じ状態を確認する。既存Robotを同じSceneに追加できることも試験する。
5. **共通exportと記事**：任意の検証済みtrialから同じexportを使う。旧専用loop/CI/モデル固定分岐をPR差分から除き、通常機能で再生成した素材を記事に採用する。

必須negative case：未対応4.0機能の3.9選択、版/lock/renderer/model不一致、Robotなしへのendpoint必須Task、実行中の版変更、塑性を落としたresume、旧epochの表示、取得していない評価値の0補完。

取得済み素材は予備検証として再利用可能だが、正式な通常Viewer経由の素材や全体RTFの証拠へ読み替えない。
この提案と今回の調査にhardware access、serial、OSC、merge、deploy、並行PRの採用は含まれない。
