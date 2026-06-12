# kinematics

## 責務

FK / IK / joint convention / joint limit / motor_space と joint_space の変換を
扱う純粋な運動学層。

## 入力

schema 型または純粋な数値入力。

## 出力

FK / IK / joint diagnostic result などの純粋な計算結果。

## 依存してよい層

`schemas`

## 依存してはいけない層

`input_sources`, `input_interpreters`, `mujoco_backend`, `transport`, `runtime`

## 禁止事項

入力デバイス依存禁止、MuJoCo data 直接操作禁止、WebSocket禁止、Three.js表示禁止、
runtime依存禁止。

## 今後 stub を置く予定のファイル名

`fast_arm_kinematics.py`, `ik_controller.py`, `joint_convention.py`,
`joint_limits.py`
