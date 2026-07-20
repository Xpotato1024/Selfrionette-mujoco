# input_sources compatibility modules

## 責務

既存public import、低位source-local algorithm、`RawInputFrame`生成の互換境界を提供する。
production runtime selectionのcatalog、versioned identity、factory registration、health、lifecycleは
`selfrionette/plugins/input_sources/`が所有する。ただし、この低位packageからplugin catalogまたは
runtimeへ逆依存しない。

Arduino / keyboard / gamepad / replay / OSC / mocapから値を読み、`RawInputFrame`を作る。
loadcellのserial frame parser、normalization、`SerialInputSource`はP3でもこのpackageの同一実装を
plugin adapterが参照する。`input_sources.registry`は既存descriptor APIのsignatureとframe behaviorだけを
維持し、production plugin catalogの第二のregistration SoTにはしない。

## 入力

デバイス値または replay ログ。

## 出力

`RawInputFrame`

## 依存してよい層

`schemas`

## 依存してはいけない層

`motion`, `kinematics`, `mujoco_backend`, `transport`, `runtime`, `plugins`

plugin catalogとのcomposition接続は`runtime`が所有する。

## 禁止事項

IK禁止、target更新禁止、joint angle 生成禁止、MuJoCo操作禁止、
WebSocket送信禁止、Three.js 表示変換禁止。

package rootの旧`selfrionette.loadcell_serial`は退役済みであり、再導入しない。
