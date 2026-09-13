---
status: canonical
owner: runtime
last_verified: 2026-09-13
canonical_for:
  - contact-task-log/v1 trial artifact and contact presentation metadata
related:
  - docs/contracts/contact-task-manifest.md
  - docs/contracts/virtual-reaction-force.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
---

# contact-task-log/v1の試行記録と表示契約

## 目的と責務

`runtime/contact/log.py`は1 trial分のcontact evidence、派生force、Task observation / state、最終outcomeを束ねる明示的なartifact contractを所有する。`experiment-motion-log/v1`とは別schemaであり、既存log schemaの変更や汎用motion streamへのcontact混入を行わない。

logは`ContactTaskManifest`、trial identity、`VirtualReactionForceManifest`へbindingされる。raw contact evidence、`virtual-reaction-force/v1` signal、Task outcomeは別々のtyped valueとして保存する。`ContactTaskOutcome`とsummary outcomeは#415の契約どおりraw evidenceから決まり、derived filter後のsignalから再判定しない。

default runtimeはartifactを作成・書込みしない。呼出側が`ContactTaskLogRecorder`を明示的に使い、completeしたlogを`write_contact_task_log`へ渡す。

## バージョン付きレコード列と識別子

schemaは`contact-task-log/v1`、integer contract versionは`1`である。source kindは`runtime_capture`または`synthetic_fixture`であり、後者は表示時にもsynthetic evidenceとして識別する。

JSONLのrecord順は固定である。

1. `header`: contact manifestとそのdigest、task context、trial、robot bundle、scene / object / presentation identity、force manifestとそのdigest、source kindを持つ。
2. 1件以上の`sample`: zero-based連続`sequence_index`、elapsed time、raw contact evidence、derived force signal、Task observation、Task stateを持つ。
3. `summary`: sample countと同じmanifest / trialに結び付いたTask outcomeを持つ。

`header.binding`はmanifest digest、signal manifest digest、trial、robot bundle、scene / object / presentation identity、source kindをcanonicalな値で繰り返す。各sampleとsummaryも同じbindingを持ち、decoderは全recordのidentity、count、order、cross-field consistencyを検証する。summary outcomeのtask条件（`dwell_interval_s`、`timeout_s`、`target_normal_force_band_n`、`approach_alignment_min_cosine`、`normal_alignment_min_cosine`、`max_contact_location_drift_m`、`require_pose_measurement`）は`header.task_context`と一致しなければならない。manifest、signal manifest、raw evidence、derived signal、Task state / outcomeのいずれかを別trialの値と差し替えても受け付けない。

## 末尾sample、summary、raw forceの整合性

各`virtual-reaction-force/v1` sampleの`raw_force_world_n`は、そのsampleのraw evidenceにある`aggregate.object_on_tool_force_world_n`の完全なcopyである。`active`および`no_contact` signalでは値が必須で、値がある場合はraw aggregateとcomponentごとに完全一致しなければならない。filterや出力変換後のforceは別の値として保持する。

`task_state`とsummaryの`outcome`は既知のphase / classification enumと整合する。success / failure / technical-invalidには対応するterminal phaseが必要で、failureとtechnical-invalidにはreasonを必須とする。summaryは末尾sampleのterminal stateとphase、classification、reasonが一致しなければならない。record済みsampleを追加しない有限streamの確定時だけ、末尾sampleがrunningのままsummary outcomeがfailureとなるfinalizer形式を許可する。

successful outcomeは末尾`task_state`がsuccessで、末尾raw evidenceが測定済みかつtarget contactを含む場合だけ有効である。no-contact evidenceからsuccessful outcomeを成立させてはならない。outcome判定と`target_normal_force_band_n`の評価元は#415のraw evidence契約であり、viewerはそれを再計算しない。`target_normal_force_band_n`は任意値であり、`null`も正当な設定としてheaderとoutcomeに保存できる。

## 決定的なJSONL形式と保存

serializationはcanonical UTF-8 JSONを1行1recordで出力し、最後にLFを1つ置く。BOM、CR、重複JSON key、unknown field / enum / version、non-finite number、record順・sequence index・binding不一致はstrict decoderが拒否する。読込後の型付きrecordを再encodeしたbytesが入力と完全一致することをread-back gateとする。

`write_contact_task_log`は既存directoryを要求し、write_contact_task_logは既存ディレクトリ内の一時ファイルへ書き込み、fsync後に保存bytesをstrict decoderで検証してから公開する。既定のoverwrite=Falseでは同じディレクトリ上でhard linkを作成して排他的に公開するため、並行する別writerが先に作成した出力先は上書きしない。hard linkをatomicに作成できないファイルシステムでは代替手段へ切り替えず失敗させる。overwrite=Trueの場合だけos.replaceで出力先をatomicに置換する。生成basenameはtrial IDの短いSHA-256 fingerprintとrepetition / attempt indexから決まり、raw trial IDをpathへ埋め込まない。

## payload metadataへの投影

`runtime/contact/presentation.py`の`build_contact_task_presentation_v1`はlogから選択したsampleを描画用DTOへ投影する。MuJoCo state、contact solver、force transform / filter、Task判定を再実行しない。`contact_task_payload_metadata_v1`は`metadata.contact_task_v1`に対応するoptional valueを返す。

callerは**同じ**`MuJoCoState` snapshotの`time_s`と`frame_index`を用いてpresentationを組み立て、結果を`state.metadata`へmergeしてから通常の`mujoco_state_to_payload`を呼ぶ。これによりqpos、time、frame、contact presentationは同じsnapshotに由来する。別々のrecordingからqposとcontactを合成して同期済みとみなしてはならない。log自身にはrobot qposを複製しない。

presentation bindingにはcontact / signal manifest digest、trial、robot bundle、scene / object / presentation identityを保持する。payload time / frameからsample ageを評価し、unsupported identity、未来sample、age上限超過、invalid measurement / signal、欠落したbackend object poseは`unavailable`または`stale`となる。

contact logにはrobot qposを複製しない。ContactSceneのfull qposにobject freejointが含まれる場合のloaded Robot modelとの対応は、payload-v0の別optional `metadata.contact_scene_robot_qpos_v1`で表す。producerは`schema_version: "contact-scene-robot-qpos/v1"`を付け、resolved `RobotProfile`と同一snapshotの実MuJoCo modelからcanonical joint name順のqpos addressを解決し、scene / manifest / frame / timeとprofile / model identityを結び付ける。viewerはこのmappingと同じsampleの`contact_task_v1` bindingを検証してから必要なjoint値だけをloaded profile modelへ適用する。欠落、stale、replayed sample、identity / dimension / address不一致はfail-closedとし、full qposを切り詰めたり第二のqpos列を作ったりしない。このextensionがない従来payloadは既存のexact-length validationを維持する。

## Viewerの表示境界

`apps/mujoco-viewer`はpayload metadataまたは明示的なlocal file inputからpresentationを厳密に読み、登録済み・現在load済みrobot profileと比較する。viewerはstatusが`available`の間、cube geometry / pose、contact point / normal、world raw force、frame情報付きderived force、Task state、raw-evidence outcomeをread-onlyに表示する。derived-force statusは`active`、`no_contact`、`measurement_unavailable`、`invalid`、`stale`に限り、raw evidenceの`invalid_contact` / `solver_invalid`をderived statusとして受け付けない。derived forceを3D矢印にするのは`mujoco_world` frameの場合だけであり、tool / device-neutral vectorをworld vectorとして再解釈しない。

状態の扱い:

| 状態 | 表示 |
|---|---|
| `available` | bindingとageの検証に通ったsampleの表示 |
| `stale` | force overlayとderived force displayを消去し、statusをstaleとする。raw logの過去recordは証拠として保持する |
| `unavailable` | contact overlayを消去し、reasonを表示する |
| missing / malformed / mismatched | unavailableとして処理し、前回のforce overlayを残さない |

statusが`available`でない場合、viewerは派生反力・現在のtask state・raw-evidence outcomeを表示せず、raw log内の過去record自体は変更しない。

offline `contact-task-log/v1`にはqposがないため、そのposeと現在のviewer poseの時刻同期は保証しない。同期したscene displayには、same-snapshotのqposを含むpayload-v0と`metadata.contact_task_v1`を使う。synthetic fixtureは合成であることを常に表示し、MuJoCo captureへ昇格させない。

## 非目標

このcontractはforce device選定、device mapping、OSC、network、serial、Arduino、robot output、actuator control、物理接触の追加計算、participant study、stability / physical safety claimを含まない。`runtime/contact`とMuJoCo backendが物理状態のSoTであり、Three.jsは受け取った値だけを描画する。
