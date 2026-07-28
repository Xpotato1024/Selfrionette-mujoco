# input_sources compatibility modules

## 責務

既存public importのcompatibility boundaryを提供する。generic reader contractは
`runtime/experiment/input_source.py`、source-owned implementationは`plugins/input_sources/`、
mapping implementationは`plugins/mappings/`がcanonical ownerである。このpackageは同一objectを
re-exportし、contract、source algorithm、parser、normalization、default、lifecycleを複製しない。

`input_sources.registry`は既存descriptor APIのsignatureとframe behaviorだけを維持し、
production plugin catalogの第二のregistration SoTにはしない。loadcellのrecorded dry-run helperは
C3/C4のcompatibility scopeとして残る。

## 入力

デバイス値または replay ログ。

## 出力

`RawInputFrame`

## 依存してよい層

canonical runtime contract、source plugin、mapping pluginのcompatibility export

## 依存してはいけない層

`kinematics`, `mujoco_backend`, `transport`

plugin catalogとのcomposition接続は`runtime`が所有する。このpackageからproduction catalogを
再登録または再投影しない。

## 禁止事項

IK禁止、target更新禁止、joint angle 生成禁止、MuJoCo操作禁止、
WebSocket送信禁止、Three.js 表示変換禁止。

package rootの旧`selfrionette.loadcell_serial`は退役済みであり、再導入しない。
