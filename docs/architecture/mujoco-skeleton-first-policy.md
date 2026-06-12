MuJoCo移行における Skeleton-First 方針

目的

Selfrionette の MuJoCo 移行では、既存実装を少しずつ置き換えるのではなく、先に責務境界を固定したスケルトンを作成し、その後に各層の実装を埋めていく。

過去の実装では、動く機能を優先して追加した結果、入力、運動生成、運動学、物理エンジン、表示、通信の責務が徐々に混在した。これにより、後から修正するたびに構造がズレ、座標系・関節意味論・表示状態の不整合が発生した。

本方針では、最初に構造を固定し、実装が構造を侵食しないようにする。

基本方針

MuJoCo移行は skeleton-first で進める。

最初の目標は、シミュレータを動かすことではない。
最初の目標は、責務の漂流を防ぐことである。

実装は次の順序で行う。

Step 1:
  完全なスケルトンを作る
Step 2:
  各層に stub 実装を入れる
Step 3:
  stub 同士を runtime で結線する
Step 4:
  その後、各 stub の中身を 1 つずつ実装する

この順序を崩してはならない。

採用する全体構造

input_sources
  → input_interpreters
  → motion
  → kinematics
  → mujoco_backend
  → transport
  → apps/mujoco-viewer

ただし、各層を直接数珠つなぎにするのではなく、実際の結線は runtime が行う。

runtime
  - InputSource を選択する
  - InputInterpreter を選択する
  - MotionGenerator を選択する
  - MuJoCo backend を起動する
  - Transport を起動する
  - 全体のループを管理する

レイヤー一覧

schemas/

共通データ構造を定義する層。

主な型:

RawInputFrame
InputIntent
TargetCommand
JointCommand
MotionCommand
MuJoCoState
RenderState

ルール:

- schemas はどの層にも依存しない
- 各層は schemas を参照してよい
- 層間の受け渡しは原則として schemas の型を使う

input_sources/

Arduino、キーボード、ゲームパッド、ログリプレイ、OSC、mocap などから入力値を取得する層。

責務:

- デバイスまたはログから値を読む
- RawInputFrame を生成する

禁止:

- IK を行う
- target を更新する
- joint angle を生成する
- MuJoCo を操作する
- Three.js 表示を意識する

input_interpreters/

RawInputFrame を操作意図へ変換する層。

責務:

RawInputFrame
  → InputIntent

例:

keyboard W
  → target +x direction
gamepad stick
  → target delta vector
loadcell
  → force or direction intent
replay
  → recorded intent

禁止:

- IK を行う
- MuJoCo に渡す qpos や ctrl を作る
- Three.js 表示形式を作る

motion/

入力意図から運動指令を生成する層。

責務:

InputIntent
  → TargetCommand
  → JointCommand
  → MotionCommand

含めてよい処理:

- target 位置更新
- workspace 制限
- 速度制限
- 安全制限
- IK 呼び出し
- joint command 生成

禁止:

- MuJoCo の model/data を直接操作する
- WebSocket 送信を行う
- Three.js 用の transform を作る

kinematics/

純粋な運動学を扱う層。

責務:

- FK
- IK
- joint limit
- joint convention
- motor_space / joint_space 変換

禁止:

- 入力デバイスを読む
- MuJoCo の data.qpos や data.ctrl を直接触る
- WebSocket 通信を行う
- Three.js 表示を行う

mujoco_backend/

MuJoCo を物理状態の Source of Truth として扱う層。

責務:

MotionCommand / JointCommand
  → MuJoCo qpos / ctrl
  → mj_forward / mj_step
  → MuJoCoState

含めてよい処理:

- XML / MJCF ロード
- model / data 管理
- qpos 反映
- ctrl 反映
- mj_forward
- mj_step
- body / site transform 取得
- contact 取得
- MuJoCoState 生成

禁止:

- Arduino やキーボードなどの入力を直接読む
- InputInterpreter を直接呼ぶ
- Three.js の描画処理を持つ
- runtime に依存する

transport/

通信と記録を扱う層。

責務:

MuJoCoState
  → JSON
  → WebSocket

含めてよい処理:

- WebSocket 送信
- JSON schema 変換
- replay recording
- frame logging

禁止:

- IK を行う
- target を更新する
- MuJoCo step を行う
- 入力デバイスを読む

runtime/

全体を結線する composition root。

責務:

- config 読み込み
- 入力 source の選択
- interpreter の選択
- motion generator の選択
- MuJoCo backend の生成
- transport の生成
- main loop の管理

ルール:

- 複数層を結線してよいのは runtime のみ
- 各層の実装は runtime に依存してはならない

apps/mujoco-viewer/

Three.js による表示層。

責務:

- MuJoCoState を受け取る
- STL / mesh を表示する
- body / site transform を mesh に適用する
- target marker を表示する
- wrist / tip marker を表示する
- error vector を表示する
- joint ring を表示する
- debug overlay を表示する

禁止:

- アーム FK を再計算する
- IK を実装する
- 入力から joint angle を生成する
- MuJoCo step を行う
- Rapier physics を新系統に持ち込む

Three.js は描画層であり、物理状態の Source of Truth ではない。

Source of Truth

新系統では MuJoCo を物理状態の Source of Truth とする。

正:
  MuJoCo model / data
    → body transform
    → site transform
    → MuJoCoState
    → Three.js 表示
誤:
  MuJoCo
  FK
  Three.js hierarchy
  Rapier body
  PoseState
  がそれぞれ別々に姿勢を持つ

Three.js 側でアーム姿勢を再計算してはならない。
Three.js は MuJoCo から送られた transform を表示するだけにする。

依存方向

許可される依存方向は以下とする。

schemas
  ↑
input_sources
input_interpreters
kinematics
motion
mujoco_backend
transport
  ↑
runtime

具体的には以下を許可する。

input_sources       → schemas
input_interpreters  → schemas
motion              → schemas, kinematics
kinematics          → schemas
mujoco_backend      → schemas
transport           → schemas
runtime             → all layers

禁止依存:

input_sources       → motion
input_sources       → kinematics
input_sources       → mujoco_backend
input_sources       → transport
input_sources       → runtime
kinematics          → input_sources
kinematics          → mujoco_backend
kinematics          → transport
kinematics          → runtime
mujoco_backend      → input_sources
mujoco_backend      → input_interpreters
mujoco_backend      → runtime
transport           → input_sources
transport           → input_interpreters
transport           → motion
transport           → kinematics
transport           → mujoco_backend
transport           → runtime

初期スケルトン作成時の完了条件

最初の architecture lock PR では、以下を完了条件とする。

- ディレクトリ構造が作成されている
- 各層に README が存在する
- 各層に責務と禁止事項が明記されている
- schemas に主要 dataclass が存在する
- input_sources / input_interpreters / motion / mujoco_backend / transport に Protocol または stub が存在する
- runtime に stub 同士を結線する場所が存在する
- apps/mujoco-viewer に表示層の空スケルトンが存在する
- import boundary test が存在する
- 既存 Rapier viewer を変更していない
- 既存 PoseState 中心設計を新系統へ持ち込んでいない

このPRでは、動作完成を求めない。

実装PRのルール

実装PRは、必ず既存スケルトンのいずれかの層に収める。

悪い例:

入力 source の実装中に IK を書く
MuJoCo backend の実装中に WebSocket を書く
Three.js viewer の実装中に FK を書く
motion 層の実装中に data.qpos を直接操作する

良い例:

input_sources/replay.py
  RawInputFrame を返すだけ
input_interpreters/replay_mapper.py
  RawInputFrame を InputIntent に変換するだけ
motion/motion_generator.py
  InputIntent を MotionCommand に変換するだけ
mujoco_backend/command_adapter.py
  MotionCommand を qpos / ctrl に反映するだけ
mujoco_backend/state_builder.py
  MuJoCo data から MuJoCoState を作るだけ
transport/websocket_server.py
  MuJoCoState を送るだけ
apps/mujoco-viewer/src/viewer/arm_renderer.ts
  MuJoCoState の transform を mesh に適用するだけ

移行対象の扱い

既存資産は次の2種類に分ける。

assets/
  採用するモデル、STL、XML、MJCFなど
legacy/
  参照用として保存する既存コード

legacy 配下のコードは直接 import しない。
必要なロジックは、責務単位で新しい層へ移植する。

Rapier の扱い

MuJoCo移行系統では、Rapierを物理エンジンとして使用しない。

Rapier既存実装は、比較用または旧viewerとして隔離する。
新しい MuJoCo + Three.js 系統へ Rapier の body、collider、joint、world を持ち込んではならない。

PoseState の扱い

既存の PoseState は旧viewer互換やログ互換のために参照してよいが、新しい MuJoCo 系統の中心には置かない。

新系統の中心は以下とする。

MotionCommand
  → MuJoCo backend
  → MuJoCoState
  → Three.js viewer

必要な場合のみ adapter を用意する。

MuJoCoState
  → PoseState compatibility adapter

ただし、この adapter は新系統の内部SoTにしてはならない。

開発順序

Step 1: 完全なスケルトンを作る

目的:

責務境界を固定する

作るもの:

- ディレクトリ
- README
- dataclass
- Protocol
- stub
- import boundary test
- architecture docs

Step 2: 各層に stub 実装を入れる

目的:

各層の入出力を固定する

例:

ReplayInputSource stub
FixedInputInterpreter stub
FixedMotionGenerator stub
DummyMuJoCoSimulator stub
DummyStatePublisher stub

Step 3: stub 同士を runtime で結線する

目的:

システム全体の流れを壊さずに確認する

この段階では、実際の MuJoCo 動作や Three.js 表示は完成していなくてよい。

Step 4: 各 stub の中身を 1 つずつ実装する

目的:

構造を保ったまま機能を増やす

実装順序の例:

1. ReplayInputSource
2. InputInterpreter
3. MotionGenerator
4. MuJoCo model loader
5. MuJoCo command adapter
6. MuJoCo state builder
7. WebSocket transport
8. Three.js viewer
9. Arduino input
10. keyboard input
11. gamepad input
12. logging / replay

最重要原則

動くものを早く作ることより、
ズレない構造を先に作ることを優先する。
実装はスケルトンに従う。
スケルトンを実装に合わせて崩してはならない。
Three.js は描画層。
MuJoCo は物理層。
Selfrionette core は入力・運動生成層。
runtime は結線層。