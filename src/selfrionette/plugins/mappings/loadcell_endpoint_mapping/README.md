# loadcell_endpoint_mapping

## 意味とresponsibility

normalized loadcell intentをcurrent tip基準のdesired endpoint deltaへ変換する。
canonical declaration: [`CONTROL_MAPPING_PLUGIN`](plugin.py)

## input / output

normalized loadcell sample、mapping config、current tip positionを受け、endpoint metadataを持つ
`InputIntent`を出力する。

## parameters

`mapping_config`と`current_tip_position_m`を必須とする。型、axis weight、scale等のcurrent semanticsは
[`implementation.py`](implementation.py)を正とする。

## lifecycleとside effect

software-only変換で、serial reader、device lifecycle、MuJoCo state取得を所有しない。

## compatibilityとcomposition

Selfrionette Input Sourceのdevice-intrinsic normalization後のsampleだけを受理する。

## command semantics route

endpoint deltaをjoint position commandへ解決するtyped routeを宣言する。Robot固有IKとsafetyは
runtime / Robot provider側で適用する。

## constraintsとnon-goals

- constraint: 7要素normalized input、finite current tip、mapping configを検証する
- non-goal: channel acquisition、serial open、Robot joint orderを所有しない

## tests / validation

- [runtime input pipeline contract](../../../../../docs/contracts/r7-b-runtime-input-pipeline-contract.md)

## canonical architecture / contract

- [continuous endpoint input](../../../../../docs/contracts/continuous-endpoint-velocity-input.md)
- [Input Source registry](../../../../../docs/contracts/runtime-input-source-registry.md)
