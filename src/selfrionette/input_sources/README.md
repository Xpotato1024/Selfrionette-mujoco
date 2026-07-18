# input_sources

## 責務

Arduino / keyboard / gamepad / replay / OSC / mocap から値を読み、
`RawInputFrame` を作る。loadcellのserial frame parser、normalization、
`SerialInputSource`は`loadcell_serial.py`が所有する。

## 入力

デバイス値または replay ログ。

## 出力

`RawInputFrame`

## 依存してよい層

`schemas`

## 依存してはいけない層

`motion`, `kinematics`, `mujoco_backend`, `transport`, `runtime`

## 禁止事項

IK禁止、target更新禁止、joint angle 生成禁止、MuJoCo操作禁止、
WebSocket送信禁止、Three.js 表示変換禁止。

package rootの旧`selfrionette.loadcell_serial`は退役済みであり、再導入しない。
