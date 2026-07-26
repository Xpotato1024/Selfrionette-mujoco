---
status: canonical
owner: architecture
last_verified: 2026-07-26
canonical_for:
  - runtime input source state payload
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/contracts/runtime-input-safety.md
  - docs/reports/implementation/r6-k-p3-input-source-state-payload.md
---

# Runtime Input Source State

## 目的

runtime payloadの`metadata`に載せるinput sourceの観測用stateと、source-owned typed healthまたは
recorded replay metadataから既存metadataへprojectionする規則を定義する。

P3ではlive / viewer / fixture sourceの`InputSourceHealth`をsource pluginが所有し、runtimeは各read後に
typed healthを取得する。replayはrecorded `RawInputFrame.metadata`をsource-stateの正本とし、pluginの
initial healthで記録済みstateを上書きしない。viewer backend bridgeの初期値は`source_active=false`、
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
source healthからmetadataへ投影する段階では、これを`stale`へ読み替えたりsynthetic reasonを追加したりしない。
runtime safety policyは別の責務として、inactive commandをholdへ変換した理由に`source_inactive`を付けてよい。

runtime step-loopは次の順で処理する。

1. `RawInputFrame`をreadする。
2. replay executionではrecorded frame metadataからsource stateを復元する。
3. replay以外では`current_health()`からtyped healthを取得する。
4. frameに明示されたstate keyだけをtyped healthと比較し、不一致をfail-closedとする。
5.省略されたstate keyをtyped healthで補完する。
6. canonical frameをinterpreter、record、diagnosticsへ渡す。

`source_kind`のsource-specific valueは保持する。runtimeがcanonicalに補完するfieldは
`source_active`、`command_age_ms`、`stale_reason`である。frameに存在しないoptional fieldをdefault値へ
読み替えてhealth mismatchとは扱わない。source-owned reasonとruntime safetyが導出するhold reasonを混同しない。

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
- replayはcustom frameのstate metadata、ordering、timestampを保持する。
- stale safetyは`source_active`, `command_age_ms`, `stale_reason`を参照する。

## viewer canonical sample

viewer sourceは`viewer_input_sample` metadataに`viewer_control_sample/v1`を出力する。
sampleにはprovider ID / schema、`source_kind`、provider timestamp、sequence、raw keyboardまたは
gamepad payload（存在する場合はunprocessed finite `raw_axes`）、`requested_control_frame`、
`source_active`、providerのraw neutralを表す`zero_state`、`stale_reason`、diagnosticsを含める。
このsampleはsourceのlatest observationであり、axis assignment、gain、deadzone、control-frame
conversion、desired endpointを含むmapping resultではない。

legacy viewer messageにprovider fieldがない場合も、sourceはknown provider contractへcanonicalize
して同じsample schemaを作る。provider identity / schemaの不一致、malformed payload、sequence / timestamp
不正はinvalidとして扱い、別providerまたはnoopへfallbackしない。keyboard blur / hidden、gamepad
disconnect、staleはinactiveまたはfailureへ遷移させる。raw gamepad sampleではlegacy normalized `axes`の
zeroやmapping deadzone内のraw axisだけではsourceをinactiveにせず、command zeroはmappingが判定する。
`raw_axes`を持たないlegacy messageだけは旧`zero_state`解釈を維持する。

viewer sourceのhealthはlatest sampleと250 ms timeoutを正本とする。runtimeはtyped healthとframeに
存在するstate keyを比較し、mapping後のintentをsource healthの代替にしない。

parse / schema / provider identity failureがsource objectへの到達前に起きた場合も、typed ingress failure
としてsourceへ通知する。sourceはlatest sampleを非active化し、healthを`invalid`へ遷移させ、diagnosticsへ
invalid reasonを保存する。valid sampleの後だけactiveへ戻る。mappingはこのcanonical sampleだけを入力とし、
legacy compatibility summaryをauthoritative inputにしない。

## #461 final audit correction (2026-07-26)

viewer canonical sampleでは、raw `raw_axes`、legacy normalized `axes`、provider / source lifecycle state、legacy `zero_state`、mapping結果としてのcommand zeroを別field / 別概念として扱う。raw axisがdeadzone内でもconnectedかつlifecycle上activeならsource healthはactiveを維持でき、button-only inputもactive command sampleとなる。hidden、blur、disconnect、stale、invalidは既存のinactive / failure / hold projectionを維持する。

mapping parameterはselection / plan readinessで検証・正規化・freezeされ、source lifecycle開始前に実行可能性を確定する。explicit runtime parameter、direct source compatibility parameter、plugin defaultの順序をprovenance付きで保持し、source healthとmapping command zeroを混同しない。
