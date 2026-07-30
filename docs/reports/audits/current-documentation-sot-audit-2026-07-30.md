---
status: historical
owner: architecture
last_verified: 2026-07-30
canonical_for: []
related:
  - docs/README.md
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/contracts/runtime-input-source-registry.md
  - docs/reports/inventories/documentation-policy-remediation-inventory.md
  - docs/reports/inventories/readme-remediation-inventory.md
  - docs/reports/inventories/code-documentation-remediation-inventory.md
---

# Issue #482 current documentation SoT監査

## 位置付け

この文書は、Issue #482の監査結果をbaseline時点のevidenceとして固定するsupporting audit reportである。
current architecture、contract、operationのsource of truthではない。現在仕様は
[`docs/README.md`](../../README.md)から各canonical documentを参照する。

- baseline main: `baabf057e02a8f5e29e51987b3ea25b92ecf6bc4`
- baseline date: 2026-07-30
- scope: Issue #421、#478、#480までに統合された実装、architecture tests、tracked Markdown、
  existing README、canonical metadata、relative links
- stack position: `main`をbaseとするstack root

## 方法

tracked Markdown全件を機械的に列挙し、front matter、Source of Truth Map、relative link、README配置を
検査した。次に、`src/selfrionette/plugins/`、experiment / composition / execution / evaluation /
control runtime、CLI、viewer application-facing path、`tests/architecture/`をsymbolsとcall path単位で
照合した。PR #479とPR #481は最終diffを、Issue #293と#421、#478、#480、#482～#486は
current bodyを確認した。

分類は次の意味で用いた。

- `canonical-current`: current topicの一意なowner
- `supporting-current`: canonical ownerへroutingするcurrent補助文書
- `historical-evidence`: 当時の状態を保存するevidence
- `audit-or-completion-snapshot`: 監査・移行・完了時点のsnapshot
- `stale-current`: currentとして案内する内容がactual実装・testと矛盾
- `duplicate-canonical-topic`: 同じcurrent topicを複数文書がownerとして宣言
- `missing-canonical-owner`: current topicにownerがない
- `missing-human-facing-entry-point`: current ownerはあるが、README等の入口がない

historical documentに当時のpathやownershipが残ることは`stale-current`に含めていない。

## inventory集計

baselineではtracked Markdown 180件、tracked README 24件を確認した。Issue #482で本監査報告と
3 inventoryを追加した後の分類は、`canonical` 61件、`supporting` 15件、`historical` 85件、
`draft` 6件、`obsolete` 1件、front matter非対象16件である。Source of Truth Mapのtargetは
`docs/README.md`自身を除くcanonical document 60件と一致する。

baselineに存在したhistorical / draft / obsolete 88件はcurrent仕様へ改稿していない。
front matter非対象のREADME等16件は入口として監査し、必要な後続actionをinventoryへ記録した。

## finding summary

| finding | baseline | #482 correction | final |
| --- | ---: | ---: | ---: |
| stale-current finding group | 15 | 15 | 0 |
| duplicate canonical topic | 1 | 1 | 0 |
| missing canonical owner | 0 | 0 | 0 |
| canonical document missing from Map | 16 | 16 | 0 |
| broken relative link | 0 | 0 | 0 |
| retired path / stale identity in current docs | 6 | 6 | 0 |
| P0 / P1 blocker | 0 | 0 | 0 |

既存canonical 16件がSource of Truth Mapから欠落していたが、owner文書自体の欠落はなかった。
新しいcanonical ownerを設けずMapへ追加した。

## corrected current SoT

### axis-local plugin infrastructure

current root `src/selfrionette/plugins/`に残る共通moduleは`bounded_discovery.py`とpackage
`__init__.py`だけである。Robot、Input Source、Control Mappingのcatalog / discoveryは各axisが
所有し、RobotとInput Sourceだけがruntime registrationを持つ。Mappingはruntime lifecycleを
登録せず、宣言をcatalogから選択してcommand semantics routeをruntimeが構成するため、
registration layerを持たない。

bounded discoveryは固定entry pointをimportし、package basenameとlogical identityを独立に検証する。
application-facing projectionはaxis catalogを唯一のsourceとして使用する。retired root registration /
discovery pathをcurrent pathとして案内していたcontractとREADMEを修正した。

### Mapping private shared owners

2つのprivate ownerを別責務として固定した。

- `_continuous_endpoint_velocity.py`: axis-local shared algorithm primitive
- `_command_routes.py`: axis-local shared declaration / route factory

`build_normalized_analog_fixture_intent()`等の細かなowner整理はbehavior-preserving cleanup候補として
#485 inventoryへ渡し、本Issueではfile moveやalgorithm refactorを行っていない。

### six-axis experiment composition

Robot Bundle、Environment / Scene、Control Mapping、Task、Evaluation、Input Source、
command semantics routeを表すgeneric contractとtest fixtureは存在する。一方、production concrete
plugin、catalog / discovery、manifest readiness、application-facing selectionが現在成立するのは
Robot、Input Source、Control Mappingを中心とするdiagnostic / operational runtimeである。

Environment、Task、Evaluationはaxis packageだけが存在し、production concrete plugin、catalog、
runner / CLI / viewer selectionは存在しない。viewerやreplayがこれらを選ばないことをbugとは分類しない。
full experiment control planeはIssue #486のplanned scopeである。

### Source of Truth Mapとmetadata

Mapを全canonical documentへ展開し、canonical / supporting metadataの必須field、canonical topicの
一意性、supporting documentの空`canonical_for`、Map targetのstatusとcoverageをvalidatorと
architecture testで検査するようにした。重複topic 1件とsupporting文書4件の誤ったowner宣言を解消した。

### existing README

root READMEのfirst-read routingと、`kinematics`、`motion`、`mujoco_backend`、`runtime`、
`transport` READMEに残っていたretired interpreter / runtime facade / stub予約を修正した。
README hierarchyの新設や全READMEの書式統一は行わず、残りは#484 inventoryへ渡した。

## intentionally unchanged historical documents

completion audit、migration snapshot、過去Issue固有report、experiment evidenceの本文は変更していない。
過去時点のpath、PR番号、ownershipがcurrentと異なる場合もprovenanceとして保持した。metadata修正は、
supporting文書をcurrent canonical ownerと誤認させる4件に限定した。

## unresolved material findings

Issue #482をblockするP0 / P1 findingはない。current behavior bug、schema不整合、plugin identity不整合も
発見していない。README入口不足、code documentation不足、policy owner不足は意図したfollow-up scopeであり、
それぞれ#484、#485、#483へinventoryとして渡す。

## follow-up handoff

- #483: [`documentation-policy-remediation-inventory.md`](../inventories/documentation-policy-remediation-inventory.md)
- #484: [`readme-remediation-inventory.md`](../inventories/readme-remediation-inventory.md)
- #485: [`code-documentation-remediation-inventory.md`](../inventories/code-documentation-remediation-inventory.md)

各Issue開始時にはactual stack baseを再取得する。inventoryはbaseline evidenceとして引き継ぐが、
実装方法を固定するcanonical policyとして扱わない。

## impact判断

- Documentation impact: あり。current canonical docs、Source of Truth Map、existing current README、
  governance validator / architecture testをactual implementationへ同期した。
- Research log impact: なし。研究で実行・評価できる能力、実験条件、metric、仮説、主張範囲を変更していない。
- Experiment evidence impact: なし。新しいexperiment condition、model、fixture、観測結果を取得していない。
- Behavior impact: なし。runtime、viewer、simulation、schema、public API、plugin identityは変更していない。

## stack handoff

`codex/482-current-documentation-sot-audit`はstack rootである。#483は#482 headから開始し、#484と#485は
#483 headから互いに独立して分岐する。#482 merge後も、dependent PRを最新mainへrebase / retargetし、
Issue固有diffとCIを再確認するまでは#482 source branchを削除しない。
