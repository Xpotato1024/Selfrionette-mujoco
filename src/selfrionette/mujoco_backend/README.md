# mujoco_backend

## 責務

`MotionCommand` / `JointCommand` を MuJoCo qpos / ctrl に反映し、
`MuJoCoState` を生成する。MuJoCo を physical SoT として扱う。

## 入力

`MotionCommand`, `JointCommand`, MJCF / XML / asset paths

## 出力

`MuJoCoState`

## 依存してよい層

`schemas`

## 依存してはいけない層

`input_sources`, `input_interpreters`, `motion`, `transport`, `runtime`

## 禁止事項

入力読み取り禁止、InputInterpreter 直接呼び出し禁止、WebSocket server禁止、
Three.js描画禁止、runtime依存禁止。

## 今後 stub を置く予定のファイル名

`model_paths.py`, `name_map.py`, `model_loader.py`, `simulator.py`,
`command_adapter.py`, `state_builder.py`
