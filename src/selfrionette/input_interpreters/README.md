# input_interpreters

## 責務

`RawInputFrame` を `InputIntent` に変換する。deadzone / scaling /
source別解釈を扱う。

## 入力

`RawInputFrame`

## 出力

`InputIntent`

## 依存してよい層

`schemas`

## 依存してはいけない層

`motion`, `mujoco_backend`, `transport`, `runtime`

## 禁止事項

IK禁止、target更新禁止、qpos生成禁止、MuJoCo操作禁止、Three.js transform
生成禁止。

## 今後 stub を置く予定のファイル名

`base.py`, `arduino_mapper.py`, `keyboard_mapper.py`, `gamepad_mapper.py`,
`replay_mapper.py`, `osc_mapper.py`
