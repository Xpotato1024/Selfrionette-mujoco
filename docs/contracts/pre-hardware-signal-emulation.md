---
status: canonical
owner: runtime
last_verified: 2026-09-20
canonical_for:
  - pre-hardware signal emulation design and acceptance boundary
related:
  - docs/contracts/physical-output.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/architecture/research-execution-roadmap.md
---

# 実機前の信号エミュレーション設計

## 目的と完了の定義

実入力装置・実ロボットを接続せず、既存protocolの入力からtyped command、
MuJoCo観測、FastArm wire preview、疑似受信結果までを追跡する。
これはsoftware-in-the-loop（SIL）検証であり、hardware-in-the-loopや実測ではない。
「実機前完了」は本書の必須software gateをすべて満たした場合だけ宣言する。
部品のunit test通過、同じencoderによるencode/decode往復、CI成功だけでは代用しない。
既存実機Issueのacceptanceは変更せず、実測なしにcloseしない。

## 調査基点と確認済みの不足

調査基点は `3cb152f2b28235a3baa42df1be9021530a0c2749`。
次は当該sourceの事実であり、推定された実機仕様ではない。

| 項目 | 確認箇所 | 判定 |
|---|---|---|
| Selfrionetteの7ch parserとinjected lines | `plugins/input_sources/selfrionette/` | 再利用する |
| Gamepad JSON ingressと250 ms stale | `runtime/control/viewer_control_ingress.py`、viewer Source | 再利用する |
| loadcell用step loop | `runtime/execution/input_step_loop.py` | LOADCELL_SOURCEがunsupported。実行でも再現 |
| 専用loadcell runner | `runtime/runners/live_selfrionette.py` | 各frameでoffline helperを呼び、MuJoCoを再生成 |
| loadcell既定写像 | `plugins/mappings/loadcell_endpoint_mapping/implementation.py` | 7x3 weightsはすべて0。実機校正ではない |
| live reader | `plugins/input_sources/selfrionette/__init__.py` | serial timeoutなし、開始後healthは常にactive/age0 |
| FastArm出力 | `runtime/output/fast_arm_adapter.py` | physical acceptanceが必要。疑似実測で突破しない |
| receive producer / tick | `docs/contracts/physical-output.md` | 未実装。#516にsoftware作業が残る |
| contact E2E | `docs/operations/r7-h-p7-contact-e2e.md` | quasistatic fixture。連続実入力contact完了を示さない |

## 不変条件

1. MuJoCoだけがsimulation stateの正本であり、viewerとemulatorにFK/IKを複製しない。
2. Input Sourceは取得・health、Mappingは信号解釈、runtimeは状態と結線を所有する。
3. physical authorizationとsignal-preview許可を分離する。previewはsendable requestではない。
4. #509 accepted physical-measurement artifactを捏造しない。既存physical gateを緩めない。
5. command、predicted state、MuJoCo observation、synthetic response、physical measurementを区別する。
6. hardware / serial / DNS / UDP / OSC実送信、robot actuationは本Roundで実行しない。
7. source / mapping / robot / routeは既存versioned identityを明示する。暗黙fallbackしない。
8. 不明な実機値はunknownとして保持し、synthetic fixture値を実機既定値へ昇格しない。

## 全体構成

```text
Gamepad JSON fixture -> viewer/v1 -------------------+
Selfrionette CSV fixture -> selfrionette/v1 ----------+-> production Mapping
                                                        -> typed command route
                                                        -> 1 session / 1 MuJoCo
                                                        -> measured observation
                                                        -> PhysicalOutputRequest
                                                           +-> physical safety: unknownはnon-allow
                                                           +-> no-I/O wire preview
                                                               -> in-memory protocol peer
                                                               -> synthetic response / timeout
                                                               -> artifact / coverage report
```

no-I/O previewはphysical sessionの別名ではない。共通のpure command conversionとcodecを使うが、
physical evidence、operator grant、socket senderを受け取るAPIを持たせない。
physical sessionの正常系は既存test-only synthetic evidenceで別途回帰する。
二つのtestを結合しただけで実機用output sessionの全経路E2Eと称しない。

## P1: 連続Selfrionette入力のruntime接続

### APIと責務

`build_runtime_input_source_step_loop_plan`は既存LOADCELL_SOURCEを受理する。
取得adapterはsource lifecycleを担い、delta/velocityの数式は選ばない。
`endpoint_delta_to_joint_position/v1`のtyped bindingがRobot-owned local generatorを構築し、
`EndpointDeltaMotionGenerator.update_delta`を明示的に呼ぶ。
`local_endpoint_velocity_to_joint_position/v1`は既存のvelocity積分を使う。
label metadataを書き換えても実行方式は切り替わらない。

Mappingは`runtime_context_parameters`を宣言し、routeの供給集合と一致することをcompositionで検証する。
continuous sourceのselectionでは`current_tip_position_m`を省略でき、placeholderは要求しない。
従来のpure mappingの完全parameter検証は維持する。明示した不正contextや未知fieldは拒否する。
毎step、同じpre-step MuJoCo snapshotから観測した位置をMappingへ渡し、固定weights/gainは変更しない。
欠落、次元違い、非finiteな観測はfail-closedとする。観測値の代わりに0を補わない。

1 planは1 simulatorと1 readerを所有する。step loopはstart/close各1回を担当する。
`pipeline.run_once`を直接使うcallerはreaderのstart/closeを所有する。
両入口は同じpipelineのMapping/context/command executionを通す。表示用annotationとpacingは別責務である。

### 意味と互換性

`loadcell_endpoint_delta/v1`は位置増分/sampleであり、velocityへ読み替えない。
ゼロ入力は現在姿勢を保持し、固定した初期位置へ戻さない。
Robot-ownedな既存local DLS policyとqpos feasibilityを再利用し、数値上限は緩めない。
Mappingの要求は`mapped_endpoint_delta_m`、policy bound後は`endpoint_delta_requested_m`へ分けて記録する。
`motion_policy_v1`がpolicy identity、endpoint norm上限、joint norm上限、FD幅、dampingを保持する。
前者も後者も要求/予測側の値であり、post-stepの`actual_tip_delta_m`とは別である。

従来のabsolute-target smokeは互換のため残すが、continuous routeの証拠とは扱わない。
公開wire schema、物理evidence、既存Robot providerの許可境界は変更しない。
統合CLI、bounded acquisition、protocol peer、contact E2Eは後続P2-P4で扱う。

### 必須検証

複数sample、zero、各軸、model生成1回、state/timeの累積、fixed parameters不変、malformed/EOF cleanupを確認する。
同じsource/Mapping/route/configからのstep loopとrun_onceについて、実際のbackend requestを照合する。
current-tip省略、観測失敗、route-context不一致、偽label、上限跨ぎ、guard rejectを含める。
requested command、candidate prediction、post-step observationを別々にassertする。
既存Gamepad world/tool、replay、R7-Gとarchitectureの回帰を維持する。

## P2: bounded acquisition / health

有限取得policyと状態遷移の正本は`docs/contracts/r7-a-lite-serial-frame-contract.md`。
取得不能を偽sampleへ変換せず、例外で既存sessionを終了する。自動retry/polling frameworkは追加しない。

serial wire形式を変更せず、readerの有限read timeout、1 tick当たりline budget、
最大line bytes、診断保持数、no-vector / EOF / malformed / disconnectを明示する。
数値上限はversioned software test policyとして宣言し、実機cadenceの実測値とは扱わない。
実serialとinjected acquisitionの共通parserを使い、fake serial / clockだけで検証する。
malformedをzero vectorへ変換しない。無信号のhealthと実測zeroを区別する。
neutralやsilent inputで過去のnonzero commandを無期限に再実行しない。
source timestampとhost monotonic receipt timeを別記録し、両時計の絶対値を直接比較しない。
start直後、fresh、stale、invalid、disconnected、close、explicit restartの遷移表をtestで固定する。
既存live APIの互換性変更が必要な場合、Issueに列挙し、勝手なversion driftを起こさない。

## P3: no-I/O protocol peerとbounded observation driver

FastArmのpure `build_fast_arm_joint_wire_command` とgeneric OSC codecを再利用する。
実機joint sign / offsetは未確認のため必須の明示mapping入力とし、fixtureはsyntheticと記録する。
peerは受信byte列からaddress/typetag/argumentを読み、送信側の期待command objectをコピーしない。
独立golden byte oracleでfloat32、joint順序、符号、degree/rad、offsetを検証する。
peerの実装範囲はrepository-owned router observation contractに限定する。
外部routerの実配備互換は別のread-only source確認または実機前preflightを必要とする。

productionのobservation parser/correlation/timeoutを再利用する有限driverを設け、
fake datagram sourceでvalid/wrong target/wrong token/malformed/duplicate/delayed/missingを投入する。
受信producerとtimeout tickのsoftware wiringを#516の前段へ抽出するが、
実socket開始はphysical evidenceとoperator許可を必要とするままとする。
stop/disconnect後の再送、pending中の次command、古いresponseでの解除を禁止する。
疑似responseは常にsynthetic。physical ACK/movement/stopへ昇格しない。

## P4: 統合runner / contact接続 / artifact / audit

CLIはlocal fixture/configと有限実行budgetのみを受け取り、port/host/enable flagを持たない。
GamepadとSelfrionetteを同じscenario envelopeへ包むが、元のwire payloadはそのまま残す。
sourceを取り替えても同じRobotとTask条件をfreezeし、同じcodec境界まで追跡する。
contactは既存scene / contact evidence / task ownerを再利用する。robot qposとscene qposを
addressで照合し、無条件sliceや独立FKを追加しない。
既存quasistatic E2E再実行だけを入力からcontactまでの統合完了とは扱わない。
安全に接続できないsoftware不足はこのgateの未完として記録する。

artifactにはschema/revision/fixture digest、source/mapping/robot/route、時刻、raw signal、
mapped intent、requested joint command、simulation observation、safety reason、
wire bytes/hash、synthetic observation、terminal reason、実行/未実行coverageを保持する。
state、timestamp、missing evidenceを実測として補完しない。
同一revision/config/fixtureの反復でbytes一致を確認し、変更した入力が出力へ伝播することも確認する。
成功の固定値を返す実装が通らないnegative controlと、独立の期待値を含める。

### 受入matrix

| Gate | 正常系 | 必須negative control |
|---|---|---|
| 入力 | Gamepad axes/buttons、7ch vector、連続保持、zero | malformed、非finite、EOF、silent、stale、disconnect |
| motion | 明示写像、同一model、連続state、typed command | missing tip、limit reject、invalid route、初期化し直し |
| wire | joint order/sign/offset/unit、OSC float32 | mapping欠落、次元差、非finite、誤ったtypetag |
| response | synthetic correlation、有限tick | wrong target/token、timeout、duplicate、stop後response |
| contact | scene identityとraw measured task evidence | no contact、invalid evidence、unrelated contact、失敗を成功へ変換しない |
| isolation | in-memory peerのみ | socket/serial/DNSをtripwireで禁止、physical gate継続拒否 |
| artifact | strict decode、再生成一致、revision追跡 | 改ざん、truncation、wrong revision、missing records |

## 不明点台帳と停止条件

| 不明点 | 扱い | 解除根拠 |
|---|---|---|
| 実機joint sign / zero / offset / limit | unknown。physical config生成禁止 | #509の資料・実測と受入 |
| loadcell各channelの指・力との対応、scale/noise | fixture mappingのみ | 実入力装置の校正・計測 |
| 実配備router/controller revisionとresponse | emulatorはrepo contractのみ | pinned source確認とreceiver preflight |
| 実移動軌道・非常停止・力安定性 | software合格から推論しない | #509/#516/#517/#518 |
| 未対応のsource/route/contact結線 | software blocker | 当該Issueの実装・回帰 |
| 独立clean-room reviewer | 未実行なら未実施 | fresh-context reviewer実行証拠 |

scope内で決められるのはsoftware contractとsynthetic test policyであり、これらを
実物の仕様だと推論しない。資料不足はnull/reason/blockedとして記録する。
新しい不明なprotocolや実機値が必要になった箇所は停止し、他の独立作業を継続する。

## 実行順と監査

詳細設計 -> Issueとnumbering SoT -> P1 -> P2 -> P3 -> P4 -> Draft PR -> fixed-SHA audit。
各PRは独立にreview可能な差分とし、依存PRの未merge時はstackを明示する。
clean checkoutでの再検証、実装者の再読、独立fresh-context監査を別の証拠として記録する。
独立reviewerを利用できない場合、clean checkoutが通っても独立clean-room PASSと書かない。
merge、Issue close、branch削除はこの依頼の実行権限に含めない。

## 完了後にも必要なphysical validation

#509のbounded safety測定、#516 gamepad、#517 Selfrionette、#518接触、#519 handoffは残る。
これらをSIL結果で完了にしない。P1-P4にsoftware未完があれば「残りは実機だけ」と報告しない。
実機calibrationの結果で追加実装が必要になる可能性も、完了報告の既知制約として残す。

## 追跡先

R7-L親: #539。P1 #540、P2 #541、P3 #542、P4 #543。
P1は連続input / delta-routeの実装対象。P2-P4の完成は個別acceptanceで判定する。
