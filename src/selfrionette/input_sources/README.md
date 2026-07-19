# input_sources compatibility modules

## 責務

既存public importとsource-local algorithmの互換境界を提供する。production sourceのcatalog、
versioned identity、factory、health、lifecycle registrationは`selfrionette/plugins/input_sources/`
が所有し、ここから新しいsource implementationを登録しない。Arduino / keyboard / gamepad /
replay / OSC / mocapから値を読み、`RawInputFrame`を作る。loadcellのserial frame parser、
normalization、`SerialInputSource`はP3でもこの互換moduleから同一実装を参照する。

## 入力

デバイス値または replay ログ。

## 出力

`RawInputFrame`

## 依存してよい層

`schemas`

## 依存してはいけない層

`motion`, `kinematics`, `mujoco_backend`, `transport`

plugin catalogとのcomposition接続は`runtime`が所有する。

## 禁止事項

IK禁止、target更新禁止、joint angle 生成禁止、MuJoCo操作禁止、
WebSocket送信禁止、Three.js 表示変換禁止。

package rootの旧`selfrionette.loadcell_serial`は退役済みであり、再導入しない。
