# transport

## 責務

`MuJoCoState` の JSON 変換、送信、frame logging、replay recording を扱う。

## 入力

`MuJoCoState`

## 出力

JSON message、WebSocket frame、log frame

## 依存してよい層

`schemas`

## 依存してはいけない層

`input_sources`, `input_interpreters`, `motion`, `kinematics`,
`mujoco_backend`, `runtime`

## 禁止事項

IK禁止、target更新禁止、MuJoCo step禁止、入力デバイス読み取り禁止、Three.js表示禁止。

## 今後 stub を置く予定のファイル名

`websocket_schema.py`, `websocket_server.py`, `recorder.py`
