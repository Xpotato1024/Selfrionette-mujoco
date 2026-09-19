---
status: historical
owner: architecture
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/architecture/data-flow.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/contracts/endpoint-metadata-vocabulary.md
---

# R7-L全体整合調査（実装前の基点）

## 基点・調査範囲

Issue #545。main `3cb152f2b28235a3baa42df1be9021530a0c2749` と
PR #544 `ae27b0746017dab5eac416e14f71763386fd8f07` を区別した。
本報告は後者の時点snapshotであり、current contractの第二SoTではない。

全845 tracked filesをpath/hashで棚卸しし、482 Python filesをASTで解析、
canonical候補78文書を抽出した。merge前に先頭front matterだけを再検査した結果、
canonicalは77文書であり、historical文書内の転載例を拾った1件を集計から除外した。
これは全845ファイルの逐行意味監査を意味しない。構造棚卸しと下表の境界レビューを分ける。
外部reviewerやCodexは使わず、同じassistantが要件から再検討した。

| 範囲 | 確認した主要owner | 深さ・制約 |
|---|---|---|
| 入力 | source catalog/registration、Selfrionette parser/lifecycle、viewer message | production entryとhealth/source state。実装した装置のcalibrationは未確認 |
| 写像 | 4 Mapping declarations、loadcell/analog/viewer implementation | schema、parameter、unit、frame、route宣言 |
| 実行 | command_routes、pipeline、input_step_loop、concrete/replay builders | 呼出順、generator選択、同一条件の実行反例 |
| 実験 | world_tool_runner、motion_log_recorder、evaluation manifest | readiness、Taskへのmeasured値、traceとlogの分離。全metric数式は再監査していない |
| 接触 | ContactScene、contact evidence/presentation、P7操作手順 | scene address/reset、raw/derived evidence。全contact solver branchは未監査 |
| 出力 | FastArm session/map、OSC codec、input-safety | physical handoff、permission、correlation、simulation/physical truth区別。実配備routerは未確認 |
| viewer | qpos application、WASM renderer、boundary guard | 受信qposをmj_forwardで描画。全UI処理やブラウザ実操作は未確認 |
| firmware | archived candidateのprotocolとREADME/REVIEW | vector形式の参照のみ。upload/serial open/ビルド/実測なし |
| 管理 | AGENTS、SoT map、workflow、Issue/PR全本文 | 履歴保持、独立監査との区別、未完了gate |

## 実行経路の分類

- operational viewer/replay: Robot / Input Source / Mapping / command routeを接続する。
- Selfrionette continuous: PR #544が追加したprogrammatic step-loop。公開generic CLIとは別である。
- R7-G: six-axis readinessから作る専用free-space experiment runner。offline/replay限定でmanaged sourceを開始しない。
- R7-H-P7: quasistaticなtool-target fixtureとmj_forwardによるcontact E2E。production連続入力やdynamic安定性の証拠ではない。
- physical output: accepted #509 evidenceとoperator permissionが必要な別session。疑似信号によってgateを突破しない。
- legacy absolute-target smoke: per-frame helper。continuousなdelta routeと同一の実行経路とは扱わない。

## 前回self監査の再分類

| 旧指摘 | 再判定 | 必要な対応 |
|---|---|---|
| 0.01 m capがあるから不正 | 断定を撤回。capはmainにも存在し、既存glossaryはbounded policyを定義する | capは維持。Mapping要求、policy bound、joint bound、measured結果のownerとprovenanceを明示 |
| metadata分岐はすべて禁止 | 断定を撤回。契約は最終Robot command semanticのidentity/type整合を要求する | 下記の同一route実行不一致を根拠に変換責務を修正 |
| caller-supplied anchorにMuJoCo値が入るのは矛盾 | 断定を撤回。callerが観測値を渡してもanchorの契約は成立する | key単独をmeasurement authorityにしない。producer/lifecycleを追記 |
| 必須placeholder | continuous APIの設計不足 | dynamic contextと固定parametersを分離。legacy純粋関数の契約は維持 |
| requestとmeasurementの試験不足 | 試験不足として維持 | 実際のbackend commandとpost-step snapshotを別々に検証 |

## F01: 同じrouteでも実行入口で異なる挙動（再現済み）

同じproduction selectionから二つのplanを作り、一方をstep loop、他方をmanaged readerの
start/closeを明示したpipeline.run_onceへ渡した。どちらもrouteは
`endpoint_delta_to_joint_position/v1`、dtは0.02 s、入力は
`vector,0,0.25,0,0,0,0,0,0`、channel0からYへのweight 1、gain/max_deltaは0.002 m。
固定anchorには比較用sentinel `(9,9,9)`を与えた。

| 出力 | step loop | pipeline.run_once |
|---|---:|---:|
| requested Y delta（m） | 0.0005 | 0.0 |
| 初期qposからのnorm変化（rad） | 0.002186812581637954 | 0.0 |

原因はstep loopだけがsource adapterを見てgenerator/context/metadataを切り替えること。
同じresolved routeが同じ変換を保証していないため、#540の受入をblockする。
修正はroute-ownedな明示delta実行methodとruntime contextへ収束させ、逆向きに検証する。

## F02: current documentationのstale記述（mainにも存在）

- data-flowは専用experiment runnerを未接続と書くが、world_tool_runnerは6軸を解決して実行する。
- unified-cliはevaluation不採用理由をrunner未実装とする。実際は専用runnerがあり、統一subcommandがない。
- data-flowはcurrent_tip_position_mを一律measurementとするが、glossaryはsource別のcompatibility anchorと定義する。
- import境界のviewer blanket prohibitionは、WASM renderer専用の既存許可と一致しない。
  mj_forwardによる描画と独立mj_stepによるphysics進行を分けて記述すべきである。

## F03: 接触sceneとcommand領域（#543へ）

ContactSceneはcube freejointを含み、robotとobjectをaddressでresetする。
一方、HeadlessMuJoCoSimulatorのjoint-position適用はmodel全jointを列挙し、qvel全体をzero化する。
4-joint commandを自由関節を含むsceneへ無条件で渡す設計は採用しない。
#543ではrobot-owned addressでcommand領域を限定し、object qpos/qvelを保つ必要がある。
既存P7のquasistatic fixture成功だけで、この結線が完了したと判断しない。

## 後続gateと未確認情報

#540はroute/context/policyの整合、#541は有限取得とreceipt clock、#542はno-I/O peer/response driver、
#543はsceneを含む統合とartifact監査を担当する。#486のgeneral control-plane UIを暗黙にscopeへ取り込まない。
実機joint sign/zero/offset/range、loadcell校正・noise/cadence、実配備router revision、実接触安定性は未確認。
未知値はplaceholderでphysical configへ書かず、実測gateを残す。

全体の構造調査を終えたことと、不整合の実装修正が終わったことは別である。
本報告単体でR7-L完了またはphysical readinessを宣言しない。

## merge前再監査での集計訂正

当初の機械索引は`canonical-content-history-separation-supplement-2026-07-16.md`内の
転載された`status: canonical`を拾っていた。当該文書自身の先頭front matterはhistoricalであり、
canonical数は78ではなく77。845 tracked filesと482 Python filesの数・AST解析は再確認済み。
過去の転載本文や原inventoryは変更せず、本報告の集計と現行契約の区別だけを訂正した。
