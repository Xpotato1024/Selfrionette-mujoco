---
status: canonical
owner: architecture
last_verified: 2026-07-26
canonical_for:
  - viewer control message schema
related:
  - docs/contracts/schemas.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/runtime-input-source-registry.md
---

# Viewer Control Messageのschema

P3ではこのmessageを受けるbackend `viewer` sourceをcompatibility pluginとしてcatalogへ登録した。
P4では既存wire shapeを維持したまま、frontend provider、backend source、Control Mapping、runtimeの
責務境界を分離する。

この文書はviewer-to-backend control messageのcanonical contractを定義する。

これはschema-onlyかつJSON-compatibleである。Viewer JSはkeyboardまたは
gamepad stateを取得してこのenvelopeをserializeしてよいが、このmessageを使って
simulation state、physics state、FK / IK、qpos、またはbrowser-sideの
source of truthを変更してはならない。

## P4 provider extension (#461)

P4では既存envelopeを維持したまま、frontend provider identityをoptionalに追加した。

- `provider_id`: `keyboard/v1`または`gamepad/v1`
- `provider_schema`: `viewer_keyboard_sample/v1`または`viewer_gamepad_sample/v1`

2 fieldは指定する場合は必ず同時に指定する。`source_kind=keyboard`は
`keyboard/v1` + `viewer_keyboard_sample/v1`、`source_kind=gamepad`は
`gamepad/v1` + `viewer_gamepad_sample/v1`だけを受け付ける。未知・重複・組合せ不一致は
keyboard、gamepad、noopへfallbackせずrejectする。provider fieldを持たない従来messageは
backend viewer sourceが`source_kind`から既知providerへcanonicalizeして受け付ける。

frontendのknown-ID registryは`keyboard/v1`と`gamepad/v1`を静的に登録し、providerごとに
attach/start、dispose、timestamp、sequence、focus / visibility / connected state、raw device neutral state、
provider固有raw payloadを所有する。backend viewer sourceはmessage parse、canonical sample、latest sample、
health、250 ms timeout、cleanupだけを所有する。mappingはcanonical
`viewer_control_sample/v1`を受け、axis/sign/gain/speed/deadzone/button supplement/control frameを
typed continuous endpoint-velocity intentへ変換する。

runtimeはmapping resultを適用し、desired endpoint progression、publish-before-rebase、
MuJoCo command compositionを所有する。従ってlegacy `metadata`のoverlay fieldを保持しても、
messageやsourceがmapping algorithmまたはendpoint progressionのSoTになることはない。

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
- `raw_axes`: optional finite number array。browserから取得したunprocessed raw axisであり、存在する場合は
  mappingのauthoritative gamepad inputとする。`axes`は既存wire互換projectionとして保持できる。
- `buttons`: button-state object array。各itemは
  `{"pressed": boolean, "value": optional finite number}`
- `stale`: optional boolean
- `zero_state`: optional boolean

`raw_axes`が存在するgamepadでは、source activityは`connected`、provider lifecycle、`stale`、disconnectなど
source-owned stateから決まり、legacy normalized `axes`やmapping deadzoneからは決まらない。`zero_state`は
providerのraw neutral / legacy wire stateであり、mapping後のcommand zeroやsource healthの代替ではない。
raw axisがzeroでもbutton pressはactive command sampleとして扱う。`raw_axes`がないlegacy messageは旧
`axes` / `zero_state`解釈を維持する。

## Backend viewer bridge

backend `viewer` pluginは`ViewerBridgeRuntimeCapability`をtyped optional bindingとして公開する。
次を同一の`ViewerInputSource` instanceへ結線する。

- message ingress
- JSON ingress
- `rebase_current_endpoint_m()`
- deterministic test / runtime clockの`rebind_clock()`

clock rebindはreaderやcapabilityを再生成しない。rebind前に受け取ったcontrol message、current endpoint、
selection capability identityを維持し、旧clockで経過済みのcommand ageを新clock domainへ連続的に移す。
plugin-backed selectionでもdirect source pathと同じframe metadata、health、timeout、initial / post-publish
rebase semanticsを維持する。viewer capabilityが欠落したplugin-backed selectionはfail-closedとする。

generic source readerへ任意attribute forwardingを追加せず、viewer固有capabilityだけをselectionとruntime
continuity codeへ渡す。frontend providerはraw acquisitionとlifecycle、backend sourceはvalidation・canonical
sample・health、mappingはsample interpretationを所有する。

## Canonical sampleとlegacy compatibility

backend sourceがframe metadataへ出力する`viewer_input_sample`（schema identity
`viewer_control_sample/v1`）がmappingのauthoritative inputである。sample単体でprovider identity / schema、
source kind、timestamp / sequence、keyboardまたはgamepad payload、requested control frame、active / zero /
stale state、raw provider value、diagnosticsを復元できる。legacy `viewer_control_message` summaryはwire
compatibilityまたはdiagnosticsとして残せるが、mappingは参照しない。両者が矛盾する場合はcanonical sampleを
使用し、canonical sample自体が不正ならfail-closedとする。

malformed JSON、schema validation、provider identity mismatchはsource-owned typed ingress failureへ伝え、
source healthを即時`invalid`にする。timeoutまで旧active sampleを保持せず、valid sample受信後にだけrecover
する。

Control Mapping parametersはsource lifecycle開始とframe readの前にgeneric `ParameterContract`および
mapping-specific semantic validation / normalizationを通過する。unknown parameter、negative / non-finite
speed・deadzone・max delta、invalid keyboard axis / directionはrejectし、検証済みのdeterministic parameterを
mappingへ渡す。

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
- clockはcallableで、rebind時にfinite valueを返さなければならない。

## 責務boundary

このschemaはread-only control intentだけを記述する。Viewer JSはkeyboardまたは
gamepad stateを取得してこのmessageをserializeしてよいが、このmessageを使って
simulation state、physics state、FK / IK、qpos、またはbrowser-sideの
source of truthを変更してはならない。
