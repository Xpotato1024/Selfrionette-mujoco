# Selfrionette MuJoCo移行 開発方針

## 目的

Selfrionette の新系統では、既存の Rapier + Three.js 実装を前提に修理を重ねるのではなく、MuJoCo を物理状態の Source of Truth とし、Three.js を表示層として用いる構成へ移行する。

この移行では、最初に動くものを急いで作るのではなく、先にディレクトリ、型、抽象インターフェース、依存方向、禁止事項を固定する。過去の実装で発生した「実装を追加するたびに責務境界がズレる」問題を防ぐことを最優先にする。

## 基本方針

```text
Step 1:
  完全なスケルトンを作る

Step 2:
  各層に stub 実装を入れる

Step 3:
  stub 同士を runtime で結線する

Step 4:
  その後、各 stub の中身を 1 つずつ実装する
```

この順序を崩してはならない。

特に、次のような「ついで実装」を禁止する。

```text
- 入力 source を作るついでに IK を書く
- IK を移植するついでに MuJoCo data.qpos を直接触る
- MuJoCo backend を作るついでに WebSocket を書く
- Three.js viewer を作るついでに FK を再実装する
- 旧 PoseState 互換のために新系統の SoT を曖昧にする
```

## 新系統の責務分離

新系統は以下の責務で分離する。

```text
schemas
  共通データ構造

input_sources
  Arduino / keyboard / gamepad / replay / OSC / mocap などから RawInputFrame を読む

input_interpreters
  RawInputFrame を InputIntent に変換する

motion
  InputIntent から TargetCommand / JointCommand / MotionCommand を生成する

kinematics
  FK / IK / joint limit / joint convention / motor_space-joint_space 変換を扱う

mujoco_backend
  MuJoCo model/data を管理し、MotionCommand を qpos/ctrl に反映し、MuJoCoState を生成する

transport
  MuJoCoState の JSON 化、WebSocket 送信、ログ記録を扱う

runtime
  各層を結線する composition root

apps/mujoco-viewer
  Three.js による表示層
```

## Source of Truth

新系統の物理状態の Source of Truth は MuJoCo とする。

```text
正:
  MuJoCo model/data
    → body/site transform
    → MuJoCoState
    → Three.js rendering

誤:
  MuJoCo
  Python FK
  Three.js hierarchy
  Rapier body
  PoseState
  が別々に姿勢を持つ
```

Three.js は描画層であり、アーム FK を再計算してはならない。Three.js は MuJoCoState に含まれる body/site transform を表示するだけにする。

## Rapier の扱い

MuJoCo 移行系統では、Rapier を物理エンジンとして使用しない。

既存の Rapier viewer は比較用または旧系統として隔離する。新しい MuJoCo + Three.js 系統へ Rapier の world、body、collider、joint を持ち込んではならない。

## PoseState の扱い

既存の PoseState は旧 viewer 互換やログ互換のために参照してよいが、新系統の中心には置かない。

新系統の中心は以下とする。

```text
MotionCommand
  → MuJoCo backend
  → MuJoCoState
  → Three.js viewer
```

必要な場合のみ adapter を用意する。

```text
MuJoCoState
  → PoseState compatibility adapter
```

ただし、この adapter を新系統内部の Source of Truth にしてはならない。

## 既存資産の扱い

既存資産は、採用資産と参照資産に分ける。

```text
assets/
  採用する XML / MJCF / STL / mesh など

legacy/
  参照用として保存する既存コード
```

legacy 配下のコードを直接 import してはならない。必要なロジックは、責務単位で新しい層へ移植する。

## 初期PRの目的

最初の PR は、機能実装ではなく architecture lock PR とする。

目的は以下である。

```text
- ディレクトリ構造を固定する
- 各層の責務を固定する
- 型と Protocol を固定する
- import boundary test を追加する
- legacy 資産と assets 資産の置き場所を固定する
- 実装が構造を侵食しないようにする
```

最初の PR では、シミュレータが動作する必要はない。

## PR運用方針

1つの PR は、1つの成果物に対応させる。

良い PR:

```text
- skeleton と boundary test だけを追加する
- replay input source stub だけを追加する
- MuJoCo model loader だけを追加する
- state builder だけを追加する
- Three.js renderer skeleton だけを追加する
```

悪い PR:

```text
- 入力、IK、MuJoCo、WebSocket、Three.js を一度に実装する
- 旧 viewer の修正と新 viewer の実装を混ぜる
- 設計変更と機能追加を混ぜる
- テストを通すために責務境界を崩す
```

## Validation方針

最初から完全な機能テストを求めない。代わりに、構造を守るための validation を先に置く。

初期 validation:

```text
- import boundary test
- schema serialization test
- layer README existence test
- model path existence test
- name map consistency test
```

機能実装後の validation:

```text
- MuJoCo model load test
- qpos apply + mj_forward test
- site/body snapshot test
- WebSocket JSON schema test
- Three.js type check
- replay pipeline smoke test
```

## 実機・安全・外部接続の扱い

初期移行では、実機接続を行わない。

禁止:

```text
- serial port open
- Arduino upload
- 実機への OSC send
- motor actuation
- hardware validation
- safety-control 変更
- secrets / credentials / deployment keys へのアクセス
```

実機接続は、MuJoCo + Three.js のソフトウェア経路が安定してから、別 Phase または手動 gate 付き Round として扱う。

## 最重要原則

```text
動くものを早く作ることより、ズレない構造を先に作ることを優先する。
```

```text
実装はスケルトンに従う。
スケルトンを実装に合わせて崩してはならない。
```

```text
Three.js は描画層。
MuJoCo は物理層。
Selfrionette core は入力・運動生成層。
runtime は結線層。
```
