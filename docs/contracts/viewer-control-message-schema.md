---
status: canonical
owner: architecture
last_verified: 2026-06-24
canonical_for:
  - viewer control message schema
related:
  - docs/contracts/schemas.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
---

# Viewer Control Messageのschema

この文書はviewer-to-backend control messageのcanonical contractを定義する。

これはschema-onlyかつJSON-compatibleである。Viewer JSはkeyboardまたは
gamepad stateを取得してこのenvelopeをserializeしてよいが、このmessageを使って
simulation state、physics state、FK / IK、qpos、またはbrowser-sideの
source of truthを変更してはならない。

## Envelope仕様

top-level field:

- `type`: literal `viewer_control_message`
- `timestamp_s`: number
- `source_kind`: `keyboard` or `gamepad`
- `sequence`: optional integer
- `keyboard`: `source_kind == "keyboard"`のときrequired
- `gamepad`: `source_kind == "gamepad"`のときrequired
- `metadata`: optional plain object

## Keyboard payload仕様

`source_kind == "keyboard"`のとき、`keyboard` objectは次を持つ。

- `active_key_codes`: string array
- `key_state`: key codeをbooleanへmapするplain object
- `focus_state`: optional string。`focused`または`blurred`
- `zero_state`: optional boolean

## Gamepad payload仕様

`source_kind == "gamepad"`のとき、`gamepad` objectは次を持つ。

- `index`: optional integer
- `id`: optional string
- `connected`: boolean
- `axes`: finite number array
- `buttons`: button-state object array。各itemは
  `{"pressed": boolean, "value": optional finite number}`
- `stale`: optional boolean
- `zero_state`: optional boolean

## Validation規則

- malformed JSONはrejectする。
- unknown top-level fieldはrejectする。
- keyboard / gamepad / button objectのunknown nested fieldはrejectする。
- `source_kind`は`keyboard`または`gamepad`でなければならない。
- 選択したsource kindに対応するsource-specific payloadが必要である。
- field type mismatchはrejectする。
- `metadata`はplain objectでなければならない。
- nested JSON-compatibleな`metadata`はそのまま保持する。
- `index`、`id`、buttonの`value`はoptionalであり、contract上もoptionalのままとする。
- buttonの`value`は、存在する場合finiteでなければならない。

## 責務boundary

このschemaはread-only control intentだけを記述する。Viewer JSはkeyboardまたは
gamepad stateを取得してこのmessageをserializeしてよいが、このmessageを使って
simulation state、physics state、FK / IK、qpos、またはbrowser-sideの
source of truthを変更してはならない。
