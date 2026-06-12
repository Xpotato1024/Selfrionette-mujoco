# Selfrionette MuJoCo移行 詳細仕様

## 1. 目的

この文書は、Selfrionette の MuJoCo + Three.js 新系統を実装するための詳細仕様を定義する。

今回の移行では、既存の Rapier viewer を逐次修正するのではなく、MuJoCo を物理状態の Source of Truth とする新しい構造を作成する。

主な目的は以下である。

```text
- 入力抽象化を固定する
- 入力から運動生成までの責務を固定する
- MuJoCo への接続責務を固定する
- Three.js 表示層を描画専用に固定する
- 旧 Selfrionette で発生した責務混在を再発させない
```

## 2. 開発順序

実装順序は以下とする。

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

この順序を守る理由は、過去の実装では機能追加のたびに責務境界が崩れ、入力、運動学、物理、表示、通信が混ざったためである。

## 3. 推奨ディレクトリ構造

```text
Selfrionette/
  AGENTS.md

  assets/
    mujoco/
      fast_arm/
        README.md
        arm.xml
        scene.xml
        meshes/
          BaseLink.stl
          SholderLink1.stl
          SholderLink2.stl
          UpperArmLink.stl
          ForeArmLink.stl

  legacy/
    fast_arm_control/
      README.md
      ...既存zip展開物...

  docs/
    architecture/
      development-policy.md
      mujoco-skeleton-first-spec.md
      dependency-boundaries.md
      data-flow.md

  src/
    selfrionette/
      schemas/
        __init__.py
        input_frame.py
        input_intent.py
        target_command.py
        joint_command.py
        motion_command.py
        mujoco_state.py
        render_state.py

      input_sources/
        __init__.py
        README.md
        base.py
        arduino_serial.py
        keyboard.py
        gamepad.py
        replay.py
        osc.py
        mocap.py

      input_interpreters/
        __init__.py
        README.md
        base.py
        arduino_mapper.py
        keyboard_mapper.py
        gamepad_mapper.py
        replay_mapper.py
        osc_mapper.py

      motion/
        __init__.py
        README.md
        motion_generator.py
        target_updater.py
        constraints.py
        safety_limits.py

      kinematics/
        __init__.py
        README.md
        fast_arm_kinematics.py
        ik_controller.py
        joint_convention.py
        joint_limits.py

      mujoco_backend/
        __init__.py
        README.md
        model_paths.py
        name_map.py
        model_loader.py
        simulator.py
        command_adapter.py
        state_builder.py

      transport/
        __init__.py
        README.md
        websocket_schema.py
        websocket_server.py
        recorder.py

      runtime/
        __init__.py
        README.md
        config.py
        pipeline.py
        main_mujoco_server.py

  apps/
    mujoco-viewer/
      README.md
      package.json
      vite.config.ts
      src/
        main.ts
        types/
          input_intent.ts
          motion_command.ts
          mujoco_state.ts
          render_state.ts
        transport/
          websocket_client.ts
        viewer/
          scene.ts
          camera.ts
          lights.ts
          mesh_loader.ts
          transform.ts
          arm_renderer.ts
          markers.ts
          joint_rings.ts
          error_vector.ts
          debug_overlay.ts
        ui/
          control_panel.ts
          debug_panel.ts

  tests/
    architecture/
      test_import_boundaries.py
      test_layer_readmes_exist.py

    schemas/
      test_schema_serialization.py

    mujoco_backend/
      test_model_paths.py
      test_name_map.py

  scripts/
    dev-mujoco.ps1
    dev-mujoco.sh
```

## 4. レイヤー責務

### 4.1 `schemas/`

共通データ構造を定義する層。

この層は、どの層にも依存してはならない。各層は `schemas` を参照してよい。

主な型:

```text
RawInputFrame
InputIntent
TargetCommand
JointCommand
MotionCommand
MuJoCoState
RenderState
```

#### `RawInputFrame`

入力 source から出る最も低レベルのフレーム。

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class RawInputFrame:
    source: str
    timestamp: float
    values: tuple[float, ...]
    buttons: tuple[bool, ...] = ()
    meta: dict[str, object] = field(default_factory=dict)
```

#### `InputIntent`

入力値を意味に変換したもの。

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class InputIntent:
    source: str
    timestamp: float
    target_delta: tuple[float, float, float] | None = None
    joint_delta: tuple[float, float, float, float] | None = None
    buttons: tuple[str, ...] = ()
    meta: dict[str, object] = field(default_factory=dict)
```

#### `TargetCommand`

target 更新指令。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TargetCommand:
    position: tuple[float, float, float]
    velocity: tuple[float, float, float] | None = None
```

#### `JointCommand`

関節角指令。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class JointCommand:
    joint_angles_rad: tuple[float, float, float, float]
    joint_velocities_rad_s: tuple[float, float, float, float] | None = None
```

#### `MotionCommand`

MuJoCo backend に渡す上位指令。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class MotionCommand:
    timestamp: float
    target: TargetCommand | None = None
    joint: JointCommand | None = None
    mode: str = "joint"
```

#### `MuJoCoState`

MuJoCo backend から出る状態 snapshot。

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TransformState:
    name: str
    position: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]

@dataclass(frozen=True, slots=True)
class ErrorState:
    from_site: str
    to_target: str
    vector: tuple[float, float, float]
    norm: float

@dataclass(frozen=True, slots=True)
class MuJoCoState:
    frame: int
    time: float
    qpos: tuple[float, ...]
    qvel: tuple[float, ...]
    bodies: tuple[TransformState, ...]
    sites: tuple[TransformState, ...]
    target_position: tuple[float, float, float] | None = None
    error: ErrorState | None = None
```

### 4.2 `input_sources/`

Arduino、キーボード、ゲームパッド、ログリプレイ、OSC、mocap などから値を読む層。

出力は必ず `RawInputFrame` とする。

許可:

```text
- デバイスから値を読む
- ログから値を読む
- RawInputFrame を返す
```

禁止:

```text
- IK
- target 更新
- joint angle 生成
- MuJoCo 操作
- WebSocket 送信
- Three.js 表示を意識した変換
```

抽象インターフェース:

```python
from typing import Protocol
from selfrionette.schemas.input_frame import RawInputFrame

class InputSource(Protocol):
    def read_frame(self) -> RawInputFrame:
        ...
```

### 4.3 `input_interpreters/`

`RawInputFrame` を `InputIntent` に変換する層。

```text
RawInputFrame
  → InputIntent
```

許可:

```text
- deadzone 処理
- スケーリング
- 入力 source ごとの正規化
- button 名への変換
- target_delta / joint_delta への変換
```

禁止:

```text
- IK
- MuJoCo qpos/ctrl 生成
- WebSocket 送信
- Three.js transform 生成
```

抽象インターフェース:

```python
from typing import Protocol
from selfrionette.schemas.input_frame import RawInputFrame
from selfrionette.schemas.input_intent import InputIntent

class InputInterpreter(Protocol):
    def interpret(self, frame: RawInputFrame) -> InputIntent:
        ...
```

### 4.4 `motion/`

`InputIntent` から `MotionCommand` を生成する層。

```text
InputIntent
  → TargetCommand
  → JointCommand
  → MotionCommand
```

許可:

```text
- target 位置更新
- workspace 制限
- 速度制限
- 安全制限
- IK 呼び出し
- JointCommand 生成
```

禁止:

```text
- MuJoCo model/data を直接操作する
- WebSocket 送信
- Three.js 用 transform 生成
```

抽象インターフェース:

```python
from typing import Protocol
from selfrionette.schemas.input_intent import InputIntent
from selfrionette.schemas.motion_command import MotionCommand

class MotionGenerator(Protocol):
    def update(self, intent: InputIntent, dt: float) -> MotionCommand:
        ...
```

### 4.5 `kinematics/`

純粋な運動学を扱う層。

許可:

```text
- FK
- IK
- joint limit
- joint convention
- motor_space / joint_space 変換
```

禁止:

```text
- 入力デバイスを読む
- MuJoCo data.qpos / data.ctrl を直接触る
- WebSocket 通信
- Three.js 表示
```

既存の `FastArmKinematics`、`IKController` はこの層へ責務単位で移植する。

### 4.6 `mujoco_backend/`

MuJoCo model/data を管理する層。

```text
MotionCommand / JointCommand
  → MuJoCo qpos / ctrl
  → mj_forward / mj_step
  → MuJoCoState
```

許可:

```text
- XML / MJCF ロード
- model / data 管理
- qpos 反映
- ctrl 反映
- mj_forward
- mj_step
- body/site transform 取得
- contact 取得
- MuJoCoState 生成
```

禁止:

```text
- Arduino / keyboard / gamepad を直接読む
- InputInterpreter を直接呼ぶ
- WebSocket server を直接持つ
- Three.js 表示処理を持つ
- runtime に依存する
```

抽象インターフェース:

```python
from typing import Protocol
from selfrionette.schemas.motion_command import MotionCommand
from selfrionette.schemas.mujoco_state import MuJoCoState

class MuJoCoSimulator(Protocol):
    def apply_command(self, command: MotionCommand) -> None:
        ...

    def step(self, dt: float) -> None:
        ...

    def snapshot(self) -> MuJoCoState:
        ...
```

初期実装では `ctrl` よりも `qpos` 直接反映 + `mj_forward` を優先する。姿勢表示と座標整合を先に固定するためである。

### 4.7 `transport/`

通信と記録を扱う層。

```text
MuJoCoState
  → JSON
  → WebSocket
```

許可:

```text
- JSON schema 変換
- WebSocket 送信
- replay recording
- frame logging
```

禁止:

```text
- IK
- target 更新
- MuJoCo step
- 入力デバイス read
```

抽象インターフェース:

```python
from typing import Protocol
from selfrionette.schemas.mujoco_state import MuJoCoState

class StatePublisher(Protocol):
    async def publish(self, state: MuJoCoState) -> None:
        ...
```

### 4.8 `runtime/`

全体を結線する composition root。

許可:

```text
- config 読み込み
- InputSource の選択
- InputInterpreter の選択
- MotionGenerator の選択
- MuJoCo backend の生成
- Transport の生成
- main loop 管理
```

重要ルール:

```text
複数層を結線してよいのは runtime のみ。
各層の実装は runtime に依存してはならない。
```

### 4.9 `apps/mujoco-viewer/`

Three.js による表示層。

許可:

```text
- MuJoCoState を受け取る
- STL / mesh をロードする
- body/site transform を mesh に適用する
- target marker を表示する
- wrist / tip marker を表示する
- error vector を表示する
- joint ring を表示する
- debug overlay を表示する
```

禁止:

```text
- アーム FK の再計算
- IK
- 入力から joint angle を生成する
- MuJoCo step
- Rapier physics の導入
```

## 5. 依存方向

許可される依存方向:

```text
input_sources       → schemas
input_interpreters  → schemas
motion              → schemas, kinematics
kinematics          → schemas
mujoco_backend      → schemas
transport           → schemas
runtime             → all layers
```

禁止依存:

```text
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
```

## 6. import boundary test

初期 PR で以下のような boundary test を置く。

```python
from pathlib import Path
import ast

ROOT = Path("src/selfrionette")

FORBIDDEN_IMPORTS = {
    "input_sources": [
        "selfrionette.motion",
        "selfrionette.kinematics",
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.runtime",
    ],
    "kinematics": [
        "selfrionette.input_sources",
        "selfrionette.mujoco_backend",
        "selfrionette.transport",
        "selfrionette.runtime",
    ],
    "mujoco_backend": [
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
        "selfrionette.runtime",
    ],
    "transport": [
        "selfrionette.input_sources",
        "selfrionette.input_interpreters",
        "selfrionette.motion",
        "selfrionette.kinematics",
        "selfrionette.mujoco_backend",
        "selfrionette.runtime",
    ],
}


def iter_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def test_import_boundaries() -> None:
    for layer, forbidden_prefixes in FORBIDDEN_IMPORTS.items():
        for path in (ROOT / layer).rglob("*.py"):
            imports = iter_imports(path)
            for imported in imports:
                for forbidden in forbidden_prefixes:
                    assert not imported.startswith(forbidden), (
                        f"{path} must not import {forbidden}; found {imported}"
                    )
```

## 7. 既存資産の移植方針

既存 `fast_arm_control` の資産は以下のように扱う。

| 既存 | 新配置 | 扱い |
|---|---|---|
| `mujoco_sim/arm.xml` | `assets/mujoco/fast_arm/arm.xml` | 採用 |
| `mujoco_sim/scene.xml` | `assets/mujoco/fast_arm/scene.xml` | 採用 |
| `mujoco_sim/assets/*.stl` | `assets/mujoco/fast_arm/meshes/*.stl` | 採用 |
| `kinematics/kinematics.py` | `src/selfrionette/kinematics/fast_arm_kinematics.py` | 責務単位で移植 |
| `ik_controller.py` | `src/selfrionette/kinematics/ik_controller.py` | 責務単位で移植 |
| `mocap_to_joint/arm_communicator.py` | `input_sources/osc.py` または `transport/` | 分解して移植 |
| `gui_controller.py` | 直接移植しない | 旧UI参照 |
| `zero.py` | `input_sources/replay.py` または scenario stub | 分解して移植 |
| `ball_touch.py` | `input_sources/osc.py` + `motion/` | 分解して移植 |
| `throw_ball_touch.py` | `input_sources/osc.py` + `motion/` | 分解して移植 |
| `mocap_to_ik.py` | `input_sources/mocap.py` + `motion/` | 分解して移植 |
| `NatNetClient.py` | `input_sources/mocap.py` または `vendor/` | 外部接続資産として隔離 |

## 8. MuJoCo name map

既存 XML では `sholder` という名前が使われている。初期移行では XML 名を変更しない。代わりに canonical alias を置く。

```python
CANONICAL_JOINTS = {
    "shoulder_joint_1": "sholder_joint_1",
    "shoulder_joint_2": "sholder_joint_2",
    "shoulder_twist": "sholder_joint_3",
    "elbow": "elbow_joint",
}

CANONICAL_BODIES = {
    "base": "base",
    "base_link": "base_link",
    "shoulder_link_1": "sholder_link_1",
    "shoulder_link_2": "sholder_link_2",
    "upper_arm": "upper_arm_link",
    "fore_arm": "fore_arm_link",
}

CANONICAL_SITES = {
    "tip": "tip",
}
```

XML 名の変更は、MuJoCo model load、state builder、Three.js 表示が安定してから別 PR で扱う。

## 9. Three.js 表示仕様

Three.js viewer は `MuJoCoState` を受け取り、表示のみを担当する。

最初に必要な表示要素:

```text
- arm mesh
- body transform application
- tip marker
- target marker
- error vector
- joint ring overlay
- debug panel
```

Three.js 側で禁止すること:

```text
- qpos から FK を再計算する
- joint convention を持つ
- motor_space / joint_space 変換を持つ
- Rapier world を作る
- MuJoCo state と別の姿勢状態を持つ
```

## 10. 初期 PR 完了条件

Architecture lock PR の完了条件:

```text
- ディレクトリ構造が作成されている
- 各層に README が存在する
- 各層 README に責務と禁止事項が書かれている
- schemas に主要 dataclass が存在する
- input_sources / input_interpreters / motion / mujoco_backend / transport に Protocol または stub が存在する
- runtime に stub 同士を結線する場所が存在する
- apps/mujoco-viewer に表示層の空スケルトンが存在する
- import boundary test が存在する
- 既存 Rapier viewer を変更していない
- 既存 PoseState 中心設計を新系統へ持ち込んでいない
```

## 11. 以後の実装順序

```text
PR 1:
  skeleton / architecture lock

PR 2:
  schemas + Protocol + stub runtime pipeline

PR 3:
  MuJoCo model path / name map / model load smoke test

PR 4:
  qpos apply + mj_forward + state builder

PR 5:
  WebSocket transport for MuJoCoState

PR 6:
  Three.js viewer skeleton + state client

PR 7:
  Three.js mesh rendering + transform application

PR 8:
  replay input source + fixed motion command

PR 9:
  IK / kinematics migration

PR 10:
  keyboard / gamepad / Arduino input sources
```

## 12. 最重要原則

```text
動くものを早く作ることより、ズレない構造を先に作ることを優先する。
```

```text
実装はスケルトンに従う。
スケルトンを実装に合わせて崩してはならない。
```

```text
MuJoCo は物理層。
Three.js は描画層。
input/motion/kinematics は制御層。
runtime は結線層。
```
