# viewer_keyboard_gamepad_mapping

## 意味とresponsibility

viewer keyboard / gamepad sampleをcontinuous local endpoint velocity intentへ変換する。
canonical declaration: [`CONTROL_MAPPING_PLUGIN`](plugin.py)

## input / output

viewer control sampleとmapping parameterを受け、source diagnosticsを保持した`InputIntent`を出力する。

## parameters

speed、deadzone、per-tick limit、control frame等をMapping側で扱う。current field、型、resourceは
[`implementation.py`](implementation.py)と[`resources/keyboard_default.json`](resources/keyboard_default.json)を正とする。

## lifecycleとside effect

backend-side software変換で、browser event listener、gamepad device acquisition、network connectionを
所有しない。

## compatibilityとcomposition

Viewer Input Sourceはsample取得だけを担当し、このMappingのparameterを所有しない。

## command semantics route

local endpoint velocityをjoint position commandへ解決するtyped routeを宣言する。

## constraintsとnon-goals

- constraint: unknown / malformed inputとstale stateを明示的に扱う
- non-goal: browser rendering、FK / IK、Robot command executionを所有しない

## tests / validation

- [keyboard / gamepad smoke](../../../../../docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md)

## canonical architecture / contract

- [continuous endpoint velocity](../../../../../docs/contracts/continuous-endpoint-velocity-input.md)
- [viewer control schema](../../../../../docs/contracts/viewer-control-message-schema.md)
