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
runtimeはsource固有のreasonを再生成せず、frame metadataとtyped healthのactive/stale状態が矛盾する
場合はfail-closedとする。viewer backend bridgeの初期値は`source_active=false`、
`command_age_ms=0`、`stale_reason=no_control_message_received`を維持する。

## fields

- `source_kind`: 選択されたruntime input sourceまたはsource-specific subtype
- `source_active`: 現在commandを出せるかどうかの観測値
- `command_age_ms`: sourceがemitしたcommand ageの観測値
- `stale_reason`: stale判定理由。正常経路では省略または`null`

これらの値はobservability用の入力状態であり、runtime stale-command safetyはこのmetadataを
読み取って別途判定する。runtimeは`command_age_ms`をwall clockから再計算しない。
offlineのprogrammed target / replay / noopはdeterministicな`0`をemitしてよい。
browser / live sourceはageとstale reasonをsource側でemitする。

## typed health projection

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
- stale safetyは`source_active`, `command_age_ms`, `stale_reason`を参照する。
