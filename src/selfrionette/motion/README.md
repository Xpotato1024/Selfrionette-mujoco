# motion

## 責務

`InputIntent` から `MotionCommand` を生成する。target更新、workspace制限、
速度制限、安全制限、IK呼び出しを担当する。

## 入力

`InputIntent`

## 出力

`TargetCommand`, `JointCommand`, `MotionCommand`

## 依存してよい層

`schemas`, `kinematics`

## 依存してはいけない層

`input_sources`, `input_interpreters`, `mujoco_backend`, `transport`, `runtime`

## 禁止事項

MuJoCo data 直接操作禁止、WebSocket送信禁止、Three.js transform生成禁止、
入力デバイス直接読み取り禁止。

## 今後 stub を置く予定のファイル名

`motion_generator.py`, `target_updater.py`, `constraints.py`, `safety_limits.py`
