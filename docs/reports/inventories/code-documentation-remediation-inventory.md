---
status: historical
owner: architecture
last_verified: 2026-07-30
canonical_for: []
related:
  - docs/reports/audits/current-documentation-sot-audit-2026-07-30.md
  - docs/reports/inventories/documentation-policy-remediation-inventory.md
---

# Issue #485 code documentation remediation inventory

## 目的と方法

Issue #482 baseline `baabf057e02a8f5e29e51987b3ea25b92ecf6bc4`で、production sourceと
architecture-sensitive support codeをAST / export scanとmanual reviewでinventoryした。
これは#485の入力であり、docstring / JSDocの必須条件は先行#483 policyを正とする。

Python automated candidateは309 symbols、viewer TypeScript exported candidateは201 symbols、
suppression candidateは68箇所だった。候補数をそのまま欠陥数とは扱わず、thin wrapper、obvious property、
Protocol member等は#483 policyに従って除外する。scoped source内の`TODO` / `FIXME` / `HACK`と、
確認済みのcommented-out dead codeは0件だった。

## Python remediation inventory

| path | symbols / scope | finding type | rationale | priority | behavior-sensitive | recommended action | target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `src/selfrionette/runtime/experiment/contracts.py` | public contract 27件 | missing public contract docstring | six-axis contract、identity、readinessの意味が型名だけでは不足 | P1 | yes | axis責務、failure、identityを日本語で記録 | #485 |
| `src/selfrionette/runtime/experiment/composition.py` | composition API 6件 | missing lifecycle / side-effect explanation | generic compositionとproduction runtimeを誤認しやすい | P1 | yes | readiness-only境界と未接続axisを記録 | #485 |
| `src/selfrionette/runtime/composition/robot_bundle.py` | provider / bundle API 14件 | missing public contract docstring | typed Robot command providerとBundle lifecycleがarchitecture boundary | P1 | yes | capability、ownership、failureを記録 | #485 |
| `src/selfrionette/runtime/execution/command_routes.py` | route API 7件 | missing public contract docstring | command semanticsからnative commandへの変換owner | P1 | yes | input / output / unsupported routeを記録 | #485 |
| `src/selfrionette/plugins/mappings/_continuous_endpoint_velocity.py` | builder / state helpers | missing unit / frame explanation | shared algorithm primitiveのunit、dt、state継続条件が重要 | P1 | yes | unit、frame、clamp、reset条件を記録 | #485 |
| `src/selfrionette/plugins/mappings/_command_routes.py` | declaration / route factory | missing ownership explanation | algorithm ownerとroute declaration ownerの区別が必要 | P1 | yes | shared declaration責務とcallerを記録 | #485 |
| `src/selfrionette/plugins/{robots,input_sources,mappings}/{catalog,discovery,registration}.py` | public catalog APIs | missing lifecycle / identity explanation | bounded discovery、basename / logical identity、registration有無がcontract | P1 | yes | axisごとのfailure-closed contractを記録 | #485 |
| `src/selfrionette/plugins/**/plugin.py` | fixed plugin entry points | missing public contract docstring | declaration、resource、compatible identityの入口 | P1 | yes | declaration fieldsとside effectなしを記録 | #485 |
| `src/selfrionette/plugins/input_sources/{selfrionette,viewer,analog_fixture,replay,programmed_target}/**` | reader / source lifecycle | missing lifecycle / side-effect explanation | open / close、hardware boundary、replay state、poll behaviorが重要 | P1 | yes | lifecycle、I/O、failure、thread safetyを記録 | #485 |
| `src/selfrionette/schemas/experiment_log.py` | public schema 9件 | missing public contract docstring | manifest v3 / readiness / freeze identityの意味がpublic contract | P1 | yes | version、unit、required / optional semanticsを記録 | #485 |
| `src/selfrionette/schemas/viewer_control.py` | public schema 7件 | missing unit / frame explanation | viewer command fieldのunitとnormalizationが必要 | P1 | yes | unit、range、route境界を記録 | #485 |
| `src/selfrionette/schemas/{command,input_intent,state,endpoint_evaluation}.py` | public schema groups | missing public contract docstring | cross-layer payloadの意味とmaterial exclusionが不足 | P1 | yes | field semantics、unit、ownerを記録 | #485 |
| `src/selfrionette/runtime/{evaluation,control}/**` | evaluation / controller public APIs | missing unit / frame explanation | metric、denominator、hold / reject semanticsがbehavior-sensitive | P1 | yes | calculation、window、frame、failureを記録 | #485 |
| `src/selfrionette/plugins/robots/fast_arm/adapter/diagnostics/endpoint_motion_sanity.py` | 28候補 | missing unit / frame explanation | physical FK / site、axis、threshold、artifact fieldの意味が重要 | P1 | yes | mathを変えずfield / unit / frameを記録 | #485 |
| `src/selfrionette/plugins/robots/fast_arm/adapter/diagnostics/{jacobian_mobility,neutral_initial_pose}.py` | diagnostic helpers | missing rationale / unit | diagnostic判定の解釈とlimitationが不足 | P2 | yes | threshold、assumption、non-goalを記録 | #485 |
| `src/selfrionette/plugins/robots/fast_arm/{diagnostics,endpoint,feasibility,initial_state,kinematics,...}.py` | compatibility re-export wrappers | compatibility comment without retirement condition | adapter移行後のpublic wrapper継続理由が不明 | P2 | yes | #483 policyに従いrationale / removal conditionを記録または整理 | #485 |

`build_normalized_analog_fixture_intent()`等、private shared primitiveへの配置をさらに整理できる候補はあるが、
file moveやalgorithm refactorをdocumentation修正へ混ぜない。必要なら別behavior-preserving cleanupとして
scopeを明示する。

## viewer TypeScript / JSDoc inventory

| path / group | candidate symbols | finding type | priority | behavior-sensitive | recommended action | target |
| --- | ---: | --- | --- | --- | --- | --- |
| `apps/mujoco-viewer/src/input/{gamepadInput,keyboardInput,viewerInputProvider}.ts` | exported API群 | missing JSDoc / lifecycle | P1 | yes | sampling、normalization、disconnect behaviorを記録 | #485 |
| `apps/mujoco-viewer/src/wasm-scene/productViewerState.ts` | exported state projection群 | missing JSDoc / ownership | P1 | yes | Python physical SoTとprojection-only境界を記録 | #485 |
| `apps/mujoco-viewer/src/transport/**` | transport API群 | missing lifecycle / side-effect explanation | P1 | yes | connect / reconnect / error / payload ownershipを記録 | #485 |
| `apps/mujoco-viewer/src/robot-profiles/**` | declaration / resource API群 | missing identity explanation | P1 | yes | logical identity、resource binding、fallback禁止を記録 | #485 |
| `apps/mujoco-viewer/src/wasm-scene/{mujocoQposSync,qposFrameTypes,mujocoSceneRenderer,mujocoSceneTransforms}.ts` | qpos / scene renderer API群 | missing unit / frame explanation | P1 | yes | qpos ordering、frame、Three.js non-SoTを記録 | #485 |
| remaining exported viewer symbols | total automated candidates 201件 | missing exported JSDoc candidate | P2 | mixed | #483のpublic surface定義でfilterして修正 | #485 |

## suppression inventory

68候補を次のgroupで再確認する。

| group | count | finding type | priority | recommended action |
| --- | ---: | --- | --- | --- |
| endpoint motion sanity diagnostics | 12 | suppression without reason candidate | P1 | numerical / optional dependency理由をinlineで明示 |
| `schemas/experiment_log.py` | 8 | suppression without reason candidate | P1 | schema typing制約とreasonを確認 |
| evaluation / manifest | 7 | suppression without reason candidate | P1 | version / union narrowing理由を確認 |
| viewer Mapping implementation | 7 | suppression without reason candidate | P1 | typed route境界のreasonを確認 |
| neutral initial pose diagnostics | 4 | suppression without reason candidate | P2 | numerical typing reasonを確認 |
| viewer / analog fixture source | 4 + 4 | suppression without reason candidate | P2 | external payload narrowing reasonを確認 |
| robot bundle | 2 | suppression without reason candidate | P1 | provider Protocol境界のreasonを確認 |
| fast_arm thin re-export wrappers | multiple singletons | wildcard `noqa` without rationale | P2 | public compatibility理由とretirement conditionを記録 |
| other singleton `type: ignore` / `noqa` | remainder | suppression without reason candidate | P2 | individual review、不要なら削除 |

## zero-result categoriesと再確認条件

- vague / unowned `TODO` / `FIXME` / `HACK`: 0件
- confirmed commented-out dead code: 0件
- confirmed historical Issue / PR / date comment embedded in production code: 0件

automated scanのprose continuationや「validated」等をfalse positiveとして除外した。#485開始時は#483 policyと
actual stack baseを取得し直し、新規差分に同categoryが増えていないことを再検査する。

## execution order

1. #483 policyでrequired / optional surfaceとlanguage boundaryを確定する。
2. architecture-sensitive P1 contract、unit、frame、lifecycleから修正する。
3. suppressionを理由付きにするか不要化する。
4. P2 wrapper / obvious symbolsをpolicyに従ってfilterする。
5. behavior、public API、schema、plugin identityを変えないfocused testsを実行する。
