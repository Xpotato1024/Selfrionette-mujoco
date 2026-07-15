---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - skeleton structure
  - layer responsibilities
related:
  - docs/architecture/development-policy.md
  - docs/architecture/dependency-boundaries.md
---

# MuJoCo skeleton-first仕様

## source of truth

MuJoCoはphysical stateのsource of truthである。Three.jsはrenderingだけを担当する。`runtime/`は唯一の
composition rootである。schemasはlayer contractを定義する。legacyは参照専用である。assetsはmodel
assetである。transportはserializationとdeliveryだけを担当する。

正しいflow:

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> Three.js display
```

禁止する構造:

```text
MuJoCo
FK
Three.js hierarchy
Rapier body
old PoseState
any duplicate arm-pose source of truth
```

## layer

### `schemas/`

`RawInputFrame`、`InputIntent`、`TargetCommand`、`JointCommand`、`MotionCommand`、
`MuJoCoState`、`RenderState`などのshared data contractを定義する。他のlayerへ依存してはならない。

### `input_sources/`

Arduino、keyboard、gamepad、replay、OSC、mocapの値を読み、`RawInputFrame`を返す。IK、target update、
joint generation、MuJoCo operation、WebSocket send、Three.js transformを実行してはならない。

### `input_interpreters/`

deadzone、scaling、button meaning、source-specific interpretationを含め、`RawInputFrame`を
`InputIntent`へ変換する。IK、target update、qpos/ctrl generation、MuJoCo operation、render transformを
実行してはならない。

### `motion/`

target update、workspace limit、speed limit、safety limit、IK call、command generationを含め、
`InputIntent`を`MotionCommand`へ変換する。MuJoCo model/dataを直接操作せず、WebSocket messageを送らず、
Three.js transformを生成せず、input deviceを読まない。

### `kinematics/`

pure FK、IK、joint limit、joint convention、motor/joint-space conversionを持つ。deviceを読まず、
MuJoCo dataを操作せず、WebSocket通信やThree.js renderingを行わず、runtimeへ依存しない。

### `mujoco_backend/`

MJCF/XMLをloadし、model/dataを管理し、qpos/ctrlを適用し、`mj_forward`と`mj_step`を実行し、
body/site transformとcontact dataを抽出して`MuJoCoState`を構築する。input deviceを読まず、interpreterを
呼ばず、runtimeへ依存せず、Three.js renderingやWebSocket server ownershipを持たない。

### `transport/`

`MuJoCoState`をserializeして送信し、frame logとreplay dataを記録する。IK、target update、MuJoCo step、
input device read、renderingを行わない。transportはpayload deliveryだけを担当し、physics stateを所有しない。

### `runtime/`

唯一のcomposition rootである。config load、input source、interpreter、motion generator、MuJoCo backend、
transportの選択とmain loop管理を行える。他のlayerはruntimeへ依存してはならない。

### `apps/mujoco-viewer/`

Three.js rendering layerである。`MuJoCoState`を受け取り、body/site transformをmesh、marker、overlayへ
適用する。FK、IK、joint generation、MuJoCo step、Rapier physicsを実装してはならない。

## Step 5-0 parallel work contract

このIssueでは、source of truthを分裂させず次の作業を並行できるcontractを固定した。

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> viewer rendering
```

規則:

- data flowとimport dependencyは同じではない
- 複数layerをcomposeできるのはruntimeだけである
- viewer、transport、input、IKはMuJoCo backendを直接composeしない
- viewerは`MuJoCoState`またはtransport payloadをrenderし、独自のphysics stateを作らない
- MotionCommand、MuJoCoState、transport payload、viewer、input/IK contractは`docs/contracts/`で固定する
- このIssueではimplementation behaviorを追加しない

## stub policy

Step 2ではschema dataclass、layer `Protocol`定義、NoOp / static stubを定義済みlayerへ追加した。stub fileは
正しいlayer内に置き、dependency ruleを迂回してはならない。runtime compositionはStep 3までscope外だった。

Step 3では`StaticInputSource` -> `NoOpInputInterpreter` -> `NoOpMotionGenerator` ->
`NoOpMuJoCoSimulator` -> `NoOpStatePublisher`を接続した。実際のMuJoCo、WebSocket、Three.js、device
input behaviorは導入しなかった。Step 4ではstub implementationを一つずつ置換した。

### Step 4-B

このIssueでは最初のheadless MuJoCo backend sliceを追加した。

- canonical model path: `assets/mujoco/fast_arm/scene.xml`
- sceneは`mujoco_backend`だけでloadする
- joint、body、site nameだけをinspectする
- loaderをruntimeへまだ接続しない
- `MuJoCoState` snapshotは構築しない。これは#10にreservedする

### Step 4-C

このIssueではheadless `MuJoCoState` snapshot sliceを追加した。

- `mujoco_backend`だけで`MjModel` / `MjData`から`MuJoCoState`を構築する
- dataを読む前に`mj_forward`を呼ぶ
- `mj_step`は呼ばない
- body transformを`BodyTransform`へmapする
- site transformを`SiteTransform`へmapする
- quaternionは`wxyz`で保存する
- snapshot sliceはまだruntimeへ接続しない

### Step 4-D

このIssueでは実際のheadless MuJoCo backendを使うruntime entryを追加した。

- stub wiring check用に`build_noop_pipeline()`を維持する
- headless backendを`RuntimePipeline`へcomposeする`build_mujoco_pipeline()`を追加する
- model pathがない場合は`assets/mujoco/fast_arm/scene.xml`を既定値にする
- `apply_command()`はcommand retentionだけを行う
- `step(dt_s)`はframe index bookkeepingだけを行う
- `mj_step`は呼ばない
- `snapshot()`から`MuJoCoState`を返す
- motion-to-qpos/ctrl、transport、viewer、hardwareは後続Issueへdeferする

### Step 5-D

このIssueではheadless backendへ最初の実command-to-simulation bridgeを追加した。

- `MotionCommand.joint`をMuJoCo `qpos`へ直接反映する
- backendのMuJoCo model joint orderとjoint `qpos` addressを使う
- `mj_step`を呼び、`data.time`とsimulation stateを進める
- actuator ctrl、PID、controller、IK、input、transport、viewerはscope外に保つ
- 進行後のbackend stateから`MuJoCoState` snapshotを構築する

### Step 5-0

このIssueではinput、motion、IK、transport、viewer作業向けのparallel work contractを固定し、新しいbehaviorは
追加しなかった。後続stepを実装するときは`docs/contracts/`配下のcanonical contractを使用する。
