---
status: historical
owner: architecture
last_verified: 2026-07-30
canonical_for: []
related:
  - docs/architecture/code-documentation-policy.md
  - docs/operations/code-documentation-review-checklist.md
  - docs/reports/inventories/code-documentation-remediation-inventory.md
---

# Issue #485 code documentation remediation結果

## 基準と方法

PR #488 head `798b6e8b113ab57bbee48bcc95402abf0d482007`を基準に、Issue #482 inventoryの
Python 309 symbols、viewer TypeScript 201 exported symbolsを再確認した。symbol数を欠陥数には
せず、canonical policyのcontract significanceで次のように分類した。

| surface | required documentation | optional documentation | documentation unnecessary | total |
| --- | ---: | ---: | ---: | ---: |
| Python | 141 | 73 | 95 | 309 |
| viewer TypeScript | 54 | 62 | 85 | 201 |

requiredには、既に十分な説明があって変更不要だったsymbolも含む。optionalはalgorithmically
non-trivialなprivate helperやP2 compatibility surface、unnecessaryはobvious private helper、
単純property、Protocol memberの型から読める繰り返し、thin projectionである。

## 修正結果

- experiment contractは6軸のreadiness/freezeであり、production diagnostic runnerを開始・接続
  しないことを明示した。validation failureはscene、Input Source、Robot commandのside effect前に
  発生する。
- Robot Bundleはlogical identityとtyped provider assemblyを所有し、production Robot selectionや
  simulator lifecycleを所有しないことを明示した。
- Mapping private ownerは、continuous endpoint velocityのunit、frame、clamp/deadzone順序、
  state非保持と、command route factoryがalgorithm/execution ownerではないことを分離した。
- 全fixed `plugin.py`はdeclaration entry pointであり、import時にreader、model、simulator、
  hardware、transport lifecycleを開始しないことを明示した。
- Selfrionette、viewer、analog fixture、replay、programmed target、noopのconstruction/start/read/
  health/close、I/O、stale/hold、thread assumptionを必要な範囲で明示した。
- command、input、state、viewer control、experiment log schemaへunit、frame、ordering、owner、
  optional/measured semantics、failure boundaryを追加した。
- viewerはbrowser acquisition、disconnect/blur/hidden/stale、WebSocket lifecycle、qpos ordering、
  Robot resource identityを説明し、Python/MuJoCo physical SoTとThree.js projection-onlyを明示した。
- fast_arm diagnosticはcommand intent、solver prediction、MuJoCo tip-site measurementを分離し、
  world position/deltaのm、joint perturbationのrad、Jacobianのm/radを明示した。

## suppression disposition

current production sourceの72候補を再監査した。

| disposition | count | result |
| --- | ---: | --- |
| necessary and self-explanatory | 55 | narrow error codeまたは直前のvalidationにより維持 |
| necessary but rationale missing | 17 | optional dependency、compatibility facade、diagnostic best-effort境界を説明 |
| overly broad | 0 | なし |
| obsolete | 0 | なし |
| hides contract / typing defect | 0 | なし |

fast_arm compatibility wrapperのF403はmodule-levelに一度だけ理由と削除条件を記録し、各import行へ
同じcommentを複製していない。public consumerの移行とcontract変更承認まではwrapperを維持する。

## zero-result scan

- vague / unowned `TODO` / `FIXME` / `HACK`: 0件
- confirmed commented-out production code: 0件
- stale / misleading production comment: remediation後0件
- historical Issue / PR / date comment in production code: 0件

`neutral_initial_pose.py`のprose continuationはcommented-out import候補ではなく、現行計算理由の
説明として維持した。

## intentionally undocumented

- vector arithmetic、finite値coercion、単純getter/property等のobvious private helper
- Protocolの型だけで十分なmemberごとの繰り返し
- field名と型の逐語説明にしかならないdataclass field単位の説明
- package-root re-export先と同じ長文説明

## remaining P2 findings

1. `build_normalized_analog_fixture_intent()`等のshared primitive配置はowner整理候補だが、file moveや
   refactorはbehavior-preserving documentation scope外である。
2. fast_arm compatibility wrapperの削除はconsumer migrationとpublic API変更を要するため、本Issue
   ではrationale/removal conditionの明示に留めた。

P0 / P1 blockerは0件。public API、schema field、error literal、plugin identity、runtime behaviorは
変更していない。

## impact

- Documentation impact: code-local contract explanationとfocused architecture guardを更新した。
- Research log impact: documentation governance/説明のみで研究能力・条件・解釈を変えないため更新不要。
- Experiment evidence impact: experiment条件・model・実行・観測結果を取得していないため更新不要。
- Hardware / external side effects: serial open、Arduino、OSC、robot output、hardware validationなし。
