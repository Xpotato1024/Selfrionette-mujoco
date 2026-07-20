---
status: canonical
owner: architecture
last_verified: 2026-07-21
canonical_for:
  - runtime input source state payload
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/reports/implementation/r6-k-p3-input-source-state-payload.md
---

# Runtime Input Source State

## 目的

runtime payloadの`metadata`に載せるinput sourceの観測用stateと、source-owned typed healthから
既存metadataへprojectionする規則を定義する。

P3では`InputSourceHealth`をsource pluginが所有し、runtimeは各read後にtyped healthを取得する。
runtimeはsource固有のreasonを再生成せず、frame metadataとtyped healthのactive / inactive / stale状態が
矛盾する場合はfail-closedとする。viewer backend bridgeの初期値は`source_active=false`、
`command_age_ms=0`、`stale_reason=no_control_message_received`を維持する。

## fields

- `source_kind`: 選択されたruntime input sourceまたはsource-specific subtype
- `source_active`: 現在commandを出せるかどうかの観測値
- `command_age_ms`: sourceがemitしたcommand ageの観測値
- `stale_reason`: stale / invalid / disconnected判定理由。activeまたは意図的inactiveでは省略または`null`

これらの値はobservability用の入力状態であり、runtime stale-command safetyはこのmetadataを
読み取って別途判定する。runtimeは`command_age_ms`をwall clockから再計算しない。
offlineのprogrammed target / replay / noopはdeterministicな`0`をemitしてよい。
browser / live sourceはageとfailure reasonをsource側でemitする。

## typed health projection

`InputSourceHealthStatus`は次を区別する。

- `active`: `source_active=true`、reasonなし
- `inactive`: `source_active=false`、reasonなし
- `stale`: `source_active=false`、reason必須
- `invalid`: `source_active=false`、reason必須
- `disconnected`: `source_active=false`、reason必須

`inactive`は、analog fixture等で既存契約が区別する「inactiveだがnon-stale」を表す。
これを`stale`へ読み替えたり、runtimeがsynthetic reasonを追加したりしない。

runtime step-loopは次の順で処理する。

1. `RawInputFrame`をreadする。
2. `current_health()`から`InputSourceHealth`を取得する。
3. frame内に既存state fieldがある場合、typed healthとの整合性を検証する。
4. `source_active`、`command_age_ms`、`stale_reason`を同じruntime-owned helperでannotateする。
5. annotate後のframeをinterpreter、record、diagnosticsへ渡す。

`source_kind`のsource-specific valueは保持する。runtimeがcanonicalに上書きするのは
`source_active`、`command_age_ms`、`stale_reason`だけである。mismatchはfail-closedとし、
source reasonやtimeout reasonをruntimeで再生成しない。

## overlay diagnostics

- viewer overlayで`runtime_input_safety_applied`, `target_status`, `target_rejected`,
  `target_rejection_reason`, `target_rejection_message`, `rejected_desired_endpoint_m`,
  `target_position_m`をread-onlyで読む。
- accepted frameではrejection fieldsは`none` / `n/a`に戻る。
- missing metadataでもviewer parserはcrashしない。

## rules

- これらはoptional metadataであり、既存payloadのparseを壊さない。
- required payload fieldsには含めない。
- endpoint evaluation semanticsを変えない。
- normal pathでは`source_active=true`, `command_age_ms=0`, `stale_reason` omittedが許容される。
- intentional inactive pathでは`source_active=false`, `stale_reason` omittedが許容される。
- stale safetyは`source_active`, `command_age_ms`, `stale_reason`を参照する。
