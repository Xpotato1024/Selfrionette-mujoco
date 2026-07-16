---
status: canonical
owner: input contract
last_verified: 2026-07-16
canonical_for:
  - recorded analog fixture mapping
related:
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/contracts/experiment-motion-log-v1.md
---

# 記録済みanalog fixture mapping

pure mappingは、JSON互換の記録済みsample 1件を既存の
`ContinuousEndpointVelocityIntent`へmappingする。これはpureなoffline boundaryであり、
自身ではfileを読まず、deviceを検出せず、serial/Arduino/OSC I/Oを実行せず、
runtime composition rootにも接続しない。

sample formatは、`timestamp_s`、数値の`raw_values`、JSON booleanの`active`、
nullableかつ空でない`stale_reason`だけを持つ。fieldの欠落・余分なfield、
numberとしてのbool、数値文字列、NaN、Infinity、不正なvector、activeとstaleの
同時指定は、zeroへ変換せずrejectする。

canonicalなSelfrionette recorded shapeは、`RawLoadcellVectorRecord`と
`docs/contracts/r7-a-lite-serial-frame-contract.md`で定義された、`ch0`から`ch6`までの
7 channel vectorである。pure fixture typeがgenericなのは、configurationでchannel数を
明示できるようにするためだけである。追跡済みのcanonical fixtureは7値を使用し、
競合するwire contractやdevice contractを作らない。

`AnalogFixtureMappingConfig`は、N個のcenter、正のhalf range、
`LoadcellEndpointMappingConfig.channel_axis_weights`と整合するN x 3の
`channel_axis_weights` matrix、sign、output axisごとのscale、component deadzone、
velocity scale、max delta provenance、requested control frame、source identityを
deepかつimmutableにfreezeする。mapping順序は、finite-value validation、centerと
half-rangeによるnormalization、componentの`[-1, 1]` clamp、重み付きchannel-to-axis
projection、sign、scale、continuous endpoint velocity component deadzone、最後のvector norm clampである。
同じsample値とconfig値からは、同じintentを生成する。

active zero、inactiveかつnon-stale、stale inactiveは、`source_active`、derived
`zero_input`、`stale_reason`によって区別したままにする。raw diagnosticはimmutableな
continuous endpoint velocity diagnostic mappingへ保持する。結果は、`source_kind`、`source_active`、
`axis_values`、`zero_input`、`stale_reason`、`local_endpoint_velocity_m_s`、
`control_frame`など、experiment motion sampleが消費するcontinuous endpoint velocity fieldを正確に公開する。
入力intentまたはexperiment log schemaは変更しない。

この契約は、hardware calibration、force estimation、sensor zeroing、live acquisition、
automatic experiment logging、viewer behavior、transport、motion policy、
target lifecycle、MuJoCo behaviorを定義しない。
